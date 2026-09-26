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
                'ready_sender': threading.Event(),
                'ready_receiver': threading.Event(),
                'chat_box_sender': threading.Event(),
                'chat_box_receiver': threading.Event(),
                'sender_added': threading.Event(),
                'receiver_accepted': threading.Event(),
                'sender_msg_sent': threading.Event(),
                'turn_1': threading.Event(),
                'turn_2': threading.Event(),
                'turn_3': threading.Event(),
                'turn_4': threading.Event(),
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

        uids = []
        for line in selected_info:
            parts = line.split("|")
            if parts:
                uids.append(parts[0])
        uids = list(dict.fromkeys(uids)) # Remove duplicates

        target_uid = None
        for i in range(len(uids)):
            if uids[i] == uid:
                if i % 2 == 0:
                    if i + 1 < len(uids):
                        target_uid = uids[i+1]
                else:
                    target_uid = uids[i-1]
                break

        if not target_uid:
            print(f"[{uid}] ⚠️ Không tìm thấy đối tác ghép cặp (có thể số lượng tài khoản là số lẻ). Bỏ qua chat 2 chiều.")
            return

        # UID nhỏ hơn = sender, lớn hơn = receiver (2 luồng luôn đồng ý)
        is_sender = uid < target_uid
        flow_type = "sender" if is_sender else "receiver"
        sync = _get_chat_sync(uid, target_uid)

        # --- BƯỚC ĐỒNG BỘ ĐẦU VÀO (Rendezvous) ---
        print(f"[{uid}] ⏳ Đang chờ {target_uid} vào luồng chat (tối đa 3 phút)...")
        if is_sender:
            sync['ready_sender'].set()
            if not sync['ready_receiver'].wait(timeout=180):
                print(f"[{uid}] ❌ Đối tác {target_uid} không vào luồng chat (có thể đang kẹt hoặc lỗi). Hủy bỏ chat 2 chiều.")
                sync['ready_sender'].clear() # Rút lại tín hiệu ready
                return
        else:
            sync['ready_receiver'].set()
            if not sync['ready_sender'].wait(timeout=180):
                print(f"[{uid}] ❌ Đối tác {target_uid} không vào luồng chat (có thể đang kẹt hoặc lỗi). Hủy bỏ chat 2 chiều.")
                sync['ready_receiver'].clear() # Rút lại tín hiệu ready
                return
                
        print(f"[{uid}] 🚀 Đã kết nối với {target_uid}. Bắt đầu thực hiện logic chat.")

        friends_xpath = (
            "//*["
            "(@role='button' or @role='combobox') and ("
            "starts-with(@aria-label, 'Bạn bè') or "
            "starts-with(@aria-label, 'Friends') or "
            "contains(@aria-label, 'Bạn bè')"
            ")]"
        )
        chat_box_xpath = (
            "//div[@role='textbox' and ("
            "contains(@aria-label, 'Write to') or "
            "contains(@aria-label, 'Viết cho') or "
            "contains(@aria-label, 'Message') or "
            "contains(@aria-label, 'Nhắn tin'))]"
        )

        # ─── BƯỚC 1: Truy cập và Kiểm tra trạng thái bạn bè ───
        cancel_xpath = (
            "//div[starts-with(@aria-label, 'Cancel Request') or "
            "starts-with(@aria-label, 'Cancel request') or "
            "starts-with(@aria-label, 'Hủy lời mời')]"
        )
        add_xpath = (
            "//*["
            "@role='button' and ("
            "starts-with(@aria-label, 'Add Friend') or "
            "starts-with(@aria-label, 'Thêm bạn bè') or "
            "starts-with(@aria-label, 'Kết bạn với') or "
            ".//span[normalize-space()='Thêm bạn bè']"
            ")]"
        )

        action_success = False
        if is_sender:
            for attempt in range(3):
                driver.get(f"https://www.facebook.com/{target_uid}")
                
                # Chờ trang load xong trạng thái bạn bè (tối đa 20s)
                try:
                    WebDriverWait(driver, 20).until(
                        lambda d: d.find_elements(By.XPATH, friends_xpath) or 
                                  d.find_elements(By.XPATH, cancel_xpath) or 
                                  d.find_elements(By.XPATH, add_xpath)
                    )
                except Exception:
                    pass # Hết thời gian chờ, chạy tiếp để loop dưới tự retry
                    
                time.sleep(random.randint(2, 4)) # Nghỉ thêm một chút cho DOM hoàn tất

                is_friends = driver.find_elements(By.XPATH, friends_xpath)
                if is_friends:
                    print(f"[{uid}] ℹ️ Đã là bạn bè với {target_uid}.")
                    sync['sender_added'].set()
                    action_success = True
                    break

                if driver.find_elements(By.XPATH, cancel_xpath):
                    print(f"[{uid}] ℹ️ Đã gửi lời mời kết bạn từ trước.")
                    sync['sender_added'].set()
                    action_success = True
                    break

                add_btns = driver.find_elements(By.XPATH, add_xpath)
                if add_btns:
                    add_btn = add_btns[0]
                    for btn in add_btns:
                        try:
                            if btn.is_displayed():
                                add_btn = btn
                                break
                        except Exception:
                            pass

                    try:
                        # Đưa nút vào vùng nhìn thấy trước khi click
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            add_btn
                        )
                        time.sleep(1)

                        try:
                            add_btn.click()
                        except:
                            driver.execute_script("arguments[0].click();", add_btn)

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
            # Receiver: chờ sender xử lý (kiểm tra bạn bè hoặc gửi lời mời) trước
            print(f"[{uid}] ⏳ Đang chờ {target_uid} gửi lời mời kết bạn (tối đa 2 phút)...")
            sync['sender_added'].wait(timeout=120)

            # Sau khi sender đã gửi xong, receiver mới bắt đầu vào tường của sender
            print(f"[{uid}] 🌐 Đã nhận tín hiệu từ Sender. Đang truy cập tường {target_uid}...")
            driver.get(f"https://www.facebook.com/{target_uid}")
            time.sleep(random.randint(5, 8))

            for attempt in range(3):
                # Luôn kiểm tra lại trạng thái bạn bè trước (vì có thể load lần đầu bị trượt)
                is_friends = driver.find_elements(By.XPATH, friends_xpath)
                if is_friends:
                    print(f"[{uid}] ℹ️ Đã là bạn bè với {target_uid}.")
                    sync['receiver_accepted'].set()
                    break

                print(f"[{uid}] 🔍 Kiểm tra nút Xác nhận lời mời kết bạn (lần {attempt+1})...")
                confirm_xpath = (
                    "//div[starts-with(@aria-label, 'Xác nhận lời mời') or "
                    "starts-with(@aria-label, 'Confirm')]"
                )
                confirm_btns = driver.find_elements(By.XPATH, confirm_xpath)
                if confirm_btns:
                    # Kích hoạt click bằng JS
                    driver.execute_script("arguments[0].click();", confirm_btns[0])
                    print(f"[{uid}] ✅ Đã xác nhận kết bạn với {target_uid}.")
                    time.sleep(3)
                    sync['receiver_accepted'].set()
                    break
                else:
                    if attempt < 2:
                        print(f"[{uid}] ⚠️ Chưa thấy lời mời, F5 và chờ thêm...")
                        driver.refresh()
                        time.sleep(8)
                    else:
                        print(f"[{uid}] ❌ Không tìm thấy lời mời kết bạn để xác nhận.")
                        sync['receiver_accepted'].set() # Vẫn set để luồng chat thử chạy tiếp (có thể đã là bạn mà lỗi dom)


        # ─── BƯỚC 2: Đồng bộ sau khi kết bạn ───
        if is_sender:
            print(f"[{uid}] ⏳ Chờ {target_uid} xác nhận kết bạn (tối đa 2 phút)...")
            sync['receiver_accepted'].wait(timeout=120)
        else:
            print(f"[{uid}] ⏳ Đã xác nhận kết bạn. Chờ đồng bộ tìm khung chat...")
            time.sleep(2)

        # ─── BƯỚC 3: Mở và Đồng bộ khung chat ───
        chat_box = None
        for attempt in range(5):
            print(f"[{uid}] 🔍 Tìm và mở khung chat (lần {attempt + 1}/5)...")
            try:
                try:
                    chat_box = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, chat_box_xpath))
                    )
                except Exception:
                    msg_btn_xpath = "//*[(@aria-label='Message' or @aria-label='Nhắn tin' or starts-with(@aria-label, 'Gửi tin nhắn')) and @role='button']"
                    msg_btn = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, msg_btn_xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", msg_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", msg_btn)
                    print(f"[{uid}] 💬 Đã nhấn nút Nhắn tin. Chờ khung chat hiện lên...")
                    time.sleep(5)
                    chat_box = WebDriverWait(driver, 60).until(
                        EC.element_to_be_clickable((By.XPATH, chat_box_xpath))
                    )
                
                if chat_box:
                    print(f"[{uid}] ✅ Đã mở được khung chat. Đang đợi đối tác mở thành công...")
                    if is_sender:
                        sync['chat_box_sender'].set()
                        if sync['chat_box_receiver'].wait(timeout=60):
                            print(f"[{uid}] 🤝 Cả 2 đã mở khung chat. Bắt đầu nhắn tin!")
                            break
                        else:
                            sync['chat_box_sender'].clear()
                    else:
                        sync['chat_box_receiver'].set()
                        if sync['chat_box_sender'].wait(timeout=60):
                            print(f"[{uid}] 🤝 Cả 2 đã mở khung chat. Bắt đầu nhắn tin!")
                            break
                        else:
                            sync['chat_box_receiver'].clear()
                            
                    print(f"[{uid}] ⚠️ Đối tác chưa mở được khung chat. Sẽ F5 và thử lại...")
            except Exception as e:
                print(f"[{uid}] ⚠️ Không tìm thấy khung chat. Đang F5 tải lại trang...")
                
            chat_box = None
            driver.refresh()
            time.sleep(8)
        
        if not chat_box:
            raise Exception("Không thể tìm thấy hoặc mở khung chat.")

        # ─── HÀM GỬI TIN NHẮN (dùng chung cho các lượt) ───
        def send_chat_messages(num_msgs):
            for msg_index in range(num_msgs):
                current_box = None
                try:
                    current_box = driver.find_element(By.XPATH, chat_box_xpath)
                    current_box.click()
                except:
                    current_box = chat_box
                    
                demo_msg = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(random.randint(5, 15)))
                print(f"[{uid}] ⌨️ Đang gõ tin nhắn {msg_index + 1}/{num_msgs}...")
                for char in demo_msg:
                    try:
                        if current_box: current_box.send_keys(char)
                    except:
                        try:
                            current_box = driver.find_element(By.XPATH, chat_box_xpath)
                            current_box.send_keys(char)
                        except:
                            pass
                    time.sleep(random.uniform(0.05, 0.2))
                time.sleep(1)
                msg_displayed = False
                for attempt in range(1, 4):
                    try:
                        send_btn = driver.find_element(By.XPATH, "//div[@aria-label='Press enter to send' or @aria-label='Nhấn Enter để gửi']")
                        driver.execute_script("arguments[0].click();", send_btn)
                    except:
                        from selenium.webdriver.common.keys import Keys
                        try:
                            if current_box: current_box.send_keys(Keys.ENTER)
                        except:
                            pass
                    sent_xpath = f"//*[contains(text(), '{demo_msg}')]"
                    try:
                        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, sent_xpath)))
                        print(f"[{uid}] ✅ Đã gửi thành công tin {msg_index + 1}!")
                        msg_displayed = True
                        break
                    except:
                        print(f"[{uid}] ⚠️ Chưa thấy xác nhận tin nhắn {msg_index + 1}. Thử lại...")
                if not msg_displayed:
                    print(f"[{uid}] ❌ Gửi thất bại tin {msg_index + 1}.")
                if msg_index < num_msgs - 1:
                    time.sleep(random.uniform(2, 5))

        # ─── BƯỚC 4: LOGIC CHAT TƯƠNG TÁC (PING-PONG) ───
        if is_sender:
            # LƯỢT 1: Sender gửi mở đầu
            print(f"[{uid}] 💬 LƯỢT 1: Sender đang gửi tin nhắn mở đầu...")
            send_chat_messages(random.randint(1, 2))
            sync['turn_1'].set()
            
            # LƯỢT 3: Sender rep lại sau khi Receiver đã rep
            print(f"[{uid}] ⏳ Đợi {target_uid} rep lại lượt 1...")
            if sync['turn_2'].wait(timeout=90):
                print(f"[{uid}] 💬 LƯỢT 3: Sender đang rep lại...")
                time.sleep(random.uniform(3, 7))
                send_chat_messages(random.randint(1, 2))
            sync['turn_3'].set()
            
            # Chờ Receiver chốt hạ trước khi kết thúc để không tắt trình duyệt sớm
            sync['turn_4'].wait(timeout=90)
            
        else:
            # LƯỢT 2: Receiver rep lại tin mở đầu
            print(f"[{uid}] ⏳ Đợi {target_uid} nhắn tin mở đầu...")
            if sync['turn_1'].wait(timeout=120):
                print(f"[{uid}] 💬 LƯỢT 2: Receiver đang rep lại tin nhắn mở đầu...")
                time.sleep(random.uniform(3, 7))
                send_chat_messages(random.randint(1, 2))
            sync['turn_2'].set()
            
            # LƯỢT 4: Receiver chốt hạ câu cuối
            print(f"[{uid}] ⏳ Đợi {target_uid} rep lại lượt 3...")
            if sync['turn_3'].wait(timeout=90):
                print(f"[{uid}] 💬 LƯỢT 4: Receiver đang chốt hạ cuộc trò chuyện...")
                time.sleep(random.uniform(3, 7))
                send_chat_messages(random.randint(1, 2))
            sync['turn_4'].set()

        print(f"[{uid}] 🏁 Hoàn thành chat tương tác 2 chiều (Ping-Pong). Tiếp tục tác vụ khác...")
        
        # Đóng khung chat
        print(f"[{uid}] 🔒 Đang đóng khung chat...")
        try:
            close_xpath = "//*[(@aria-label='Đóng đoạn chat' or @aria-label='Close chat' or contains(@aria-label, 'Đóng')) and @role='button']"
            close_btns = driver.find_elements(By.XPATH, close_xpath)
            for btn in close_btns:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                except:
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except:
                        pass
        except Exception as e:
            print(f"[{uid}] ⚠️ Không thể đóng khung chat: {e}")

    except Exception as e:
        print(f"[{uid}] ❌ Lỗi chat 2 chiều: {e}")
        # Đảm bảo unblock luồng kia nếu lỗi
        try:
            if uid < target_uid:
                if not sync['sender_added'].is_set(): sync['sender_added'].set()
                if not sync['turn_1'].is_set(): sync['turn_1'].set()
                if not sync['turn_3'].is_set(): sync['turn_3'].set()
            else:
                if not sync['receiver_accepted'].is_set(): sync['receiver_accepted'].set()
                if not sync['turn_2'].is_set(): sync['turn_2'].set()
                if not sync['turn_4'].is_set(): sync['turn_4'].set()
        except Exception:
            pass
    finally:
        # Xóa tín hiệu để lượt sau (Turn 2, 3...) không bị dính trạng thái cũ
        try:
            for key in sync:
                if hasattr(sync[key], 'clear'):
                    sync[key].clear()
        except Exception:
            pass
