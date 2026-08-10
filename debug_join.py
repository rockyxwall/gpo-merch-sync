import os
import sys
import json
import time
import ctypes
import subprocess
import datetime

try:
    import cv2
    import pydirectinput
    import pygetwindow as gw
    import pyperclip
    import keyboard
    from PIL import ImageGrab
    import pyvda
except ImportError:
    print("[!] Missing dependencies. Run with uv:")
    print("    uv run python debug_join.py")
    sys.exit(1)

# Configure pydirectinput
pydirectinput.FAILSAFE = False
pydirectinput.PAUSE = 0.2

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

EMERGENCY_STOP = False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def force_kill_roblox():
    print("  [Action] Force closing Roblox (taskkill)...")
    subprocess.run("taskkill /f /im RobloxPlayerBeta.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def setup_hotkeys():
    global EMERGENCY_STOP
    def on_stop():
        global EMERGENCY_STOP
        print("\n[Hotkey F6/F8] EMERGENCY FORCE STOP TRIGGERED! Closing Roblox...")
        EMERGENCY_STOP = True
        force_kill_roblox()
        os._exit(1)

    keyboard.add_hotkey("f6", on_stop)
    keyboard.add_hotkey("f8", on_stop)
    print(" [Hotkeys Active] Press F6 or F8 at any time to FORCE STOP the script.")

def get_current_desktop_num():
    try:
        if hasattr(pyvda, "VirtualDesktop"):
            return pyvda.VirtualDesktop.current().number
        elif hasattr(pyvda, "get_current_desktop"):
            return pyvda.get_current_desktop().number
    except Exception as e:
        print(f"  [!] Error getting desktop number: {e}")
    return 1

def switch_to_desktop_num(num):
    print(f"  [Action] Switching to Virtual Desktop #{num}...")
    try:
        if hasattr(pyvda, "VirtualDesktop"):
            pyvda.VirtualDesktop(num).go()
            time.sleep(0.8)
            curr = get_current_desktop_num()
            print(f"  [✓] Virtual Desktop switch result: Now on Desktop #{curr}")
            return curr == num
        elif hasattr(pyvda, "get_virtual_desktops"):
            desktops = pyvda.get_virtual_desktops()
            for d in desktops:
                if getattr(d, "number", None) == num:
                    if hasattr(d, "go"):
                        d.go()
                    elif hasattr(d, "switch"):
                        d.switch()
                    time.sleep(0.8)
                    return True
    except Exception as e:
        print(f"  [!] Virtual desktop switch error: {e}")
    return False

def focus_roblox_window(maximize=True):
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Roblox")
        if not hwnd:
            windows = gw.getWindowsWithTitle("Roblox")
            if windows:
                hwnd = windows[0]._hWnd
        
        if hwnd:
            cmd = 3 if maximize else 9  # 3 = SW_MAXIMIZE, 9 = SW_RESTORE
            ctypes.windll.user32.ShowWindow(hwnd, cmd)
            ctypes.windll.user32.BringWindowToTop(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt down
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt up
            time.sleep(0.5)
            return True
            
        windows = gw.getWindowsWithTitle("Roblox")
        if windows:
            rbox = windows[0]
            if maximize:
                try:
                    rbox.maximize()
                except Exception:
                    pass
            elif rbox.isMinimized:
                rbox.restore()
            rbox.activate()
            time.sleep(0.5)
            return True
    except Exception as e:
        print(f"  [!] Warning focusing Roblox window: {e}")
    return False

def wait_for_roblox_window(timeout=30):
    print(f"  [System] Waiting up to {timeout}s for Roblox window to load & maximize...")
    start = time.time()
    while time.time() - start < timeout:
        if EMERGENCY_STOP:
            return False
        if focus_roblox_window(maximize=True):
            print(f"  [✓] Roblox window detected & MAXIMIZED on screen!")
            return True
        time.sleep(1.0)
    print("  [!] Roblox window was NOT found within timeout.")
    return False

def get_config_confidence():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                return float(cfg.get("confidence", 0.5))
    except Exception:
        pass
    return 0.5

def find_image_on_screen(image_name, confidence=None, timeout=10):
    if confidence is None:
        confidence = get_config_confidence()
    image_path = os.path.join(ASSETS_DIR, image_name)
    if not os.path.exists(image_path):
        print(f"  [Notice] Image template file missing: assets/{image_name}")
        return None
        
    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None
        
    th, tw = template.shape[:2]
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if EMERGENCY_STOP:
            return None
        screenshot = ImageGrab.grab()
        screenshot_path = os.path.join(ASSETS_DIR, "_temp_scan.png")
        screenshot.save(screenshot_path)
        
        screen_img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            
        if screen_img is None:
            time.sleep(0.5)
            continue
            
        res = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= confidence:
            center_x = max_loc[0] + (tw // 2)
            center_y = max_loc[1] + (th // 2)
            print(f"  [Match Found] {image_name} at ({center_x}, {center_y}) confidence: {max_val:.2f}")
            return (center_x, center_y)
            
        time.sleep(0.5)
        
    print(f"  [!] Scan timed out for template: assets/{image_name}")
    return None

def enter_ps_code(code):
    print(f"  [Action] Copying & pasting PS code: '{code}'...")
    pyperclip.copy(code)
    time.sleep(0.3)
    pydirectinput.keyDown('ctrl')
    pydirectinput.press('v')
    pydirectinput.keyUp('ctrl')
    time.sleep(0.3)

def real_mouse_click(x, y, hover_pause=0.3):
    """Moves physical cursor to (x, y), hovers to trigger UI hover state, then clicks."""
    pydirectinput.moveTo(int(x), int(y))
    time.sleep(hover_pause)
    pydirectinput.click(int(x), int(y))
    time.sleep(0.2)

def run_debug():
    print("======================================================")
    print("   GPO Merch Sync - Standalone Join Debug Script 🧪   ")
    print("======================================================")
    
    if not is_admin():
        print("[!] WARNING: Terminal is not running as Administrator.")

    setup_hotkeys()

    if not os.path.exists(CONFIG_PATH):
        print(f"[!] config.json not found at {CONFIG_PATH}!")
        return

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    afk_desktop = config.get("afk_desktop_index", 2)
    ps_code = config.get("gpo_ps_code", "")
    place_id = config.get("roblox_place_id", "1730877806")

    print(f"Config Loaded:")
    print(f"  - AFK Desktop: #{afk_desktop}")
    print(f"  - PS Code: '{ps_code}'")
    print(f"  - Place ID: {place_id}\n")

    # Step 1: Switch Desktop
    print("\n--- [Step 1] Switch Desktop ---")
    switch_to_desktop_num(afk_desktop)

    # Step 2: Launch via roblox://
    print("\n--- [Step 2] Launch roblox:// ---")
    print(f"  [Action] Launching roblox://placeId={place_id}...")
    os.startfile(f"roblox://placeId={place_id}")

    # Step 3: Wait & Focus Window
    print("\n--- [Step 3] Wait for Roblox & Maximize Window ---")
    roblox_ready = wait_for_roblox_window(timeout=30)
    
    if not roblox_ready:
        print("\n[!] CRITICAL: Roblox window failed to launch or be detected.")
        print("[!] Aborting join sequence.")
        return

    conf = float(config.get("confidence", 0.5))

    if EMERGENCY_STOP:
        return

    # Step 4: Detect GPO Logo & Press 'f'
    print("\n--- [Step 4] Detect GPO Splash Logo (gpo_logo.png) & Enter Main Menu ---")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before GPO logo check. Aborting.")
        return
        
    print(f"  [System] Scanning screen with OpenCV for GPO Logo ('gpo_logo.png', timeout 45s, threshold {conf})...")
    logo_pos = find_image_on_screen("gpo_logo.png", confidence=conf, timeout=45)
    
    if logo_pos:
        print(f"  [✓ Image Recognized] GPO Logo screen detected at {logo_pos}!")
    else:
        print("  [Notice] GPO Logo scan completed. Sending keypress...")

    focus_roblox_window(maximize=True)
    print("  [Action] Sending keypress 'f' to enter Main Menu...")
    pydirectinput.press('f')
    time.sleep(3.0)

    if EMERGENCY_STOP:
        return

    # Step 5: PS Button (100% Pure Image Recognition)
    print("\n--- [Step 5] Detect Main Menu Screen (ps_button.png) ---")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before PS Button click. Aborting.")
        return
        
    print(f"  [System] Scanning screen with OpenCV for 'ps_button.png' (timeout 30s, threshold {conf})...")
    ps_btn_pos = find_image_on_screen("ps_button.png", confidence=conf, timeout=30)
    
    if ps_btn_pos:
        print(f"  [✓ Image Recognized] Found Main Menu PS Button at {ps_btn_pos}")
        focus_roblox_window(maximize=True)
        print(f"  [Action] Hovering & Clicking PS Button at {ps_btn_pos}...")
        real_mouse_click(ps_btn_pos[0], ps_btn_pos[1], hover_pause=0.3)
        time.sleep(2.0)
    else:
        print("  [!] ERROR: Image recognition failed for 'assets/ps_button.png'. Please re-run setup.py!")
        return

    if EMERGENCY_STOP:
        return

    # Step 6: PS Box (100% Pure Image Recognition)
    print("\n--- [Step 6] Detect PS Box (ps_box.png) ---")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before PS Box click. Aborting.")
        return
        
    print(f"  [System] Scanning screen with OpenCV for 'ps_box.png' (timeout 15s, threshold {conf})...")
    ps_pos = find_image_on_screen("ps_box.png", confidence=conf, timeout=15)

    if ps_pos:
        print(f"  [✓ Image Recognized] Found PS Box at {ps_pos}")
        focus_roblox_window(maximize=True)
        print(f"  [Action] Hovering & Clicking PS Code Box at {ps_pos}...")
        real_mouse_click(ps_pos[0], ps_pos[1], hover_pause=0.3)
        time.sleep(0.5)
        enter_ps_code(ps_code)
        print("  [Action] Pressing Enter...")
        pydirectinput.press('enter')
        time.sleep(3.0)
    else:
        print("  [!] ERROR: Image recognition failed for 'assets/ps_box.png'. Please re-run setup.py!")
        return

    if EMERGENCY_STOP:
        return

    # Step 7: Regular Button (100% Pure Image Recognition)
    print("\n--- [Step 7] Detect 'Regular' Mode Button (regular_button.png) ---")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before Regular Button click. Aborting.")
        return
        
    print(f"  [System] Scanning screen with OpenCV for 'regular_button.png' (timeout 15s, threshold {conf})...")
    reg_pos = find_image_on_screen("regular_button.png", confidence=conf, timeout=15)

    if reg_pos:
        print(f"  [✓ Image Recognized] Found Regular Button at {reg_pos}")
        focus_roblox_window(maximize=True)
        print(f"  [Action] Hovering & Clicking 'Regular' Button at {reg_pos}...")
        real_mouse_click(reg_pos[0], reg_pos[1], hover_pause=0.3)
        time.sleep(2.5)
    else:
        print("  [!] ERROR: Image recognition failed for 'assets/regular_button.png'. Please re-run setup.py!")
        return

    if EMERGENCY_STOP:
        return

    # Step 8: First Sea Button (100% Pure Image Recognition)
    print("\n--- [Step 8] Detect 'First Sea' Button (first_sea_button.png) ---")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before First Sea Button click. Aborting.")
        return
        
    print(f"  [System] Scanning screen with OpenCV for 'first_sea_button.png' (timeout 15s, threshold {conf})...")
    sea_pos = find_image_on_screen("first_sea_button.png", confidence=conf, timeout=15)
    if not sea_pos:
        sea_pos = find_image_on_screen("first_sea.png", confidence=conf, timeout=5)

    if sea_pos:
        print(f"  [✓ Image Recognized] Found First Sea Button at {sea_pos}")
        focus_roblox_window(maximize=True)
        print(f"  [Action] Hovering & Clicking 'First Sea' Button at {sea_pos}...")
        real_mouse_click(sea_pos[0], sea_pos[1], hover_pause=0.3)
    else:
        print("  [!] ERROR: Image recognition failed for 'assets/first_sea_button.png'. Please re-run setup.py!")

    print("\n======================================================")
    print(" [✓] Debug Join Sequence Finished!")
    print("======================================================")

if __name__ == "__main__":
    run_debug()
