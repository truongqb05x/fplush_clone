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

def type_human_like(driver, text):
    """Giả lập gõ phím từng chữ như người thật, xử lý xuống dòng cho Facebook"""
    for char in text:
        actions = ActionChains(driver)
        if char == '\n':
            # Shift + Enter để xuống dòng trong comment FB mà không bị gửi
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
        else:
            actions.send_keys(char).perform()
        time.sleep(random.uniform(0.1, 0.4))

def process_group_cycle(driver, uid, group_id, is_edit_comment="yes"):
    try:
        # Xử lý nếu group_id đã là full URL (ví dụ https://www.facebook.com/groups/xxxx/)
        if group_id.startswith("http"):
            # Chuẩn hóa URL để lấy link gốc của group (loại bỏ các sub-path như /posts/, /permalink/...)
            m = re.match(r"(https?://(?:www\.|m\.)?facebook\.com/groups/[^/]+)/?", group_id)
            if m:
                base_url = m.group(1).rstrip("/") + "/"
            else:
                base_url = group_id.split("?")[0].rstrip("/") + "/"
        else:
            base_url = f"https://www.facebook.com/groups/{group_id}/"

        target_url = f"{base_url}?sorting_setting=CHRONOLOGICAL"

        print(f"[{uid}]  Quét group: {target_url}...")
        driver.get(target_url)
        
        # Đợi modal (nếu có) xuất hiện, thử nhiều lần trong 8 giây
        print(f"[{uid}] ⏳ Đang kiểm tra modal chào mừng nhóm...")
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
                        print(f"[{uid}] 🔘 Đã đóng modal giới thiệu/chào mừng của nhóm.")
                        modal_closed = True
                        time.sleep(1)
                        break
                if modal_closed:
                    break
            except Exception:
                pass
        
        # 1. Đợi feed hiện (nhiều lớp bảo vệ)
        print(f"[{uid}]  Đang đợi nội dung nhóm hiển thị...")
        feed_selectors = ["div[role='feed']", "div[data-pagelet^='FeedUnit']", "div[aria-label='Nội dung nhúm']", "div[aria-label='Feed of Group']"]
        feed_found = False
        for selector in feed_selectors:
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                feed_found = True
                print(f"[{uid}] ✅ Đã tìm thấy Feed bằng selector: {selector}")
                break
            except: continue
        
        if not feed_found:
            print(f"[{uid}] ⚠️ Không tìm thấy Feed container cụ thể, thử cuộn mù...")

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
        for attempt in range(2): # Thử tối đa 2 lần (lần 2 sẽ reload)
            if attempt > 0:
                print(f"[{uid}] 🔄 Không tìm thấy bài viết, thử reload trang và quét lại lần {attempt + 1}...")
                driver.refresh()
                time.sleep(10)

            print(f"[{uid}] 📜 Bắt đầu cuộn và quét bài viết (Lần thử {attempt + 1}/2)...")
            consecutive_skip_count = 0
            for scan_idx in range(20): # Thử 20 lần cuộn
                # Cuộn xuống
                scroll_dist = random.randint(400, 600)
                driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                print(f"[{uid}]   ⬇️ Đã cuộn xuống {scroll_dist}px (Lần {scan_idx+1}/20)...")
                time.sleep(4) # Chờ load content
                
                candidates = driver.find_elements(By.CSS_SELECTOR, 'a[role="link"]:not([data-scanned="true"])')
                print(f"[{uid}]   🔍 Tìm thấy {len(candidates)} link tiềm năng trên màn hình.")
                
                for cand in candidates:
                    try:
                        text = cand.text
                        href = cand.get_attribute('href')
                        
                        # Pattern thời gian mở rộng
                        time_regex = r'(\d+\s*(phút|giờ|ngày|tuần|tháng|năm|h|d|w|m|y|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)|vừa xong|Hôm qua|Just now|Yesterday)'
                        is_time = re.search(time_regex, text, re.I)
                        is_post_url = href and ("/posts/" in href or "/permalink/" in href or "story_fbid" in href)

                        if is_time or is_post_url:
                            # KIỂM TRA ĐỘ TƯƠI CỦA BÀI VIẾT (Chỉ lấy bài < 24 giờ)
                            is_young = True
                            if is_time:
                                age_text = text.lower()
                                # Các từ khóa chỉ thời gian cũ (> 24h)
                                old_keywords = ["ngày", "tháng", "năm", "hôm qua", "tuần", "day", "yesterday", "week", "month", "year"]
                                if any(kw in age_text for kw in old_keywords):
                                    is_young = False
                                # Kiểm tra ký hiệu 'd' (days) trong tiếng Anh (ví dụ: 1d, 2d)
                                elif re.search(r'\d+\s*d', age_text) and not re.search(r'\d+\s*(h|min|s|giây|phút|giờ)', age_text):
                                    is_young = False
                            
                            if not is_young:
                                print(f"[{uid}]     ⏩ Bỏ qua bài quá cũ (>24h): {text[:30]}...")
                                print(f"[{uid}] 🛑 Phát hiện bài viết cũ. Lập tức chuyển sang group khác.")
                                return False

                            is_first_post_evaluated = False
                            driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", cand)
                            print(f"[{uid}]     🔗 Phù hợp: {text[:20]}... (URL: {href[:40]})")
                            
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
                                        print(f"[{uid}] ⭐ THÀNH CÔNG: Tìm thấy bài viết chưa comment: {pid}")
                                        consecutive_skip_count = 0 # Reset khi tìm thấy bài mới
                                        collected_links.add(real_url)
                                        break
                                    else:
                                        print(f"[{uid}] ⏭️ Bỏ qua {pid} vì đã comment trước đó.")
                                        consecutive_skip_count += 1
                                        if consecutive_skip_count >= 10:
                                            print(f"[{uid}] 🛑 Đã bỏ qua liên tiếp {consecutive_skip_count} bài viết. Dừng account này.")
                                            return "STOP_ACCOUNT"
                                else:
                                    print(f"[{uid}] ⚠️ Link không phải permalink bài viết: {real_url[:50]}")
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
        image_groups_file = "resources/image_groups.txt"
        is_image_comment = False
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
            print(f"[{uid}] 📝 Chế độ No-Edit: Sử dụng nội dung từ {target_content_file}")
        else:
            # Nếu có edit, lấy ngẫu nhiên từ stt.txt như cũ
            with FILE_LOCK:
                stt_lines = read_file("resources/stt.txt")
            content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"
            print(f"[{uid}] 📝 Chế độ Edit: Sử dụng nội dung ngẫu nhiên từ stt.txt")


        textbox_xpath = '//div[@role="textbox"]'
        comment_input = wait_for_element_with_retry(driver, By.XPATH, textbox_xpath, timeout=15)
        if comment_input:
            print(f"[{uid}] ✍️ Đang xử lý comment...")
            time.sleep(random.uniform(5, 10))

            if is_image_comment:
                # === CHẾ ĐỘ COMMENT ẢNH ===
                ActionChains(driver).move_to_element(comment_input).click().perform()
                time.sleep(random.uniform(2, 4))

                # Chọn ảnh ngẫu nhiên từ thư mục resources/images/
                images_dir = "resources/images"
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
                    print(f"[{uid}] 📎 Tìm thấy input file qua nút 'Đính kèm ảnh'.")
                except Exception:
                    pass

                # Cách 2: Tìm trong #focused-state-actions-list (comment toolbar)
                if not file_input:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, "#focused-state-actions-list input[type='file']")
                        if els:
                            file_input = els[0]
                            print(f"[{uid}] 📎 Tìm thấy input file trong #focused-state-actions-list.")
                    except Exception:
                        pass

                # Cách 3: Tìm trong form comment (form[role='presentation'])
                if not file_input:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, "form[role='presentation'] input[type='file']")
                        if els:
                            file_input = els[0]
                            print(f"[{uid}] 📎 Tìm thấy input file trong form comment.")
                    except Exception:
                        pass

                if not file_input:
                    print(f"[{uid}] ❌ Không tìm thấy input file của comment để upload ảnh.")
                    return False

                file_input.send_keys(chosen_image)
                print(f"[{uid}]  Đang chờ ảnh upload hoàn tất...")
                time.sleep(random.uniform(5, 8))

                # Click nút gửi comment (trở nên enabled sau khi có ảnh đính kèm)
                submitted = False
                for submit_xpath in [
                    "//div[@id='focused-state-composer-submit']//div[@role='button' and not(@aria-disabled='true')]",
                    "//div[@aria-label='Đăng bình luận' and @role='button' and not(@aria-disabled='true')]",
                    "//div[@aria-label='Post comment' and @role='button' and not(@aria-disabled='true')]",
                ]:
                    try:
                        btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_xpath)))
                        btn.click()
                        submitted = True
                        print(f"[{uid}] ✅ Đã gửi comment ảnh thành công.")
                        break
                    except: continue

                if not submitted:
                    print(f"[{uid}] ⚠️ Không tìm thấy nút gửi, thử Enter fallback.")
                    ActionChains(driver).send_keys(Keys.ENTER).perform()

                time.sleep(15)
            else:
                # === CHẾ ĐỘ COMMENT TEXT (logic gốc) ===
                # Focus và gõ từng chữ
                ActionChains(driver).move_to_element(comment_input).click().perform()
                time_human_start = time.time()
                type_human_like(driver, content)

                # Gửi
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                print(f"[{uid}] ✅ Đã gửi comment (Gõ trong {int(time.time()-time_human_start)}s)")
                time.sleep(5)

            # --- Check for Feature Block Modal (Giờ bạn chưa dùng được tính năng này) ---
            try:
                block_modal_selectors = [
                    "//*[contains(text(), 'Giờ bạn chưa dùng được tính năng này')]",
                    "//*[contains(text(), 'chưa dùng được tính năng này')]",
                    "//*[contains(text(), 'giới hạn tần suất bạn đăng bài')]"
                ]
                block_found = False
                for sel in block_modal_selectors:
                    if driver.find_elements(By.XPATH, sel):
                        block_found = True
                        break
                
                if block_found:
                    print(f"[{uid}] ⚠️ Phát hiện modal chặn tính năng của Facebook!")
                    try:
                        ok_btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='OK']")
                        if ok_btns:
                            ok_btns[0].click()
                            print(f"[{uid}] 🔘 Đã click OK trên modal chặn tính năng.")
                            time.sleep(2)
                    except Exception as e_click_ok:
                        print(f"[{uid}] ⚠️ Lỗi khi click nút OK trên modal chặn: {e_click_ok}")
                    return "BLOCK_MODAL_DETECTED"
            except Exception as e_block:
                print(f"[{uid}] ⚠️ Lỗi khi check modal chặn tính năng: {e_block}")

            # --- Check for Membership Questions Modal (Xem xét quyền tham gia) ---
            try:
                modal_selectors = [
                    "//div[@aria-label='Xem xét quyền tham gia']",
                    "//*[contains(text(), 'Xem xét quyền tham gia')]"
                ]
                modal_found = False
                for sel in modal_selectors:
                    if driver.find_elements(By.XPATH, sel):
                        modal_found = True
                        break
                
                if modal_found:
                    print(f"[{uid}] 🚩 Phát hiện modal 'Xem xét quyền tham gia'. Đang xử lý trả lời câu hỏi...")
                    # 1. Điền "ok" vào toàn bộ textarea trong modal
                    textareas = driver.find_elements(By.TAG_NAME, "textarea")
                    for ta in textareas:
                        try:
                            if ta.is_displayed():
                                ta.send_keys("ok")
                                time.sleep(random.uniform(1, 2))
                        except: pass
                    
                    # 2. Nhấn nút Gửi
                    submit_btn_xpath = "//div[@aria-label='Gửi' and @role='button']"
                    submit_btns = driver.find_elements(By.XPATH, submit_btn_xpath)
                    if submit_btns:
                        submit_btns[0].click()
                        print(f"[{uid}] ✅ Đã nhấn 'Gửi' modal. Thoát luôn không chỉnh sửa và không lưu ID.")
                        time.sleep(3)
                        return False # Trả về False để không lưu history và skip edit
                    else:
                        print(f"[{uid}] ⚠️ Không tìm thấy nút 'Gửi' trong modal. Thoát.")
                        return False
            except Exception as e_modal:
                print(f"[{uid}] ⚠️ Lỗi khi xử lý modal trả lời câu hỏi: {e_modal}")
            
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
                    
                    print(f"[{uid}] ✍️ Sửa thành nội dung từ {target_content_file}...")
                    type_human_like(driver, new_content)
                    time.sleep(1)
                    box.send_keys(Keys.ENTER)
                    print(f"[{uid}] ✅ Đã sửa comment thành công.")
                    time.sleep(3)
                except Exception as e_edit:
                    print(f"[{uid}] ⚠️ Lỗi quy trình sửa comment: {e_edit}")
            else:
                if is_image_comment:
                    print(f"[{uid}] ⏩ Bỏ qua bước sửa comment (Chế độ Comment Ảnh - không hỗ trợ edit).")
                else:
                    print(f"[{uid}] ⏩ Bỏ qua bước sửa comment (Chế độ No-Edit).")
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

def process_keyword_search(driver, uid, keyword, is_edit_comment="yes"):
    try:
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        # URL search với filter "Recent Posts"
        target_url = f"https://www.facebook.com/search/top?q={encoded_keyword}&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"

        print(f"[{uid}] 🔍 Đang tìm kiếm keyword: {keyword}...")
        driver.get(target_url)
        
        # 1. Đợi kết quả hiện
        print(f"[{uid}]  Đang đợi kết quả tìm kiếm hiển thị...")
        time.sleep(7)
        
        collected_links = set()
        history_file = "resources/commented.txt"
        selected_pid = None
        
        with FILE_LOCK:
            commented_ids = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    commented_ids = set(l.strip() for l in f if l.strip())

        # 2. Scan & Scroll loop (Tương tự Mode 1)
        print(f"[{uid}] 📜 Bắt đầu cuộn và quét bài viết từ kết quả tìm kiếm...")
        consecutive_skip_count = 0
        is_first_post_evaluated = True
        for scan_idx in range(10): # Thử 10 lần quét cho keyword
            candidates = driver.find_elements(By.CSS_SELECTOR, 'a[role="link"]:not([data-scanned="true"])')
            print(f"[{uid}]   🔍 Tìm thấy {len(candidates)} link mới tiềm năng...")
            
            for cand in candidates:
                try:
                    text = cand.text
                    href = cand.get_attribute('href')
                    if not text or not href: continue

                    # Pattern thời gian
                    time_regex = r'(\d+\s*(phút|giờ|ngày|tuần|tháng|năm|h|d|w|m|y|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)|vừa xong|Hôm qua|Just now|Yesterday)'
                    is_time = re.search(time_regex, text, re.I)
                    
                    # Log nhẹ để biết đang xét gì
                    # print(f"[{uid}]      DEBUG: text='{text[:20]}', href='{href[:40]}'")

                    if is_time:
                        clean_text = text.replace('\n', ' ')
                        print(f"[{uid}]      🕒 Phát hiện link thời gian: '{clean_text}'")
                        # KIỂM TRA ĐỘ TƯƠI
                        is_young = True
                        age_text = text.lower()
                        old_keywords = ["ngày", "tháng", "năm", "hôm qua", "tuần", "day", "yesterday", "week", "month", "year"]
                        if any(kw in age_text for kw in old_keywords):
                            is_young = False
                        elif re.search(r'\d+\s*d', age_text) and not re.search(r'\d+\s*(h|min|s|giây|phút|giờ)', age_text):
                            is_young = False
                        
                        if not is_young:
                            print(f"[{uid}]      ⏩ Bỏ qua bài cũ: {text}")
                            driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", cand)
                            print(f"[{uid}] 🛑 Phát hiện bài viết cũ. Lập tức chuyển sang keyword/nhóm khác.")
                            return False

                        is_first_post_evaluated = False
                        print(f"[{uid}]      🎯 Phù hợp! Đang mở tab mới để kiểm tra ID...")
                        driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", cand)
                        
                        # Click new tab để lấy ID
                        ActionChains(driver).key_down(Keys.CONTROL).click(cand).key_up(Keys.CONTROL).perform()
                        time.sleep(5)
                        
                        curr = driver.current_window_handle
                        if len(driver.window_handles) > 1:
                            new_w = [w for w in driver.window_handles if w != curr][-1]
                            driver.switch_to.window(new_w)
                            time.sleep(3)
                            real_url = driver.current_url.split("?")[0]
                            print(f"[{uid}]      🔗 URL bài viết: {real_url}")
                            driver.close()
                            driver.switch_to.window(curr)

                            # Check ID - Regex linh hoạt hơn cho Search page
                            # TRƯỚC HẾT: Bỏ qua nếu là link trang chủ group (không phải bài viết cụ thể)
                            if "/groups/" in real_url and real_url.strip("/").split("/")[-2] == "groups":
                                # VD: .../groups/123/ -> skip
                                print(f"[{uid}]      ⏩ Bỏ qua link trang chủ nhóm: {real_url}")
                                continue

                            # Bỏ qua link reel
                            if "/reel/" in real_url:
                                print(f"[{uid}]      ⏩ Bỏ qua link reel: {real_url}")
                                continue

                            m = re.search(r"(?:/posts/|/permalink/|story_fbid=|/groups/\d+/posts/|/watch/|/videos/)([^/?&]+)", real_url)
                            if not m:
                                # Một số link search có thể có dạng khác, nhưng phải đảm bảo có dấu hiệu bài viết
                                if any(x in real_url for x in ["/posts/", "/permalink/", "story_fbid", "/watch/", "/videos/"]):
                                     # Lấy phần tử cuối cùng có vẻ là ID (số hoặc pfbid)
                                     parts = real_url.strip("/").split("/")
                                     if parts:
                                         m_id = parts[-1]
                                         if len(m_id) > 5: # ID thường dài
                                             pid = m_id
                                         else:
                                             m = None
                                     else:
                                         m = None
                            
                            if m and not isinstance(m, str):
                                pid = m.group(1)
                            elif 'pid' in locals() and pid:
                                pass # Đã lấy từ logic parts
                            else:
                                pid = None

                            if pid:
                                if pid not in commented_ids:
                                    print(f"[{uid}] ⭐ THÀNH CÔNG: Tìm thấy bài viết chưa comment: {pid}")
                                    collected_links.add(real_url)
                                    selected_pid = pid
                                    break
                                else:
                                    print(f"[{uid}] ⏭️ Bỏ qua {pid} vì đã comment trước đó.")
                                    consecutive_skip_count += 1
                                    if consecutive_skip_count >= 10:
                                        print(f"[{uid}] 🛑 Bỏ qua liên tiếp {consecutive_skip_count} bài. Dừng keyword này.")
                                        return "STOP_KEYWORD"
                            else:
                                print(f"[{uid}] ⚠️ Không trích xuất được ID từ URL: {real_url}")
                except Exception as e_cand:
                    # print(f"[{uid}] ⚠️ Lỗi khi duyệt candidate: {e_cand}")
                    pass
            
            if collected_links: break

            # Nếu chưa tìm thấy link và chưa hết lượt quét, thực hiện cuộn để tải thêm
            if scan_idx < 9:
                scroll_dist = random.randint(400, 600)
                driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                print(f"[{uid}]   ⬇️ Cuộn lần {scan_idx+1}/10...")
                time.sleep(5)

        if not collected_links:
            print(f"[{uid}] ⚠️ Không tìm thấy bài viết mới cho keyword: {keyword}")
            return False

        # 3. Comment logic (Reuse logic from process_group_cycle)
        post_url = list(collected_links)[0]
        if selected_pid:
            with FILE_LOCK:
                with open(history_file, "a", encoding="utf-8") as f: f.write(f"{selected_pid}\n")
            print(f"[{uid}] 💾 Đã lưu lịch sử {selected_pid} (Dùng chung toàn bộ tool).")

        driver.get(post_url)
        time.sleep(5)
        
        target_content_file = "resources/edit_stt.txt"
        
        # Lấy nội dung comment
        if is_edit_comment == "no":
            content = "Check inbox nhé"
            if os.path.exists(target_content_file):
                with open(target_content_file, "r", encoding="utf-8-sig") as f:
                    content = f.read().strip()
        else:
            with FILE_LOCK:
                stt_lines = read_file("resources/stt.txt")
            content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"


        textbox_xpath = '//div[@role="textbox"]'
        comment_input = wait_for_element_with_retry(driver, By.XPATH, textbox_xpath, timeout=15)
        if comment_input:
            print(f"[{uid}] ✍️ Đang gõ nội dung...")
            time.sleep(random.uniform(5, 10))
            ActionChains(driver).move_to_element(comment_input).click().perform()
            type_human_like(driver, content)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(5)
            
            # Edit logic
            if is_edit_comment == "yes":
                try:
                    comment_text_xpath = f"//*[contains(text(), '{content}')]"
                    posted_comment = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, comment_text_xpath)))
                    actions = ActionChains(driver)
                    actions.move_to_element(posted_comment).perform()
                    time.sleep(1)
                    menu_xpath = "//div[@aria-label='Chỉnh sửa hoặc xóa bình luận này' or @aria-label='Edit or delete this comment']"
                    menu_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, menu_xpath)))
                    menu_btn.click()
                    time.sleep(2)
                    edit_xpath = "//span[contains(text(), 'Chỉnh sửa') or contains(text(), 'Edit')]"
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, edit_xpath))).click()
                    time.sleep(3)
                    box = driver.switch_to.active_element
                    box.send_keys(Keys.CONTROL, "a")
                    box.send_keys(Keys.BACKSPACE)
                    new_content = "Check inbox nhé"
                    if os.path.exists(target_content_file):
                        with open(target_content_file, "r", encoding="utf-8-sig") as f:
                            new_content = f.read().strip()
                    type_human_like(driver, new_content)
                    time.sleep(1)
                    box.send_keys(Keys.ENTER)
                    print(f"[{uid}] ✅ Đã sửa comment keyword thành công.")
                    time.sleep(3)
                except Exception as e_edit:
                    print(f"[{uid}] ⚠️ Lỗi sửa comment keyword: {e_edit}")

            # Save history (Đã lưu sớm ở trên)
            return True

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi keyword search: {e}")
    return False


def process_page_cycle(driver, uid, page_id, is_edit_comment="yes", comment_mode="text"):
    """
    Mode 8: Truy cập trang Facebook Page (facebook.com/<page_id>),
    cuộn tìm bài mới nhất (<24h), rồi comment (text từ edit_stt.txt hoặc ảnh).

    Args:
        driver: Selenium WebDriver instance
        uid: User ID của tài khoản đang chạy
        page_id: ID hoặc username của Page Facebook
        is_edit_comment: "yes" / "no" - có sửa comment sau khi đăng không
        comment_mode: "text" (nội dung từ edit_stt.txt) hoặc "image" (ảnh từ resources/images/)

    Returns:
        True nếu comment thành công, False nếu thất bại,
        "BLOCK_MODAL_DETECTED" nếu bị chặn tính năng
    """
    try:
        # Chuẩn hóa URL của page
        if page_id.startswith("http"):
            base_url = page_id.rstrip("/")
        else:
            base_url = f"https://www.facebook.com/{page_id.strip('/')}"

        # Thêm tham số sắp xếp theo thời gian mới nhất
        target_url = f"{base_url}"

        print(f"[{uid}] 📄 [MODE 8] Truy cập Page: {target_url}...")
        driver.get(target_url)

        # Đợi feed của page hiện ra
        print(f"[{uid}]  Đang đợi feed của Page hiển thị...")
        feed_selectors = [
            "div[role='feed']",
            "div[data-pagelet^='FeedUnit']",
            "div[data-pagelet='ProfileTimeline']",
            "div[aria-label='Feed']",
        ]
        feed_found = False
        for selector in feed_selectors:
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                feed_found = True
                print(f"[{uid}] ✅ Đã tìm thấy Feed bằng selector: {selector}")
                break
            except:
                continue

        if not feed_found:
            print(f"[{uid}] ⚠️ Không tìm thấy Feed container, thử cuộn mù...")

        collected_links = set()
        history_file = "resources/commented.txt"

        # Load lịch sử đã comment
        with FILE_LOCK:
            commented_ids = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    commented_ids = set(l.strip() for l in f if l.strip())

        # Scan & Scroll loop — tương tự Mode 1
        for attempt in range(2):
            if attempt > 0:
                print(f"[{uid}] 🔄 Reload và quét lại lần {attempt + 1}...")
                driver.refresh()
                time.sleep(10)

            print(f"[{uid}] 📜 Bắt đầu cuộn và quét bài viết (Lần thử {attempt + 1}/2)...")
            consecutive_skip_count = 0

            for scan_idx in range(20):  # Tối đa 20 lần cuộn
                scroll_dist = random.randint(400, 600)
                driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                print(f"[{uid}]   ⬇️ Cuộn xuống {scroll_dist}px (Lần {scan_idx + 1}/20)...")
                time.sleep(4)

                candidates = driver.find_elements(
                    By.CSS_SELECTOR, 'a[role="link"]:not([data-scanned="true"])'
                )
                print(f"[{uid}]   🔍 Tìm thấy {len(candidates)} link tiềm năng trên màn hình.")

                for cand in candidates:
                    try:
                        text = cand.text
                        href = cand.get_attribute("href")

                        time_regex = r'(\d+\s*(phút|giờ|ngày|tuần|tháng|năm|h|d|w|m|y|min|mins|hour|hours|day|days|week|weeks|month|months|year|years)|vừa xong|Hôm qua|Just now|Yesterday)'
                        is_time = re.search(time_regex, text, re.I)
                        is_post_url = href and (
                            "/posts/" in href
                            or "/permalink/" in href
                            or "story_fbid" in href
                            or "/videos/" in href
                        )

                        if is_time or is_post_url:
                            # Kiểm tra độ tươi (<24h)
                            is_young = True
                            if is_time:
                                age_text = text.lower()
                                old_keywords = [
                                    "ngày", "tháng", "năm", "hôm qua", "tuần",
                                    "day", "yesterday", "week", "month", "year"
                                ]
                                if any(kw in age_text for kw in old_keywords):
                                    is_young = False
                                elif re.search(r'\d+\s*d', age_text) and not re.search(
                                    r'\d+\s*(h|min|s|giây|phút|giờ)', age_text
                                ):
                                    is_young = False

                            if not is_young:
                                print(f"[{uid}]     ⏩ Bỏ qua bài cũ (>24h): {text[:30]}...")
                                print(f"[{uid}] 🛑 Phát hiện bài viết cũ. Dừng tìm kiếm.")
                                return False

                            driver.execute_script(
                                "arguments[0].setAttribute('data-scanned', 'true')", cand
                            )
                            print(f"[{uid}]     🔗 Phù hợp: {text[:20]}... (URL: {href[:50]})")

                            # Mở tab mới để lấy URL thực
                            ActionChains(driver).key_down(Keys.CONTROL).click(cand).key_up(Keys.CONTROL).perform()
                            time.sleep(4)

                            curr = driver.current_window_handle
                            if len(driver.window_handles) > 1:
                                new_w = [w for w in driver.window_handles if w != curr][-1]
                                driver.switch_to.window(new_w)
                                time.sleep(2)
                                full_url = driver.current_url  # Giữ nguyên full URL (bao gồm query params)
                                driver.close()
                                driver.switch_to.window(curr)

                                # Trích xuất post ID từ full URL (bao gồm permalink.php?story_fbid=)
                                pid = None

                                # Ưu tiên: story_fbid trong query params (permalink.php?story_fbid=XXXX)
                                sfbid = re.search(r'[?&]story_fbid=([^&]+)', full_url)
                                if sfbid:
                                    pid = sfbid.group(1)
                                else:
                                    # Fallback: /posts/ID hoặc /permalink/ID hoặc /videos/ID trong path
                                    m = re.search(r"(?:/posts/|/permalink/|/videos/)([^/?&]+)", full_url)
                                    if m:
                                        pid = m.group(1)

                                # URL để điều hướng: nếu là permalink.php giữ nguyên full URL, còn lại bỏ query
                                if "permalink.php" in full_url:
                                    nav_url = full_url  # Giữ nguyên vì story_fbid là bắt buộc
                                else:
                                    nav_url = full_url.split("?")[0]

                                if pid:
                                    if pid not in commented_ids:
                                        print(f"[{uid}] ⭐ Tìm thấy bài viết chưa comment: {pid}")
                                        consecutive_skip_count = 0
                                        collected_links.add(nav_url)
                                        break
                                    else:
                                        print(f"[{uid}] ⏭️ Bỏ qua {pid} — đã comment trước đó.")
                                        consecutive_skip_count += 1
                                        if consecutive_skip_count >= 10:
                                            print(f"[{uid}] 🛑 Bỏ qua liên tiếp {consecutive_skip_count} bài. Dừng page này.")
                                            return False
                                else:
                                    print(f"[{uid}] ⚠️ Không trích xuất được ID từ: {full_url[:80]}")
                    except Exception:
                        pass

                if collected_links:
                    break

            if collected_links:
                break

        if not collected_links:
            print(f"[{uid}] ⚠️ Không tìm thấy bài viết nào phù hợp (<24h) trên page này.")
            return False

        # ===== XÁC ĐỊNH CHẾ ĐỘ COMMENT =====
        target_content_file = "resources/edit_stt.txt"
        is_image_comment = (comment_mode == "image")

        # Truy cập bài viết
        post_url = list(collected_links)[0]
        driver.get(post_url)
        time.sleep(5)

        # Lấy nội dung comment text
        if is_edit_comment == "no" or is_image_comment:
            content = "Check inbox nhé"  # Fallback
            if os.path.exists(target_content_file):
                with open(target_content_file, "r", encoding="utf-8-sig") as f:
                    content = f.read().strip()
            print(f"[{uid}] 📝 Sử dụng nội dung từ {target_content_file}")
        else:
            with FILE_LOCK:
                stt_lines = read_file("resources/stt.txt")
            content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"
            print(f"[{uid}] 📝 Chế độ Edit: Nội dung ngẫu nhiên từ stt.txt")

        # Tìm textbox comment
        textbox_xpath = '//div[@role="textbox"]'
        comment_input = wait_for_element_with_retry(driver, By.XPATH, textbox_xpath, timeout=15)

        if not comment_input:
            print(f"[{uid}] ❌ Không tìm thấy ô comment. Bỏ qua bài viết này.")
            return False

        print(f"[{uid}] ✍️ Đang xử lý comment...")
        time.sleep(random.uniform(5, 10))

        if is_image_comment:
            # === CHẾ ĐỘ COMMENT ẢNH ===
            ActionChains(driver).move_to_element(comment_input).click().perform()
            time.sleep(random.uniform(2, 4))

            images_dir = "resources/images"
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
            available_images = []
            if os.path.exists(images_dir):
                available_images = [
                    os.path.abspath(os.path.join(images_dir, img_f))
                    for img_f in os.listdir(images_dir)
                    if img_f.lower().endswith(image_extensions)
                ]

            if not available_images:
                print(f"[{uid}] ❌ Không có ảnh nào trong thư mục '{images_dir}'. Bỏ qua.")
                return False

            chosen_image = random.choice(available_images)
            print(f"[{uid}] 🖼️ Chọn ảnh: {os.path.basename(chosen_image)}")

            file_input = None
            try:
                attach_btn = driver.find_element(
                    By.XPATH,
                    "//div[@aria-label='Đính kèm một ảnh hoặc video' or @aria-label='Attach a photo or video']/ancestor::li//input[@type='file']"
                )
                file_input = attach_btn
                print(f"[{uid}] 📎 Tìm thấy input file qua nút 'Đính kèm ảnh'.")
            except Exception:
                pass

            if not file_input:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, "#focused-state-actions-list input[type='file']")
                    if els:
                        file_input = els[0]
                        print(f"[{uid}] 📎 Tìm thấy input file trong #focused-state-actions-list.")
                except Exception:
                    pass

            if not file_input:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, "form[role='presentation'] input[type='file']")
                    if els:
                        file_input = els[0]
                        print(f"[{uid}] 📎 Tìm thấy input file trong form comment.")
                except Exception:
                    pass

            if not file_input:
                print(f"[{uid}] ❌ Không tìm thấy input file để upload ảnh.")
                return False

            file_input.send_keys(chosen_image)
            print(f"[{uid}]  Đang chờ ảnh upload hoàn tất...")
            time.sleep(random.uniform(5, 8))

            submitted = False
            for submit_xpath in [
                "//div[@id='focused-state-composer-submit']//div[@role='button' and not(@aria-disabled='true')]",
                "//div[@aria-label='Đăng bình luận' and @role='button' and not(@aria-disabled='true')]",
                "//div[@aria-label='Post comment' and @role='button' and not(@aria-disabled='true')]",
            ]:
                try:
                    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_xpath)))
                    btn.click()
                    submitted = True
                    print(f"[{uid}] ✅ Đã gửi comment ảnh thành công.")
                    break
                except:
                    continue

            if not submitted:
                print(f"[{uid}] ⚠️ Không tìm thấy nút gửi, thử Enter fallback.")
                ActionChains(driver).send_keys(Keys.ENTER).perform()

            time.sleep(15)

        else:
            # === CHẾ ĐỘ COMMENT TEXT ===
            ActionChains(driver).move_to_element(comment_input).click().perform()
            time_human_start = time.time()
            type_human_like(driver, content)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            print(f"[{uid}] ✅ Đã gửi comment text (Gõ trong {int(time.time() - time_human_start)}s)")
            time.sleep(5)

        # --- Kiểm tra Modal chặn tính năng ---
        try:
            block_modal_selectors = [
                "//*[contains(text(), 'Giờ bạn chưa dùng được tính năng này')]",
                "//*[contains(text(), 'chưa dùng được tính năng này')]",
                "//*[contains(text(), 'giới hạn tần suất bạn đăng bài')]",
            ]
            block_found = False
            for sel in block_modal_selectors:
                if driver.find_elements(By.XPATH, sel):
                    block_found = True
                    break
            if block_found:
                print(f"[{uid}] ⚠️ Phát hiện modal chặn tính năng của Facebook!")
                try:
                    ok_btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='OK']")
                    if ok_btns:
                        ok_btns[0].click()
                        time.sleep(2)
                except Exception:
                    pass
                return "BLOCK_MODAL_DETECTED"
        except Exception as e_block:
            print(f"[{uid}] ⚠️ Lỗi khi check modal chặn: {e_block}")

        # --- Edit & Re-comment (chỉ khi comment text và is_edit_comment == "yes") ---
        if is_edit_comment == "yes" and not is_image_comment:
            try:
                print(f"[{uid}] 🔄 Đang bắt đầu quy trình Sửa & Re-comment...")
                comment_text_xpath = f"//*[contains(text(), '{content}')]"
                posted_comment = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, comment_text_xpath))
                )
                ActionChains(driver).move_to_element(posted_comment).perform()
                time.sleep(1)

                menu_xpath = "//div[@aria-label='Chỉnh sửa hoặc xóa bình luận này' or @aria-label='Edit or delete this comment']"
                menu_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, menu_xpath)))
                menu_btn.click()
                time.sleep(2)

                edit_xpath = "//span[contains(text(), 'Chỉnh sửa') or contains(text(), 'Edit')]"
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, edit_xpath))).click()
                time.sleep(3)

                box = driver.switch_to.active_element
                box.send_keys(Keys.CONTROL, "a")
                box.send_keys(Keys.BACKSPACE)
                time.sleep(1)

                new_content = "Check inbox nhé"
                if os.path.exists(target_content_file):
                    with open(target_content_file, "r", encoding="utf-8-sig") as f:
                        new_content = f.read().strip()

                print(f"[{uid}] ✍️ Sửa thành nội dung từ {target_content_file}...")
                type_human_like(driver, new_content)
                time.sleep(1)
                box.send_keys(Keys.ENTER)
                print(f"[{uid}] ✅ Đã sửa comment thành công.")
                time.sleep(3)
            except Exception as e_edit:
                print(f"[{uid}] ⚠️ Lỗi quy trình sửa comment page: {e_edit}")

        # Lưu lịch sử — hỗ trợ cả permalink.php?story_fbid= (page) và /posts/ (group)
        sfbid_match = re.search(r'[?&]story_fbid=([^&]+)', post_url)
        if sfbid_match:
            pid = sfbid_match.group(1)
        else:
            path_match = re.search(r"(?:/posts/|/permalink/|/videos/)([^/?&]+)", post_url)
            pid = path_match.group(1) if path_match else None

        if pid:
            with FILE_LOCK:
                with open(history_file, "a", encoding="utf-8") as f:
                    f.write(f"{pid}\n")
            print(f"[{uid}] 💾 Đã lưu lịch sử {pid}")

        return True  # THÀNH CÔNG

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi page cycle: {e}")
    return False

def process_ttc_cycle(driver, uid, job_link, job_id, is_edit_comment="yes", comment_mode="text"):
    """
    Mode 9: Truy cập trực tiếp link từ TTC, comment (text từ edit_stt.txt hoặc ảnh).

    Args:
        driver: Selenium WebDriver instance
        uid: User ID của tài khoản đang chạy
        job_link: Link bài viết từ TTC
        job_id: ID post từ TTC (để lưu lịch sử)
        is_edit_comment: "yes" / "no"
        comment_mode: "text" hoặc "image"

    Returns:
        True nếu comment thành công, False nếu thất bại,
        "BLOCK_MODAL_DETECTED" nếu bị chặn tính năng
    """
    try:
        print(f"[{uid}] 📄 [MODE 9] Truy cập bài viết TTC: {job_link}...")
        driver.get(job_link)
        time.sleep(5)

        # Check if the resolved URL is a reel
        if "/reel/" in driver.current_url:
            print(f"[{uid}]  Bỏ qua link vì Facebook chuyển hướng đến reel (chưa hỗ trợ): {driver.current_url}")
            return False

        # ===== XÁC ĐỊNH CHẾ ĐỘ COMMENT =====
        target_content_file = "resources/edit_stt.txt"
        is_image_comment = (comment_mode == "image")
        history_file = "resources/ttc_commented.txt"

        # Lấy nội dung comment text
        if is_edit_comment == "no" or is_image_comment:
            content = "Check inbox nhé"  # Fallback
            if os.path.exists(target_content_file):
                with open(target_content_file, "r", encoding="utf-8-sig") as f:
                    content = f.read().strip()
            print(f"[{uid}] 📝 Sử dụng nội dung từ {target_content_file}")
        else:
            with FILE_LOCK:
                stt_lines = read_file("resources/stt.txt")
            content = random.choice(stt_lines) if stt_lines else "Up bài giúp b nhé"
            print(f"[{uid}] 📝 Chế độ Edit: Nội dung ngẫu nhiên từ stt.txt")

        # Tìm textbox comment
        textbox_xpath = '//div[@role="textbox"]'
        comment_input = wait_for_element_with_retry(driver, By.XPATH, textbox_xpath, timeout=15)

        if not comment_input:
            print(f"[{uid}] ❌ Không tìm thấy ô comment. Bỏ qua bài viết này.")
            return False

        print(f"[{uid}] ✍️ Đang xử lý comment...")
        time.sleep(random.uniform(5, 10))

        if is_image_comment:
            # === CHẾ ĐỘ COMMENT ẢNH ===
            ActionChains(driver).move_to_element(comment_input).click().perform()
            time.sleep(random.uniform(2, 4))

            images_dir = "resources/images"
            image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
            available_images = []
            if os.path.exists(images_dir):
                available_images = [
                    os.path.abspath(os.path.join(images_dir, img_f))
                    for img_f in os.listdir(images_dir)
                    if img_f.lower().endswith(image_extensions)
                ]

            if not available_images:
                print(f"[{uid}] ❌ Không có ảnh nào trong thư mục '{images_dir}'. Bỏ qua.")
                return False

            chosen_image = random.choice(available_images)
            print(f"[{uid}] 🖼️ Chọn ảnh: {os.path.basename(chosen_image)}")

            file_input = None
            try:
                attach_btn = driver.find_element(
                    By.XPATH,
                    "//div[@aria-label='Đính kèm một ảnh hoặc video' or @aria-label='Attach a photo or video']/ancestor::li//input[@type='file']"
                )
                file_input = attach_btn
            except Exception:
                pass

            if not file_input:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, "#focused-state-actions-list input[type='file']")
                    if els: file_input = els[0]
                except Exception:
                    pass

            if not file_input:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, "form[role='presentation'] input[type='file']")
                    if els: file_input = els[0]
                except Exception:
                    pass

            if not file_input:
                print(f"[{uid}] ❌ Không tìm thấy input file để upload ảnh.")
                return False

            file_input.send_keys(chosen_image)
            print(f"[{uid}]  Đang chờ ảnh upload hoàn tất...")
            time.sleep(random.uniform(5, 8))

            submitted = False
            for submit_xpath in [
                "//div[@id='focused-state-composer-submit']//div[@role='button' and not(@aria-disabled='true')]",
                "//div[@aria-label='Đăng bình luận' and @role='button' and not(@aria-disabled='true')]",
                "//div[@aria-label='Post comment' and @role='button' and not(@aria-disabled='true')]",
            ]:
                try:
                    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_xpath)))
                    btn.click()
                    submitted = True
                    print(f"[{uid}] ✅ Đã gửi comment ảnh thành công.")
                    break
                except:
                    continue

            if not submitted:
                print(f"[{uid}] ⚠️ Không tìm thấy nút gửi, thử Enter fallback.")
                ActionChains(driver).send_keys(Keys.ENTER).perform()

            time.sleep(15)

        else:
            # === CHẾ ĐỘ COMMENT TEXT ===
            ActionChains(driver).move_to_element(comment_input).click().perform()
            time_human_start = time.time()
            type_human_like(driver, content)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            print(f"[{uid}] ✅ Đã gửi comment text (Gõ trong {int(time.time() - time_human_start)}s)")
            time.sleep(5)

        # --- Kiểm tra Modal chặn tính năng ---
        try:
            block_modal_selectors = [
                "//*[contains(text(), 'Giờ bạn chưa dùng được tính năng này')]",
                "//*[contains(text(), 'chưa dùng được tính năng này')]",
                "//*[contains(text(), 'giới hạn tần suất bạn đăng bài')]",
            ]
            block_found = False
            for sel in block_modal_selectors:
                if driver.find_elements(By.XPATH, sel):
                    block_found = True
                    break
            if block_found:
                print(f"[{uid}] ⚠️ Phát hiện modal chặn tính năng của Facebook!")
                try:
                    ok_btns = driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='OK']")
                    if ok_btns:
                        ok_btns[0].click()
                        time.sleep(2)
                except Exception:
                    pass
                return "BLOCK_MODAL_DETECTED"
        except Exception as e_block:
            print(f"[{uid}] ⚠️ Lỗi khi check modal chặn: {e_block}")

        # --- Edit & Re-comment (chỉ khi comment text và is_edit_comment == "yes") ---
        if is_edit_comment == "yes" and not is_image_comment:
            try:
                print(f"[{uid}] 🔄 Đang bắt đầu quy trình Sửa & Re-comment...")
                comment_text_xpath = f"//*[contains(text(), '{content}')]"
                posted_comment = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, comment_text_xpath))
                )
                ActionChains(driver).move_to_element(posted_comment).perform()
                time.sleep(1)

                menu_xpath = "//div[@aria-label='Chỉnh sửa hoặc xóa bình luận này' or @aria-label='Edit or delete this comment']"
                menu_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, menu_xpath)))
                menu_btn.click()
                time.sleep(2)

                edit_xpath = "//span[contains(text(), 'Chỉnh sửa') or contains(text(), 'Edit')]"
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, edit_xpath))).click()
                time.sleep(3)

                box = driver.switch_to.active_element
                box.send_keys(Keys.CONTROL, "a")
                box.send_keys(Keys.BACKSPACE)
                time.sleep(1)

                new_content = "Check inbox nhé"
                if os.path.exists(target_content_file):
                    with open(target_content_file, "r", encoding="utf-8-sig") as f:
                        new_content = f.read().strip()

                print(f"[{uid}] ✍️ Sửa thành nội dung từ {target_content_file}...")
                type_human_like(driver, new_content)
                time.sleep(1)
                box.send_keys(Keys.ENTER)
                print(f"[{uid}] ✅ Đã sửa comment thành công.")
                time.sleep(3)
            except Exception as e_edit:
                print(f"[{uid}] ⚠️ Lỗi quy trình sửa comment TTC: {e_edit}")

        # Lưu lịch sử TTC
        if job_id:
            with FILE_LOCK:
                with open(history_file, "a", encoding="utf-8") as f:
                    f.write(f"{job_id}\n")
            print(f"[{uid}] 💾 Đã lưu lịch sử TTC ID {job_id}")

        return True  # THÀNH CÔNG

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi process_ttc_cycle: {e}")
    return False
