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
        return pyvda.get_current_desktop().number
    except Exception:
        return 1

def switch_to_desktop_num(num):
    try:
        desktops = pyvda.get_desktops()
        for d in desktops:
            if d.number == num:
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

def focus_roblox_window():
    try:
        windows = gw.getWindowsWithTitle("Roblox")
        if windows:
            rbox = windows[0]
            if rbox.isMinimized:
                rbox.restore()
            rbox.activate()
            time.sleep(0.5)
            return True
    except Exception:
        pass
    return False

def find_image_on_screen(image_name, confidence=0.8, timeout=90):
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
            return (center_x, center_y)
            
        time.sleep(1)
        
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

def run_ps_join_workflow(config):
    afk_desktop = config.get("afk_desktop_index", 2)
    ps_code = config.get("gpo_ps_code", "")
    place_id = config.get("roblox_place_id", "1730877806")
    coords = config.get("coords", {})

    print(f"\n[Action] Switching to AFK Virtual Desktop #{afk_desktop}...")
    switch_to_desktop_num(afk_desktop)

    # 1. Pre-flight cleanup
    force_kill_roblox()
    time.sleep(1.5)

    # 2. Browserless Launch via roblox://
    print("[Action] Launching Roblox GPO via roblox:// protocol...")
    os.startfile(f"roblox://placeId={place_id}")

    # 3. Dynamic Wait for Main Menu PS Button (if present/configured)
    print("[System] Checking for Private Server Main Menu button (assets/ps_button.png)...")
    ps_btn_pos = find_image_on_screen("ps_button.png", confidence=config.get("confidence", 0.8), timeout=15)
    if not ps_btn_pos and coords.get("ps_button"):
        ps_btn_pos = (coords["ps_button"]["x"], coords["ps_button"]["y"])

    if ps_btn_pos:
        focus_roblox_window()
        print(f"[Action] DirectInput Clicking Main Menu PS Button at {ps_btn_pos}...")
        pydirectinput.click(ps_btn_pos[0], ps_btn_pos[1])
        time.sleep(1.5)

    # 4. Dynamic Wait for PS Code Box (on PS Page)
    print("[System] Waiting for PS Code box (assets/ps_box.png)...")
    ps_pos = find_image_on_screen("ps_box.png", confidence=config.get("confidence", 0.8), timeout=90)
    
    if not ps_pos and coords.get("ps_box"):
        ps_pos = (coords["ps_box"]["x"], coords["ps_box"]["y"])
        
    if not ps_pos:
        print("[!] Timeout waiting for PS Code box. Retrying cycle...")
        return False

    focus_roblox_window()
    print(f"[Action] DirectInput Clicking PS Code Box at {ps_pos}...")
    pydirectinput.click(ps_pos[0], ps_pos[1])
    time.sleep(0.5)
    
    print("[Action] Pasting PS Code...")
    enter_ps_code(ps_code)
    pydirectinput.press('enter')
    time.sleep(2.0)

    # 4. Mode Selection: Regular Button
    print("[System] Waiting for 'Regular' mode button (assets/regular_button.png)...")
    reg_pos = find_image_on_screen("regular_button.png", confidence=config.get("confidence", 0.8), timeout=90)
    
    if not reg_pos and coords.get("regular_button"):
        reg_pos = (coords["regular_button"]["x"], coords["regular_button"]["y"])

    if reg_pos:
        print(f"[Action] DirectInput Clicking 'Regular' button at {reg_pos}...")
        pydirectinput.click(reg_pos[0], reg_pos[1])
        time.sleep(2.0)

    # 5. Sea Selection: First Sea Button
    print("[System] Waiting for 'First Sea' button (assets/first_sea.png)...")
    sea_pos = find_image_on_screen("first_sea.png", confidence=config.get("confidence", 0.8), timeout=90)
    
    if not sea_pos and coords.get("first_sea_button"):
        sea_pos = (coords["first_sea_button"]["x"], coords["first_sea_button"]["y"])

    if sea_pos:
        print(f"[Action] DirectInput Clicking 'First Sea' button at {sea_pos}...")
        pydirectinput.click(sea_pos[0], sea_pos[1])

    # 6. Server HUD Verification (Bottom-Right Clock)
    print("[System] Waiting for server spawn HUD clock (assets/server_time.png)...")
    hud_pos = find_image_on_screen("server_time.png", confidence=0.7, timeout=120)
    
    if not hud_pos:
        print("[!] HUD clock not detected within 120s, but proceeding with spawn buffer...")
    else:
        print(" [✓] In-Game Server Spawn Verified!")

    return True

def get_countdown_input():
    print("\n------------------------------------------------------")
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
        print("[!] ERROR: Administrator rights required for DirectInput & Keybind hooks!")
        print("    Please re-run your terminal as Administrator!")
        print("    Command: uv run python main.py")
        input("\nPress ENTER to exit...")
        sys.exit(1)

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

    wiki_seconds_left = get_countdown_input()
    
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

        wait_time = launch_time - current_time
        CURRENT_MAIN_DESKTOP = get_current_desktop_num()
        launch_str = datetime.datetime.fromtimestamp(launch_time).strftime('%I:%M:%S %p')

        print(f"\n[Timer] Waiting {int(wait_time//60)}m {int(wait_time%60)}s on Desktop #{CURRENT_MAIN_DESKTOP}.")
        print(f"[Timer] Roblox AFK join will trigger at exactly {launch_str}.")

        # Sleep on main study desktop
        time.sleep(max(1, wait_time))

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
