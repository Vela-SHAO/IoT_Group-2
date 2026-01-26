import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..", "Sensors")))
from Sensors.devices_actuator import Acutuator

def actuator_demo():
    room_name = str(input("Enter room name (e.g., R1): ")).strip()
    actuator_index = int(input("Enter actuator index (e.g., 1): ").strip())
    actuator_type = str(input("Enter actuator type t (for temperature) or w for wifi: ")).strip()

    if actuator_type == 't':
        actuator_type = "temperature"
    elif actuator_type == 'w':
        actuator_type = "wifi"
    else:
        print("Invalid actuator type. Please enter 't' for temperature or 'w' for wifi.")
        return
  
    actuator = Acutuator(room=room_name, index=actuator_index, sensor_type=actuator_type)
    actuator.start()

if __name__ == "__main__":
    actuator_demo()