import os
import sys
import json
import time
import ctypes
import subprocess

try:
    import cv2
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

def ensure_assets_dir():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)

def select_and_crop(window_title, prompt_msg, save_filename):
    print(f"\n[+] Step: {prompt_msg}")
    print("    Taking a screenshot of your screen in 3 seconds... Switch to the Roblox window now if needed!")
    for i in range(3, 0, -1):
        print(f"    {i}...")
        time.sleep(1)
    
    screenshot = ImageGrab.grab()
    screenshot_path = os.path.join(ASSETS_DIR, "_temp_setup.png")
    screenshot.save(screenshot_path)
    
    img = cv2.imread(screenshot_path)
    print("    -> Drag a bounding box over the target area using your mouse.")
    print("    -> Press SPACE or ENTER to confirm the selection.")
    print("    -> Press 'c' to cancel and re-try.")
    
    roi = cv2.selectROI(window_title, img, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()
    
    x, y, w, h = [int(v) for v in roi]
    
    if w == 0 or h == 0:
        print("[!] Selection canceled or invalid width/height. Please try again.")
        return None
    
    # Save cropped image template
    cropped = img[y:y+h, x:x+w]
    target_path = os.path.join(ASSETS_DIR, save_filename)
    cv2.imwrite(target_path, cropped)
    
    center_x = x + (w // 2)
    center_y = y + (h // 2)
    print(f"    [Success] Saved '{save_filename}'! Center coordinate: ({center_x}, {center_y})")
    
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)
        
    return {"x": center_x, "y": center_y, "bbox": [x, y, w, h]}

def main():
    print("======================================================")
    print("   GPO Merch Sync - 1-Click Setup Wizard 🏴‍☠️           ")
    print("======================================================")
    
    if not is_admin():
        print("[!] WARNING: Running without Administrator privileges.")
        print("    For best results, run in an Administrator terminal!")
    
    ensure_assets_dir()
    
    # Load existing config or fallback to config.example.json / default
    config = {
        "gpo_ps_code": "",
        "roblox_place_id": "1730877806",
        "afk_desktop_index": 2,
        "confidence": 0.8,
        "menu_timeout_seconds": 90,
        "merchant_alarm_lead_seconds": 15,
        "afk_timeout_seconds": 300,
        "coords": {}
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

    # Prompt for PS Code
    ps_input = input(f"\nEnter your GPO Private Server Code [{current_ps}]: ").strip()
    if ps_input:
        config["gpo_ps_code"] = ps_input
    elif current_ps:
        config["gpo_ps_code"] = current_ps

    print("\n[Virtual Desktop Setup]")
    print(" Hint: Press Win + Ctrl + D in Windows to create a new Virtual Desktop if you haven't already.")
    desktop_input = input(f"Enter the Virtual Desktop number to use for Roblox AFK [Default {config.get('afk_desktop_index', 2)}]: ").strip()
    if desktop_input.isdigit():
        config["afk_desktop_index"] = int(desktop_input)

    place_id = config.get("roblox_place_id", "1730877806")
    print(f"\n[Action] Launching Grand Piece Online (Place ID: {place_id}) via roblox:// protocol to load main menu...")
    os.startfile(f"roblox://placeId={place_id}")
    print("Waiting 12 seconds for Roblox to launch...")
    time.sleep(12)

    # Capture 1: PS Box
    ps_res = select_and_crop("1. Crop GPO PS Code Input Box", "Select the Private Server Code text input box", "ps_box.png")
    if ps_res:
        config["coords"]["ps_box"] = ps_res

    # Capture 2: Regular Mode Button
    reg_res = select_and_crop("2. Crop 'Regular' Mode Button", "Select the 'Regular' game mode button", "regular_button.png")
    if reg_res:
        config["coords"]["regular_button"] = reg_res

    # Capture 3: First Sea Button
    sea_res = select_and_crop("3. Crop 'First Sea' Button", "Select the 'First Sea' button", "first_sea.png")
    if sea_res:
        config["coords"]["first_sea_button"] = sea_res

    # Capture 4: Bottom-Right Server Time HUD
    print("\n[Action] Please click into GPO First Sea game server now to display the bottom-right server clock!")
    input("Press ENTER once you are spawned into the First Sea world and see the bottom-right server time... ")
    
    hud_res = select_and_crop("4. Crop Bottom-Right Server Time Clock", "Select the Server Time indicator in the bottom-right corner", "server_time.png")
    if hud_res:
        config["coords"]["server_time"] = hud_res

    # Save to config.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print("\n======================================================")
    print(" [✓] Setup Complete!")
    print(f" [✓] Configuration saved to: {CONFIG_PATH}")
    print(f" [✓] Template images saved to: {ASSETS_DIR}")
    print(" You can now run GPO Merch Sync using:")
    print("     uv run python main.py")
    print("======================================================")

if __name__ == "__main__":
    main()
