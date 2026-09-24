# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

def random_like_post(driver, uid, allowed_reactions=None):
    """
    Tìm nút Like bài viết trên màn hình, di chuột vào để hiện popup cảm xúc,
    và chọn ngẫu nhiên một cảm xúc (Like, Love, Haha, Wow...).
    Phân biệt nút like bài viết và like comment bằng data-ad-rendering-role="like_button".
    """
    try:
        # Tìm nút like bài viết (chưa được like bởi tool trong phiên này)
        like_buttons = driver.find_elements(
            By.XPATH, 
            '//div[@role="button" and not(@data-liked="true") and .//div[@data-ad-rendering-role="like_button"]]'
        )
        
        if like_buttons:
            # Ưu tiên lấy nút like đầu tiên hiển thị trên màn hình
            target_like = like_buttons[0]
            
            # Đánh dấu đã tương tác để tránh click đúp (unlike) nếu vô tình quét lại
            driver.execute_script("arguments[0].setAttribute('data-liked', 'true')", target_like)
            
            # Hover vào nút Like để hiện menu cảm xúc
            ActionChains(driver).move_to_element(target_like).pause(2).perform()
            time.sleep(2)  # Đợi popup hiện lên
            
            # Các nhãn cảm xúc phổ biến (Việt / Anh)
            if not allowed_reactions:
                labels = ["Thích", "Like", "Yêu thích", "Haha", "Wow", "Buồn", "Thương thương", "Phẫn nộ", 
                          "Love", "Care", "Sad", "Angry"]
            else:
                labels = allowed_reactions
            
            xpath_expr = " | ".join([f'//div[@role="button" and @aria-label="{lbl}"]' for lbl in labels])
            reactions = driver.find_elements(By.XPATH, xpath_expr)
            
            # Chỉ lấy các cảm xúc đang hiển thị trên popup
            visible_reactions = [r for r in reactions if r.is_displayed()]
            
            if visible_reactions:
                chosen_reaction = random.choice(visible_reactions)
                reaction_name = chosen_reaction.get_attribute("aria-label")
                
                # Di chuột đến cảm xúc đó và click
                ActionChains(driver).move_to_element(chosen_reaction).pause(0.5).click().perform()
                print(f"[{uid}] 👍 Đã thả cảm xúc bài viết: {reaction_name}")
                return True
            else:
                # Fallback: Nếu không bắt được popup cảm xúc, click mặc định vào nút Like
                ActionChains(driver).click(target_like).perform()
                print(f"[{uid}] 👍 Không bắt được popup cảm xúc, đã bấm Like mặc định.")
                return True
    except Exception as e:
        print(f"[{uid}] ❌ Lỗi khi thả cảm xúc: {e}")
        pass
        
    return False
