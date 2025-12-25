import json
import threading
import os
import shutil
import cherrypy
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader

# ==========================================
# 第一部分：数据仓库 (CatalogStore)
# 负责读写 catalog.json 文件
# ==========================================
class CatalogStore:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        # [修正 1] 将 self.data 改名为 self.catalog，与 API 中的调用保持一致
        self.catalog = {} 

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {
                "project_info": {},
                "system_settings": {},
                "devices": [], 
                "users": [],  
                "services": [] 
            }

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            shutil.move(tmp, self.path)

# ==========================================
# 第二部分：API 接口 (Devices)
# 负责处理 /api/devices 的请求
# ==========================================
class DevicesAPI:
    exposed = True
    def __init__(self, store: CatalogStore):
        self.store = store

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        with self.store.lock:
            # 现在 self.store.catalog 是存在的了
            original_list = self.store.catalog.get("devices", [])
            devices_list = original_list[:] # 浅拷贝，线程安全

        if len(uri) == 0:
            return devices_list

        device_id = uri[0] 
        for item in devices_list:
            if str(item["id"]) == str(device_id):
                return item
        
        raise cherrypy.HTTPError(404, "Device not found")

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        obj = cherrypy.request.json
        
        # --- 校验逻辑 ---
        if "id" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: id")

        required_keys = ["type", "resources", "mqtt_topics", "location"]
        for key in required_keys:
            if key not in obj:
                raise cherrypy.HTTPError(400, f"Missing required field: {key}")

        loc = obj.get("location", {}) 
        required_loc_keys = ["campus", "building", "floor", "room"]
        for key in required_loc_keys:
            if key not in loc:
                raise cherrypy.HTTPError(400, f"Missing location info: {key}")

        # --- 写入逻辑 ---
        with self.store.lock:
            data_list = self.store.catalog.setdefault("devices", [])
            target_id = str(obj["id"])

            for i, item in enumerate(data_list):
                if str(item.get("id")) == target_id:
                    print(f"[Device] Update existing: {target_id}")
                    data_list[i] = obj
                    break
            else:
                print(f"[Device] Register new: {target_id}")
                data_list.append(obj)
            
            self.store.save()
        
        cherrypy.response.status = 201
        return {"message": "Registered", "id": target_id}

# ==========================================
# 第三部分：API 接口 (Users)
# 负责处理 /api/users 的请求
# ==========================================
class UsersAPI:
    exposed = True
    def __init__(self, store: CatalogStore):
        self.store = store

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        with self.store.lock:
            original_list = self.store.catalog.get("users", [])
            user_list = original_list[:]

        if len(uri) == 0:
            return user_list

        user_id = uri[0]
        for u in user_list:
            if str(u.get("id")) == str(user_id):
                return u
            
        raise cherrypy.HTTPError(404, "User not found")

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        obj = cherrypy.request.json
        
        if "id" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: id")

        required_keys = ["name", "role"]
        for key in required_keys:
            if key not in obj:
                raise cherrypy.HTTPError(400, f"Missing required field: {key}")

        with self.store.lock:
            data_list = self.store.catalog.setdefault("users", [])
            target_id = str(obj["id"])

            for i, item in enumerate(data_list):
                if str(item.get("id")) == target_id:
                    print(f"[User] Update existing: {target_id}") # 修正了日志文字
                    data_list[i] = obj
                    break
            else:
                print(f"[User] Register new: {target_id}") # 修正了日志文字
                data_list.append(obj)
            
            self.store.save()
        
        cherrypy.response.status = 201
        return {"status": "ok", "id": target_id}

# ==========================================
# 第四部分：服务器启动与路由挂载
# ==========================================
def run(host="0.0.0.0", port=8080):
    # [修正 3] 使用绝对路径，防止找不到文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "catalog_script.json")
    config_path = os.path.join(current_dir, "setting_config.json")
    
    # 自动创建目录（如果不存在）
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    store = CatalogStore(path)

    try:
        loader = RoomConfigLoader(config_path)
        broker_conf = loader.get_broker_info()
        print(f"[*] Loaded System Config. MQTT Broker: {broker_conf['broker']}:{broker_conf['port']}")
        
        
    except Exception as e:
        print(f"[!] Warning: Failed to load settings ({e}). Using defaults.")

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }

    cherrypy.tree.mount(DevicesAPI(store), '/api/devices', config=conf)
    cherrypy.tree.mount(UsersAPI(store),   '/api/users',   config=conf)

    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
    })

    print(f"[*] Catalog Server started at http://{host}:{port}")
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    run()