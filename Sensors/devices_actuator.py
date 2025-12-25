import time
import json
from devices_base import GenericDevice

# ==========================================
# 子类 2: Controller (执行器)
# 核心差异：
# 1. 角色 (Role) 必须是 actuator
# 2. 行为不是 Publish 而是 Subscribe
# 3. 需要一个函数来处理收到的消息
# ==========================================
class Controller(GenericDevice):
    def __init__(self, room, index, catalog_type):
        # [填空 1] 初始化父类
        # 目标：调用 super().__init__
        # 思考：这里的 role 应该填什么？(它决定了 ID 是 ..._sensor_1 还是 ..._actuator_1)
        # 思考：catalog_type 依然是 "temperature" 或 "wifi"
        super().__init__(room, index, catalog_type, "actuator")

        # [填空 2] 定义 Topic
        # 目标：Controller 是被控制端，所以我们要监听命令。
        # 思考：Sensor 用了 "/value"，Controller 应该用什么后缀？(我们之前商定的是 "/cmd")
        self.topics = {
            "cmd": self.base_topic + "/cmd"
        }

    def notify(self, topic, payload):
        """
        [填空 3] 业务逻辑处理
        这是真正干活的地方。当有人给你发消息时，这个函数会被触发。
        """
        # 目标：打印出“我收到了指令”。
        # 进阶挑战：尝试解析 payload。如果 payload 里包含 "ON"，打印 "空调已开启"；否则打印 "关闭"。
        print(f"[!] Message received on {topic}")
        try:
            command = json.loads(payload)

            if "status" in command:
                sensor_status = command["status"]
                if sensor_status.upper() == "ON":
                    print("[+] Air conditioner turned ON")
                else:
                    print("[-] Air conditioner turned OFF")

            if "target_temp" in command:
                temp_value = command["target_temp"]
                print(f"[+] Setting target temperature to {temp_value}°C")
                
            if "mode" in command:
                mode_value = command["mode"]
                print(f"[+] Setting mode to {mode_value}")
            
        except json.JSONDecodeError:
            # 如果 Breaker 发来的不是 JSON，而是纯数字或字符串
            print(f">>> Unvalid: {payload}")


    def start(self):
        # 1. 向 Catalog 注册 (这步和 Sensor 一样，直接送分)
        if not self.register_to_catalog(self.topics):
            return

        # 2. 连接 MQTT (这也一样)
        client = self.connect_mqtt()

        # =======================================================
        # [填空 4] 设置 MQTT 回调逻辑 (最难的部分)
        # =======================================================
        # 目标：告诉 Paho 库，“每当收到新消息，请帮我运行这个函数”。
        # 提示 1：你需要定义一个内部函数 on_message(client, userdata, msg)
        # 提示 2：在内部函数里，调用上面的 self.notify()。
        #        注意 msg 对象里有 msg.topic 和 msg.payload (是二进制，要 .decode())
        
        def on_message(client, userdata, msg):
            self.notify(msg.topic, msg.payload.decode())

        
        # 这一行是把你的函数挂载到 client 上
        client.on_message = on_message


        # =======================================================
        # [填空 5] 订阅 Topic
        # =======================================================
        # 目标：告诉 Broker，“我要监听这个频道”。
        # 提示：使用 client.subscribe()
        # 参数：是我们定义的 self.topics['cmd']
        target_topic = self.topics['cmd']
        client.subscribe(target_topic)

        print(f"[*] Controller started. Listening on: {self.topics['cmd']}")

        # 3. 保持运行
        # 思考：为什么这里不需要像 Sensor 那样写 while True: publish?
        # 因为 loop_start() 已经在后台线程帮我们收消息了。
        # 我们只需要让主线程不退出即可。
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            print("Controller Stopped")

if __name__ == "__main__":
    # 请在这里写代码实例化 Controller 并运行
    # 模拟：R1 房间的第 1 号温度控制器
    room = "R1"
    index = 1
    catalog_type = "temperature"
    controller = Controller(room, index, catalog_type)
    controller.start()