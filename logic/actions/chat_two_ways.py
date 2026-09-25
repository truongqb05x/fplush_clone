# -*- coding: utf-8 -*-
import time
import os
import random
import base64
import logging
import string
import threading

logging.getLogger('seleniumwire').setLevel(logging.CRITICAL)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import config

# ===== MODULE-LEVEL SYNC STATE =====
_CHAT_SYNC_LOCK = threading.Lock()
_CHAT_SYNC: dict = {}


def _get_chat_sync(uid: str, target_uid: str) -> dict:
    """Lấy hoặc tạo bộ sync events cho cặp (uid, target_uid)."""
    pair_key = "_".join(sorted([uid, target_uid]))
    with _CHAT_SYNC_LOCK:
        if pair_key not in _CHAT_SYNC:
            _CHAT_SYNC[pair_key] = {
                'sender_added': threading.Event(),
                'receiver_accepted': threading.Event(),
                'sender_msg_sent': threading.Event(),
            }
        return _CHAT_SYNC[pair_key]


def run_two_way_chat(driver=None, uid: str = None, task_config: dict = None, cookie_lines=None):
    """
    Chat 2 chiều dùng driver đang chạy (không mở Chrome mới).

    Flow (giống logic gốc run_account_flow):
    ─────────────────────────────────────────
    Nếu đã bạn bè:
      Sender  → set sender_added
      Receiver → set receiver_accepted
    Nếu chưa bạn bè:
      Sender  → Add friend → set sender_added → chờ receiver_accepted
      Receiver → chờ sender_added → F5 tìm Confirm → set receiver_accepted

    Sau khi xử lý bạn bè:
      Sender  → chờ receiver_accepted → Nhắn tin → set sender_msg_sent
      Receiver → chờ sender_msg_sent → Trả lời tin nhắn
    """
    if driver is None or uid is None:
        return

    try:
        selected_info = task_config.get("SelectedAccountsInfo", []) if task_config else []
        if not selected_info or len(selected_info) < 2:
            return

        # Tìm uid khác trong batch
        target_uid = None
        for line in selected_info:
            other_uid = line.split("|")[0]
            if other_uid != uid:
                target_uid = other_uid
                break

        if not target_uid:
            return

        # UID nhỏ hơn = sender, lớn hơn = receiver (2 luồng luôn đồng ý)
        is_sender = uid < target_uid
        flow_type = "sender" if is_sender else "receiver"
        sync = _get_chat_sync(uid, target_uid)

        friends_xpath = (
            "//div[starts-with(@aria-label, 'Bạn bè') or "
            "starts-with(@aria-label, 'Friends') or "
            "contains(@aria-label, 'Bạn bè')]"
        )
        chat_box_xpath = (
            "//div[@role='textbox' and ("
            "contains(@aria-label, 'Write to') or "
            "contains(@aria-label, 'Viết cho') or "
            "contains(@aria-label, 'Message') or "
            "contains(@aria-label, 'Nhắn tin'))]"
        )

        # ─── BƯỚC 1: Truy cập và Kiểm tra trạng thái bạn bè ───
        action_success = False
        if is_sender:
            for attempt in range(3):
                driver.get(f"https://www.facebook.com/{target_uid}")
                time.sleep(random.randint(5, 8))

                is_friends = driver.find_elements(By.XPATH, friends_xpath)
                if is_friends:
                    print(f"[{uid}] ℹ️ Đã là bạn bè với {target_uid}.")
                    sync['sender_added'].set()
                    action_success = True
                    break

                cancel_xpath = (
                    "//div[starts-with(@aria-label, 'Cancel Request') or "
                    "starts-with(@aria-label, 'Cancel request') or "
                    "starts-with(@aria-label, 'Hủy lời mời')]"
                )
                if driver.find_elements(By.XPATH, cancel_xpath):
                    print(f"[{uid}] ℹ️ Đã gửi lời mời kết bạn từ trước.")
                    sync['sender_added'].set()
                    action_success = True
                    break

                add_xpath = (
                    "//div["
                    "starts-with(@aria-label, 'Add Friend') or "
                    "starts-with(@aria-label, 'Thêm bạn bè') or "
                    "starts-with(@aria-label, 'Kết bạn với') or "
                    ".//span[normalize-space()='Thêm bạn bè']"
                    "]"
                )
                add_btns = driver.find_elements(By.XPATH, add_xpath)
                if add_btns:
                    add_btn = add_btns[0]

                    try:
                        # Đưa nút vào vùng nhìn thấy trước khi click
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            add_btn
                        )
                        time.sleep(0.5)

                        # Ưu tiên click bằng Selenium
                        add_btn.click()

                    except Exception:
                        # Selenium click thất bại thì mới fallback sang JS click
                        try:
                            driver.execute_script(
                                "arguments[0].click();",
                                add_btn
                            )
                        except Exception as click_error:
                            print(
                                f"[{uid}] ⚠️ Không thể click nút Kết bạn: "
                                f"{click_error}"
                            )
                            continue

                    print(
                        f"[{uid}] 👥 Đã thực hiện click Kết bạn → "
                        f"{target_uid}. Đang xác minh..."
                    )

                    # Không đánh dấu thành công chỉ vì click không báo lỗi.
                    # Xác minh Facebook đã đổi sang trạng thái "Hủy lời mời".
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: len(
                                d.find_elements(
                                    By.XPATH,
                                    cancel_xpath
                                )
                            ) > 0
                        )

                        print(
                            f"[{uid}] ✅ Đã xác nhận lời mời kết bạn "
                            f"đã được gửi → {target_uid}."
                        )

                        sync['sender_added'].set()
                        action_success = True
                        break

                    except Exception:
                        print(
                            f"[{uid}] ⚠️ Click xong nhưng chưa thấy "
                            f"trạng thái 'Hủy lời mời'. Refresh kiểm tra..."
                        )

                        # Refresh để lấy lại trạng thái thật từ Facebook
                        try:
                            driver.refresh()
                            time.sleep(random.randint(4, 6))

                            if driver.find_elements(
                                By.XPATH,
                                cancel_xpath
                            ):
                                print(
                                    f"[{uid}] ✅ Sau khi refresh: "
                                    f"lời mời đã được gửi → {target_uid}."
                                )

                                sync['sender_added'].set()
                                action_success = True
                                break

                        except Exception as refresh_error:
                            print(
                                f"[{uid}] ⚠️ Lỗi khi refresh kiểm tra: "
                                f"{refresh_error}"
                            )

                        print(
                            f"[{uid}] 🔄 Chưa xác nhận được lời mời. "
                            f"Sẽ thử lại..."
                        )

                else:
                    print(
                        f"[{uid}] ⚠️ Không tìm thấy nút Kết bạn "
                        f"(lần {attempt + 1}). Thử lại..."
                    )
            
            if not action_success:
                print(f"[{uid}] ❌ Bỏ qua vì không thể gửi kết bạn sau 3 lần thử.")
                return

        else:
            driver.get(f"https://www.facebook.com/{target_uid}")
            time.sleep(random.randint(5, 8))

            is_friends = driver.find_elements(By.XPATH, friends_xpath)
            if is_friends:
                print(f"[{uid}] ℹ️ Đã là bạn bè với {target_uid}.")
                sync['receiver_accepted'].set()
            else:
                # Receiver: chờ sender add rồi mới confirm
                print(f"[{uid}] ⏳ Chờ {target_uid} gửi lời mời kết bạn (tối đa 2 phút)...")
                sync['sender_added'].wait(timeout=120)

                print(f"[{uid}] 🔍 Kiểm tra lời mời kết bạn...")
                confirm_xpath = (
                    "//div[starts-with(@aria-label, 'Xác nhận lời mời') or "
                    "starts-with(@aria-label, 'Confirm')]"
                )
                for attempt in range(3):
                    confirm_btns = driver.find_elements(By.XPATH, confirm_xpath)
                    if confirm_btns:
                        driver.execute_script("arguments[0].click();", confirm_btns[0])
                        print(f"[{uid}] ✅ Đã xác nhận kết bạn với {target_uid}.")
                        time.sleep(3)
                        break
                    else:
                        if attempt < 2:
                            print(f"[{uid}] ℹ️ Chưa thấy lời mời, F5 và chờ thêm...")
                            time.sleep(10)
                            driver.refresh()
                            time.sleep(8)
                        else:
                            print(f"[{uid}] ⚠️ Không tìm thấy lời mời sau nhiều lần thử.")
                sync['receiver_accepted'].set()

        # ─── BƯỚC 2: Đồng bộ trước khi nhắn tin ───
        if is_sender:
            print(f"[{uid}] ⏳ Chờ {target_uid} xác nhận kết bạn (tối đa 2 phút)...")
            sync['receiver_accepted'].wait(timeout=120)
        else:
            print(f"[{uid}] ⏳ Chờ {target_uid} nhắn tin trước (tối đa 2 phút)...")
            sync['sender_msg_sent'].wait(timeout=120)
            print(f"[{uid}] 💬 Bắt đầu tìm khung chat...")

        # ─── BƯỚC 3: Mở khung chat ───
        try:
            chat_box = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, chat_box_xpath))
            )
            print(f"[{uid}] 💬 Khung chat đã có sẵn.")
        except Exception:
            print(f"[{uid}] 🔍 Tìm nút Nhắn tin...")
            msg_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@aria-label='Message' or @aria-label='Nhắn tin']")
                )
            )
            driver.execute_script("arguments[0].click();", msg_btn)
            print(f"[{uid}] 💬 Đã nhấn nút Nhắn tin. Chờ khung chat...")
            time.sleep(5)
            chat_box = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, chat_box_xpath))
            )

        chat_box.click()
        demo_msg = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))

        print(f"[{uid}] ⌨️ Đang gõ tin nhắn...")
        for char in demo_msg:
            chat_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

        time.sleep(1)
        msg_displayed = False
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            print(f"[{uid}] 📤 Gửi tin nhắn... ({attempt}/{max_retries})")
            try:
                send_btn = driver.find_element(
                    By.XPATH,
                    "//div[@aria-label='Press enter to send' or @aria-label='Nhấn Enter để gửi']"
                )
                driver.execute_script("arguments[0].click();", send_btn)
            except Exception:
                from selenium.webdriver.common.keys import Keys
                chat_box.send_keys(Keys.ENTER)

            sent_xpath = f"//*[contains(text(), '{demo_msg}')]"
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, sent_xpath))
                )
                print(f"[{uid}] ✅ Đã gửi thành công!")
                msg_displayed = True
                if is_sender:
                    sync['sender_msg_sent'].set()
                break
            except Exception:
                print(f"[{uid}] ⚠️ Chưa thấy tin nhắn sau 30s. Thử lại...")

        if not msg_displayed:
            print(f"[{uid}] ❌ Gửi thất bại sau {max_retries} lần thử.")
            if is_sender:
                sync['sender_msg_sent'].set()  # unblock receiver dù thất bại

        print(f"[{uid}] 🏁 Hoàn thành chat 2 chiều. Tiếp tục comment group...")

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi chat 2 chiều: {e}")
        # Đảm bảo unblock luồng kia nếu lỗi
        try:
            if uid < target_uid:
                if not sync['sender_added'].is_set(): sync['sender_added'].set()
                if not sync['sender_msg_sent'].is_set(): sync['sender_msg_sent'].set()
            else:
                if not sync['receiver_accepted'].is_set(): sync['receiver_accepted'].set()
        except Exception:
            pass
