import time
import os
import random
import base64
import logging
import threading

# Ẩn các log lỗi ồn ào của seleniumwire (mitmproxy)
logging.getLogger('seleniumwire').setLevel(logging.CRITICAL)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.driver_utils import create_driver, load_proxies
from config import config

from utils.account_registry import (
    load_proxy_mapping, get_assigned_ua,
    get_assigned_proxy, parse_proxy_str,
    load_kiot_mapping, get_assigned_kiot
)
from utils.kiot_proxy import get_new_kiot_proxy, parse_kiot_proxy_string

# Cấu hình cửa sổ
WIN_WIDTH = 500
WIN_HEIGHT = 700

def get_window_pos(index):
    # Cửa sổ thứ index sẽ nằm cạnh nhau
    return (index * WIN_WIDTH, 0, WIN_WIDTH, WIN_HEIGHT)

def get_profile_path(uid):
    profile_dir = getattr(config, "PROFILE_DIR", "profiles")
    if not os.path.isabs(profile_dir):
        profile_dir = os.path.join(os.getcwd(), profile_dir)
    return os.path.join(profile_dir, uid)

def run_account_flow(cookie_line):
    parts = cookie_line.split("|")
    uid = parts[0]
    password = parts[1] if len(parts) > 1 else ""
    cookie_str = "|".join(parts[2:]) if len(parts) > 2 else ""
    
    print(f"[Account-{uid}] Bắt đầu tài khoản UID: {uid}")
    
    user_agent = None
    actual_cookies = []
    for c in cookie_str.split(";"):
        c = c.strip()
        if not c: continue
        if "=" in c:
            k, v = c.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k.lower() == "useragent":
                try:
                    user_agent = base64.b64decode(v).decode('utf-8')
                except:
                    user_agent = v
            else:
                actual_cookies.append({"name": k, "value": v})
                    
    if not user_agent:
        import utils.account_registry as ar
        mapping_ua = ar.load_ua_mapping()
        user_agent = get_assigned_ua(uid, mapping_ua)
        
    proxy_config = None
    proxy_str = None
    kiot_keys = []
    kiot_file = getattr(config, "KIOT_FILE", "resources/kiot.txt")
    if os.path.exists(kiot_file):
        with open(kiot_file, "r", encoding="utf-8") as f:
            kiot_keys = [l.strip() for l in f if l.strip()]
            
    if kiot_keys:
        mapping_kiot = load_kiot_mapping()
        assigned_kiot_key = get_assigned_kiot(uid, kiot_keys, mapping_kiot)
        if assigned_kiot_key:
            kiot_proxy_str = get_new_kiot_proxy(assigned_kiot_key)
            if kiot_proxy_str:
                proxy_config = parse_kiot_proxy_string(kiot_proxy_str)
                proxy_str = kiot_proxy_str

    if not proxy_config:
        mapping_proxy = load_proxy_mapping()
        all_proxies = load_proxies()
        proxy_str = get_assigned_proxy(uid, all_proxies, mapping_proxy)
        if proxy_str:
            proxy_config = parse_proxy_str(proxy_str)
            
    print(f"[Account-{uid}] Proxy: {proxy_str if proxy_str else 'Direct'}")
    
    profile_path = get_profile_path(uid)
    win_pos = get_window_pos(0)
    
    try:
        driver, wait, _ = create_driver(
            user_data_dir=profile_path,
            proxy_config=proxy_config,
            window_pos=win_pos,
            user_agent=user_agent
        )
        
        driver.get("https://www.facebook.com/")
        print(f"[Account-{uid}] Kiểm tra login...")
        time.sleep(5)
        
        current_cookies = driver.get_cookies()
        has_c_user = any(c['name'] == 'c_user' and uid in str(c['value']) for c in current_cookies)
                
        is_logged_in = False
        if has_c_user:
            try:
                login_els = driver.find_elements(By.NAME, "login") or driver.find_elements(By.ID, "loginbutton") or driver.find_elements(By.XPATH, "//*[text()='Đăng nhập' or text()='Log In']")
                if not login_els:
                    is_logged_in = True
            except: pass
            
        if is_logged_in:
            print(f"[Account-{uid}] Đã lưu phiên đăng nhập!")
        else:
            print(f"[Account-{uid}] Nạp cookie mới...")
            expiry_time = int(time.time()) + (365 * 24 * 3600)
            for cookie_dict in actual_cookies:
                try: 
                    cookie_dict["domain"] = ".facebook.com"
                    cookie_dict["path"] = "/"
                    cookie_dict["expiry"] = expiry_time
                    driver.add_cookie(cookie_dict)
                except:
                    pass
            driver.refresh()
            time.sleep(8)
            
        def verify_uid(dr, t_uid):
            curr_url = dr.current_url or ""
            if t_uid in curr_url or f"profile.php?id={t_uid}" in curr_url or "/me" in curr_url: return True
            cookies = dr.get_cookies()
            if any(c['name'] == 'c_user' and str(c['value']) == str(t_uid) for c in cookies): return True
            ps = dr.page_source
            if f'\"userID\":\"{t_uid}\"' in ps or f'\"ACCOUNT_ID\":\"{t_uid}\"' in ps: return True
            return False

        login_verified = verify_uid(driver, uid)
        if not login_verified:
            driver.get("https://www.facebook.com/me")
            time.sleep(5)
            login_verified = verify_uid(driver, uid)
            
        if not login_verified:
            print(f"[Account-{uid}] Cookie lỗi, thử MK...")
            if password:
                from actions.login import login_with_credentials
                login_with_credentials(driver, uid, password)
                time.sleep(5)
                login_verified = verify_uid(driver, uid)
        
        if login_verified:
            print(f"[Account-{uid}] Xác minh login thành công.")
        else:
            print(f"[Account-{uid}] Không thể login, dừng luồng này.")
            return
            
        try:
            # Kiểm tra ngôn ngữ hiện tại của trang
            current_lang = driver.execute_script("return document.documentElement.lang;")
            print(f"[Account-{uid}] Ngôn ngữ hiện tại của trang web: {current_lang}")
            
            if current_lang and current_lang.startswith("en"):
                print(f"[Account-{uid}] Bắt đầu tiến trình đổi ngôn ngữ sang Tiếng Việt...")
                
                def do_click(xpath, fallback_texts=None):
                    end_time = time.time() + 60
                    while time.time() < end_time:
                        try:
                            # 1. Thử dùng XPath
                            elements = driver.find_elements(By.XPATH, xpath)
                            for el in elements:
                                try:
                                    if el.is_displayed() or el.get_attribute("aria-hidden") == "false" or True: # execute_script bỏ qua is_displayed
                                        driver.execute_script("arguments[0].click();", el)
                                        time.sleep(1) # Đợi 1 chút cho menu bung ra
                                        return
                                except:
                                    pass
                            
                            # 2. Fallback dùng JS tìm bằng chữ
                            if fallback_texts:
                                success = driver.execute_script("""
                                    var texts = arguments[0];
                                    var els = document.querySelectorAll('span, div');
                                    for(var i=0; i<els.length; i++) {
                                        var text = els[i].innerText;
                                        if (text && els[i].children.length === 0) { // Lấy element chứa chữ cuối cùng
                                            text = text.trim();
                                            for(var j=0; j<texts.length; j++) {
                                                if (text === texts[j] || text.includes(texts[j])) {
                                                    els[i].click();
                                                    return true;
                                                }
                                            }
                                        }
                                    }
                                    return false;
                                """, fallback_texts)
                                if success:
                                    time.sleep(1)
                                    return
                        except Exception:
                            pass
                        time.sleep(1)
                    raise Exception(f"Không thể click vào phần tử: {fallback_texts if fallback_texts else xpath} sau 60s")

                # 1. Tìm nút Account / Your profile và click
                print(f"[Account-{uid}] Đang chờ và nhấn vào avatar menu...")
                do_click("//div[@role='button' and (contains(@aria-label, 'Your profile') or contains(@aria-label, 'Trang cá nhân của bạn') or contains(@aria-label, 'Account') or contains(@aria-label, 'Tài khoản'))]")
                
                # 2. Tìm và click Cài đặt
                print(f"[Account-{uid}] Đang chờ và nhấn vào 'Settings & privacy'...")
                do_click("//span[contains(text(), 'Settings & privacy') or contains(text(), 'Cài đặt & quyền riêng tư') or text()='Cài đặt' or text()='Settings']", ["Settings & privacy", "Cài đặt & quyền riêng tư", "Cài đặt", "Settings"])
                
                # 3. Tìm và click Ngôn ngữ
                print(f"[Account-{uid}] Đang chờ và nhấn vào 'Language'...")
                do_click("//span[contains(text(), 'Language') or contains(text(), 'Ngôn ngữ')]", ["Language", "Ngôn ngữ"])
                
                # 4. Tìm và click Facebook Language
                print(f"[Account-{uid}] Đang chờ và nhấn vào 'Facebook Language'...")
                do_click("//span[contains(text(), 'Facebook Language') or contains(text(), 'Ngôn ngữ trên Facebook') or contains(text(), 'Ngôn ngữ của Facebook')]", ["Facebook Language", "Ngôn ngữ trên Facebook", "Ngôn ngữ của Facebook"])
                
                # 5. Chọn Tiếng Việt
                print(f"[Account-{uid}] Đang chờ và chọn 'Tiếng Việt'...")
                do_click("//span[text()='Tiếng Việt' or contains(text(), 'Tiếng Việt')]", ["Tiếng Việt"])
                
                # Chờ trang ổn định và kiểm tra lại (tối đa 30s)
                print(f"[Account-{uid}] Đang đợi trang web tải lại (tối đa 30s) để xác nhận...")
                try:
                    WebDriverWait(driver, 30).until(
                        lambda d: d.execute_script("return document.documentElement.lang;") and d.execute_script("return document.documentElement.lang;").startswith("vi")
                    )
                    print(f"[Account-{uid}] => THÀNH CÔNG: Giao diện đã đổi thành Tiếng Việt!")
                except Exception:
                    final_lang = driver.execute_script("return document.documentElement.lang;")
                    if final_lang and final_lang.startswith("vi"):
                        print(f"[Account-{uid}] => THÀNH CÔNG: Giao diện đã đổi thành Tiếng Việt!")
                    else:
                        print(f"[Account-{uid}] => THẤT BẠI: Hết 30s chờ nhưng ngôn ngữ vẫn là {final_lang}.")
                        
            elif current_lang and current_lang.startswith("vi"):
                print(f"[Account-{uid}] Trang web đã là Tiếng Việt, không cần đổi.")
            else:
                print(f"[Account-{uid}] Ngôn ngữ không phải tiếng Anh ({current_lang}), bỏ qua bước đổi.")
                
        except Exception as ex:
            print(f"[Account-{uid}] Lỗi khi thao tác đổi ngôn ngữ: {ex}")
        time.sleep(10)
        print(f"[Account-{uid}] Đã hoàn tất logic.")
        input(f"\n[Account-{uid}] >>> Trình duyệt đang được giữ mở. NHẤN ENTER TẠI ĐÂY (cmd) ĐỂ KẾT THÚC... <<<\n")
        print(f"[Account-{uid}] Đang đóng trình duyệt...")
        driver.quit()
        
    except Exception as e:
        print(f"[Account-{uid}] Lỗi hoặc trình duyệt đóng: {e}")
        try:
            driver.quit()
        except:
            pass

def main():
    print("--- Bắt đầu Demo ---")
    acc_file = getattr(config, 'COOKIE_FILE', "resources/account.txt")
    
    try:
        with open(acc_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            
        if not lines:
            return print("Lỗi: File account trống.")
            
        # Chạy trực tiếp không cần tạo Thread
        run_account_flow(lines[0])
        
    except KeyboardInterrupt:
        print("\n[*] Dừng chương trình từ bàn phím.")
    except Exception as e:
        print(f"Lỗi khởi chạy: {e}")
    finally:
        print("[*] Đóng toàn bộ tiến trình...")
        os._exit(0)

if __name__ == "__main__":
    main()
