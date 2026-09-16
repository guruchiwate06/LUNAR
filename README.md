# LUNAR

LUNAR is an AI-powered assistant with a graphical user interface (GUI) and avatar representation.

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
