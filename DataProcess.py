import json
import paho.mqtt.client as mqtt
import os

class SmartCampusProcessor:
    def __init__(self, config_filename):
        # 自动获取路径，确保读取 IoT_Shao 文件夹下的 JSON
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, config_filename)
        
        print(f"Loading configuration from: {full_path}")
        with open(full_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 将教室列表转为字典
        self.rooms = {r['room_id']: r for r in self.config['rooms']}
        # 使用公共测试 Broker
        self.broker = "broker.hivemq.com" 
        self.port = 1883

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Successfully connected to MQTT Broker!")
            # 订阅主题：building/R/+/occupancy
            topic = f"building/{self.config['building']}/+/occupancy"
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
        else:
            print(f"Connection failed with code: {rc}")

    def on_message(self, client, userdata, msg):
        """处理传感器消息"""
        try:
            # 提取 Room ID 和人数
            room_id = msg.topic.split('/')[-2]
            new_occupancy = int(msg.payload.decode())
            
            if room_id in self.rooms:
                # 更新内存数据
                self.rooms[room_id]['current_people'] = new_occupancy
                
                # 执行温控逻辑
                self.thermal_control_logic(client, room_id, new_occupancy)
                
                # 执行推荐逻辑
                self.check_recommendation()
        except Exception as e:
            print(f"Error processing message: {e}")

    def thermal_control_logic(self, client, room_id, occupancy):
        """自适应温控逻辑 (Presence-Based Thermal Control)"""
        target_topic = f"building/R/{room_id}/hvac/control"
        
        # 逻辑：有人开启舒适模式，无人开启节能模式
        if occupancy > 0:
            command = {"status": "ON", "target_temp": 22, "mode": "Comfort"}
            print(f"[HVAC] Room {room_id}: Occupied ({occupancy} ppl). Sending ON command.")
        else:
            command = {"status": "OFF", "target_temp": 26, "mode": "EnergySaving"}
            print(f"[HVAC] Room {room_id}: Empty. Sending OFF/EnergySaving command.")
            
        client.publish(target_topic, json.dumps(command))

    def check_recommendation(self):
        """教室推荐逻辑 (Study-room Recommendation)"""
        results = []
        for r in self.rooms.values():
            rate = (r['current_people'] / r['capacity']) * 100
            results.append({
                "id": r['room_id'],
                "type": r['type'],
                "rate": rate,
                "people": r['current_people']
            })
        
        # 按照上座率排序
        results.sort(key=lambda x: x['rate'])
        
        print("\n--- Real-time Study-room Recommendations (Top 3) ---")
        for r in results[:3]:
            print(f"ID: {r['id']:<5} | Type: {r['type']:<15} | Occupancy: {r['rate']:>6.2f}% | People: {r['people']}")
        print("----------------------------------------------------\n")

    def run(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        print(f"Connecting to broker {self.broker}...")
        client.connect(self.broker, self.port, 60)
        client.loop_forever()

if __name__ == "__main__":
    # 实例化并运行
    processor = SmartCampusProcessor("rooms_config.json")
    processor.run()