# config.py

COOKIE_FILE = "resources/account.txt"
LOAD_IMAGES = True  # Đổi thành True nếu muốn xem hình ảnh để kiểm tra giao diện

# --- PROFILE CONFIG ---
# Thư mục chứa profile của Chrome. 
# Có thể đổi thành đường dẫn tuyệt đối (ví dụ r"D:\shared_profiles") để dùng chung giữa nhiều bản copy của tool.
# Mặc định là thư mục "profiles" nằm ngay bên trong thư mục chạy tool.
PROFILE_DIR = "profiles"



# --- DRIVER & RESOURCE CONFIG ---
# Trỏ thủ công đến file chromedriver.exe nếu bản tự động tải về bị lỗi [WinError 193] trên VPS
# Ví dụ: CHROMEDRIVER_PATH = r"C:\path\to\chromedriver.exe"
CHROMEDRIVER_PATH = "resources/chromedriver.exe" 

# Ẩn các cảnh báo về thiếu file proxy/useragent nếu đặt là False
RESOURCE_LOGGING = False


# Cấu hình Avatar
AVATAR_FOLDER = "C:\\Users\\Administrator\\Downloads\\Avatar"
AVATAR_STT_FILE = "resources/stt.txt"

# Cấu hình File Paths
KIOT_FILE = "resources/kiot.txt"
PAGES_FILE = "resources/id_pages.txt"
TTC_COMMENTED_FILE = "resources/ttc_commented.txt"
GROUP_FILE = "resources/group.txt"
TARGET_GROUPS_FILE = "resources/target_groups.txt"
CONFIG_JSON_FILE = "resources/config.json"
KEYWORD_FILE = "resources/keyword.txt"
GROUP_JOIN_FILE = "resources/id_groups_join.txt"