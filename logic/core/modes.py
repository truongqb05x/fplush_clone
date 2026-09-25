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


import sys
import time
import json
import os
from concurrent.futures import ThreadPoolExecutor
from config import config
from utils.file_utils import read_file
from core.task_runner import run_account_task
from core.globals import *

def run_cli():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass

    task_config = None
    choice = "1"
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
        if len(sys.argv) > 2:
            task_config_path = sys.argv[2].strip()
            if os.path.exists(task_config_path):
                try:
                    with open(task_config_path, "r", encoding="utf-8") as f:
                        task_config = json.load(f)
                except Exception: pass

    cookies_data = task_config.get("SelectedAccountsInfo", []) if task_config else []
    if not cookies_data:
        cookies_data = read_file(config.COOKIE_FILE)
        
    if not cookies_data:
        print(" HẾT COOKIE")
    else:
        max_threads = 3
        max_limit = 5
        is_edit_comment = "yes"
        config_path = getattr(config, "CONFIG_JSON_FILE", "resources/config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    max_threads = cfg.get("MaxThreads", 3)
                    max_limit = cfg.get("MaxCommentsPerAcc", 5)
                    is_edit_comment = cfg.get("IsEditComment", "yes")
                    # print(f" Loaded config: {max_threads} threads, {max_limit} limit, Edit: {is_edit_comment}.")
            except Exception as e:
                print(f" Lỗi khi đọc file config.json: {e}")
        else:
            pass # print(" No config file found, using default settings.")

        MAX_THREADS = max_threads 
        
        # print("\n" + "="*50)
        # print("          FB TOOLS - CHỌN CHẾ ĐỘ CHẠY")
        # print("="*50)
        # print("1. Spam Comment Groups")
        # print("3. Nuôi Tài Khoản")
        # print("4. Spam Comment Keyword")
        # print("5. Join Groups theo danh sách")
        # print("7. Rời nhóm")
        # print("8. Comment ID Page")
        # print("9. Comment bài viết (TTC)")
        # print("10. Upload Avatar")
        # print("="*50)
        
        if len(sys.argv) > 1:
            print(f"👉 Chế độ được truyền qua đối số: {choice}")
            if task_config:
                print(f" Loaded task config from {sys.argv[2].strip()}")
        else:
            try:
                choice = input("👉 Nhập lựa chọn: ").strip()
            except:
                choice = "1"
                choice = "1"
            
        if choice == "4":
            # MODE 4: SPAM COMMENT KEYWORD
            print(f" BẮT ĐẦU CHẾ ĐỘ 4: Spam Comment Keyword ({max_threads} luồng)")
            keyword_list = read_file(getattr(config, "KEYWORD_FILE", "resources/keyword.txt"))
            if not keyword_list:
                print(" Không tìm thấy file keyword hoặc file trống.")
                sys.exit(1)
            
            cycle_count = 1
            while True:
                print(f"\n BẮT ĐẦU VÒNG LẶP DANH SÁCH THỨ {cycle_count}")
                current_cookies = read_file(config.COOKIE_FILE)
                if not current_cookies:
                    print(" Danh sách tài khoản trống. Thử lại sau 30s...")
                    time.sleep(30)
                    continue

                batch_id = 0
                for i in range(0, len(current_cookies), max_threads):
                    batch = current_cookies[i:i+max_threads]
                    proxy_turn = f"{cycle_count}_{batch_id}"
                    print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                    with ThreadPoolExecutor(max_workers=max_threads) as executor:
                        futures = []
                        for idx, cookie in enumerate(batch):
                            slot_index = idx % max_threads
                            futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=4, keyword_list=keyword_list, cycle_count=proxy_turn))
                        for f in futures:
                            f.result()
                    batch_id += 1
                
                print(f" Đã chạy xong 1 vòng ({len(current_cookies)} tài khoản). Nghỉ 3600s trước khi lặp lại từ đầu...")
                time.sleep(3600)
                cycle_count += 1

        elif choice == "5":
            # MODE 5: JOIN GROUPS
            print(f" BẮT ĐẦU CHẾ ĐỘ 5: Join Groups ({max_threads} luồng)")
            group_join_list = read_file(getattr(config, "GROUP_JOIN_FILE", "resources/id_groups_join.txt"))
            if not group_join_list:
                print(f" Không tìm thấy file {getattr(config, 'GROUP_JOIN_FILE', 'resources/id_groups_join.txt')} hoặc file trống.")
                sys.exit(1)
            
            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            print(f" Bắt đầu chạy danh sách ({len(current_cookies)} tài khoản)...")
            batch_id = 0
            for i in range(0, len(current_cookies), max_threads):
                batch = current_cookies[i:i+max_threads]
                proxy_turn = f"1_{batch_id}"
                print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = []
                    for idx, cookie in enumerate(batch):
                        slot_index = idx % max_threads
                        futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=5, group_join_list=group_join_list, cycle_count=proxy_turn))
                    for f in futures:
                        f.result()
                batch_id += 1
            
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

                batch_id = 0
                for i in range(0, len(current_cookies), max_threads):
                    batch = current_cookies[i:i+max_threads]
                    proxy_turn = f"{cycle_count}_{batch_id}"
                    print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                    with ThreadPoolExecutor(max_workers=max_threads) as executor:
                        futures = []
                        for idx, cookie in enumerate(batch):
                            slot_index = idx % max_threads
                            futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=3, warmup_time_sec=warmup_time_sec, cycle_count=proxy_turn))
                        
                        # Chờ các luồng trong đợt này hoàn thành
                        for f in futures:
                            f.result()
                    
                    batch_id += 1
                
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
            
            batch_id = 0
            for i in range(0, len(current_cookies), max_threads):
                batch = current_cookies[i:i+max_threads]
                proxy_turn = f"1_{batch_id}"
                print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = []
                    for idx, cookie in enumerate(batch):
                        slot_index = idx % max_threads
                        futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=2, cycle_count=proxy_turn))
                    
                    for f in futures:
                        res = f.result()
                        if res == "SKIPPED":
                            skip_count += 1
                        elif res is True:
                            success_count += 1
                        else:
                            fail_count += 1
                batch_id += 1
            
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
                if len(sys.argv) > 1:
                    selected_input = "all"
                else:
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

            batch_id = 0
            for i in range(0, len(selected_accounts), max_threads):
                batch = selected_accounts[i:i+max_threads]
                proxy_turn = f"1_{batch_id}"
                print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = []
                    for idx, cookie in enumerate(batch):
                        slot_index = idx % max_threads
                        futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=6, cycle_count=proxy_turn))
                    for f in futures:
                        f.result()
                batch_id += 1
            
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
            batch_id = 0
            for i in range(0, len(current_cookies), max_threads):
                batch = current_cookies[i:i+max_threads]
                proxy_turn = f"1_{batch_id}"
                print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = []
                    for idx, cookie in enumerate(batch):
                        slot_index = idx % max_threads
                        futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, 
                                        execution_mode=7, out_group_mode=og_mode, out_group_list=og_list, cycle_count=proxy_turn))
                    for f in futures:
                        f.result()
                batch_id += 1
            
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
            pages_file = getattr(config, "PAGES_FILE", "resources/id_pages.txt")
            page_list = read_file(pages_file)
            if not page_list:
                print(f" Không tìm thấy file {pages_file} hoặc file trống.")
                print(f" Hãy thêm ID/username page vào file {pages_file} (mỗi dòng 1 cái).")
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
            batch_id = 0
            for i in range(0, len(current_cookies), max_threads):
                batch = current_cookies[i:i+max_threads]
                proxy_turn = f"1_{batch_id}"
                print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = []
                    for idx, cookie in enumerate(batch):
                        slot_index = idx % max_threads
                        futures.append(executor.submit(
                            run_account_task, cookie, slot_index, max_limit, is_edit_comment,
                            execution_mode=8,
                            page_list=list(page_list),
                            page_comment_mode=page_comment_mode,
                            delete_page_after_comment=delete_page_after_comment,
                            cycle_count=proxy_turn
                        ))
                    for f in futures:
                        f.result()
                batch_id += 1

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

                batch_id = 0
                for i in range(0, len(current_cookies), max_threads):
                    batch = current_cookies[i:i+max_threads]
                    proxy_turn = f"{cycle_count}_{batch_id}"
                    print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                    with ThreadPoolExecutor(max_workers=max_threads) as executor:
                        futures = []
                        for idx, cookie in enumerate(batch):
                            slot_index = idx % max_threads
                            futures.append(executor.submit(
                                run_account_task, cookie, slot_index, max_limit, is_edit_comment,
                                execution_mode=9,
                                ttc_jobs=shared_ttc_jobs,
                                ttc_comment_mode=ttc_comment_mode,
                                cycle_count=proxy_turn
                            ))
                        for f in futures:
                            f.result()
                    batch_id += 1
                
                print(f" Đã chạy xong 1 vòng. Nghỉ 60s trước khi bắt đầu vòng lặp mới...")
                time.sleep(60)
                cycle_count += 1

        elif choice == "10":
            # MODE 10: UPLOAD AVATAR
            print(f" BẮT ĐẦU CHẾ ĐỘ 10: Upload Avatar ({max_threads} luồng)")
            current_cookies = read_file(config.COOKIE_FILE)
            if not current_cookies:
                print(" Danh sách tài khoản trống.")
                sys.exit(0)

            MAX_RETRIES = 3
            current_retry = 0
            cookies_to_process = current_cookies.copy()

            while cookies_to_process and current_retry <= MAX_RETRIES:
                if current_retry > 0:
                    print(f"\n [RETRY {current_retry}/{MAX_RETRIES}] Đang chạy lại {len(cookies_to_process)} tài khoản bị lỗi...")
                    time.sleep(5)
                else:
                    print(f" Bắt đầu chạy danh sách ({len(cookies_to_process)} tài khoản)...")
                    
                failed_cookies = []
                batch_id = 0
                
                for i in range(0, len(cookies_to_process), max_threads):
                    batch = cookies_to_process[i:i+max_threads]
                    proxy_turn = f"{current_retry + 1}_{batch_id}"
                    print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                    
                    with ThreadPoolExecutor(max_workers=max_threads) as executor:
                        future_to_cookie = {}
                        for idx, cookie in enumerate(batch):
                            slot_index = idx % max_threads
                            f = executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=10, cycle_count=proxy_turn)
                            future_to_cookie[f] = cookie
                        
                        for f in future_to_cookie:
                            cookie = future_to_cookie[f]
                            try:
                                res = f.result()
                                if res is False:
                                    failed_cookies.append(cookie)
                            except Exception as e:
                                print(f" Lỗi luồng: {e}")
                                failed_cookies.append(cookie)
                                
                    batch_id += 1
                
                cookies_to_process = failed_cookies
                current_retry += 1
            
            if cookies_to_process:
                print(f"\n Đã thử lại {MAX_RETRIES} lần nhưng vẫn còn {len(cookies_to_process)} tài khoản lỗi.")
            else:
                print("\n Đã hoàn thành toàn bộ danh sách thành công!")
                
            print(f" Đã chạy xong toàn bộ danh sách. Dừng chương trình.")
            sys.exit(0)

        else:
            # MODE 1: SPAM COMMENT GROUPS (CONFIGURABLE)
            print(f" Bắt đầu quy trình Spam Comment Groups từ cấu hình UI...")
            
            # Lấy thông số từ config
            is_repeat = task_config.get("IsRepeat", False) if task_config else False
            repeat_count = task_config.get("RepeatCount", 1) if task_config else 1
            selected_uids = task_config.get("SelectedAccounts", []) if task_config else []
            
            # Nếu chạy lặp vô hạn thì gán repeat_count cực lớn
            if not is_repeat:
                repeat_count = 1
            else:
                # Nếu lặp lại có số lần cụ thể thì lấy số đó, nếu 0 thì vô hạn (ở đây UI truyền số)
                pass

            # Parse DCOM config
            is_reset_dcom = task_config.get("IsResetDcom", False) if task_config else False
            reset_dcom_after = task_config.get("ResetDcomAfter", 2) if task_config else 2
            proxy_method = task_config.get("ProxyMethod", 0) if task_config else 0
            accounts_processed = 0  # đếm số account đã chạy để biết khi nào reset

            cycle_count = 1
            while cycle_count <= repeat_count:
                print(f"\n BẮT ĐẦU VÒNG LẶP DANH SÁCH THỨ {cycle_count}/{repeat_count}")
                if task_config and task_config.get("SelectedAccountsInfo"):
                    current_cookies = task_config.get("SelectedAccountsInfo")
                else:
                    current_cookies = read_file(config.COOKIE_FILE)
                    if selected_uids:
                        current_cookies = [c for c in current_cookies if c.split("|")[0] in selected_uids]

                if not current_cookies:
                    print(" Danh sách tài khoản đã chọn trống.")
                    break

                batch_id = 0
                for i in range(0, len(current_cookies), max_threads):
                    batch = current_cookies[i:i+max_threads]
                    proxy_turn = f"{cycle_count}_{batch_id}"
                    print(f"\n Đang chạy đợt {batch_id + 1} (gồm {len(batch)} tài khoản)...")
                    with ThreadPoolExecutor(max_workers=max_threads) as executor:
                        futures = []
                        for idx, cookie in enumerate(batch):
                            slot_index = idx % max_threads
                            futures.append(executor.submit(run_account_task, cookie, slot_index, max_limit, is_edit_comment, execution_mode=1, warmup_time_sec=None, cycle_count=proxy_turn, task_config=task_config))
                        for f in futures:
                            f.result()
                    
                    accounts_processed += len(batch)
                    batch_id += 1

                    # Kiểm tra Reset DCOM sau mỗi đợt (chỉ KiotProxy)
                    if is_reset_dcom and proxy_method == 2 and reset_dcom_after > 0:
                        if accounts_processed >= reset_dcom_after:
                            print(f"\n Đã chạy {accounts_processed} tài khoản. Đang thực hiện Reset DCOM để lấy IP mới...")
                            try:
                                import subprocess
                                result = subprocess.run(["net", "stop", "RasMan"], capture_output=True, text=True, timeout=15)
                                time.sleep(2)
                                result = subprocess.run(["net", "start", "RasMan"], capture_output=True, text=True, timeout=15)
                                print(f" Reset DCOM hoàn tất. Đợi 10s cho kết nối ổn định...")
                                time.sleep(10)
                                # Xóa cache KiotProxy để buộc lấy IP mới
                                with KIOT_PROXY_LOCK:
                                    KIOT_PROXY_CACHE.clear()
                                accounts_processed = 0  # reset bộ đếm
                            except Exception as e:
                                print(f" Lỗi khi Reset DCOM: {e}")
                
                print(f" Đã chạy hết vòng {cycle_count}. Nghỉ 60s trước khi vòng mới...")
                time.sleep(60) 
                cycle_count += 1
                
            print(" Đã hoàn thành cấu hình tiến trình Spam Comment Groups.")
            sys.exit(0)