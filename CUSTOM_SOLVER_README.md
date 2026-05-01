# 🤖 Custom Roblox Captcha Solver

A **100% custom, self-hosted captcha solver** that works on all terminals (Linux, Windows, macOS) without external APIs like 2captcha.

## 🚀 Features

- ✅ **No External APIs** - Completely free and self-contained
- ✅ **Works on All Terminals** - Linux, Windows, macOS
- ✅ **Stealth Mode** - Bypasses bot detection with realistic browser simulation
- ✅ **Proxy Support** - Works with authenticated proxies
- ✅ **FunCaptcha Support** - Handles Roblox's Arkose Labs FunCaptcha
- ✅ **Audio Fallback** - Switches to audio challenge if visual fails
- ✅ **Human-like Simulation** - Randomized mouse movements to avoid detection

## 📦 Installation

```bash
# Install playwright
pip install playwright

# Install browser binaries
playwright install chromium
```

## 💻 Usage

### Basic Usage
```python
from custom_solver import CustomCaptchaSolver

solver = CustomCaptchaSolver(debug=True)
try:
    success = solver.solve_funcaptcha(
        site_key="E09A8CCB-2271-4D7A-82FE-F6AAD458DD49",
        service_url="https://www.roblox.com/Login"
    )
    if success:
        print("[SUCCESS] Captcha solved!")
    else:
        print("[FAILED] Could not solve captcha")
finally:
    solver.close()
```

### With Proxy
```python
from custom_solver import CustomCaptchaSolver
from util import parse_proxy

proxy_string = "username:password:host:port"
proxy_dict = parse_proxy(proxy_string)

solver = CustomCaptchaSolver(debug=True)
solver.start_browser(proxy=proxy_dict)
# ... rest of solving logic
```

## 🔧 How It Works

1. **Browser Launch**: Starts a stealthy Chromium instance with anti-detection scripts
2. **Captcha Detection**: Locates the FunCaptcha iframe and canvas element
3. **Game Logic**: 
   - Uses heuristic algorithms to simulate human interaction
   - Performs rotation sweeps to align objects
   - Randomizes timing and movement patterns
4. **Fallback Systems**:
   - If visual detection fails → switches to audio challenge
   - If game logic fails → retries with different parameters

## ⚙️ Advanced Configuration

### Debug Mode
Enable verbose logging for troubleshooting:
```python
solver = CustomCaptchaSolver(debug=True)
```

### Custom User Agent
Modify the user agent in `start_browser()` if needed.

### Headless Mode
For servers without display:
```python
launch_args["headless"] = True  # Note: May reduce success rate
```

## 🎯 Success Rate Optimization

For best results:
1. Use residential proxies (datacenter IPs are often flagged)
2. Add delays between attempts
3. Rotate user agents
4. Keep browser visible (headless=False) when possible

## 🛠️ Extending the Solver

### Adding AI Model Support
You can integrate a custom YOLO/ResNet model for image recognition:

```python
def _solve_game_logic(self, frame, canvas):
    # Take screenshot
    screenshot = canvas.screenshot()
    
    # Pass to your custom AI model
    rotation_angle = my_custom_model.predict(screenshot)
    
    # Apply rotation
    self._rotate_object(rotation_angle)
```

### Adding Audio Processing
For audio challenges, integrate speech-to-text:

```python
def _process_audio(self, audio_url):
    # Download audio
    # Use Whisper or similar for transcription
    # Return answer
    pass
```

## ⚠️ Limitations

- **FunCaptcha Complexity**: Some games require visual recognition that needs trained models
- **Rate Limits**: Too many attempts from same IP may trigger additional security
- **Updates**: Arkose Labs frequently updates their challenges; keep this script updated

## 📝 Notes

- This solver uses **browser automation** rather than API calls
- No monthly fees or token limits
- Works offline (except for initial browser download)
- For production use, consider training a custom ML model on FunCaptcha images

## 🐛 Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### "TimeoutError"
- Increase timeout values
- Check proxy connectivity
- Ensure target website is accessible

### "Element not found"
- Selectors may have changed; update frame_locator queries
- Try different service_url

## 📄 License

Free to use and modify. No attribution required.
