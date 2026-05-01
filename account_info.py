# account_info.py - FIXED - ADDED CLASS
from session_noproxy import Session
from util import get_config
import requests

config = get_config()
rare_items = config.get("rareItems", [])

def make_str(l):
    if l:
        s = ", ".join(l)
        return s[:1021] + "..." if len(s) > 1024 else s
    return "None"

def format_number(num):
    try: return "{:,}".format(int(num))
    except: return str(num)

def retry(func):
    def wrapper(*a, **k):
        for _ in range(3):
            try: return func(*a, **k)
            except Exception as e:
                if hasattr(e, 'response') and e.response.status_code == 401:
                    return "Unauthorized"
        raise
    return wrapper

@retry
def get_rap(session: Session, UserID: int) -> str:
    TotalValue = 0
    Cursor = ""
    while True:
        resp = session.get(f"https://inventory.roblox.com/v1/users/{UserID}/assets/collectibles?limit=100&cursor={Cursor}")
        if resp.status_code == 401: return "Unauthorized"
        data = resp.json()
        Cursor = data.get("nextPageCursor")
        for item in data.get("data", []):
            try: TotalValue += int(item["recentAveragePrice"])
            except: pass
        if not Cursor: break
    return format_number(TotalValue)

@retry
def get_robux(session: Session, user_id):
    resp = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency")
    return resp.json().get("robux", 0) if resp.status_code == 200 else 0

@retry
def get_premium(session: Session, user_id):
    resp = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}")
    return resp.status_code == 200

@retry
def get_payment_info(session: Session):
    resp = session.get("https://billing.roblox.com/v1/credit")
    return resp.status_code == 200

@retry
def get_creation_date(session: Session, user_id):
    resp = session.get(f"https://users.roblox.com/v1/users/{user_id}")
    if resp.status_code != 200: return "_unknown"
    return resp.json().get("created", "_unknown")[:10]

@retry
def get_items(session: Session, user_id):
    resp = session.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset")
    items = resp.json().get("data", [])
    rare = [i["assetId"] for i in items if i["assetId"] in rare_items]
    return {"rare_items": make_str(rare), "total_items": len(items)}

@retry
def get_thumbnail(session: Session, user_id):
    resp = session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png")
    return resp.json()["data"][0]["imageUrl"] if resp.json()["data"] else "_unknown"

# Alias for backwards compatibility
has_payment_info = get_payment_info

# ADDED CLASS
class AccountInfo:
    @staticmethod
    def get_account_info(session: Session, user_id):
        return {
            "Robux": get_robux(session, user_id),
            "Premium": get_premium(session, user_id),
            "Payment Info": get_payment_info(session),
            "RAP": get_rap(session, user_id),
            "Creation Date": get_creation_date(session, user_id),
            "Rare Items": get_items(session, user_id)["rare_items"],
            "Total Items": get_items(session, user_id)["total_items"],
            "Thumbnail": get_thumbnail(session, user_id)
        }