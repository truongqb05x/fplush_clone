import time
import random
import requests
import json
import os

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import config

PROXY_FILE = "resources/proxy.txt"
MAX_RETRY = 5
UA_FILE = "resources/useragent.txt"

# Thêm file để lưu proxy blacklist
PROXY_BLACKLIST_FILE = "resources/proxy_blacklist.txt"

# File để lưu proxy đã xóa (có thể tái sử dụng khi proxy file rỗng)
PROXY_DELETED_FILE = "resources/proxy_deleted.txt"


def load_user_agents():
    uas = []
    try:
        if os.path.exists(UA_FILE):
            with open(UA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    ua = line.strip()
                    if ua:
                        uas.append(ua)
        elif getattr(config, 'RESOURCE_LOGGING', True):
            print("⚠️ Không tìm thấy useragent.txt")
    except Exception as e:
        if getattr(config, 'RESOURCE_LOGGING', True):
            print(f"⚠️ Lỗi đọc useragent.txt: {e}")
    return uas


def get_random_ua(uas):
    if not uas:
        return None
    ua = random.choice(uas)
    print(f"🎭 User-Agent: {ua}")
    return ua


def load_proxies():
    """Tải danh sách proxy từ file, loại bỏ proxy đã bị blacklist. Nếu file rỗng, tái sử dụng proxy đã xóa"""
    all_proxies = []
    
    try:
        # Tải blacklist nếu có
        blacklist = set()
        if os.path.exists(PROXY_BLACKLIST_FILE):
            try:
                with open(PROXY_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            blacklist.add(line)
            except:
                pass
        
        # Tải proxy từ file chính
        proxy_found = False
        if os.path.exists(PROXY_FILE):
            with open(PROXY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    proxy_found = True
                    # Kiểm tra xem proxy có trong blacklist không
                    proxy_parts = line.split(":")
                    if len(proxy_parts) >= 2:
                        proxy_key = f"{proxy_parts[0]}:{proxy_parts[1]}"
                        if proxy_key in blacklist:
                            print(f"⏭️ Bỏ qua proxy blacklisted: {proxy_key}")
                            continue
                    
                    if len(proxy_parts) >= 4:
                        host, port, user, pwd = proxy_parts[0:4]
                        all_proxies.append({
                            "host": host,
                            "port": port,
                            "user": user,
                            "pass": pwd
                        })
        
        if not all_proxies and not proxy_found:
            if getattr(config, 'RESOURCE_LOGGING', True):
                print("⚠️ Không tìm thấy proxy.txt")
    
    except Exception as e:
        if getattr(config, 'RESOURCE_LOGGING', True):
            print(f"❌ Lỗi tải proxy: {e}")
    
    return all_proxies


def get_sequential_proxy(proxies, last_proxy_index):
    """Lấy proxy theo thứ tự tuần tự (round-robin)"""
    if not proxies:
        return None, last_proxy_index
    
    # Tính index tiếp theo
    next_index = (last_proxy_index + 1) % len(proxies)
    proxy = proxies[next_index]
    
    print(f"🎲 Chọn proxy ({next_index + 1}/{len(proxies)}): {proxy['host']}:{proxy['port']}")
    return proxy, next_index


def get_real_ip():
    try:
        return requests.get("https://icanhazip.com", timeout=8).text.strip()
    except:
        return "UNKNOWN"


def build_chrome_options(user_data_dir=None, window_pos=None, user_agent=None):
    chrome_options = Options()
    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--profile-directory=Default")

    chrome_options.page_load_strategy = "eager"
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    
    # Cấu hình cửa sổ thu nhỏ & vị trí nếu có
    if window_pos:
        x, y, w, h = window_pos
        chrome_options.add_argument(f"--window-position={x},{y}")
        chrome_options.add_argument(f"--window-size={w},{h}")
    else:
        chrome_options.add_argument("--start-maximized")

    # ===== USER AGENT =====
    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent}")
    else:
        # Fallback logic cũ (Random) nếu không truyền vào
        uas = load_user_agents()
        if uas:
            ua = get_random_ua(uas)
            if ua:
                chrome_options.add_argument(f"--user-agent={ua}")

    # Tùy chọn load hình ảnh để tiết kiệm băng thông/tăng tốc
    load_images = getattr(config, 'LOAD_IMAGES', False)
    images_val = 1 if load_images else 2 # 1: Allow, 2: Block
    
    prefs = {
        "profile.managed_default_content_settings.images": images_val,
        "profile.managed_default_content_settings.videos": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)

    return chrome_options

def get_service():
    """Lấy Service object, ưu tiên path thủ công từ config nếu có"""
    manual_path = getattr(config, 'CHROMEDRIVER_PATH', None)
    if manual_path:
        # Nếu là đường dẫn tương đối, ghép với thư mục gốc của tool
        if not os.path.isabs(manual_path):
            project_root = os.getcwd()
            manual_path = os.path.join(project_root, manual_path)
            
        if os.path.exists(manual_path):
            print(f"🚀 Sử dụng chromedriver thủ công: {manual_path}")
            return Service(executable_path=manual_path)
        else:
            print(f"⚠️ Cảnh báo: File CHROMEDRIVER_PATH không tồn tại: {manual_path}")
            
    return Service(ChromeDriverManager().install())

def create_driver(user_data_dir=None, proxy_config=None, window_pos=None, user_agent=None):
    """
    Tạo driver với proxy, window pos và user_agent cụ thể.
    proxy_config là dict: {"host":..., "port":..., "user":..., "pass":...}
    """
    
    # Nếu không truyền proxy_config, thử lấy ngẫu nhiên (logic cũ fallback)
    if not proxy_config:
        proxies = load_proxies()
        if proxies:
            proxy_config = random.choice(proxies)

    seleniumwire_options = None
    if proxy_config:
        seleniumwire_options = {
            "proxy": {
                "http": f"http://{proxy_config['user']}:{proxy_config['pass']}@{proxy_config['host']}:{proxy_config['port']}",
                "https": f"http://{proxy_config['user']}:{proxy_config['pass']}@{proxy_config['host']}:{proxy_config['port']}",
            },
            "verify_ssl": False,
            "connection_timeout": 20,
            "request_timeout": 20
        }
    
    try:
        service = get_service()
        options = build_chrome_options(user_data_dir, window_pos, user_agent)
        
        if seleniumwire_options:
            driver = webdriver.Chrome(
                service=service,
                seleniumwire_options=seleniumwire_options,
                options=options
            )
        else:
            driver = webdriver.Chrome(
                service=service,
                options=options
            )
            
        driver.set_page_load_timeout(45)
        wait = WebDriverWait(driver, 20)
        return driver, wait, proxy_config
        
    except OSError as e:
        if "193" in str(e):
            print("\n" + "!"*50)
            print("❌ LỖI [WinError 193]: %1 is not a valid Win32 application")
            print("👉 Nguyên nhân: Bản Chromedriver tự động tải về không khớp kiến trúc VPS (32/64 bit).")
            print("👉 Cách xử lý: Tải Chromedriver thủ công fit với bản Chrome trên VPS,")
            print("   sau đó copy đường dẫn vào CHROMEDRIVER_PATH trong config/config.py")
            print("!"*50 + "\n")
        raise e
    except Exception as e:
        print(f"❌ Lỗi khởi tạo driver: {e}")
        raise e
