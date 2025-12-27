import sys
import os
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime

# 保持对 ThermalLogic 的引用
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ThermalLogic import decide_hvac_status

class OccupancyAnalyzer:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.occupancy_cache = {}
        
        # 加载静态课表（仍使用本地文件）
        schedule_path = os.path.join(BASE_DIR, "schedule.json")
        with open(schedule_path, 'r', encoding='utf-8') as f:
            self.schedule = json.load(f)

        print(f"[*] Fetching MQTT config from Catalog: {self.catalog_url}")
        try:
            response = requests.get(f"{self.catalog_url}/api/services")
            # 增加检查：如果响应为空或不是 200，则跳过
            if response.status_code == 200 and response.text.strip():
                services = response.json()
                mqtt_service = next((s for s in services if s.get("service_type") == "mqtt"), None)
                
                if mqtt_service:
                    self.broker = mqtt_service["endpoint"]["broker"]
                    self.port = mqtt_service["endpoint"]["broker_port"]
                    self.topic_structure = mqtt_service["endpoint"]["topic_structure"]
                    print(f"[*] Config Loaded from Catalog: {self.broker}:{self.port}")
                    return # 成功拿到配置，退出初始化
            
            raise ValueError("MQTT service not found in Catalog response")

        except Exception as e:
            # --- 容错方案：如果 Catalog 没给数据，使用默认值 ---
            print(f"[!] Warning: Falling back to default config due to: {e}")
            self.broker = "test.mosquitto.org"
            self.port = 1883
            self.topic_structure = "polito/smartcampus/{room_id}/{device_type}/{index_number}"

    def get_dynamic_topic(self, room_id, device_type, index="1"):
        """按照 Mya 的结构生成 Topic: polito/smartcampus/{room}/{type}/{index}"""
        return self.topic_structure.replace("{room_id}", room_id)\
                                   .replace("{device_type}", device_type)\
                                   .replace("{index_number}", index)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # 订阅所有房间的 wifi 传感器数据 (用于统计人数)
            # 根据 Mya 的结构，wifi 数据的 Topic 是 .../{room_id}/wifi/{index}/value
            sub_topic = self.get_dynamic_topic("+", "wifi", "+") + "/value"
            client.subscribe(sub_topic)
            print(f"[*] Success! Subscribed to: {sub_topic}")
        else:
            print(f"[!] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # 解析 Topic 拿到 room_id (例如: polito/smartcampus/R1/wifi/1/value)
            parts = msg.topic.split('/')
            room_id = parts[2]
            count = int(msg.payload.decode())
            self.process_analysis(room_id, count)
        except Exception as e:
            print(f"[ERROR] on_message: {e}")

    def process_analysis(self, room_id, count):
        try:
            # 2. 从 Catalog 获取房间的 meta 信息（比如容量）
            # Mya 的 Catalog 提供了 /api/devices?room=R1 的过滤功能
            dev_resp = requests.get(f"{self.catalog_url}/api/devices", params={"room": room_id, "type": "temperature"})
            devices = dev_resp.json()
            
            # 如果 Catalog 里没找到这个房间，默认用 30 人
            capacity = 30
            if devices:
                # 假设我们从第一个关联设备的 location meta 里拿容量 (或根据 Mya 的结构调整)
                capacity = 30 # 这里可以根据 Mya 真实的 device 结构进一步细化获取方式

            # 3. 核心逻辑判断
            ac_on = decide_hvac_status(28, count, capacity)
            
            # 4. 生成分析结果 JSON
            analysis_result = {
                "room_id": room_id,
                "status": "occupied" if count > 0 else "free",
                "hvac_status": "ON" if ac_on else "OFF",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 5. 【Mya 的核心要求】Post back 给 Catalog 注册/更新状态
            requests.post(f"{self.catalog_url}/api/devices", json={
                "id": f"Analysis_{room_id}",
                "type": "analysis_result",
                "resources": ["status", "hvac"],
                "mqtt_topics": {"val": self.get_dynamic_topic(room_id, "analysis")},
                "location": {"campus": "POLITO", "building": "R", "floor": "0", "room": room_id},
                "last_value": analysis_result
            })

            print(f"[SENT TO CATALOG] {room_id}: {analysis_result['status']}")

        except Exception as e:
            print(f"[ERROR] analysis: {e}")

    def start(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(self.broker, self.port, 60)
        client.loop_forever()

if __name__ == "__main__":
    # 传入 Catalog 的地址
    analyzer = OccupancyAnalyzer("http://127.0.0.1:8080")
    analyzer.start()