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

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def force_kill_roblox():
    print("  [Action] Force closing Roblox (taskkill)...")
    subprocess.run("taskkill /f /im RobloxPlayerBeta.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

def focus_roblox_window():
    print("  [Action] Attempting to focus Roblox window...")
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Roblox")
        if not hwnd:
            windows = gw.getWindowsWithTitle("Roblox")
            if windows:
                hwnd = windows[0]._hWnd
        
        if hwnd:
            print(f"  [Found Window] HWND: {hwnd}")
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.BringWindowToTop(hwnd)
            # Alt key tap to unlock SetForegroundWindow
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt down
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt up
            time.sleep(0.5)
            return True
            
        windows = gw.getWindowsWithTitle("Roblox")
        if windows:
            rbox = windows[0]
            print(f"  [Found Window via pygetwindow] Title: {rbox.title}")
            if rbox.isMinimized:
                rbox.restore()
            rbox.activate()
            time.sleep(0.5)
            return True
        else:
            print("  [!] Roblox window not found!")
    except Exception as e:
        print(f"  [!] Warning focusing Roblox window: {e}")
    return False

def find_image_on_screen(image_name, confidence=0.8, timeout=10):
    image_path = os.path.join(ASSETS_DIR, image_name)
    if not os.path.exists(image_path):
        print(f"  [!] Template missing: {image_path}")
        return None
        
    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None
        
    th, tw = template.shape[:2]
    start_time = time.time()
    
    while time.time() - start_time < timeout:
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
        
    print(f"  [!] Match timed out for {image_name}")
    return None

def enter_ps_code(code):
    print(f"  [Action] Copying & pasting PS code: '{code}'...")
    pyperclip.copy(code)
    time.sleep(0.3)
    pydirectinput.keyDown('ctrl')
    pydirectinput.press('v')
    pydirectinput.keyUp('ctrl')
    time.sleep(0.3)

def run_debug():
    print("======================================================")
    print("   GPO Merch Sync - Standalone Join Debug Script 🧪   ")
    print("======================================================")
    
    if not is_admin():
        print("[!] WARNING: Terminal is not running as Administrator.")

    if not os.path.exists(CONFIG_PATH):
        print(f"[!] config.json not found at {CONFIG_PATH}!")
        return

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    afk_desktop = config.get("afk_desktop_index", 2)
    ps_code = config.get("gpo_ps_code", "")
    place_id = config.get("roblox_place_id", "1730877806")
    coords = config.get("coords", {})

    print(f"Config Loaded:")
    print(f"  - AFK Desktop: #{afk_desktop}")
    print(f"  - PS Code: '{ps_code}'")
    print(f"  - Place ID: {place_id}")
    print(f"  - Coordinates: {coords}\n")

    # Step 1: Switch Desktop
    print("\n--- [Step 1] Switch Desktop ---")
    switch_to_desktop_num(afk_desktop)

    # Step 2: Cleanup & Launch
    print("\n--- [Step 2] Kill Roblox & Launch roblox:// ---")
    force_kill_roblox()
    time.sleep(1.5)
    
    print(f"  [Action] Launching roblox://placeId={place_id}...")
    os.startfile(f"roblox://placeId={place_id}")

    # Step 3: Wait & Focus Window
    print("\n--- [Step 3] Wait for Roblox & Focus ---")
    print("  [System] Polling for Roblox window (max 15s)...")
    focused = False
    for i in range(15):
        if focus_roblox_window():
            print(f"  [✓] Focused Roblox window after {i+1} seconds.")
            focused = True
            break
        time.sleep(1.0)
        
    if not focused:
        print("  [!] Failed to focus Roblox window after 15 seconds.")

    time.sleep(3.0)

    # Step 4: Keypress to dismiss splash
    print("\n--- [Step 4] Keypress to dismiss splash screen ---")
    focus_roblox_window()
    print("  [Action] Sending keypress 'f'...")
    pydirectinput.press('f')
    time.sleep(2.5)

    # Step 5: PS Button
    print("\n--- [Step 5] Click Main Menu PS Button ---")
    focus_roblox_window()
    ps_btn_pos = None
    if coords.get("ps_button") and isinstance(coords["ps_button"], dict):
        ps_btn_pos = (coords["ps_button"]["x"], coords["ps_button"]["y"])
        print(f"  [Config Coords] Main Menu PS Button: {ps_btn_pos}")
    else:
        ps_btn_pos = find_image_on_screen("ps_button.png", timeout=5)

    if ps_btn_pos:
        focus_roblox_window()
        print(f"  [Action] pydirectinput.click({ps_btn_pos[0]}, {ps_btn_pos[1]})...")
        pydirectinput.click(ps_btn_pos[0], ps_btn_pos[1])
        time.sleep(1.5)
    else:
        print("  [!] No coordinates or template found for Main Menu PS Button!")

    # Step 6: PS Box
    print("\n--- [Step 6] Click PS Box & Paste PS Code ---")
    focus_roblox_window()
    ps_pos = None
    if coords.get("ps_box") and isinstance(coords["ps_box"], dict):
        ps_pos = (coords["ps_box"]["x"], coords["ps_box"]["y"])
        print(f"  [Config Coords] PS Box: {ps_pos}")
    else:
        ps_pos = find_image_on_screen("ps_box.png", timeout=5)

    if ps_pos:
        focus_roblox_window()
        print(f"  [Action] pydirectinput.click({ps_pos[0]}, {ps_pos[1]})...")
        pydirectinput.click(ps_pos[0], ps_pos[1])
        time.sleep(0.5)
        enter_ps_code(ps_code)
        print("  [Action] Pressing Enter...")
        pydirectinput.press('enter')
        time.sleep(2.5)
    else:
        print("  [!] No coordinates or template found for PS Box!")

    # Step 7: Regular Button
    print("\n--- [Step 7] Click 'Regular' Button ---")
    focus_roblox_window()
    reg_pos = None
    if coords.get("regular_button") and isinstance(coords["regular_button"], dict):
        reg_pos = (coords["regular_button"]["x"], coords["regular_button"]["y"])
        print(f"  [Config Coords] Regular Button: {reg_pos}")
    else:
        reg_pos = find_image_on_screen("regular_button.png", timeout=5)

    if reg_pos:
        focus_roblox_window()
        print(f"  [Action] pydirectinput.click({reg_pos[0]}, {reg_pos[1]})...")
        pydirectinput.click(reg_pos[0], reg_pos[1])
        time.sleep(2.0)
    else:
        print("  [!] No coordinates or template found for Regular Button!")

    # Step 8: First Sea Button
    print("\n--- [Step 8] Click 'First Sea' Button ---")
    focus_roblox_window()
    sea_pos = None
    if coords.get("first_sea_button") and isinstance(coords["first_sea_button"], dict):
        sea_pos = (coords["first_sea_button"]["x"], coords["first_sea_button"]["y"])
        print(f"  [Config Coords] First Sea Button: {sea_pos}")
    else:
        sea_pos = find_image_on_screen("first_sea.png", timeout=5)

    if sea_pos:
        focus_roblox_window()
        print(f"  [Action] pydirectinput.click({sea_pos[0]}, {sea_pos[1]})...")
        pydirectinput.click(sea_pos[0], sea_pos[1])
    else:
        print("  [!] No coordinates or template found for First Sea Button!")

    print("\n======================================================")
    print(" [✓] Debug Join Sequence Finished!")
    print("======================================================")

if __name__ == "__main__":
    run_debug()
