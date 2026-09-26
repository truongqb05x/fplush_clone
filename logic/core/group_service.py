# -*- coding: utf-8 -*-
import time
import re
import os
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.file_utils import read_file
from utils.waiter import wait_for_element_with_retry
from utils.locks import FILE_LOCK
from utils.helpers import (
    is_checkpoint, is_soft_checkpoint, safe_url, type_human_like,
    is_logged_out
)
from actions.utils.like_actions import random_like_post
from actions.join_groups import join_single_group

def close_obstructing_modals(driver, uid):
    try:
        close_btns = driver.find_elements(By.XPATH, "//div[@aria-label='Đóng' and @role='button']")
        for btn in close_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
    except Exception:
        pass


def check_comment_status_after_post(driver, uid):
    """
    Kiểm tra sau khi gửi comment:
    - Modal chặn tính năng (Feature Block)
    - Modal Xem xét quyền tham gia (Membership)
    - Comment bị từ chối / chờ duyệt (dựa vào nút Chỉnh sửa)
    Return: "BLOCK_MODAL_DETECTED" | "MEMBERSHIP_MODAL" | "BLOCK_EDIT_DETECTED" | "OK"
    """
    # 1. Feature Block Modal
    try:
        block_modal_selectors = [
            "//*[contains(text(), 'Giờ bạn chưa dùng được tính năng này')]",
            "//*[contains(text(), 'chưa dùng được tính năng này')]",
            "//*[contains(text(), 'giới hạn tần suất bạn đăng bài')]"
        ]
        for sel in block_modal_selectors:
            if driver.find_elements(By.XPATH, sel):
                print(f"[{uid}] ⚠️ Phát hiện modal chặn tính năng của Facebook!")
                try:
                    ok_btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='OK']")
                    if ok_btns:
                        ok_btns[0].click()
                        time.sleep(2)
                except: pass
                return "BLOCK_MODAL_DETECTED"
    except Exception as e:
        print(f"[{uid}] ⚠️ Lỗi khi check modal chặn tính năng: {e}")

    # 2. Membership Modal (Xem xét quyền tham gia)
    try:
        membership_selectors = [
            "//div[@aria-label='Xem xét quyền tham gia']",
            "//*[contains(text(), 'Xem xét quyền tham gia')]"
        ]
        for sel in membership_selectors:
            if driver.find_elements(By.XPATH, sel):
                textareas = driver.find_elements(By.TAG_NAME, "textarea")
                for ta in textareas:
                    try:
                        if ta.is_displayed():
                            ta.send_keys("ok")
                            time.sleep(random.uniform(1, 2))
                    except: pass
                submit_btns = driver.find_elements(By.XPATH, "//div[@aria-label='Gửi' and @role='button']")
                if submit_btns:
                    submit_btns[0].click()
                    time.sleep(3)
                return "MEMBERSHIP_MODAL"
    except Exception as e:
        print(f"[{uid}] ⚠️ Lỗi khi xử lý modal thành viên: {e}")

    # 3. Kiểm tra nút Chỉnh sửa (comment được duyệt hay bị từ chối)
    time.sleep(random.uniform(10, 30))
    try:
        menu_xpath = "//div[@aria-label='Chỉnh sửa hoặc xóa bình luận này' or @aria-label='Edit or delete this comment' or @aria-label='Edit or delete this']"
        menu_btns = driver.find_elements(By.XPATH, menu_xpath)
        if menu_btns:
            menu_btn = menu_btns[-1]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu_btn)
            time.sleep(1)
            ActionChains(driver).move_to_element(menu_btn).perform()
            time.sleep(1)
            menu_btn.click()
            time.sleep(2)
            edit_opts = driver.find_elements(By.XPATH, "//span[contains(text(), 'Chỉnh sửa') or contains(text(), 'Edit')]")
            if not edit_opts:
                print(f"[{uid}] ❌ Không có tùy chọn 'Chỉnh sửa'. Comment có thể đã bị từ chối hoặc đang chờ duyệt.")
                return "BLOCK_EDIT_DETECTED"
            else:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
        else:
            print(f"[{uid}] ⚠️ Không tìm thấy nút menu của comment. Có thể đã bị từ chối/chờ duyệt.")
            return "BLOCK_EDIT_DETECTED"
    except Exception as e:
        print(f"[{uid}] ⚠️ Lỗi khi kiểm tra nút Chỉnh sửa: {e}")
        return "BLOCK_EDIT_DETECTED"

    return "OK"


def process_group_cycle(driver, uid, group_id, is_edit_comment="yes", task_config=None, comment_index=0):
    if is_logged_out(driver):
        print(f"[{uid}] ⚠️ Phát hiện tài khoản đã bị đăng xuất!")
        return "LOGGED_OUT"

    try:
        # Xử lý nếu group_id đã là full URL (ví dụ https://www.facebook.com/groups/xxxx/)
        if group_id.startswith("http"):
            # Chuẩn hóa URL để lấy link gốc của group
            m = re.match(r"(https?://(?:www\.|m\.)?facebook\.com/groups/[^/]+)/?", group_id)
            if m:
                base_url = m.group(1).rstrip("/") + "/"
            else:
                base_url = group_id.split("?")[0].rstrip("/") + "/"
            g_id = base_url.rstrip("/").split("/")[-1]
        else:
            base_url = f"https://www.facebook.com/groups/{group_id}/"
            g_id = group_id

        target_url = f"{base_url}?sorting_setting=CHRONOLOGICAL"

        # Truy cập danh sách nhóm đã tham gia
        joins_url = "https://www.facebook.com/groups/joins/?nav_source=tab"
        
        # Chuyển hướng bằng DOM click để an toàn và giống người thật hơn
        script_joins = f"""
            var a = document.createElement('a');
            a.href = '{joins_url}';
            document.body.appendChild(a);
            a.click();
        """
        driver.execute_script(script_joins)
        time.sleep(5)
        
        group_clicked = False
        for _ in range(4): # Cuộn vài lần để load thêm nhóm
            try:
                group_links = driver.find_elements(By.XPATH, f"//a[contains(@href, '/groups/{g_id}')]")
                for glnk in group_links:
                    if glnk.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", glnk)
                        time.sleep(1)
                        glnk.click()
                        group_clicked = True
                        break
                if group_clicked:
                    break
            except:
                pass
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
            
        if not group_clicked:
            # Nếu không tìm thấy trong danh sách đã tham gia, thử kiểm tra và tham gia nhóm
            print(f"[{uid}] Không tìm thấy trong danh sách nhóm đã tham gia. Tiến hành kiểm tra và tham gia...")
            join_single_group(driver, None, uid, g_id)
            time.sleep(2)
            
            script_target = f"""
                var a = document.createElement('a');
                a.href = '{target_url}';
                document.body.appendChild(a);
                a.click();
            """
            driver.execute_script(script_target)
        else:
            time.sleep(4)
            if "sorting_setting=CHRONOLOGICAL" not in driver.current_url:
                # Đảm bảo vào chế độ bài viết mới nhất
                script_target = f"""
                    var a = document.createElement('a');
                    a.href = '{target_url}';
                    document.body.appendChild(a);
                    a.click();
                """
                driver.execute_script(script_target)
        
        # Đợi modal (nếu có) xuất hiện, thử nhiều lần trong 8 giây
        modal_closed = False
        for _ in range(4): # Thử 4 lần, mỗi lần chờ 2 giây
            time.sleep(2)
            try:
                close_modal_xpath = "//div[@role='dialog']//div[@aria-label='Đóng' and @role='button']"
                close_btns = driver.find_elements(By.XPATH, close_modal_xpath)
                for btn in close_btns:
                    if btn.is_displayed():
                        # Dùng JavaScript click để chắc chắn không bị block bởi UI khác
                        driver.execute_script("arguments[0].click();", btn)
                        modal_closed = True
                        time.sleep(1)
                        break
                if modal_closed:
                    break
            except Exception:
                pass
        
        # 1. Đợi feed hiện (nhiều lớp bảo vệ)
        feed_selectors = ["div[role='feed']", "div[data-pagelet^='FeedUnit']", "div[aria-label='Nội dung nhúm']", "div[aria-label='Feed of Group']"]
        feed_found = False
        for selector in feed_selectors:
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                feed_found = True
                break
            except: continue
        

        collected_links = set()
        history_file = "resources/commented.txt"
        
        # Load history với Lock
        with FILE_LOCK:
            commented_ids = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    commented_ids = set(l.strip() for l in f if l.strip())

        # 2. Scan & Scroll loop
        is_first_post_evaluated = True
        
        # --- START DIRECT MODE ---
        if True:
            
            target_content_file = "resources/edit_stt.txt"
            special_groups_file = "resources/special_groups.txt"
            if os.path.exists(special_groups_file):
                with open(special_groups_file, "r", encoding="utf-8-sig") as f:
                    special_groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                is_special = any(item in group_id or item in target_url for item in special_groups)
                if is_special:
                    target_content_file = "resources/special_stt.txt"
                    print(f"[{uid}] 🌟 PHÁT HIỆN GROUP ĐẶC BIỆT! Sử dụng file: {target_content_file}")
            
            is_image_comment = False
            is_image_comment_with_text = False
            images_dir = "resources/images"
            if task_config:
                if task_config.get("IsImageComment"):
                    is_image_comment = True
                    images_dir = task_config.get("ImageFolderPath", "resources/images")
                    is_image_comment_with_text = task_config.get("IsImageCommentWithText", False)
                else:
                    image_group_uids = task_config.get("ImageGroupUids", [])
                    if image_group_uids:
                        is_image_comment = any(item in group_id or item in target_url for item in image_group_uids)
                        if is_image_comment:
                            print(f"[{uid}] 🖼️ PHÁT HIỆN GROUP ƯU TIÊN ẢNH (Text Mode)! Sử dụng chế độ comment bằng ảnh.")
                            images_dir = task_config.get("ImageFolderPath", "resources/images")
            else:
                image_groups_file = "resources/image_groups.txt"
                if os.path.exists(image_groups_file):
                    with open(image_groups_file, "r", encoding="utf-8-sig") as f:
                        image_groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    is_image_comment = any(item in group_id or item in target_url for item in image_groups)
                    if is_image_comment:
                        print(f"[{uid}] 🖼️ PHÁT HIỆN GROUP ẢNH! Sử dụng chế độ comment bằng ảnh.")

            for attempt in range(2):
                if attempt > 0:
                    driver.refresh()
                    time.sleep(10)
                
                comment_box_found = False
                is_permalink_fallback = False
                for scan_idx in range(20):
                    scroll_dist = random.randint(400, 600)
                    driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                    time.sleep(4)
                    
                    try:
                        # ƯU TIÊN 1: Tìm ô textbox TRƯỚC, nếu đã có sẵn thì KHÔNG CẦN click nút "Bình luận" (tránh bị chuyển sang bài viết)
                        comment_boxes = driver.find_elements(By.XPATH, "//div[@role='textbox' and @contenteditable='true' and not(@data-commented='true')]")
                        box_to_comment = None
                        
                        for box in comment_boxes:
                            if box.is_displayed():
                                aria_label = box.get_attribute("aria-label") or ""
                                if "viết gì đó" in aria_label.lower() or "write something" in aria_label.lower() or "tạo bài viết" in aria_label.lower() or "create a public post" in aria_label.lower():
                                    continue
                                box_to_comment = box
                                break
                        
                        # ƯU TIÊN 2: Nếu chưa có ô comment, mới thử click nút "Bình luận"
                        if not box_to_comment:
                            comment_btns = driver.find_elements(By.XPATH, "//div[@role='button' and (@aria-label='Bình luận' or @aria-label='Comment' or @aria-label='Viết bình luận' or @aria-label='Write a comment' or @aria-label='Để lại bình luận' or @aria-label='Leave a comment') and not(@data-scanned='true')]")
                            for btn in comment_btns:
                                if btn.is_displayed():
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                        time.sleep(1)
                                    except:
                                        pass
                                    driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", btn)
                                    driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(2)
                                    break # Chỉ click 1 nút rồi kiểm tra lại
                            
                            # Kiểm tra lại ô comment sau khi click
                            comment_boxes = driver.find_elements(By.XPATH, "//div[@role='textbox' and @contenteditable='true' and not(@data-commented='true')]")
                            for box in comment_boxes:
                                if box.is_displayed():
                                    aria_label = box.get_attribute("aria-label") or ""
                                    if "viết gì đó" in aria_label.lower() or "write something" in aria_label.lower() or "tạo bài viết" in aria_label.lower() or "create a public post" in aria_label.lower():
                                        continue
                                    box_to_comment = box
                                    break

                        # NẾU TÌM THẤY Ô COMMENT -> XỬ LÝ
                        if box_to_comment:
                            driver.execute_script("arguments[0].setAttribute('data-commented', 'true')", box_to_comment)
                            
                            delay1 = random.randint(1, 10)
                            time.sleep(delay1)
                            
                            close_obstructing_modals(driver, uid)
                            random_like_post(driver, uid)
                            
                            delay2 = random.randint(3, 5)
                            time.sleep(delay2)
                            
                            comment_input = box_to_comment
                                
                            # Cuộn ô comment ra giữa màn hình để tránh bị che bởi header/footer và click nhầm vào sticker
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
                                time.sleep(1)
                                driver.execute_script("window.scrollBy(0, 100);")
                                time.sleep(1)
                            except:
                                pass
                            
                            if task_config:
                                comment_list = task_config.get("CommentsList", [])
                                if comment_list:
                                    if task_config.get("IsSequentialComment"):
                                        idx = comment_index % len(comment_list)
                                        content = comment_list[idx]
                                    else:
                                        content = random.choice(comment_list)
                                else:
                                    content = "Check inbox nhé"
                            else:
                                if is_edit_comment == "no":
                                    content = "Check inbox nhé"
                                    if os.path.exists(target_content_file):
                                        with open(target_content_file, "r", encoding="utf-8-sig") as f:
                                            content = f.read().strip()
                                else:
                                    with FILE_LOCK:
                                        stt_lines = read_file("resources/stt.txt")
                                    content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"
                            
                            time.sleep(random.uniform(2, 5))
                            
                            # --- PERMALINK FALLBACK LOGIC ---
                            current_url = driver.current_url
                            if "/permalink/" in current_url or "/posts/" in current_url or "story_fbid=" in current_url:
                                m = re.search(r"(?:\/posts\/|\/permalink\/|story_fbid=)(\d+)", current_url)
                                if m:
                                    pid = m.group(1)
                                    if pid in commented_ids:
                                        print(f"[{uid}] ⏭️ Bỏ qua {pid} vì đã comment trước đó.")
                                        return False
                                    else:
                                        collected_links.add(current_url)
                                        is_permalink_fallback = True
                                        break
                            # ---------------------------------
                            
                            if is_image_comment:
                                # Click và focus vào ô comment để Facebook hiện nút Send (Submit)
                                driver.execute_script("arguments[0].click(); arguments[0].focus();", comment_input)
                                time.sleep(2)
                                
                                if is_image_comment_with_text and content:
                                    type_human_like(driver, content, element=comment_input)
                                    time.sleep(2)
                                
                                # images_dir đã được lấy từ task_config ở trên
                                image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
                                available_images = []
                                if os.path.exists(images_dir):
                                    available_images = [os.path.abspath(os.path.join(images_dir, img_f)) for img_f in os.listdir(images_dir) if img_f.lower().endswith(image_extensions)]
                                if not available_images:
                                    print(f"[{uid}] ❌ Không có ảnh. Bỏ qua.")
                                    return False
                                chosen_image = random.choice(available_images)
                                
                                file_input = None
                                
                                # Ưu tiên tìm input file TRONG CÙNG FORM với ô comment để không nhầm bài khác
                                try:
                                    parent_form = comment_input.find_element(By.XPATH, "./ancestor::form")
                                    if parent_form:
                                        els = parent_form.find_elements(By.XPATH, ".//input[@type='file']")
                                        if els:
                                            file_input = els[0]
                                except:
                                    pass
                                    
                                if not file_input:
                                    try:
                                        attach_btn = driver.find_element(By.XPATH, "//div[@aria-label='Đính kèm một ảnh hoặc video' or @aria-label='Attach a photo or video']/ancestor::li//input[@type='file']")
                                        file_input = attach_btn
                                    except: pass
                                if not file_input:
                                    try:
                                        els = driver.find_elements(By.CSS_SELECTOR, "#focused-state-actions-list input[type='file']")
                                        if els: file_input = els[0]
                                    except: pass
                                if not file_input:
                                    try:
                                        els = driver.find_elements(By.CSS_SELECTOR, "form[role='presentation'] input[type='file']")
                                        if els: file_input = els[0]
                                    except: pass
                                
                                if file_input:
                                    file_input.send_keys(chosen_image)
                                    submitted = False
                                    start_wait = time.time()
                                    while time.time() - start_wait < 30:
                                        for submit_xpath in [
                                            "//div[@id='focused-state-composer-submit']//div[@role='button' and not(@aria-disabled='true')]",
                                            "//div[@aria-label='Đăng bình luận' and @role='button' and not(@aria-disabled='true')]",
                                            "//div[@aria-label='Post comment' and @role='button' and not(@aria-disabled='true')]",
                                        ]:
                                            try:
                                                btn = driver.find_element(By.XPATH, submit_xpath)
                                                if btn.is_displayed():
                                                    btn.click()
                                                    submitted = True
                                                    break
                                            except: continue
                                        if submitted:
                                            break
                                        time.sleep(1)
                                    if not submitted:
                                        ActionChains(driver).send_keys(Keys.ENTER).perform()
                                    time.sleep(15)
                                else:
                                    print(f"[{uid}] ❌ Không tìm thấy input ảnh.")
                                    return False
                            else:
                                # Chỉ focus phần tử qua JS, sau đó gõ phím trực tiếp vào phần tử đó, bỏ qua click chuột!
                                driver.execute_script("arguments[0].click(); arguments[0].focus();", comment_input)
                                time.sleep(1)
                                type_human_like(driver, content, element=None)
                                ActionChains(driver).send_keys(Keys.ENTER).perform()
                                print(f"[{uid}] ✅ Đã gửi comment text trực tiếp.")
                                time.sleep(5)
                            
                            # ===== KIỂM TRA BỊ CHẶN / CHỜ DUYỆT (DIRECT MODE) =====
                            _status = check_comment_status_after_post(driver, uid)
                            if _status in ("BLOCK_MODAL_DETECTED", "BLOCK_EDIT_DETECTED"):
                                return _status
                            if _status == "MEMBERSHIP_MODAL":
                                return False
                            # ========================================================

                            comment_box_found = True
                            break
                    except Exception as e:
                        pass
                        
                    if comment_box_found or is_permalink_fallback:
                        break
                
                if comment_box_found or is_permalink_fallback:
                    break
            
            if comment_box_found:
                return True
            if not is_permalink_fallback:
                print(f"[{uid}] ⚠️ Không tìm thấy ô comment nào trực tiếp trong nhóm này.")
                return False
        # --- END DIRECT MODE ---
        for attempt in range(2): # Thử tối đa 2 lần (lần 2 sẽ reload)
            if collected_links: break # Bỏ qua quét link nếu đã có từ fallback
            if attempt > 0:
                print(f"[{uid}] 🔄 Không tìm thấy bài viết, thử reload trang và quét lại lần {attempt + 1}...")
                driver.refresh()
                time.sleep(10)

            consecutive_skip_count = 0
            for scan_idx in range(20): # Thử 20 lần cuộn
                # Cuộn xuống
                scroll_dist = random.randint(400, 600)
                driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                time.sleep(4) # Chờ load content
                
                candidates = driver.find_elements(By.CSS_SELECTOR, 'a[role="link"]:not([data-scanned="true"])')
                
                for cand in candidates:
                    try:
                        text = cand.text or ""
                        href = cand.get_attribute('href') or ""
                        aria_label = cand.get_attribute('aria-label') or ""
                        
                        # Pattern thời gian mở rộng
                        time_regex = r'(\d+\s*(phút|giờ|ngày|tuần|tháng|năm|h|d|w|m|y|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)|vừa xong|Hôm qua|Just now|Yesterday)'
                        is_time = re.search(time_regex, text, re.I)
                        
                        # Nhận diện thêm bằng aria-label Tiếng Anh (vd: "Monday, September 21, 2026 at 7:27 AM")
                        is_english_time = re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Yesterday|Just now).+(AM|PM|at)', aria_label, re.I)
                        
                        is_post_url = href and ("/posts/" in href or "/permalink/" in href or "story_fbid" in href or "comment_id=" in href)

                        if is_time or is_english_time or is_post_url:
                            # KIỂM TRA ĐỘ TƯƠI CỦA BÀI VIẾT (Chỉ lấy bài < 24 giờ)
                            is_young = True
                            
                            if text:
                                age_text = text.lower()
                                # Các từ khóa chỉ thời gian cũ (> 24h)
                                old_keywords = ["ngày", "tháng", "năm", "hôm qua", "tuần", "day", "days", "yesterday", "week", "weeks", "month", "months", "year", "years"]
                                if any(kw in age_text for kw in old_keywords):
                                    is_young = False
                                # Kiểm tra ký hiệu 'd', 'w', 'y' (days, weeks, years) trong tiếng Anh
                                elif re.search(r'\d+\s*(d|w|y)\b', age_text) and not re.search(r'\d+\s*(h|m|min|mins|s|giây|phút|giờ)\b', age_text):
                                    is_young = False
                                # Kiểm tra định dạng ngày tháng tuyệt đối của FB Tiếng Anh (vd: "September 18")
                                elif re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}', age_text):
                                    is_young = False
                            elif aria_label:
                                # Nếu không có text nhưng có aria-label, kiểm tra năm cũ
                                if "2023" in aria_label or "2024" in aria_label or "2025" in aria_label:
                                    is_young = False
                            
                            if not is_young:
                                print(f"[{uid}] 🛑 Bài viết cũ (>24h). Chuyển group khác.")
                                return False

                            is_first_post_evaluated = False
                            driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", cand)
                            
                            # Click new tab
                            ActionChains(driver).key_down(Keys.CONTROL).click(cand).key_up(Keys.CONTROL).perform()
                            time.sleep(4)
                            
                            curr = driver.current_window_handle
                            if len(driver.window_handles) > 1:
                                new_w = [w for w in driver.window_handles if w != curr][-1]
                                driver.switch_to.window(new_w)
                                time.sleep(2)
                                real_url = driver.current_url.split("?")[0]
                                driver.close()
                                driver.switch_to.window(curr)

                                # Check ID
                                m = re.search(r"(?:\/posts\/|\/permalink\/|story_fbid=)(\d+)", real_url)
                                if m:
                                    pid = m.group(1)
                                    if pid not in commented_ids:
                                        consecutive_skip_count = 0
                                        collected_links.add(real_url)
                                        break
                                    else:
                                        print(f"[{uid}] ⏭️ Bỏ qua {pid} vì đã comment trước đó.")
                                        consecutive_skip_count += 1
                                        if consecutive_skip_count >= 10:
                                            print(f"[{uid}] 🛑 Đã bỏ qua liên tiếp {consecutive_skip_count} bài viết. Dừng account này.")
                                            return "STOP_ACCOUNT"
                    except Exception:
                        pass
                
                if collected_links: break
            
            if collected_links:
                break


        if not collected_links:
            print(f"[{uid}] ⚠️ Không tìm thấy bài viết nào phù hợp (<24h) trong nhóm này.")
            return False

        # Xác định file nội dung đích (Special Group logic)
        target_content_file = "resources/edit_stt.txt"
        special_groups_file = "resources/special_groups.txt"
        if os.path.exists(special_groups_file):
            with open(special_groups_file, "r", encoding="utf-8-sig") as f:
                special_groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
            # Kiểm tra nếu group_id hoặc target_url chứa bất kỳ ID/Username nào trong danh sách
            is_special = any(item in group_id or item in target_url for item in special_groups)
            if is_special:
                target_content_file = "resources/special_stt.txt"
                print(f"[{uid}] 🌟 PHÁT HIỆN GROUP ĐẶC BIỆT! Sử dụng file: {target_content_file}")

        # Xác định chế độ comment ảnh (Image Group logic)
        is_image_comment = False
        is_image_comment_with_text = False
        images_dir = "resources/images"
        if task_config:
            if task_config.get("IsImageComment"):
                is_image_comment = True
                images_dir = task_config.get("ImageFolderPath", "resources/images")
                is_image_comment_with_text = task_config.get("IsImageCommentWithText", False)
            else:
                image_group_uids = task_config.get("ImageGroupUids", [])
                if image_group_uids:
                    is_image_comment = any(item in group_id or item in target_url for item in image_group_uids)
                    if is_image_comment:
                        print(f"[{uid}] 🖼️ PHÁT HIỆN GROUP ƯU TIÊN ẢNH! Sử dụng chế độ comment bằng ảnh.")
                        images_dir = task_config.get("ImageFolderPath", "resources/images")
        else:
            image_groups_file = "resources/image_groups.txt"
            if os.path.exists(image_groups_file):
                with open(image_groups_file, "r", encoding="utf-8-sig") as f:
                    image_groups = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                is_image_comment = any(item in group_id or item in target_url for item in image_groups)
                if is_image_comment:
                    print(f"[{uid}] 🖼️ PHÁT HIỆN GROUP ẢNH! Sử dụng chế độ comment bằng ảnh.")

        # Comment logic
        post_url = list(collected_links)[0]
        driver.get(post_url)
        time.sleep(5)
        
        # 3. Lấy nội dung comment
        if is_edit_comment == "no":
            # Nếu không edit, lấy trực tiếp nội dung từ file đích
            content = "Check inbox nhé" # Fallback
            if os.path.exists(target_content_file):
                with open(target_content_file, "r", encoding="utf-8-sig") as f:
                    content = f.read().strip()
        else:
            # Nếu có edit, lấy ngẫu nhiên từ stt.txt như cũ
            with FILE_LOCK:
                stt_lines = read_file("resources/stt.txt")
            content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"


        textbox_xpath = '//div[@role="textbox"]'
        comment_input = wait_for_element_with_retry(driver, By.XPATH, textbox_xpath, timeout=15)
        if comment_input:
            delay1 = random.randint(1, 10)
            time.sleep(delay1)
            
            close_obstructing_modals(driver, uid)
            random_like_post(driver, uid)
            
            delay2 = random.randint(3, 5)
            time.sleep(delay2)
            
            time.sleep(random.uniform(5, 10))
            
            # Cuộn trang xuống giữa màn hình và thêm 100px để tránh che khuất footer
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_input)
                time.sleep(1)
                driver.execute_script("window.scrollBy(0, 100);")
                time.sleep(1)
            except:
                pass

            if is_image_comment:
                # === CHẾ ĐỘ COMMENT ẢNH ===
                if is_image_comment_with_text and content:
                    driver.execute_script("arguments[0].focus();", comment_input)
                    time.sleep(1)
                    type_human_like(driver, content, element=comment_input)
                    time.sleep(2)
                    
                # Bỏ qua hoàn toàn việc click, vì Selenium có thể tương tác trực tiếp với input type=file
                pass

                # images_dir đã được lấy ở trên
                image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
                available_images = []
                if os.path.exists(images_dir):
                    available_images = [
                        os.path.abspath(os.path.join(images_dir, img_f))
                        for img_f in os.listdir(images_dir)
                        if img_f.lower().endswith(image_extensions)
                    ]

                if not available_images:
                    print(f"[{uid}] ❌ Không có ảnh nào trong thư mục '{images_dir}'. Bỏ qua group này.")
                    return False

                chosen_image = random.choice(available_images)
                print(f"[{uid}] 🖼️ Chọn ảnh: {os.path.basename(chosen_image)}")

                # Tìm input[type="file"] đúng của comment bar (tránh nhầm input của ô tạo bài viết)
                # Ưu tiên tìm trong #focused-state-actions-list (div riêng của comment area)
                file_input = None

                # Cách 1: Tìm qua button "Đính kèm ảnh" → ancestor li → input (chính xác nhất)
                try:
                    attach_btn = driver.find_element(By.XPATH,
                        "//div[@aria-label='Đính kèm một ảnh hoặc video' or @aria-label='Attach a photo or video']/ancestor::li//input[@type='file']"
                    )
                    file_input = attach_btn
                except Exception:
                    pass

                # Cách 2: Tìm trong #focused-state-actions-list (comment toolbar)
                if not file_input:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, "#focused-state-actions-list input[type='file']")
                        if els:
                            file_input = els[0]
                    except Exception:
                        pass

                # Cách 3: Tìm trong form comment (form[role='presentation'])
                if not file_input:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, "form[role='presentation'] input[type='file']")
                        if els:
                            file_input = els[0]
                    except Exception:
                        pass

                if not file_input:
                    print(f"[{uid}] ❌ Không tìm thấy input file của comment để upload ảnh.")
                    return False

                file_input.send_keys(chosen_image)
                submitted = False
                start_wait = time.time()
                while time.time() - start_wait < 30:
                    for submit_xpath in [
                        "//div[@id='focused-state-composer-submit']//div[@role='button' and not(@aria-disabled='true')]",
                        "//div[@aria-label='Đăng bình luận' and @role='button' and not(@aria-disabled='true')]",
                        "//div[@aria-label='Post comment' and @role='button' and not(@aria-disabled='true')]",
                    ]:
                        try:
                            btn = driver.find_element(By.XPATH, submit_xpath)
                            if btn.is_displayed():
                                btn.click()
                                submitted = True
                                break
                        except: continue
                    if submitted:
                        break
                    time.sleep(1)

                if not submitted:
                    print(f"[{uid}] ⚠️ Không tìm thấy nút gửi, thử Enter fallback.")
                    ActionChains(driver).send_keys(Keys.ENTER).perform()

                time.sleep(15)
            else:
                # === CHẾ ĐỘ COMMENT TEXT (logic gốc) ===
                driver.execute_script("arguments[0].focus();", comment_input)
                time.sleep(1)
                time_human_start = time.time()
                type_human_like(driver, content, element=comment_input)

                # Gửi
                ActionChains(driver).send_keys_to_element(comment_input, Keys.ENTER).perform()
                print(f"[{uid}] ✅ Đã gửi comment (Gõ trong {int(time.time()-time_human_start)}s)")
                time.sleep(5)

            # ===== KIỂM TRA BỊ CHẶN / CHỜ DUYỆT (LINK MODE) =====
            _status = check_comment_status_after_post(driver, uid)
            if _status in ("BLOCK_MODAL_DETECTED", "BLOCK_EDIT_DETECTED"):
                return _status
            if _status == "MEMBERSHIP_MODAL":
                return False
            # =================================================================

            # ================= START EDIT & RE-COMMENT =================
            if is_edit_comment == "yes" and not is_image_comment:
                try:
                    print(f"[{uid}] 🔄 Đang bắt đầu quy trình Sửa & Re-comment (Bulk Content)...")
                    # 1. Tìm comment vừa đăng (theo nội dung vừa gõ)
                    comment_text_xpath = f"//*[contains(text(), '{content}')]"
                    posted_comment = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, comment_text_xpath)))
                    
                    # Hover & Click Menu
                    actions = ActionChains(driver)
                    actions.move_to_element(posted_comment).perform()
                    time.sleep(1)
                    
                    menu_xpath = "//div[@aria-label='Chỉnh sửa hoặc xóa bình luận này' or @aria-label='Edit or delete this comment']"
                    menu_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, menu_xpath)))
                    menu_btn.click()
                    time.sleep(2)
                    
                    # Click Chỉnh sửa
                    edit_xpath = "//span[contains(text(), 'Chỉnh sửa') or contains(text(), 'Edit')]"
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, edit_xpath))).click()
                    time.sleep(3)
                    
                    # Xóa cũ, nhập mới qua active_element
                    box = driver.switch_to.active_element
                    box.send_keys(Keys.CONTROL, "a")
                    box.send_keys(Keys.BACKSPACE)
                    time.sleep(1)
                    
                    # LẤY TOÀN BỘ NỘI DUNG FILE ĐÍCH
                    new_content = "Check inbox nhé" # Fallback
                    if os.path.exists(target_content_file):
                        with open(target_content_file, "r", encoding="utf-8-sig") as f:
                            new_content = f.read().strip()
                    
                    type_human_like(driver, new_content, element=box)
                    time.sleep(1)
                    box.send_keys(Keys.ENTER)
                    print(f"[{uid}] ✅ Đã sửa comment thành công.")
                    time.sleep(3)
                except Exception as e_edit:
                    print(f"[{uid}] ⚠️ Lỗi quy trình sửa comment: {e_edit}")
            # ===========================================================

            # Save history với Lock
            pid_match = re.search(r"(?:\/posts\/|\/permalink\/|story_fbid=)(\d+)", post_url)
            
            if pid_match:
                pid = pid_match.group(1)
                with FILE_LOCK:
                    with open(history_file, "a", encoding="utf-8") as f: f.write(f"{pid}\n")
                print(f"[{uid}] 💾 Đã lưu lịch sử {pid} (Dùng chung toàn bộ tool).")
            return True # THÀNH CÔNG

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi group cycle: {e}")
    return False # THẤT BẠI
