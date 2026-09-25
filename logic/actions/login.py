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
                    driver.execute_script("arguments[0].click();", switch_btn)
                    time.sleep(3)
                    break
            except: continue

        # 2. Chờ input email
        email_input = wait_for_element_with_retry(driver, By.NAME, "email", timeout=15, description="Email input")
        
        if not email_input:
            print(f"[{username}] ❌ Login thất bại.")
            return False
        
        # Nhập email
        email_input.clear()
        for char in username:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        # 2. Chờ input password
        pass_input = wait_for_element_with_retry(driver, By.NAME, "pass", timeout=15, description="Password input")
        if not pass_input:
            print(f"[{username}] ❌ Login thất bại.")
            return False
        
        # Nhập password
        pass_input.clear()
        for char in password:
            pass_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        # 3. Click nút Đăng nhập
        # Dựa trên HTML: <span class="...">Đăng nhập</span> bên trong một div role="none"
        # Thêm các trường hợp tiếng Anh và dùng XPath linh hoạt hơn
        # 3. Click nút Đăng nhập
        # Cập nhật XPath cho Facebook React: div có role="button" và aria-label="Log in"
        login_btn_selectors = [
            (By.XPATH, "//*[(@aria-label='Log in' or @aria-label='Đăng nhập' or @aria-label='Log In') and @role='button']"),
            (By.NAME, "login"),
            (By.XPATH, "//button[@name='login' or @type='submit']"),
            (By.XPATH, "//div[@role='button']//*[contains(text(), 'Đăng nhập') or contains(text(), 'Log in')]")
        ]
        
        login_btn_clicked = False
        for by, val in login_btn_selectors:
            try:
                btns = driver.find_elements(by, val)
                if btns:
                    for btn in btns:
                        if btn.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(0.5)
                                # Ưu tiên dùng JS click vì thẻ div của FB hay bị báo lỗi element not interactable
                                driver.execute_script("arguments[0].click();", btn)
                                login_btn_clicked = True
                                break
                            except Exception:
                                pass
                if login_btn_clicked:
                    break
            except Exception:
                continue
        
        if not login_btn_clicked:
            # Fallback: Nếu mọi loại nút click đều xịt, nhấn thẳng phím Enter trên ô mật khẩu
            try:
                pass_input.send_keys(Keys.ENTER)
            except:
                pass

        # Polling mỗi 1 giây, tối đa 30 giây.
        # Facebook hay đi qua nhiều bước trung gian:
        #   login → facebook.com/ (thoáng) → two_step_verification → facebook.com/ (đích)
        # → Chỉ kết luận THÀNH CÔNG khi URL thực sự là trang sạch (không login/two_step/checkpoint).
        # → Tiếp tục chờ qua các bước trung gian cho đến hết 30 giây.
        max_wait = 60
        poll_interval = 1
        elapsed = 0
        success = False

        from utils.helpers import is_checkpoint as check_checkpoint
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            url = driver.current_url.lower()

            is_login     = "login"      in url
            is_two_step  = "two_step"   in url or "two_factor" in url
            is_checkpoint = check_checkpoint(driver)

            if is_checkpoint:
                # Checkpoint cứng — không tự giải quyết được, thoát sớm
                break

            if not is_login and not is_two_step and not is_checkpoint:
                # Đợi thêm 3s để đảm bảo trình duyệt không tự redirect sang trang 2FA/checkpoint
                time.sleep(3)
                elapsed += 3
                url = driver.current_url.lower()
                is_login     = "login"      in url
                is_two_step  = "two_step"   in url or "two_factor" in url
                is_checkpoint = check_checkpoint(driver)
                
                if is_checkpoint:
                    break

                if not is_login and not is_two_step and not is_checkpoint:
                    # URL sạch thực sự — đã qua hết bước trung gian
                    success = True
                    print(f"[{username}] ✅ Login thành công.")
                    break

        if success:
            return True

        # Hết 30s hoặc gặp checkpoint → xử lý
        current_url = driver.current_url
        if check_checkpoint(driver):
            from utils.helpers import is_soft_checkpoint
            if is_soft_checkpoint(driver):
                driver.get("https://www.facebook.com/")
                time.sleep(5)
                if not check_checkpoint(driver):
                    print(f"[{username}] ✅ Login thành công.")
                    return True

        print(f"[{username}] ❌ Login thất bại.")
        return False

    except Exception as e:
        print(f"[{username}] ❌ Login thất bại.")
        return False
