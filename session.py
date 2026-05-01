import requests
import json
import time
import random
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Import utilities
from util import get_proxy_url, random_user_agent, parse_proxy

class RobloxSession:
    def __init__(self, proxy=None):
        self.session = requests.Session()
        self.proxy_dict = None
        self.proxy_url = None
        
        # Setup Proxy
        if proxy:
            if isinstance(proxy, str):
                proxy = parse_proxy(proxy)
            
            if isinstance(proxy, dict):
                self.proxy_dict = proxy
                self.proxy_url = get_proxy_url(proxy)
                # Configure requests session
                self.session.proxies = {
                    "http": self.proxy_url,
                    "https": self.proxy_url
                }
        
        # Setup Headers
        self.session.headers.update({
            "User-Agent": random_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/"
        })
        
        self.csrf_token = None
        self.auth_ticket = None
        self.user_id = None
        self.username = None
        self.password = None
        self.is_logged_in = False
        self.needs_captcha = False
        self.captcha_blob = None
        self.captcha_site_key = "476068BF-9607-4799-B53D-966BE98E2B81" # Standard Roblox Arkose Key

    def _get_csrf(self) -> bool:
        """Fetches a fresh CSRF token from Roblox."""
        try:
            resp = self.session.get("https://auth.roblox.com/v2/captcha-metadata", timeout=10)
            token = resp.headers.get('x-csrf-token')
            if token and len(token) > 10:
                self.csrf_token = token
                return True

            resp = self.session.get("https://www.roblox.com/login", timeout=10)
            token = resp.headers.get('x-csrf-token')
            if token and len(token) > 10:
                self.csrf_token = token
                return True

            resp = self.session.post("https://auth.roblox.com/v2/login", json={}, timeout=10)
            token = resp.headers.get('x-csrf-token')
            if token and len(token) > 10:
                self.csrf_token = token
                return True

            return False
        except Exception:
            return False

    def login_status(self, username, password) -> Dict[str, Any]:
        """Attempts login and returns a detailed status dictionary."""
        self.username = username
        self.is_logged_in = False
        self.needs_captcha = False
        self.captcha_blob = None

        if not self._get_csrf():
            time.sleep(1)
            if not self._get_csrf():
                return {'status': 'error', 'message': 'Failed to retrieve CSRF token', 'retry': True}

        url = "https://auth.roblox.com/v2/login"
        payload = {
            "ctype": "username",
            "cvalue": username,
            "password": password
        }

        headers = {
            "Content-Type": "application/json",
            "x-csrf-token": self.csrf_token or "",
            "Referer": "https://www.roblox.com/login"
        }

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=15)
            # Get fresh CSRF from response headers (Roblox rotates them)
            new_csrf = resp.headers.get('x-csrf-token')
            if new_csrf and len(new_csrf) > 10:
                self.csrf_token = new_csrf
            
            data = resp.json() if resp.text else {}

            if resp.status_code == 200 and data.get("user"):
                self.is_logged_in = True
                self.username = data["user"].get("userName", username)
                self.user_id = data["user"].get("id")
                if ".ROBLOSECURITY" in resp.cookies:
                    self.session.cookies.set(".ROBLOSECURITY", resp.cookies[".ROBLOSECURITY"])
                return {'status': 'success', 'message': 'Logged in successfully', 'csrf': self.csrf_token}

            errors = data.get("errors", [])
            if not errors:
                return {'status': 'error', 'message': 'Unknown response format', 'retry': True}

            for err in errors:
                code = err.get("code")
                msg = str(err.get("message", ""))
                lower_msg = msg.lower()

                # Check for captcha requirement (including challenge required)
                if code == 10 or code == "CaptchaRequired" or "captcha" in lower_msg or "challenge is required" in lower_msg:
                    self.needs_captcha = True
                    self.captcha_blob = err.get("context", {}).get("captchaBlob") or msg
                    return {'status': 'captcha', 'message': 'Captcha required', 'csrf': resp.headers.get('x-csrf-token', '')}

                if code == 4 or code == "InvalidCredentials" or ("invalid" in lower_msg and "credential" in lower_msg):
                    return {'status': 'invalid', 'message': 'Invalid username or password'}

                if code in [13, 8] or "banned" in lower_msg or "locked" in lower_msg:
                    return {'status': 'banned', 'message': f'Account status: {msg}'}

                if code == 5 or "rate" in lower_msg:
                    return {'status': 'error', 'message': 'Rate limited', 'retry': True}

            full_text = str(errors).lower()
            if "incorrect" in full_text or "wrong" in full_text:
                return {'status': 'invalid', 'message': 'Credentials incorrect'}
            
            # If we get a challenge required error, treat it as captcha
            if "challenge is required" in full_text:
                self.needs_captcha = True
                return {'status': 'captcha', 'message': 'Challenge required', 'csrf': resp.headers.get('x-csrf-token', '')}

            return {'status': 'error', 'message': f'Unexpected error: {errors}', 'retry': True}

        except Exception as e:
            return {'status': 'error', 'message': f'Request failed: {str(e)}', 'retry': True}

    def login(self, username, password) -> Dict[str, Any]:
        """Attempts to log in and returns a detailed status dictionary."""
        self.password = password
        return self.login_status(username, password)

    def solve_captcha_and_retry(self, username: str, password: str, csrf_token: str, solver_func) -> Dict[str, Any]:
        """
        Handles the full flow: Solve Captcha -> Submit Token -> Verify Login
        Enhanced to properly handle VISUAL_SUCCESS and NO_CHALLENGE tokens.
        """
        self.username = username
        self.password = password

        if not self.needs_captcha:
            return {'status': 'error', 'message': 'No captcha challenge present'}

        print(f"   ⚡ Solving Captcha for {username}...")
        result = solver_func(username, password, csrf_token)

        if not result or not result.get('success'):
            print(f"   ❌ Solver failed for {username}")
            return {'status': 'captcha_failed', 'message': 'Solver failed to get token'}

        token = result.get('token')
        
        # Handle special tokens from visual solver
        if token == 'NO_CHALLENGE':
            print(f"   ✅ No captcha required, retrying login...")
            # Just retry login without captcha token
            return self._retry_login(username, password, csrf_token, captcha_token=None)
        
        elif token == 'VISUAL_SUCCESS':
            print(f"   ✅ Captcha visually solved! Retrying login...")
            # The browser session already solved it, just need to verify
            return self._retry_login(username, password, csrf_token, captcha_token='VISUAL_SUCCESS')
        
        elif token and len(token) > 20:
            print(f"   ✅ Captcha Solved! Token: {token[:20]}...")
            self.session.headers['x-captcha-token'] = token
            return self._retry_login(username, password, csrf_token, captcha_token=token)
        
        else:
            print(f"   ❌ Invalid token received")
            return {'status': 'captcha_failed', 'message': 'Solver returned invalid token'}

    def _retry_login(self, username: str, password: str, csrf_token: str, captcha_token=None) -> Dict[str, Any]:
        """Retry login after captcha is solved."""
        self.needs_captcha = False

        url = "https://auth.roblox.com/v2/login"
        payload = {
            "ctype": "username",
            "cvalue": username,
            "password": password,
        }
        
        # Only add captchaToken if we have a real token (not VISUAL_SUCCESS)
        if captcha_token and captcha_token != 'VISUAL_SUCCESS':
            payload["captchaToken"] = captcha_token
            
        headers = {
            "Content-Type": "application/json",
            "x-csrf-token": csrf_token,
            "Referer": "https://www.roblox.com/login"
        }

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=15)
            data = resp.json() if resp.text else {}

            if resp.status_code == 200 and data.get('user'):
                self.is_logged_in = True
                self.user_id = data['user'].get('id')
                if '.ROBLOSECURITY' in resp.cookies:
                    self.session.cookies.set('.ROBLOSECURITY', resp.cookies['.ROBLOSECURITY'])
                return {'status': 'success', 'message': 'Logged in after captcha'}

            errors = data.get('errors', [])
            for err in errors:
                code = err.get('code')
                msg = str(err.get('message', '')).lower()

                if code == 4 or 'invalid' in msg:
                    return {'status': 'invalid', 'message': 'Invalid credentials (post-captcha)'}
                if 'captcha' in msg:
                    return {'status': 'captcha', 'message': 'Captcha failed/invalid token', 'retry_captcha': True}

            return {'status': 'error', 'message': 'Login retry failed', 'retry': True}
        except Exception as e:
            return {'status': 'error', 'message': f'Retry request failed: {str(e)}'}

    def get_account_info(self):
        """Fetches Robux and other details for the logged-in user."""
        if not self.is_logged_in or not self.user_id:
            return {"error": "Not logged in", "robux": 0, "premium": False}
        
        try:
            # 1. Get Robux Balance
            robux_resp = self.session.get(
                f"https://economy.roblox.com/v1/users/{self.user_id}/currency",
                timeout=15
            )
            if robux_resp.status_code == 200:
                robux_data = robux_resp.json()
                robux = robux_data.get("robux", 0)
            else:
                robux = 0
            
            # 2. Get Premium Status
            is_premium = False
            try:
                premium_resp = self.session.get(
                    f"https://premiumfeatures.roblox.com/v1/users/{self.user_id}/validate-membership",
                    timeout=15
                )
                if premium_resp.status_code == 200:
                    is_premium = premium_resp.json().get("isMember", False)
            except:
                pass
            
            # 3. Get Additional Info (optional)
            try:
                info_resp = self.session.get(
                    f"https://users.roblox.com/v1/users/{self.user_id}",
                    timeout=15
                )
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    display_name = info_data.get("displayName", self.username)
                else:
                    display_name = self.username
            except:
                display_name = self.username
            
            return {
                "username": self.username,
                "display_name": display_name,
                "user_id": self.user_id,
                "robux": robux,
                "premium": is_premium
            }
            
        except Exception as e:
            return {"error": str(e), "robux": 0, "premium": False}

    def set_captcha_token(self, token):
        """Helper to manually set captcha token if solved externally."""
        self.session.headers["x-captcha-token"] = token
        self.needs_captcha = False

# Alias for backwards compatibility with roblox.py
Session = RobloxSession