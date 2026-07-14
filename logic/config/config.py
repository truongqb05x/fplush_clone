# config.py

COOKIE_FILE = "resources/account.txt"
RESULT_FILE = "resources/result.txt"
AVATAR_FOLDER = r"C:\Users\Administrator\Downloads\avvt"
STT_FILE = "resources/stt.txt"
IS_EDIT_COMMENT = "yes"
LOAD_IMAGES = False  # Đổi thành True nếu muốn xem hình ảnh để kiểm tra giao diện
TARGET_GROUPS_FILE = "resources/target_groups.txt"

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

# XPATH GIAO DIỆN CŨ
BTN_SHOW_MODAL = "/html/body/div[1]/div[2]/div[1]/div/div/div[1]/div[2]/form/div[2]/div/a"
INPUT_EMAIL = "/html/body/div[5]/div[2]/div/div/form/div[2]/div/div/input"
BTN_SUBMIT_EMAIL = "/html/body/div[5]/div[2]/div/div/form/div[3]/button"
INPUT_OTP = "/html/body/div[1]/div[2]/div[1]/div/div/div[1]/div[2]/form/div[1]/div[1]/label/div/input"
BTN_CONFIRM_OTP = "/html/body/div[1]/div[2]/div[1]/div/div/div[1]/div[2]/form/div[2]/div/button"

# XPATH GIAO DIỆN MỚI - THEO BẠN CUNG CẤP
# Bước 1: Nút "Tôi không nhận được mã"
BTN_NO_CODE_NEW = "//span[contains(text(),'Tôi không nhận được mã')]"
BTN_NO_CODE_NEW_FULL = "/html/body/div[1]/div/div/div/div/div/div/div[1]/div/div/div[1]/div[1]/div/div/div/div/div/div/div[1]/div[2]/div/div/div/div/div/div/div[3]/div/div/div[2]/div/div/div/div[1]/div/span/span"

# Bước 2: Nút "Thay đổi số di động hoặc email" (sau khi click "Tôi không nhận được mã")
BTN_CHANGE_EMAIL_NEW = "//div[contains(text(),'Thay đổi số di động hoặc email')]"
BTN_CHANGE_EMAIL_NEW_FULL = "/html/body/div[4]/div[1]/div/div[2]/div/div/div/div/div/div/div[2]/div[2]/div[3]/div/div/div[2]/div/div[2]/div[1]"

# Bước 3: Input email (sau khi click "Thay đổi số di động hoặc email")
# Email input – loại trừ OTP (maxlength 5/6)
INPUT_EMAIL_NEW = (
    "//input[@type='text' and contains(@id,'_r_') "
    "and not(@maxlength='5') "
    "and not(@maxlength='6')]"
)
INPUT_EMAIL_NEW_FULL = "/html/body/div[4]/div[1]/div/div[2]/div/div/div/div/div[2]/div/div[2]/div[2]/div[3]/div/div/div[2]/div/div[1]/div[1]/input"

# Bước 4: Nút "Thêm" (sau khi nhập email)
BTN_ADD_NEW = "//span[contains(text(),'Thêm')]"
BTN_ADD_NEW_FULL = "/html/body/div[4]/div[1]/div/div[2]/div/div/div/div/div[2]/div/div[3]/div/div/div/div/div/div[2]/div[2]/div/div"

# Bước 5: Input OTP (sau khi click "Thêm")
INPUT_OTP_NEW = "//input[@maxlength='5' and @type='text']"
INPUT_OTP_NEW_FULL = "/html/body/div[1]/div/div[1]/div/div/div/div/div[1]/div/div/div[1]/div[1]/div/div/div/div/div/div/div[1]/div[2]/div/div/div/div/div/div/div[2]/div/div/div/div/div/div[1]/div[1]/input"

# Nút tiếp tục sau khi nhập OTP
BTN_CONFIRM_OTP_NEW = "//div[@role='button']//span[contains(text(),'Tiếp tục')]"
# Nút tiếp tục sau OTP (Tiếng Anh - full xpath)
BTN_CONFIRM_OTP_EN_FULL = "/html/body/div[1]/div/div/div/div/div/div/div[1]/div/div/div[1]/div[1]/div/div/div/div/div/div/div[1]/div[2]/div/div/div/div/div/div/div[4]/div/div/div[1]/div/div/div"

AVATAR_BUTTON = "//div[@aria-label='Hành động với ảnh đại diện']"
CHOOSE_AVATAR = "//span[text()='Chọn ảnh đại diện']"
UPLOAD_BUTTON = "//input[@type='file']"
STATUS_TEXTAREA = "//textarea"
SAVE_BUTTON = "//span[text()='Lưu']/ancestor::div[@role='none']"
DELAY_BETWEEN_ACCOUNTS = 5
# config.py

# --- PHẦN AVATAR (Hỗ trợ Anh/Việt) ---
# config.py

# --- PHẦN AVATAR (Hỗ trợ Anh/Việt) ---

# Bước 1: Nút Camera trên ảnh đại diện (Dùng aria-label)
AVATAR_BUTTON = "//div[@aria-label='Hành động với ảnh đại diện' or @aria-label='Update profile picture' or @aria-label='Profile picture actions']"

# Bước 2: Nút "Chọn ảnh đại diện" trong menu (Dùng role và text linh hoạt)
# Xpath này tìm menuitem có chứa icon hoặc text tương ứng
CHOOSE_AVATAR_UNIVERSAL = (
    "//div[@role='menuitem']//span[contains(text(),'Chọn ảnh đại diện') "
    "or contains(text(),'Choose profile picture') "
    "or contains(text(),'Select profile picture')]"
)

# Bước 3: Input file để upload (Dùng thuộc tính type chuẩn)
UPLOAD_INPUT_HIDDEN = "//input[@type='file' and contains(@accept, 'image')]"

# Bước 4: Nút Lưu cuối cùng
SAVE_BUTTON_UNIVERSAL = (
    "//div[@role='button']//span[text()='Lưu' "
    "or text()='Save' "
    "or text()='Done']"
)
# config.py

# XPath cho phần nhập Status (Description) - Hỗ trợ cả Anh/Việt
# Cách này tìm textarea nằm dưới thẻ có chữ Description hoặc nằm trong modal
STATUS_TEXTAREA = "//textarea[contains(@id, 'r_')] | //textarea[@aria-label='Mô tả'] | //span[text()='Description']/following-sibling::div//textarea"

# Nút Lưu cho giao diện mới (dựa trên các class bạn đã gửi ở turn trước)
SAVE_BUTTON_AVATAR = "//div[@role='button']//span[text()='Save' or text()='Lưu' or text()='Done']"
# Textarea để viết STT
STATUS_TEXTAREA = "//textarea"