import os
import sys
import json
import time
import ctypes
import datetime

try:
    import keyboard
    import pydirectinput
    from PIL import ImageGrab
except ImportError:
    print("[!] Dependencies missing. Please run using uv:")
    print("    uv run python setup.py")
    sys.exit(1)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def get_mouse_position():
    try:
        class POINT(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)
    except Exception:
        pos = pydirectinput.position()
        return int(pos[0]), int(pos[1])

def capture_image_template(step_num, title, template_filename, hint_instruction):
    print(f"\n=======================================================")
    print(f" [Step {step_num}/5] Capture '{title}' Image Template")
    print(f"  Instructions:")
    print(f"   1. {hint_instruction}")
    print(f"   2. Hover mouse over the center of '{title}'.")
    print(f"   3. Press [ F4 ] to capture image template.")
    print(f"=======================================================")

    template_path = os.path.join(ASSETS_DIR, template_filename)

    if os.path.exists(template_path):
        print(f"  Existing image template found: assets/{template_filename}")
        skip = input(f"  Keep existing template for '{title}'? (y/n) [y]: ").strip().lower()
        if skip != 'n':
            print(f"  [✓] Preserved assets/{template_filename}")
            return True

    while keyboard.is_pressed('f4'):
        time.sleep(0.05)

    print("  Waiting for [ F4 ] keypress...")
    while True:
        if keyboard.is_pressed('f4'):
            x, y = get_mouse_position()
            
            # Crop 120x60 ROI centered around mouse position for OpenCV template matching
            try:
                screen = ImageGrab.grab()
                left = max(0, x - 60)
                top = max(0, y - 30)
                right = min(screen.width, x + 60)
                bottom = min(screen.height, y + 30)
                
                crop_img = screen.crop((left, top, right, bottom))
                os.makedirs(ASSETS_DIR, exist_ok=True)
                crop_img.save(template_path)
                print(f"  [✓] Successfully captured & saved template: assets/{template_filename}")
            except Exception as e:
                print(f"  [!] Error capturing image template: {e}")
                return False

            time.sleep(0.3)
            return True
        time.sleep(0.05)

def main():
    print("======================================================")
    print("   GPO Merch Sync - 100% Vision Setup Wizard 🏴‍☠️    ")
    print("======================================================")
    
    if not is_admin():
        print("[!] WARNING: Running without Administrator privileges.")
        print("    For best results, run in an Administrator terminal!")

    config = {
        "gpo_ps_code": "",
        "roblox_place_id": "1730877806",
        "afk_desktop_index": 2,
        "confidence": 0.7,
        "menu_timeout_seconds": 90,
        "merchant_alarm_lead_seconds": 15,
        "afk_timeout_seconds": 300,
        "calibrated_refresh_timestamp": 0
    }
    
    example_config_path = os.path.join(os.path.dirname(__file__), "config.example.json")
    if os.path.exists(example_config_path):
        try:
            with open(example_config_path, "r") as f:
                config.update(json.load(f))
        except Exception:
            pass

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config.update(json.load(f))
        except Exception:
            pass

    current_ps = config.get('gpo_ps_code', '')
    if current_ps == "YOUR_PS_CODE_HERE":
        current_ps = ""

    # 1. Prompt for PS Code
    if current_ps:
        print(f"\nExisting GPO Private Server Code: '{current_ps}'")
        keep_ps = input("Keep existing Private Server Code? (y/n) [y]: ").strip().lower()
        if keep_ps != 'n':
            print(f" [✓] Preserved Private Server Code: '{current_ps}'")
        else:
            ps_input = input("Enter new GPO Private Server Code: ").strip()
            if ps_input:
                config["gpo_ps_code"] = ps_input
    else:
        ps_input = input("\nEnter your GPO Private Server Code: ").strip()
        if ps_input:
            config["gpo_ps_code"] = ps_input

    # 2. Virtual Desktop setup
    current_desktop = config.get('afk_desktop_index', 2)
    print("\n[Virtual Desktop Setup]")
    print(" Hint: Press Win + Ctrl + D in Windows to create a new Virtual Desktop if needed.")
    print(f"Existing Virtual Desktop for Roblox AFK: #{current_desktop}")
    keep_desktop = input(f"Keep existing Virtual Desktop #{current_desktop}? (y/n) [y]: ").strip().lower()
    if keep_desktop != 'n':
        print(f" [✓] Preserved Virtual Desktop: #{current_desktop}")
    else:
        desktop_input = input(f"Enter new Virtual Desktop number for Roblox AFK [Default 2]: ").strip()
        if desktop_input.isdigit():
            config["afk_desktop_index"] = int(desktop_input)

    # 3. Stock Tracker Restock Time Calculation
    print("\n------------------------------------------------------")
    print(" [Global Stock Refresh Calibration]")
    calibrated_ts = config.get("calibrated_refresh_timestamp", 0)
    now_ts = time.time()
    
    use_existing_ts = False
    if calibrated_ts > now_ts:
        seconds_remaining = calibrated_ts - now_ts
        mins_r = int(seconds_remaining // 60)
        secs_r = int(seconds_remaining % 60)
        refresh_local_str = datetime.datetime.fromtimestamp(calibrated_ts).strftime('%I:%M:%S %p')
        print(f" Saved Calibration Found: Next Refresh at {refresh_local_str} ({mins_r}m {secs_r}s remaining)")
        keep_ts = input(" Keep existing calibration from config? (y/n) [y]: ").strip().lower()
        if keep_ts != 'n':
            use_existing_ts = True
            print(f" [✓] Preserved Next Global Stock Refresh: {refresh_local_str}")

    if not use_existing_ts:
        print(" Look at the Discord Stock Tracker bot.")
        try:
            mins_left = int(input(" Enter remaining MINUTES until Global Stock Refresh: ").strip())
            secs_left = int(input(" Enter remaining SECONDS until Global Stock Refresh: ").strip())
        except ValueError:
            print("[!] Invalid input. Defaulting to 15m 00s.")
            mins_left, secs_left = 15, 0

        refresh_ts = now_ts + (mins_left * 60) + secs_left
        config["calibrated_refresh_timestamp"] = refresh_ts
        refresh_local_str = datetime.datetime.fromtimestamp(refresh_ts).strftime('%I:%M:%S %p')
        print(f" [✓] Calibrated! Next Global Stock Refresh at: {refresh_local_str}")
    print("------------------------------------------------------")

    # 4. Launch Roblox GPO & Guide 5 Image Captures
    place_id = config.get("roblox_place_id", "1730877806")
    print(f"\n[Action] Launching Grand Piece Online (Place ID: {place_id}) via roblox:// protocol...")
    os.startfile(f"roblox://placeId={place_id}")
    input("\n[!] Press ENTER once GPO splash screen is visible on your screen... ")

    # Step 1: GPO Logo / Splash Title
    capture_image_template(
        1, "GPO Splash Screen Logo", "gpo_logo.png",
        "Make sure GPO title splash screen is visible."
    )

    print("\n[Action] Transitioning to GPO Main Menu...")
    input("[!] Press 'F' key in GPO to open the Main Menu, then press ENTER in this terminal... ")

    # Step 2: Main Menu PS Button
    capture_image_template(
        2, "Main Menu 'Private Server' Button", "ps_button.png",
        "Make sure the Main Menu is visible on screen."
    )

    input("\n[!] Click 'Private Server' in GPO, then press ENTER once the PS Code Box is visible... ")

    # Step 3: PS Code Box
    capture_image_template(
        3, "PS Code Text Input Box", "ps_box.png",
        "Make sure the PS Code input box modal is open on screen."
    )

    ps_code_val = config.get('gpo_ps_code', '')
    print(f"\n[!] Click PS text box, paste code ('{ps_code_val}'), hit ENTER in GPO...")
    input("    Press ENTER once the 'Regular' game mode button is visible on screen... ")

    # Step 4: Regular Button
    capture_image_template(
        4, "'Regular' Game Mode Button", "regular_button.png",
        "Make sure the Game Mode selection screen is visible."
    )

    input("\n[!] Click 'Regular' in GPO, then press ENTER once 'First Sea' button is visible... ")

    # Step 5: First Sea Button
    capture_image_template(
        5, "'First Sea' Button", "first_sea_button.png",
        "Make sure the Sea selection screen is visible."
    )

    # Save config.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print("\n======================================================")
    print(" [✓] 100% Vision Setup Complete!")
    print(f" [✓] Configuration saved to: {CONFIG_PATH}")
    print(f" [✓] Image Templates Saved to: {ASSETS_DIR}/")
    print(" You can now test the looper using:")
    print("     uv run python debug_join.py")
    print("     uv run python main.py")
    print("======================================================")

if __name__ == "__main__":
    main()
