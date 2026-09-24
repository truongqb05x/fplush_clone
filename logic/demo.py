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

def run_account_flow(cookie_line, target_uid, flow_type, window_index, sync_events):
    parts = cookie_line.split("|")
    uid = parts[0]
    password = parts[1] if len(parts) > 1 else ""
    cookie_str = "|".join(parts[2:]) if len(parts) > 2 else ""
    
    print(f"[Thread-{flow_type}] Bắt đầu tài khoản UID: {uid}")
    
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
            
    print(f"[Thread-{flow_type}] Proxy: {proxy_str if proxy_str else 'Direct'}")
    
    profile_path = get_profile_path(uid)
    win_pos = get_window_pos(window_index)
    
    try:
        driver, wait, _ = create_driver(
            user_data_dir=profile_path,
            proxy_config=proxy_config,
            window_pos=win_pos,
            user_agent=user_agent
        )
        
        driver.get("https://www.facebook.com/")
        print(f"[Thread-{flow_type}] Kiểm tra login...")
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
            print(f"[Thread-{flow_type}] Đã lưu phiên đăng nhập!")
        else:
            print(f"[Thread-{flow_type}] Nạp cookie mới...")
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
            print(f"[Thread-{flow_type}] Cookie lỗi, thử MK...")
            if password:
                from actions.login import login_with_credentials
                login_with_credentials(driver, uid, password)
                time.sleep(5)
                login_verified = verify_uid(driver, uid)
        
        if login_verified:
            print(f"[Thread-{flow_type}] Xác minh login thành công.")
        else:
            print(f"[Thread-{flow_type}] Không thể login, dừng luồng này.")
            return
            
        time.sleep(random.randint(5, 10))
        
        target_url = f"https://www.facebook.com/{target_uid}"
        print(f"[Thread-{flow_type}] Truy cập {target_url}...")
        driver.get(target_url)
        time.sleep(random.randint(5, 8))
        
        try:
            print(f"[Thread-{flow_type}] Kiểm tra trạng thái bạn bè...")
            friends_xpath = "//div[starts-with(@aria-label, 'Bạn bè') or starts-with(@aria-label, 'Friends') or contains(@aria-label, 'Bạn bè')]"
            is_friends = driver.find_elements(By.XPATH, friends_xpath)
            
            if is_friends:
                print(f"[Thread-{flow_type}] Đã là bạn bè.")
                if flow_type == "sender":
                    sync_events['sender_added'].set()
                elif flow_type == "receiver":
                    sync_events['receiver_accepted'].set()
            else:
                if flow_type == "sender":
                    print(f"[Thread-{flow_type}] Kiểm tra kết bạn...")
                    cancel_req_xpath = "//div[starts-with(@aria-label, 'Cancel Request') or starts-with(@aria-label, 'Cancel request') or starts-with(@aria-label, 'Hủy lời mời')]"
                    cancel_req_btns = driver.find_elements(By.XPATH, cancel_req_xpath)
                    
                    if cancel_req_btns:
                        print(f"[Thread-{flow_type}] Đã gửi lời mời từ trước.")
                    else:
                        print(f"[Thread-{flow_type}] Nhấn nút Kết bạn...")
                        add_friend_xpath = "//div[starts-with(@aria-label, 'Add Friend') or starts-with(@aria-label, 'Thêm bạn bè') or starts-with(@aria-label, 'Kết bạn với')]"
                        add_friend_btns = driver.find_elements(By.XPATH, add_friend_xpath)
                        if add_friend_btns:
                            driver.execute_script("arguments[0].click();", add_friend_btns[0])
                            print(f"[Thread-{flow_type}] Đã nhấn Kết bạn. Chờ 10s...")
                            time.sleep(10)
                        else:
                            print(f"[Thread-{flow_type}] Không tìm thấy nút Kết bạn (có thể bị ẩn). Bỏ qua...")
                    sync_events['sender_added'].set()
                        
                elif flow_type == "receiver":
                    print(f"[Thread-{flow_type}] Đang chờ người gửi kết bạn (tối đa 2 phút)...")
                    sync_events['sender_added'].wait(timeout=120)
                    print(f"[Thread-{flow_type}] Kiểm tra xem có lời mời không...")
                    for attempt in range(3):
                        confirm_req_xpath = "//div[starts-with(@aria-label, 'Xác nhận lời mời') or starts-with(@aria-label, 'Confirm')]"
                        confirm_req_btns = driver.find_elements(By.XPATH, confirm_req_xpath)
                        if confirm_req_btns:
                            print(f"[Thread-{flow_type}] Đang xác nhận kết bạn...")
                            driver.execute_script("arguments[0].click();", confirm_req_btns[0])
                            time.sleep(3)
                            break
                        else:
                            if attempt < 2:
                                print(f"[Thread-{flow_type}] Chưa thấy lời mời, F5 và chờ thêm...")
                                time.sleep(10)
                                driver.refresh()
                                time.sleep(8)
                            else:
                                print(f"[Thread-{flow_type}] Không có lời mời cần xác nhận sau nhiều lần thử.")
                    sync_events['receiver_accepted'].set()

            if flow_type == "sender":
                print(f"[Thread-{flow_type}] Đang chờ người nhận xác nhận kết bạn (tối đa 2 phút)...")
                sync_events['receiver_accepted'].wait(timeout=120)
            elif flow_type == "receiver":
                print(f"[Thread-{flow_type}] Đang chờ người gửi hoàn tất tin nhắn (tối đa 2 phút)...")
                sync_events['sender_msg_sent'].wait(timeout=120)
                print(f"[Thread-{flow_type}] Bắt đầu kiểm tra khung chat...")

            chat_box_xpath = "//div[@role='textbox' and (contains(@aria-label, 'Write to') or contains(@aria-label, 'Viết cho') or contains(@aria-label, 'Message') or contains(@aria-label, 'Nhắn tin'))]"
            try:
                # Kiểm tra xem khung chat có tự động bật lên chưa
                chat_box = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, chat_box_xpath)))
                print(f"[Thread-{flow_type}] Khung chat đã có sẵn trên màn hình.")
            except:
                print(f"[Thread-{flow_type}] Đang tìm và nhấn nút Nhắn tin...")
                msg_xpath = "//div[@aria-label='Message' or @aria-label='Nhắn tin']"
                msg_btn = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, msg_xpath)))
                driver.execute_script("arguments[0].click();", msg_btn)
                print(f"[Thread-{flow_type}] Đã nhấn nút Nhắn tin. Chờ khung chat...")
                time.sleep(5)
                chat_box = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, chat_box_xpath)))
            
            chat_box.click()
            
            import string
            demo_msg = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
            
            print(f"[Thread-{flow_type}] Đang gõ: {demo_msg}")
            for char in demo_msg:
                chat_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
                
            time.sleep(1)
            max_retries = 3
            msg_displayed = False
            
            for attempt in range(1, max_retries + 1):
                print(f"[Thread-{flow_type}] Đang ấn Gửi... ({attempt}/{max_retries})")
                try:
                    send_btn_xpath = "//div[@aria-label='Press enter to send' or @aria-label='Nhấn Enter để gửi']"
                    send_btn = driver.find_element(By.XPATH, send_btn_xpath)
                    driver.execute_script("arguments[0].click();", send_btn)
                except:
                    from selenium.webdriver.common.keys import Keys
                    chat_box.send_keys(Keys.ENTER)
                    
                sent_msg_xpath = f"//*[contains(text(), '{demo_msg}')]"
                try:
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, sent_msg_xpath)))
                    print(f"[Thread-{flow_type}] [+] Đã gửi thành công!")
                    msg_displayed = True
                    if flow_type == "sender":
                        sync_events['sender_msg_sent'].set()
                    break
                except Exception:
                    print(f"[Thread-{flow_type}] [-] Chưa thấy tin nhắn sau 30s.")
            
            if not msg_displayed:
                print(f"[Thread-{flow_type}] [-] Gửi thất bại sau 3 lần thử.")
                if flow_type == "sender":
                    sync_events['sender_msg_sent'].set()

        except Exception as e:
            print(f"[Thread-{flow_type}] Lỗi trong luồng: {e}")
            
        print(f"[Thread-{flow_type}] Đã hoàn tất luồng tự động.")
        while True:
            _ = driver.window_handles
            time.sleep(5)
            
    except Exception as e:
        print(f"[Thread-{flow_type}] Lỗi hoặc trình duyệt đóng: {e}")


def main():
    print("--- Bắt đầu Demo 2 Luồng Đồng Thời ---")
    
    acc_file = config.COOKIE_FILE
    if not os.path.exists(acc_file):
        print(f"Lỗi: Không tìm thấy file {acc_file}")
        return
        
    with open(acc_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        
    if len(lines) < 2:
        print("Lỗi: Cần ít nhất 2 tài khoản trong file account.txt để demo luồng gửi-nhận.")
        return
        
    acc1 = lines[0]
    acc2 = lines[1]
    
    uid1 = acc1.split("|")[0]
    uid2 = acc2.split("|")[0]
    
    print(f"[*] Account 1 (Người gửi): {uid1}")
    print(f"[*] Account 2 (Người nhận): {uid2}")
    
    sync_events = {
        'sender_added': threading.Event(),
        'receiver_accepted': threading.Event(),
        'sender_msg_sent': threading.Event()
    }
    
    # Mở 2 luồng
    t1 = threading.Thread(target=run_account_flow, args=(acc1, uid2, "sender", 0, sync_events))
    t2 = threading.Thread(target=run_account_flow, args=(acc2, uid1, "receiver", 1, sync_events))
    
    t1.start()
    # Chờ 1 chút để lệch nhịp mở trình duyệt
    time.sleep(5)
    t2.start()
    
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("\n[*] Dừng chương trình từ bàn phím.")

if __name__ == "__main__":
    main()
