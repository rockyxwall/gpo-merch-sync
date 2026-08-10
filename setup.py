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

def capture_coordinate_fast(step_num, title, coord_key, existing_coords):
    print(f"\n=======================================================")
    print(f" [Step {step_num}] {title}")
    print(f"  1. Switch to/hover mouse over '{title}' in Roblox.")
    print(f"  2. Press [ F4 ] to record position & capture template image.")
    print(f"=======================================================")

    current_coord = existing_coords.get(coord_key)
    template_path = os.path.join(ASSETS_DIR, f"{coord_key}.png")

    if current_coord and isinstance(current_coord, dict) and "x" in current_coord and "y" in current_coord and os.path.exists(template_path):
        print(f"  Existing coordinate: ({current_coord['x']}, {current_coord['y']})")
        print(f"  Existing image template: assets/{coord_key}.png")
        skip = input(f"  Keep existing configuration for '{coord_key}'? (y/n) [y]: ").strip().lower()
        if skip != 'n':
            print(f"  [✓] Preserved ({current_coord['x']}, {current_coord['y']}) & assets/{coord_key}.png")
            return current_coord

    while keyboard.is_pressed('f4'):
        time.sleep(0.05)

    print("  Waiting for [ F4 ] keypress...")
    while True:
        if keyboard.is_pressed('f4'):
            x, y = get_mouse_position()
            
            # Crop 120x60 ROI around mouse position for OpenCV template matching
            try:
                screen = ImageGrab.grab()
                left = max(0, x - 60)
                top = max(0, y - 30)
                right = min(screen.width, x + 60)
                bottom = min(screen.height, y + 30)
                
                crop_img = screen.crop((left, top, right, bottom))
                os.makedirs(ASSETS_DIR, exist_ok=True)
                crop_img.save(template_path)
                print(f"  [✓] Saved image recognition template: assets/{coord_key}.png")
            except Exception as e:
                print(f"  [!] Warning saving template image: {e}")

            print(f"  [✓] F4 Pressed! Recorded coordinate: ({x}, {y})")
            time.sleep(0.3)
            return {"x": x, "y": y}
        time.sleep(0.05)

def main():
    print("======================================================")
    print("   GPO Merch Sync - Fast 1-Click Setup Wizard 🏴‍☠️     ")
    print("======================================================")
    
    if not is_admin():
        print("[!] WARNING: Running without Administrator privileges.")
        print("    For best results, run in an Administrator terminal!")

    config = {
        "gpo_ps_code": "",
        "roblox_place_id": "1730877806",
        "afk_desktop_index": 2,
        "confidence": 0.8,
        "menu_timeout_seconds": 90,
        "merchant_alarm_lead_seconds": 15,
        "afk_timeout_seconds": 300,
        "calibrated_refresh_timestamp": 0,
        "coords": {
            "ps_button": None,
            "ps_box": None,
            "regular_button": None,
            "first_sea_button": None
        }
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

    # 4. Launch Roblox GPO
    place_id = config.get("roblox_place_id", "1730877806")
    print(f"\n[Action] Launching Grand Piece Online (Place ID: {place_id}) via roblox:// protocol...")
    os.startfile(f"roblox://placeId={place_id}")
    input("\n[!] Press 'F' key in GPO (or any key) to enter Main Menu, then press ENTER in this terminal... ")

    existing_coords = config.get("coords", {})

    # Step 1: Main Menu PS Button
    config["coords"]["ps_button"] = capture_coordinate_fast(1, "Main Menu 'Private Server' Button", "ps_button", existing_coords)

    input("\n[!] Click 'Private Server' in GPO, then press ENTER once the PS Code Box is visible... ")

    # Step 2: PS Code Input Box
    config["coords"]["ps_box"] = capture_coordinate_fast(2, "PS Code Text Input Box", "ps_box", existing_coords)

    ps_code_val = config.get('gpo_ps_code', '')
    print(f"\n[!] Click PS text box, paste code ('{ps_code_val}'), hit ENTER in GPO...")
    input("    Press ENTER once the 'Regular' game mode button is visible on screen... ")

    # Step 3: Regular Button
    config["coords"]["regular_button"] = capture_coordinate_fast(3, "'Regular' Game Mode Button", "regular_button", existing_coords)

    input("\n[!] Click 'Regular' in GPO, then press ENTER once 'First Sea' button is visible... ")

    # Step 4: First Sea Button
    config["coords"]["first_sea_button"] = capture_coordinate_fast(4, "'First Sea' Button", "first_sea_button", existing_coords)

    # Save config.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print("\n======================================================")
    print(" [✓] Fast Setup Complete!")
    print(f" [✓] Configuration saved to: {CONFIG_PATH}")
    print(f" [✓] Next Global Stock Refresh: {refresh_local_str}")
    print(" You can now run GPO Merch Sync using:")
    print("     uv run python main.py")
    print("======================================================")

if __name__ == "__main__":
    main()
