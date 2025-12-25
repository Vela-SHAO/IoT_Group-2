import time
import json
import random
from devices_base import GenericDevice

# ==========================================
# 子类 1: Sensor (传感器)
# 职责：注册 -> 连接 -> 循环生成数据 -> 发布
# ==========================================
class Sensor(GenericDevice):
    def __init__(self, room, index, sensor_type, frequency):

        super().__init__(room, index, sensor_type, "sensor", frequency)
        self.topics = {"val": self.base_topic + "/value"}

    def start(self):

        if not self.register_to_catalog(self.topics):
            return False

        client = self.connect_mqtt()

        print(f"[*] Sensor started. Publishing to: {self.topics['val']}")


        try:
            while True:
                # 待修改：生成模拟数据
                if self.sensor_type == "temperature":
                    value = round(random.uniform(20.0, 30.0), 2)
                # 待修改：生成模拟数据
                else:
                    value = random.randint(0, 100)


                payload = {
                    "id": self.device_id,
                    "v": value,
                    "u": "C" if self.sensor_type == "temperature" else "%",
                    "t": time.time()
                }

                client.publish(self.topics['val'], json.dumps(payload))
                print(f"--> Sent: {payload}")

                time.sleep(self.frequency)

        except KeyboardInterrupt:
            client.loop_stop()
            print("Sensor Stopped")



if __name__ == "__main__":
    room = "R1"
    index = 1
    sensor_type = "temperature"
    frequency = 30
    sensor = Sensor(room, index, sensor_type, frequency)
    sensor.start()

