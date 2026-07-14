# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

def random_like_post(driver, uid):
    """
    Tìm ngẫu nhiên một nút Like (Thích) trên màn hình và tương tác.
    Đã xử lý chống click trùng (Unlike) và giả lập thao tác chuột của người thật.
    """
    try:
        # Tìm các nút Like (Thích) chưa được tương tác
        like_buttons = driver.find_elements(
            By.XPATH, 
            '//div[@role="button" and (@aria-label="Thích" or @aria-label="Like") and not(@data-liked="true")]'
        )
        
        if like_buttons:
            # Chọn ngẫu nhiên 1 nút
            target_like = random.choice(like_buttons)
            
            # Đánh dấu đã click để tránh bấm lại (thành Unlike)
            driver.execute_script("arguments[0].setAttribute('data-liked', 'true')", target_like)
            
            # Di chuyển chuột đến hướng nút Like và click để giả lập người thật
            ActionChains(driver).move_to_element(target_like).pause(random.uniform(0.5, 1.5)).click().perform()
            print(f"[{uid}] 👍 Tương tác ngẫu nhiên: Thả cảm xúc thành công.")
            time.sleep(random.uniform(2, 5))
            return True
    except Exception:
        pass
        
    return False
