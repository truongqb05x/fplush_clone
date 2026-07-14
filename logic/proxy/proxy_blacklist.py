# proxy_blacklist.py
PROXY_BLACKLIST_FILE = "resources/proxy_blacklist.txt"


def add_to_proxy_blacklist(proxy_info):
    """Thêm proxy vào blacklist"""
    try:
        proxy_key = f"{proxy_info['host']}:{proxy_info['port']}"
        
        # Kiểm tra xem đã có trong blacklist chưa
        blacklist = set()
        try:
            with open(PROXY_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        blacklist.add(line)
        except FileNotFoundError:
            pass
        
        # Nếu chưa có thì thêm vào
        if proxy_key not in blacklist:
            with open(PROXY_BLACKLIST_FILE, "a", encoding="utf-8") as f:
                f.write(f"{proxy_key}\n")
            
            print(f"✅ Đã thêm {proxy_key} vào blacklist")
            return True
        else:
            print(f"⏭️ Proxy {proxy_key} đã có trong blacklist")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi thêm vào blacklist: {e}")
        return False


def remove_from_proxy_blacklist(proxy_key):
    """Xóa proxy khỏi blacklist"""
    try:
        blacklist = []
        found = False
        
        # Đọc blacklist hiện tại
        try:
            with open(PROXY_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and line != proxy_key:
                        blacklist.append(line)
                    elif line == proxy_key:
                        found = True
        except FileNotFoundError:
            pass
        
        # Ghi lại nếu tìm thấy
        if found:
            with open(PROXY_BLACKLIST_FILE, "w", encoding="utf-8") as f:
                for proxy in blacklist:
                    f.write(f"{proxy}\n")
            
            print(f"✅ Đã xóa {proxy_key} khỏi blacklist")
            return True
        else:
            print(f"⚠️ Không tìm thấy {proxy_key} trong blacklist")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa khỏi blacklist: {e}")
        return False


def is_proxy_blacklisted(proxy_info):
    """Kiểm tra xem proxy có trong blacklist không"""
    try:
        proxy_key = f"{proxy_info['host']}:{proxy_info['port']}"
        
        try:
            with open(PROXY_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if proxy_key in line.strip():
                        return True
        except FileNotFoundError:
            pass
        
        return False
        
    except:
        return False