import json
import time
import threading
from datetime import datetime, timezone

import cherrypy
import paho.mqtt.client as mqtt
import copy
import requests
import os, sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, PROJECT_ROOT)

from Catalog.config_loader import RoomConfigLoader


# =========================
# ThingSpeak CONFIG
# =========================
THINGSPEAK_WRITE_API_KEY = "MM0ILXWBZQ7GJ5AM"
THINGSPEAK_URL = "https://api.thingspeak.com/update"


class Controller:
    def __init__(self,
                 mqtt_host,
                 mqtt_port,
                 catalog_host: str = "127.0.0.1",
                 catalog_port: int = 8080,
                 catalog_api_path: str = "/api",
                 config_filename: str = "setting_config.json") -> None:

        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.catalog_base_url = f"http://{catalog_host}:{catalog_port}{catalog_api_path}"

        self.people_value_topic_by_room = {}
        self.temperature_value_topic_by_room = {}
        self.temperature_cmd_topic_by_room = {}

        self.latest_by_room = {}
        
        # 从配置文件加载房间容量
        self.room_capacity = {}
        self.config_loader = RoomConfigLoader(config_filename)
        self._load_room_capacities()

        self.data_lock = threading.Lock()

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        self._decision_thread = None
        self._stop_event = threading.Event()

        # ThingSpeak 限速
        self._thingspeak_last_sent_at = 0.0
        self.THINGSPEAK_MIN_INTERVAL = 16.0
        
        # 轮流发送的房间索引
        self._current_room_index = 0

    def _load_room_capacities(self):
        """从配置文件加载房间容量"""
        try:
            rooms = self.config_loader.get_rooms()
            for room in rooms:
                room_id = room.get("room_id")
                capacity = room.get("capacity", 300)
                if room_id:
                    self.room_capacity[room_id] = capacity
            print(f"[Config] Loaded room capacities: {self.room_capacity}")
        except Exception as e:
            print(f"[Config] Error loading room capacities: {e}")
            # 默认容量
            self.room_capacity = {
                "R1": 300, "R2": 300, "R3": 300, "R4": 300,
                "R1B": 150, "R2B": 150, "R3B": 150, "R4B": 150,
                "RS1": 24, "RS2": 24
            }

    # -------------------------
    # Catalog
    # -------------------------
    def _catalog_get_devices(self, **query_params) -> list:
        try:
            url = f"{self.catalog_base_url}/devices"
            res = requests.get(url, params=query_params, timeout=5)
            res.raise_for_status()
            data = res.json()
            return data if isinstance(data, list) else [data]
        except Exception as e:
            print(f"[Catalog] Error: {e}")
            return []

    def refresh_topics_from_catalog(self):
        devices = self._catalog_get_devices()

        people_map = {}
        temp_val_map = {}

        for dev in devices:
            dev_type = dev.get("type")
            room_id = dev.get("location", {}).get("room")
            mqtt_topics = dev.get("mqtt_topics", {})

            if not room_id:
                continue

            if dev_type == "wifi" and "val" in mqtt_topics:
                people_map[room_id] = mqtt_topics["val"]

            if dev_type == "temperature" and "val" in mqtt_topics:
                temp_val_map[room_id] = mqtt_topics["val"]

        self.people_value_topic_by_room = people_map
        self.temperature_value_topic_by_room = temp_val_map

    # -------------------------
    # MQTT
    # -------------------------
    def _parse_topic(self, topic: str):
        parts = topic.split("/")
        if len(parts) < 4 or parts[-1] != "value":
            return None
        return parts[-4], parts[-3], parts[-2]

    def start_mqtt(self):
        try:
            print(f"[MQTT] Connecting to {self.mqtt_host}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"[MQTT] Error: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"[MQTT] Connected!")
        self.refresh_topics_from_catalog()
        
        for topic in self.people_value_topic_by_room.values():
            client.subscribe(topic)
        for topic in self.temperature_value_topic_by_room.values():
            client.subscribe(topic)

    def _on_mqtt_message(self, client, userdata, msg):
        parsed = self._parse_topic(msg.topic)
        if parsed is None:
            return

        room_id, device_type, index_number = parsed

        try:
            payload_data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return

        with self.data_lock:
            self.latest_by_room.setdefault(room_id, {}) \
                .setdefault(device_type, {})[index_number] = payload_data

    def get_snapshot(self) -> dict:
        with self.data_lock:
            return copy.deepcopy(self.latest_by_room)

    # -------------------------
    # ThingSpeak
    # -------------------------
    def send_to_thingspeak(self, room_data: dict):
        """轮流发送每个房间的数据"""
        now = time.time()
        
        # 限速检查
        time_since_last = now - self._thingspeak_last_sent_at
        if time_since_last < self.THINGSPEAK_MIN_INTERVAL:
            return
        
        if not room_data:
            return
        
        # 获取房间列表
        room_list = sorted(room_data.keys())
        
        if not room_list:
            return
        
        # 获取当前要发送的房间
        current_room = room_list[self._current_room_index % len(room_list)]
        room_info = room_data[current_room]
        
        # 获取该房间的真实容量
        room_capacity = self.room_capacity.get(current_room, 300)
        
        # 获取房间人数
        room_people = 0
        if "wifi" in room_info:
            for device_id, device_data in room_info["wifi"].items():
                people = device_data.get("v", 0)
                room_people += people
        
        # 获取房间温度
        room_temp = None
        if "temperature" in room_info:
            for device_id, device_data in room_info["temperature"].items():
                temp = device_data.get("v")
                if temp is not None and temp > 0:
                    room_temp = temp
                    break
        
        # 如果温度数据无效，跳过
        if room_temp is None:
            print(f"[ThingSpeak] Skipping {current_room} - no temperature data")
            self._current_room_index += 1
            return
        
        # 计算占用率百分比（使用真实容量）
        occupancy_percent = round((room_people / room_capacity) * 100, 1)
        
        # 判断是否可用（80%以下认为可用）
        is_available = 1 if occupancy_percent < 80 else 0
        
        # 房间ID转数字
        room_id_num = self._room_id_to_number(current_room)
        
        # ThingSpeak 字段
        payload = {
            "api_key": THINGSPEAK_WRITE_API_KEY,
            "field1": room_id_num,           # Room ID
            "field2": occupancy_percent,     # Occupancy %
            "field3": room_temp,             # Temperature
            "field4": is_available,          # Availability (0/1)
        }
        
        print(f"[ThingSpeak] Room={current_room} (ID:{room_id_num}), Occupancy={occupancy_percent}% ({room_people}/{room_capacity}), Temp={room_temp}°C, Available={'YES' if is_available else 'NO'}")
        
        try:
            res = requests.post(THINGSPEAK_URL, data=payload, timeout=5)
            
            if res.text.strip() != "0":
                print(f"[ThingSpeak] ✅ Entry: {res.text}")
                self._current_room_index += 1
            else:
                print("[ThingSpeak] ❌ FAILED")
            
            self._thingspeak_last_sent_at = now
            
        except Exception as e:
            print(f"[ThingSpeak] ❌ Error: {e}")
    
    def _room_id_to_number(self, room_id: str) -> int:
        """房间ID转数字"""
        if room_id.startswith("RS"):
            return 100 + int(room_id[2:])
        elif room_id.endswith("B"):
            base_num = int(room_id[1])
            return 10 + base_num
        else:
            return int(room_id[1:])

    # -------------------------
    # Decision Loop
    # -------------------------
    def start_decision_loop(self, interval_seconds: float = 5.0):
        def loop():
            print("[DecisionLoop] Started")
            while not self._stop_event.is_set():
                try:
                    snapshot = self.get_snapshot()
                    
                    if snapshot:
                        self.send_to_thingspeak(snapshot)
                        
                except Exception as e:
                    print(f"[DecisionLoop] Error: {e}")

                time.sleep(interval_seconds)

        self._decision_thread = threading.Thread(target=loop, daemon=True)
        self._decision_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


class RestAPI:
    exposed = True

    def __init__(self, controller: Controller):
        self.controller = controller

    @cherrypy.tools.allow(methods=["GET"])
    def GET(self, *uri, **params):
        cherrypy.response.headers["Content-Type"] = "application/json"
        snapshot = self.controller.get_snapshot()
        return json.dumps({
            "status": "Controller running",
            "data": snapshot
        }).encode("utf-8")


def main():
    print("=" * 60)
    print("ThingSpeak Controller - Student Dashboard")
    print("=" * 60)
    
    controller = Controller(
        mqtt_host="test.mosquitto.org",
        mqtt_port=1883,
        catalog_host="127.0.0.1",
        catalog_port=8080,
        catalog_api_path="/api",
        config_filename="setting_config.json"
    )

    controller.start_mqtt()
    controller.start_decision_loop(interval_seconds=5)

    cherrypy.tree.mount(RestAPI(controller), "/", {
        "/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}
    })
    cherrypy.config.update({"server.socket_port": 18080})
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
    except Exception as e:
        print(f"[Main] Fatal error: {e}")
        import traceback
        traceback.print_exc()