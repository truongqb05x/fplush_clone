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


def periodic_seleniumwire_cleanup(driver, step=50):
    """
    Dọn seleniumwire định kỳ sau N request
    """
    try:
        if hasattr(driver, "requests") and len(driver.requests) >= step:
            driver.requests.clear()
            print(f"🧼 Seleniumwire cleanup sau {step} requests")
    except:
        pass


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


def kill_all_chrome():
    """Kill tất cả process Chrome"""
    subprocess.call(
        "taskkill /F /IM chrome.exe /T",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )


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
    "601051028565049",  # Checkpoint xác minh danh tính tạm thời
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


def is_http_pool_timeout(e):
    """Kiểm tra có phải lỗi HTTPConnectionPool Read Timeout không"""
    msg = str(e).lower()
    return "httpconnectionpool" in msg and "read timed out" in msg


def is_crash_error(e):
    """Kiểm tra có phải lỗi crash không"""
    msg = str(e).lower()
    return any(x in msg for x in [
        "chrome not reachable",
        "disconnected",
        "timed out",
        "connection refused",
        "httpconnectionpool",
        "invalid session id",
        "timed out receiving message",
        "no such window",
        "target frame detached"
    ])


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


# ================= FORCE LANGUAGE (NO CHECK) =================
def try_force_change_language(driver, timeout=10):
    """
    Thử chuyển ngôn ngữ sang Tiếng Việt.
    An toàn với SeleniumWire, KHÔNG gây HTTPPOOL, KHÔNG treo Chrome.
    """

    print("🧼 Cleanup seleniumwire trước khi đổi ngôn ngữ...")
    try:
        driver.requests.clear()
    except:
        pass

    try:
        driver.scopes = []   # ⛔ TẮT seleniumwire intercept
    except:
        pass

    try:
        print("🌐 Kiểm tra và chuyển ngôn ngữ sang Tiếng Việt...")

        # ================== 1️⃣ KIỂM TRA ĐÃ Ở TIẾNG VIỆT CHƯA ==================
        print("1️⃣ Kiểm tra xem đã ở Tiếng Việt chưa...")

        vietnamese_indicators = [
            "xác nhận email",
            "nhập mã",
            "tiếp tục",
            "gửi lại",
            "thay đổi",
            "tôi không nhận được mã",
        ]

        try:
            page_source = driver.page_source.lower()[:20000]  # giới hạn tránh treo
            for indicator in vietnamese_indicators:
                if indicator in page_source:
                    print(f"   ✅ ĐÃ Ở TIẾNG VIỆT (tìm thấy: '{indicator}')")
                    return True

            html_lang = driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
            if html_lang and ("vi" in html_lang.lower()):
                print(f"   ✅ ĐÃ Ở TIẾNG VIỆT (lang='{html_lang}')")
                return True

            print("   ❌ Chưa ở Tiếng Việt, tiếp tục tìm nút chuyển ngôn ngữ...")

        except Exception as e:
            print(f"   ⚠️ Lỗi khi kiểm tra ngôn ngữ: {e}")

        # ================== 2️⃣ TÌM NÚT TIẾNG VIỆT ==================
        print("2️⃣ Tìm nút chuyển sang Tiếng Việt...")

        vietnamese_selectors = [
            (By.XPATH, "//a[@title='Vietnamese' and contains(@href,'confirmemail.php')]"),
            (By.XPATH, "//*[contains(text(),'Tiếng Việt') and not(contains(text(),'English'))]"),
            (By.XPATH, "//*[contains(text(),'Vietnamese') and not(contains(text(),'English'))]"),
            (By.XPATH, "//a[contains(text(),'Tiếng Việt')]"),
            (By.XPATH, "//span[contains(text(),'Tiếng Việt')]"),
            (By.XPATH, "//div[contains(text(),'Tiếng Việt')]"),
        ]

        found_element = None
        for by, selector in vietnamese_selectors:
            try:
                print(f"   🔎 Thử selector: {selector[:60]}...")
                found_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((by, selector))
                )

                text = found_element.text.strip()
                if "Tiếng Việt" in text or "Vietnamese" in text:
                    print(f"   ✅ Tìm thấy nút chuyển ngôn ngữ: '{text}'")
                    break
                else:
                    found_element = None

            except:
                continue

        if not found_element:
            print("⚠️ Không tìm thấy nút Tiếng Việt → bỏ qua")
            return False

        # ================== 3️⃣ CLICK AN TOÀN (KHÔNG GÂY HTTPPOOL) ==================
        print("3️⃣ Click vào nút Tiếng Việt (safe mode)...")

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                found_element
            )
        except:
            pass

        driver.execute_script("""
            arguments[0].dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true
            }));
        """, found_element)

        print("   ✅ Đã dispatch click Tiếng Việt")

        # ================== 4️⃣ ĐỢI RELOAD NHẸ (KHÔNG ĐỢI MÙ) ==================
        print("⏳ Đợi reload sau đổi ngôn ngữ (tối đa 8s)...")
        try:
            WebDriverWait(driver, 8).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            print("⚠️ Reload chậm, tiếp tục flow")

        # ================== 5️⃣ KIỂM TRA LẠI ==================
        try:
            new_source = driver.page_source.lower()[:20000]
            for indicator in vietnamese_indicators:
                if indicator in new_source:
                    print("✅ ĐÃ CHUYỂN SANG TIẾNG VIỆT THÀNH CÔNG")
                    return True
        except:
            pass

        print("⚠️ Không chắc đã đổi ngôn ngữ, nhưng tiếp tục chạy")
        return False

    except Exception as e:
        msg = str(e).lower()

        if "httpconnectionpool" in msg:
            print("⚠️ HTTPPOOL khi đổi ngôn ngữ → BỎ QUA, KHÔNG KILL CHROME")
            return False

        print(f"⚠️ Lỗi khi kiểm tra/chuyển ngôn ngữ: {str(e)[:120]}")
        return False


# ================= FORCE LANGUAGE TO ENGLISH =================
def try_force_change_language_en(driver, timeout=10):
    """
    Thử chuyển ngôn ngữ sang Tiếng Anh (English US).
    Dựa trên cấu trúc footer của Facebook: <li><a title='English (US)'>...</a></li>
    """

    print("🧼 Cleanup seleniumwire trước khi đổi ngôn ngữ...")
    try:
        driver.requests.clear()
    except:
        pass

    try:
        driver.scopes = []   # ⛔ TẮT seleniumwire intercept để tăng tốc
    except:
        pass

    try:
        print("🌐 Kiểm tra và chuyển ngôn ngữ sang English (US)...")

        # ================== 1️⃣ KIỂM TRA ĐÃ Ở TIẾNG ANH CHƯA ==================
        english_indicators = [
            "confirm your email",
            "enter code",
            "continue",
            "resend email",
            "didn't get a code",
            "change email address",
        ]

        try:
            # Kiểm tra thuộc tính lang của thẻ html
            html_lang = driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
            if html_lang and ("en" in html_lang.lower()):
                print(f"   ✅ ĐÃ Ở TIẾNG ANH (lang='{html_lang}')")
                return True

            # Kiểm tra text trên trang
            page_source = driver.page_source.lower()[:20000]
            for indicator in english_indicators:
                if indicator in page_source:
                    print(f"   ✅ ĐÃ Ở TIẾNG ANH (tìm thấy từ khóa: '{indicator}')")
                    return True

            print("   ❌ Chưa ở Tiếng Anh, tiến hành tìm nút chuyển...")

        except Exception as e:
            print(f"   ⚠️ Lỗi khi kiểm tra ngôn ngữ: {e}")

        # ================== 2️⃣ TÌM NÚT ENGLISH (US) ==================
        # Dựa vào HTML bạn cung cấp: <a title="English (US)">
        english_selectors = [
            (By.XPATH, "//a[@title='English (US)']"),
            (By.XPATH, "//a[contains(@href, 'en-gb.facebook.com')]"),
            (By.XPATH, "//a[text()='English (US)']"),
            (By.XPATH, "//a[contains(text(),'English')]"),
            # Selector đặc định cho cấu trúc footer bạn gửi
            (By.CSS_SELECTOR, "a._sv4[title*='English']"), 
        ]

        found_element = None
        for by, selector in english_selectors:
            try:
                found_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by, selector))
                )
                if found_element:
                    print(f"   ✅ Tìm thấy nút English bằng: {selector}")
                    break
            except:
                continue

        if not found_element:
            print("⚠️ Không tìm thấy nút English (US) trong danh sách")
            return False

        # ================== 3️⃣ CLICK AN TOÀN ==================
        print("3️⃣ Cuộn và Click vào English (US)...")

        try:
            # Cuộn đến phần tử
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", found_element)
            time.sleep(0.5)
            
            # Click bằng JS để tránh bị các thẻ div khác che khuất
            driver.execute_script("""
                arguments[0].dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                }));
            """, found_element)
            print("   ✅ Đã gửi lệnh click English (US)")
        except Exception as e:
            print(f"   ❌ Không thể click nút English: {e}")
            return False

        # ================== 4️⃣ ĐỢI RELOAD ==================
        print("⏳ Đợi trang tải lại...")
        try:
            WebDriverWait(driver, 8).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass

        # ================== 5️⃣ XÁC NHẬN CUỐI CÙNG ==================
        try:
            new_source = driver.page_source.lower()[:20000]
            if "confirm your email" in new_source or "en" in driver.find_element(By.TAG_NAME, "html").get_attribute("lang"):
                print("✅ CHUYỂN SANG TIẾNG ANH THÀNH CÔNG")
                return True
        except:
            pass

        return False

    except Exception as e:
        print(f"⚠️ Lỗi tổng quát khi đổi ngôn ngữ EN: {str(e)[:120]}")
        return False
