import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def read_one_random_notification(driver, uid):
    """
    Mở bảng thông báo và đọc ngẫu nhiên 1 thông báo duy nhất.
    Sử dụng thi thoảng trong quá trình nuôi account.
    """
    print(f"[{uid}] 🔔 Bắt đầu ngẫu nhiên kiểm tra thông báo...")
    wait = WebDriverWait(driver, 15)

    try:
        # Nếu chưa ở trang chủ (feed chính) thì về trang chủ để dễ tìm nút chuông
        if "facebook.com" not in driver.current_url or len(driver.current_url) > 30:
            driver.get("https://www.facebook.com/")
            time.sleep(random.randint(3, 5))
            
        svg_path = "M3 9.5a9 9 0 1 1 18 0v2.927c0 1.69.475 3.345 1.37 4.778a1.5 1.5 0 0 1-1.272 2.295h-4.625a4.5 4.5 0 0 1-8.946 0H2.902a1.5 1.5 0 0 1-1.272-2.295A9.01 9.01 0 0 0 3 12.43V9.5zm6.55 10a2.5 2.5 0 0 0 4.9 0h-4.9z"
        xpath = f"//*[local-name()='path' and @d='{svg_path}']"
        
        path_el = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        driver.execute_script("arguments[0].closest('div[role=\"button\"]').click();", path_el)
        print(f"[{uid}] Đã mở bảng thông báo.")
    except Exception as e:
        print(f"[{uid}] [-] Lỗi mở thông báo qua SVG, thử fallback...")
        try:
            fallback_xpath = "//div[@role='button' and (contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'thông báo') or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'notifications'))]"
            btn_el = wait.until(EC.element_to_be_clickable((By.XPATH, fallback_xpath)))
            driver.execute_script("arguments[0].click();", btn_el)
        except Exception as ex:
            print(f"[{uid}] [-] Không thể mở bảng thông báo: {ex}")
            return

    try:
        print(f"[{uid}] Đang chờ danh sách thông báo tải...")
        notif_xpath = "//a[contains(@href, 'notif_id=')]"
        
        # Chờ hiển thị ít nhất 1 thông báo
        wait.until(EC.presence_of_all_elements_located((By.XPATH, notif_xpath)))
        time.sleep(random.randint(2, 4)) # Chờ UI ổn định
        
        notifs = driver.find_elements(By.XPATH, notif_xpath)
        if notifs:
            random_notif = random.choice(notifs)
            
            # Cuộn và click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_notif)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", random_notif)
            print(f"[{uid}] Đã click vào 1 thông báo để đọc.")
            
            # Delay ngẫu nhiên để mô phỏng người dùng đọc
            read_delay = random.randint(10, 25)
            print(f"[{uid}] Đang xem nội dung thông báo (chờ {read_delay}s)...")
            
            # Cuộn dần đọc thông báo
            end_view_time = time.time() + read_delay
            while time.time() < end_view_time:
                scroll_dist = random.randint(100, 300)
                try:
                    driver.execute_script(f"window.scrollBy(0, {scroll_dist});")
                except:
                    pass
                chunk_sleep = random.uniform(2, 5)
                if time.time() + chunk_sleep > end_view_time:
                    time.sleep(max(0, end_view_time - time.time()))
                    break
                else:
                    time.sleep(chunk_sleep)
            
            print(f"[{uid}] Đã đọc xong thông báo, trở về News Feed.")
            driver.get("https://www.facebook.com/")
            time.sleep(3)
        else:
            print(f"[{uid}] Không tìm thấy thông báo nào để đọc.")
    except Exception as e:
        print(f"[{uid}] [-] Lỗi khi tải/click thông báo: {e}")
