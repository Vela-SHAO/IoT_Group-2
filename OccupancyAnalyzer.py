import sys
import os
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import time

import random
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

# if __name__ == "__main__":
#     # 传入 Catalog 的地址
#     analyzer = OccupancyAnalyzer("http://127.0.0.1:8080")
#     analyzer.start()
        






#模拟用，之后可以替换成真实数据。
class simulate:
    def simu_people(capacity,isAvailavle:bool)-> int:

        if isAvailavle:            
            current_people = random.randint(0,int(capacity/3))
            return current_people
        else:
            current_people = random.randint(int(capacity/3),int(1.2*capacity))
            return current_people
        
    def simu_temperature(month)-> float:

        if month in [5,6,7,8]:
            temperature = round(random.uniform(15,29),1)
            return temperature
        else:
            temperature = round(random.uniform(10,25),1)
            return temperature



#现在课表是每天一致的。后期再优化周几的问题吧。目前只做小时：分钟的匹配。
def read_nonOccupiedScedule(schedule_path)->dict[str,list]:
    with open(schedule_path,"r",encoding="utf-8")as file:
        available_schedule = json.load(file)
        return available_schedule
    
#计算落在哪个时间段    
def match_slot(hour:int, minute:int,slot_count)->int|None:
    start = 8*60 +30 #slot1 start 8:30
    end = 19*60 #slot 7 end at 19:00
    slot_length =90 
    askingTime = hour* 60 +minute
    if askingTime <start or askingTime >end:
        return None
    
    slot_index =((askingTime-start)/slot_length)+1
    if slot_index > slot_count :
        return None
    return slot_index

#translate timestamp into dict
def parse_timestamp(timestamp)->dict:
    dt = datetime.fromtimestamp(timestamp,tz=timezone.utc)
    month = dt.month
    weekday = dt.strftime("%A")

    hour = dt.hour
    minute = dt.minute
    return {
        "month":month,
        "weekday":weekday,
        "hour":hour,
        "minute":minute
    }

#get non occupied room from json 
#后续可以考虑是否加入weekday
def get_available_room(request_hour,request_minute,schedule_path)->list:


    available_schedule = read_nonOccupiedScedule(schedule_path)
    slot_count = len(available_schedule)
    slot_index = match_slot(request_hour,request_minute,slot_count)

    available_rooms_list=available_schedule.get(str(slot_index),[])
    return available_rooms_list

#read setting_config
def get_room_info(path)->list[dict]:
    with open(path,"r",encoding="utf-8")as file:
        data = json.load(file)
        rooms_info = data["rooms"]
        return rooms_info

def pick_latest_value(snapshot:dict,room_id:str,device_type:str):
    ''' snapshot structure:
    [room_id][device_type][index_number] = {"value":..., "received_at":...}
    return value dict or None'''
    room_bucket =snapshot.get(room_id)
    if not room_bucket:
        return None
    type_bucket = room_bucket.get(device_type)
    if not type_bucket:
        return None
    latest_item = None
    latest_received_at = -1
    for _, item in type_bucket.items():
        received_at = item.get("received_at",-1)
        if received_at > latest_received_at:
            latest_received_at = received_at
            latest_item = item

    if latest_item is None:
        return None
    
    return latest_item.get("value")

def fill_from_snapshot_or_simulate(
        room:dict,request_month,available_rooms_list,snapshot: dict | None):
    room_id = room["room_id"]
    is_available = room_id in available_rooms_list
    room["available"] = is_available


    temperature_value = None
    if snapshot is not None:
        temperature_value = pick_latest_value(snapshot, room_id, "temperature")

    # if temperature_value is None:
        # temperature_value = simulate.simu_temperature(request_month)

    room["temperature"] = temperature_value


    people_value = None
    if snapshot is not None:
        people_value = pick_latest_value(snapshot, room_id, "wifi")

    # if people_value is None:
    #     people_value = simulate.simu_people(room["capacity"], is_available)

    room["students"] = people_value

def get_student_dashboard_response(timestamp,snapshot = None):
    dt = parse_timestamp(timestamp)
    request_weekday = dt["weekday"]  
    request_hour = dt["hour"]
    request_minute = dt["minute"]
    request_month = dt["month"]

    schedule_path = "schedule.json"
    available_rooms_list=get_available_room(request_hour,request_minute,schedule_path)

    room_info_path ="setting_config.json"
    rooms_info= get_room_info(room_info_path)
    random.seed(42)
    for room in rooms_info:
        fill_from_snapshot_or_simulate(room, request_month, available_rooms_list, snapshot)

    return rooms_info

def deciede_ac_from_room_info(request_timestamp,snapshot)->dict[str,dict[str,object]]:
    ac_decided ={
        #room_id:{
            #decied:bool,
            #decied_time:timestamp
        #}
    }
    rooms_info = get_student_dashboard_response(request_timestamp,snapshot)
    dt = parse_timestamp(request_timestamp)
    month = dt["month"]
    decided_time =datetime.now(timezone.utc).timestamp()
    for room_state in rooms_info:
        room_id = room_state.get("room_id")
        temperature = room_state.get("temperature")
        students = room_state.get("students")#people_value current in the classroom
        capacity = room_state.get("capacity")

        ac_decision = decied_ac(temperature,students,capacity,month)
        ac_decided[room_id] = {
                "should_on": ac_decision,
                "decide_time": decided_time
            }

        if ac_decision is not None:
            print(f"[AC Decider]{room_id}:open is {ac_decided[room_id]['should_on']},people:{students},temperature:{temperature}")
    return ac_decided


    
  
def get_mode(month)->str:
    if month in[5,6,7,8]:
        return "Cool"
    elif month in [11,12,1,2,3,4]:
        return"Heat"
    else:
        return "OFF"
    

def decied_ac(temperature,people,capacity,month)-> bool:
    summer_lower =24
    summer_upper =26
    winter_lower = 20
    winter_upper = 22
    occupancy_threshold =0.6 
    season ={
        "summer":[5,6,7,8],
        "winter":[11,12,1,2,3,4],
        "transition":[9,10]
    }



    if temperature is None or people is None or capacity is None or capacity <= 0:
        return None
    if people == 0:
        return False 
    occupancy_ratio = people / capacity
    high = occupancy_ratio > occupancy_threshold

    mode = get_mode(month)
    if mode == "OFF":
        return None
    
    if mode == "Cool":
        on_threshold = summer_upper -1 if high else summer_upper
        off_threshold = summer_upper -2 if high else summer_lower

        if temperature>= on_threshold:
             return True
        
        if temperature<=off_threshold:
            return False
        return None
    
    if mode =="Heat":
        on_threshold = winter_lower +1 if high else winter_lower
        off_threshold = winter_lower +2 if high else winter_upper

        if temperature<= on_threshold:
            return True
        if temperature>= off_threshold:
            return False
        return None






if __name__==  "__main__":
    timestamp=1735635600 #wed 10:20
    room_info =get_student_dashboard_response(timestamp)
    print(room_info)