# -*- coding: utf-8 -*-
"""
veri_account_facebook - Package initialization
"""

__version__ = "2.0"
__description__ = "Facebook Account Verifier - Refactored"

# Import các module chính
from helpers import (
    is_checkpoint, is_facebook_home, is_http_pool_timeout,
    is_crash_error, safe_url, cleanup_seleniumwire, kill_all_chrome,
    periodic_seleniumwire_cleanup, normalize_url, wait_for_page_load
)

from waiter import (
    safe_wait_until, wait_for_element_with_retry,
    wait_for_clickable_with_retry, wait_for_redirect
)

from interface_handlers import (
    detect_interface_simple, add_email_with_detection,
    enter_otp_with_detection, add_email_old_interface,
    add_email_new_interface, enter_otp_old_interface,
    enter_otp_new_interface
)

from proxy_manager import (
    reset_proxy_checkpoint_count, mark_proxy_checkpoint,
    add_proxy_to_blacklist
)

__all__ = [
    # helpers
    'is_checkpoint', 'is_facebook_home', 'is_http_pool_timeout', 'is_crash_error',
    'safe_url', 'cleanup_seleniumwire', 'kill_all_chrome', 'periodic_seleniumwire_cleanup',
    'normalize_url', 'wait_for_page_load',
    
    # waiter
    'safe_wait_until', 'wait_for_element_with_retry', 'wait_for_clickable_with_retry',
    'wait_for_redirect',
    
    # interface_handlers
    'detect_interface_simple', 'add_email_with_detection', 'enter_otp_with_detection',
    'add_email_old_interface', 'add_email_new_interface', 'enter_otp_old_interface',
    'enter_otp_new_interface',
    
    # proxy_manager
    'reset_proxy_checkpoint_count', 'mark_proxy_checkpoint', 'add_proxy_to_blacklist',
]
