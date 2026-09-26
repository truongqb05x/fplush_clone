import time
import random
import os
from utils.helpers import safe_url, is_checkpoint, is_soft_checkpoint, cleanup_seleniumwire
from utils.driver_utils import create_driver
from config import config
from utils.locks import FILE_LOCK
from utils.file_utils import read_file
from core.globals import *
from core.helpers import get_profile_path, remove_dead_account
from actions.feed_actions import warm_up_account
from core.automation_service import process_keyword_search, process_page_cycle, process_ttc_cycle, process_group_cycle
from actions.join_groups import join_single_group
from actions.out_group import out_groups_by_mode
from actions.read_notifications import read_one_random_notification
from actions.chat_two_ways import run_two_way_chat
from actions.login import login_with_credentials
from utils.scan_group import get_joined_groups

def dispatch_execution_mode(driver, wait, uid, execution_mode, max_comments, is_edit_comment, warmup_time_sec, keyword_list, group_join_list, out_group_mode, out_group_list, page_list, page_comment_mode, delete_page_after_comment, ttc_jobs, ttc_comment_mode, cycle_count, task_config, parts, win_pos, proxy_config, user_agent):
    is_dead = False
    # The verify_uid function was defined locally, we need to redefine it here since mode 5 uses it

    def verify_uid(dr, target_uid):
        curr_url = safe_url(dr)
        if target_uid in curr_url or f"profile.php?id={target_uid}" in curr_url or "/me" in curr_url: return True
        cookies = dr.get_cookies()
        if any(c['name'] == 'c_user' and str(c['value']) == str(target_uid) for c in cookies): return True
        ps = dr.page_source
        if f'"userID":"{target_uid}"' in ps or f'"ACCOUNT_ID":"{target_uid}"' in ps: return True
        return False
    if execution_mode == 2:
        print(f"[{uid}]  MODE 2: Profile created and Login verified. Success.")
        return True

    if execution_mode == 3:
        print(f"[{uid}] MODE 3: Tiến hành nuôi tài khoản trong {warmup_time_sec} giây...")
        warm_up_account(driver, uid, warmup_time=warmup_time_sec, cfg=task_config)
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
        
        idx = 0
        while idx < len(group_join_list):
            gid = group_join_list[idx].strip()
            if not gid:
                idx += 1
                continue
            
            try:
                success = join_single_group(driver, wait, uid, gid)
                if not success:
                    print(f"[{uid}] ⚠️ Lỗi khi tham gia {gid}, tiến hành thử lại...")
                    # Kiểm tra xem driver còn sống không
                    try:
                        _ = driver.current_url
                    except Exception:
                        print(f"[{uid}] ❌ Trình duyệt bị crash! Đang khởi tạo lại ngay...")
                        try:
                            cleanup_seleniumwire(driver)
                            driver.quit()
                        except: pass
                        
                        profile_path = get_profile_path(uid)
                        driver, wait, _ = create_driver(
                            user_data_dir=profile_path, 
                            proxy_config=proxy_config, 
                            window_pos=win_pos,
                            user_agent=user_agent
                        )
                        driver.get("https://www.facebook.com/")
                        time.sleep(5)
                        
                        # Check checkpoint và login giống như lúc mở tab
                        current_url = safe_url(driver)
                        if "checkpoint" in current_url.lower() or is_checkpoint(driver):
                            if is_soft_checkpoint(driver):
                                print(f"[{uid}]  Đã xử lý CHECKPOINT TẠM THỜI (Dismiss). Đang load lại trang...")
                                driver.get("https://www.facebook.com/")
                                time.sleep(5)
                                if is_checkpoint(driver):
                                    print(f"[{uid}]  Vẫn còn CHECKPOINT. Bỏ qua tài khoản.")
                                    return "SKIPPED_SOFT_CHECKPOINT"
                            else:
                                print(f"[{uid}]  PHÁT HIỆN CHECKPOINT CỨNG -> Xóa tài khoản.")
                                is_dead = True
                                return False
                                
                        if not verify_uid(driver, uid):
                            driver.get("https://www.facebook.com/me")
                            time.sleep(5)
                            if not verify_uid(driver, uid):
                                print(f"[{uid}] Session lỗi hoặc không trùng UID sau khi khởi tạo lại. Đang xóa tài khoản...")
                                is_dead = True
                                return False
                        
                        continue # Lặp lại cùng gid
                    
                    time.sleep(3)
                    continue # Lặp lại cùng gid
            except Exception as e:
                print(f"[{uid}] ❌ Lỗi crash: {e}, đang khởi tạo lại...")
                try:
                    cleanup_seleniumwire(driver)
                    driver.quit()
                except: pass
                
                profile_path = get_profile_path(uid)
                driver, wait, _ = create_driver(
                    user_data_dir=profile_path, 
                    proxy_config=proxy_config, 
                    window_pos=win_pos,
                    user_agent=user_agent
                )
                driver.get("https://www.facebook.com/")
                time.sleep(5)
                
                # Check checkpoint và login giống như lúc mở tab
                current_url = safe_url(driver)
                if "checkpoint" in current_url.lower() or is_checkpoint(driver):
                    if is_soft_checkpoint(driver):
                        print(f"[{uid}]  Đã xử lý CHECKPOINT TẠM THỜI (Dismiss). Đang load lại trang...")
                        driver.get("https://www.facebook.com/")
                        time.sleep(5)
                        if is_checkpoint(driver):
                            print(f"[{uid}]  Vẫn còn CHECKPOINT. Bỏ qua tài khoản.")
                            return "SKIPPED_SOFT_CHECKPOINT"
                    else:
                        print(f"[{uid}]  PHÁT HIỆN CHECKPOINT CỨNG -> Xóa tài khoản.")
                        is_dead = True
                        return False
                        
                if not verify_uid(driver, uid):
                    driver.get("https://www.facebook.com/me")
                    time.sleep(5)
                    if not verify_uid(driver, uid):
                        print(f"[{uid}] Session lỗi hoặc không trùng UID sau khi khởi tạo lại. Đang xóa tài khoản...")
                        is_dead = True
                        return False
                        
                continue

            idx += 1
            if idx < len(group_join_list):
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
                            pages_file = getattr(config, "PAGES_FILE", "resources/id_pages.txt")
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
                                history_file = getattr(config, "TTC_COMMENTED_FILE", "resources/ttc_commented.txt")
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

    if execution_mode == 10:
        print(f"[{uid}]  MODE 10: Upload Avatar...")
        from actions.avatar_utils import upload_avatar_and_status
        from config.config import AVATAR_FOLDER, AVATAR_STT_FILE
        result = upload_avatar_and_status(driver, wait, AVATAR_FOLDER, AVATAR_STT_FILE)
        if result:
            print(f"[{uid}]  MODE 10: Upload avatar thành công.")
        else:
            print(f"[{uid}]  MODE 10: Upload avatar thất bại.")
        return result

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

    if execution_mode == 1 and task_config:
        # print(f"[{uid}]  Sử dụng cấu hình từ UI...")
        g_list = task_config.get("GroupUids", [])
        
        if task_config.get("ActionBeforePost"):
            cfg = task_config.get("ConfigBeforePost", {})
            if cfg.get("IsScrollFeed"):
                print(f"[{uid}]  Thực hiện hành động TRƯỚC khi post: Lướt Newfeed")
                feed_time = cfg.get("ScrollTimeMax", 60)
                warm_up_account(driver, uid, warmup_time=feed_time, cfg=cfg)
            if cfg.get("IsReadNotifications"):
                print(f"[{uid}]  Thực hiện hành động TRƯỚC khi post: Đọc thông báo")
                count = cfg.get("ReadNotificationsCount", 1)
                for _ in range(count):
                    read_one_random_notification(driver, uid)
            if cfg.get("IsChatWithEachOther"):
                print(f"[{uid}]  Thực hiện hành động TRƯỚC khi post: Nhắn tin 2 chiều")
                run_two_way_chat(driver=driver, uid=uid, task_config=task_config)
                
    else:
        warm_up_account(driver, uid, warmup_time=warmup_time_sec)
        
        if uid in SCANNED_GROUPS_CACHE:
            print(f"[{uid}]  Sử dụng danh sách group đã quét từ cache...")
            g_list = list(SCANNED_GROUPS_CACHE[uid])
        else:
            print(f"[{uid}]  UID LIVE. Bắt đầu quét danh sách group đã tham gia...")
            
            # Lấy danh sách group động từ utils/scan_group.py
            scanned_groups = get_joined_groups(driver, uid=uid)
            if scanned_groups == "LOGGED_OUT":
                print(f"[{uid}]  Phát hiện tài khoản bị đăng xuất trong lúc quét nhóm! Thử đăng nhập lại...")
                password = parts[1] if len(parts) > 1 else ""
                if password and login_with_credentials(driver, uid, password):
                    print(f"[{uid}]  Đăng nhập lại thành công! Quét lại nhóm...")
                    scanned_groups = get_joined_groups(driver, uid=uid)
                    if scanned_groups == "LOGGED_OUT":
                        print(f"[{uid}]  Vẫn báo lỗi đăng xuất. Hủy account.")
                        is_dead = True
                        return False
                else:
                    print(f"[{uid}]  Đăng nhập lại thất bại. Hủy account.")
                    is_dead = True
                    return False
                    
            if not scanned_groups:
                print(f"[{uid}]  Không tìm thấy group nào đã tham gia. Thử dùng file group dự phòng...")
                with FILE_LOCK:
                    g_list = read_file(getattr(config, "GROUP_FILE", "resources/group.txt"))
            else:
                g_list = [g['uid'] if g['uid'] != "N/A" else g['link'] for g in scanned_groups]
                print(f"[{uid}]  Đã tìm thấy {len(g_list)} group.")

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
                        if not t_str: continue
                        if t_str == g_str or t_str in g_str or g_str in t_str:
                            match_found = True
                            break
                    if match_found:
                        filtered_g_list.append(g)
                g_list = filtered_g_list
                
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
        retry_group_count = 0
        found_and_commented = False
        
        while retry_group_count < 5:
            # Chọn group tiếp theo từ danh sách đã shuffle (đảm bảo không trùng)
            try:
                target_gid = next(group_iterator)
            except StopIteration:
                print(f"[{uid}]  Đã thử hết toàn bộ danh sách group.")
                break

            result = process_group_cycle(driver, uid, target_gid, is_edit_comment, task_config=task_config, comment_index=success_count)
            
            if result == "LOGGED_OUT":
                print(f"[{uid}]  Phát hiện tài khoản bị đăng xuất khi chuẩn bị comment! Thử đăng nhập lại...")
                password = parts[1] if len(parts) > 1 else ""
                if password and login_with_credentials(driver, uid, password):
                    print(f"[{uid}]  Đăng nhập lại thành công! Thử lại group này...")
                    continue
                else:
                    print(f"[{uid}]  Đăng nhập lại thất bại. Dừng account.")
                    is_dead = True
                    break
                    
            if result == "STOP_ACCOUNT":
                print(f"[{uid}]  Tín hiệu dừng account được kích hoạt. Đang thoát luồng...")
                found_and_commented = False
                break # Thoát khỏi retry_group_count loop
            
            if result == "BLOCK_MODAL_DETECTED":
                print(f"[{uid}]  Phát hiện modal chặn tính năng từ Facebook. Đang đưa tài khoản vào danh sách bỏ qua...")
                BLOCKED_ACCOUNTS.add(uid)
                found_and_commented = False
                break # Thoát khỏi retry_group_count loop
            
            if result == "BLOCK_EDIT_DETECTED":
                print(f"[{uid}]  Phát hiện comment bị từ chối/chờ duyệt. Xóa khỏi danh sách tài khoản được chọn trong UI chạy...")
                print(f"[{uid}] UI_REMOVE|{uid}")  # Tín hiệu để C# xóa account khỏi list chờ trong UI
                # Không gọi remove_dead_account(cookie_line) để không xóa trong file
                BLOCKED_ACCOUNTS.add(uid)
                found_and_commented = False
                break # Thoát khỏi retry_group_count loop
            
            if result is True:
                success_count += 1
                found_and_commented = True
                print(f"[{uid}]  Đã hoàn thành {success_count}/{max_comments} comment.")
                print(f" Comment thành công: {uid} | Group: {target_gid}")
                
                # ACTION SAU KHI POST
                if execution_mode == 1 and task_config and task_config.get("ActionAfterPost"):
                    cfg = task_config.get("ConfigAfterPost", {})
                    if cfg.get("IsScrollFeed"):
                        print(f"[{uid}]  Thực hiện hành động SAU khi post: Lướt Newfeed")
                        feed_time = cfg.get("ScrollTimeMax", 60)
                        warm_up_account(driver, uid, warmup_time=feed_time, cfg=cfg)
                    if cfg.get("IsReadNotifications"):
                        print(f"[{uid}]  Thực hiện hành động SAU khi post: Đọc thông báo")
                        count = cfg.get("ReadNotificationsCount", 1)
                        for _ in range(count):
                            read_one_random_notification(driver, uid)
                    if cfg.get("IsChatWithEachOther"):
                        print(f"[{uid}]  Thực hiện hành động SAU khi post: Nhắn tin 2 chiều")
                        run_two_way_chat(driver=driver, uid=uid, task_config=task_config)
                        
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
            
    return True, is_dead, driver
