# avatar_utils.py
import os
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from config.config import *

def get_random_image(folder):
    if not os.path.exists(folder):
        raise Exception(f" Thư mục không tồn tại: {folder}")

    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    if not files:
        raise Exception(" Không có ảnh hợp lệ")
    return random.choice(files)

def get_random_stt(file_path):
    if not os.path.exists(file_path):
        return "Cập nhật ảnh đại diện mới"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return random.choice(lines) if lines else "Update profile picture"

def upload_avatar_and_status(driver, wait, avatar_folder, stt_file):
    try:
        print(" Truy cập trang cá nhân...")
        driver.get("https://www.facebook.com/me")

        # 1️⃣ Click icon avatar
        print(" Click icon máy ảnh")
        try:
            avatar_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//div[@aria-label='Hành động với ảnh đại diện' or "
                "@aria-label='Update profile picture' or "
                "@aria-label='Profile picture actions']"
            )))
        except TimeoutException:
            avatar_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div/div/div[1]/div[2]/div/div/div/div[1]/div/div/div/div[2]/div/div[2]/i"
            )))
        driver.execute_script("arguments[0].click();", avatar_btn)

        # 2️⃣ Chờ dialog & click "Choose profile picture"
        print(" Chọn ảnh đại diện")
        dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))

        try:
            choose_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//span[contains(text(),'Chọn ảnh đại diện') or contains(text(),'Choose profile picture')]"
            )))
        except TimeoutException:
            choose_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/div/div/div/div/div"
            )))
        driver.execute_script("arguments[0].click();", choose_btn)

        # 3️⃣ Upload file
        print(" Upload ảnh")
        file_input = wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[@role='dialog']//input[@type='file']"
        )))

        driver.execute_script(
            "arguments[0].style.display='block'; arguments[0].style.opacity='1';",
            file_input
        )

        file_path = get_random_image(avatar_folder)
        file_input.send_keys(file_path)
        print(f" Đã chọn: {os.path.basename(file_path)}")

        # 4️⃣ Chờ ảnh load xong → nút Save enable
        print(" Chờ ảnh load")
        wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[@role='button']//span[text()='Save' or text()='Lưu']"
        )))

        # 5️⃣ Điền status (nếu có)
        print(" Điền mô tả")
        try:
            textarea = wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//textarea[@aria-label='Description' or @aria-label='Mô tả' or contains(@id,'r_')]"
            )))
            textarea.send_keys(get_random_stt(stt_file))
        except TimeoutException:
            print(" Không tìm thấy ô mô tả, bỏ qua")

        # 6️⃣ Lưu
        print(" Nhấn Lưu")
        save_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[@role='button']//span[text()='Save' or text()='Lưu']"
        )))
        driver.execute_script("arguments[0].click();", save_btn)

        # 7️⃣ Chờ dialog đóng = lưu xong
        wait.until(EC.invisibility_of_element(dialog))

        print(" HOÀN TẤT: Đã cập nhật avatar & status")
        return True

    except Exception as e:
        print(f" Lỗi upload avatar: {e}")
        return False
