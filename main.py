import os
import sys
import json
import time
import ctypes
import threading
import subprocess
import datetime
import winsound

try:
    import cv2
    import pydirectinput
    import pygetwindow as gw
    import pyperclip
    import keyboard
    from plyer import notification
    from PIL import ImageGrab
    import pyvda
except ImportError:
    print("[!] Missing dependencies. Run with uv:")
    print("    uv run python main.py")
    sys.exit(1)

# Configure pydirectinput safety
pydirectinput.FAILSAFE = False  # Controlled via keyboard F6 hotkey & bounds checks
pydirectinput.PAUSE = 0.1

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Global flags
CYCLE_FINISHED = False
EMERGENCY_STOP = False
CURRENT_MAIN_DESKTOP = 1

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def force_kill_roblox():
    print("\n[System] Closing Roblox process...")
    subprocess.run("taskkill /f /im RobloxPlayerBeta.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_alarm():
    def _beep():
        for _ in range(5):
            if CYCLE_FINISHED or EMERGENCY_STOP:
                break
            winsound.Beep(1000, 400)
            time.sleep(0.1)
            winsound.Beep(1500, 400)
            time.sleep(0.1)
    threading.Thread(target=_beep, daemon=True).start()

def send_toast(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="GPO Merch Sync",
            timeout=10
        )
    except Exception:
        pass

def get_current_desktop_num():
    try:
        if hasattr(pyvda, "VirtualDesktop"):
            return pyvda.VirtualDesktop.current().number
        elif hasattr(pyvda, "get_current_desktop"):
            return pyvda.get_current_desktop().number
    except Exception:
        pass
    return 1

def switch_to_desktop_num(num):
    try:
        if hasattr(pyvda, "VirtualDesktop"):
            pyvda.VirtualDesktop(num).go()
            time.sleep(0.5)
            return True
        elif hasattr(pyvda, "get_virtual_desktops"):
            desktops = pyvda.get_virtual_desktops()
            for d in desktops:
                if getattr(d, "number", None) == num:
                    if hasattr(d, "go"):
                        d.go()
                    elif hasattr(d, "switch"):
                        d.switch()
                    time.sleep(0.5)
                    return True
    except Exception as e:
        print(f"[!] Virtual desktop switch error: {e}")
    return False

def setup_hotkeys(afk_desktop_num):
    global CYCLE_FINISHED, EMERGENCY_STOP, CURRENT_MAIN_DESKTOP
    
    def on_f8():
        global CYCLE_FINISHED
        print("\n[Hotkey F8] Cycle finished! Closing Roblox & returning to Desktop 1...")
        CYCLE_FINISHED = True
        force_kill_roblox()
        switch_to_desktop_num(CURRENT_MAIN_DESKTOP)

    def on_f6():
        global EMERGENCY_STOP
        print("\n[Hotkey F6] EMERGENCY STOP ACTIVATED!")
        EMERGENCY_STOP = True
        force_kill_roblox()
        switch_to_desktop_num(CURRENT_MAIN_DESKTOP)
        os._exit(1)

    keyboard.add_hotkey("f8", on_f8)
    keyboard.add_hotkey("f6", on_f6)
    print(" [Keybinds Active] F8: Finish Stock Check & Return | F6: Emergency Force Stop")

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
        print(f"[!] Warning focusing Roblox window: {e}")
    return False

def wait_for_roblox_window(timeout=30):
    print(f"[System] Waiting up to {timeout}s for Roblox window to load & maximize...")
    start = time.time()
    while time.time() - start < timeout:
        if EMERGENCY_STOP:
            return False
        if focus_roblox_window(maximize=True):
            print(f" [✓] Roblox window detected & MAXIMIZED on screen!")
            return True
        time.sleep(1.0)
    print("[!] Roblox window was NOT found within timeout.")
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

def find_image_on_screen(image_name, confidence=None, timeout=90):
    if confidence is None:
        confidence = get_config_confidence()
    image_path = os.path.join(ASSETS_DIR, image_name)
    if not os.path.exists(image_path):
        print(f"[!] Template image missing: {image_path}. Run setup.py first!")
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
            print(f" [✓ Image Rec] {image_name} matched at ({center_x}, {center_y}) score: {max_val:.2f} (threshold: {confidence:.2f})")
            return (center_x, center_y)
            
        time.sleep(0.5)
        
    return None

def enter_ps_code(code):
    pyperclip.copy(code)
    time.sleep(0.2)
    pydirectinput.keyDown('ctrl')
    pydirectinput.press('v')
    pydirectinput.keyUp('ctrl')
    time.sleep(0.3)
    # Fallback writing if clipboard is blank
    if not code:
        pydirectinput.write(code)

def real_mouse_click(x, y, hover_pause=0.3):
    """Moves physical cursor to (x, y), hovers to trigger UI hover state, then clicks."""
    pydirectinput.moveTo(x, y)
    time.sleep(hover_pause)
    pydirectinput.click(x, y)
    time.sleep(0.2)

def run_ps_join_workflow(config):
    afk_desktop = config.get("afk_desktop_index", 2)
    ps_code = config.get("gpo_ps_code", "")
    place_id = config.get("roblox_place_id", "1730877806")
    coords = config.get("coords", {})

    print(f"\n[Action] Switching to AFK Virtual Desktop #{afk_desktop}...")
    switch_to_desktop_num(afk_desktop)

    # Launch via roblox://
    print("[Action] Launching Roblox GPO via roblox:// protocol...")
    os.startfile(f"roblox://placeId={place_id}")
    
    # Wait for Roblox window to load & maximize
    roblox_ready = wait_for_roblox_window(timeout=30)
    if not roblox_ready:
        print("[!] CRITICAL: Roblox window failed to launch or be detected. Aborting join workflow.")
        return False

    conf = config.get("confidence", 0.5)

    # 3. Detect GPO Splash Logo (gpo_logo.png) & Press 'f' to enter Main Menu
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before GPO logo check. Aborting.")
        return False
        
    print(f"[System] Scanning screen with OpenCV for GPO Logo ('gpo_logo.png', timeout 45s, threshold {conf})...")
    logo_pos = find_image_on_screen("gpo_logo.png", confidence=conf, timeout=45)
    if logo_pos:
        print(f" [✓ Image Recognized] GPO Splash screen detected at {logo_pos}!")

    focus_roblox_window(maximize=True)
    print("[Action] Focusing Roblox & pressing 'f' key to enter Main Menu...")
    pydirectinput.press('f')
    time.sleep(3.0)  # Wait for main menu UI buttons to appear

    # 4. Main Menu PS Button (100% Pure Image Recognition)
    print(f"[System] Using OpenCV image recognition to detect Main Menu ('ps_button.png', threshold {conf})...")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before PS Button click. Aborting.")
        return False
        
    ps_btn_pos = find_image_on_screen("ps_button.png", confidence=conf, timeout=30)
    
    if ps_btn_pos:
        focus_roblox_window(maximize=True)
        print(f"[Action] Hovering & Clicking Main Menu PS Button at {ps_btn_pos}...")
        real_mouse_click(ps_btn_pos[0], ps_btn_pos[1], hover_pause=0.3)
        time.sleep(2.0)
    else:
        print("[!] ERROR: Image recognition failed for 'assets/ps_button.png'. Please re-run setup.py!")
        return False

    if EMERGENCY_STOP:
        return False

    # 5. PS Code Box (100% Pure Image Recognition)
    print(f"[System] Using image recognition to detect PS Code text input box ('ps_box.png', threshold {conf})...")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before PS Box click. Aborting.")
        return False
        
    ps_pos = find_image_on_screen("ps_box.png", confidence=conf, timeout=15)

    if ps_pos:
        focus_roblox_window(maximize=True)
        print(f"[Action] Hovering & Clicking PS Code Box at {ps_pos}...")
        real_mouse_click(ps_pos[0], ps_pos[1], hover_pause=0.3)
        time.sleep(0.5)
        
        print("[Action] Pasting PS Code...")
        enter_ps_code(ps_code)
        pydirectinput.press('enter')
        time.sleep(3.0)
    else:
        print("[!] ERROR: Image recognition failed for 'assets/ps_box.png'. Please re-run setup.py!")
        return False

    if EMERGENCY_STOP:
        return False

    # 6. Regular Button (100% Pure Image Recognition)
    print(f"[System] Using image recognition to detect 'Regular' game mode button (threshold {conf})...")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before Regular Button click. Aborting.")
        return False
        
    reg_pos = find_image_on_screen("regular_button.png", confidence=conf, timeout=15)

    if reg_pos:
        focus_roblox_window(maximize=True)
        print(f"[Action] Hovering & Clicking 'Regular' button at {reg_pos}...")
        real_mouse_click(reg_pos[0], reg_pos[1], hover_pause=0.3)
        time.sleep(2.5)
    else:
        print("[!] ERROR: Image recognition failed for 'assets/regular_button.png'. Please re-run setup.py!")
        return False

    if EMERGENCY_STOP:
        return False

    # 7. First Sea Button (100% Pure Image Recognition)
    print(f"[System] Using image recognition to detect 'First Sea' button (threshold {conf})...")
    if not focus_roblox_window(maximize=True):
        print("[!] Roblox window lost before First Sea Button click. Aborting.")
        return False
        
    sea_pos = find_image_on_screen("first_sea_button.png", confidence=conf, timeout=15)
    if not sea_pos:
        sea_pos = find_image_on_screen("first_sea.png", confidence=conf, timeout=5)

    if sea_pos:
        focus_roblox_window(maximize=True)
        print(f"[Action] Hovering & Clicking 'First Sea' button at {sea_pos}...")
        real_mouse_click(sea_pos[0], sea_pos[1], hover_pause=0.3)
    else:
        print("[!] ERROR: Image recognition failed for 'assets/first_sea_button.png'. Please re-run setup.py!")
        return False

    print(" [✓] Server join sequence completed!")
    return True

def get_countdown_input(config):
    print("\n------------------------------------------------------")
    print(" [Global Stock Refresh Calibration]")

    # Check if config has calibrated_refresh_timestamp
    calibrated_ts = config.get("calibrated_refresh_timestamp", 0)
    if calibrated_ts > time.time():
        seconds_left = calibrated_ts - time.time()
        refresh_str = datetime.datetime.fromtimestamp(calibrated_ts).strftime('%I:%M:%S %p')
        print(f" Saved Calibration Found: Next Refresh at {refresh_str}")
        use_saved = input(" Use saved calibration from setup.py? (y/n) [y]: ").strip().lower()
        if use_saved != 'n':
            return seconds_left

    print(" Look at the Discord Stock Tracker bot.")
    try:
        minutes = int(input(" Enter remaining MINUTES until Global Stock Refresh: "))
        seconds = int(input(" Enter remaining SECONDS until Global Stock Refresh: "))
        return (minutes * 60) + seconds
    except ValueError:
        print("[!] Invalid input. Defaulting to 15 minutes.")
        return 15 * 60

def main():
    global CURRENT_MAIN_DESKTOP, CYCLE_FINISHED, EMERGENCY_STOP
    
    print("======================================================")
    print("    GPO Merch Sync - Virtual Desktop AFK Looper 🏴‍☠️  ")
    print("======================================================")

    if not is_admin():
        print("[!] WARNING: Running without Administrator privileges.")
        print("    For best results with DirectInput & keybind hooks, run in an Administrator terminal!")

    if not os.path.exists(CONFIG_PATH):
        print("\n[!] ERROR: config.json not found!")
        print("    Please run the setup wizard first to configure your settings:")
        print("    Command: uv run python setup.py\n")
        input("Press ENTER to exit...")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    if not config.get("gpo_ps_code") or config.get("gpo_ps_code") == "YOUR_PS_CODE_HERE":
        print("\n[!] ERROR: GPO Private Server Code is not configured in config.json!")
        print("    Please run setup.py to set your PS Code:")
        print("    Command: uv run python setup.py\n")
        input("Press ENTER to exit...")
        sys.exit(1)

    afk_desktop_num = config.get("afk_desktop_index", 2)
    setup_hotkeys(afk_desktop_num)

    wiki_seconds_left = get_countdown_input(config)
    
    current_time = time.time()
    next_refresh_time = current_time + wiki_seconds_left

    # Launch timing offset: Launch at T-13m 30s before refresh
    join_offset_seconds = (13 * 60) + 30
    refresh_cycle_seconds = 30 * 60

    print("\n [✓] Calibrated successfully.")

    while not EMERGENCY_STOP:
        CYCLE_FINISHED = False
        current_time = time.time()
        launch_time = next_refresh_time - join_offset_seconds

        if launch_time <= current_time:
            next_refresh_time += refresh_cycle_seconds
            launch_time = next_refresh_time - join_offset_seconds

        CURRENT_MAIN_DESKTOP = get_current_desktop_num()
        launch_str = datetime.datetime.fromtimestamp(launch_time).strftime('%I:%M:%S %p')
        refresh_str = datetime.datetime.fromtimestamp(next_refresh_time).strftime('%I:%M:%S %p')

        print(f"\n[Timer] Next Global Stock Refresh at: {refresh_str}")
        print(f"[Timer] Roblox AFK join will trigger at: {launch_str}")
        print(f"[Timer] Waiting on Desktop #{CURRENT_MAIN_DESKTOP} for AFK trigger...")

        while time.time() < launch_time and not EMERGENCY_STOP:
            now = time.time()
            remaining = launch_time - now
            mins = int(max(0, remaining) // 60)
            secs = int(max(0, remaining) % 60)
            total_secs = int(max(0, remaining))

            sys.stdout.write(f"\r[Timer Countdown] {mins}m {secs}s remaining ({total_secs}s) until AFK join...   ")
            sys.stdout.flush()
            time.sleep(1)

        print("")

        if EMERGENCY_STOP:
            break

        # Save main study desktop index before switching
        CURRENT_MAIN_DESKTOP = get_current_desktop_num()

        # Run join sequence on AFK desktop
        success = run_ps_join_workflow(config)

        if success:
            # Switch back to study desktop after spawn
            print(f"\n[Action] Server joined! Returning to Study Desktop #{CURRENT_MAIN_DESKTOP}...")
            switch_to_desktop_num(CURRENT_MAIN_DESKTOP)

            # Wait until Server Uptime hits 10:00 (Merchant Spawn)
            # Spawn occurs 3.5 minutes after our join offset (13m 30s - 10m 00s = 3m 30s)
            merchant_wait = (3 * 60) + 30 - config.get("merchant_alarm_lead_seconds", 15)
            print(f"[Timer] Merchant spawns in ~3.5m. Waiting for alarm on Desktop #{CURRENT_MAIN_DESKTOP}...")
            time.sleep(max(1, merchant_wait))

            # Trigger Alarm & Toast Notification
            print("\n🔔 [ALARM] GPO Merchant Has Spawned! (Server Uptime 10:00)")
            send_toast("GPO Merchant Active!", "Merchant spawned! Stock #1 ready. Stock #2 in 3 minutes.")
            play_alarm()

            # Switch view to AFK desktop for stock check
            print(f"[Action] Switching to AFK Desktop #{afk_desktop_num} to check stocks...")
            switch_to_desktop_num(afk_desktop_num)
            focus_roblox_window()

            print("\n------------------------------------------------------")
            print(" [INSTRUCTIONS] ")
            print(" 1. Locate Merchant & check Stock #1.")
            print(" 2. At Global Refresh (Server Uptime 13:00), check Stock #2.")
            print(" 3. Press F8 to close Roblox & return to your Study Desktop!")
            print(" 4. (Or wait for 5-minute auto-kill timeout).")
            print("------------------------------------------------------")

            # Wait for user F8 hotkey or 5-minute timeout
            afk_timeout = config.get("afk_timeout_seconds", 300)
            start_check_time = time.time()

            while not CYCLE_FINISHED and not EMERGENCY_STOP:
                if time.time() - start_check_time > afk_timeout:
                    print("\n[System] 5-minute AFK timeout reached! Force closing Roblox...")
                    force_kill_roblox()
                    switch_to_desktop_num(CURRENT_MAIN_DESKTOP)
                    break
                time.sleep(1)

        # Prepare for next 30-minute cycle
        next_refresh_time += refresh_cycle_seconds
        print("\n[System] Cycle completed. Calibrating next 30-minute refresh window...")

if __name__ == "__main__":
    main()
