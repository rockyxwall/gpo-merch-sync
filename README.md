# GPO Merch Sync 🏴‍☠️

An automated, non-disruptive Roblox **Grand Piece Online (GPO) Traveling Merchant AFK Looper** designed specifically to run on a background **Windows Virtual Desktop** while you study, watch anime, or browse the web on your primary workspace.

---

## 🌟 Key Features

1. **Dual-Workspace / Virtual Desktop Automation**:
   - Runs Roblox on **Virtual Desktop 2** (AFK workspace).
   - Automatically switches view back to **Virtual Desktop 1** (Study workspace) while waiting for the server spawn.
   - Zero mouse or keyboard interference with your main screen.
2. **Browserless Roblox Launch (`roblox://` Protocol)**:
   - Bypasses Chrome/Edge entirely by calling Windows protocol handler `roblox://placeId=1730877806`.
   - Saves RAM, loads faster, and eliminates browser tab clutter.
3. **2 Stocks per Server Guarantee (Math Verified)**:
   - Calibrates launch timing at `T - 13m 30s` before Global Refresh.
   - Spawns at Server Uptime `00:00`.
   - Merchant spawns at Server Uptime `10:00` (**Stock #1**).
   - Global Refresh occurs at Server Uptime `13:00` (**Stock #2**).
   - Despawns at Server Uptime `20:00`. Total playtime 21.5m, leaving 8.5m of clean downtime with zero cycle overlap.
4. **Roblox Hyperion DirectInput & Anti-Cheat Fixes**:
   - Uses `pydirectinput` for low-level DirectX scancodes.
   - Uses `pyperclip` clipboard pasting (`Ctrl+V`) for instant, error-free Private Server code input.
5. **Dynamic 90s Image Recognition & HUD Clock Sync**:
   - Uses OpenCV template matching (`cv2`) with 90s dynamic wait loops for background Roblox updates.
   - Detects the bottom-right server time HUD (`assets/server_time.png`) to eliminate local clock desync.
6. **Background Hotkeys & Alarm Alerts**:
   - Plays an audio chime 🔔 and sends a Windows Toast notification when Merchant spawns.
   - **`F8`**: Finish stock check, force close Roblox (`taskkill`), and switch back to Desktop 1.
   - **`F6`**: Emergency force-stop kill switch.
   - **5-Minute AFK Timeout**: Auto-kills Roblox if you are away or asleep.

---

## 🔒 Privacy & Open-Source Security

`gpo-merch-sync` is built with open-source privacy in mind:
- **`config.json` is git-ignored**: Your personal GPO Private Server code and local screen coordinates are never committed to GitHub.
- **`config.example.json`**: Included as a clean template for first-time configuration.

---

## 📋 Requirements

- **OS**: Windows 10 or Windows 11
- **Virtual Desktop**: At least 2 Virtual Desktops enabled (press `Win + Ctrl + D` in Windows to create a new Virtual Desktop).
- **Python Package Manager**: `uv` (Fast Python package runner)
- **Privileges**: Terminal must be run **As Administrator** (required for `keyboard` hooks & DirectInput scancodes).

---

## 🚀 Quick Start Guide

### Step 1: Install Dependencies using `uv`
Clone the repository and run setup:
```powershell
# Open an Administrator PowerShell or Command Prompt
uv run python setup.py
```

### Step 2: 1-Click Interactive Setup (`setup.py`)
1. Enter your **GPO Private Server Code** when prompted.
2. Enter your AFK Virtual Desktop number (default: `2`).
3. The wizard will launch Roblox GPO to the main menu.
4. An OpenCV crop window will appear for 4 target UI elements:
   - **PS Code Input Box** (`assets/ps_box.png`)
   - **"Regular" Mode Button** (`assets/regular_button.png`)
   - **"First Sea" Button** (`assets/first_sea.png`)
   - **Bottom-Right Server Time Clock** (`assets/server_time.png`)
5. Simply click and drag a bounding box over each target area and press `ENTER`.
6. Your configuration is automatically saved into `config.json` (git-ignored) and `assets/`!

---

### Step 3: Run GPO Merch Sync (`main.py`)

```powershell
# Run in Administrator PowerShell
uv run python main.py
```

1. Look at the Discord Stock Tracker bot timer.
2. Enter the remaining **minutes** and **seconds** until the next Global Stock Refresh.
3. The script will calculate the precise launch window and manage Virtual Desktops automatically:
   - Launches GPO on **Virtual Desktop 2**.
   - Types PS code & enters First Sea.
   - Verifies server spawn via bottom-right clock.
   - **Switches view back to Virtual Desktop 1** so you can study/watch anime!
   - Chimes an alarm 🔔 & sends a Windows Toast when Merchant spawns at Server Uptime `10:00`.
   - Switches view to Desktop 2 for stock checks.
   - Press **`F8`** to close Roblox & return to Desktop 1!

---

## 🎮 Keybind Controls

| Hotkey | Action |
| :--- | :--- |
| **`F8`** | Finish cycle: Force closes Roblox (`taskkill`) and switches view back to Desktop 1 immediately. |
| **`F6`** | Emergency Stop: Kills Roblox and terminates the Python script immediately. |
| **5m Timeout** | Auto-kills Roblox and switches back to Desktop 1 if `F8` is not pressed within 5 minutes after alarm. |

---

## 📂 Project Structure

```
gpo-merch-sync/
├── .gitignore           # Git ignore rules (config.json, assets/*.png, .venv)
├── LICENSE              # MIT License
├── config.example.json  # Open-source template configuration
├── config.json          # Local config (Stores PS Code, Virtual Desktop index, coords)
├── setup.py             # 1-Click OpenCV ROI bounding-box capture wizard
├── main.py              # Core AFK looper script (Admin elevated, pyvda, pydirectinput)
├── requirements.txt     # Dependency list (pydirectinput, pyvda, opencv, pyperclip, keyboard)
└── assets/              # Template images (ps_box.png, regular_button.png, first_sea.png, server_time.png)
```

---

## ⚙️ Configuration (`config.json`)

```json
{
  "gpo_ps_code": "YOUR_PS_CODE_HERE",
  "roblox_place_id": "1730877806",
  "afk_desktop_index": 2,
  "confidence": 0.8,
  "menu_timeout_seconds": 90,
  "merchant_alarm_lead_seconds": 15,
  "afk_timeout_seconds": 300,
  "coords": {
    "ps_box": { "x": 960, "y": 400 },
    "regular_button": { "x": 960, "y": 500 },
    "first_sea_button": { "x": 960, "y": 600 },
    "server_time": { "x": 1800, "y": 1000 }
  }
}
```

---

## ❓ Frequently Asked Questions (FAQ)

#### Q: How does browserless launch work?
Roblox registers the `roblox://` protocol on Windows. Calling `roblox://placeId=1730877806` opens `RobloxPlayerBeta.exe` directly without launching Chrome or Edge!

#### Q: Will it interfere with my homework or anime on Desktop 1?
No! Image recognition and input clicking take place **only when Desktop 2 is active**. Once spawned into First Sea, the script automatically switches your view back to Desktop 1 while it waits for the 10-minute Merchant spawn.

#### Q: What if Roblox has an update?
`main.py` uses dynamic 90-second wait loops for image matching (`cv2`). If Roblox takes 30 seconds to download an update before showing the main menu, the script waits dynamically instead of failing.

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](file:///e:/lazyman/rockyxwall/02_Codeing/01_Github/gpo-merchant-ps/LICENSE) for details.
