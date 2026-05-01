#!/usr/bin/env python3
# test_proxy_parser.py - Test proxy format parsing

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import parse_proxy, format_proxy_for_2captcha

def test_proxy_formats():
    """Test all supported proxy formats"""
    
    test_cases = [
        # Format 1: Simple host:port
        ("192.168.1.1:8080", "http://192.168.1.1:8080", "192.168.1.1:8080"),
        
        # Format 2: With protocol
        ("http://192.168.1.1:8080", "http://192.168.1.1:8080", "192.168.1.1:8080"),
        ("https://192.168.1.1:8080", "https://192.168.1.1:8080", "192.168.1.1:8080"),
        
        # Format 3: With authentication (username:password@host:port)
        ("user:pass@192.168.1.1:8080", "http://user:pass@192.168.1.1:8080", "user:pass:192.168.1.1:8080"),
        
        # Format 4: With protocol and authentication
        ("http://user:pass@192.168.1.1:8080", "http://user:pass@192.168.1.1:8080", "user:pass:192.168.1.1:8080"),
        ("https://admin:secret123@proxy.example.com:3128", "https://admin:secret123@proxy.example.com:3128", "admin:secret123:proxy.example.com:3128"),
        
        # Format 5: Colon-separated (username:password:host:port) - MOST COMMON
        ("user:pass:192.168.1.1:8080", "http://user:pass@192.168.1.1:8080", "user:pass:192.168.1.1:8080"),
    ]
    
    print("=" * 80)
    print("PROXY FORMAT PARSER TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, (input_str, expected_url, expected_2captcha) in enumerate(test_cases, 1):
        result = parse_proxy(input_str)
        
        if result is None:
            print(f"\n❌ Test {i} FAILED: {input_str}")
            print(f"   Expected URL: {expected_url}")
            print(f"   Got: None")
            failed += 1
            continue
        
        actual_url = result.get('url', '')
        actual_2captcha = format_proxy_for_2captcha(result)
        
        url_match = actual_url == expected_url
        captcha_match = actual_2captcha == expected_2captcha
        
        if url_match and captcha_match:
            print(f"\n✅ Test {i} PASSED: {input_str}")
            print(f"   URL: {actual_url}")
            print(f"   2Captcha: {actual_2captcha}")
            passed += 1
        else:
            print(f"\n❌ Test {i} FAILED: {input_str}")
            if not url_match:
                print(f"   Expected URL: {expected_url}")
                print(f"   Got URL: {actual_url}")
            if not captcha_match:
                print(f"   Expected 2Captcha: {expected_2captcha}")
                print(f"   Got 2Captcha: {actual_2captcha}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_proxy_formats()
    sys.exit(0 if success else 1)
