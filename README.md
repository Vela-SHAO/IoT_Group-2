# IoT_Group-2
项目结构
========
├── Catalog/                  # [服务端] 核心管理模块
│   ├── Catalog_manage.py     # 主程序：REST API 服务，负责设备注册与服务发现
│   ├── config_loader.py      # 工具类：负责读取 JSON 配置文件
│   ├── setting_config.json   # [配置文件] 系统启动的“基准配置” (Bootstrap Config)
│   └── catalog_script.json   # [数据库] 持久化存储已注册的设备列表
│
└── Sensors/                  # [设备端] 模拟器模块
    ├── devices_base.py       # [核心父类] 定义了所有设备的通用行为 (GenericDevice)
    ├── devices_sensor.py     # [子类] 传感器逻辑 (温度、Wifi人数)，包含数据生成算法
    ├── devices_actuator.py   # [子类] 执行器逻辑 (空调、开关)，负责监听指令
    ├── sensors_running.py    # [启动脚本] 多线程启动全楼栋的传感器
    └── actuators_running.py  # [启动脚本] 多线程启动全楼栋的执行器

2. 🏗 System Architecture (系统架构)
我们的架构遵循 LinkSmart 标准，采用了 “Bootstrapping (自举) -> Discovery (发现) -> Operation (运行)” 的三步走模式。

🔄 核心流程
Bootstrapping (自举):

    设备启动时，只读取本地的 setting_config.json。

    此时设备不知道 MQTT Broker 的地址，它只知道 Catalog 的 HTTP 地址。

Service Discovery (服务发现):

    设备向 Catalog 发送 HTTP GET 请求 (/api/services)。

    Catalog 返回 MQTT Broker 的 IP、端口，以及一个 Topic Template (主题模板)。

    (Topic 格式由服务端统一制定，设备负责填空。例如 Catalog 给定 {base}/{room}/{type}/{id}，设备自动填入 polito/R1/temp/1。)

Registration (注册):

    设备携带自己的 ID、Topic、位置信息 (Location)，向 Catalog 发送 POST 请求进行注册。

MQTT Operation (通信):

    Sensors: 连接 Broker，开始周期性发布数据 (Publish)。

    Actuators: 连接 Broker，订阅特定指令频道 (Subscribe)，进入监听模式。

3. 🧠 Simulation Logic (模拟逻辑)
为了让模拟数据更贴近真实世界，我们摒弃了纯随机生成，采用了以下算法：

🌡️ Sensors (数据生成)
    机制: State Memory (状态记忆) + Random Walk (随机游走)。

    原理: 下一刻的数值是基于当前数值进行微调，而不是重新生成。

    温度: 平滑波动，带回归力（防止温度无限升高或降低）。

    人数: 模拟人群流动（进出 -2 ~ +2 人），并受限于房间的 Capacity（最大容量），不会出现负数或超员。

🎮 Actuators (指令响应)
机制: Multi-threading Listening (多线程监听)。

    原理: 每个执行器（如 R1 的空调）都在独立的线程中运行一个 MQTT Client 循环。

    通信:

    订阅: .../cmd (接收控制指令，如 {"status": "ON"})

    反馈: 控制台会打印接收到的指令及执行动作。

🏃 Runners (多线程启动器)
    sensors_running.py 和 actuators_running.py 是系统的上帝视角脚本。

    它们读取房间列表，为每个房间自动创建对应的传感器和执行器实例，并使用 threading 模块并发运行，模拟真实的分布式物联网环境。

4. 🚀 How to Run (运行指南)
请按照以下顺序启动系统，以保证服务发现流程正常工作。

Step 1: 启动 Catalog 服务 (必须最先启动)
Catalog 需要运行在后台，等待设备来询问 Broker 地址。


    # 在项目根目录下
    python Catalog/Catalog_manage.py
    验证: 浏览器访问 http://127.0.0.1:8080 确认服务在线。

    Step 2: 启动传感器模拟 (Sensors)
    模拟全楼栋的数据采集设备。


# 打开一个新的终端窗口
    python Sensors/sensors_running.py
    现象: 你会看到大量 --> Sent 日志，表示数据正在源源不断地发往 Broker。

    Step 3: 启动执行器模拟 (Actuators)
    模拟空调、开关等控制设备.



# 打开另一个新的终端窗口
    python Sensors/actuators_running.py
    现象: 终端会显示 [*] Controller started... 并进入静默监听状态。你可以使用额外的 Publisher 脚本向它们发送指令进行测试。

5. 🖥 Dashboard (Front-end)
    Dashboard 负责将系统中已注册的 Rooms / Sensors / Actuators 以可视化方式呈现，
    并验证系统是否具备 **Service Discovery** 与 **Live Update** 能力。

本项目包含两类 Dashboard：

- Student Dashboard（只读） 
- Manager Dashboard（可控制）

---

5.1 Dashboard Design Goals
Dashboard 的设计目标是：

  不写死任何房间（No hard-coded rooms）
  不写死任何设备（No hard-coded sensors / actuators）
  通过 Catalog / Controller **自动发现新加入的设备**
  当前端运行时：
  - 新 sensor / actuator 被注册
  - 新 room 出现  
  前端无需修改代码即可自动显示

5.2 Data Source Strategy
Dashboard **不直接订阅 MQTT**，而是通过 HTTP 接口获取系统状态。

当前支持的数据来源包括：

   Catalog API  GET http://127.0.0.1:8080/api/devices
用于：
  发现当前系统中已注册的 rooms
  获取每个 room 下的 sensors / actuators
  获取对应的 MQTT topics

（Controller API 可作为扩展，用于实时状态 / 控制）

5.3 Student Dashboard
位置：Dashboard/student_dashboard.py
功能：
  自动展示所有已注册房间
  显示每个房间下的 sensors
  显示对应 MQTT topic
  只读（Read-only）

启动方式：
   streamlit run Dashboard/student_dashboard.py

5.4 Manager Dashboard
位置：Dashboard/Manager_dashboard.py
功能：
	•	自动发现房间与执行器
	•	提供控制按钮（如 HVAC ON/OFF）
	•	控制指令将通过 Controller → MQTT → Actuator

启动方式：
    streamlit run Dashboard/Manager_dashboard.py

5.5 Test Room & Dynamic Discovery
为了验证系统的动态发现能力，项目中允许存在 Test Room：
	•	Test Room 不是预定义在前端
	•	只要有设备注册到 Catalog（即使房间名是 test / tesr）
	•	Dashboard 会自动展示

该机制用于验证：
	•	Dashboard 的鲁棒性
	•	系统在运行时扩展设备的能力

位置：demo/dashboard_demo.py
启动方式：
streamlit run demo/dashboard_demo.py


6. ⚙️ Configuration (配置说明)
Catalog/setting_config.json
这是系统的源头配置。如果你需要修改：

    Catalog 地址: 修改 catalog_config。

    MQTT Broker 地址: 修改 mqtt_config (注意：这里修改后，所有设备重启后会自动获取新地址，无需修改设备代码)。

    房间容量/布局: 修改 rooms 列表。


    {
    "mqtt_config": {
        "broker_address": "test.mosquitto.org", 
        "topic_template": "polito/smartcampus/{room_id}/{device_type}/{index}"
    },
    "rooms": [
        { "room_id": "R1", "type": "classroom", "capacity": 50 }
    ]
    }

📡 MQTT Topic Strategy (Topic 策略说明)
系统采用 Template Pattern (模板模式) 管理 MQTT Topic。

1. 结构定义 (Topic Structure)
Topic 的具体结构逻辑 定义在服务端代码 (Catalog_manage.py) 中，并通过服务发现接口 (/api/services) 动态下发给设备。

当前定义的模板结构如下： "{base_topic_prefix}/{room_id}/{device_type}/{index}"

{base_topic_prefix}: 读取自 setting_config.json (如 polito/smartcampus)。

{room_id}: 房间号 (如 R1)。

{device_type}: 设备类型 (如 temperature, wifi)。

{index}: 设备编号 (如 1)。

2. 后缀规范 (Suffix Standards)
为了区分“数据上传”和“控制指令”，我们在基础 Topic 后增加了功能后缀：
    <img width="677" height="331" alt="image" src="https://github.com/user-attachments/assets/f0d7ddcb-eb15-48a9-bbfd-41210876240a" />

