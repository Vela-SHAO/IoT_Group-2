import sys
import os
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import time

import random
# Maintain reference to ThermalLogic
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ThermalLogic import decide_hvac_status

class OccupancyAnalyzer:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.occupancy_cache = {}
        
        # Load static schedule (still using local file)
        schedule_path = os.path.join(BASE_DIR, "schedule.json")
        with open(schedule_path, 'r', encoding='utf-8') as f:
            self.schedule = json.load(f)

        print(f"[*] Fetching MQTT config from Catalog: {self.catalog_url}")
        try:
            response = requests.get(f"{self.catalog_url}/api/services")
            # Validation: Skip if response is empty or not 200
            if response.status_code == 200 and response.text.strip():
                services = response.json()
                mqtt_service = next((s for s in services if s.get("service_type") == "mqtt"), None)
                
                if mqtt_service:
                    self.broker = mqtt_service["endpoint"]["broker"]
                    self.port = mqtt_service["endpoint"]["broker_port"]
                    self.topic_structure = mqtt_service["endpoint"]["topic_structure"]
                    print(f"[*] Config Loaded from Catalog: {self.broker}:{self.port}")
                    return # Successfully retrieved config, exit init
            
            raise ValueError("MQTT service not found in Catalog response")

        except Exception as e:
            # --- Fallback: Use default config if Catalog fails to provide data ---
            print(f"[!] Warning: Falling back to default config due to: {e}")
            self.broker = "test.mosquitto.org"
            self.port = 1883
            self.topic_structure = "polito/smartcampus/{room_id}/{device_type}/{index_number}"

    def get_dynamic_topic(self, room_id, device_type, index="1"):
        """Generate Topic based on Mya's structure: polito/smartcampus/{room}/{type}/{index}"""
        return self.topic_structure.replace("{room_id}", room_id)\
                                   .replace("{device_type}", device_type)\
                                   .replace("{index_number}", index)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # Subscribe to wifi sensor data for all rooms (for occupancy tracking)
            # Based on Mya's structure, wifi topic is .../{room_id}/wifi/{index}/value
            sub_topic = self.get_dynamic_topic("+", "wifi", "+") + "/value"
            client.subscribe(sub_topic)
            print(f"[*] Success! Subscribed to: {sub_topic}")
        else:
            print(f"[!] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # Parse Topic to get room_id
            parts = msg.topic.split('/')
            room_id = parts[2]
            count = int(msg.payload.decode())
            self.process_analysis(room_id, count)
        except Exception as e:
            print(f"[ERROR] on_message: {e}")

    def process_analysis(self, room_id, count):
        try:
            # 2. Get room meta info (e.g., capacity) from Catalog
            # Mya's Catalog provides filtering via /api/devices?room=R1
            dev_resp = requests.get(f"{self.catalog_url}/api/devices", params={"room": room_id, "type": "temperature"})
            devices = dev_resp.json()
            
           # Default to 30 people if room is not found in Catalog
            capacity = 30
            if devices:

            # 3. Core logic decision
                ac_on = decide_hvac_status(28, count, capacity)
            
            # 4. Generate Analysis Result JSON
            analysis_result = {
                "room_id": room_id,
                "status": "occupied" if count > 0 else "free",
                "hvac_status": "ON" if ac_on else "OFF",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 5. Post back to Catalog to register/update status
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


# For simulation, can be replaced with real data later.
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



# Current schedule is consistent daily. Optimization for weekdays to be added later. Hour:minute matching only.
def read_nonOccupiedScedule(schedule_path)->dict[str,list]:
    with open(schedule_path,"r",encoding="utf-8")as file:
        available_schedule = json.load(file)
        return available_schedule
    
# Determine time slot    
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
# Consider adding weekday filtering later
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

    # 现有房间集合
    existing = set()
    for r in rooms_info:
        rid = r.get("room_id")
        if rid:
            existing.add(rid)

    # 把 snapshot 里出现但不在 setting_config 的房间也加入，给默认 capacity
    if snapshot is not None:
        for rid in snapshot.keys():
            if rid not in existing:
                rooms_info.append({
                    "room_id": rid,
                    "capacity": 30
                })
                existing.add(rid)

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
