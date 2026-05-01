# thread_lock.py
import threading
import signal
import sys

class ThreadLock:
    def __init__(self):
        self.lock = threading.RLock()

    def get_lock(self):
        return self.lock

# Global lock
lock = ThreadLock()

# === GRACEFUL SHUTDOWN ===
def _signal_handler(signum, frame):
    print("\n[!] Ctrl+C detected. Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)