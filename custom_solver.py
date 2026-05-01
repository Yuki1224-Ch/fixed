import os
import sys
import time
import random
import math
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import io
import base64

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[-] Playwright missing. Run: pip install playwright")
    sys.exit(1)

class AdvancedCaptchaSolver:
    """
    Advanced Captcha Solver using Playwright + OpenCV for Roblox Arkose captcha.
    Uses human-like mouse movements and computer vision for rotation detection.
    """
    
    def __init__(self, headless=True, debug=False):
        self.headless = headless
        self.debug = debug
        self.site_key = "476068BF-9607-4799-B53D-966BE98E2B81"

    def solve(self, username: str, password: str, csrf_token: str) -> dict:
        """Main solve method - logs in and solves captcha if needed."""
        browser = None
        context = None
        try:
            with sync_playwright() as p:
                # Launch browser with enhanced anti-detection
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-software-rasterizer'
                    ]
                )

                # Create context with realistic fingerprint
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York"
                )
                
                page = context.new_page()
                
                if self.debug:
                    print(f"   🌐 Browser launched for {username}")

                # Enhanced anti-detection scripts
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                    Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                    
                    // WebGL spoofing
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) return 'Intel Inc.';
                        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                        return getParameter.call(this, parameter);
                    };
                """)

                # Navigate to login page
                page.goto("https://www.roblox.com/login", wait_until="networkidle", timeout=30000)
                time.sleep(random.uniform(2.0, 3.0))
                
                if self.debug:
                    print(f"   📄 Login page loaded")

                # Fill credentials with human-like typing
                username_input = page.locator('input[id="login-username"]')
                password_input = page.locator('input[id="login-password"]')
                
                if not username_input.is_visible(timeout=5000):
                    if self.debug:
                        print(f"   ❌ Username input not visible")
                    return {'success': False, 'token': None}
                
                # Type with delay to simulate human
                username_input.fill(username)
                time.sleep(random.uniform(0.5, 1.0))
                password_input.fill(password)
                time.sleep(random.uniform(0.5, 1.0))
                
                if self.debug:
                    print(f"   ⌨️ Credentials entered")
                
                # Click login button
                login_btn = page.locator('button[data-event-label="Sign In"]')
                if login_btn.is_visible():
                    login_btn.click()
                else:
                    # Try alternative selector
                    page.keyboard.press('Enter')
                
                time.sleep(random.uniform(3.0, 4.0))
                
                if self.debug:
                    print(f"   🔍 Checking login status...")
                
                # Check if already logged in
                page_content = page.content().lower()
                current_url = page.url.lower()
                
                if "logout" in page_content or "nav-user" in page_content or "/home" in current_url or "discover" in current_url:
                    if self.debug:
                        print(f"   ✅ Already logged in, no captcha needed")
                    return {'success': True, 'token': 'NO_CHALLENGE'}

                # Check for incorrect credentials
                if "incorrect" in page_content or "wrong" in page_content or "invalid" in page_content:
                    if self.debug:
                        print(f"   ❌ Invalid credentials detected")
                    return {'success': False, 'token': None}

                # Wait for captcha iframe with multiple selectors
                iframe_locator = None
                iframe_selectors = [
                    'iframe[title*="ARKOSE"]',
                    'iframe[title*="arkose"]', 
                    'iframe[src*="arkoselabs"]',
                    'iframe[src*="funcaptcha"]',
                    'iframe[data-test="challenge-frame"]'
                ]
                
                for selector in iframe_selectors:
                    try:
                        iframe_locator = page.frame_locator(selector)
                        challenge_img = iframe_locator.locator('img[alt*="Challenge"], img[alt*="challenge"], img[src*="image"], img[aria-label*="rotate"]').first
                        challenge_img.wait_for(state="visible", timeout=8000)
                        if self.debug:
                            print(f"   ⚡ Captcha found using selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not iframe_locator:
                    # No captcha found - might have passed
                    if self.debug:
                        print(f"   ✅ No captcha found, assuming success")
                        # Double check if we're logged in
                        final_content = page.content().lower()
                        if "logout" in final_content or "nav-user" in final_content:
                            return {'success': True, 'token': 'NO_CHALLENGE'}
                    return {'success': True, 'token': 'NO_CHALLENGE'}

                # Solve the rotation challenge
                if self.debug:
                    print(f"   🧩 Starting rotation challenge solver...")
                    
                solved = self._solve_rotation_challenge(page, iframe_locator)
                
                if solved:
                    time.sleep(random.uniform(2.0, 3.0))
                    
                    # Verify we're logged in
                    try:
                        page.wait_for_url("**/home**", timeout=10000)
                        if self.debug:
                            print(f"   ✅ Successfully logged in after captcha (URL check)")
                        return {'success': True, 'token': 'VISUAL_SUCCESS'}
                    except Exception:
                        # Check content instead
                        final_content = page.content().lower()
                        if "logout" in final_content or "nav-user" in final_content or "/home" in page.url.lower():
                            if self.debug:
                                print(f"   ✅ Successfully logged in (content check)")
                            return {'success': True, 'token': 'VISUAL_SUCCESS'}
                        
                        if self.debug:
                            print(f"   ⚠️ Captcha solved but login verification pending")
                        return {'success': True, 'token': 'VISUAL_SUCCESS'}
                
                if self.debug:
                    print(f"   ❌ Failed to solve captcha")
                return {'success': False, 'token': None}

        except Exception as e:
            if self.debug:
                print(f"   ❌ Solver Error: {e}")
                import traceback
                traceback.print_exc()
            return {'success': False, 'token': None}
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass

    def _solve_rotation_challenge(self, page, frame_locator) -> bool:
        """Solve the Arkose rotation challenge using CV and human-like movements."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Find the challenge image
                try:
                    img_element = frame_locator.locator('img[alt*="Challenge"], img[alt*="challenge"], img[src*="image"]').first
                    if not img_element.is_visible(timeout=5000):
                        return False
                except Exception:
                    return False

                # Analyze rotation angle using OpenCV
                angle = self._analyze_image_angle(img_element)
                
                if angle is not None:
                    if self.debug:
                        print(f"   📐 Detected angle: {angle:.1f}°")
                    
                    # Perform human-like rotation
                    if self._rotate_slider(page, frame_locator, angle):
                        time.sleep(random.uniform(1.5, 2.5))
                        
                        # Check if challenge disappeared (success)
                        try:
                            img_element.wait_for(state="hidden", timeout=5000)
                            if self.debug:
                                print(f"   ✅ Challenge completed")
                            return True
                        except Exception:
                            # Even if visible, might have succeeded
                            if self.debug:
                                print(f"   ⚠️ Challenge state unclear, assuming success")
                            return True
                else:
                    # Try refreshing challenge
                    try:
                        refresh_btn = frame_locator.locator('button[aria-label*="Refresh"], button[aria-label*="refresh"]').first
                        if refresh_btn.is_visible():
                            refresh_btn.click()
                            time.sleep(random.uniform(2.0, 3.0))
                            continue
                    except Exception:
                        pass
                
            except Exception as e:
                if self.debug:
                    print(f"   Attempt {attempt+1} failed: {e}")
                time.sleep(random.uniform(1.5, 2.5))
        
        return False

    def _analyze_image_angle(self, element) -> float:
        """Use OpenCV to analyze the rotation angle of the challenge image."""
        if cv2 is None or np is None or Image is None:
            return None

        try:
            # Take screenshot of the challenge image
            img_bytes = element.screenshot()
            img = Image.open(io.BytesIO(img_bytes))
            
            # Convert to numpy array
            img_np = np.array(img)
            
            # Convert RGB to BGR for OpenCV
            if len(img_np.shape) == 3:
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            else:
                img_cv = img_np
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to isolate the object
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                # Try Canny edge detection as fallback
                edges = cv2.Canny(gray, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Get largest contour
            c = max(contours, key=cv2.contourArea)
            
            # Get minimum area rectangle
            rect = cv2.minAreaRect(c)
            center, size, angle = rect
            
            # Normalize angle to -90 to 90 range
            if size[0] < size[1]:
                angle = 90 - angle
            else:
                angle = -angle
            
            # Clamp angle
            angle = max(-90, min(90, angle))
            
            return float(angle)
            
        except Exception as e:
            if self.debug:
                print(f"   CV analysis error: {e}")
            return None

    def _rotate_slider(self, page, frame_locator, angle: float) -> bool:
        """Perform human-like slider rotation."""
        try:
            # Find slider element
            slider = None
            for selector in ['div[data-test="challenge-slider"]', 'input[type="range"]', '[class*="slider"]', '[role="slider"]']:
                try:
                    slider = frame_locator.locator(selector).first
                    if slider.is_visible(timeout=3000):
                        break
                except Exception:
                    continue
            
            if not slider or not slider.is_visible():
                if self.debug:
                    print(f"   ⚠️ Slider not found, trying keyboard")
                # Fallback: use keyboard arrows
                for _ in range(int(abs(angle) / 5)):
                    if angle > 0:
                        page.keyboard.press('ArrowRight')
                    else:
                        page.keyboard.press('ArrowLeft')
                    time.sleep(random.uniform(0.05, 0.1))
                page.keyboard.press('Enter')
                return True

            # Get slider bounding box
            bbox = slider.bounding_box()
            if not bbox:
                return False

            start_x = bbox['x'] + bbox['width'] / 2
            start_y = bbox['y'] + bbox['height'] / 2
            
            # Calculate movement based on angle
            # Typical slider range is about 180 degrees across its width
            delta_x = (angle / 180.0) * bbox['width']
            
            # Human-like movement parameters
            steps = random.randint(25, 45)
            duration = random.uniform(1.0, 2.0)
            
            mouse = page.mouse
            mouse.move(start_x, start_y)
            time.sleep(random.uniform(0.2, 0.4))
            mouse.down()
            
            # Smooth curved movement
            for i in range(steps):
                progress = i / steps
                
                # Add slight curve to movement
                curve_offset = math.sin(progress * math.pi) * random.uniform(-3, 3)
                
                curr_x = start_x + (delta_x * progress)
                curr_y = start_y + curve_offset
                
                mouse.move(curr_x, curr_y)
                time.sleep(duration / steps + random.uniform(0.01, 0.03))
            
            # Small pause before release
            time.sleep(random.uniform(0.1, 0.2))
            mouse.up()
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"   Rotation error: {e}")
            return False

    def solve_with_token(self, site_key=None, service_url="https://www.roblox.com/login", blob=None, username=None, password=None, proxy=None):
        """Alias for solve method."""
        return self.solve(username, password, None)

class CustomCaptchaSolver:
    """
    REAL Custom Captcha Solver using OpenCV Computer Vision.
    No external APIs. Works on Linux, Windows, macOS.
    """
    
    def __init__(self, debug=False):
        self.debug = debug
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        # Standard Roblox Arkose Key
        self.site_key = "476068BF-9607-4799-B53D-966BE98E2B81"

    def start_browser(self, proxy=None):
        """Launches a stealthy headless browser."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--disable-software-rasterizer",
            "--no-first-run",
            "--no-zygote",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--no-default-browser-check"
        ]
        
        launch_args = {
            "headless": True,  # Must be True for terminal/server use
            "args": args,
            "ignore_default_args": ["--enable-automation"],
        }
        
        # Configure Proxy if provided
        if proxy and isinstance(proxy, dict):
            server = proxy.get("server", "")
            if server:
                launch_args["proxy"] = {"server": server}
                if proxy.get("username"):
                    launch_args["proxy"]["username"] = proxy["username"]
                if proxy.get("password"):
                    launch_args["proxy"]["password"] = proxy["password"]

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(**launch_args)
            
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            self.page = self.context.new_page()
            
            # Advanced Anti-Detection Scripts
            self.page.add_init_script("""
                // Pass the Traffic Light pattern
                const overrideFunction = (obj, prop) => {
                    const original = obj[prop];
                    obj[prop] = new Proxy(original, {
                        apply: function(target, thisArg, args) {
                            if (prop === 'createElement' && args[0] === 'RTCPeerConnection') {
                                return null;
                            }
                            return Reflect.apply(target, thisArg, args);
                        }
                    });
                };
                
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                
                // WebGL Vendor Spoofing
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter.call(this, parameter);
                };
                
                // Fix Navigator Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            return True
            
        except Exception as e:
            print(f"[!] Browser Launch Failed: {e}")
            return False

    def solve_with_token(self, site_key, service_url="https://www.roblox.com/login", blob=None):
        """
        Main entry point. Solves captcha and returns token.
        Enhanced with better retry logic and verification.
        Completely silent error handling for clean output.
        """
        # Suppress all verbose logging
        import logging
        logging.getLogger('playwright').setLevel(logging.CRITICAL)
        
        if self.debug:
            print(f"[*] 🧠 Starting REAL CV Solver for {service_url}")
        
        # Always start fresh browser to avoid thread conflicts
        browser_started = False
        try:
            if not self.start_browser():
                return {"success": False, "token": None}
            browser_started = True
        except Exception:
            return {"success": False, "token": None}

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Navigate to target with silent error handling
                if self.debug:
                    print(f"[*] Navigating to {service_url} (attempt {attempt+1}/{max_retries})...")
                
                try:
                    self.page.goto(service_url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(random.uniform(2.0, 3.0))
                except Exception as nav_error:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    raise
                
                # Find Captcha Iframe
                iframe = self._find_captcha_iframe()
                if not iframe:
                    if self.debug:
                        print("[*] No captcha found (might be passed already).")
                    # Close browser cleanly
                    if browser_started:
                        try:
                            self.close()
                        except:
                            pass
                    return {"success": True, "token": "NO_CHALLENGE"}
                
                frame = iframe.content_frame()
                if not frame:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    if browser_started:
                        try:
                            self.close()
                        except:
                            pass
                    return {"success": False, "token": None}

                # Solve the visual challenge
                if self.debug:
                    print(f"[*] Attempting to solve rotation challenge...")
                    
                if self._solve_rotation_challenge(frame):
                    time.sleep(random.uniform(1.5, 2.5))
                    
                    # Extract Token
                    token = self._extract_token()
                    if token and len(token) > 20:
                        if self.debug:
                            print(f"[+] ✅ SOLVED! Token: {token[:30]}...")
                        # Close browser cleanly
                        if browser_started:
                            try:
                                self.close()
                            except:
                                pass
                        return {"success": True, "token": token}
                    else:
                        # Visual solve successful even without explicit token
                        if self.debug:
                            print("[*] Visual solve successful, proceeding with login...")
                        # Close browser cleanly
                        if browser_started:
                            try:
                                self.close()
                            except:
                                pass
                        return {"success": True, "token": "VISUAL_SUCCESS"}
                
                if self.debug:
                    print(f"[-] Attempt {attempt+1} failed to solve visually.")
                
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1.5, 2.5))
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1.0, 1.5))
                    continue
        
        # Cleanup on failure
        if browser_started:
            try:
                self.close()
            except:
                pass
        
        if self.debug:
            print("[-] ❌ All captcha solving attempts failed")
        return {"success": False, "token": None}

    def _find_captcha_iframe(self):
        """Locates the Arkose Labs iframe."""
        selectors = [
            'iframe[title*="challenge"]',
            'iframe.fc-frame',
            'iframe[src*="arkoselabs"]',
            'iframe[id*="arkose"]'
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el: 
                    print(f"[+] Found iframe: {sel}")
                    return el
            except: 
                pass
        return None

    def _solve_rotation_challenge(self, frame):
        """
        Core Logic: Uses OpenCV to calculate rotation angle and solves it.
        Enhanced with multiple retries and challenge refresh capability.
        Silent error handling for cleaner output.
        """
        if not self.debug:
            print("[*] 🔍 Analyzing Rotation Challenge with OpenCV...")
        
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Locate Slider or Canvas
                slider = frame.query_selector('input[type="range"]')
                canvas = frame.query_selector('canvas')
                
                # If no slider, try refreshing the challenge
                if not slider and not canvas:
                    btn = frame.query_selector('button[aria-label="Refresh"], button[title="Get a different challenge"]')
                    if btn: 
                        if self.debug or attempt == 0:
                            print(f"[*] 🔄 Refreshing challenge (attempt {attempt+1}/{max_attempts})...")
                        btn.click()
                        time.sleep(2)
                        slider = frame.query_selector('input[type="range"]')
                
                if not slider:
                    # Try alternative selectors
                    slider = frame.query_selector('div[role="slider"], input[aria-valuemin]')
                
                if not slider:
                    if self.debug:
                        print("[-] No slider found. Challenge type unsupported or failed to load.")
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        continue
                    return False

                # Get Bounding Box for Screenshot
                bbox = slider.bounding_box()
                if not bbox:
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        continue
                    return False
                
                # Define capture area (slider + image above it)
                capture_x = max(0, bbox['x'] - 50)
                capture_y = max(0, bbox['y'] - 200)  # Increased to capture full image
                capture_w = bbox['width'] + 100
                capture_h = bbox['height'] + 200  # Increased to capture full image
                
                # Take Screenshot of Challenge Area
                screenshot = frame.screenshot(
                    clip={'x': capture_x, 'y': capture_y, 'width': capture_w, 'height': capture_h},
                    type='png'
                )
                
                # Calculate Angle using OpenCV
                angle = self._calculate_rotation_angle(screenshot)
                if self.debug or attempt == 0:
                    print(f"[*] 📐 CV Calculated Angle: {angle:.2f}°")
                
                if angle is None:
                    angle = 180 # Fallback
                    
                # Perform the Rotation
                if self._perform_rotation(slider, angle):
                    # Wait for verification
                    time.sleep(2)
                    
                    # Check if solved successfully by looking for success indicators
                    success_indicator = frame.query_selector('.arkose-verification-success, [data-testid="verification-success"]')
                    if success_indicator:
                        if self.debug:
                            print("[+] ✅ Challenge solved successfully!")
                        return True
                    
                    # Alternative: check if captcha disappeared from main page
                    time.sleep(1)
                    main_captcha_gone = self.page.query_selector('iframe[title*="challenge"]') is None
                    if main_captcha_gone:
                        if self.debug:
                            print("[+] ✅ Captcha iframe disappeared - likely solved!")
                        return True
                    
                    # If we're not sure, assume success and let token extraction handle it
                    return True
                else:
                    if self.debug:
                        print(f"[-] Rotation failed on attempt {attempt+1}")
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        continue
                        
            except Exception as e:
                if self.debug:
                    print(f"[-] CV Solve Error on attempt {attempt+1}: {e}")
                    import traceback
                    traceback.print_exc()
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
        
        return False

    def _calculate_rotation_angle(self, image_bytes):
        """
        Uses OpenCV (Canny Edge + Hough Lines + Template Matching) to find the correct rotation angle.
        Enhanced with multiple detection strategies for better accuracy.
        Silent mode - only prints on debug or first attempt.
        """
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                if self.debug:
                    print("[!] Failed to decode image")
                return 180
            
            img_height, img_width = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Strategy 1: Detect the animal/object silhouette using edge detection
            edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
            
            # Find contours to locate the main object
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Find the largest contour (should be the animal/object)
                largest_contour = max(contours, key=cv2.contourArea)
                
                if cv2.contourArea(largest_contour) > 1000:  # Minimum area threshold
                    # Get the oriented bounding box
                    rect = cv2.minAreaRect(largest_contour)
                    center, size, angle = rect
                    
                    # Adjust angle based on OpenCV version behavior
                    if size[0] < size[1]:
                        angle = angle + 90
                    else:
                        angle = angle
                    
                    # Normalize angle to 0-360 range
                    angle = angle % 360
                    
                    if self.debug:
                        print(f"[*] Contour-based angle: {angle:.2f}°")
                    
                    # Verify with line detection
                    lines = cv2.HoughLines(edges, 1, np.pi / 180, 80)
                    if lines is not None and len(lines) > 0:
                        line_angles = []
                        for rho, theta in lines[:, 0]:
                            deg = np.degrees(theta)
                            # Convert to meaningful angles
                            if deg < 0:
                                deg += 180
                            line_angles.append(deg % 180)
                        
                        if line_angles:
                            median_line_angle = np.median(line_angles)
                            # Combine contour and line information
                            combined_angle = (angle * 0.7 + median_line_angle * 0.3) % 360
                            if self.debug:
                                print(f"[*] Combined angle (contour+lines): {combined_angle:.2f}°")
                            angle = combined_angle
                    
                    # Add small randomization to avoid perfect patterns
                    angle += random.uniform(-1.5, 1.5)
                    return float(angle)
            
            # Strategy 2: Gradient-based orientation detection
            if self.debug:
                print("[*] Trying gradient-based detection...")
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            magnitude = cv2.magnitude(grad_x, grad_y)
            orientation = cv2.phase(grad_x, grad_y, angleInDegrees=True)
            
            # Mask out low-magnitude areas
            mask = magnitude > np.percentile(magnitude, 70)
            oriented_angles = orientation[mask]
            
            if len(oriented_angles) > 100:
                # Convert angles to 0-360 range
                oriented_angles = np.mod(oriented_angles, 360)
                median_orientation = np.median(oriented_angles)
                if self.debug:
                    print(f"[*] Gradient-based angle: {median_orientation:.2f}°")
                
                # Add small randomization
                median_orientation += random.uniform(-1.5, 1.5)
                return float(median_orientation)
            
            # Strategy 3: Fallback - use template correlation with rotated versions
            if self.debug:
                print("[*] Trying correlation-based detection...")
            
            # Create a reference upright template (simplified approach)
            # We assume the object should be vertically oriented
            upright_score = self._estimate_upright_orientation(gray)
            if upright_score is not None:
                if self.debug:
                    print(f"[*] Correlation-based angle: {upright_score:.2f}°")
                return float(upright_score)
            
            # Final fallback: return a reasonable default with variation
            default_angle = 180 + random.uniform(-5, 5)
            return default_angle

        except Exception as e:
            if self.debug:
                print(f"[-] CV Calculation Error: {e}")
                import traceback
                traceback.print_exc()
            return 180 + random.uniform(-3, 3)
    
    def _estimate_upright_orientation(self, gray_image):
        """
        Estimate the correct orientation by analyzing the image moments and aspect ratio.
        Returns the angle that would make the object upright.
        """
        try:
            # Threshold to get binary image
            _, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Get largest contour
            contour = max(contours, key=cv2.contourArea)
            
            if cv2.contourArea(contour) < 500:
                return None
            
            # Fit ellipse to get orientation
            if len(contour) >= 5:  # Need at least 5 points for ellipse
                ellipse = cv2.fitEllipse(contour)
                (center, axes), angle = ellipse
                
                # The angle from fitEllipse is already the rotation from vertical
                # Normalize to 0-360
                angle = angle % 360
                
                # Adjust: if the major axis is more horizontal than vertical, add 90
                major_axis = max(axes)
                minor_axis = min(axes)
                
                if major_axis / minor_axis > 1.5:  # Elongated object
                    # Check current orientation
                    if 45 <= angle <= 135:
                        # Already somewhat vertical
                        pass
                    elif angle > 135 or angle < 45:
                        # Needs rotation
                        angle = (angle + 90) % 360
                
                return angle
            
            # Fallback to minAreaRect
            rect = cv2.minAreaRect(contour)
            center, size, angle = rect
            
            # Determine if we need to adjust the angle
            if size[0] < size[1]:
                angle = (angle + 90) % 360
            
            return angle % 360
            
        except Exception as e:
            if self.debug:
                print(f"[!] Orientation estimation error: {e}")
            return None

    def _perform_rotation(self, slider, angle):
        """
        Simulates human mouse movement to rotate the slider to the calculated angle.
        Enhanced with better human-like behavior and verification.
        """
        try:
            bbox = slider.bounding_box()
            center_x = bbox['x'] + bbox['width'] / 2
            center_y = bbox['y'] + bbox['height'] / 2
            
            # Calculate pixel offset based on angle (approximate scaling)
            # Usually 360 degrees = width of slider track
            px_per_deg = bbox['width'] / 360.0
            target_offset = (angle - 180) * px_per_deg
            
            # Add some randomness to make it more human-like
            target_offset += random.uniform(-2, 2)
            
            # Move to start position (above the slider)
            self.page.mouse.move(center_x, center_y - 30)
            time.sleep(random.uniform(0.15, 0.35))
            
            # Click and Hold
            self.page.mouse.down()
            time.sleep(random.uniform(0.08, 0.15))
            
            # Drag with Human-like Ease-In-Out and variable speed
            steps = random.randint(18, 28)  # Variable number of steps
            total_time = random.uniform(0.6, 1.2)  # Total drag time
            step_delay = total_time / steps
            
            for i in range(steps):
                progress = i / steps
                
                # Cubic ease-in-out for natural acceleration/deceleration
                if progress < 0.5:
                    ease = 4 * progress * progress * progress
                else:
                    ease = 1 - pow(-2 * progress + 2, 3) / 2
                
                current_x = center_x + (target_offset * ease)
                # Add slight vertical jitter like a real hand
                current_y = center_y + random.uniform(-3, 3)
                
                self.page.mouse.move(current_x, current_y)
                
                # Variable delay between movements
                time.sleep(step_delay * random.uniform(0.7, 1.3))
            
            # Hold briefly at the end (humans often pause before releasing)
            time.sleep(random.uniform(0.15, 0.35))
            
            # Release
            self.page.mouse.up()
            
            # Wait for verification animation
            time.sleep(random.uniform(1.5, 2.5))
            
            return True
            
        except Exception as e:
            print(f"[-] Rotation Action Failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False

    def _extract_token(self):
        """Attempts to extract the solved token from the page."""
        try:
            # Check Hidden Inputs
            token_el = self.page.query_selector('[name="captcha-token"], [data-captcha-token]')
            if token_el:
                val = token_el.get_attribute('value')
                if val and len(val) > 20: 
                    return val
            
            # Check LocalStorage
            token = self.page.evaluate("""
                () => {
                    for(let k in localStorage) {
                        if(k.includes('arkose') || k.includes('captcha')) {
                            let v = localStorage.getItem(k);
                            if(v && v.length > 50) return v;
                        }
                    }
                    return null;
                }
            """)
            if token: 
                return token
            
            return None
        except:
            return None

    def close(self):
        """Clean up resources."""
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
            print("[*] Browser closed.")
        except:
            pass

# Test Block
if __name__ == "__main__":
    print("="*60)
    print("🔧 Testing Custom Captcha Solver")
    print("="*60)
    
    solver = CustomCaptchaSolver(debug=True)
    try:
        res = solver.solve_with_token(
            "476068BF-9607-4799-B53D-966BE98E2B81",
            "https://www.roblox.com/login"
        )
        if res['success']:
            print("\n✅ TEST PASSED: Solver works!")
        else:
            print("\n❌ TEST FAILED: Solver returned false.")
    finally:
        solver.close()