import paho.mqtt.client as mqtt
import time
import random

# 使用与 DataProcess.py 相同的公共 Broker
BROKER = "broker.hivemq.com"
PORT = 1883
# 我们要模拟的房间列表
ROOMS = ["R1", "R1B", "R2", "R2B", "RS1", "RS2"]

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

print("--- IoT Campus Mock Sensor Started ---")
print("Simulating real-time occupancy updates for Building R...")

try:
    while True:
        # 随机选择一个房间
        room = random.choice(ROOMS)
        # 随机产生一个人数 (0 到 150 之间)
        occupancy = random.randint(0, 150)
        
        topic = f"building/R/{room}/occupancy"
        client.publish(topic, str(occupancy))
        
        print(f"Update sent: {room} now has {occupancy} students.")
        time.sleep(5) # 每 5 秒更新一次
except KeyboardInterrupt:
    print("Simulation stopped.")