# -*- coding: utf-8 -*-
"""
Các hàm wait và retry cho element
"""
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from utils.helpers import is_http_pool_timeout


def safe_wait_until(driver, timeout, condition, description=""):
    """
    Wrapper an WebDriverWait.until() với kiểm tra HTTPConnectionPool timeout
    Nếu gặp lỗi này, sẽ throw ngay (không chờ)
    """
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(condition)
    except Exception as e:
        # ===== HTTPConnectionPool TIMEOUT → OUT NGAY =====
        if is_http_pool_timeout(e):
            print(f"💥 HTTPConnectionPool READ TIMEOUT {description} → OUT NGAY")
            raise e
        raise e


def wait_for_element_with_retry(driver, by, value, timeout=30, retry=2, description=""):
    """Chờ element xuất hiện với retry"""
    for attempt in range(retry + 1):
        try:
            print(f"⏳ Chờ element {description} (lần {attempt + 1}/{retry + 1})...")
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            
            # Cuộn tới element
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            return element
        except Exception as e:
            # ===== HTTPConnectionPool TIMEOUT → OUT NGAY =====
            if is_http_pool_timeout(e):
                print(f"💥 HTTPConnectionPool READ TIMEOUT khi chờ {description} → OUT NGAY")
                raise e
            
            if attempt < retry:
                print(f"⚠️ Chưa thấy {description}, đang dừng các request treo và reload...")
                try:
                    driver.execute_script("window.stop();") # Dừng các request đang treo trước khi refresh
                except:
                    pass
                driver.refresh()
                time.sleep(3)
            else:
                raise e


def wait_for_clickable_with_retry(driver, by, value, timeout=30, retry=2, description=""):
    """Chờ element clickable với retry"""
    for attempt in range(retry + 1):
        try:
            print(f"⏳ Chờ element clickable {description} (lần {attempt + 1}/{retry + 1})...")
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by, value)))
            print(f"✅ Element {description} đã clickable")
            return element
        except Exception as e:
            # ===== HTTPConnectionPool TIMEOUT → OUT NGAY =====
            if is_http_pool_timeout(e):
                print(f"💥 HTTPConnectionPool READ TIMEOUT khi chờ clickable {description} → OUT NGAY")
                raise e
            
            if isinstance(e, TimeoutException):
                if attempt < retry:
                    print(f"⚠️ Timeout clickable lần {attempt + 1}, thử lại...")
                else:
                    print(f"❌ Element {description} không clickable sau {retry + 1} lần thử")
                    raise
            else:
                raise e
    return None


def wait_for_redirect(driver, timeout=15):
    """Chờ chuyển hướng sau khi nhập OTP"""
    from utils.helpers import safe_url, is_checkpoint, is_facebook_home
    
    print("\n⏳ CHỜ CHUYỂN HƯỚNG SAU OTP...")
    start_time = time.time()
    last_url = None
    check_interval = 1  # Kiểm tra mỗi 1 giây
    
    while time.time() - start_time < timeout:
        try:
            current_url = safe_url(driver)
            elapsed = int(time.time() - start_time)
            
            # Nếu URL thay đổi, in ra để debug
            if current_url != last_url:
                print(f"⏱️ ({elapsed}s/{timeout}s) URL: {current_url[:80]}...")
                last_url = current_url
            
            # Nếu đã về trang chủ Facebook
            if is_facebook_home(driver):
                print("✅ ĐÃ VỀ TRANG CHỦ FACEBOOK")
                time.sleep(2)
                return True
            
            # Nếu là trang checkpoint
            if is_checkpoint(driver):
                print("⚠️ PHÁT HIỆN CHECKPOINT SAU OTP")
                return False
            
            # Nếu vẫn ở trang confirm email, chỉ log lần đầu
            if "confirmemail.php" in current_url and current_url != last_url:
                print(f"📧 Vẫn ở trang xác nhận email, chờ chuyển hướng...")
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"⚠️ Lỗi khi chờ chuyển hướng: {e}")
            time.sleep(check_interval)
    
    print(f"⏰ ĐÃ CHỜ {timeout}s, CHUYỂN SANG BƯỚC TIẾP THEO...")
    current_url = safe_url(driver)
    print(f"📍 URL CUỐI CÙNG: {current_url}")
    return True
