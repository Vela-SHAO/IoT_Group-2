import json
import time
import threading
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader
from devices_actuator import Acutuator

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
config_path = os.path.join(project_root, "Catalog", "setting_config.json")

print(f"DEBUG: Loading config from: {config_path}")

def load_rooms():
    if not os.path.exists(config_path):
        print(f"Error: Config not found at {config_path}")
        return []
        
    loader = RoomConfigLoader(config_path)
    rooms = loader.get_room_config()
    return rooms


def run_actuator(room_id, device_index, device_type):
    freq = 30 if device_type == "temperature" else 10
    actuator = Acutuator(room=room_id, index=device_index, sensor_type=device_type, frequency=freq)
    actuator.start()


if __name__ == "__main__":
    room_list = load_rooms()
    target_types = ["temperature"]
    threads = []
    

    print(f"[*] Starting actuators for rooms: {room_list}")

    for room in room_list:
        for s_type in target_types:
            
            device_index = 1
            
            t = threading.Thread(
                target=run_actuator, 
                args=(room, device_index, s_type)
            )
            t.daemon = True 
            t.start()
            threads.append(t)
            
            time.sleep(0.2) 
    print(f"[*] System running. Total actuators: {len(threads)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping all actuators...")
