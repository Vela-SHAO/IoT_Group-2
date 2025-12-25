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

        # 1. 提取全局信息 (Project Info)
        project_info = self.data.get("project_info", {})
        campus = project_info.get("campus", "Unknown")
        rooms_list = self.data.get("rooms", [])

        # 2. 如果没有指定房间，返回所有所有房间名称
        if not target_room_id:
            return [room["room_id"] for room in rooms_list]


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
                "building": found_room["building"],  # 用字母 "R"
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