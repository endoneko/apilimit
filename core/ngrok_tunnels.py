import json
import os
from pyngrok import ngrok, conf

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

def start_tunnel(port):
    routes_path = os.path.join(CONFIG_DIR, 'routes.json')
    if not os.path.exists(routes_path):
        return None
    
    with open(routes_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f).get('ngrok_config', {})
    
    token = cfg.get('authtoken')
    if not token or token == "your_ngrok_token":
        print("[Ngrok] Token not configued correctly. Exited public tunnel setup.")
        return None
        
    pyngrok_config = conf.PyngrokConfig(auth_token=token, region=cfg.get('region', 'us'))
    conf.set_default(pyngrok_config)

    print(f"[Ngrok] Starting tunnel on port {port}...")
    try:
        tunnel = ngrok.connect(port, bind_tls=cfg.get('bind_tls', True))
        url = tunnel.public_url
        print(f"\n=======================================================")
        print(f"  [SUCCESS] Ngrok Tunnel live at ==> {url}")
        print(f"=======================================================\n")
        return url
    except Exception as e:
        print("[Ngrok] Failed to start tunnel:", e)
        return None