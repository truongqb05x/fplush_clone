import time
import requests

def parse_kiot_proxy_string(proxy_str):
    if not proxy_str:
        return None
    parts = proxy_str.split(":")
    if len(parts) == 2:
        return {
            "host": parts[0],
            "port": parts[1],
            "user": "1",
            "pass": "1"
        }
    elif len(parts) == 4:
        return {
            "host": parts[0],
            "port": parts[1],
            "user": parts[2],
            "pass": parts[3]
        }
    return None

def get_current_kiot_proxy(key):
    """Lấy proxy hiện tại của key"""
    url = f"https://api.kiotproxy.com/api/v1/proxies/current?key={key}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("success") and data.get("data"):
            return data["data"].get("http")
    except Exception as e:
        pass
    return None

def get_new_kiot_proxy(key, region="random"):
    """Lấy proxy mới cho key và đợi nếu cần thiết"""
    url = f"https://api.kiotproxy.com/api/v1/proxies/new?key={key}&region={region}"
    
    old_proxy = get_current_kiot_proxy(key)
    
    while True:
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get("success") and data.get("data"):
                new_proxy = data["data"].get("http")
                
                if old_proxy and new_proxy == old_proxy:
                    print(f"[KiotProxy] Proxy mới trùng với proxy cũ. Đợi 30s...")
                    time.sleep(30)
                    continue
                
                print(f"[KiotProxy] Lấy proxy thành công: {new_proxy}")
                return new_proxy
            else:
                msg = data.get("message", "")
                if data.get("error") == "KEY_NOT_FOUND":
                    print(f"[KiotProxy] Key không tồn tại: {key}")
                    return None
                    
                import re
                wait_time = 30
                match = re.search(r'sau (\d+) giây', msg, re.IGNORECASE)
                if match:
                    wait_time = int(match.group(1)) + 1
                    
                print(f"[KiotProxy] Lấy thất bại: {msg}. Đợi {wait_time}s...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"[KiotProxy] Lỗi API: {e}. Đợi 30s...")
            time.sleep(30)
