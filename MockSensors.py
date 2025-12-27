import paho.mqtt.client as mqtt
import time
import random

BROKER = "test.mosquitto.org" # 统一使用 test.mosquitto.org
PORT = 1883
ROOMS = ["R1", "R1B", "R2", "R2B", "RS1", "RS2"]

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

print("--- IoT Mock Sensor: Sending Data to Mya's Topic Structure ---")

while True:
    room = random.choice(ROOMS)
    occupancy = random.randint(0, 150)
    
    # 必须是这个精确的 Topic
    topic = f"polito/smartcampus/{room}/wifi/1/value"
    client.publish(topic, str(occupancy))
    
    print(f">>> Sent to {topic}: {occupancy} students")
    time.sleep(5)