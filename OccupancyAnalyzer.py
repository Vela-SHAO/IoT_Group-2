import sys
import os
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# ==========================================
# 1. 路径自动定位：确保无论在哪运行都能找到文件
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 导入自定义模块
from Catalog.config_loader import RoomConfigLoader
from ThermalLogic import decide_hvac_status

class OccupancyAnalyzer:
    def __init__(self, schedule_name, config_name):
        # 自动拼接文件绝对路径
        schedule_path = os.path.join(BASE_DIR, schedule_name)
        config_path = os.path.join(BASE_DIR, config_name)
        
        # 加载静态课表 [中文注释供协作]
        with open(schedule_path, 'r', encoding='utf-8') as f:
            self.schedule = json.load(f)
        
        # 2. 容错加载配置：解决 KeyError 'port' 问题
        self.loader = RoomConfigLoader(config_path)
        broker_info = self.loader.get_broker_info()
        
        self.broker = broker_info.get("broker", "broker.hivemq.com")
        # 优先读取 port，如果没有则读取 broker_port，再没有则默认 1883
        self.port = broker_info.get("port") or broker_info.get("broker_port") or 1883
        self.base_topic = broker_info.get("base_topic_prefix", "polito/smartcampus")
        
        # 内存缓存
        self.occupancy_cache = {}

    def get_current_slot(self):
        """Map time to schedule slot (All English output)"""
        hour = datetime.now().hour
        if 8 <= hour < 10: return "1"
        if 10 <= hour < 12: return "2"
        if 12 <= hour < 14: return "3"
        return "4"

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # 订阅 MockSensors 发出的数据
            topic = "polito/smartcampus/+/occupancy/value"
            client.subscribe(topic)
            print(f"[*] Connection Success! Subscribed to: {topic}")
        else:
            print(f"[!] Connection Failed. Code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # Topic 结构: polito/smartcampus/R1/occupancy/value
            # split('/') 之后，R1 在索引 2 的位置
            parts = msg.topic.split('/')
            room_id = parts[2] 

            count = int(msg.payload.decode())
            self.occupancy_cache[room_id] = count
            self.process_analysis(room_id, count)
        except Exception as e:
            print(f"[ERROR] Parsing failed: {e}")

    def process_analysis(self, room_id, count):
        try:
            # 1. 获取房间配置
            room_meta = self.loader.get_room_config(room_id)["meta"]
            capacity = room_meta["capacity"]
            
            # 2. 调用逻辑判断
            ac_on = decide_hvac_status(28, count, capacity)
            is_free = room_id in self.schedule.get(self.get_current_slot(), [])
            
            # 3. 【修改】打包成 Mya 要求的JSON 格式
            analysis_result = {
                "room_id": room_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": {
                    "students_count": count,
                    "capacity": capacity,
                    "is_available": is_free,
                    "hvac_status": "ON" if ac_on else "OFF"
                },
                "raw_flags": {
                    "usage": "AVAILABLE" if is_free else "IN_CLASS",
                    "ac_icon": "❄️" if ac_on else "💤"
                }
            }
            
            # 4. 打印 JSON 字符串（方便 Mya 后续取值）
            print(json.dumps(analysis_result))
            
            # 5. (可选) 如果需要发回 MQTT 供其他设备订阅
            # self.client.publish(f"building/analysis/{room_id}", json.dumps(analysis_result))

        except Exception as e:
            # print(f"[DEBUG] Skipping or Error for room {room_id}: {e}")
            pass

    def start(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        print(f"[*] Connecting to {self.broker}:{self.port}...")
        client.connect(self.broker, self.port, 60)
        client.loop_forever()

if __name__ == "__main__":
    analyzer = OccupancyAnalyzer("schedule.json", "setting_config.json")
    analyzer.start()