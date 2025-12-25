import time
import json
from devices_base import GenericDevice


class Acutuator(GenericDevice):
    def __init__(self, room, index, sensor_type, frequency):
        super().__init__(room, index, sensor_type, "actuator", frequency)
        self.room = room
        self.topics = {
            "cmd": self.base_topic + "/cmd"
        }
        self.frequency = frequency
    def notify(self, topic, payload):
        print(f"[!] Message received on {topic}")
        try:
            command = json.loads(payload)

            if "status" in command:
                sensor_status = command["status"]
                if sensor_status.upper() == "ON":
                    print(f"[+]Room {self.room} Air conditioner turned ON")
                else:
                    print(f"[-]Room {self.room} Air conditioner turned OFF")

            if "target_temp" in command:
                temp_value = command["target_temp"]
                print(f"[+]Room {self.room} Setting target temperature to {temp_value}°C")
                
            if "mode" in command:
                mode_value = command["mode"]
                print(f"[+]Room {self.room} Setting mode to {mode_value}")
            
        except json.JSONDecodeError:

            print(f">>> Unvalid: {payload}")


    def start(self):

        if not self.register_to_catalog(self.topics):
            return

        client = self.connect_mqtt()

        def on_message(client, userdata, msg):
            self.notify(msg.topic, msg.payload.decode())

        client.on_message = on_message

        target_topic = self.topics['cmd']
        client.subscribe(target_topic)

        print(f"[*] Actuator started. Listening on: {self.topics['cmd']}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            print("Actuator Stopped")
