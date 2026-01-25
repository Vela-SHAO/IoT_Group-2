import time
import json
from devices_base import GenericDevice


class Acutuator(GenericDevice):
    def __init__(self, room, index, sensor_type, frequency=None):
        if frequency is None:
            frequency = 5
        super().__init__(room, index, sensor_type, "actuator", frequency)
        self.room = room
        self.topics = {
            "cmd": self.base_topic + "/cmd",
            "status": self.base_topic + "/status"
        }
        self.frequency = frequency

        self.current_states = {
            "status": "OFF",
            "target_temp": 26,
            "mode": "comfort"
        }
    def notify(self, topic, payload, client):
        print(f"[!] Message received on {topic}")
        try:
            command = json.loads(payload)
            status_changed = False

            if "status" in command:
                new_status = command["status"]
                self.current_states["status"] = new_status
                status_changed = True
                if new_status.upper() == "ON":
                    print(f"[+]Room {self.room} Air conditioner turned ON")
                else:
                    print(f"[-]Room {self.room} Air conditioner turned OFF")

            if "target_temp" in command:
                self.current_states["target_temp"] = command["target_temp"]
                status_changed = True
                print(f"[+]Room {self.room} Setting target temperature to {self.current_states['target_temp']}°C")
                
            if "mode" in command:
                self.current_states["mode"] = command["mode"]
                status_changed = True
                print(f"[+]Room {self.room} Setting mode to {self.current_states['mode']}")
            
            if status_changed:
                self.publish_status(client)
            
        except json.JSONDecodeError:

            print(f">>> Unvalid: {payload}")
    def publish_status(self, client):

        payload = json.dumps(self.current_states)
        client.publish(self.topics["status"], payload, retain=True)
        print(f"[>] Feedback sent to {self.topics['status']}: {payload}")

    def start(self):

        if not self.register_to_catalog(self.topics):
            return

        client = self.connect_mqtt()

        def on_message(client, userdata, msg):
            self.notify(msg.topic, msg.payload.decode(),client)

        client.on_message = on_message

        target_topic = self.topics['cmd']
        client.subscribe(target_topic)

        print(f"[*] Actuator started. Listening on: {self.topics['cmd']}")

        self.publish_status(self.client)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            print("Actuator Stopped")
