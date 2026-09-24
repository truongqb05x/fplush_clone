# -*- coding: utf-8 -*-
"""
Các hàm bổ trợ chung (cleanup, URL handling, state detection, language switching)
"""
import time
import subprocess
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def type_human_like(driver, text, element=None):
    """Giả lập gõ phím từng chữ như người thật, xử lý xuống dòng cho Facebook"""
    for char in text:
        actions = ActionChains(driver)
        if element:
            if char == '\n':
                actions.key_down(Keys.SHIFT).send_keys_to_element(element, Keys.ENTER).key_up(Keys.SHIFT).perform()
            else:
                actions.send_keys_to_element(element, char).perform()
        else:
            if char == '\n':
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            else:
                actions.send_keys(char).perform()
        time.sleep(random.uniform(0.1, 0.4))



def cleanup_seleniumwire(driver):
    """Xóa seleniumwire request log và cache browser"""
    try:
        driver.requests.clear()
        # Tạm thời tắt dọn cache để debug persistence
        # driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        # driver.execute_cdp_cmd('Network.clearBrowserCookies', {}) # Đã xóa để giữ login
        print("🧼 Đã dọn seleniumwire (Cache/Cookies preserved)")
    except:
        pass



def safe_url(driver):
    """Lấy URL hiện tại một cách an toàn"""
    try:
        return driver.current_url or ""
    except:
        return ""


def normalize_url(url: str):
    """Chuẩn hóa URL"""
    try:
        return (
            url.lower()
            .replace("m.facebook.com", "facebook.com")
            .replace("facebook.me", "facebook.com")
            .rstrip("/")
        )
    except:
        return ""


# Danh sách các checkpoint "nhẹ" (tạm thời) - chỉ bỏ qua, KHÔNG xóa tài khoản
SOFT_CHECKPOINT_IDS = {
    "601051028565049",  
}

def is_checkpoint(driver):
    """Kiểm tra xem hiện tại có ở trang checkpoint không"""
    return "checkpoint" in normalize_url(safe_url(driver))


def is_soft_checkpoint(driver):
    """
    Kiểm tra xem checkpoint hiện tại có phải loại "nhẹ" (tạm thời) không.
    Nếu True → chỉ bỏ qua tài khoản, KHÔNG xóa.
    Nếu False → checkpoint cứng, xóa tài khoản bình thường.
    """
    try:
        url = safe_url(driver)
        for cp_id in SOFT_CHECKPOINT_IDS:
            if cp_id in url:
                try:
                    dismiss_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[(@aria-label='Dismiss' or @aria-label='Bỏ qua') and @role='button']"))
                    )
                    dismiss_btn.click()
                    print("Đã click nút Dismiss cho soft checkpoint.")
                    time.sleep(2)
                except Exception as e:
                    print(f"Không thể click nút Dismiss: {e}")
                return True
    except:
        pass
    return False


def is_facebook_home(driver):
    """Kiểm tra xem hiện tại có ở trang chủ Facebook không"""
    url = normalize_url(safe_url(driver))
    home_urls = [
        "https://www.facebook.com",
        "https://facebook.com",
        "https://www.facebook.com/",
        "https://facebook.com/",
        "https://www.facebook.com/?sk=welcome",
        "https://facebook.com/?sk=welcome"
    ]
    return url in home_urls or "facebook.com/home.php" in url

def is_logged_out(driver):
    """Kiểm tra xem trình duyệt có đang ở màn hình login (bị văng cookie) không"""
    url = safe_url(driver).lower()
    if "facebook.com/login" in url:
        return True
    try:
        els = driver.find_elements(By.NAME, "login") or driver.find_elements(By.XPATH, "//button[@name='login']")
        if els:
            return True
        els_pass = driver.find_elements(By.NAME, "pass")
        if els_pass:
            return True
    except:
        pass
    return False

def is_http_pool_timeout(e):
    """Kiểm tra có phải lỗi HTTPConnectionPool Read Timeout không"""
    msg = str(e).lower()
    return "httpconnectionpool" in msg and "read timed out" in msg



def wait_for_page_load(driver, timeout=15):
    """Đợi trang tải ổn định nhưng không đợi hoàn tất 100%"""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        # Chỉ đợi body xuất hiện là đủ để thao tác
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except:
        # Nếu quá timeout mà vẫn chưa load xong, ép trình duyệt dừng lại để làm việc tiếp
        try:
            driver.execute_script("window.stop();")
            print("⚠️ Ép dừng tải trang (window.stop) do quá thời gian.")
        except:
            pass


