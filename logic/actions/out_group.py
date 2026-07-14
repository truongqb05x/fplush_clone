# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.helpers import wait_for_page_load
from utils.scan_group import get_joined_groups

def leave_group_logic(driver, uid, group_id_or_link):
    """
    Truy cập vào group và thực hiện các bước rời nhóm dựa trên UI Facebook.
    Dựa trên các snippet HTML được cung cấp.
    """
    try:
        # 1. Truy cập group
        if str(group_id_or_link).startswith("http"):
            url = group_id_or_link
        else:
            url = f"https://www.facebook.com/groups/{group_id_or_link}/"
        
        print(f"[{uid}] 🚀 Đang truy cập group: {url}")
        driver.get(url)
        
        # Đợi trang tải xong
        wait_for_page_load(driver, timeout=20)
        
        # Chờ giao diện ổn định
        print(f"[{uid}] ⏳ Đợi giao diện ổn định...")
        time.sleep(random.randint(7, 10))

        # 2. Tìm và click nút "Đã tham gia" (Joined)
        print(f"[{uid}] 🔍 Đang tìm nút 'Đã tham gia'...")
        try:
            # Selector tìm container chứa text "Đã tham gia" hoặc icon đặc trưng
            joined_xpath = (
                "//div[@role='button'][.//span[text()='Đã tham gia']] | "
                "//div[@role='none'][.//span[text()='Đã tham gia']] | "
                "//*[local-name()='svg']/*[local-name()='path' and starts-with(@d, 'M5.25 4.75')]/ancestor::div[1]"
            )
            
            joined_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, joined_xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", joined_btn)
            time.sleep(1)
            
            # Click bằng JS để vượt qua việc phần tử bị ẩn/che khuất
            driver.execute_script("arguments[0].click();", joined_btn)
            print(f"[{uid}] ✅ Đã click nút 'Đã tham gia'.")
            time.sleep(random.randint(3, 5))
        except Exception as e:
            print(f"[{uid}] ❌ Không tìm thấy nút 'Đã tham gia': {e}")
            return False

        # 3. Click "Rời nhóm" trong menu xuất hiện
        print(f"[{uid}] 🔍 Đang tìm mục 'Rời nhóm' trong menu...")
        try:
            leave_menu_item = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Rời nhóm']"))
            )
            leave_menu_item.click()
            print(f"[{uid}] ✅ Đã click 'Rời nhóm' từ menu.")
            time.sleep(random.randint(3, 5))
        except Exception:
            try:
                leave_menu_item = driver.find_element(By.XPATH, "//div[@role='menuitem']//span[contains(text(),'Rời nhóm')]")
                leave_menu_item.click()
                print(f"[{uid}] ✅ Đã click 'Rời nhóm' (fallback).")
                time.sleep(random.randint(3, 5))
            except:
                print(f"[{uid}] ❌ Không tìm thấy mục 'Rời nhóm' trong menu.")
                return False

        # 4. Xác nhận "Rời khỏi nhóm" trong dialog
        print(f"[{uid}] 🔍 Đang xác nhận rời nhóm trong dialog...")
        try:
            confirm_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Rời khỏi nhóm' and @role='button'] | //span[text()='Rời khỏi nhóm']/ancestor::div[@role='button']"))
            )
            confirm_btn.click()
            print(f"[{uid}] ✅ Đã xác nhận rời khỏi nhóm thành công.")
            time.sleep(5)
            return True
        except Exception as e:
            print(f"[{uid}] ❌ Lỗi khi xác nhận rời nhóm: {e}")
            return False

    except Exception as e:
        print(f"[{uid}] 💥 Lỗi khi thực hiện rời nhóm: {e}")
        return False

def out_groups_by_mode(driver, uid, mode, filter_list=None):
    """
    Thực hiện out group dựa trên chế độ chọn.
    mode 1: Out all
    mode 2: Out list
    mode 3: Out all except list
    """
    print(f"[{uid}] 🔍 Đang quét danh sách group đã tham gia...")
    all_groups = get_joined_groups(driver, uid=uid)
    
    if not all_groups:
        print(f"[{uid}] ⚠️ Không tìm thấy group nào đã tham gia.")
        return False
    
    target_groups = []
    filter_set = set(filter_list) if filter_list else set()

    if mode == "1":
        target_groups = all_groups
        print(f"[{uid}] 🎯 Chế độ: Out ALL ({len(target_groups)} nhóm).")
    elif mode == "2":
        target_groups = [g for g in all_groups if (g.get('uid') in filter_set or g.get('link') in filter_set)]
        print(f"[{uid}] 🎯 Chế độ: Out theo danh sách ({len(target_groups)} nhóm tìm thấy).")
    elif mode == "3":
        target_groups = [g for g in all_groups if (g.get('uid') not in filter_set and g.get('link') not in filter_set)]
        print(f"[{uid}] 🎯 Chế độ: Out ngoại trừ danh sách ({len(target_groups)} nhóm).")

    if not target_groups:
        print(f"[{uid}] ⚠️ Không có nhóm nào phù hợp để out.")
        return False

    success_count = 0
    for idx, group in enumerate(target_groups):
        gid = group.get('uid') if group.get('uid') != "N/A" else group.get('link')
        name = group.get('name', 'Unknown Group')
        
        print(f"[{uid}] 🚪 ({idx+1}/{len(target_groups)}) Đang out group: '{name}' ({gid})...")
        if leave_group_logic(driver, uid, gid):
            success_count += 1
            print(f"[{uid}] ✅ Đã out thành công.")
        else:
            print(f"[{uid}] ❌ Out thất bại hoặc có lỗi.")
        
        # Delay giữa các group
        if idx < len(target_groups) - 1:
            delay = random.randint(5, 10)
            print(f"[{uid}] ⏳ Nghỉ {delay}s trước khi sang group tiếp theo...")
            time.sleep(delay)

    print(f"[{uid}] ✨ Đã hoàn thành Out Group. Thành công {success_count} nhóm.")
    return True
