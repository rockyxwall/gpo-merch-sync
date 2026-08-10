import os
import sys
import json
import time
import ctypes
import subprocess

try:
    import cv2
    import numpy as np
    import keyboard
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

def select_and_crop_one_click(window_title, prompt_msg, save_filename):
    print(f"\n[+] Step: {prompt_msg}")
    print("    =======================================================")
    print("    --> Switch to the Roblox window now.")
    print("    --> Press [ F4 ] on your keyboard to take the screenshot!")
    print("    =======================================================")
    
    while keyboard.is_pressed('f4'):
        time.sleep(0.05)
        
    keyboard.wait('f4')
    print("    [✓] F4 pressed! Capturing screen...")
    time.sleep(0.2)
    
    screenshot = ImageGrab.grab()
    screenshot_path = os.path.join(ASSETS_DIR, "_temp_setup.png")
    screenshot.save(screenshot_path)
    
    img = cv2.imread(screenshot_path)
    if img is None:
        print("[!] Selection canceled or image failed to load.")
        return None

    h_img, w_img = img.shape[:2]
    top_border = 50
    display_img = cv2.copyMakeBorder(
        img, top_border, 0, 0, 0,
        cv2.BORDER_CONSTANT, value=[25, 25, 25]
    )
    
    instruction_line1 = f"1-CLICK TARGET: {prompt_msg}"
    instruction_line2 = "LEFT-CLICK on the target element -> Press ENTER/SPACE to confirm | Press 'c' or ESC to retry"
    
    cv2.putText(display_img, instruction_line1, (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(display_img, instruction_line2, (15, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    click_point = {"x": None, "y": None}
    canvas = display_img.copy()

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click_point["x"] = x
            click_point["y"] = y
            np.copyto(canvas, display_img)
            cv2.circle(canvas, (x, y), 12, (0, 0, 255), 2)
            cv2.line(canvas, (x - 20, y), (x + 20, y), (0, 255, 0), 2)
            cv2.line(canvas, (x, y - 20), (x, y + 20), (0, 255, 0), 2)
            cv2.imshow(window_title, canvas)

    cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
    cv2.imshow(window_title, canvas)
    cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 1)
    cv2.setMouseCallback(window_title, on_mouse)

    print(f"    -> LEFT-CLICK directly on '{prompt_msg}' on screen.")
    print("    -> Press SPACE or ENTER to confirm the selection.")
    
    while True:
        key = cv2.waitKey(50) & 0xFF
        if key == 13 or key == 32:  # ENTER or SPACE
            if click_point["x"] is not None:
                break
            else:
                print("    [!] Please left-click on the screen target first!")
        elif key == 27 or key == ord('c'):  # ESC or c
            cv2.destroyAllWindows()
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
            return None

    cv2.destroyAllWindows()

    click_x = click_point["x"]
    click_y = click_point["y"]

    real_center_x = click_x
    real_center_y = max(0, click_y - top_border)

    crop_w, crop_h = 80, 40
    x1 = max(0, real_center_x - (crop_w // 2))
    y1 = max(0, real_center_y - (crop_h // 2))
    x2 = min(w_img, x1 + crop_w)
    y2 = min(h_img, y1 + crop_h)

    cropped = img[y1:y2, x1:x2]
    target_path = os.path.join(ASSETS_DIR, save_filename)
    cv2.imwrite(target_path, cropped)

    print(f"    [Success] Saved 1-Click coordinate ({real_center_x}, {real_center_y}) & template '{save_filename}'!")

    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)

    return {"x": real_center_x, "y": real_center_y, "bbox": [x1, y1, x2 - x1, y2 - y1]}

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
    print("    Waiting for Roblox to open and GPO to load into the Main Menu...")
    input("\n[!] Press ENTER once GPO has fully loaded and the Main Menu is visible on your screen... ")

    def capture_with_retry(window_title, prompt_msg, save_filename, coord_key):
        target_path = os.path.join(ASSETS_DIR, save_filename)
        if os.path.exists(target_path):
            print(f"\n[✓] Existing template image found: 'assets/{save_filename}'")
            skip = input(f"    Keep existing template and skip capturing '{save_filename}'? (y/n) [y]: ").strip().lower()
            if skip != 'n':
                print(f"    [Skipped] Preserved existing '{save_filename}'.")
                existing_coord = config.get("coords", {}).get(coord_key)
                if existing_coord:
                    return existing_coord
                img = cv2.imread(target_path)
                if img is not None:
                    h, w = img.shape[:2]
                    return {"x": w // 2, "y": h // 2, "bbox": [0, 0, w, h]}
                return True

        while True:
            res = select_and_crop_one_click(window_title, prompt_msg, save_filename)
            if res is not None:
                return res
            retry = input("  [?] Selection was canceled or invalid. Retry this step? (y/n) [y]: ").strip().lower()
            if retry == 'n':
                return None

    # Step 1: Main Menu Private Server Button
    ps_btn_res = capture_with_retry(
        "1. Select GPO Main Menu PS Button",
        "Select the 'Private Server' button on the Main Menu",
        "ps_button.png",
        "ps_button"
    )
    if ps_btn_res and ps_btn_res is not True:
        config["coords"]["ps_button"] = ps_btn_res

    # Transition 1 -> 2: Open Private Server Page
    print("\n-----------------------------------------------------------------------")
    print(" [Action Required]")
    print(" 1. Click the 'Private Server' button in GPO to open the Private Server page.")
    print(" 2. Wait for the Private Server Code input box to appear on screen.")
    print("-----------------------------------------------------------------------")
    input("Press ENTER once the Private Server Code input box is visible on screen... ")

    # Step 2: Private Server Code Input Box (on PS Page)
    ps_res = capture_with_retry(
        "2. Select GPO PS Code Input Box",
        "Select the Private Server Code text input box (on the PS page)",
        "ps_box.png",
        "ps_box"
    )
    if ps_res and ps_res is not True:
        config["coords"]["ps_box"] = ps_res

    # Transition 2 -> 3: Enter PS Code & Open Game Mode Menu
    ps_code_val = config.get('gpo_ps_code', '')
    print("\n-----------------------------------------------------------------------")
    print(" [Action Required]")
    print(" 1. Click inside the Private Server Code text box in GPO to select it.")
    print(f" 2. Type/paste your Private Server Code: '{ps_code_val}' & press ENTER.")
    print(" 3. Wait for GPO to open the Mode Selection screen (showing 'Regular').")
    print("-----------------------------------------------------------------------")
    input("Press ENTER once the 'Regular' game mode button is visible on your screen... ")

    # Step 3: Regular Mode Button
    reg_res = capture_with_retry(
        "3. Select 'Regular' Mode Button",
        "Select the 'Regular' game mode button",
        "regular_button.png",
        "regular_button"
    )
    if reg_res and reg_res is not True:
        config["coords"]["regular_button"] = reg_res

    # Transition 3 -> 4: Select Game Mode
    print("\n-----------------------------------------------------------------------")
    print(" [Action Required]")
    print(" 1. Click the 'Regular' game mode button in GPO.")
    print(" 2. Wait for GPO to open the Sea Selection screen (showing 'First Sea').")
    print("-----------------------------------------------------------------------")
    input("Press ENTER once the 'First Sea' button is visible on your screen... ")

    # Step 4: First Sea Button
    sea_res = capture_with_retry(
        "4. Select 'First Sea' Button",
        "Select the 'First Sea' button",
        "first_sea.png",
        "first_sea_button"
    )
    if sea_res and sea_res is not True:
        config["coords"]["first_sea_button"] = sea_res

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
