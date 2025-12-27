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
            original_list = self.store.catalog.get("devices", [])
            devices_list = original_list[:] 


        if len(uri) > 0:
            device_id = uri[0]
            for item in devices_list:
                if item['id'] == device_id:
                    return item

            raise cherrypy.HTTPError(404, "Device not found")
    
        if not params:
            return devices_list

        filtered_results = []
        for dev in devices_list:
            match = True
            
            if 'id' in params and dev['id'] != params['id']:
                match = False

            if 'room' in params:
                if dev.get('location', {}).get('room') != params['room']:
                    match = False
            
            if 'type' in params and dev.get('type') != params['type']:
                match = False
            
            if match:
                filtered_results.append(dev)

        return filtered_results

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

        if len(uri) > 0:
            user_id = uri[0]
            for u in user_list:
                if str(u.get("id")) == str(user_id):
                    return u
                
            raise cherrypy.HTTPError(404, "User not found")
        
        if not params:
            return user_list
        filtered_results = []
        for user in user_list:
            match = True

            if 'name'in params and user.get('name') != params['name']:
                match = False   
            
            if 'role' in params and user.get('role') != params['role']:
                match = False
            if match:
                filtered_results.append(user)

        return filtered_results


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
    
# ==========================================
# 第四部分：API 接口 (Services)
# 负责处理 /api/services 的请求
# ==========================================
class ServicesAPI:
    exposed = True
    def __init__(self, store: CatalogStore, config_loader):
        self.store = store
        self.config_loader = config_loader
        
    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        broker_info = self.config_loader.get_broker_info() 
        catalog_info = self.config_loader.get_catalog_info()
        
        static_services = [
            {
                "id": "MQTT_BROKER_01",
                "service_type": "mqtt",
                "endpoint": {
                    "broker": broker_info.get("broker"),
                    "broker_port": broker_info.get("broker_port"),
                    "topic_structure": f'{broker_info.get("base_topic_prefix")}/{{room_id}}/{{device_type}}/{{index_number}}'
                }
            },
            {
                "id": "REST_CATALOG_01",
                "service_type": "catalog",
                "endpoint": {
                    "url": f"http://{catalog_info['host']}:{catalog_info['port']}{catalog_info['api_path']}"
                }
            }
        ]

        with self.store.lock:
            # 浅拷贝一份，防止并发问题
            registered_services = self.store.catalog.get("services", [])[:]

        # 3. 如果是查询特定 ID (/api/services/ID)
        if len(uri) > 0:
            target_id = uri[0]
            # 先找静态的
            for s in static_services:
                if str(s['id']) == str(target_id): return s
            # 再找动态的
            for s in registered_services:
                if str(s['id']) == str(target_id): return s
            
            raise cherrypy.HTTPError(404, "Service not found")

        # 4. 如果是查询所有，合并两者返回
        # 静态在前，动态在后
        return static_services + registered_services
    
    
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *uri, **params):
        obj = cherrypy.request.json

        if "id" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: id")
        if "service_type" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: service_type")
        if "endpoint" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: endpoint")
        
        with self.store.lock:
            data_list = self.store.catalog.setdefault("services", [])
            target_id = str(obj["id"])

            for i, item in enumerate(data_list):
                if str(item.get("id")) == target_id:
                    print(f"[Service] Update existing: {target_id}")
                    data_list[i] = obj
                    break
            else:
                print(f"[Service] Register new: {target_id}")
                data_list.append(obj)
            
            self.store.save()

        cherrypy.response.status = 201
        return {"message": "Registered", "id": target_id}

# ==========================================
# 第四部分：服务器启动与路由挂载
# ==========================================
def run(host="0.0.0.0", port=8080):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "catalog_script.json")
    config_path = os.path.join(current_dir, "setting_config.json")
    

    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    store = CatalogStore(path)

    loader = None  # <12.27修改，因在运行OccupancyAnalyzer时找不到loader：在 try 之前先定义它，哪怕是空的
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
    cherrypy.tree.mount(ServicesAPI(store, loader), '/api/services', config=conf)

    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
    })

    print(f"[*] Catalog Server started at http://{host}:{port}")
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    run()