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



class Controller:
    def __init__(self,mqtt_host,mqtt_port,
                 people_topic,temperature_topic) -> None:
        self.base_topic_prefix = "polito/smartcampus"

        self.mqtt_host =mqtt_host
        self.mqtt_port = mqtt_port
        self.people_topic = people_topic
        self.temperature_topic = temperature_topic
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

    def _parse_topic(self, topic: str):
            """
            topic 格式：{base_topic_prefix}/{room_id}/{device_type}/{index_number}
            返回 (room_id, device_type, index_number)，解析失败返回 None
            """
            topic_parts = topic.split("/")
            base_parts = self.base_topic_prefix.split("/")

            if len(topic_parts) != len(base_parts)+4:
                return None
            if topic_parts[:len(base_parts)]!= base_parts:
                return None
            room_id = topic_parts[len(base_parts)]
            device_type= topic_parts[len(base_parts)+1]
            index_number = topic_parts[len(base_parts)+2]
            tail = topic_parts[len(base_parts) + 3]
            if tail != "value":
                return None
            return room_id,device_type,index_number



    def start_mqtt(self):
        print("MQTT connecting to", self.mqtt_host, self.mqtt_port)

        self.mqtt_client.connect(self.mqtt_host,self.mqtt_port,keepalive=60)
        self.mqtt_client.loop_start()

    def _on_mqtt_connect(self,client,userdata,flags,reason_code,properties=None):
        '''subscribe topics after connecting'''
        client.subscribe(self.people_topic)
        client.subscribe(self.temperature_topic)

    def _on_mqtt_message(self,client,userdata,msg):
        parsed = self._parse_topic(msg.topic)


        if parsed is None:
            return
        room_id,device_type, index_number =parsed
        print(f"[MQTT] parsed room_id type={type(room_id)} value={room_id}")
        try :
            payload_text =msg.payload.decode("utf-8")
            payload_data = json.loads(payload_text)
            print(f"[MQTT] {msg.topic} -> {payload_data}")
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
    controller = Controller(
        mqtt_host="test.mosquitto.org",
        mqtt_port=1883,
        people_topic="polito/smartcampus/+/+/+/value",
        temperature_topic="polito/smartcampus/+/+/+/value",


    )

    controller.start_mqtt()

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
    # cherrypy.engine.start()
    # cherrypy.engine.block()
    while True:
        time.sleep(1)



if __name__ == "__main__":
    main()