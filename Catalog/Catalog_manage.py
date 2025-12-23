import json, threading, os, shutil, cherrypy

# ==========================================
# 第一部分：数据仓库 (CatalogStore)
# 负责读写 catalog.json 文件
# ==========================================
class CatalogStore:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.data = {}
        

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {
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
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            shutil.move(tmp, self.path)

# ==========================================
# 第二部分：API 接口 (Devices)
# 负责处理 /api/devices 的请求
# ==========================================

class DevicesAPI:
    exposed = True
    def __init__(self, store: CatalogStore):
        self.store = store

    def GET(self, device_id=None):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        with self.store.lock:
            data_list = self.store.data.get("devices", [])
            
            if device_id is None:
                return json.dumps(data_list)
            
            for item in data_list:
                if str(item.get("id")) == str(device_id):
                    return json.dumps(item)
        
        raise cherrypy.HTTPError(404, "Device not found")

    def POST(self):
        body = cherrypy.request.body.read() or b"{}"
        try:
            obj = json.loads(body)
        except Exception:
            raise cherrypy.HTTPError(400, "Invalid JSON")
        
        required_keys = ["type", "resources", "mqtt_topics", "location"]

        for key in required_keys:
            if key not in obj:
                raise cherrypy.HTTPError(400, f"Missing required field: {key}")

        loc = obj.get("location", {}) 

        required_loc_keys = ["campus", "building", "floor", "room"]
        
        for key in required_loc_keys:
            if key not in loc:
                 raise cherrypy.HTTPError(400, f"Missing location info: {key}")

        with self.store.lock:
            data_list = self.store.data.setdefault("devices", [])

            
            # 更新模式
            if "id" in obj:
                target_id = str(obj["id"])
                for i, item in enumerate(data_list):
                    if str(item.get("id")) == target_id:
                        data_list[i] = obj
                        break
                else:
                    raise cherrypy.HTTPError(404, f"Device ID {target_id} not found. Cannot update.")

            # 新建模式
            else:
                room_name = loc["room"]
                dev_type = obj["type"]
                
                count = len(data_list) + 1
                new_id = f"{room_name}_{dev_type}_{count}"

                existing_ids = [str(d.get("id")) for d in data_list]
                while new_id in existing_ids:
                    count += 1
                    new_id = f"{room_name}_{dev_type}_{count}"
                
                obj["id"] = new_id
                data_list.append(obj)
            
            self.store.save()
        
        cherrypy.response.status = 201
        return json.dumps({"status": "ok", "id": obj["id"]})

# ==========================================
# 第三部分：API 接口 (Users)
# 负责处理 /api/users 的请求
# ==========================================
class UsersAPI:
    exposed = True
    def __init__(self, store: CatalogStore):
        self.store = store

    def GET(self, user_id=None):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        with self.store.lock:
            user_list = self.store.data.get("users", [])
            
            if user_id is None:
                return json.dumps(user_list)
            
            for u in user_list:
                if str(u.get("id")) == str(user_id):
                    return json.dumps(u)
                
        raise cherrypy.HTTPError(404, "User not found")

        
    def POST(self):
        body = cherrypy.request.body.read() or b"{}"
        try:
            obj = json.loads(body)
        except Exception:
            raise cherrypy.HTTPError(400, "Invalid JSON")

        required_keys = ["name", "role"]

        for key in required_keys:
            if key not in obj:
                raise cherrypy.HTTPError(400, f"Missing required field: {key}")

        with self.store.lock:
            user_list = self.store.data.setdefault("users", [])

             # 更新模式
            if "id" in obj:
                target_id = str(obj["id"])
                for i, item in enumerate(user_list):
                    if str(item.get("id")) == target_id:
                        user_list[i] = obj
                        break
                else:
                    raise cherrypy.HTTPError(404, f"User ID {target_id} not found. Cannot update.")

            # 新建模式
            else:
                count = len(user_list) + 1
                new_id = f"user_{count}"

                existing_ids = [str(d.get("id")) for d in user_list]
                while new_id in existing_ids:
                    count += 1
                    new_id = f"user_{count}"
                
                obj["id"] = new_id
                user_list.append(obj)
            
            self.store.save()
        
        cherrypy.response.status = 201
        return json.dumps({"status": "ok", "id": obj["id"]})

# ==========================================
# 第四部分：服务器启动与路由挂载
# ==========================================
def run(host="0.0.0.0", port=8080):
    path = "Catalog/catalog_script.json"
    store = CatalogStore(path)

    rest_conf = {
        '/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()},
    }

    cherrypy.tree.mount(DevicesAPI(store), '/api/devices', config=rest_conf)

    cherrypy.tree.mount(UsersAPI(store),   '/api/users',   config=rest_conf)

    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
        'tools.encode.on': True,
        'tools.encode.encoding': 'utf-8'
    })

    print(f"Server started at http://{host}:{port}")
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    run()
