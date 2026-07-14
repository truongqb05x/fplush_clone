import requests

ACCESS_TOKEN = "6fb5ebe26f9b04a484b5d8ad84dc2a01"
NICK_CHAY = "100000160204164"

def fetch_ttc_jobs():
    """
    Fetches jobs from TuongTacCheo API.
    Returns a list of job dictionaries, e.g., [{"idpost": "...", "idfb": "...", "link": "..."}, ...]
    """
    session = requests.Session()

    try:
        # Login
        login = session.post(
            "https://tuongtaccheo.com/logintoken.php",
            data={"access_token": ACCESS_TOKEN},
            timeout=10
        )
        # print("TTC Login Response:", login.text)

        # Lấy job
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://tuongtaccheo.com/kiemtien/likepostvipre/",
            "X-Requested-With": "XMLHttpRequest"
        }

        response = session.get(
            "https://tuongtaccheo.com/kiemtien/likepostvipre/getpost.php",
            params={
                "nickchay": NICK_CHAY
            },
            headers=headers,
            timeout=10
        )

        jobs = response.json()
        print(f" Tìm thấy {len(jobs)} nhiệm vụ TTC")
        return jobs
    except Exception as e:
        print(f" Lỗi khi fetch job TTC: {e}")
        return []

if __name__ == "__main__":
    jobs = fetch_ttc_jobs()
    for i, job in enumerate(jobs, start=1):
        print(f"Job {i}")
        print("ID TTC :", job.get("idpost"))
        print("ID FB  :", job.get("idfb"))
        print("Link   :", job.get("link"))
        print("-" * 50)

