import time
import json
import random
import datetime
import os, sys
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader
from devices_base import GenericDevice

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
config_path = os.path.join(project_root, "Catalog", "setting_config.json")

# ==========================================
# 子类 1: Sensor (传感器)
# 职责：注册 -> 连接 -> 循环生成数据 -> 发布
# ==========================================
class Sensor(GenericDevice):
    def __init__(self, room, index, sensor_type, frequency, loader_instance=None):

        super().__init__(room, index, sensor_type, "sensor", frequency)
        self.topics = {"val": self.base_topic + "/value"}

        # about wifi people count part
        loader = loader_instance if loader_instance else RoomConfigLoader(config_path)
        self.capacity = loader.get_room_config(target_room_id=self.room)["meta"].get("capabilities", 30)
        self.people_count = random.randint(int(self.capacity * 0.1), int(self.capacity * 0.5))
        self.last_wifi_update_time = 0 # last time when people count was updated
        self.wifi_interval = 60 # seconds for people count interval

        # about temperature part
        self.current_temp = 22.0
        self.ac_status = "OFF"
        self.ac_mode = "auto"
        self.ac_target_temp = 24.0

        # sensor will look for its corresponding actuator topic (just for simulate the real scenario)
        self.target_actuator_topic = None

        print(f"[{sensor_type}] Init: {self.room}, Max: {self.capacity}, Start People: {self.people_count}")

    def _lookup_actuator_topic(self):
        if self.sensor_type != "temperature":
            return None
        
        search_url = f"{self.catalog_url}/devices"

        try:
            res = requests.get(search_url, params={"room": self.room})
            if res.status_code == 200:
                devices = res.json()
                for dev in devices:
                    if dev["id"] == self.device_id: continue
                    
                    mqtt_topics = dev.get("mqtt_topics", {})
                    if "status" in mqtt_topics:
                        found = mqtt_topics["status"]
                        print(f"    -> Found Actuator Topic: {found}")
                        return found
            
            return None
            
        except Exception as e:
            print(f"   [-] Actuator lookup failed: {e}")
            return None
        
    def on_actuator_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            if "status" in payload:
                self.ac_status = payload["status"]

            if "target_temp" in payload:
                self.ac_target_temp = float(payload["target_temp"])
        except:
            pass

        
    def _simulate_people_movement(self):
       
        change = random.randint(-3, 5)
        self.people_count += change

        if self.people_count < 0: 
            self.people_count = 0
        if self.people_count > self.capacity: 
            self.people_count = self.capacity
            
        return self.people_count
    
    def calculate_physics_temp(self, current_people):
        
        month = datetime.datetime.now().month
        if month in [11, 12, 1, 2, 3]: 
            base_outdoor = 10.0 
        elif month in [6, 7, 8]:       
            base_outdoor = 30.0
        else:                          
            base_outdoor = 22.0

        heat_from_people = (current_people / self.capacity) * 5.0
        natural_target = (base_outdoor + heat_from_people)

        final_target_temp = natural_target

        if self.ac_status == "ON":
            final_target_temp = self.ac_target_temp

        step = 0.3

        if self.current_temp < final_target_temp:
            change = min(step, final_target_temp - self.current_temp)
            self.current_temp += change
        elif self.current_temp > final_target_temp:
            change = min(step, self.current_temp - final_target_temp)
            self.current_temp -= change
        
        return round(self.current_temp, 2)

    def start(self):

        if not self.register_to_catalog(self.topics):
            return False
        
        if self.sensor_type == "temperature":
            print(f"[*] Looking up actuator for room {self.room}...")
            while self.target_actuator_topic is None:
                self.target_actuator_topic = self._lookup_actuator_topic()
                if self.target_actuator_topic is None:
                    print("    [-] Actuator not found, retrying in 2s...")
                    time.sleep(2)

        client = self.connect_mqtt()

        print(f"[*] Sensor started. Publishing to: {self.topics['val']}")

        if self.target_actuator_topic:
            client.subscribe(self.target_actuator_topic)
            client.message_callback_add(self.target_actuator_topic, self.on_actuator_message)
            print(f"[*] Subscribed to Actuator Topic: {self.target_actuator_topic}")

        last_reported_people = -1

        try:
            while True:
                current_time = time.time()
                if current_time - self.last_wifi_update_time >= self.wifi_interval:
                    current_people = self._simulate_people_movement()
                    self.last_wifi_update_time = current_time
                    print(f"   [Simulation] Room {self.room} People Updated: {current_people}")
                    last_reported_people = current_people
                else:
                    current_people = self.people_count

                value = 0
                if self.sensor_type == "temperature":
                    value = self.calculate_physics_temp(current_people)
                else:
                    value = current_people
                
                unit = "C" if self.sensor_type == "temperature" else "count"

                payload = {
                    "id": self.device_id,
                    "v": value,
                    "u": unit,
                    "t": time.time()
                }

                client.publish(self.topics['val'], json.dumps(payload))
                if self.sensor_type == "temperature":
                    print(f"--> {self.room}[Temp] {value}C (Target:{self.ac_target_temp}, AC:{self.ac_status})")
                else:
                    if value != last_reported_people:
                        print(f"--> {self.room}[WiFi] People Count: {value}")
                        last_reported_people = value
                    else:
                        pass

                time.sleep(self.frequency)

        except KeyboardInterrupt:
            client.loop_stop()
            print("Sensor Stopped")


