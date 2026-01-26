import json
import threading
import os
import shutil
import cherrypy
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Catalog.config_loader import RoomConfigLoader

# ==========================================
# Part 1: Catalog registry store and management
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
                "services": [] 
            }

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            shutil.move(tmp, self.path)


# ==========================================
# Part2 : Device API Interface
# Responsible for handling /api/devices requests
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
        
        # --- check logic ---
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

        # --- register logic ---
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
    

    @cherrypy.tools.json_out()
    def DELETE(self, *uri, **params):
        with self.store.lock:
            original_list = self.store.catalog.get("devices", [])
            new_list = []
            delete_count = 0

            if len(uri) > 0:
                device_id = uri[0]
                new_list = [d for d in original_list if d.get("id") != device_id]

                if len(new_list) == len(original_list):
                    raise cherrypy.HTTPError(404, "Device not found")
                else:
                    self.store.catalog["devices"] = new_list
                    self.store.save()
                    return {"message": "Deleted", "id": device_id}
            
            elif len(params) > 0:
                valid_keys = ["id", "room", "type"]
                if not any (k in params for k in valid_keys):
                    raise cherrypy.HTTPError(400, "No valid deletion criteria provided")
                
                for d in original_list:
                    device_id = d.get("id")

                    try:
                        parts = device_id.split("_")

                        id_room = parts[0]
                        id_type = parts[1]
                    except:
                        new_list.append(d)
                        continue

                    should_delete = True
                    if 'room' in params and id_room != params['room']:
                        should_delete = False
                    if 'type' in params and id_type != params['type']:
                        should_delete = False
                    if 'id' in params and device_id != params['id']:
                        should_delete = False
                    
                    if should_delete:
                        delete_count += 1
                    else:
                        new_list.append(d)
                if delete_count == 0:
                    raise cherrypy.HTTPError(404, "No matching devices found to delete")


                self.store.catalog["devices"] = new_list
                self.store.save()
                return {"message": "Deleted devices based on filters"}
            else:
                raise cherrypy.HTTPError(400, "No deletion criteria provided")
            
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, *uri, **params):
        obj = cherrypy.request.json

        if len(uri) > 0:
            url_id = uri[0]
            body_id = str(obj.get("id"))
            if body_id and body_id != url_id:
                raise cherrypy.HTTPError(400, "ID in URL and body do not match")
            

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
        
        with self.store.lock:
            original_list = self.store.catalog.setdefault("devices", [])
            target_id = str(obj["id"])

            for i, item in enumerate(original_list):
                if str(item.get("id")) == target_id:
                    print(f"[Device] Update existing via PUT: {target_id}")
                    original_list[i] = obj
                    cherrypy.response.status = 200
                    break
            else:
                print(f"[Device] Register new via PUT: {target_id}")
                original_list.append(obj)
                cherrypy.response.status = 201

            self.store.save()
        return {"message": "Updated", "id": target_id}


# ==========================================
# Part 3: Services API Interface
# Responsible for handling /api/services requests
# ==========================================
class ServicesAPI:
    exposed = True
    def __init__(self, store: CatalogStore, config_loader):
        self.store = store
        self.config_loader = config_loader
        self.static_services = self._build_static_services()

    def _build_static_services(self):

        static_services = []

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
        return static_services
        
    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        with self.store.lock:
            registered_services = self.store.catalog.get("services", [])[:]
        
        all_services = self.static_services + registered_services

        
        if len(uri) > 0:
            target_id = uri[0]
            for s in all_services:
                if str(s['id']) == str(target_id): return s
            raise cherrypy.HTTPError(404, "Service not found")
        return all_services


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
        return {"message": "Service Registered", "id": target_id}
    
    @cherrypy.tools.json_out()
    def DELETE(self, *uri, **params):
        with self.store.lock:
            original_list = self.store.catalog.get("services", [])
            new_list = []

            if len(uri) > 0:
                service_id = uri[0]
                new_list = [s for s in original_list if s.get("id") != service_id]

                if len(new_list) == len(original_list):
                    raise cherrypy.HTTPError(404, "Service not found")
                else:
                    self.store.catalog["services"] = new_list
                    self.store.save()
                    return {"message": "Deleted", "id": service_id}
    
            else:
                raise cherrypy.HTTPError(400, "No deletion criteria provided")
    
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, *uri, **params):
        obj = cherrypy.request.json

        if len(uri) > 0:
            url_id = uri[0]
            body_id = str(obj.get("id"))
            if body_id and body_id != url_id:
                raise cherrypy.HTTPError(400, "ID in URL and body do not match")
        
        if "id" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: id")
        if "service_type" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: service_type")
        if "endpoint" not in obj:
            raise cherrypy.HTTPError(400, "Missing required field: endpoint")
        
        with self.store.lock:
            original_list = self.store.catalog.setdefault("services", [])
            target_id = str(obj["id"])

            for i, item in enumerate(original_list):
                if str(item.get("id")) == target_id:
                    print(f"[Service] Update existing via PUT: {target_id}")
                    original_list[i] = obj
                    cherrypy.response.status = 200
                    break
            else:
                print(f"[Service] Register new via PUT: {target_id}")
                original_list.append(obj)
                cherrypy.response.status = 201

            self.store.save()
        return {"message": "Service Updated", "id": target_id}


# ==========================================
# Part 4: Run Catalog Server
# ==========================================
def run(host="0.0.0.0", port=8080):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "catalog_script.json")
    
    config_filename = "setting_config.json"
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    store = CatalogStore(path)
    
    loader = None 

    loader = None  
    try:
        loader = RoomConfigLoader(config_filename)
        broker_conf = loader.get_broker_info()
        print(f"[*] Loaded System Config. MQTT Broker: {broker_conf.get('broker')}:{broker_conf.get('broker_port')}")
        
    except Exception as e:
        print(f"[!] Warning: Failed to load settings ({e}).")
        print("[!] ServicesAPI will NOT be mounted because config is missing.")

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }

    cherrypy.tree.mount(DevicesAPI(store), '/api/devices', config=conf)
    
    if loader:
        cherrypy.tree.mount(ServicesAPI(store, loader), '/api/services', config=conf)
    else:
        print("[!] SKIP: /api/services not mounted due to config error.")

    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
    })

    print(f"[*] Catalog Server started at http://{host}:{port}")
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    run()