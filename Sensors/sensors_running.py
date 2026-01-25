import json
import time
import threading
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader
from devices_sensor import Sensor 


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)


config_filename = "setting_config.json"

possible_paths = [
            os.path.join(project_root, config_filename),  
            os.path.join(current_dir, config_filename),   
            config_filename                               
        ]

config_path = None

for path in possible_paths:
    if os.path.exists(path):
        config_path = path
        break
        
if config_path is None:
    config_path = os.path.join(project_root, config_filename)

loader = RoomConfigLoader(config_path)


def load_rooms():
    if not os.path.exists(config_path):
        print(f"Error: Config not found at {config_path}")
        return []
    
    rooms = loader.get_room_config()
    return rooms


def run_sensor(room_id, device_index, device_type):
    freq = 5
    sensor = Sensor(room=room_id, index=device_index, sensor_type=device_type, frequency=freq, loader_instance=loader)
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
