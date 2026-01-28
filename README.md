# IoT_Group-2
1. Project structure:
========
├── Catalog/                  # Catalog
│   ├── Catalog_manage.py     # Main script, for managing device registration and service discovery
│   ├── config_loader.py      # Utility class: responsible for reading JSON configuration files
│   └── catalog_script.json   # [Database] Persistent storage of registered device list
│
└── Sensors/                  # [Device side] Simulator module
|   ├── devices_base.py       # [Core parent class] Defines common behavior for all devices (GenericDevice)
|   ├── devices_sensor.py     # [Subclass] Sensor logic (temperature, Wifi), includes data generation algorithms
|   ├── devices_actuator.py   # [Subclass] Actuator logic (AC switch), responsible for listening to commands and publishing status
|   ├── sensors_running.py    # [Startup script] Multithreaded launch of sensors for the entire building
|   └── actuators_running.py  # [Startup script] Multithreaded launch of actuators for the entire building
|
└── Add/Delete/               # [Add of delete side] Simulator module
│   ├── actuator_add.py       # add actuator
│   ├── device_delete.py      # delete device
│   └── sensor_add.py         # add sensor
│   └── wifi_sensor_add.py.   # add wifi sensor when new device is running
|
└── Controller/               # [Intelligence side] Data process of the system,
|    ├── OccupancyAnalyzer.py  # Main analyzer: Make decision by the 'snapshot' from Controller
|    └── Controller.py         # subscribe '/value' ,upadate'snapshot' and periodly publish '/cmd'
|
└── Dashboard/               # Dashboard
│   ├── student_dashboard.py      # Dashboard for student usage(read-only)
│   ├── Manager_dashboard.py      # Dashboard for manager usage(with control capabilities)
|
|—— ├── setting_config.json   # All the MQTT and HTTP setting info, the basic room info
|——	├── schedule.json         # Room occupied schedule
|


3. HOW TO RUN 
Strict Order Required: Catalog → Sensors → Actuators.

    1. Start Catalog (Infrastructure)
        Must run first to enable Service Discovery.

        python Catalog/Catalog_manage.py
        Verify: Check http://127.0.0.1:8080.

    2. Start Sensors (Data Publishers)
        Opens a new terminal.
        python Sensors/sensors_running.py
        Behavior: Devices auto-register and immediately start streaming data (--> Sent logs).

    3. Start Actuators (Command Listeners)
        Opens a new terminal.
        python Sensors/actuators_running.py
        Behavior: Devices auto-register, publish initial status, and enter listening mode ([*] Controller started...) to await /cmd.
	
    4. Start Controller
        Opens a new terminal.
        python Controller\Controller.py
        Behavior: MQTT connect successfully, Catalog topics loaded / refresh， decision loop.
       
    6. Start Dashboard
       Opens a new terminal.
       python Dashboard/student_dashboard.py
       python Dashboard/Manager_dashboard.py
       Behavior: Automatically displays all registered rooms status and managers are able to command back to actuators

    
    8. Dynamic Management
        Run CLI tools to add/remove devices at runtime without restarting the system.

        python Add/Delete/sensor_add.py
        # or python Add/Delete/actuator_add.py
        # or python Add/Delete/wifi_sensor_add.py
        # or python Add/Delete/device_delete.py

        Usage: Follow the prompts (Room/Type/Role/Index). Press Enter to use wildcards.
        Effect: Instantly updates the Catalog Registry and Controller logic.

4. System Explanation
Our architecture follows the LinkSmart style / pattern, adopting a three-step model: "Bootstrapping -> Discovery -> Operation".

    1. Bootstrapping: Devices boot using only the local setting_config.json to find the Catalog URL.

    2. Service Discovery: Devices query the Catalog (GET /api/services) to retrieve the MQTT Broker address and Topic Template.

    3. Registration: Devices auto-fill the topic template (e.g., polito/R1/temp/1) and register metadata via POST.

    4. Operation:

        Sensors: Connect to MQTT and publish data periodically.

        Actuators: Subscribe to .../cmd for control and publish to .../status for feedback.
   

5. Logic & Simulation
    1. Sensor Algorithms:

        Wi-Fi (People Count): Uses a Random Walk algorithm (previous value ± random fluctuation) constrained by room capacity to simulate realistic crowd flow.

        Temperature: Calculated as Seasonal Base + Heat Effect (driven by current people count).

    2. Multi-threading: sensors_running.py and actuators_running.py spawn concurrent threads for each room to simulate a distributed environment.

    3. Dynamic Management: We provide a CLI tool to dynamically add or delete devices (by room, type, role, index) during runtime, instantly updating the Registry and Controller logic.



6. Dashboard (Front-end)

    5.1 Dashboard Design Goals
    The dashboard is designed with the following goals:
    No hard-coded rooms
    No hard-coded sensors or actuators
    Automatic discovery of newly registered devices via the Catalog or Controller

    While the dashboard is running:
        •	Newly registered sensors or actuators
        •	Newly appearing rooms
    will be displayed automatically without any front-end code changes.

    5.2 Data Source Strategy
    The dashboard does not subscribe to MQTT directly.
    Instead, it retrieves system state through HTTP APIs.


7. Notes / Troubleshooting
    1.  Dynamic registration boundary (Catalog vs MQTT data)
        Dynamic Management updates Catalog registry immediately.
        A newly registered room/device will not produce /value data unless the corresponding sensor simulator (or real device) is running.
        Controller can only build snapshot from received /value messages.

    2. Controller pipeline validation (logs):
        ✅ Accepted ... Room X: device metadata loaded from Catalog
        [MQTT] RX topic=.../X/.../value: Controller is receiving sensor data for room X
        [CMD] publish -> .../X/.../cmd: Controller has published a command for room X

    3. Index support:
        Snapshot stores values per room_id / device_type / index.
        AC decision is currently produced per room and published to a room-level cmd topic (one command channel per room in current version).
