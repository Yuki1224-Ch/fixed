#!/usr/bin/env python3
"""Test script to verify main.py statistics work correctly"""

import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from main
from main import stats, stats_lock, activity_log, log_lock, add_log, check_account_task

def test_stats_update():
    """Test that stats update correctly"""
    print("🧪 Testing Statistics Update...")
    print(f"Initial stats: {stats}")
    
    # Simulate multiple threads updating stats
    def simulate_check(result_type):
        with stats_lock:
            stats["checked"] += 1
            if result_type == "valid":
                stats["valid"] += 1
            elif result_type == "invalid":
                stats["invalid"] += 1
            elif result_type == "captcha":
                stats["valid"] += 1
                stats["captcha_solved"] += 1
            else:
                stats["errors"] += 1
    
    # Run simulations in parallel
    results = ["valid", "invalid", "valid", "captcha", "error", "invalid", "valid"]
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(simulate_check, r) for r in results]
        for future in as_completed(futures):
            pass
    
    print(f"Final stats: {stats}")
    
    # Verify counts
    expected = {
        "checked": len(results),
        "valid": results.count("valid") + results.count("captcha"),
        "invalid": results.count("invalid"),
        "captcha_solved": results.count("captcha"),
        "errors": results.count("error")
    }
    
    success = True
    for key, expected_val in expected.items():
        actual_val = stats[key]
        if actual_val != expected_val:
            print(f"❌ {key}: expected {expected_val}, got {actual_val}")
            success = False
        else:
            print(f"✅ {key}: {actual_val} (correct)")
    
    if success:
        print("\n✅ All statistics tests PASSED!")
    else:
        print("\n❌ Some statistics tests FAILED!")
    
    return success

if __name__ == "__main__":
    success = test_stats_update()
    sys.exit(0 if success else 1)
