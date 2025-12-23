1. Overview | 项目概述
The Data Processing Layer is the core intelligence of the SmartCampus system. It follows a microservices architecture and integrates two communication paradigms: REST and MQTT. It is responsible for analyzing real-time data to automate classroom comfort and resource optimization.
数据处理层是 SmartCampus 系统的核心智能部分 。它遵循微服务架构，整合了 REST 和 MQTT 两种通信模式 ，负责分析实时数据以实现教室舒适度自动调节和资源优化 。


2. Key Features | 核心功能
Presence-Based Thermal Control: Automatically sends HVAC activation (Comfort Mode) or energy-saving commands based on real-time room occupancy.
存在感应热控制: 根据实时人数自动发送空调开启（舒适模式）或节能指令 。

Study-room Recommendation: Calculates occupancy rates and ranks classrooms to help students find study spaces.
自习室推荐: 计算教室上座率并进行排序，帮助学生高效寻找自习位 。

Unified MQTT Integration: Subscribes to sensors and publishes commands to actuators through the Message Broker.
统一 MQTT 集成: 通过消息代理订阅传感器数据并向执行器发布控制指令 。


3. Data Structure | 数据结构 (rooms_config.json)
The system uses a JSON-based configuration to define the campus layout (Building R). 系统使用 JSON 配置文件来定义校园布局（R 教学楼） ：
    Capacity: Maximum seating for occupancy rate calculation.
    Capacity: 教室容量，用于上座率计算 。

    Type: Categorizes spaces (e.g., "Sala gradonata", "Aula", "Sale studio").
    Type: 空间类别（如阶梯教室、普通教室、工作室）。


4. Logic Workflow | 逻辑工作流
Input: Subscribes to building/R/+/occupancy from the WiFi-based Occupancy Connector.
输入: 从 WiFi 人数检测器订阅实时人数数据 。


Processing:
    Occupancy Rate: Calculates current_people / capacity.
    上座率: 计算 当前人数 / 总容量。


    Thermal Logic: If people > 0, HVAC status = ON (22°C); else OFF (26°C).
    温控逻辑: 若有人则空调开启（22°C），无人则关闭或节能（26°C） 。


    Output: Publishes JSON commands to building/R/+/hvac/control.
    输出: 向空调控制器发布 JSON 格式的控制指令 。


5. Execution Example | 运行日志示例

Connecting to broker broker.hivemq.com...
Successfully connected to MQTT Broker!

[HVAC] Room R1: Occupied (25 ppl). Sending ON command.

--- Real-time Study-room Recommendations (Top 3) ---
ID: R1B   | Type: Aula            | Occupancy:   0.00% | People: 0
ID: R2    | Type: Sala gradonata  | Occupancy:   0.00% | People: 0
ID: R1    | Type: Sala gradonata  | Occupancy:   8.33% | People: 25
----------------------------------------------------