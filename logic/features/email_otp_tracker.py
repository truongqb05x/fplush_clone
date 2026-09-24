# -*- coding: utf-8 -*-
"""
Module: Email OTP Timeout Tracking
Chức năng: Theo dõi khi email gây lỗi OTP_TIMEOUT_90S
Nếu 2+ tài khoản bị timeout với cùng 1 email thì đánh dấu mail đó đã dùng
"""

import json
import os


class EmailOTPTimeoutTracker:
    """Theo dõi lỗi OTP timeout cho từng email"""
    
    TRACKER_FILE = "resources/email_timeout_tracker.json"
    TIMEOUT_LIMIT = 2  # nếu 2+ tài khoản timeout, đánh dấu mail đã dùng
    
    def __init__(self):
        """Khởi tạo và load file tracker"""
        self.tracker_data = self._load_tracker()
    
    def _load_tracker(self):
        """Load dữ liệu tracker từ file"""
        if os.path.exists(self.TRACKER_FILE):
            try:
                with open(self.TRACKER_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_tracker(self):
        """Lưu dữ liệu tracker vào file"""
        os.makedirs(os.path.dirname(self.TRACKER_FILE), exist_ok=True)
        with open(self.TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tracker_data, f, indent=2, ensure_ascii=False)
    
    def track_otp_timeout(self, email, uid):
        """
        Ghi lại tài khoản bị OTP timeout với email này
        Args:
            email: Email address (full format hoặc chỉ email part)
            uid: UID gặp lỗi OTP_TIMEOUT_90S
        
        Returns:
            Bool: True nếu vượt quá limit (nên bỏ mail)
        """
        email_only = email.split('|')[0] if '|' in email else email
        
        if email_only not in self.tracker_data:
            self.tracker_data[email_only] = {
                "timeout_accounts": [],
                "should_discard": False
            }
        
        # Ghi lại tài khoản nếu chưa có
        if uid not in self.tracker_data[email_only]["timeout_accounts"]:
            self.tracker_data[email_only]["timeout_accounts"].append(uid)
            
            timeout_count = len(self.tracker_data[email_only]["timeout_accounts"])
            print(f" EMAIL {email_only}: OTP TIMEOUT → {timeout_count}/{self.TIMEOUT_LIMIT} tài khoản")
            
            # Nếu đủ 2 tài khoản bị timeout, đánh dấu bỏ mail này
            if timeout_count >= self.TIMEOUT_LIMIT:
                self.tracker_data[email_only]["should_discard"] = True
                self._save_tracker()
                
                timeout_accounts_str = ", ".join(self.tracker_data[email_only]["timeout_accounts"])
                print(f" BỎ ĐI EMAIL {email_only}")
                print(f"   Lý do: OTP TIMEOUT cho {self.TIMEOUT_LIMIT} tài khoản")
                print(f"   UIDs: {timeout_accounts_str}")
                
                return True  # Nên bỏ mail này
        
        self._save_tracker()
        return False  # Vẫn dùng được
    
    def should_discard(self, email):
        """Kiểm tra email có nên bỏ đi không"""
        email_only = email.split('|')[0] if '|' in email else email
        return self.tracker_data.get(email_only, {}).get("should_discard", False)


# Global instance
email_otp_timeout_tracker = EmailOTPTimeoutTracker()
