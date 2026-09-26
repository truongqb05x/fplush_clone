# -*- coding: utf-8 -*-
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from actions.utils.like_actions import random_like_post
from actions.utils.read_notifications import read_one_random_notification
from actions.utils.chat_two_ways import run_two_way_chat

def warm_up_account(driver, uid, warmup_time=None, cfg=None):
    if warmup_time is None:
        warmup_time = random.randint(120, 240) # 2-4 phút
    start_time = time.time()
    
    # Parse cfg
    is_like_post = False
    allowed_reactions = []
    reaction_delay_min = 5
    reaction_delay_max = 15
    if cfg:
        is_like_post = cfg.get("IsLikePost", False)
        if cfg.get("IsReactionLike"): allowed_reactions.extend(["Thích", "Like"])
        if cfg.get("IsReactionLove"): allowed_reactions.extend(["Yêu thích", "Love"])
        if cfg.get("IsReactionCare"): allowed_reactions.extend(["Thương thương", "Care"])
        if cfg.get("IsReactionHaha"): allowed_reactions.extend(["Haha"])
        if cfg.get("IsReactionWow"): allowed_reactions.extend(["Wow"])
        if cfg.get("IsReactionSad"): allowed_reactions.extend(["Buồn", "Sad"])
        if cfg.get("IsReactionAngry"): allowed_reactions.extend(["Phẫn nộ", "Angry"])
        reaction_delay_min = cfg.get("ReactionDelayMin", 5)
        reaction_delay_max = cfg.get("ReactionDelayMax", 15)
        is_read_noti = cfg.get("IsReadNoti", False)
        read_noti_count = cfg.get("ReadNotiCount", 5)
        is_chat = cfg.get("IsChat", False)
        is_random_click = cfg.get("IsRandomClick", True)
    else:
        is_read_noti = False
        read_noti_count = 5
        is_chat = False
        is_random_click = True

    if is_read_noti:
        print(f"[{uid}]  Bắt đầu đọc {read_noti_count} thông báo...")
        for _ in range(read_noti_count):
            read_one_random_notification(driver, uid)
            time.sleep(random.uniform(2, 5))

    if is_chat:
        print(f"[{uid}]  Bắt đầu mở hộp thoại chat...")
        run_two_way_chat(driver, uid, task_config=cfg)
        time.sleep(3)

    # Ưu tiên News Feed để có nhiều link tương tác
    url = "https://www.facebook.com/"
    driver.get(url)
    
    while (time.time() - start_time) < warmup_time:
        scroll_amount = random.randint(400, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(4, 9))
        
        # Ngẫu nhiên mở link (khoảng 20% cơ hội mỗi lần cuộn)
        if is_random_click and random.random() < 0.2:
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
                    
                    # Click trực tiếp trong cùng tab
                    target.click()
                    
                    # Tính toán thời gian xem sao cho không vượt quá thời gian nuôi còn lại
                    remaining_time = warmup_time - (time.time() - start_time)
                    wait_view = random.randint(5, 50)
                    
                    # Cắt giảm thời gian xem nếu sắp hết giờ (chừa lại 3s để load & back)
                    if wait_view > remaining_time - 3:
                        wait_view = int(remaining_time - 3)
                    
                    if wait_view > 0:
                        end_view_time = time.time() + wait_view
                        
                        # Vòng lặp cuộn dần dần để giả lập người dùng đọc nội dung
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
                    
                    # Quay lại Feed để tiếp tục nuôi
                    driver.back()
                    time.sleep(3)
            except Exception:
                # Bỏ qua lỗi nhỏ khi tìm link/click để không làm crash luồng nuôi
                pass
        
        # Logic like bài viết
        if is_like_post:
            # Ngẫu nhiên thả cảm xúc theo cấu hình (tỷ lệ 15% mỗi lần cuộn)
            if random.random() < 0.15:
                delay = random.uniform(reaction_delay_min, reaction_delay_max)
                time.sleep(delay)
                random_like_post(driver, uid, allowed_reactions=allowed_reactions)
        else:
            # Ngẫu nhiên thả cảm xúc mặc định (Giảm xuống còn khoảng 5% cơ hội mỗi lần cuộn để tránh spam Like)
            if random.random() < 0.05:
                random_like_post(driver, uid)

    print(f"[{uid}] ✅ Hoàn thành warm-up.")
