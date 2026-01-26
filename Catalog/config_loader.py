import json
import os

class RoomConfigLoader:
    def __init__(self, config_filename):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)


        possible_paths = [
            os.path.join(project_root, config_filename),  
            os.path.join(current_dir, config_filename),   
            config_filename                               
        ]

        self.config_path = None

        for path in possible_paths:
            if os.path.exists(path):
                self.config_path = path
                break
        
        if self.config_path is None:
            self.config_path = os.path.join(project_root, config_filename)

        self.data = self._load_data()

    def _load_data(self):
        print(f"[*] Loading config from: {self.config_path}") 
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"[-] Config file NOT found at: {self.config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"[-] Invalid JSON format in: {self.config_path}")
    
    def get_broker_info(self):
        mqtt = self.data.get("mqtt_config", {})
        return {
            "broker": mqtt.get("broker_address", "test.mosquitto.org"),
            "broker_port": mqtt.get("broker_port", 1883),
            "base_topic_prefix": mqtt.get("base_topic_prefix", "polito/smartcampus")
        }
    
    def get_catalog_info(self):
        catalog = self.data.get("catalog_config", {})
        return {
            "host": catalog.get("host", "127.0.0.1"),
            "port": catalog.get("port", 8080),
            "api_path": catalog.get("api_path", "/api")
        }

    def get_room_config(self, target_room_id=None):

    
        project_info = self.data.get("project_info", {})
        campus = project_info.get("campus", "Unknown")
        rooms_list = self.data.get("rooms", [])

        if not target_room_id:
            return [room["room_id"] for room in rooms_list]


        found_room = None
        for room in self.data.get("rooms", []):
            if room["room_id"] == target_room_id:
                found_room = room
                break
        
        if not found_room:
            raise ValueError(f"Room ID '{target_room_id}' not found in configuration.")


        return {
            "location": {
                "campus": campus,
                "building": found_room["building"],  
                "floor": found_room["floor"],     
                "room": target_room_id
            },
            "meta": {
                "type": found_room.get("type"),
                "capacity": found_room.get("capacity")
            }
        }


