# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.waiter import wait_for_element_with_retry, wait_for_clickable_with_retry

def login_with_credentials(driver, username, password):
    """
    Login vào Facebook bằng tài khoản và mật khẩu
    Dựa trên HTML được cung cấp bởi user
    """
    try:
        print(f"🔑 Đang tiến hành login cho: {username}")
        
        # 1. Kiểm tra nếu có nút "Dùng trang cá nhân khác" thì nhấn trước
        switch_selectors = [
            (By.XPATH, "//div[@aria-label='Dùng trang cá nhân khác' or @aria-label='Use another profile']"),
            (By.XPATH, "//span[contains(text(), 'Dùng trang cá nhân khác') or contains(text(), 'Use another account')]")
        ]
        
        switch_btn = None
        for by, val in switch_selectors:
            try:
                switch_btn = driver.find_element(by, val)
                if switch_btn and switch_btn.is_displayed(): 
                    print(f"[{username}] 🖱️ Đã tìm thấy nút chuyển tài khoản, đang click trước...")
                    driver.execute_script("arguments[0].click();", switch_btn)
                    time.sleep(3)
                    break
            except: continue

        # 2. Chờ input email
        email_input = wait_for_element_with_retry(driver, By.NAME, "email", timeout=15, description="Email input")
        
        if not email_input:
            print("❌ Không tìm thấy input Email")
            return False
        
        # Nhập email
        email_input.clear()
        for char in username:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        # 2. Chờ input password
        pass_input = wait_for_element_with_retry(driver, By.NAME, "pass", timeout=15, description="Password input")
        if not pass_input:
            print("❌ Không tìm thấy input Password")
            return False
        
        # Nhập password
        pass_input.clear()
        for char in password:
            pass_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        # 3. Click nút Đăng nhập
        # Dựa trên HTML: <span class="...">Đăng nhập</span> bên trong một div role="none"
        # Thêm các trường hợp tiếng Anh và dùng XPath linh hoạt hơn
        login_btn_selectors = [
            (By.NAME, "login"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//div[@aria-label='Log in' or @aria-label='Đăng nhập']"),
            (By.XPATH, "//span[contains(text(), 'Đăng nhập') or contains(text(), 'Log in') or contains(text(), 'Log In')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'Đăng nhập') or contains(text(), 'Log in') or contains(text(), 'Log In')]")
        ]
        
        login_btn = None
        for by, val in login_btn_selectors:
            try:
                print(f"🔍 Thử tìm nút login bằng {by}: {val}")
                login_btn = wait_for_clickable_with_retry(driver, by, val, timeout=5, retry=0, description=f"Login button ({val})")
                if login_btn:
                    break
            except:
                continue
        
        if login_btn:
            print("🖱️ Đang click nút Đăng nhập...")
            try:
                login_btn.click()
            except:
                print("⚠️ Click thông thường lỗi, thử click bằng JavaScript...")
                driver.execute_script("arguments[0].click();", login_btn)
        else:
            print("⚠️ Không tìm thấy nút Đăng nhập cụ thể, thử phím ENTER trên ô password")
            pass_input.send_keys(Keys.ENTER)
        
        print("⏳ Đang chờ chuyển hướng sau khi click Đăng nhập...")
        time.sleep(10)
        
        # Kiểm tra nếu vẫn ở trang login hoặc có lỗi
        current_url = driver.current_url
        if "login" in current_url.lower() or "checkpoint" in current_url.lower():
            print(f"⚠️ Cảnh báo: Có thể login chưa thành công hoặc gặp checkpoint. URL: {current_url}")
            return False
            
        print("✅ Login có vẻ đã thành công (hoặc đang chuyển hướng)")
        return True

    except Exception as e:
        print(f"❌ Lỗi trong quá trình login: {e}")
        return False
