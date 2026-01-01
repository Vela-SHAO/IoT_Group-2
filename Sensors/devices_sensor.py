import time
import json
import random
import datetime
import os, sys
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

        loader = loader_instance if loader_instance else RoomConfigLoader(config_path)
        self.capacity = loader.get_room_config(target_room_id=self.room)["meta"].get("capabilities", 30)
        self.people_count = random.randint(int(self.capacity * 0.1), int(self.capacity * 0.5))

        print(f"[{sensor_type}] Init: {self.room}, Max: {self.capacity}, Start People: {self.people_count}")
        
    def _simulate_people_movement(self):
       
        change = random.randint(-3, 5)
        self.people_count += change

        if self.people_count < 0: 
            self.people_count = 0
        if self.people_count > self.capacity: 
            self.people_count = self.capacity
            
        return self.people_count

    def start(self):

        if not self.register_to_catalog(self.topics):
            return False

        client = self.connect_mqtt()

        print(f"[*] Sensor started. Publishing to: {self.topics['val']}")


        try:
            while True:
                current_people = self._simulate_people_movement()
                value = 0
                if self.sensor_type == "temperature":
                    month = datetime.datetime.now().month
                    if month in [11, 12, 1, 2, 3]: 
                        base = 18.5 # winter
                    elif month in [6, 7, 8]:       
                        base = 26.0 # summer
                    else:                          
                        base = 22.0 # spring/fall

                    heat_rise = (current_people / self.capacity) * 3.5

                    value = round(base + heat_rise, 2)
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
                print(f"--> Sent: {payload}")

                time.sleep(self.frequency)

        except KeyboardInterrupt:
            client.loop_stop()
            print("Sensor Stopped")


