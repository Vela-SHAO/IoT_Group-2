import json
import time 
import threading
from datetime import datetime, timezone

import cherrypy
import paho.mqtt.client as mqtt
import os,sys
import copy


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, PROJECT_ROOT)

import OccupancyAnalyzer

import requests


class Controller:
    def __init__(self,
                 mqtt_host,
                 mqtt_port,
                 catalog_host: str = "127.0.0.1",
                 catalog_port: int = 8080,
                 catalog_api_path: str = "/api") -> None:
        # ==========================================
        # 这里base_topic_prefix后续似乎没有用到？需要保留吗 -- Mya
        # ==========================================
        self.base_topic_prefix = "polito/smartcampus"

        self.mqtt_host =mqtt_host
        self.mqtt_port = mqtt_port
        self.catalog_base_url = f"http://{catalog_host}:{catalog_port}{catalog_api_path}"
        self.people_value_topic_by_room = {}
        self.temperature_value_topic_by_room = {}
        self.temperature_cmd_topic_by_room = {}
        # self.people_topic = people_topic
        # self.temperature_topic = temperature_topic
        self.latest_people_by_room ={}
        self.latest_temperature_by_room = {}
        self.latest_by_room = {}

        self.ac_state_by_room = {
        # room_id: {
        #     "should_on": None,            # latest decision（True/False/None）
        #     "decided_at": None,           # latest decision time
        #     "actual_on": None,            # real actual(None)
        #     "actual_reported_at": None,   # real actual time
        #     "last_cmd_sent_on": None,     
        #     "last_cmd_sent_at": None      
        # }
        }


        self.latest_people_received_at = None
        self.latest_temperature_received_at = None


        self.data_lock = threading.Lock()

        self.mqtt_client = mqtt.Client()

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        self._decision_thread = None
        self._stop_event = threading.Event()


    def _catalog_get_devices(self, **query_params) -> list:
        """
        GET {catalog_base_url}/devices?...
        返回 devices 列表（JSON）
        """
        url = f"{self.catalog_base_url}/devices"
        res = requests.get(url, params=query_params, timeout=5)
        res.raise_for_status()
        data = res.json()
        if isinstance(data, list):
            return data
        # 如果对方返回单个 dict（按 id 查），这里也兜底成 list
        return [data]

    def refresh_topics_from_catalog(self):
        """
        从 Catalog 建三张表：
        - wifi sensors: mqtt_topics["val"] 作为 people 订阅 topic
        - temperature sensors: mqtt_topics["val"] 作为 temperature 订阅 topic
        - temperature actuators: mqtt_topics["cmd"] 作为 cmd 发布 topic
        """
        devices = self._catalog_get_devices()  
        

        people_map = {}
        temp_val_map = {}
        temp_cmd_map = {}

        for dev in devices:
            dev_type = dev.get("type")
            dev_id = dev.get("id", "")
            room_id = dev.get("location", {}).get("room")
            mqtt_topics = dev.get("mqtt_topics", {})

            if not room_id:
                continue

            # wifi sensor -> people value topic
            if dev_type == "wifi" and "val" in mqtt_topics:
                people_map[room_id] = mqtt_topics["val"]

            # temperature sensor -> temperature value topic
            if dev_type == "temperature" and dev_id.endswith("_sensor_1") and "val" in mqtt_topics:
                temp_val_map[room_id] = mqtt_topics["val"]

            # temperature actuator -> cmd topic
            if dev_type == "temperature" and dev_id.endswith("_actuator_1") and "cmd" in mqtt_topics:
                temp_cmd_map[room_id] = mqtt_topics["cmd"]

        self.people_value_topic_by_room = people_map
        self.temperature_value_topic_by_room = temp_val_map
        self.temperature_cmd_topic_by_room = temp_cmd_map

        print("[Catalog] topics loaded:")
        print("  wifi(value) rooms:", sorted(self.people_value_topic_by_room.keys()))
        print("  temp(value) rooms:", sorted(self.temperature_value_topic_by_room.keys()))
        print("  temp(cmd)   rooms:", sorted(self.temperature_cmd_topic_by_room.keys()))

    def _parse_topic(self, topic: str):
            """
            topic 格式：{base_topic_prefix}/{room_id}/{device_type}/{index_number}
            返回 (room_id, device_type, index_number)，解析失败返回 None
            """
            parts = topic.split("/")
            if len(parts) < 4:
                return None

            room_id = parts[-4]
            device_type = parts[-3]
            index_number = parts[-2]
            tail = parts[-1]

            if tail != "value":
                return None

            return room_id, device_type, index_number



    def start_mqtt(self):
        print("MQTT connecting to", self.mqtt_host, self.mqtt_port)

        self.mqtt_client.connect(self.mqtt_host,self.mqtt_port,keepalive=60)
        self.mqtt_client.loop_start()

    def _on_mqtt_connect(self,client,userdata,flags,reason_code,properties=None):
        '''subscribe topics after connecting'''
        try:
            self.refresh_topics_from_catalog()
        except Exception as e:
            print(f"[Catalog] refresh_topics_from_catalog failed: {e}")
            # 刷新失败就不订阅，避免订阅错 topic
            return

        # 订阅 wifi(value) 和 temperature(value)
        for room_id, topic in self.people_value_topic_by_room.items():
            client.subscribe(topic)
        for room_id, topic in self.temperature_value_topic_by_room.items():
            client.subscribe(topic)

        #print("[MQTT] subscribed to wifi/value and temperature/value topics from Catalog")

    def _on_mqtt_message(self,client,userdata,msg):
        parsed = self._parse_topic(msg.topic)


        if parsed is None:
            return
        room_id,device_type, index_number =parsed
        #print(f"[MQTT] parsed room_id type={type(room_id)} value={room_id}")
        try :
            payload_text =msg.payload.decode("utf-8")
            payload_data = json.loads(payload_text)
            # print(f"[MQTT] {msg.topic} -> {payload_data}")
        except Exception:
            return
        
        sensor_id = payload_data.get("id")
        value = payload_data.get("v")
        unit = payload_data.get("u")
        sensor_timestamp = payload_data.get("t")
        
        received_at = time.time()

        with self.data_lock:
            room_bucket = self.latest_by_room.setdefault(room_id,{})
            type_bucket = room_bucket.setdefault(device_type,{})
            type_bucket[index_number]={
                "sensor_id": sensor_id,
                "value": value,
                "unit": unit,
                "sensor_timestamp": sensor_timestamp,
                "received_at": received_at
            }

    def get_snapshot(self) -> dict:
        """Return a deep copy of latest data snapshot."""
        with self.data_lock:
            return copy.deepcopy(self.latest_by_room)
    
    def send_ac_cmd(self,room_id,should_on:bool,
                    
                    mode=None
                    ):
        topic = self.temperature_cmd_topic_by_room.get(room_id)
        if not topic:
            print(f"[CMD] No actuator cmd topic for room {room_id}. Did Catalog register actuator?")
            return False
        payload ={"status": "ON" if should_on else "OFF"}
        if mode is not None:
            payload["mode"] = mode

        payload_text = json.dumps(payload, ensure_ascii=False)
        self.mqtt_client.publish(topic, payload_text)
        print(f"[CMD] publish -> {topic} : {payload_text}")
        return True
        
    
    def ensure_ac_state(self,ac_state_by_room: dict, room_id: str) -> dict:
        """
        确保 ac_state_by_room[room_id] 存在；不存在就创建默认结构并返回。
        """
        state = ac_state_by_room.get(room_id)
        if state is None:
            state = {
                "should_on": None,
                "decided_at": None,
                "actual_on": None,
                "actual_reported_at": None,
                "last_cmd_sent_on": None,
                "last_cmd_sent_at": None
            }
            ac_state_by_room[room_id] = state
        return state
    

    def should_send_cmd(self,decided_at,room_state: dict)->bool:
        last_sent_at = room_state.get("last_cmd_sent_at")
        last_decision = room_state["last_cmd_sent_on"]
        should_on = room_state.get("should_on")
        MIN_INTERVAL = 30
        if last_sent_at is None:
            return True
        if last_decision == should_on or should_on is None:
            return False
        return(decided_at-last_sent_at)>=MIN_INTERVAL

    def apply_ac_decisions(self,ac_decision_by_room: dict, ac_state_by_room: dict):  
        """
        ac_decision_by_room:
        {room_id: {"decide": True/False/None, "decide_time": float}}
        """
        for room_id, decision in ac_decision_by_room.items():
            #print("[DEBUG decision keys]", room_id, list(decision.keys()))

            state = self.ensure_ac_state(ac_state_by_room, room_id)

            should_on = decision.get("decide", decision.get("should_on"))
            decided_at = decision.get("decide_time")

            if should_on is None  or decided_at is None:
                continue

            state["should_on"] = should_on
            state["decided_at"] = decided_at
            
            if not self.should_send_cmd(decided_at,state):
                continue
            
            last_sent_on = state.get("last_cmd_sent_on")

            #send_cmd
            self.send_ac_cmd(room_id,should_on)
                

            state["last_cmd_sent_on"] = should_on
            state["last_cmd_sent_at"] = decided_at
            print(f"{room_id} HVAC open {state['last_cmd_sent_on']} at {datetime.fromtimestamp(state['last_cmd_sent_at'])}")

    def start_decision_loop(self, interval_seconds: float = 5.0):
        """
        每隔 interval_seconds:
        - 取一次 snapshot
        - 交给 OccupancyAnalyzer 算“是否建议开空调”
        - 调用 apply_ac_decisions -> 触发 publish cmd
        """
        if self._decision_thread is not None:
            return  # 防止重复启动

        def loop():
            while not self._stop_event.is_set():
                try:
                    request_timestamp = datetime.now(timezone.utc).timestamp()
                    snapshot = self.get_snapshot()
                    ac_decision_by_room = OccupancyAnalyzer.deciede_ac_from_room_info(request_timestamp,snapshot)
                    self.apply_ac_decisions(ac_decision_by_room, self.ac_state_by_room)
                    print("[cmd]in the loop")
                except Exception as e:
                    import traceback
                    print(f"[DecisionLoop] error: {e}")
                    traceback.print_exc()

                time.sleep(interval_seconds)

        self._decision_thread = threading.Thread(target=loop, daemon=True)
        self._decision_thread.start()
    
    def stop(self):
        self._stop_event.set()








class RestAPI:
    exposed = True

    def __init__(self,controller:Controller) :
        self.controller = controller

    @cherrypy.tools.allow(methods=["GET"])
    def GET(self,*uri, **params):
        request_timestamp = datetime.now(timezone.utc).timestamp()

        snapshot = self.controller.get_snapshot()

        if len(uri) >= 2 and uri[0] == "debug" and uri[1] == "cache":
            snapshot = self.controller.get_snapshot()
            cherrypy.response.headers["Content-Type"] = "application/json; charset=utf-8"
            return json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
        

        #之后把数据处理的参数改为2个，snapshot和request_timestamp
        result_list = OccupancyAnalyzer.get_student_dashboard_response(request_timestamp,snapshot)

        cherrypy.response.headers["Content-Type"] = "application/json; charset=utf-8"

        return json.dumps(result_list,ensure_ascii=False).encode("utf-8")
    
    
def main():
    # ==========================================
    # 这里建议不用硬编码 localhost 和端口，改成从环境变量读，方便部署和测试 -- Mya
    # ==========================================
    controller = Controller(
        mqtt_host="test.mosquitto.org",
        mqtt_port=1883,
        catalog_host="127.0.0.1",
        catalog_port=8080,
        catalog_api_path="/api"
    )

    controller.start_mqtt()
    controller.start_decision_loop(interval_seconds=5)


    config={
        "/":{
            "request.dispatch":cherrypy.dispatch.MethodDispatcher(),
            "tools.response_headers.on":True,
        }
    }

    cherrypy.tree.mount(RestAPI(controller),"/",config)
    cherrypy.config.update({
        "server.socket_host":"0.0.0.0",
        "server.socket_port":18080
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
    # while True:
    #     time.sleep(1)



if __name__ == "__main__":
    main()