import requests
import json
import paho.mqtt.client as mqtt
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader

class GenericDevice:
    def __init__(self, room="R1", index=1, sensor_type="unknown", role="unknown", frequency=10):

        self.room = room
        self.index = index
        self.sensor_type = sensor_type
        self.role = role
        self.frequency = frequency
        self.device_id = f"{self.room}_{self.sensor_type}_{self.role}_{self.index}"

        self.broker = None
        self.port = None
        self.base_topic = None
        self.client = None
        self.mqtt_topics = {}

        loader = RoomConfigLoader("setting_config.json")
        cata_info = loader.get_catalog_info()
        self.catalog_url = f"http://{cata_info['host']}:{cata_info['port']}{cata_info['api_path']}"

        # fexible location assignment
        try:
            room_config = loader.get_room_config(self.room)
            if self.room:
                self.location = room_config.get("location")
            else:
                raise ValueError("Room ID not found in configuration.")
        except Exception:
            self.location = {
                "campus": "Unknown",
                "building": "Unknown",
                "floor": "0",
                "room": room
                }

        if not self._discover_services():
            raise ConnectionError("CRITICAL: Failed to discover MQTT Broker from Catalog!")
    
    def _discover_services(self):
        service_url = f"{self.catalog_url}/services"
        print(f"[{self.device_id}] Discovering services at {service_url}...")

        try:
            res = requests.get(service_url)
            if res.status_code != 200:
                print(f"[-] Service Discovery Failed with status code: {res.status_code}")
                return False
            
            services = res.json()
            for service in services:
                if service["service_type"] == "mqtt":
                    self.broker = service["endpoint"]["broker"]
                    self.port = service["endpoint"]["broker_port"]
                    
                    topic_template = service["endpoint"].get("topic_structure")
                    self.base_topic = topic_template.format(
                        room_id=self.room,
                        device_type=self.sensor_type,
                        index_number=self.index
                    )
                    return True
            
            print("[-] MQTT Broker service not found in Catalog.")
            return False
        
        except Exception as e:
            print(f"   [-] Discovery failed: {e}")
            return False
        
    def register_to_catalog(self, specific_topics):

        print(f"[*] Registering {self.device_id}...")
        device_url = f"{self.catalog_url}/devices"
        
        payload = {
            "id": self.device_id,
            "type": self.sensor_type,
            "resources": list(specific_topics.keys()),
            "mqtt_topics": specific_topics,
            "update_interval": self.frequency,
            "location": self.location
        }

        try:
            res = requests.post(device_url, json=payload)
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
        self.client = mqtt.Client(client_id=self.device_id)
        print(f"[*] Connecting to Broker: {self.broker}...")
        try:
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            return self.client
        except Exception as e:
            print(f"   [!] MQTT Connection failed: {e}")
            return None