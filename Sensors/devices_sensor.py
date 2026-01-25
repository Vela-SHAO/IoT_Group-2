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
config_path = os.path.join(project_root, "setting_config.json")


class Sensor(GenericDevice):
    def __init__(self, room, index, sensor_type, frequency=None, loader_instance=None):

        if frequency is None:
            frequency = 5

        super().__init__(room, index, sensor_type, "sensor", frequency)
        self.topics = {"val": self.base_topic + "/value"}

        # about wifi people count part and control people movement simulation
        loader = loader_instance if loader_instance else RoomConfigLoader(config_path)
        try:
            self.capacity = loader.get_room_config(target_room_id=self.room)["meta"].get("capabilities", 30)
        except:
            self.capacity = 30
        self.people_count = random.randint(int(self.capacity * 0.1), int(self.capacity * 0.5))
        self.last_wifi_update_time = time.time()
        self.wifi_interval = 30
        self.current_temp = 22.0

        print(f"[{sensor_type}] Init: {self.room}, Max: {self.capacity}, Start People: {self.people_count}, Start Temp: {self.current_temp} C")

        
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
            base_temp = 18.0 
        elif month in [6, 7, 8]:       
            base_temp = 28.0
        else:                          
            base_temp = 22.0

        heat_from_people = (current_people / self.capacity) * 8.0
        final_target_temp = base_temp + heat_from_people

        step = 0.1
        if self.current_temp < final_target_temp:
            self.current_temp += step
            if self.current_temp > final_target_temp:
                self.current_temp = final_target_temp
        elif self.current_temp > final_target_temp:
            self.current_temp -= step
            if self.current_temp < final_target_temp:
                self.current_temp = final_target_temp
        
        return round(self.current_temp, 2)

    def start(self):

        if not self.register_to_catalog(self.topics):
            return False
        client = self.connect_mqtt()
        if not client:
            print("Error: MQTT Connection failed.")
            return False
        
        try:
            while True:
                current_time = time.time()
                payload = {}

                if current_time - self.last_wifi_update_time >= self.wifi_interval:
                    self.people_count = self._simulate_people_movement()
                    self.last_wifi_update_time = current_time
                
                if self.sensor_type == "wifi":
                    payload = {
                        "id": self.device_id,
                        "v": self.people_count,
                        "u": "count",
                        "t": time.time()
                    }
                    print(f"[wifi] {self.room} People: {self.people_count}")
                elif self.sensor_type == "temperature":
                    temp_val = self.calculate_physics_temp(self.people_count)
                    payload = {
                        "id": self.device_id,
                        "v": temp_val,
                        "u": "C",
                        "t": time.time()
                    }
                    print(f"[temp] {self.room} Temperature: {temp_val} C")
                
                if payload:
                    client.publish(self.topics["val"], json.dumps(payload))
                
                time.sleep(self.frequency)

            
        except KeyboardInterrupt:
            client.loop_stop()
            print("Sensor Stopped")


