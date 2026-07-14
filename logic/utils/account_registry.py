# -*- coding: utf-8 -*-
import os
import json
import threading
import random
from utils.driver_utils import load_user_agents, get_random_ua

# Constants
ACCOUNT_PROXY_FILE = "resources/account_proxy.json"
ACCOUNT_UA_FILE = "resources/account_ua.json"

# Locks
PROXY_MAP_LOCK = threading.Lock()
UA_MAP_LOCK = threading.Lock()

def load_proxy_mapping():
    """Tải mapping UID -> Proxy từ JSON"""
    with PROXY_MAP_LOCK:
        if os.path.exists(ACCOUNT_PROXY_FILE):
            try:
                with open(ACCOUNT_PROXY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_proxy_mapping(mapping):
    """Lưu mapping UID -> Proxy vào JSON"""
    with PROXY_MAP_LOCK:
        os.makedirs(os.path.dirname(ACCOUNT_PROXY_FILE), exist_ok=True)
        with open(ACCOUNT_PROXY_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=4)

def load_ua_mapping():
    """Tải mapping UID -> UserAgent từ JSON"""
    with UA_MAP_LOCK:
        if os.path.exists(ACCOUNT_UA_FILE):
            try:
                with open(ACCOUNT_UA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_ua_mapping(mapping):
    """Lưu mapping UID -> UserAgent vào JSON"""
    with UA_MAP_LOCK:
        os.makedirs(os.path.dirname(ACCOUNT_UA_FILE), exist_ok=True)
        with open(ACCOUNT_UA_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=4)

def get_assigned_ua(uid, mapping):
    """Lấy UserAgent đã gán hoặc gán mới từ file useragent.txt"""
    if uid in mapping:
        return mapping[uid]
    
    # Nếu chưa có, lấy ngẫu nhiên 1 cái từ useragent.txt rồi cố định luôn
    uas = load_user_agents()
    if uas:
        new_ua = get_random_ua(uas)
        if new_ua:
            mapping[uid] = new_ua
            save_ua_mapping(mapping)
            return new_ua
    return None

def get_assigned_proxy(uid, all_proxies, mapping):
    """Lấy proxy đã gán hoặc gán proxy mới duy nhất cho UID"""
    if not all_proxies:
        return None
        
    if uid in mapping:
        return mapping[uid]
    
    # Tìm proxy chưa được gán cho ai
    assigned_proxies = set(mapping.values())
    for proxy in all_proxies:
        proxy_str = f"{proxy['host']}:{proxy['port']}:{proxy['user']}:{proxy['pass']}"
        if proxy_str not in assigned_proxies:
            mapping[uid] = proxy_str
            save_proxy_mapping(mapping)
            return proxy_str
            
    # Nếu hết proxy mới, dùng đại một cái
    print(f"⚠️ Hết proxy duy nhất cho UID {uid}, chọn ngẫu nhiên...")
    if all_proxies:
        p = random.choice(all_proxies)
        return f"{p['host']}:{p['port']}:{p['user']}:{p['pass']}"
    return None

def parse_proxy_str(proxy_str):
    if not proxy_str: return None
    parts = proxy_str.split(":")
    if len(parts) < 4: return None
    return {
        "host": parts[0], "port": parts[1],
        "user": parts[2], "pass": parts[3]
    }
