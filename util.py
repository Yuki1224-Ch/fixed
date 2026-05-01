import os
import json
import random
import string
import re
from pathlib import Path

# --- Configuration Management ---

DEFAULT_CONFIG = {
    "threads": 5,
    "timeout": 30,
    "retry_attempts": 3,
    "useCustomSolver": True,
    "headless": True,
    "debug": False,
    "rareItems": [],
    "minRobux": 0,
    "saveValidOnly": True,
    "delay_between_checks": [1, 3]
}

def get_config_path():
    return Path("config.json")

def load_config():
    """Loads configuration from config.json or creates default."""
    path = get_config_path()
    if not path.exists():
        with open(path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    except Exception as e:
        print(f"[!] Error loading config.json: {e}. Using defaults.")
        return DEFAULT_CONFIG

def get_config():
    return load_config()

def save_config(config):
    """Saves configuration to config.json."""
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=4)

# --- Proxy Parsing & Formatting ---

def parse_proxy(proxy_str):
    """
    Parses a proxy string into a standardized dictionary format.
    Supports:
      1. username:password@ip:port  <-- ADDED/ENHANCED
      2. http://username:password@ip:port
      3. username:password:ip:port
      4. ip:port
      5. http://ip:port
    
    Returns dict: {'server': 'http://ip:port', 'username': ..., 'password': ...} or None
    """
    if not proxy_str or not isinstance(proxy_str, str):
        return None
    
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None

    # Remove protocol prefix if present for easier parsing
    clean_str = proxy_str
    protocol = "http"
    if proxy_str.startswith("http://"):
        clean_str = proxy_str[7:]
        protocol = "http"
    elif proxy_str.startswith("https://"):
        clean_str = proxy_str[8:]
        protocol = "https"

    # --- FORMAT 1 & 2: username:password@ip:port ---
    # This handles both "user:pass@ip:port" and "ip:port" (if no @ found)
    if "@" in clean_str:
        try:
            auth_part, host_part = clean_str.split("@", 1)
            # Split auth into user and pass
            # Note: Password might contain colons, so we split only on the first colon for user
            if ":" in auth_part:
                user, pwd = auth_part.split(":", 1)
            else:
                user, pwd = auth_part, ""
            
            # Split host into ip and port
            if ":" in host_part:
                host, port = host_part.rsplit(":", 1)
                if port.isdigit():
                    return {
                        "server": f"{protocol}://{host}:{port}",
                        "username": user,
                        "password": pwd
                    }
        except ValueError:
            pass

    # --- FORMAT 3: username:password:ip:port (4 parts) ---
    parts = clean_str.split(":")
    if len(parts) == 4:
        user, pwd, host, port = parts
        if port.isdigit():
            return {
                "server": f"{protocol}://{host}:{port}",
                "username": user,
                "password": pwd
            }

    # --- FORMAT 4 & 5: ip:port (2 parts) ---
    if len(parts) == 2:
        host, port = parts
        if port.isdigit():
            return {
                "server": f"{protocol}://{host}:{port}"
            }

    # Fallback for weird formats
    return None

def get_proxy_url(proxy_dict):
    """Extracts the full URL string from a proxy dict for requests library."""
    if not proxy_dict:
        return None
    
    server = proxy_dict.get('server', '')
    username = proxy_dict.get('username')
    password = proxy_dict.get('password')
    
    if username and password:
        protocol, rest = server.split('://')
        return f"{protocol}://{username}:{password}@{rest}"
    
    return server

def format_proxy_for_2captcha(proxy_dict):
    """Formats proxy specifically for 2captcha API (user:pass:ip:port)."""
    if not proxy_dict:
        return ""
    
    server = proxy_dict.get('server', '')
    username = proxy_dict.get('username')
    password = proxy_dict.get('password')
    
    match = re.search(r'://([^:]+):(\d+)', server)
    if not match:
        return ""
    
    ip, port = match.groups()
    
    if username and password:
        return f"{username}:{password}:{ip}:{port}"
    else:
        return f"{ip}:{port}"

def load_proxies(filename="proxies.txt"):
    """Loads proxies from a file and parses them."""
    if not os.path.exists(filename):
        print(f"[!] {filename} not found. Running without proxies.")
        return []
    
    proxies = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parsed = parse_proxy(line)
                if parsed:
                    proxies.append(parsed)
                else:
                    print(f"[!] Invalid proxy format skipped: {line}")
    
    print(f"[+] Loaded {len(proxies)} valid proxies.")
    return proxies

# --- Account Loading ---

def load_accounts(filename="accounts.txt"):
    """Loads accounts from a file (format: user:pass)."""
    if not os.path.exists(filename):
        print(f"[!] {filename} not found.")
        return []
    
    accounts = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if ':' in line:
                    accounts.append(line)
                else:
                    print(f"[!] Invalid account format (expected user:pass): {line}")
    
    print(f"[+] Loaded {len(accounts)} accounts.")
    return accounts

# --- Helper Utilities ---

def random_string(length=10):
    """Generates a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_user_agent():
    """Returns a random realistic User-Agent."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"
    ]
    return random.choice(agents)

def delay(min_sec=1, max_sec=3):
    """Sleeps for a random duration between min and max seconds."""
    import time
    sec = random.uniform(min_sec, max_sec)
    time.sleep(sec)

if __name__ == "__main__":
    print("Testing Util Functions...")
    
    # Test Config
    cfg = get_config()
    print(f"Config loaded: Threads={cfg['threads']}, CustomSolver={cfg['useCustomSolver']}")
    
    # Test Proxy Parsing including the new format
    test_proxies = [
        "192.168.1.1:8080",
        "http://192.168.1.1:8080",
        "user:pass@192.168.1.1:8080",       # NEW FORMAT TEST
        "http://user:pass@192.168.1.1:8080", # NEW FORMAT TEST with http
        "user:pass:192.168.1.1:8080"
    ]
    
    print("\nProxy Parsing Tests:")
    for p in test_proxies:
        res = parse_proxy(p)
        print(f"Input: {p:<40} -> Parsed: {res}")
    
    print("\n✅ Util module ready.")