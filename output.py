# output.py
from datetime import datetime
from colorama import init, Fore
from threading import Lock
init()
lock = Lock()

class Output:
    def __init__(self, level):
        self.level = level
        self.color_map = {
            "INFO": (Fore.LIGHTCYAN_EX, "^"),
            "CAPTCHA": (Fore.LIGHTBLUE_EX, "robot"),
            "ERROR": (Fore.LIGHTRED_EX, "cross"),
            "SUCCESS": (Fore.LIGHTGREEN_EX, "check"),
            "WARNING": (Fore.YELLOW, "warning"),
            "MAIL": (Fore.RESET, "email"),
            "HUMANIZE": (Fore.YELLOW, "boy"),
            "GROUP": (Fore.MAGENTA, "group"),
            "FOLLOW": (Fore.YELLOW, "boy")
        }

    def log(self, *args):
        color, text = self.color_map.get(self.level, (Fore.WHITE, "info"))
        time_now = datetime.now().strftime("%H:%M:%S")
        base = f"{Fore.LIGHTBLACK_EX}[{time_now}]{Fore.RESET} ({color}{text.upper()}{Fore.RESET})"
        for arg in args:
            base += f"{color} {arg}"
        with lock:
            print(base)