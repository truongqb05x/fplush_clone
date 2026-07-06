import time
import re
import sys
import os
from bs4 import BeautifulSoup

# Add project root to path if running from utils/
if os.path.basename(os.getcwd()) == 'utils':
    sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
else:
    sys.path.append(os.getcwd())

from utils.driver_utils import create_driver
import threading

# Global cache for joined groups: {uid: [group_data, ...]}
GROUP_CACHE = {}
CACHE_LOCK = threading.Lock()

def get_joined_groups(driver, max_scrolls=5, uid=None):
    """
    Navigates to the Joined Groups page and extracts all group links and UIDs.
    Uses memory cache if uid is provided to avoid rescanning in the same session.
    """
    if uid:
        with CACHE_LOCK:
            if uid in GROUP_CACHE:
                print(f"📂 [Scan] Loading groups from memory cache for UID {uid}...")
                return GROUP_CACHE[uid]

    url = "https://www.facebook.com/groups/joins/?nav_source=tab"
    print(f"📂 [Scan] Navigating to joined groups page...")
    driver.get(url)
    time.sleep(4)
    
    seen_urls = set()
    group_data = []

    # Scroll loop to load more groups
    for i in range(max_scrolls):
        print(f"   📜 Scrolling to load more groups ({i+1}/{max_scrolls})...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # Tìm tất cả các item trong danh sách nhóm
        items = soup.find_all('div', role='listitem')
        print(f"   🔍 [Debug] Tìm thấy {len(items)} items trong HTML hiện tại.")
        
        for idx, item in enumerate(items):
            # Lấy link của nhóm trong item này
            link_tag = item.find('a', href=True)
            if not link_tag:
                continue
                
            href = link_tag.get('href', '')
            if '/groups/' in href and not any(x in href for x in ['/feed/', '/discover/', '/joins/', '/posts/', '/permalink/', 'category=create', 'ordering=viewer_added']):
                
                # Kiểm tra text trong item để lọc nhóm chờ phê duyệt
                item_text = item.get_text(separator=" ", strip=True)
                item_text_lower = item_text.lower()
                
                # Debug chi tiết nội dung từng item
                display_text = item_text.replace('\n', ' ')[:100]
                print(f"      🔹 Item #{idx+1}: {display_text}...")

                # Các dấu hiệu nhóm chưa vào được (Case-insensitive)
                pending_keywords = [
                    "group title pending", "chờ phê duyệt", "yêu cầu đã gửi", 
                    "hủy yêu cầu", "request sent", "cancel request",
                    "đã yêu cầu tham gia", "trả lời câu hỏi", "cập nhật câu trả lời",
                    "yêu cầu tham gia"
                ]
                
                found_kw = next((kw for kw in pending_keywords if kw in item_text_lower), None)
                if found_kw:
                    print(f"      ⏩ [Skip] Lọc bỏ vì chứa: '{found_kw}'")
                    continue

                clean_url = href.split('?')[0].rstrip('/')
                if not clean_url.startswith('http'):
                    clean_url = "https://www.facebook.com" + clean_url
                
                if clean_url in seen_urls or clean_url.endswith('/groups'):
                    continue
                    
                seen_urls.add(clean_url)
                
                # Extract UID
                uid_match = re.search(r'/groups/(\d+)/?$', clean_url)
                uid = uid_match.group(1) if uid_match else "N/A"
                
                # Extract Name
                name = link_tag.get_text(strip=True)
                if not name or name == "Xem nhóm":
                    name_tag = item.find(['h2', 'span'], dir='auto')
                    if name_tag:
                        name = name_tag.get_text(strip=True)
                
                if not name: name = "Unknown Group"
                
                print(f"      ✅ [Keep] Chấp nhận nhóm: '{name}' (UID: {uid})")

                group_data.append({
                    'name': name,
                    'link': clean_url,
                    'uid': uid
                })
        
        # Stop if we seem to have reached the end (page height doesn't change)
        # Or just stick to max_scrolls for safety
        
    print(f"✅ [Scan] Finished. Found {len(group_data)} groups total.")
    
    if uid and group_data:
        with CACHE_LOCK:
            GROUP_CACHE[uid] = group_data
            print(f"💾 [Scan] Cached {len(group_data)} groups in memory for {uid}.")
            
    return group_data

if __name__ == "__main__":
    # Example standalone usage (requires manual login or existing session)
    print("🚀 Running scan_group.py as standalone...")
    driver = None
    try:
        # NOTE: This part is for local testing. In production, main.py calls get_joined_groups()
        driver, wait, proxy = create_driver()
        
        # You would need to add cookie login here if testing standalone
        # See main.py for login logic
        
        print("⚠️ Standalone test requires an active session. Please log in first.")
        # groups = get_joined_groups(driver)
        # print(f"Found {len(groups)} groups.")
        
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        if driver:
            print("\n🏁 Closing browser...")
            driver.quit()
