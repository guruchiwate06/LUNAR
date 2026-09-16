# LUNAR

LUNAR is an advanced, AI-powered Operating System automation assistant featuring a sleek Graphical User Interface (GUI) and an interactive virtual avatar. Built entirely to run locally utilizing the Ollama framework (e.g., `qwen2.5-coder:7b`), it serves as a privacy-focused copilot that helps manage your computer seamlessly.

With LUNAR, you can control your desktop through natural language conversations. Its core capabilities include:
- **OS Automation:** Executing native shell commands for file and directory management.
- **Application Control:** Launching desktop applications (e.g., VS Code, Chrome, Calculator) instantly.
- **Web Navigation:** Opening specific websites and platforms directly in your default browser.
- **Autonomous Typing:** Typing text directly into whichever desktop window currently has focus using `pyautogui`.

## Structure
- `assistant.py`: Core logic for the assistant.
- `gui_assistant.py`: Graphical user interface for LUNAR.
- `lunar_avatar_widget.py`: Avatar visualization component.

## Running Locally

### Prerequisites
Make sure you have Python installed. This project relies on local language models, so you need [Ollama](https://ollama.com/) installed and running locally.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/guruchiwate06/LUNAR.git
   cd LUNAR
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Execution

To run the full GUI assistant with the avatar representation, use:
```bash
python lunar_avatar_widget.py
```

To run the basic GUI assistant, use:
```bash
python gui_assistant.py
```

If you prefer the CLI version, run:
```bash
python assistant.py
```
