import threading

KIOT_PROXY_LOCK = threading.Lock()
KIOT_PROXY_CACHE = {}

BLOCKED_ACCOUNTS = set()
SCANNED_GROUPS_CACHE = {}
SEEN_TTC_JOBS = set()

# Cấu hình cửa sổ (Grid layout)
WIN_WIDTH = 500
WIN_HEIGHT = 700
COLS = 3  

def get_window_pos(index):
    """Tính toán vị trí cửa sổ dựa trên index luồng"""
    col = index % COLS
    row = index // COLS
    x = col * (WIN_WIDTH + 10)
    y = row * (WIN_HEIGHT + 10)
    return (x, y, WIN_WIDTH, WIN_HEIGHT)
