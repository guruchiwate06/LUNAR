<div align="center">

<img src="bot_avatar.png" alt="LUNAR Avatar" width="180" />

# 🌙 LUNAR

**Local Universal Neural Automation & Robotics Assistant**

*A privacy-first, fully local AI desktop copilot with an interactive floating avatar, built on Ollama and CustomTkinter.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black.svg)](https://ollama.com/)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://customtkinter.tomschimansky.com/)
[![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

---

</div>

## 📖 Overview

**LUNAR** is an autonomous, privacy-focused Operating System assistant designed to bridge natural language instructions with direct OS automation. Running 100% locally via the [Ollama](https://ollama.com/) engine (using models like `qwen2.5-coder:7b`), LUNAR requires zero external API keys and never sends telemetry or sensitive desktop data to third-party clouds.

Whether you prefer a minimalist terminal interface, a dedicated windowed dashboard, or a futuristic floating desktop avatar that lives on your screen, LUNAR provides seamless desktop automation at your fingertips.

---

## ✨ Key Features

- 🤖 **Interactive Standing Avatar Widget**:
  - Always-on-top, borderless floating avatar that sits in the corner of your screen.
  - Transparent background support on Windows.
  - Click to toggle the chat drawer; drag-and-drop to position anywhere on your desktop.
- 🖥️ **Full Graphical Dashboard**:
  - Dark-mode GUI crafted with `CustomTkinter`.
  - Non-blocking asynchronous threaded inference prevents UI freezing during complex model generation.
- ⚡ **Autonomous OS Tool Calling**:
  - **Shell Command Execution (`execute_command`)**: Native system commands for folder and file manipulation (`mkdir`, `dir`, `ls`, etc.).
  - **App Launcher (`launch_app`)**: Opens system applications (VS Code, Chrome, Notepad, Calculator, Edge, etc.) across Windows, macOS, and Linux.
  - **Web Navigation (`open_website`)**: Instantly launches and navigates to URLs or popular platforms in your default browser.
  - **Synthetic Typing (`type_in_active_window`)**: Simulates realistic human keystrokes directly into active target windows using `pyautogui`.
- 🔒 **Safety & Failsafes**:
  - **PyAutoGUI Failsafe**: Slam the mouse cursor into any corner of your monitor to instantly abort automated mouse/keyboard actions.
  - **Human-in-the-Loop Safeguard**: CLI mode prompts for explicit user confirmation before executing native shell commands or launching binaries.
  - **Resilient Function Parsing**: Handles both Ollama native structured tool calls and raw JSON output fallbacks.

---

## 🏛️ Project Architecture

```
LUNAR/
├── bot_avatar.png           # Avatar asset for standing desktop widget
├── assistant.py             # CLI mode with human-in-the-loop approvals
├── gui_assistant.py         # Dedicated CustomTkinter windowed app
├── lunar_avatar_widget.py   # Floating desktop avatar with expandable chat
├── requirements.txt         # Core Python dependencies
├── .gitignore               # Git ignore patterns for clean version control
└── README.md                # Documentation and project manual
```

---

## 🚀 Getting Started

### 1. Prerequisites

1. **Python 3.10+**: Ensure Python is installed and added to your `PATH`.
2. **Ollama**: Download and install Ollama from [ollama.com](https://ollama.com/).
3. **Pull the AI Model**:
   LUNAR is optimized for `qwen2.5-coder:7b` for precise tool calling, but works with any Ollama model supporting function calling.
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
4. **Start the Ollama Server**:
   Ensure Ollama is running in the background:
   ```bash
   ollama serve
   ```

---

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/guruchiwate06/LUNAR.git
   cd LUNAR
   ```

2. **Create and activate a virtual environment:**
   - **Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎮 Usage Modes

LUNAR can be launched in three different interfaces depending on your workflow:

### Mode 1: Floating Desktop Avatar (Recommended)
Launches the persistent, interactive desktop mascot in the bottom-right corner of your screen. Click the avatar to expand the conversation drawer, or drag it anywhere.

```bash
python lunar_avatar_widget.py
```

### Mode 2: Dedicated Windowed GUI
Launches a standalone windowed CustomTkinter desktop interface with conversation logging.

```bash
python gui_assistant.py
```

### Mode 3: Terminal / CLI Mode
Launches a command-line interface with interactive safety confirmations (`y/n`) before executing shell operations.

```bash
python assistant.py
```

---

## 🛠️ Tool Calling Capabilities

| Tool | Trigger Intent | Example Prompts |
|---|---|---|
| `execute_command` | Filesystem & Shell tasks | *"Create a folder named ProjectAlpha and list files"* |
| `launch_app` | System Applications | *"Open VS Code"*, *"Launch calculator"* |
| `open_website` | Web Browsing | *"Go to github.com"*, *"Open YouTube"* |
| `type_in_active_window` | Keystroke simulation | *"Type 'Hello World' in my editor"* |

---

## ⚙️ Configuration & Model Customization

To change the underlying model, update `MODEL_NAME` at the top of the respective script:

```python
MODEL_NAME = "qwen2.5-coder:7b"  # e.g., "llama3.1:8b", "mistral-nemo", "phi3"
```

Make sure the selected model has been pulled locally (`ollama pull <model_name>`).

---

## 🛡️ Safety & Fail-Safe Tips

- **Emergency Exit**: If automated typing or mouse movements run wild, move your mouse cursor aggressively to **any of the four screen corners**. PyAutoGUI fail-safe will abort execution immediately.
- **Focus Delay**: When triggering `type_in_active_window`, LUNAR provides a **2-second delay buffer** before starting to type, allowing you to click into your target input field or document.

---

## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
