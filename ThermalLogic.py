def decide_hvac_status(temperature, occupancy, capacity):
    """
    解耦的温控判断逻辑 [坤浩的建议]
    返回布尔值 (True/False)，供 Controller 脚本直接调用执行行为
    """
    # 计算上座率，用于高密度人群的通风逻辑
    occupancy_rate = (occupancy / capacity) if capacity > 0 else 0
    
    # 规则 1：节能优先 - 如果房间没人，建议关闭空调 (False)
    if occupancy == 0:
        return False
        
    # 规则 2：舒适度优先 - 如果温度过热 (>26°C) 或过冷 (<18°C)，建议开启 (True)
    if temperature > 26 or temperature < 18:
        return True
    
    # 规则 3：人群密度优先 - 即使温度正常，如果上座率超过 80%，开启通风 (True)
    if occupancy_rate > 0.8:
        return True
        
    return False