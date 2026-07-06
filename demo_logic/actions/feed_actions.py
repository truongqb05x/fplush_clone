# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from actions.like_actions import random_like_post

def warm_up_account(driver, uid, warmup_time=None):
    print(f"[{uid}] 🍵 Đang nuôi tài khoản (Warm-up)...")
    if warmup_time is None:
        warmup_time = random.randint(120, 240) # 2-4 phút
    start_time = time.time()
    
    # Ưu tiên News Feed để có nhiều link tương tác
    url = "https://www.facebook.com/"
    driver.get(url)
    
    while (time.time() - start_time) < warmup_time:
        scroll_amount = random.randint(400, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(4, 9))
        
        # Ngẫu nhiên mở link (khoảng 20% cơ hội mỗi lần cuộn)
        if random.random() < 0.2:
            try:
                # Tìm các link tiềm năng (bài viết, link chia sẻ...)
                candidates = driver.find_elements(By.CSS_SELECTOR, 'a[role="link"]:not([data-scanned="true"])')
                
                # Lọc links có vẻ là bài viết hoặc permalink
                post_links = [c for c in candidates if c.get_attribute("href") and 
                             ("/posts/" in c.get_attribute("href") or 
                              "/permalink/" in c.get_attribute("href") or 
                              "story_fbid" in c.get_attribute("href"))]
                
                if post_links:
                    target = random.choice(post_links)
                    # Đánh dấu đã quét để tránh click lại chính nó
                    driver.execute_script("arguments[0].setAttribute('data-scanned', 'true')", target)
                    
                    link_href = target.get_attribute("href")
                    print(f"[{uid}] 🖱️ Ngẫu nhiên mở link: {link_href[:60]}...")
                    
                    # Click trực tiếp trong cùng tab
                    target.click()
                    
                    # Chờ 5-10s giả lập đang đọc
                    wait_view = random.randint(5, 50)
                    print(f"[{uid}] ⏳ Đang xem nội dung trong {wait_view}s...")
                    time.sleep(wait_view)
                    
                    # Quay lại Feed để tiếp tục nuôi
                    driver.back()
                    time.sleep(3)
                    print(f"[{uid}] 🔙 Đã quay lại News Feed.")
            except Exception:
                # Bỏ qua lỗi nhỏ khi tìm link/click để không làm crash luồng nuôi
                pass
        
        # Ngẫu nhiên thả cảm xúc (Giảm xuống còn khoảng 5% cơ hội mỗi lần cuộn để tránh spam Like)
        if random.random() < 0.05:
            random_like_post(driver, uid)

    print(f"[{uid}] ✅ Hoàn thành warm-up.")
