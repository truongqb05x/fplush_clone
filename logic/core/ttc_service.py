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
