import time
import os
import random
import base64
import logging
import threading

# Ẩn các log lỗi ồn ào của seleniumwire (mitmproxy)
logging.getLogger('seleniumwire').setLevel(logging.CRITICAL)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.driver_utils import create_driver, load_proxies
from config import config

from utils.account_registry import (
    load_proxy_mapping, get_assigned_ua,
    get_assigned_proxy, parse_proxy_str,
    load_kiot_mapping, get_assigned_kiot
)
from utils.kiot_proxy import get_new_kiot_proxy, parse_kiot_proxy_string

# Cấu hình cửa sổ
WIN_WIDTH = 500
WIN_HEIGHT = 700

def get_window_pos(index):
    # Cửa sổ thứ index sẽ nằm cạnh nhau
    return (index * WIN_WIDTH, 0, WIN_WIDTH, WIN_HEIGHT)

def get_profile_path(uid):
    profile_dir = getattr(config, "PROFILE_DIR", "profiles")
    if not os.path.isabs(profile_dir):
        profile_dir = os.path.join(os.getcwd(), profile_dir)
    return os.path.join(profile_dir, uid)

def get_random_post(target_uid, access_token, limit=10):
    import requests
    url = f"https://graph.facebook.com/v23.0/{target_uid}/posts"
    params = {
        "access_token": access_token,
        "fields": "id,message,created_time,permalink_url,full_picture",
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.ok:
            data = response.json()
            posts = data.get("data", [])
            if not posts:
                return None
            
            # Chọn ngẫu nhiên một bài viết
            random_post = random.choice(posts)
            
            message = random_post.get("message", "")
            picture_url = random_post.get("full_picture", "")
            
            image_path = None
            if picture_url:
                try:
                    img_res = requests.get(picture_url, timeout=15)
                    if img_res.ok:
                        temp_dir = os.path.join(os.getcwd(), "temp_images")
                        os.makedirs(temp_dir, exist_ok=True)
                        image_path = os.path.join(temp_dir, f"post_img_{int(time.time())}.jpg")
                        with open(image_path, "wb") as f:
                            f.write(img_res.content)
                except Exception as e:
                    print(f"Lỗi tải ảnh từ bài viết: {e}")
                    
            return {
                "id": random_post.get("id"),
                "message": message,
                "image_path": image_path,
                "permalink_url": random_post.get("permalink_url")
            }
        else:
            print("HTTP Error:", response.status_code, response.text)
            return None
    except Exception as e:
        print(f"Lỗi gọi API: {e}")
        return None

def post_manual_content(driver, uid, post_content=None, image_path=None):
    import time
    def do_click(xpath, fallback_texts=None):
        from selenium.webdriver.common.action_chains import ActionChains
        end_time = time.time() + 60
        while time.time() < end_time:
            try:
                # 1. Thử dùng XPath
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    try:
                        # Cuộn phần tử vào giữa màn hình
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", el)
                        time.sleep(0.5)
                        
                        if el.is_displayed():
                            # Cách 1: Click bằng ActionChains (giả lập chuột thật nhất)
                            try:
                                ActionChains(driver).move_to_element(el).click().perform()
                                time.sleep(1)
                                return
                            except:
                                pass
                            
                        # Cách 2: Click bằng Javascript
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(1)
                        return
                    except:
                        pass
                
                # 2. Fallback dùng JS tìm bằng chữ và click theo toạ độ
                if fallback_texts:
                    success = driver.execute_script("""
                        var texts = arguments[0].map(function(t) { return t.toLowerCase(); });
                        
                        function tryClick(el) {
                            try { el.click(); } catch(e) {}
                            try {
                                ['mousedown', 'mouseup', 'click'].forEach(function(eventType) {
                                    el.dispatchEvent(new MouseEvent(eventType, {
                                        view: window, bubbles: true, cancelable: true, buttons: 1
                                    }));
                                });
                            } catch(e) {}
                        }
                        
                        var spans = document.querySelectorAll('span');
                        for (var i = 0; i < spans.length; i++) {
                            var text = (spans[i].innerText || spans[i].textContent || "").trim().toLowerCase();
                            if (text) {
                                for (var j = 0; j < texts.length; j++) {
                                    if (text.includes(texts[j])) {
                                        var target = spans[i];
                                        // Cuộn tới
                                        target.scrollIntoView({block: 'center'});
                                        
                                        // Tìm thẻ div cha có role button
                                        var curr = target;
                                        while (curr && curr !== document.body) {
                                            if (curr.getAttribute('role') === 'button' || curr.tagName.toLowerCase() === 'div' && curr.getAttribute('aria-label')) {
                                                target = curr;
                                                break;
                                            }
                                            curr = curr.parentElement;
                                        }
                                        
                                        tryClick(target);
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    """, fallback_texts)
                    if success:
                        time.sleep(1)
                        return
            except Exception:
                pass
            time.sleep(1)
        print(f"[Account-{uid}] Không thể click vào phần tử: {fallback_texts if fallback_texts else xpath} sau 60s")

    print(f"[Account-{uid}] Truy cập trang chủ Facebook...")
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    # Vòng lặp tối đa 3 lần để xử lý việc tải lại trang nếu gặp modal Lưu
    for attempt in range(3):
        print(f"[Account-{uid}] (Lần {attempt+1}) Đang tìm và nhấn vào 'Bạn đang nghĩ gì thế?' (What's on your mind?)...")
        do_click(
            "//div[@role='button'][.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nghĩ gì') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mind')]] | //span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nghĩ gì')]", 
            ["nghĩ gì", "mind", "tạo bài viết", "create post"]
        )

        print(f"[Account-{uid}] Đang kiểm tra các popup đăng bài (chờ thông minh tối đa 60s)...")
        end_time_popup = time.time() + 60
        is_ready = False
        while time.time() < end_time_popup:
            try:
                # 1. Kiểm tra xem có bảng Chọn đối tượng (Công khai / Lưu) không
                cong_khai_xpath = "//span[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='công khai' or translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='public'] | //div[@role='radio' or @role='button']//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'công khai')]"
                luu_xpath = "//div[contains(@aria-label, 'Lưu') or contains(@aria-label, 'Save')][@role='button'] | //span[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='lưu' or translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='save']"
                
                cong_khai_els = driver.find_elements(By.XPATH, cong_khai_xpath)
                luu_els = driver.find_elements(By.XPATH, luu_xpath)
                if cong_khai_els and any(t.is_displayed() for t in cong_khai_els) and luu_els and any(t.is_displayed() for t in luu_els):
                    print(f"[Account-{uid}] Phát hiện bảng 'Chọn đối tượng', đang chọn 'Công khai'...")
                    do_click(cong_khai_xpath, ["công khai", "public"])
                    time.sleep(1)
                    print(f"[Account-{uid}] Đang nhấn 'Lưu' (Save)...")
                    do_click(luu_xpath, ["lưu", "save"])
                    print(f"[Account-{uid}] Đã lưu đối tượng. Đang tải lại trang (F5)...")
                    time.sleep(3) # Đợi Facebook ghi nhận thao tác
                    driver.refresh()
                    time.sleep(5)
                    break # Thoát vòng check popup để thực hiện lại từ đầu việc click "Tạo bài viết"
                
                # 2. Kiểm tra xem có nút Tiếp tục (Continue) không
                tiep_tuc_xpath = "//div[@aria-label='Tiếp tục' or @aria-label='Continue'][@role='button'] | //span[text()='Tiếp tục' or text()='Continue']"
                tiep_tuc = driver.find_elements(By.XPATH, tiep_tuc_xpath)
                if tiep_tuc and any(t.is_displayed() for t in tiep_tuc):
                    print(f"[Account-{uid}] Phát hiện popup 'Xem lại đối tượng', đang nhấn 'Tiếp tục'...")
                    do_click(tiep_tuc_xpath, ["tiếp tục", "continue"])
                    time.sleep(1)
                    continue  # Tiếp tục vòng lặp để check popup tiếp theo
                
                # 3. Kiểm tra xem ô nhập nội dung bài viết đã xuất hiện chưa (nếu xuất hiện tức là không bị popup chặn)
                textbox_xpath = "//div[@role='textbox' and @contenteditable='true']"
                textbox = driver.find_elements(By.XPATH, textbox_xpath)
                if textbox and any(tb.is_displayed() for tb in textbox):
                    print(f"[Account-{uid}] Khung đăng bài đã sẵn sàng (không bị popup chặn).")
                    is_ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
            
        if is_ready:
            try:
                print(f"[Account-{uid}] Đang tìm và nhấn nút 'Cảm xúc/hoạt động' (Feeling/Activity)...")
                camxuc_xpath = "//div[@aria-label='Cảm xúc/hoạt động' or @aria-label='Feeling/activity'][@role='button']"
                camxuc_els = driver.find_elements(By.XPATH, camxuc_xpath)
                clicked_camxuc = False
                for el in camxuc_els:
                    if el.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", el)
                            clicked_camxuc = True
                            print(f"[Account-{uid}] Đã click 'Cảm xúc/hoạt động' bằng JS!")
                            break
                        except Exception as e:
                            print(f"[Account-{uid}] Lỗi click JS: {e}")
                
                if not clicked_camxuc:
                    # Fallback về hàm do_click nếu JS click không thành công
                    do_click(camxuc_xpath, ["cảm xúc", "feeling"])
                    
                import random
                time.sleep(random.uniform(2.0, 3.5))
                
                # Chọn random cảm xúc
                try:
                    print(f"[Account-{uid}] Đang chọn ngẫu nhiên một cảm xúc...")
                    # Lấy tất cả các thẻ có role='button' bên trong danh sách listbox/option
                    feelings = driver.find_elements(By.XPATH, "//ul[@role='listbox']//li[@role='option']//div[@role='button']")
                    visible_feelings = [f for f in feelings if f.is_displayed()]
                    if visible_feelings:
                        random_feeling = random.choice(visible_feelings)
                        feeling_name = random_feeling.get_attribute("aria-label")
                        print(f"[Account-{uid}] Đã bốc trúng cảm xúc: {feeling_name}")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_feeling)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", random_feeling)
                        print(f"[Account-{uid}] Đã click chọn cảm xúc thành công!")
                    else:
                        print(f"[Account-{uid}] Không tìm thấy danh sách cảm xúc để chọn!")
                except Exception as e:
                    print(f"[Account-{uid}] Lỗi khi chọn cảm xúc: {e}")
                    
                time.sleep(random.uniform(1.5, 3.0))

                print(f"[Account-{uid}] Đang tải lên file ảnh/video...")
                try:
                    file_path = image_path if image_path else r"D:\facebook\Tools\spam_comment_group\resources\images\OK.png"
                    if file_path and os.path.exists(file_path):
                        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
                        file_input.send_keys(file_path)
                        print(f"[Account-{uid}] Đã gửi lệnh tải lên file: {file_path}")
                        time.sleep(random.uniform(3.0, 5.0)) # Đợi ảnh xử lý
                except Exception as e:
                    print(f"[Account-{uid}] Lỗi khi tải ảnh lên: {e}")

                content = post_content if post_content else f"Hôm nay thật tuyệt vời! {random.randint(1000, 9999)}"
                print(f"[Account-{uid}] Đang nhập nội dung bài viết: '{content}'")
                
                # Lấy lại element textbox
                textbox_xpath = "//div[@role='textbox' and @contenteditable='true']"
                textboxes = driver.find_elements(By.XPATH, textbox_xpath)
                tb = next((t for t in textboxes if t.is_displayed()), None)
                
                if tb:
                    try:
                        # Cuộn phần tử vào giữa màn hình
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tb)
                        time.sleep(0.5)
                        
                        # Cách 1: Dùng ActionChains click và gõ vào active element
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(tb).click().perform()
                        time.sleep(0.5)
                        
                        active_el = driver.switch_to.active_element
                        for char in content:
                            active_el.send_keys(char)
                            time.sleep(random.uniform(0.02, 0.1))
                            
                    except Exception as e:
                        print(f"[Account-{uid}] Lỗi gõ bằng ActionChains, thử cách 2... ({e})")
                        # Cách 2: Fallback click JS và send_keys trực tiếp
                        driver.execute_script("arguments[0].click();", tb)
                        time.sleep(0.5)
                        for char in content:
                            tb.send_keys(char)
                            time.sleep(random.uniform(0.02, 0.1))
                            
                    time.sleep(2)
                else:
                    print(f"[Account-{uid}] Lỗi: Không tìm thấy ô nhập nội dung đang hiển thị!")
                
                react_click_script = """
                var el = arguments[0];
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                """

                # Hàm mở rộng menu 3 chấm
                def open_more_options():
                    print(f"[Account-{uid}] Đang thử click nút 3 chấm 'Lựa chọn khác' để mở menu...")
                    # Blur ô nhập text trước khi click để tránh React nuốt mất click đầu tiên
                    driver.execute_script("if(document.activeElement) document.activeElement.blur();")
                    time.sleep(0.5)
                    
                    xp = "//div[@role='dialog']//div[@aria-label='Lựa chọn khác cho bài viết' or @aria-label='More options for your post'][@role='button']"
                    els = driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                                time.sleep(0.5)
                                driver.execute_script(react_click_script, el)
                                print(f"[Account-{uid}] Đã mở menu thành công (MouseEvent)!")
                                time.sleep(random.uniform(1.0, 2.0))
                                return True
                            except:
                                pass
                    return False

                open_more_options()

                print(f"[Account-{uid}] Đang tìm và nhấn nút 'Check in'...")
                checkin_xpath = "//div[@role='dialog']//div[@aria-label='Check in' or @aria-label='Check In'][@role='button']"
                checkin_els = driver.find_elements(By.XPATH, checkin_xpath)
                clicked_checkin = False
                for el in checkin_els:
                    if el.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            time.sleep(0.5)
                            driver.execute_script(react_click_script, el)
                            clicked_checkin = True
                            print(f"[Account-{uid}] Đã click 'Check in' bằng JS (MouseEvent)!")
                            break
                        except Exception as e:
                            print(f"[Account-{uid}] Lỗi click JS Check in: {e}")
                
                if not clicked_checkin:
                    do_click(checkin_xpath, ["check in", "check-in"])
                    
                time.sleep(random.uniform(2.0, 3.5))
                
                # Chọn random vị trí
                try:
                    print(f"[Account-{uid}] Đang chọn ngẫu nhiên một vị trí...")
                    locations = driver.find_elements(By.XPATH, "//ul[@role='listbox']//li[@role='option']//div[@role='button'] | //ul[@role='listbox']//li[@role='option']")
                    visible_locs = [loc for loc in locations if loc.is_displayed()]
                    if visible_locs:
                        random_loc = random.choice(visible_locs)
                        # Lấy text hiển thị của location
                        loc_name = random_loc.text.replace('\n', ' - ') if random_loc.text else "Một vị trí nào đó"
                        if not loc_name.strip():
                            loc_name = random_loc.get_attribute("aria-label") or "Một vị trí ẩn danh"
                        
                        print(f"[Account-{uid}] Đã bốc trúng vị trí: {loc_name}")
                        try:
                            click_target = random_loc.find_element(By.XPATH, ".//div[contains(@class, 'x1i10hfl')] | .//div[@role='button'] | .//div[@role='none']")
                        except:
                            click_target = random_loc
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_target)
                        time.sleep(0.5)
                        driver.execute_script(react_click_script, click_target)
                        print(f"[Account-{uid}] Đã click chọn vị trí thành công (MouseEvent)!")
                    else:
                        print(f"[Account-{uid}] Không tìm thấy danh sách vị trí để chọn!")
                except Exception as e:
                    print(f"[Account-{uid}] Lỗi khi chọn vị trí: {e}")
                    
                time.sleep(random.uniform(1.5, 3.0))
                
                open_more_options()

                print(f"[Account-{uid}] Đang tìm và nhấn nút 'Gắn thẻ người khác' (Tag people)...")
                tag_xpath = "//div[@role='dialog']//div[@aria-label='Gắn thẻ người khác' or @aria-label='Tag people'][@role='button']"
                tag_els = driver.find_elements(By.XPATH, tag_xpath)
                clicked_tag = False
                for el in tag_els:
                    if el.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            time.sleep(0.5)
                            driver.execute_script(react_click_script, el)
                            clicked_tag = True
                            print(f"[Account-{uid}] Đã click 'Gắn thẻ người khác' bằng JS (MouseEvent)!")
                            break
                        except Exception as e:
                            print(f"[Account-{uid}] Lỗi click JS Gắn thẻ: {e}")
                
                if not clicked_tag:
                    do_click(tag_xpath, ["gắn thẻ", "tag"])
                    
                time.sleep(random.uniform(2.0, 3.5))
                
                # Chọn random 1-3 bạn bè
                try:
                    print(f"[Account-{uid}] Đang chọn ngẫu nhiên bạn bè để gắn thẻ...")
                    friends = driver.find_elements(By.XPATH, "//ul[@role='listbox']//li[@role='option']")
                    visible_friends = [f for f in friends if f.is_displayed()]
                    if visible_friends:
                        num_to_tag = random.randint(1, min(3, len(visible_friends)))
                        random_friends = random.sample(visible_friends, num_to_tag)
                        
                        for i, friend in enumerate(random_friends):
                            friend_name = friend.text.replace('\n', ' - ') if friend.text else f"Bạn bè {i+1}"
                            print(f"[Account-{uid}] Đang gắn thẻ: {friend_name}")
                            try:
                                click_target = friend.find_element(By.XPATH, ".//div[contains(@class, 'x1i10hfl')] | .//div[@role='button'] | .//div[@role='none']")
                            except:
                                click_target = friend
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_target)
                            time.sleep(0.5)
                            driver.execute_script(react_click_script, click_target)
                            time.sleep(0.5)
                        
                        print(f"[Account-{uid}] Đã gắn thẻ xong {num_to_tag} người, đang nhấn nút 'Xong'...")
                        xong_xpath = "//div[@role='button'][.//span[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='xong' or translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='done']]"
                        xong_els = driver.find_elements(By.XPATH, xong_xpath)
                        clicked_xong = False
                        for el in xong_els:
                            if el.is_displayed():
                                try:
                                    driver.execute_script(react_click_script, el)
                                    clicked_xong = True
                                    break
                                except:
                                    pass
                        
                        if not clicked_xong:
                            do_click(xong_xpath, ["xong", "done"])
                            
                    else:
                        print(f"[Account-{uid}] Không tìm thấy danh sách bạn bè để gắn thẻ!")
                except Exception as e:
                    print(f"[Account-{uid}] Lỗi khi gắn thẻ bạn bè: {e}")
                    
                time.sleep(random.uniform(2.0, 4.0))
                
                # print(f"[Account-{uid}] Đang tìm và nhấn nút 'Đăng' (Post)...")
                # dang_xpath = "//div[@aria-label='Đăng' or @aria-label='Post'][@role='button'] | //div[@role='button']//span[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='đăng' or translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='post']"
                # do_click(dang_xpath, ["đăng", "post"])
                # print(f"[Account-{uid}] Đã gửi lệnh click Đăng bài thành công!")
                # 
                # wait_time = random.uniform(10, 15)
                # print(f"[Account-{uid}] Đang đợi {wait_time:.1f} giây để hoàn tất quá trình đăng bài...")
                # time.sleep(wait_time)
                # print(f"[Account-{uid}] HOÀN THÀNH: Quá trình đăng bài đã thành công!")
            except Exception as e:
                print(f"[Account-{uid}] Lỗi khi nhập văn bản hoặc click Đăng: {e}")
                
            break # Thoát khỏi vòng lặp for nếu đã mở được popup thành công
        else:
            if time.time() >= end_time_popup:
                print(f"[Account-{uid}] Quá 60s không thấy khung đăng bài hay popup nào. Bỏ qua.")
                break



def run_account_flow(cookie_line, mode="1"):
    parts = cookie_line.split("|")
    uid = parts[0]
    password = parts[1] if len(parts) > 1 else ""
    cookie_str = "|".join(parts[2:]) if len(parts) > 2 else ""
    
    print(f"[Account-{uid}] Bắt đầu tài khoản UID: {uid}")
    

    user_agent = None
    actual_cookies = []
    for c in cookie_str.split(";"):
        c = c.strip()
        if not c: continue
        if "=" in c:
            k, v = c.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k.lower() == "useragent":
                try:
                    user_agent = base64.b64decode(v).decode('utf-8')
                except:
                    user_agent = v
            else:
                actual_cookies.append({"name": k, "value": v})
                    
    if not user_agent:
        import utils.account_registry as ar
        mapping_ua = ar.load_ua_mapping()
        user_agent = get_assigned_ua(uid, mapping_ua)
        
    proxy_config = None
    proxy_str = None
    kiot_keys = []
    kiot_file = getattr(config, "KIOT_FILE", "resources/kiot.txt")
    if os.path.exists(kiot_file):
        with open(kiot_file, "r", encoding="utf-8") as f:
            kiot_keys = [l.strip() for l in f if l.strip()]
            
    if kiot_keys:
        mapping_kiot = load_kiot_mapping()
        assigned_kiot_key = get_assigned_kiot(uid, kiot_keys, mapping_kiot)
        if assigned_kiot_key:
            kiot_proxy_str = get_new_kiot_proxy(assigned_kiot_key)
            if kiot_proxy_str:
                proxy_config = parse_kiot_proxy_string(kiot_proxy_str)
                proxy_str = kiot_proxy_str

    if not proxy_config:
        mapping_proxy = load_proxy_mapping()
        all_proxies = load_proxies()
        proxy_str = get_assigned_proxy(uid, all_proxies, mapping_proxy)
        if proxy_str:
            proxy_config = parse_proxy_str(proxy_str)
            
    print(f"[Account-{uid}] Proxy: {proxy_str if proxy_str else 'Direct'}")
    
    profile_path = get_profile_path(uid)
    win_pos = get_window_pos(0)
    
    try:
        driver, wait, _ = create_driver(
            user_data_dir=profile_path,
            proxy_config=proxy_config,
            window_pos=win_pos,
            user_agent=user_agent
        )
        
        driver.get("https://www.facebook.com/")
        print(f"[Account-{uid}] Kiểm tra login...")
        time.sleep(5)
        
        current_cookies = driver.get_cookies()
        has_c_user = any(c['name'] == 'c_user' and uid in str(c['value']) for c in current_cookies)
                
        is_logged_in = False
        if has_c_user:
            try:
                login_els = driver.find_elements(By.NAME, "login") or driver.find_elements(By.ID, "loginbutton") or driver.find_elements(By.XPATH, "//*[text()='Đăng nhập' or text()='Log In']")
                if not login_els:
                    is_logged_in = True
            except: pass
            
        if is_logged_in:
            print(f"[Account-{uid}] Đã lưu phiên đăng nhập!")
        else:
            print(f"[Account-{uid}] Nạp cookie mới...")
            expiry_time = int(time.time()) + (365 * 24 * 3600)
            for cookie_dict in actual_cookies:
                try: 
                    cookie_dict["domain"] = ".facebook.com"
                    cookie_dict["path"] = "/"
                    cookie_dict["expiry"] = expiry_time
                    driver.add_cookie(cookie_dict)
                except:
                    pass
            driver.refresh()
            time.sleep(8)
            
        def verify_uid(dr, t_uid):
            curr_url = dr.current_url or ""
            if t_uid in curr_url or f"profile.php?id={t_uid}" in curr_url or "/me" in curr_url: return True
            cookies = dr.get_cookies()
            if any(c['name'] == 'c_user' and str(c['value']) == str(t_uid) for c in cookies): return True
            ps = dr.page_source
            if f'\"userID\":\"{t_uid}\"' in ps or f'\"ACCOUNT_ID\":\"{t_uid}\"' in ps: return True
            return False

        login_verified = verify_uid(driver, uid)
        if not login_verified:
            driver.get("https://www.facebook.com/me")
            time.sleep(5)
            login_verified = verify_uid(driver, uid)
            
        if not login_verified:
            print(f"[Account-{uid}] Cookie lỗi, thử MK...")
            if password:
                from actions.login import login_with_credentials
                login_with_credentials(driver, uid, password)
                time.sleep(5)
                login_verified = verify_uid(driver, uid)
        
        if login_verified:
            print(f"[Account-{uid}] Xác minh login thành công.")
        else:
            print(f"[Account-{uid}] Không thể login, dừng luồng này.")
            return
            
        # Chức năng 1: Đăng bài nội dung thủ công
        if mode == "1":
            # Chức năng 1: Đăng bài nội dung thủ công
            post_manual_content(driver, uid)
        elif mode == "2":
            print(f"[Account-{uid}] Lấy bài viết ngẫu nhiên từ API...")
            target_uid = "100072095290428"
            access_token = "EAAAAUaZA8jlABQ7IWv8yBHIu1AnOHE8Wt4XqrACtZAKm0EERw8rcXoVIs2VQ2obfE98kpawmClywgMJzjEyJIYslODXFvAmr5v0ELBKs8Q6vMMX8dVgxpARgOPhPKzHkkKZAeGYpE2y8gNyStB1vWbwh2chje8H3CnNIAk8IXszu4LOEPZA4lMZAFvU1TEZBbz2PcX00EZCzwZDZD"
            post_data = get_random_post(target_uid, access_token)
            if post_data:
                print(f"[Account-{uid}] Bài viết bốc được: {post_data['message']}")
                post_manual_content(driver, uid, post_content=post_data["message"], image_path=post_data["image_path"])
            else:
                print(f"[Account-{uid}] Lỗi không lấy được bài viết, dùng nội dung mặc định.")
                post_manual_content(driver, uid)

        time.sleep(10)
        print(f"[Account-{uid}] Đã hoàn tất logic.")
        input(f"\n[Account-{uid}] >>> Trình duyệt đang được giữ mở. NHẤN ENTER TẠI ĐÂY (cmd) ĐỂ KẾT THÚC... <<<\n")
        print(f"[Account-{uid}] Đang đóng trình duyệt...")
        driver.quit()
        
    except Exception as e:
        print(f"[Account-{uid}] Lỗi hoặc trình duyệt đóng: {e}")
        try:
            driver.quit()
        except:
            pass

def main():
    print("--- Bắt đầu Demo ---")
    
    print("Chọn chức năng đăng bài:")
    print("1. Đăng bài nội dung thủ công (Selenium)")
    print("2. Đăng bài qua Graph API (Đang phát triển)")
    mode = input("Nhập lựa chọn (1 hoặc 2) [Mặc định: 1]: ").strip()
    if mode not in ["1", "2"]:
        mode = "1"
        
    acc_file = getattr(config, 'COOKIE_FILE', "resources/account.txt")
    
    try:
        with open(acc_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            
        if not lines:
            return print("Lỗi: File account trống.")
            
        # Chạy trực tiếp không cần tạo Thread
        run_account_flow(lines[0], mode)
        
    except KeyboardInterrupt:
        print("\n[*] Dừng chương trình từ bàn phím.")
    except Exception as e:
        print(f"Lỗi khởi chạy: {e}")
    finally:
        print("[*] Đóng toàn bộ tiến trình...")
        os._exit(0)

if __name__ == "__main__":
    main()
