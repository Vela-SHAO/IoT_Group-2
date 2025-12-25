import json
import os

class RoomConfigLoader:
    def __init__(self, config_path):
        # 自动处理绝对路径，防止文件找不到
        if not os.path.isabs(config_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, config_path)
            
        self.config_path = config_path
        self.data = self._load_data()

    def _load_data(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"[-] Config file missing: {self.config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"[-] Config file is not valid JSON: {self.config_path}")
    
    def get_broker_info(self):
        mqtt = self.data.get("mqtt_config", {})
        return {
            "broker": mqtt.get("broker_address", "127.0.0.1"),
            "port": mqtt.get("broker_port", 1883),
            "catalog_url": mqtt.get("catalog_url", "http://127.0.0.1:8080"),
            "base_topic_prefix": mqtt.get("base_topic_prefix", "polito/smartcampus")
        }

    def get_room_config(self, target_room_id):

        # 1. 提取全局信息 (Project Info)
        project_info = self.data.get("project_info", {})
        campus = project_info.get("campus", "Unknown")
        building = project_info.get("building", "Unknown")


        # 3. 查找具体房间
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
                "building": building,
                "floor": found_room["floor"],      # 用数字 "0"
                "room": target_room_id
            },
            "meta": {
                "type": found_room.get("type"),
                "capacity": found_room.get("capacity")
            }
        }


if __name__ == "__main__":
    loader = RoomConfigLoader("setting_config.json")
    try:
        broker_info = loader.get_broker_info()
        print(f"Broker Info: {broker_info}")
        conf = loader.get_room_config("R1")
        print(f"成功加载 R1 配置: {conf}")
    except Exception as e:
        print(e)