import threading
import time
from custom_solver import CustomCaptchaSolver

# Global solver instances per-thread to avoid greenlet conflicts
_solver_instances = {}
_solver_lock = threading.Lock()

def get_solver_instance():
    """Get or create a solver instance for the current thread."""
    thread_id = threading.get_ident()
    
    with _solver_lock:
        if thread_id not in _solver_instances:
            _solver_instances[thread_id] = CustomCaptchaSolver(debug=True)
        return _solver_instances[thread_id]

def cleanup_thread_solver():
    """Cleanup solver for current thread."""
    thread_id = threading.get_ident()
    with _solver_lock:
        if thread_id in _solver_instances:
            _solver_instances[thread_id].close()
            del _solver_instances[thread_id]

def get_token(session, metadata=None):
    """
    Legacy wrapper for backwards compatibility with roblox.py
    Returns token string or None
    """
    result_container = {"success": False, "token": None}
    event = threading.Event()

    def run_solver_task():
        nonlocal result_container
        try:
            solver = get_solver_instance()
            url = getattr(session, 'url', 'https://www.roblox.com/login')
            blob = getattr(session, 'captcha_blob', None)
            site_key = getattr(session, 'captcha_site_key', "476068BF-9607-4799-B53D-966BE98E2B81")
            username = getattr(session, 'username', None)
            password = getattr(session, 'password', None)
            proxy = getattr(session, 'proxy_dict', None)

            print(f"[*] 🧠 Solving Captcha...")
            res = solver.solve_with_token(site_key, url, blob, username=username, password=password, proxy=proxy)

            if res.get('success'):
                result_container['success'] = True
                result_container['token'] = res.get('token')
            else:
                print("[-] ❌ Solver returned failure")
                
        except Exception as e:
            print(f"[-] 💥 Solver Thread Crash: {e}")
            import traceback
            traceback.print_exc()
        finally:
            event.set()

    t = threading.Thread(target=run_solver_task)
    t.daemon = True
    t.start()
    
    completed = event.wait(timeout=60)
    
    if not completed:
        print("[-] ⏱️ Captcha Solver Timed Out (60s)")
        return None
        
    return result_container['token'] if result_container['success'] else None

def solve_captcha_wrapper(session):
    """
    Runs the captcha solver in a background thread to prevent freezing.
    Returns True if solved, False otherwise.
    """
    result_container = {"success": False, "token": None}
    event = threading.Event()

    def run_solver_task():
        nonlocal result_container
        try:
            solver = get_solver_instance()
            url = getattr(session, 'url', 'https://www.roblox.com/login')
            blob = getattr(session, 'captcha_blob', None)
            site_key = getattr(session, 'captcha_site_key', "476068BF-9607-4799-B53D-966BE98E2B81")
            username = getattr(session, 'username', 'Unknown')
            password = getattr(session, 'password', None)
            proxy = getattr(session, 'proxy_dict', None)

            print(f"[*] 🧠 Solving Captcha for {username}...")
            res = solver.solve_with_token(site_key, url, blob, username=username, password=password, proxy=proxy)

            if res.get('success'):
                result_container['success'] = True
                result_container['token'] = res.get('token')
                
                if hasattr(session, 'set_captcha_token'):
                    session.set_captcha_token(result_container['token'])
                    token_preview = result_container['token'][:20] if result_container['token'] and len(result_container['token']) > 20 else 'N/A'
                    print(f"[+] ✅ Captcha Solved! Token: {token_preview}...")
                else:
                    print("[!] Session missing set_captcha_token method")
            else:
                print("[-] ❌ Solver returned failure")
                
        except Exception as e:
            print(f"[-] 💥 Solver Thread Crash: {e}")
        finally:
            event.set()

    t = threading.Thread(target=run_solver_task, daemon=True)
    t.start()
    
    completed = event.wait(timeout=60)
    
    if not completed:
        print("[-] ⏱️ Captcha Solver Timed Out (60s)")
        return False
        
    return result_container['success']

def cleanup_solver():
    """Call this at the end of your program to close all browser instances."""
    global _solver_instances
    with _solver_lock:
        for thread_id, solver in list(_solver_instances.items()):
            try:
                print(f"[*] Closing solver browser for thread {thread_id}...")
                solver.close()
            except Exception as e:
                print(f"[!] Error closing solver: {e}")
        _solver_instances.clear()