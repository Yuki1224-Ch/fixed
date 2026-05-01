# session_noproxy.py
from curl_cffi import requests

class Session(requests.Session):
    def __init__(self):
        super().__init__(impersonate="chrome124")