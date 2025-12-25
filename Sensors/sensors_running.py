import json
import os
import time
import threading
from devices_sensor import Sensor 



current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
config_path = os.path.join(project_root, "Catalog", "setting_config.json")

print(f"DEBUG: Loading config from: {config_path}")

def load_rooms():
    if not os.path.exists(config_path):
        print(f"Error: Config not found at {config_path}")
        return []
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        rooms = config_data.get("rooms", [])
        return [r.get("room_id") for r in rooms]


def run_sensor(room_id, device_index, device_type):
    freq = 30 if device_type == "temperature" else 10
    sensor = Sensor(room=room_id, index=device_index, catalog_type=device_type, frequency=freq)
    sensor.start()


if __name__ == "__main__":
    room_list = load_rooms()
    target_types = ["temperature", "wifi"]
    threads = []
    

    print(f"[*] Starting sensors for rooms: {room_list}")

    for room in room_list:
        for s_type in target_types:
            
            device_index = 1
            
            t = threading.Thread(
                target=run_sensor, 
                args=(room, device_index, s_type)
            )
            t.daemon = True 
            t.start()
            threads.append(t)
            
            time.sleep(0.2) 
    print(f"[*] System running. Total sensors: {len(threads)}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping all sensors...")
