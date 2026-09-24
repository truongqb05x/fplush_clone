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
            print(f"[{uid}]  Đang chờ ảnh upload hoàn tất và quét nút đăng bình luận (tối đa 30s)...")
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
                            print(f"[{uid}] ✅ Đã gửi comment ảnh thành công (sau {int(time.time() - start_wait)}s).")
                            break
                    except:
                        continue
                if submitted:
                    break
                time.sleep(1)

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
