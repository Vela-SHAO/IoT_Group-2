import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "..", "Sensors")))

from Sensors.devices_sensor import Sensor

def sensor_demo():
    room_name = str(input("Enter room name (e.g., R1): ")).strip()
    sensor_index = int(input("Enter sensor index (e.g., 1): ").strip())
    sensor_type = str(input("Enter sensor type t (for temperature) or w for wifi: ")).strip()

    if sensor_type == 't':
        sensor_type = "temperature"
    elif sensor_type == 'w':
        sensor_type = "wifi"
    else:
        print("Invalid sensor type. Please enter 't' for temperature or 'w' for wifi.")
        return

    sensor = Sensor(room=room_name, index=sensor_index, sensor_type=sensor_type)
    sensor.start()

if __name__ == "__main__":
    sensor_demo()