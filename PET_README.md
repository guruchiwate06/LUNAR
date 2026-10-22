# 🌙 LUNAR Desktop Pet Widget (PyQt6 Animated Pet)

A lightweight, animated cartoon moon-robot desktop pet built with **PyQt6**, featuring true per-pixel transparency, hardware-accelerated smooth animations, interactive physics, and lifelike autonomous behaviors.

---

## 🎨 Features

- **Per-Pixel Transparency**: Frameless, transparent floating widget with zero white or black edge halos.
- **Taskbar Hidden**: Operates as a clean desktop companion without cluttering the Windows taskbar.
- **Draggable & Persistent**: Drag anywhere with the left mouse button. Automatically saves its screen coordinates in `pet_position.json` across sessions.
- **Autonomous Lifelike Animations**:
  - **Idle Bob**: Smooth sine-wave floating bob, alternating `float_up` and `float_down` sprites based on physics velocity.
  - **Blink**: Natural periodic blinking every 3 to 7 seconds.
  - **Look Around**: Inquisitive looking behavior every 10 to 18 seconds.
  - **Turn**: Brief playful turn animation.
  - **Happy Bounce**: Excited energetic bounce for ~2 seconds when clicked.
  - **Sleep**: Automatically drifts to sleep after 60 seconds of inactivity with gentle breathing motion. Click wakes it up into a happy bounce!
- **Context Menu**: Right-click anytime for options:
  - *Sleep*
  - *Wake*
  - *Always on Top* (Toggle)
  - *Quit*

---

## 📦 Requirements & Installation

1. Install all dependencies from `requirements.txt`:
   ```powershell
   pip install PyQt6 Pillow rembg onnxruntime
   ```

2. (Optional) Re-generate or customize sprites from `sprite_sheet.png`:
   ```powershell
   python prepare_sprites.py
   ```
   This automatically crops all 8 poses, applies neural background removal via `rembg`, strips floating sparkles, stars, and symbols, and centers each sprite onto a uniform 512x512 transparent canvas.

---

## 🚀 How to Run

### Option 1: Run with Python
```powershell
python pet.py
```

### Option 2: Silent Background Mode (No Terminal Window)
Double-click `start_pet.bat` or run:
```powershell
pythonw pet.py
```

---

## ⚙️ How to Start Automatically on Windows Startup

To have your moon-robot pet launch automatically whenever your computer boots:

### Method A: Automated PowerShell Setup (Recommended)
Open PowerShell in this folder and run:
```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\LunarPet.lnk")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = """$((Get-Item .).FullName)\pet.py"""
$Shortcut.WorkingDirectory = "$((Get-Item .).FullName)"
$Shortcut.Save()
Write-Host "Startup shortcut created successfully!"
```

### Method B: Manual Shortcut Placement
1. Press `Win + R`, type `shell:startup`, and press **Enter**.
2. Right-click inside the folder, select **New > Shortcut**.
3. In the location box, enter:
   ```text
   pythonw.exe "f:\02.Projects\LUNAR\pet.py"
   ```
4. Click **Next**, name the shortcut `Lunar Pet`, and click **Finish**.
5. Right-click the newly created shortcut, select **Properties**, and set **Start in** to:
   ```text
   f:\02.Projects\LUNAR
   ```

---

## 🛠️ Configuration Constants (Top of `pet.py`)

You can customize the pet's size and physical behavior by editing the top of `pet.py`:

```python
SPRITE_HEIGHT = 210       # On-screen height of the sprite in pixels
BOB_SPEED = 0.05          # Speed of the floating bob (radians/frame)
BOB_HEIGHT = 11           # Maximum vertical amplitude of the bob in pixels
SLEEP_TIMEOUT = 60.0      # Seconds of inactivity before sleeping
FPS = 60                  # Frame rate for silky-smooth animations
```
