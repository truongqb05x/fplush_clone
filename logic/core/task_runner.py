# -*- coding: utf-8 -*-
"""
Main Script: FB Spam Comment Group with Multi-threading & Persistent Proxies
"""
import time
import shutil
import os
import random
import json
import base64
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By

KIOT_PROXY_LOCK = threading.Lock()
KIOT_PROXY_CACHE = {}

from utils.helpers import (
    is_checkpoint, is_soft_checkpoint, safe_url, cleanup_seleniumwire
)
from utils.driver_utils import create_driver, load_proxies
from utils.file_utils import read_file
from config import config
from utils.scan_group import get_joined_groups

# Modular imports
from utils.locks import FILE_LOCK
from utils.account_registry import (
    load_proxy_mapping, save_proxy_mapping,
    load_ua_mapping, get_assigned_ua,
    get_assigned_proxy, parse_proxy_str,
    load_kiot_mapping, get_assigned_kiot
)
from utils.kiot_proxy import get_new_kiot_proxy, parse_kiot_proxy_string
from core.automation_service import process_group_cycle, process_keyword_search, process_page_cycle, process_ttc_cycle
from actions.feed_actions import warm_up_account
from actions.login import login_with_credentials
from actions.join_groups import join_single_group
from actions.out_group import out_groups_by_mode
from actions.TTC.get_job import fetch_ttc_jobs
from actions.read_notifications import read_one_random_notification
from actions.chat_two_ways import run_two_way_chat


from core.globals import *
from core.helpers import get_profile_path, remove_dead_account
from core.mode_handlers import dispatch_execution_mode

def run_account_task(cookie_line, thread_index, max_comments, is_edit_comment="yes", execution_mode=1, warmup_time_sec=None, keyword_list=None, group_join_list=None, out_group_mode=None, out_group_list=None, page_list=None, page_comment_mode="text", delete_page_after_comment=True, ttc_jobs=None, ttc_comment_mode="text", cycle_count=1, task_config=None):
    driver = None
    is_dead = False
    try:
        parts = cookie_line.split("|")
        uid = parts[0]
        
        # Bỏ qua tài khoản nếu đã bị block tính năng ở lượt chạy trước trong phiên chạy này
        if execution_mode == 1 and uid in BLOCKED_ACCOUNTS:
            print(f"[{uid}]  Tài khoản này đã bị chặn tính năng ở lượt chạy trước trong phiên này. Bỏ qua.")
            return "SKIPPED_BLOCKED"

        cookie_str = "|".join(parts[2:]) if len(parts) > 2 else ""
        
        # Vị trí cửa sổ
        win_pos = get_window_pos(thread_index)
        
        # --- XỬ LÝ USER-AGENT TỪ COOKIE LINE ---
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
                        # Thử giải mã Base64 (vì account.txt thường encode UA)
                        user_agent = base64.b64decode(v).decode('utf-8')
                        print(f"[{uid}]  Đã giải mã UA từ file account: {user_agent[:50]}...")
                    except:
                        user_agent = v
                        print(f"[{uid}]  Sử dụng UA thô từ file account.")
                else:
                    actual_cookies.append({"name": k, "value": v})
        
        # Nếu dòng account không có UA, dùng mapping cũ hoặc random
        if not user_agent:
            mapping_ua = load_ua_mapping()
            user_agent = get_assigned_ua(uid, mapping_ua)
        
        # Proxy handling
        proxy_config = None
        proxy_str = None
        proxy_field = parts[5].strip() if len(parts) > 5 else ""

        # Ưu tiên: dùng proxy từ task_config (cài đặt Settings UI) nếu execution_mode == 1
        if execution_mode == 1 and task_config:
            proxy_method = task_config.get("ProxyMethod", 0)
            if proxy_method == 1:  # Tĩnh
                proxy_list = task_config.get("ProxyList", [])
                if proxy_list:
                    # Phân phối round-robin theo thứ tự của task_config["SelectedAccounts"]
                    selected_accounts = task_config.get("SelectedAccounts", [])
                    try:
                        acc_index = selected_accounts.index(uid)
                    except ValueError:
                        acc_index = 0
                    proxy_str = proxy_list[acc_index % len(proxy_list)]
                    proxy_config = parse_proxy_str(proxy_str)
                    # print(f"[{uid}]  [Settings] Sử dụng proxy tĩnh từ cài đặt: {proxy_str}")
            elif proxy_method == 2:  # KiotProxy
                kiot_key = task_config.get("KiotProxyKey", "")
                is_reset_dcom = task_config.get("IsResetDcom", False)
                reset_dcom_after = task_config.get("ResetDcomAfter", 2)
                if kiot_key:
                    kiot_proxy_str = None
                    with KIOT_PROXY_LOCK:
                        cached = KIOT_PROXY_CACHE.get(kiot_key)
                        need_new = False
                        
                        if not cached:
                            need_new = True
                        else:
                            if not is_reset_dcom:
                                need_new = False
                            else:
                                if cached.get("last_turn") != cycle_count:
                                    turns_used = cached.get("turns_used", 1)
                                    if turns_used >= reset_dcom_after:
                                        need_new = True
                                    else:
                                        cached["last_turn"] = cycle_count
                                        cached["turns_used"] = turns_used + 1
                                        need_new = False
                                else:
                                    need_new = False

                        if need_new:
                            kiot_proxy_str = get_new_kiot_proxy(kiot_key)
                            if kiot_proxy_str:
                                KIOT_PROXY_CACHE[kiot_key] = {
                                    "proxy": kiot_proxy_str, 
                                    "last_turn": cycle_count,
                                    "turns_used": 1
                                }
                        else:
                            kiot_proxy_str = cached.get("proxy") if cached else None

                    if kiot_proxy_str:
                        proxy_config = parse_kiot_proxy_string(kiot_proxy_str)
                        proxy_str = kiot_proxy_str
                        # print(f"[{uid}]  [Settings] Sử dụng KiotProxy từ cài đặt: {kiot_proxy_str[:30]}...")
            else:  # proxy_method == 0 hoặc không xác định → không dùng proxy
                proxy_config = None
                proxy_str = None
                proxy_field = ""  # Đặt proxy_field rỗng để bỏ qua fallback phía dưới
                # print(f"[{uid}]  [Settings] Không sử dụng proxy (Direct connection).")
        
        # Chỉ xử lý proxy theo cách cũ nếu chưa được gán từ Settings UI
        if not (execution_mode == 1 and task_config and task_config.get("ProxyMethod", 0) in (0, 1, 2)):
            pass  # Đã xử lý bên trên
        elif not proxy_config and proxy_field:
            if ":" not in proxy_field and len(proxy_field) > 10:
                # Kiot Proxy Key provided from UI
                assigned_kiot_key = proxy_field
                kiot_proxy_str = None
                with KIOT_PROXY_LOCK:
                    cached = KIOT_PROXY_CACHE.get(assigned_kiot_key)
                    
                    is_reset_dcom = False
                    reset_dcom_after = 2
                    if task_config:
                        is_reset_dcom = task_config.get("IsResetDcom", False)
                        reset_dcom_after = task_config.get("ResetDcomAfter", 2)
                        
                    need_new = False
                    if not cached:
                        need_new = True
                    else:
                        if not is_reset_dcom:
                            need_new = False
                        else:
                            if cached.get("last_turn") != cycle_count:
                                turns_used = cached.get("turns_used", 1)
                                if turns_used >= reset_dcom_after:
                                    need_new = True
                                else:
                                    cached["last_turn"] = cycle_count
                                    cached["turns_used"] = turns_used + 1
                                    need_new = False
                            else:
                                need_new = False

                    if need_new:
                        kiot_proxy_str = get_new_kiot_proxy(assigned_kiot_key)
                        if kiot_proxy_str:
                            KIOT_PROXY_CACHE[assigned_kiot_key] = {
                                "proxy": kiot_proxy_str, 
                                "last_turn": cycle_count,
                                "turns_used": 1
                            }
                    else:
                        kiot_proxy_str = cached.get("proxy") if cached else None
                        print(f"[{uid}]  Dùng chung proxy Kiot đã lấy cho key {assigned_kiot_key[:10]} (Turn {cycle_count})")

                if kiot_proxy_str:
                    proxy_config = parse_kiot_proxy_string(kiot_proxy_str)
                    proxy_str = kiot_proxy_str
            else:
                # Static proxy provided from UI
                proxy_str = proxy_field
                proxy_config = parse_proxy_str(proxy_str)
        elif not (execution_mode == 1 and task_config):
            # Fallback to old file mapping if no proxy passed from UI (chế độ cũ)
            kiot_keys = []
            kiot_file = getattr(config, "KIOT_FILE", "resources/kiot.txt")
            if os.path.exists(kiot_file):
                with open(kiot_file, "r", encoding="utf-8") as f:
                    kiot_keys = [l.strip() for l in f if l.strip()]
                    
            if kiot_keys:
                mapping_kiot = load_kiot_mapping()
                assigned_kiot_key = get_assigned_kiot(uid, kiot_keys, mapping_kiot)
                if assigned_kiot_key:
                    kiot_proxy_str = None
                    with KIOT_PROXY_LOCK:
                        cached = KIOT_PROXY_CACHE.get(assigned_kiot_key)
                        
                        is_reset_dcom = False
                        reset_dcom_after = 2
                        if task_config:
                            is_reset_dcom = task_config.get("IsResetDcom", False)
                            reset_dcom_after = task_config.get("ResetDcomAfter", 2)
                            
                        need_new = False
                        if not cached:
                            need_new = True
                        else:
                            if not is_reset_dcom:
                                need_new = False
                            else:
                                if cached.get("last_turn") != cycle_count:
                                    turns_used = cached.get("turns_used", 1)
                                    if turns_used >= reset_dcom_after:
                                        need_new = True
                                    else:
                                        cached["last_turn"] = cycle_count
                                        cached["turns_used"] = turns_used + 1
                                        need_new = False
                                else:
                                    need_new = False

                        if need_new:
                            kiot_proxy_str = get_new_kiot_proxy(assigned_kiot_key)
                            if kiot_proxy_str:
                                KIOT_PROXY_CACHE[assigned_kiot_key] = {
                                    "proxy": kiot_proxy_str, 
                                    "last_turn": cycle_count,
                                    "turns_used": 1
                                }
                        else:
                            kiot_proxy_str = cached.get("proxy") if cached else None
                            print(f"[{uid}]  Dùng chung proxy Kiot đã lấy cho key {assigned_kiot_key[:10]} (Turn {cycle_count})")

                    if kiot_proxy_str:
                        proxy_config = parse_kiot_proxy_string(kiot_proxy_str)
                        proxy_str = kiot_proxy_str

            # Fallback to normal proxy mapping if no kiot proxy
            if not proxy_config:
                mapping_proxy = load_proxy_mapping()
                all_proxies = load_proxies()
                proxy_str = get_assigned_proxy(uid, all_proxies, mapping_proxy)
                proxy_config = parse_proxy_str(proxy_str)
        
        _proxy_display = ":".join((proxy_str or "Direct").split(":")[:2])
        print(f"[{uid}] {_proxy_display}")
        
        for login_attempt in range(2):
            profile_path = get_profile_path(uid)
            # print(f"[{uid}]  Profile Path: {profile_path}")
            if os.path.exists(profile_path):
                if execution_mode == 2:
                    print(f"[{uid}]  Bỏ qua vì Profile đã tồn tại (Chế độ 2).")
                    return "SKIPPED"
                # print(f"[{uid}]  Profile đã tồn tại.")
            else:
                pass # print(f"[{uid}]  Profile chưa tồn tại, đang tạo mới.")
            
            driver, wait, _ = create_driver(
                user_data_dir=profile_path, 
                proxy_config=proxy_config, 
                window_pos=win_pos,
                user_agent=user_agent
            )
            
            # --- SMART LOGIN LOGIC ---
            driver.get("https://www.facebook.com/")
            # print(f"[{uid}]  Đang kiểm tra trạng thái login tại: {driver.current_url}")
            time.sleep(5) # Chờ redirect
            
            current_cookies = driver.get_cookies()
            has_c_user = False
            found_c_user_val = "None"
            for c in current_cookies:
                if c['name'] == 'c_user':
                    found_c_user_val = str(c['value'])
                    if uid in found_c_user_val:
                        has_c_user = True
                        break
            
            is_logged_in = False
            if has_c_user:
                # Nếu có cookie, check xem có bị đá ra trang login không
                try:
                    # Chờ xem có element của người dùng đã login không (ví dụ: aria-label="Facebook")
                    # Nếu thấy nút login hoặc "Đăng nhập" thì chắc chắn là logout
                    login_els = driver.find_elements(By.NAME, "login") or \
                                driver.find_elements(By.ID, "loginbutton") or \
                                driver.find_elements(By.XPATH, "//*[text()='Đăng nhập' or text()='Log In']")
                    
                    if login_els:
                        print(f"[{uid}]  Tìm thấy nút Login dù đã có cookie. Có thể session đã die.")
                    else:
                        is_logged_in = True
                except Exception as e:
                    print(f"[{uid}]  Lỗi khi quét nút login: {e}")
                    pass
            
            if is_logged_in:
                pass # Session cũ vẫn còn hiệu lực
            else:
                # print(f"[{uid}]  Session hết hạn/chưa có (hoặc sai UA). Tiến hành nạp cookie mới...")
                # driver.delete_all_cookies() # Đã ẩn để tránh clear profile vô ích
                # print(f"[{uid}]  Đang nạp {len(actual_cookies)} cookie từ file account (Sẽ thêm Expiry 1 năm)...")
                
                # Tính toán expiry: 1 năm kể từ hiện tại
                expiry_time = int(time.time()) + (365 * 24 * 3600)
                
                for cookie_dict in actual_cookies:
                    try: 
                        cookie_dict["domain"] = ".facebook.com"
                        cookie_dict["path"] = "/"
                        cookie_dict["expiry"] = expiry_time # Ép persistent
                        driver.add_cookie(cookie_dict)
                    except Exception as e_cook:
                        pass
                driver.refresh()
                time.sleep(8)
    
            # Check status sau khi nạp (hoặc dùng session cũ)
            current_url = safe_url(driver)
            
            # --- KIỂM TRA TRẠNG THÁI LOGIN ---
            if execution_mode != 6 and ("checkpoint" in current_url.lower() or is_checkpoint(driver)):
                if is_soft_checkpoint(driver):
                    print(f"[{uid}]  Đã xử lý CHECKPOINT TẠM THỜI (Dismiss). Đang load lại trang...")
                    driver.get("https://www.facebook.com/")
                    time.sleep(5)
                    if is_checkpoint(driver):
                        print(f"[{uid}]  Vẫn còn CHECKPOINT sau khi Dismiss. Bỏ qua tài khoản, KHÔNG xóa.")
                        return "SKIPPED_SOFT_CHECKPOINT"
                    else:
                        print(f"[{uid}]  Đã vượt CHECKPOINT TẠM THỜI thành công, tiếp tục chạy.")
                else:
                    print(f"[{uid}]  PHÁT HIỆN CHECKPOINT CỨNG -> Xóa tài khoản.")
                    print(f"[{uid}] UI_STATUS|Die")
                    is_dead = True
                    return False
    
            # Kiểm tra xem có đúng UID không
            def verify_uid(dr, target_uid):
                curr_url = safe_url(dr)
                # 1. Check URL
                if target_uid in curr_url or f"profile.php?id={target_uid}" in curr_url or "/me" in curr_url:
                    return True
                # 2. Check cookie
                cookies = dr.get_cookies()
                if any(c['name'] == 'c_user' and str(c['value']) == str(target_uid) for c in cookies):
                    return True
                # 3. Check page source
                ps = dr.page_source
                if f'\"userID\":\"{target_uid}\"' in ps or f'\"ACCOUNT_ID\":\"{target_uid}\"' in ps:
                    return True
                return False
    
            # --- XÁC MINH TRẠNG THÁI LOGIN & FALLBACK LOGIN ---
            login_verified = verify_uid(driver, uid)
            
            if not login_verified:
                print(f"[{uid}] 🔎 Chưa xác minh được UID, đang thử chuyển hướng đến /me...")
                driver.get("https://www.facebook.com/me")
                time.sleep(5)
                login_verified = verify_uid(driver, uid)
    
            if not login_verified:
                print(f"[{uid}]  Session hết hạn hoặc UID không khớp. Tiến hành login bằng Username/Password...")
                password = parts[1] if len(parts) > 1 else ""
                if login_with_credentials(driver, uid, password):
                    time.sleep(5)
                    if verify_uid(driver, uid):
                        login_verified = True
                        print(f"[{uid}]  Login và xác minh UID thành công.")
                        try:
                            new_cookies = driver.get_cookies()
                            
                            # Ép cookie thành persistent để profile lưu lại sau khi tắt Chrome
                            expiry_time = int(time.time()) + (365 * 24 * 3600)
                            for c in new_cookies:
                                try:
                                    c_copy = c.copy()
                                    c_copy['expiry'] = expiry_time
                                    driver.add_cookie(c_copy)
                                except:
                                    pass
                                    
                            cookie_pairs = [f"{c['name']}={c['value']}" for c in new_cookies]
                            new_cookie_str = "; ".join(cookie_pairs)
                            
                            if user_agent:
                                import base64
                                ua_b64 = base64.b64encode(user_agent.encode('utf-8')).decode('utf-8')
                                new_cookie_str += f"; useragent={ua_b64}"
                                
                            with FILE_LOCK:
                                acc_file = config.COOKIE_FILE
                                if os.path.exists(acc_file):
                                    with open(acc_file, "r", encoding="utf-8") as f:
                                        lines = f.readlines()
                                    new_lines = []
                                    updated = False
                                    for l in lines:
                                        if l.strip() == cookie_line.strip():
                                            l_parts = l.strip().split("|")
                                            if len(l_parts) >= 3:
                                                l_parts[2] = new_cookie_str
                                                new_line = "|".join(l_parts)
                                                new_lines.append(new_line + "\n")
                                                cookie_line = new_line
                                                updated = True
                                            else:
                                                new_lines.append(l)
                                        else:
                                            new_lines.append(l)
                                    if updated:
                                        with open(acc_file, "w", encoding="utf-8") as f:
                                            f.writelines(new_lines)
                                        print(f"[{uid}]  Đã cập nhật cookie mới vào file.")
                        except Exception as e_upd:
                            print(f"[{uid}]  Lỗi khi cập nhật cookie: {e_upd}")
                    else:
                        print(f"[{uid}]  Đã login nhưng vẫn không xác minh được UID (URL: {safe_url(driver)}). Đang xóa profile để thử lại ngay bây giờ...")
                        try:
                            cleanup_seleniumwire(driver)
                            driver.quit()
                            time.sleep(2)
                            import shutil
                            if os.path.exists(profile_path):
                                shutil.rmtree(profile_path)
                        except Exception as e_del:
                            print(f"[{uid}]  Lỗi khi xóa profile: {e_del}")
                        if login_attempt == 0: continue
                        print(f"[{uid}]  Đã thử lại nhưng vẫn thất bại. Đang xóa tài khoản...")
                        print(f"[{uid}] UI_STATUS|Die")
                        is_dead = True
                        if execution_mode != 6: return False
                else:
                    print(f"[{uid}]  Login bằng credentials thất bại. Đang xóa profile để thử lại ngay bây giờ...")
                    try:
                        cleanup_seleniumwire(driver)
                        driver.quit()
                        time.sleep(2)
                        import shutil
                        if os.path.exists(profile_path):
                            shutil.rmtree(profile_path)
                    except Exception as e_del:
                        print(f"[{uid}]  Lỗi khi xóa profile: {e_del}")
                    if login_attempt == 0: continue
                    print(f"[{uid}]  Đã thử lại nhưng vẫn thất bại. Đang xóa tài khoản...")
                    print(f"[{uid}] UI_STATUS|Die")
                    is_dead = True
                    if execution_mode != 6: return False
            
            if login_verified:
                break

        # Call the dispatcher
        res = dispatch_execution_mode(driver, wait, uid, execution_mode, max_comments, is_edit_comment, warmup_time_sec, keyword_list, group_join_list, out_group_mode, out_group_list, page_list, page_comment_mode, delete_page_after_comment, ttc_jobs, ttc_comment_mode, cycle_count, task_config, parts, win_pos, proxy_config, user_agent)
        if type(res) == tuple and len(res) == 3:
            result_val, is_dead, driver = res
            if result_val is not True:
                return result_val
        else:
            return res

    except Exception as e:
        print(f" Thread Error for {cookie_line[:20]}...: {e}")
        return False
    finally:
        if driver:
            try:
                cleanup_seleniumwire(driver)
                driver.quit()
                time.sleep(1) # Chờ process giải phóng file
            except: pass
            
        if is_dead:
            remove_dead_account(cookie_line)
