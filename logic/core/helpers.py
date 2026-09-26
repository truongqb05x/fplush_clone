# -*- coding: utf-8 -*-
"""
Main Script: FB Spam Comment Group with Multi-threading & Persistent Proxies
"""
import time
import shutil
import os
import random
import json
import base64
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By

KIOT_PROXY_LOCK = threading.Lock()
KIOT_PROXY_CACHE = {}

from utils.helpers import (
    is_checkpoint, is_soft_checkpoint, safe_url, cleanup_seleniumwire
)
from utils.driver_utils import create_driver, load_proxies
from utils.file_utils import read_file
from config import config
from utils.scan_group import get_joined_groups

# Modular imports
from utils.locks import FILE_LOCK
from utils.account_registry import (
    load_proxy_mapping, save_proxy_mapping,
    load_ua_mapping, get_assigned_ua,
    get_assigned_proxy, parse_proxy_str,
    load_kiot_mapping, get_assigned_kiot
)
from utils.kiot_proxy import get_new_kiot_proxy, parse_kiot_proxy_string
from core.automation_service import process_group_cycle, process_keyword_search, process_page_cycle, process_ttc_cycle
from actions.feed_actions import warm_up_account
from actions.login import login_with_credentials
from actions.join_groups import join_single_group
from actions.out_group import out_groups_by_mode
from actions.TTC.get_job import fetch_ttc_jobs
from actions.utils.read_notifications import read_one_random_notification
from actions.utils.chat_two_ways import run_two_way_chat


import shutil
import os
from utils.locks import FILE_LOCK
from core.globals import *

def get_profile_path(uid):
    """Tính toán đường dẫn tuyệt đối của thư mục profile cho một UID"""
    profile_dir = getattr(config, "PROFILE_DIR", "profiles")
    if not os.path.isabs(profile_dir):
        profile_dir = os.path.join(os.getcwd(), profile_dir)
    return os.path.join(profile_dir, uid)

def remove_dead_account(cookie_line):
    """Xóa tài khoản die khỏi file account.txt, xóa proxy mapping và profile"""
    uid = cookie_line.split("|")[0] if "|" in cookie_line else "Unknown"
    
    # 1. Xóa khỏi account.txt
    with FILE_LOCK:
        try:
            acc_file = config.COOKIE_FILE
            if os.path.exists(acc_file):
                with open(acc_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                # Lọc bỏ dòng trùng khớp
                new_lines = [l for l in lines if l.strip() != cookie_line.strip()]
                
                with open(acc_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                print(f" Đã xóa tài khoản {uid} khỏi {acc_file}")
                # print(f"UI_STATUS|{uid}|Checkpoint")
        except Exception as e:
            print(f" Lỗi khi xóa tài khoản die khỏi file: {e}")

    # 2. Xóa khỏi account_proxy.json
    if uid != "Unknown":
        mapping = load_proxy_mapping()
        if uid in mapping:
            del mapping[uid]
            save_proxy_mapping(mapping)
            print(f"Đã giải phóng proxy mapping cho UID {uid}")
            
        # 3. Xóa thư mục profile
        profile_path = get_profile_path(uid)
        if os.path.exists(profile_path):
            try:
                shutil.rmtree(profile_path, ignore_errors=True)
                print(f" Đã xóa thư mục profile của UID {uid}")
            except Exception as e:
                print(f" Lỗi khi xóa thư mục profile của UID {uid}: {e}")

