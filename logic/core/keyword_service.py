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
