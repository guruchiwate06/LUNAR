<div align="center">

# 🌙 LUNAR

**Local Universal Neural Automation & Robotics Copilot**

*A local-first, privacy-respecting AI desktop assistant with an animated floating astronaut mascot, built on Ollama, CustomTkinter, and PyAutoGUI.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black.svg)](https://ollama.com/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![Tests](https://img.shields.io/badge/Tests-47%20Passed-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

</div>

## 📖 Overview

**LUNAR** is a local-first desktop automation copilot that connects natural language instructions to direct operating system actions. Powered by local LLMs via [Ollama](https://ollama.com/) (default: `qwen2.5-coder:7b`), LUNAR runs locally without sending your desktop activities, typed text, or conversation history to external third-party cloud APIs.

LUNAR offers three flexible interfaces:
1. **Animated Floating Desktop Pet (PyQt6)**: A borderless, draggable, cartoon moon-robot that floats on your desktop with per-pixel alpha transparency, physics bobbing, autonomous blinking/looking/turning, and sleep/wake cycles.
2. **Dedicated Windowed GUI**: A standalone dark-mode desktop application built with `CustomTkinter`.
3. **Terminal / CLI Mode**: A command-line interface with interactive authorization prompts.

---

## 🏛️ Architecture & Project Structure

The codebase is built with a centralized security and tool-execution core (`lunar_core.py`) shared by all user interfaces:

```
LUNAR/
├── lunar_core.py            # Central security validation, dynamic app resolution, & Ollama engine
├── assistant.py             # Mode 1: Interactive CLI with terminal authorization
├── gui_assistant.py         # Mode 2: CustomTkinter windowed desktop application
├── pet.py                   # Mode 3: PyQt6 animated desktop pet widget (per-pixel transparency)
├── lunar_desktop_pet.py     # Desktop pet launcher entry point (calls pet.py)
├── prepare_sprites.py       # Sprite splitter, background removal, & 512x512 canvas pipeline
├── requirements.txt         # Core dependencies with version constraints
├── start_pet.bat            # Silent background launcher
├── PET_README.md            # Desktop pet user manual & Windows startup setup
├── .gitignore               # Clean repository exclusions (pycache, pytest, venvs, local configs)
├── LUNAR.spec               # PyInstaller build specification
├── sprite_sheet.png         # Source cartoon moon-robot sprite sheet
├── sprites_preview.png      # 8-pose cutout quality preview grid
├── sprites/                 # 8 standardized transparent 512x512 PNG sprites
├── tests/                   # Automated pytest test suite (47 passed)
│   ├── test_validation.py      # URL, typing, and command safety validation tests
│   ├── test_tool_execution.py  # Subprocess, timeout, dynamic discovery, and injection prevention
│   ├── test_parsing.py         # Tool call extraction and fallback JSON parsing tests
│   ├── test_ollama.py          # Ollama health checks and error recovery tests
│   ├── test_fast_intent.py     # Deterministic zero-lag intent matching tests
│   └── test_concurrency.py     # Thread synchronization and request locking tests
└── README.md                # Comprehensive documentation and manual
```

---

## 🛡️ Security & Safeguards

LUNAR interacts directly with the operating system, which requires strict defensive safeguards:

1. **Strictly Blocked Dangerous Commands**:
   - Destructive commands such as disk formatting (`format`, `mkfs`), recursive forced root deletion (`rm -rf /`, `rmdir /s`), malicious download pipes (`curl ... | bash`), and encoded PowerShell payloads are strictly blocked before execution.
2. **Human-in-the-Loop Confirmation**:
   - **CLI Mode**: Prompts the user with `Allow execution? (y/N)` before executing shell actions or launching applications.
   - **GUI & Avatar Modes**: Uses thread-safe modal confirmation dialogs on the main UI thread to authorize sensitive or destructive actions before execution.
3. **Command Injection Prevention**:
   - Application launching validates targets against known app mappings and clean identifier formats, avoiding unsafe `shell=True` argument concatenation.
4. **URL & Scheme Whitelisting**:
   - Web navigation strictly permits only `http://` and `https://` URLs with valid hostnames. Prohibited protocols (`file:///`, `javascript:`, `data:`, `ms-*`) are rejected.
5. **Fail-Safe Synthetic Typing**:
   - PyAutoGUI screen-corner fail-safe is enabled: slamming the mouse cursor into any screen corner immediately aborts typing.
   - Includes a 2-second buffer delay to focus the target window, text validation, and a clipboard fallback for non-ASCII keyboard layouts.
6. **Execution Timeouts & Error Codes**:
   - Shell commands enforce a 30-second timeout to prevent hanging processes.
   - Non-zero process exit codes and stderr are reported to the user without falsely claiming success.

---

## 🚀 Getting Started

### 1. Prerequisites

* **Python 3.10+**: Ensure Python is installed and accessible in your terminal.
* **Ollama**: Download and install from [ollama.com](https://ollama.com/).
* **Pull the Model**:
  ```powershell
  ollama pull qwen2.5-coder:7b
  ```
  *(For lower-spec systems running without a dedicated GPU, `qwen2.5-coder:1.5b` or `qwen2.5:3b` can be used for significantly faster CPU inference).*
* **Start Ollama**:
  ```powershell
  ollama serve
  ```

---

### 2. Installation

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/guruchiwate06/LUNAR.git
   cd LUNAR
   ```

2. **Create and activate a virtual environment:**
   * **Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

---

## 🎮 Launch Modes

### Mode 1: Floating Desktop Avatar (Recommended)
Launches the persistent desktop mascot in the bottom-right corner of your screen. Click the avatar to toggle the chat drawer; drag it anywhere on your desktop.

```powershell
python lunar_avatar_widget.py
```

### Mode 2: Dedicated Windowed GUI
Launches the standalone windowed CustomTkinter desktop interface with real-time status indicators.

```powershell
python gui_assistant.py
```

### Mode 3: Terminal / CLI Mode
Launches the terminal copilot with interactive authorization prompts.

```powershell
python assistant.py
```

---

## 🧪 Automated Testing

LUNAR includes a comprehensive automated test suite covering command validation, tool execution, injection prevention, Ollama health checking, tool call parsing, and concurrency synchronization:

```powershell
python -m pytest -v tests/
```

All 40 unit test cases mock external processes, Ollama responses, and desktop typing to ensure safe, deterministic execution without modifying your desktop.

---

## 🌐 Supported Operating Systems & Limitations

| Feature / OS | Windows | macOS | Linux |
|---|---|---|---|
| **CLI Mode** | Fully Supported | Fully Supported | Fully Supported |
| **Windowed GUI** | Fully Supported | Supported | Supported (X11 / Wayland) |
| **Avatar Mascot** | Supported with Transparency | Supported (Dark Window Frame) | Supported (Dark Window Frame) |
| **App Launcher** | Notepad, VS Code, Chrome, Edge, Calc | VS Code, Chrome, Safari, TextEdit | VS Code, Chrome, Firefox, Gedit |
| **Synthetic Typing** | Supported (PyAutoGUI + Clipboard) | Supported (Accessibility permissions required) | Supported (X11; Wayland requires xdotool / uinput) |

### Remaining Limitations & Considerations
* **Local-First Privileges**: LUNAR runs with the permissions of the current logged-in user. It is not sandboxed in an isolated container; user confirmations are the primary defense against unauthorized actions.
* **CPU vs GPU Inference**: When running without an NVIDIA GPU (`CUDA: False`), 7B models can take 10–25 seconds per query on CPU. For faster responses, use `qwen2.5-coder:1.5b`.
* **Transparency**: Desktop transparency (`-transparentcolor`) is a Windows-specific Tkinter API. On macOS and Linux, the avatar window uses a styled dark slate background.
* **macOS Keystroke Permissions**: macOS requires granting Accessibility permissions to your terminal or Python executable in *System Preferences > Privacy & Security > Accessibility* for PyAutoGUI typing to work.

---

## 🔧 Troubleshooting

* **"Cannot connect to Ollama server"**:
  Make sure Ollama is running in the background. Open a terminal and run `ollama serve`.
* **"Model 'qwen2.5-coder:7b' not found"**:
  Download the model by running `ollama pull qwen2.5-coder:7b`.
* **PyAutoGUI Typing Interrupted**:
  Moving the mouse cursor to any corner of your monitor activates the emergency fail-safe. Keep the mouse still or click into the target window during the 2-second buffer delay.
* **CustomTkinter Appearance on Linux**:
  If CustomTkinter throws display errors on headless or minimal Linux installations, ensure `python3-tk` and an active X11/Wayland display server are installed.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
