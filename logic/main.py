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
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By

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
    get_assigned_proxy, parse_proxy_str
)
from core.automation_service import process_group_cycle, process_keyword_search, process_page_cycle, process_ttc_cycle
from actions.feed_actions import warm_up_account
from actions.login import login_with_credentials
from actions.join_groups import join_single_group
from actions.out_group import out_groups_by_mode
from actions.TTC.get_job import fetch_ttc_jobs

# Danh sách các tài khoản bị block tính năng tạm thời (chỉ lưu in-memory trong phiên chạy này)
BLOCKED_ACCOUNTS = set()

# Cache lưu trữ danh sách group đã quét cho mỗi UID để tránh quét lại nhiều lần trong cùng một phiên chạy
SCANNED_GROUPS_CACHE = {}

SEEN_TTC_JOBS = set()

# Cấu hình cửa sổ (Grid layout)
WIN_WIDTH = 500
WIN_HEIGHT = 700
COLS = 3  

def get_window_pos(index):
    """Tính toán vị trí cửa sổ dựa trên index luồng"""
    col = index % COLS
    row = index // COLS
    x = col * (WIN_WIDTH + 10)
    y = row * (WIN_HEIGHT + 10)
    return (x, y, WIN_WIDTH, WIN_HEIGHT)


def get_profile_path(uid):
    """Tính toán đường dẫn tuyệt đối của thư mục profile cho một UID"""
    profile_dir = getattr(config, "PROFILE_DIR", "profiles")
    if not os.path.isabs(profile_dir):
        profile_dir = os.path.join(os.getcwd(), profile_dir)
    return os.path.join(profile_dir, uid)

def remove_dead_account(cookie_line):
    """Xóa tài khoản die khỏi file account.txt, xóa proxy mapping và profile"""
    uid = cookie_line.split("|")[0] if "|" in cookie_line else "Unknown"
    
    # 1. Xóa khỏi account.txt
    with FILE_LOCK:
        try:
            acc_file = config.COOKIE_FILE
            if os.path.exists(acc_file):
                with open(acc_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                # Lọc bỏ dòng trùng khớp
                new_lines = [l for l in lines if l.strip() != cookie_line.strip()]
                
                with open(acc_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                print(f" Đã xóa tài khoản {uid} khỏi {acc_file}")
                # print(f"UI_STATUS|{uid}|Checkpoint")
        except Exception as e:
            print(f" Lỗi khi xóa tài khoản die khỏi file: {e}")

    # 2. Xóa khỏi account_proxy.json
    if uid != "Unknown":
        mapping = load_proxy_mapping()
        if uid in mapping:
            del mapping[uid]
            save_proxy_mapping(mapping)
            print(f"Đã giải phóng proxy mapping cho UID {uid}")
            
        # 3. Xóa thư mục profile
        profile_path = get_profile_path(uid)
        if os.path.exists(profile_path):
            try:
                shutil.rmtree(profile_path)
                print(f" Đã xóa thư mục profile của UID {uid}")
            except Exception as e:
                print(f" Lỗi khi xóa thư mục profile của UID {uid}: {e}")

def run_account_task(cookie_line, thread_index, max_comments, is_edit_comment="yes", execution_mode=1, warmup_time_sec=None, keyword_list=None, group_join_list=None, out_group_mode=None, out_group_list=None, page_list=None, page_comment_mode="text", delete_page_after_comment=True, ttc_jobs=None, ttc_comment_mode="text"):
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
        
        # Proxy mapping
        mapping_proxy = load_proxy_mapping()
        all_proxies = load_proxies()
        proxy_str = get_assigned_proxy(uid, all_proxies, mapping_proxy)
        proxy_config = parse_proxy_str(proxy_str)
        
        print(f"[{uid}]  Khởi động luồng (Proxy: {proxy_str if proxy_str else 'Direct'})")
        
        profile_path = get_profile_path(uid)
        print(f"[{uid}]  Profile Path: {profile_path}")
        if os.path.exists(profile_path):
            if execution_mode == 2:
                print(f"[{uid}]  Bỏ qua vì Profile đã tồn tại (Chế độ 2).")
                return "SKIPPED"
            print(f"[{uid}]  Profile đã tồn tại.")
        else:
            print(f"[{uid}]  Profile chưa tồn tại, đang tạo mới.")
        
        driver, wait, _ = create_driver(
            user_data_dir=profile_path, 
            proxy_config=proxy_config, 
            window_pos=win_pos,
            user_agent=user_agent
        )
        
        # --- SMART LOGIN LOGIC ---
        driver.get("https://www.facebook.com/")
        print(f"[{uid}]  Đang kiểm tra trạng thái login tại: {driver.current_url}")
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
            print(f"[{uid}]  Session cũ trong Profile vẫn còn hiệu lực. Bỏ qua nạp cookie.")
        else:
            print(f"[{uid}]  Session hết hạn/chưa có (hoặc sai UA). Tiến hành nạp cookie mới...")
            # driver.delete_all_cookies() # Đã ẩn để tránh clear profile vô ích
            print(f"[{uid}]  Đang nạp {len(actual_cookies)} cookie từ file account (Sẽ thêm Expiry 1 năm)...")
            
            # Tính toán expiry: 1 năm kể từ hiện tại
            expiry_time = int(time.time()) + (365 * 24 * 3600)
            
            for cookie_dict in actual_cookies:
                try: 
                    cookie_dict["domain"] = ".facebook.com"
                    cookie_dict["path"] = "/"
                    cookie_dict["expiry"] = expiry_time # Ép persistent
                    driver.add_cookie(cookie_dict)
                except Exception as e_cook:
                    # In lỗi nếu nạp thất bại (trừ các cookie rác)
                    if cookie_dict.get('name') in ['c_user', 'xs', 'fr', 'datr']:
                        print(f"[{uid}]  Lỗi nạp cookie quan trọng ({cookie_dict.get('name')}): {e_cook}")
                    pass
            driver.refresh()
            time.sleep(8)

        # Check status sau khi nạp (hoặc dùng session cũ)
        current_url = safe_url(driver)
        
        # --- KIỂM TRA TRẠNG THÁI LOGIN ---
        if execution_mode != 6 and ("checkpoint" in current_url.lower() or is_checkpoint(driver)):
            if is_soft_checkpoint(driver):
                print(f"[{uid}]  CHECKPOINT TẠM THỜI (601051028565049) - Bỏ qua tài khoản, KHÔNG xóa.")
                return "SKIPPED_SOFT_CHECKPOINT"
            else:
                print(f"[{uid}]  PHÁT HIỆN CHECKPOINT CỨNG -> Xóa tài khoản.")
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
                    print(f"[{uid}]  Login và xác minh UID thành công.")
                else:
                    print(f"[{uid}]  Đã login nhưng vẫn không xác minh được UID (URL: {safe_url(driver)}).")
                    if execution_mode != 6: return False
            else:
                print(f"[{uid}]  Login bằng credentials thất bại.")
                if execution_mode != 6: return False

        if execution_mode == 2:
            print(f"[{uid}]  MODE 2: Profile created and Login verified. Success.")
            return True

        if execution_mode == 3:
            print(f"[{uid}] MODE 3: Tiến hành nuôi tài khoản trong {warmup_time_sec} giây...")
            warm_up_account(driver, uid, warmup_time=warmup_time_sec)
            print(f"[{uid}]  MODE 3: Nuôi tài khoản hoàn tất.")
            return True

        if execution_mode == 4:
            print(f"[{uid}]  MODE 4: Spam Comment Keyword...")
            if not keyword_list:
                print(f"[{uid}]  Không có danh sách keyword.")
                return False
            
            random.shuffle(keyword_list)
            kw_iterator = iter(keyword_list)
            
            success_count = 0
            while success_count < max_comments:
                try:
                    kw = next(kw_iterator)
                except StopIteration:
                    print(f"[{uid}]  Đã thử hết toàn bộ danh sách keyword.")
                    break
                
                result = process_keyword_search(driver, uid, kw, is_edit_comment)
                if result is True:
                    success_count += 1
                    print(f"[{uid}]  Đã hoàn thành {success_count}/{max_comments} comment keyword.")
                
                if success_count >= max_comments: break
                time.sleep(random.randint(15, 30))
            
            print(f"[{uid}]  MODE 4: Hoàn thành task keyword.")
            return True

        if execution_mode == 5:
            print(f"[{uid}]  MODE 5: Tham gia nhóm (Join Groups)...")
            if not group_join_list:
                print(f"[{uid}]  Không có danh sách nhóm để tham gia.")
                return False
            
            for gid in group_join_list:
                gid = gid.strip()
                if not gid: continue
                join_single_group(driver, wait, uid, gid)
                delay = random.randint(5, 10)
                print(f"[{uid}]  Nghỉ {delay}s trước khi chuyển sang nhóm tiếp theo...")
                time.sleep(delay)
            
            print(f"[{uid}]  MODE 5: Hoàn thành danh sách tham gia nhóm.")
            return True

        if execution_mode == 7:
            print(f"[{uid}]  MODE 7: Rời nhóm (Out Group)...")
            out_groups_by_mode(driver, uid, out_group_mode, out_group_list)
            print(f"[{uid}]  MODE 7: Hoàn thành.")
            return True

        if execution_mode == 8:
            print(f"[{uid}]  MODE 8: Comment ID Page ({page_comment_mode.upper()})...")
            if not page_list:
                print(f"[{uid}]  Không có danh sách Page ID.")
                return False

            success_count = 0
            for page_id in list(page_list):  # Iterate bản sao để có thể xóa an toàn
                page_id = page_id.strip()
                if not page_id:
                    continue

                result = process_page_cycle(driver, uid, page_id, is_edit_comment, page_comment_mode)

                if result == "BLOCK_MODAL_DETECTED":
                    print(f"[{uid}]  Bị chặn tính năng. Dừng tài khoản này.")
                    BLOCKED_ACCOUNTS.add(uid)
                    break

                if result is True:
                    success_count += 1
                    print(f"[{uid}]  Comment thành công page: {page_id}")
                    # Xóa page đã xong khỏi file id_pages.txt (nếu được bật)
                    if delete_page_after_comment:
                        with FILE_LOCK:
                            try:
                                pages_file = "resources/id_pages.txt"
                                if os.path.exists(pages_file):
                                    with open(pages_file, "r", encoding="utf-8") as f:
                                        remaining = [l for l in f.readlines()
                                                     if l.strip() and l.strip() != page_id]
                                    with open(pages_file, "w", encoding="utf-8") as f:
                                        f.writelines(remaining)
                                    print(f"[{uid}]  Đã xóa page '{page_id}' khỏi id_pages.txt")
                            except Exception as e_del:
                                print(f"[{uid}]  Lỗi khi xóa page khỏi file: {e_del}")
                    else:
                        print(f"[{uid}]  Giữ lại page '{page_id}' trong file (không xóa).")
                else:
                    print(f"[{uid}]  Không comment được page: {page_id}. Thử page tiếp theo.")

                delay = random.randint(10, 20)
                print(f"[{uid}]  Nghỉ {delay}s trước khi chuyển sang page tiếp theo...")
                time.sleep(delay)

            print(f"[{uid}]  MODE 8: Hoàn thành — đã comment {success_count} page.")
            return True

        if execution_mode == 9:
            print(f"[{uid}]  MODE 9: Comment TTC ({ttc_comment_mode.upper()})...")

            success_count = 0
            while True:
                job = None
                with FILE_LOCK:
                    if ttc_jobs:
                        job = ttc_jobs.pop(0)
                
                if not job:
                    # Nếu hàng đợi rỗng, thử lấy thêm job mới từ TTC
                    with FILE_LOCK:
                        # Double check phòng khi luồng khác vừa lấy xong
                        if ttc_jobs:
                            job = ttc_jobs.pop(0)
                        else:
                            print(f"[{uid}]  Đang lấy thêm job mới từ TTC...")
                            try:
                                from actions.TTC.get_job import fetch_ttc_jobs
                                new_jobs = fetch_ttc_jobs()
                                if new_jobs:
                                    history_file = "resources/ttc_commented.txt"
                                    commented_ids = set()
                                    if os.path.exists(history_file):
                                        with open(history_file, "r", encoding="utf-8") as f:
                                            commented_ids = set(l.strip() for l in f if l.strip())
                                    
                                    for j in new_jobs:
                                        jid = str(j.get("idpost"))
                                        if jid not in commented_ids and jid not in SEEN_TTC_JOBS:
                                            ttc_jobs.append(j)
                                            SEEN_TTC_JOBS.add(jid)
                                
                                if ttc_jobs:
                                    job = ttc_jobs.pop(0)
                            except Exception as e:
                                print(f"[{uid}]  Lỗi lấy thêm job TTC: {e}")
                
                if not job:
                    print(f"[{uid}]  Không còn job TTC mới lúc này. Dừng tài khoản.")
                    break

                job_id = job.get("idpost")
                job_link = job.get("link")
                if not job_id or not job_link:
                    continue

                result = process_ttc_cycle(driver, uid, job_link, job_id, is_edit_comment, ttc_comment_mode)

                if result == "BLOCK_MODAL_DETECTED":
                    print(f"[{uid}]  Bị chặn tính năng. Dừng tài khoản này.")
                    BLOCKED_ACCOUNTS.add(uid)
                    break

                if result is True:
                    success_count += 1
                    print(f"[{uid}]  Comment thành công TTC Job: {job_id}")
                else:
                    print(f"[{uid}]  Không comment được TTC Job: {job_id}.")
                
                if success_count >= max_comments:
                    print(f"[{uid}]  Đã đạt mục tiêu {max_comments} comment cho tài khoản này.")
                    break

                # Nghỉ ngơi 1 chút trước khi làm job tiếp theo
                delay = random.randint(10, 20)
                print(f"[{uid}]  Nghỉ {delay}s trước khi chuyển sang job tiếp theo...")
                time.sleep(delay)

            print(f"[{uid}]  MODE 9: Hoàn thành — đã comment {success_count} job TTC trong lượt này.")
            return True

        if execution_mode == 6:
            print(f"[{uid}]  MODE 6: Đã mở Profile và xác minh Login. Trình duyệt sẽ được giữ nguyên.")
            print(f"[{uid}]  Vui lòng thao tác thủ công. Đóng trình duyệt để kết thúc luồng này.")
            try:
                while True:
                    # Kiểm tra xem trình duyệt còn mở không
                    _ = driver.window_handles
                    time.sleep(5)
            except Exception:
                print(f"[{uid}]  Trình duyệt đã đóng. Kết thúc luồng.")
            return True

        if uid in SCANNED_GROUPS_CACHE:
            print(f"[{uid}]  Sử dụng danh sách group đã quét từ cache...")
            g_list = list(SCANNED_GROUPS_CACHE[uid])
        else:
            print(f"[{uid}]  UID LIVE. Bắt đầu quét danh sách group đã tham gia...")
            
            # Lấy danh sách group động từ utils/scan_group.py
            scanned_groups = get_joined_groups(driver, uid=uid)
            if not scanned_groups:
                print(f"[{uid}]  Không tìm thấy group nào đã tham gia. Thử dùng file group.txt dự phòng...")
                with FILE_LOCK:
                    g_list = read_file("resources/group.txt")
            else:
                # Chuyển đổi list object sang list GID (hoặc Link nếu không có ID)
                g_list = [g['uid'] if g['uid'] != "N/A" else g['link'] for g in scanned_groups]
                print(f"[{uid}]  Đã tìm thấy {len(g_list)} group.")

            # Lọc group theo file target_groups.txt (nếu có dữ liệu mục tiêu)
            target_file = getattr(config, "TARGET_GROUPS_FILE", "resources/target_groups.txt")
            target_list = read_file(target_file)
            if target_list:
                print(f"[{uid}]  Phát hiện file group mục tiêu từ {target_file} ({len(target_list)} mục). Tiến hành lọc...")
                filtered_g_list = []
                for g in g_list:
                    g_str = str(g).strip()
                    match_found = False
                    for target in target_list:
                        t_str = str(target).strip()
                        if not t_str:
                            continue
                        if t_str == g_str or t_str in g_str or g_str in t_str:
                            match_found = True
                            break
                    if match_found:
                        filtered_g_list.append(g)
                print(f"[{uid}]  Đã lọc: Còn {len(filtered_g_list)}/{len(g_list)} group trùng khớp.")
                g_list = filtered_g_list
                
            # Lưu vào cache để dùng cho các vòng lặp sau
            SCANNED_GROUPS_CACHE[uid] = list(g_list)

        # SHUFFLE GROUP ĐỂ RANDOM KHÔNG TRÙNG (1 turn không trùng group)
        random.shuffle(g_list)
        group_iterator = iter(g_list)

        # Loop với giới hạn số lần comment
        success_count = 0
        while success_count < max_comments:
            if not g_list:
                print(f"[{uid}]  Không có danh sách group để chạy.")
                break

            warm_up_account(driver, uid, warmup_time=warmup_time_sec)
            
            retry_group_count = 0
            found_and_commented = False
            
            while retry_group_count < 5:
                # Chọn group tiếp theo từ danh sách đã shuffle (đảm bảo không trùng)
                try:
                    target_gid = next(group_iterator)
                except StopIteration:
                    print(f"[{uid}]  Đã thử hết toàn bộ danh sách group.")
                    break

                result = process_group_cycle(driver, uid, target_gid, is_edit_comment)
                
                if result == "STOP_ACCOUNT":
                    print(f"[{uid}]  Tín hiệu dừng account được kích hoạt. Đang thoát luồng...")
                    found_and_commented = False
                    break # Thoát khỏi retry_group_count loop
                
                if result == "BLOCK_MODAL_DETECTED":
                    print(f"[{uid}]  Phát hiện modal chặn tính năng từ Facebook. Đang đưa tài khoản vào danh sách bỏ qua...")
                    BLOCKED_ACCOUNTS.add(uid)
                    found_and_commented = False
                    break # Thoát khỏi retry_group_count loop
                
                if result is True:
                    success_count += 1
                    found_and_commented = True
                    print(f"[{uid}]  Đã hoàn thành {success_count}/{max_comments} comment.")
                    print(f" Comment thành công: {uid} | Group: {target_gid}")
                    # print(f"UI_STATUS|{uid}|Success")
                    # print(f"UI_SUCCESS|{uid}|1")
                    break
                else:
                    retry_group_count += 1
                    print(f"[{uid}]  Thử sang group khác ({retry_group_count}/5)...")
            
            if not found_and_commented:
                print(f"[{uid}]  Đã thử 5 group nhưng không tìm thấy bài viết phù hợp. Dừng account này.")
                break
            
            if success_count >= max_comments:
                print(f"[{uid}]  Đã đạt mục tiêu {max_comments} comment. Đang đổi account...")
                break

            # Sau 3-5 lần thành công -> Nghỉ lâu (Coffee Break)
            if success_count > 0 and success_count % random.randint(3, 5) == 0:
                break_time = random.randint(120, 300)
                print(f"[{uid}]  Nghỉ giải lao {break_time}s...")
                time.sleep(break_time)
            else:
                print(f"[{uid}]  Nghỉ 10s...")
                time.sleep(10)
                
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

# ================= MAIN ENTRY =================
if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass

    cookies_data = read_file(config.COOKIE_FILE)
    if not cookies_data:
        print(" HẾT COOKIE")
    else:
        max_threads = 3
        max_limit = 5
        is_edit_comment = "yes"
        config_path = "resources/config.json"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    max_threads = cfg.get("MaxThreads", 3)
                    max_limit = cfg.get("MaxCommentsPerAcc", 5)
                    is_edit_comment = cfg.get("IsEditComment", "yes")
                    print(f" Loaded config: {max_threads} threads, {max_limit} limit, Edit: {is_edit_comment}.")
            except Exception as e:
                print(f" Lỗi khi đọc file config.json: {e}")
        else:
            print(" No config file found, using default settings.")

        MAX_THREADS = max_threads 
        
        print("\n" + "="*50)
        print("          FB TOOLS - CHỌN CHẾ ĐỘ CHẠY")
        print("="*50)
        print("1. Spam Comment Groups")
        print("2. Create Profile & Check Live")
        print("3. Nuôi Tài Khoản")
        print("4. Spam Comment Keyword")
        print("5. Join Groups theo danh sách")
        print("6. Mở Profile")
        print("7. Rời nhóm")
        print("8. Comment ID Page")
        print("9. Comment bài viết (TTC)")
        print("="*50)
        
        try:
            choice = input("👉 Nhập lựa chọn: ").strip()
        except:
            choice = "1"
            
        if choice == "4":
            # MODE 4: SPAM COMMENT KEYWORD
            print(f" BẮT ĐẦU CHẾ ĐỘ 4: Spam Comment Keyword ({max_threads} luồng)")
            keyword_list = read_file("resources/keyword.txt")
            if not keyword_list:
                print(" Không tìm thấy file resources/keyword.txt hoặc file trống.")
                sys.exit(1)
            
            cycle_count = 1
            while True:
                print(f"\n BẮT ĐẦU VÒNG LẶP DANH SÁCH THỨ {cycle_count}")
                current_cookies = read_file(config.COOKIE_FILE)
                if not current_cookies:
                    print(" Danh sách tài khoản trống. Thử lại sau 30s...")
                    time.sleep(30)
                    continue

                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    for idx, cookie in enumerate(current_cookies):
                        slot_index = idx % max_threads
                        executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=4, keyword_list=keyword_list)
                
                print(f" Đã chạy xong 1 vòng ({len(current_cookies)} tài khoản). Nghỉ 3600s trước khi lặp lại từ đầu...")
                time.sleep(3600)
                cycle_count += 1

        elif choice == "5":
            # MODE 5: JOIN GROUPS
            print(f" BẮT ĐẦU CHẾ ĐỘ 5: Join Groups ({max_threads} luồng)")
            group_join_list = read_file("resources/id_groups_join.txt")
            if not group_join_list:
                print(" Không tìm thấy file resources/id_groups_join.txt hoặc file trống.")
                sys.exit(1)
            
            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            print(f" Bắt đầu chạy danh sách ({len(current_cookies)} tài khoản)...")
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for idx, cookie in enumerate(current_cookies):
                    slot_index = idx % max_threads
                    executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=5, group_join_list=group_join_list)
            
            print(f" Đã chạy xong toàn bộ danh sách. Dừng chương trình.")
            sys.exit(0)

        elif choice == "3":
            # MODE 3: WARM UP ACCOUNTS INFINITELY
            try:
                warmup_minutes = int(input(" Nhập số phút nuôi cho mỗi tài khoản (Ví dụ: 5): ").strip())
            except ValueError:
                print(" Lỗi định dạng nhập vào. Sẽ sử dụng mặc định là 5 phút.")
                warmup_minutes = 5
                
            warmup_time_sec = warmup_minutes * 60
            print(f" BẮT ĐẦU CHẾ ĐỘ 3: Nuôi Tài Khoản ({max_threads} luồng, {warmup_minutes} phút/acc)")
            
            cycle_count = 1
            while True:
                print(f"\n BẮT ĐẦU VÒNG LẶP DANH SÁCH THỨ {cycle_count}")
                current_cookies = read_file(config.COOKIE_FILE)
                if not current_cookies:
                    print(" Danh sách tài khoản trống. Thử lại sau 30s...")
                    time.sleep(30)
                    continue

                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    for idx, cookie in enumerate(current_cookies):
                        slot_index = idx % max_threads
                        executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=3, warmup_time_sec=warmup_time_sec)
                
                print(f" Đã chạy xong 1 vòng ({len(current_cookies)} tài khoản). Nghỉ 600s trước khi lặp lại từ đầu...")
                time.sleep(600)
                cycle_count += 1
                
        elif choice == "2":
            # MODE 2: CREATE PROFILE & CHECK LIVE
            print(f" BẮT ĐẦU CHẾ ĐỘ: Create Profile & Check Live ({max_threads} luồng)")
            current_cookies = read_file(config.COOKIE_FILE)
            total_acc = len(current_cookies)
            success_count = 0
            fail_count = 0
            skip_count = 0
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = []
                for idx, cookie in enumerate(current_cookies):
                    slot_index = idx % max_threads
                    futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=2))
                
                for f in futures:
                    res = f.result()
                    if res == "SKIPPED":
                        skip_count += 1
                    elif res is True:
                        success_count += 1
                    else:
                        fail_count += 1
            
            print("\n" + "="*50)
            print(" HOÀN THÀNH CHẾ ĐỘ CREATE PROFILE & CHECK LIVE")
            print(f" Tổng số tài khoản: {total_acc}")
            print(f" Thành công (Live): {success_count}")
            print(f" Đã bỏ qua (Đã có sẵn): {skip_count}")
            print(f" Thất bại (Checkpoint/Die): {fail_count}")
            print("="*50)
            sys.exit(0)
            
        elif choice == "6":
            # MODE 6: OPEN PROFILE ONLY
            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            print("\n DANH SÁCH TÀI KHOẢN HIỆN CÓ:")
            for i, line in enumerate(current_cookies):
                uid = line.split("|")[0] if "|" in line else "Unknown"
                print(f"[{i+1}] UID: {uid}")

            try:
                selected_input = input("\n👉 Nhập số thứ tự các tài khoản muốn mở (ví dụ: 1,2,5 hoặc 'all'): ").strip().lower()
                if selected_input == "all":
                    selected_indices = list(range(len(current_cookies)))
                else:
                    # Parse input like "1,2,5"
                    selected_indices = [int(x.strip()) - 1 for x in selected_input.split(",") if x.strip().isdigit()]
            except Exception as e:
                print(f" Lỗi nhập liệu: {e}")
                sys.exit(0)

            if not selected_indices:
                print(" Không có tài khoản nào được chọn hợp lệ.")
                sys.exit(0)

            # Lọc danh sách được chọn
            selected_accounts = []
            for idx in selected_indices:
                if 0 <= idx < len(current_cookies):
                    selected_accounts.append(current_cookies[idx])
                else:
                    print(f" Bỏ qua số thứ tự {idx+1} (không tồn tại).")

            if not selected_accounts:
                print(" Không có tài khoản nào để mở.")
                sys.exit(0)

            print(f" BẮT ĐẦU CHẾ ĐỘ 6: Mở Profile ({len(selected_accounts)} tài khoản - tối đa {max_threads} luồng)")

            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for idx, cookie in enumerate(selected_accounts):
                    slot_index = idx % max_threads
                    executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=6)
            
            print(f" Đã đóng tất cả các Profile của Mode 6.")
            sys.exit(0)

        elif choice == "7":
            # MODE 7: OUT GROUP
            print("\n" + "-"*30)
            print("CHẾ ĐỘ RỜI NHÓM (OUT GROUP)")
            print("1. Rời TẤT CẢ các nhóm")
            print("2. Rời nhóm THEO DANH SÁCH ID")
            print("3. Rời nhóm NGOẠI TRỪ DANH SÁCH ID")
            print("-"*30)
            
            og_mode = input("👉 Chọn chế độ (1/2/3): ").strip()
            og_list = []
            
            if og_mode in ["2", "3"]:
                print("\n Dán danh sách GID/Link nhóm (mỗi dòng 1 cái).")
                print("Xong thì nhấn Enter -> Ctrl+Z -> Enter:")
                try:
                    raw_input = sys.stdin.read()
                    og_list = [x.strip() for x in raw_input.splitlines() if x.strip()]
                    print(f" Đã nhận {len(og_list)} ID nhóm.")
                except EOFError: pass

            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            print(f" BẮT ĐẦU CHẾ ĐỘ 7: Out Group ({max_threads} luồng)")
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for idx, cookie in enumerate(current_cookies):
                    slot_index = idx % max_threads
                    executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, 
                                    execution_mode=7, out_group_mode=og_mode, out_group_list=og_list)
            
            print(f" Đã chạy xong toàn bộ danh sách. Dừng chương trình.")
            sys.exit(0)

        elif choice == "8":
            # MODE 8: COMMENT ID PAGE
            print("\n" + "-"*40)
            print(" CHẾ ĐỘ 8: COMMENT ID PAGE")
            print("-"*40)
            print(" File danh sách page: resources/id_pages.txt")
            print(" Mỗi dòng 1 ID hoặc username page.")
            print("-"*40)

            # Chọn kiểu comment
            print("\n Chọn kiểu comment:")
            print("  1. Comment bằng TXT (nội dung từ edit_stt.txt)")
            print("  2. Comment bằng ẢNH (từ thư mục resources/images/)")
            try:
                cm_choice = input("👉 Nhập lựa chọn (1/2): ").strip()
            except:
                cm_choice = "1"

            page_comment_mode = "image" if cm_choice == "2" else "text"
            print(f" Kiểu comment: {'ẢNH' if page_comment_mode == 'image' else 'TXT (edit_stt.txt)'}")

            # Đọc danh sách page
            pages_file = "resources/id_pages.txt"
            page_list = read_file(pages_file)
            if not page_list:
                print(f" Không tìm thấy file {pages_file} hoặc file trống.")
                print(" Hãy thêm ID/username page vào file resources/id_pages.txt (mỗi dòng 1 cái).")
                sys.exit(1)

            print(f" Tìm thấy {len(page_list)} page trong danh sách.")

            # Hỏi có xóa page ID khỏi file sau khi comment thành công không
            print("\n Tự động xóa page ID khỏi file sau khi comment thành công?")
            print("  y. CÓ — xóa page đã làm xong (mặc định)")
            print("  n. KHÔNG — giữ nguyên file, chỉ comment")
            try:
                del_choice = input("👉 Nhập lựa chọn (y/n): ").strip().lower()
            except:
                del_choice = "y"
            delete_page_after_comment = (del_choice != "n")
            print(f" Chế độ xóa sau comment: {'CÓ' if delete_page_after_comment else 'KHÔNG'}")

            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            print(f" BẮT ĐẦU CHẾ ĐỘ 8: Comment ID Page ({max_threads} luồng)")

            # Mỗi tài khoản sẽ nhận bản sao danh sách page để tự xử lý xóa riêng.
            # Việc xóa khỏi file id_pages.txt được bảo vệ bởi FILE_LOCK.
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                for idx, cookie in enumerate(current_cookies):
                    slot_index = idx % max_threads
                    executor.submit(
                        run_account_task, cookie, slot_index, max_limit, is_edit_comment,
                        execution_mode=8,
                        page_list=list(page_list),
                        page_comment_mode=page_comment_mode,
                        delete_page_after_comment=delete_page_after_comment
                    )

            print(f" Đã chạy xong toàn bộ danh sách. Dừng chương trình.")
            sys.exit(0)

        elif choice == "9":
            # MODE 9: COMMENT BÀI VIẾT (TTC)
            print("\n" + "-"*40)
            print(" CHẾ ĐỘ 9: COMMENT BÀI VIẾT (TTC)")
            print("-"*40)

            # Chọn kiểu comment
            print("\n Chọn kiểu comment:")
            print("  1. Comment bằng TXT (nội dung từ edit_stt.txt)")
            print("  2. Comment bằng ẢNH (từ thư mục resources/images/)")
            try:
                cm_choice = input("👉 Nhập lựa chọn (1/2): ").strip()
            except:
                cm_choice = "1"

            ttc_comment_mode = "image" if cm_choice == "2" else "text"
            print(f" Kiểu comment: {'ẢNH' if ttc_comment_mode == 'image' else 'TXT (edit_stt.txt)'}")

            cycle_count = 1
            while True:
                print(f"\n BẮT ĐẦU VÒNG LẶP TTC THỨ {cycle_count}")
                current_cookies = read_file(config.COOKIE_FILE)
                if not current_cookies:
                    print(" Danh sách tài khoản trống. Thử lại sau 30s...")
                    time.sleep(30)
                    continue
                
                # Khởi tạo danh sách job trống ban đầu, các luồng sẽ tự đi lấy nếu thiếu
                shared_ttc_jobs = []
                SEEN_TTC_JOBS.clear()

                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    for idx, cookie in enumerate(current_cookies):
                        slot_index = idx % max_threads
                        executor.submit(
                            run_account_task, cookie, slot_index, max_limit, is_edit_comment,
                            execution_mode=9,
                            ttc_jobs=shared_ttc_jobs,
                            ttc_comment_mode=ttc_comment_mode
                        )
                
                print(f" Đã chạy xong 1 vòng. Nghỉ 60s trước khi bắt đầu vòng lặp mới...")
                time.sleep(60)
                cycle_count += 1

        else:
            # MODE 1: SPAM COMMENT GROUPS (ORIGINAL)
            try:
                warmup_minutes = int(input(" Nhập số phút lướt New Feed trước khi scan (Ví dụ: 2): ").strip())
            except ValueError:
                print(" Lỗi định dạng. Sử dụng mặc định 2 phút.")
                warmup_minutes = 2
            
            warmup_time_sec = warmup_minutes * 60
            print(f" Bắt đầu quy trình Spam: {max_threads} luồng, {max_limit} comment/acc, Warmup: {warmup_minutes}m. Lặp vô tận.")
            
            cycle_count = 1
            while True:
                print(f"\n BẮT ĐẦU VÒNG LẶP DANH SÁCH THỨ {cycle_count}")
                current_cookies = read_file(config.COOKIE_FILE)
                if not current_cookies:
                    print(" Danh sách tài khoản trống. Thử lại sau 30s...")
                    time.sleep(30)
                    continue

                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    for idx, cookie in enumerate(current_cookies):
                        slot_index = idx % max_threads
                        executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=1, warmup_time_sec=warmup_time_sec)
                
                print(f" Đã chạy hết danh sách ({len(current_cookies)} bài). Nghỉ 3600s trước khi lặp lại từ đầu...")
                time.sleep(3600)
                cycle_count += 1