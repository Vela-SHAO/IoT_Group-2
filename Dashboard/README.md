学生端 Dashboard（Student Dashboard）
文件名： Student_dashboard.py
面向学生用户，根据教室当前使用情况，推荐最适合学习的教室，相当于决策支持型dashboard：
1，显示 Top 3 推荐教室
2，推荐逻辑基于：当前人数 / 容量（上座率）和教室容量大小，日后可以扩展教室类型，噪声等内容加入推荐
3，页面每 10 秒自动刷新一次
4，页面展示内容：教室编号，教室类型，当前人数/最大容量，上座率展示条，推荐原因（如有）
5，运行方式：streamlit run Dashboard/student_dashboard.py


管理员端 Dashboard（Manager Dashboard）
文件名： manager_dashboard.py
面向管理员用户，用于实时监控教室状态，并提供逻辑层面的温控控制界面：
1，页面每 10 秒自动刷新一次
2，页面展示内容：当前人数，上座率，当前温度
3，提供全局温控模式选择：Automatic，Comfort，Energy Saving，点击按钮后，仅展示“控制指令已发送”的逻辑流程说明
4，运行方式：streamlit run Dashboard/manager_dashboard.py

数据配置说明
所有教室的基础信息（教室编号、类型、容量等）统一存放在：rooms_config.json



