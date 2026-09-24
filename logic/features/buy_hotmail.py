# -*- coding: utf-8 -*-
import time
import requests
import json

# =========================
# CONFIG
# =========================

# --- Dongvanfb ---
HOTMAIL_API = "https://api.dongvanfb.net/user/buy"
DONGVAN_API_KEY = "FQSXuwGkDa24bwhFsZF7LWcl1"



# --- EmailSieure ---
EMAILSIEURE_BUY_API = "https://emailsieure.com/api/v1/orders/buy"
EMAILSIEURE_API_KEY = "msk_x0PTrZ-krYISKk2yL0ETJcyE41Acj-iD1wYC1IkMYuU"
EMAILSIEURE_PRODUCT_ID = 20
EMAILSIEURE_QUANTITY = 1


# --- Mailsngon ---
MAILSNGON_API = "https://mailsngon.com/api/v2/orders"
MAILSNGON_TOKEN = "lhix4gjx6ieiwq45hlm29xoei8gjkdvs3ar8rfcqum"
MAILSNGON_TYPE_ID = 1051
MAILSNGON_QUANTITY = 1

# --- ShopMailMMO ---
SHOPMAILMMO_BASE_URL = "https://shopmailmmo.store"
SHOPMAILMMO_API_KEY = "Gg3IM912Cf2ykk2R4Ek5UEi7rRXvQBsn"
SHOPMAILMMO_SERVICE = "hotmail_new_1h_3h"


# =========================
# BUY VIA MAILSNGON (1 LẦN)
# =========================
def buy_hotmail_mailsngon_once():
    try:
        headers = {
            "x-api-key": MAILSNGON_TOKEN,
            "Accept": "application/json"
        }
        params = {
            "mailTypeId": MAILSNGON_TYPE_ID,
            "quantity": MAILSNGON_QUANTITY
        }

        r = requests.get(MAILSNGON_API, headers=headers, params=params, timeout=25)
        
        try:
            data = r.json()
        except Exception:
            print(f"❌ Mailsngon: Phản hồi không phải JSON (Status: {r.status_code})")
            return None

        # Format thực tế: {"status": 200, "data": {"result": "[\"mail|pass|...\"]"}}
        if data.get("status") == 200 or data.get("is_success"):
            # Lấy data object (hoặc list tùy theo user prompt vs thực tế)
            d = data.get("data", [])
            lst = []
            
            if isinstance(d, dict) and "result" in d:
                # Actual Mailsngon v2 format
                try:
                    lst = json.loads(d["result"])
                except Exception:
                    pass
            elif isinstance(d, list):
                # Format provided in user prompt
                lst = d
                
            if lst:
                mail_line = lst[0]
                print("📧 Mailsngon: Mua mail thành công")
                return mail_line
        
        print(f"❌ Mailsngon: {data.get('message', 'Fail / hết hàng')}")
        return None

    except Exception as e:
        print("⚠️ Mailsngon error:", e)
        return None


# =========================
# BUY VIA DONGVANFB (1 LẦN)
# =========================
def buy_hotmail_dongvan_once():
    try:
        params = {
            "apikey": DONGVAN_API_KEY,
            "account_type": 1,
            "quality": 1,
            "type": "full"
        }

        res = requests.get(HOTMAIL_API, params=params, timeout=20)
        data = res.json()

        if data.get("status") and data.get("error_code") == 200:
            mail_line = data["data"]["list_data"][0]
            print("📧 DongvanFB: Mua mail thành công")
            return mail_line

        print("❌ DongvanFB: Không có mail")
        return None

    except Exception as e:
        print("⚠️ DongvanFB error:", e)
        return None





# =========================
# BUY VIA SHOPMAILMMO (1 LẦN)
# =========================
def buy_hotmail_shopmailmmo_once(service: str = None) -> str | None:
    """Mua 1 mail từ shopmailmmo.store. Trả về chuỗi mail data hoặc None."""
    try:
        svc = service or SHOPMAILMMO_SERVICE
        url = f"{SHOPMAILMMO_BASE_URL}/v1/orders"
        headers = {"api_key": SHOPMAILMMO_API_KEY, "Content-Type": "application/json"}
        params = {"service": svc}

        res = requests.post(url, headers=headers, params=params, timeout=30)
        data = res.json()

        if data.get("status") == "fail" or res.status_code != 200:
            print(f"❌ ShopMailMMO: {data.get('error', 'Unknown error')}")
            return None

        mail = data.get("mail")
        if mail:
            print(f"📧 ShopMailMMO ({svc}): Mua mail thành công → {mail.split('|')[0]}")
            return mail

        print("❌ ShopMailMMO: Response không có trường mail")
        return None

    except Exception as e:
        print("⚠️ ShopMailMMO error:", e)
        return None


# =========================
# BUY VIA EMAILSIEURE (1 LẦN)
# =========================
def buy_hotmail_emailsieure_once(product_id=None):
    try:
        p_id = product_id if product_id is not None else EMAILSIEURE_PRODUCT_ID
        params = {
            "productId": p_id,
            "quantity": EMAILSIEURE_QUANTITY,
            "apikey": EMAILSIEURE_API_KEY
        }

        r = requests.get(EMAILSIEURE_BUY_API, params=params, timeout=25)
        try:
            data = r.json()
        except Exception:
            print(f"❌ EmailSieure (ID {p_id}): Phản hồi không phải JSON (Status: {r.status_code})")
            return None

        if data.get("success") is True:
            lst = data.get("data", {}).get("accountData", [])
            if lst:
                mail_line = lst[0]
                print(f"📧 EmailSieure (ID {p_id}): Mua mail thành công")
                return mail_line
        
        print(f"❌ EmailSieure (ID {p_id}): Fail / hết hàng")
        return None

    except Exception as e:
        print("⚠️ EmailSieure error:", e)
        return None


# =========================
# MAIN LOOP (ƯU TIÊN MAILSNGON → EMAILSIEURE → DONGVAN → SHOPMAILMMO)
# =========================
def buy_hotmail_loop():
    """
    Ưu tiên:
        1️⃣ Mailsngon      (ID 1051)
        2️⃣ DongvanFB
        3️⃣ EmailSieure    (ID 1)
        4️⃣ EmailSieure    (ID 20)
        5️⃣ ShopMailMMO    (hotmail_new_1h_3h)
    Lặp vô hạn cho đến khi mua được mail
    """
    while True:
        print("🔁 Thử mua mail từ Mailsngon (ID 1051)...")
        mail = buy_hotmail_mailsngon_once()
        if mail:
            return mail

        print("🔁 Mailsngon FAIL → thử DongvanFB...")
        mail = buy_hotmail_dongvan_once()
        if mail:
            return mail

        print("🔁 DongvanFB FAIL → thử EmailSieure (ID 1)...")
        mail = buy_hotmail_emailsieure_once(product_id=1)
        if mail:
            return mail

        print("🔁 EmailSieure ID 1 FAIL → thử EmailSieure (ID 20)...")
        mail = buy_hotmail_emailsieure_once(product_id=20)
        if mail:
            return mail

        print("🔁 EmailSieure ID 20 FAIL → thử ShopMailMMO...")
        mail = buy_hotmail_shopmailmmo_once()
        if mail:
            return mail

        print("⏳ Tất cả nguồn đều FAIL → đợi 1s rồi thử lại...\n")
        time.sleep(1)
