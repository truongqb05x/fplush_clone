# -*- coding: utf-8 -*-
"""
Quản lý proxy: checkpoint tracking, blacklist, delete
"""
import os

PROXY_FILE = "resources/proxy.txt"
PROXY_DELETED_FILE = "resources/proxy_deleted.txt"

# Dict để đếm checkpoint cho từng proxy
proxy_checkpoint_count = {}


def reset_proxy_checkpoint_count(proxy_info):
    """Reset counter checkpoint cho proxy khi thành công"""
    if not proxy_info:
        return
    
    proxy_key = f"{proxy_info['host']}:{proxy_info['port']}"
    if proxy_key in proxy_checkpoint_count:
        print(f"🔄 Reset checkpoint counter cho proxy {proxy_key}")
        proxy_checkpoint_count[proxy_key] = 0


def mark_proxy_checkpoint(proxy_info):
    """Đánh dấu proxy gây checkpoint"""
    if not proxy_info:
        return
    
    # Tạo key để nhận diện proxy (host:port)
    proxy_key = f"{proxy_info['host']}:{proxy_info['port']}"
    
    # Tăng count checkpoint
    proxy_checkpoint_count[proxy_key] = proxy_checkpoint_count.get(proxy_key, 0) + 1
    
    print(f"⚠️ Proxy {proxy_key} gây checkpoint lần thứ {proxy_checkpoint_count[proxy_key]}")
    
    # Nếu checkpoint 2 lần liên tiếp, thêm vào blacklist
    if proxy_checkpoint_count[proxy_key] >= 2:
        print(f"🚫 BLACKLIST PROXY: {proxy_key} (checkpoint 2 lần)")
        add_proxy_to_blacklist(proxy_info)


def add_proxy_to_blacklist(proxy_info):
    """Thêm proxy vào blacklist và lưu vào proxy_deleted.txt để tái sử dụng sau"""
    try:
        # Tạo key để nhận diện proxy
        blacklist_key = f"{proxy_info['host']}:{proxy_info['port']}"
        proxy_line = f"{proxy_info['host']}:{proxy_info['port']}:{proxy_info.get('user', '')}:{proxy_info.get('pass', '')}"
        
        # Lưu proxy vào file proxy_deleted.txt để tái sử dụng sau
        try:
            with open(PROXY_DELETED_FILE, "r", encoding="utf-8") as f:
                deleted_proxies = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            deleted_proxies = []
        
        # Chỉ thêm nếu chưa có
        if proxy_line not in deleted_proxies:
            with open(PROXY_DELETED_FILE, "a", encoding="utf-8") as f:
                f.write(f"{proxy_line}\n")
            print(f"💾 Đã lưu proxy {blacklist_key} vào proxy_deleted.txt để tái sử dụng")
        
        # Đọc file proxy hiện tại
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Lọc ra proxy không phải là proxy bị xóa
        new_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Kiểm tra xem proxy có phải là proxy bị xóa không
            proxy_parts = line.split(":")
            if len(proxy_parts) >= 2: 
                proxy_key = f"{proxy_parts[0]}:{proxy_parts[1]}"
                if proxy_key != blacklist_key:
                    new_lines.append(line + "\n")
        
        # Ghi lại file proxy đã lọc
        with open(PROXY_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        print(f"✅ Đã xóa proxy {blacklist_key} khỏi proxy.txt")
        
        # Xóa khỏi counter
        proxy_key = f"{proxy_info['host']}:{proxy_info['port']}"
        if proxy_key in proxy_checkpoint_count:
            del proxy_checkpoint_count[proxy_key]
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa proxy: {e}")
