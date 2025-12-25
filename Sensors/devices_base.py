import requests
import json
import paho.mqtt.client as mqtt
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader

class GenericDevice:
    def __init__(self, room, index, catalog_type, role, frequency):

        self.room = room
        self.catalog_type = catalog_type
        self.role = role
        self.frequency = frequency

        loader = RoomConfigLoader("setting_config.json")
        broker_info = loader.get_broker_info()
        self.broker = broker_info["broker"]
        self.port = broker_info["port"]
        self.catalog_url = broker_info["catalog_url"] + "/api/devices"
        self.base_topic_prefix = broker_info["base_topic_prefix"]
        print(f"DEBUG: Catalog URL is {self.catalog_url}")

        location = loader.get_room_config(room)["location"]
        self.campus = location["campus"]
        self.building = location["building"]
        self.floor = location["floor"]


        self.device_id = f"{self.room}_{self.catalog_type}_{self.role}_{index}"
        self.base_topic = f"{self.base_topic_prefix}/{room}/{self.catalog_type}/{self.device_id}"
        
        self.mqtt_topics = {} 

    def register_to_catalog(self, specific_topics):

        print(f"[*] Registering {self.device_id}...")
        
        payload = {
            "id": self.device_id,
            "type": self.catalog_type,  # 记住：Catalog 只要 "temperature" 或 "wifi"
            "resources": list(specific_topics.keys()),
            "mqtt_topics": specific_topics,
            "update_interval": self.frequency,
            "location": {
                "campus": self.campus,
                "building": self.building,
                "floor": self.floor,
                "room": self.room
            }
        }

        try:
            # 发送请求
            res = requests.post(self.catalog_url, json=payload)
            if res.status_code in [200, 201]:
                print(f"[+] Registered: {self.device_id}")
                return True
            else:
                print(f"[-] Catalog Refused!")
                print(f"Status Code: {res.status_code}")
                print(f"Response Text: {res.text}")
                return False
        except Exception as e:
            print(f"[-] Connection Error: {e}")
            return False

    def connect_mqtt(self):
        # 通用的 MQTT 连接逻辑
        self.client = mqtt.Client(client_id=self.device_id)
        print(f"[*] Connecting to Broker: {self.broker}...")
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        return self.client