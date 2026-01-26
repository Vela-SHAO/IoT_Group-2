import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..", "Sensors")))

from Sensors.devices_base import GenericDevice

def device_delete():
    print("\n=== Device Deletion Tool ===")
    print("Tip: Press [Enter] to skip any field.\n")
    
    room_name = input("Enter room name (e.g., R1): ").strip()
    room_name = room_name if room_name else "unknown"

    device_index = input("Enter device index (e.g., 1): ").strip()
    if device_index.isdigit():
        device_index = int(device_index)
    else:
        device_index = None

    device_type = input("Enter device type t (for temperature) or w (for wifi): ").strip()
    if device_type == 't':
        device_type = "temperature"
    elif device_type == 'w':
        device_type = "wifi"
    elif device_type == '':
        device_type = "unknown"
    else:
        print("Invalid device type. Please enter 't' for temperature or 'w' for wifi.")
        return

    device_role = input("Enter device role s (for sensor) or a (for actuator): ").strip()
    if device_role == 's':
        device_role = "sensor"
    elif device_role == 'a':
        device_role = "actuator"
    elif device_role == '':
        device_role = "unknown"
    else:
        print("Invalid device role. Please enter 's' for sensor or 'a' for actuator.")
        return

    sensor = GenericDevice(room=room_name, index=device_index, sensor_type=device_type, role=device_role)
    sensor.delete_from_catalog()

if __name__ == "__main__":
    device_delete()