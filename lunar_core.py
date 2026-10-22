"""
LUNAR Core - Shared Security, Validation, and Tool Execution Engine
Provides centralized command validation, safe execution, Ollama integration,
and tool parsing for CLI, GUI, and Avatar widget interfaces.
"""

import os
import sys
import re
import shlex
import logging
import platform
import subprocess
import shutil
import json
import time
import urllib.parse
import webbrowser
from typing import Tuple, Optional, Dict, Any, Callable, List

# Configure module-level logger without logging sensitive user data
logger = logging.getLogger("LUNAR")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# PyAutoGUI import with fail-safe preservation
try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

try:
    import ollama
except ImportError:
    ollama = None

MODEL_NAME = "qwen2.5-coder:7b"
SYSTEM_OS = platform.system()  # 'Windows', 'Darwin', 'Linux'

# --- RESOURCE PATH RESOLUTION ---

def get_resource_path(relative_path: str) -> str:
    """Returns absolute path to resource, compatible with PyInstaller bundles and source execution."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)


# --- TOOL SCHEMAS FOR OLLAMA ---

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Executes a system shell command for file, directory, or diagnostic operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to execute (e.g., 'mkdir test', 'dir', 'ls')."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launches a desktop application executable (e.g., Notepad, VS Code, Chrome, Calculator).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name or identifier of the application (e.g., 'notepad', 'code', 'calc', 'chrome')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Opens a web URL directly in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The web URL to open (e.g., 'https://github.com', 'https://www.google.com')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_in_active_window",
            "description": "Types text directly into the currently focused desktop window using simulated keystrokes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The exact text string to type into the active target window."
                    }
                },
                "required": ["text"]
            }
        }
    }
]

# --- KNOWN APPLICATIONS ALLOWLIST & MAPPINGS ---

KNOWN_APPS: Dict[str, Dict[str, list]] = {
    "Windows": {
        "notepad": ["notepad.exe"],
        "calc": ["calc.exe"],
        "calculator": ["calc.exe"],
        "code": ["code.cmd", "code"],
        "vs code": ["code.cmd", "code"],
        "vscode": ["code.cmd", "code"],
        "chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "msedge": ["msedge.exe"],
        "explorer": ["explorer.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "mspaint": ["mspaint.exe"],
        "paint": ["mspaint.exe"],
        "taskmgr": ["taskmgr.exe"],
    },
    "Darwin": {
        "notepad": ["open", "-a", "TextEdit"],
        "textedit": ["open", "-a", "TextEdit"],
        "calc": ["open", "-a", "Calculator"],
        "calculator": ["open", "-a", "Calculator"],
        "code": ["open", "-a", "Visual Studio Code"],
        "vs code": ["open", "-a", "Visual Studio Code"],
        "vscode": ["open", "-a", "Visual Studio Code"],
        "chrome": ["open", "-a", "Google Chrome"],
        "safari": ["open", "-a", "Safari"],
        "terminal": ["open", "-a", "Terminal"],
    },
    "Linux": {
        "notepad": ["gedit"],
        "textedit": ["gedit"],
        "calc": ["gnome-calculator"],
        "calculator": ["gnome-calculator"],
        "code": ["code"],
        "vs code": ["code"],
        "vscode": ["code"],
        "chrome": ["google-chrome"],
        "firefox": ["firefox"],
        "terminal": ["x-terminal-emulator"],
    }
}

# Dangerous shell commands and patterns that are either strictly blocked or require sensitive approval
STRICTLY_BLOCKED_PATTERNS = [
    r"\bformat\b",
    r"\brmdir\s+/[sS]",
    r"\brm\s+-[rR]*[fF]",
    r"\bdel\s+/[fFqQsS]",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
    r"\bcurl\b.*\|\s*(?:bash|sh|cmd|powershell)",
    r"\bwget\b.*\|\s*(?:bash|sh|cmd|powershell)",
    r"\bpowershell\b.*-[eE](?:nc|ncodedcommand)?\b",
]

SENSITIVE_COMMAND_PATTERNS = [
    r"\bdel\b",
    r"\brm\b",
    r"\brmdir\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\breg\b",
    r"\bnet\s+user\b",
    r"\btaskkill\b",
    r"\bkill\b",
    r"\bpkill\b",
    r"\bchmod\b",
    r"\bchown\b",
]


# --- VALIDATION FUNCTIONS ---

def validate_url(url: str) -> Tuple[bool, str, str]:
    """
    Validates a URL for web navigation.
    Returns (is_valid, sanitized_url, error_message).
    Only http and https protocols are permitted; file://, javascript:, data: are rejected.
    """
    if not url or not isinstance(url, str):
        return False, "", "URL must be a non-empty string."

    url = url.strip()
    if not url:
        return False, "", "URL cannot be empty."

    # If scheme missing, default to https://
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        url = f"https://{url}"

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "", f"Prohibited URL scheme '{parsed.scheme}'. Only http and https are allowed."

        hostname = parsed.hostname
        if not hostname or len(hostname) < 3 or "." not in hostname and hostname != "localhost":
            return False, "", f"Invalid hostname in URL: '{hostname}'."

        return True, url, ""
    except Exception as e:
        return False, "", f"Malformed URL: {str(e)}"


def validate_command_safety(command: str) -> Tuple[bool, bool, str]:
    """
    Checks shell command safety.
    Returns (is_allowed, is_sensitive, reason).
    - If is_allowed is False, the command is strictly blocked for security.
    - If is_sensitive is True, explicit confirmation is mandatory before execution.
    """
    if not command or not isinstance(command, str):
        return False, False, "Command must be a non-empty string."

    cmd_clean = command.strip()
    if not cmd_clean:
        return False, False, "Command cannot be empty."

    # Check for strictly blocked patterns
    for pattern in STRICTLY_BLOCKED_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return False, False, f"Command contains strictly prohibited dangerous pattern matching '{pattern}'."

    # Check for sensitive patterns
    for pattern in SENSITIVE_COMMAND_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return True, True, f"Command contains potentially sensitive or destructive operation ('{pattern}')."

    return True, False, ""


def validate_typing_text(text: str) -> Tuple[bool, str, str]:
    """
    Validates text before typing into active windows.
    Returns (is_valid, sanitized_text, error_message).
    """
    if text is None or not isinstance(text, str):
        return False, "", "Typing input must be a string."

    if not text:
        return False, "", "Typing input cannot be empty."

    if len(text) > 4000:
        return False, "", "Typing input exceeds maximum allowed length of 4,000 characters."

    return True, text, ""


# --- TOOL EXECUTION IMPLEMENTATIONS ---

def execute_shell_command(
    command: str,
    confirm_callback: Optional[Callable[[str, str], bool]] = None,
    timeout: int = 30
) -> str:
    """
    Safely executes a system shell command with validation, optional user confirmation,
    and a strict timeout.
    confirm_callback should accept (action_description, details) and return True/False.
    """
    is_allowed, is_sensitive, reason = validate_command_safety(command)
    if not is_allowed:
        logger.warning(f"Blocked dangerous command: {command} - {reason}")
        return f"Security Error: Command blocked. {reason}"

    # Human-in-the-loop confirmation
    if confirm_callback is not None:
        prompt_desc = "Execute Shell Command"
        if is_sensitive:
            prompt_desc = "⚠️ SENSITIVE / DESTRUCTIVE Shell Command"
        
        allowed = confirm_callback(prompt_desc, command)
        if not allowed:
            return "Execution cancelled by user."

    try:
        # Execute with timeout
        # Note: on Windows native shell commands (dir, mkdir) require shell=True,
        # but the command has been validated and cleared via confirmation.
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            err_msg = stderr if stderr else stdout
            return f"Command exited with error code {result.returncode}:\n{err_msg if err_msg else 'Unknown command failure'}"

        output = stdout if stdout else stderr
        return output if output else "Command executed successfully with no terminal output."

    except subprocess.TimeoutExpired:
        return f"Command execution timed out after {timeout} seconds."
    except Exception as e:
        return f"Shell execution error: {str(e)}"


def find_system_executable(app_name: str) -> Optional[List[str]]:
    """
    Dynamically discovers the executable binary for an application name
    using system PATH and operating system application registries (zero hardcoding).
    Works automatically for Chrome, Edge, VS Code, Discord, Spotify, etc.
    """
    if not app_name or not isinstance(app_name, str):
        return None

    clean = app_name.strip()
    if clean.lower().endswith(".exe"):
        clean = clean[:-4]

    # 1. System PATH lookup via shutil.which
    found = shutil.which(clean) or shutil.which(f"{clean}.exe")
    if found:
        return [found]

    # 2. Dynamic lookup via Windows App Paths registry
    if SYSTEM_OS == "Windows":
        try:
            import winreg
            for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for sub_key in (
                    f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean}.exe",
                    f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean}",
                ):
                    try:
                        with winreg.OpenKey(root_key, sub_key) as key:
                            val, _ = winreg.QueryValueEx(key, "")
                            target = str(val).strip().strip('"')
                            if target and os.path.exists(target):
                                return [target]
                    except OSError:
                        pass
        except ImportError:
            pass

    # 3. macOS dynamic application bundle lookup
    elif SYSTEM_OS == "Darwin":
        for app_dir in ("/Applications", os.path.expanduser("~/Applications")):
            candidate = os.path.join(app_dir, f"{clean}.app")
            if os.path.exists(candidate):
                return ["open", "-a", candidate]

    # 4. Check alias mappings (e.g. 'vscode' -> 'code', 'calc' -> 'calc.exe')
    system_apps = KNOWN_APPS.get(SYSTEM_OS, {})
    if clean.lower() in system_apps:
        alias_target = system_apps[clean.lower()]
        if alias_target:
            resolved_alias = shutil.which(alias_target[0])
            if resolved_alias:
                return [resolved_alias] + alias_target[1:]
            return alias_target

    return None


def safe_launch_application(
    app_name: str,
    confirm_callback: Optional[Callable[[str, str], bool]] = None
) -> str:
    """
    Safely launches an application using dynamic discovery without hardcoded paths
    and without command injection vulnerabilities.
    """
    if not app_name or not isinstance(app_name, str):
        return "Error: App name must be a non-empty string."

    app_clean = app_name.lower().strip()
    if not app_clean:
        return "Error: App name cannot be empty."

    # Prevent shell injection characters if unmapped
    if any(ch in app_clean for ch in [';', '&', '|', '>', '<', '`', '$', '\n', '\r']):
        return "Security Error: App name contains invalid or potentially dangerous characters."

    # Dynamically discover executable across system PATH and OS registries
    cmd_args = find_system_executable(app_clean)

    # For unrecognized applications, require confirmation if callback provided
    if not cmd_args and confirm_callback is not None:
        allowed = confirm_callback("Launch Unrecognized Application", f"Application: {app_name}")
        if not allowed:
            return "Launch cancelled by user."

    try:
        if cmd_args:
            # Launch without shell=True wherever possible
            if SYSTEM_OS == "Windows":
                subprocess.Popen(cmd_args, shell=False)
            elif SYSTEM_OS == "Darwin":
                subprocess.Popen(cmd_args, shell=False)
            else:
                subprocess.Popen(cmd_args, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Application '{app_name}' launched successfully."
        else:
            # Fallback for Windows: attempt shell-registered invocation
            if SYSTEM_OS == "Windows":
                if not re.match(r'^[a-zA-Z0-9_\-\.\s]+$', app_name.strip()):
                    return f"Security Error: '{app_name}' is not recognized and contains unsupported characters."
                try:
                    os.startfile(app_clean)
                    return f"Application '{app_name}' launched successfully."
                except Exception:
                    subprocess.Popen(f'start "" "{app_name.strip()}"', shell=True)
                    return f"Application '{app_name}' launched."

            return f"Error: Application '{app_name}' was not found on this system."
    except FileNotFoundError:
        return f"Error: Application '{app_name}' was not found on this system."
    except Exception as e:
        return f"Failed to launch '{app_name}': {str(e)}"


def safe_open_web_page(url: str) -> str:
    """Validates and opens a web URL in the system browser."""
    is_valid, target_url, err = validate_url(url)
    if not is_valid:
        return f"Browser Error: {err}"

    try:
        opened = webbrowser.open(target_url)
        if opened:
            return f"Opened browser and navigated to: {target_url}"
        else:
            return f"Navigated to {target_url} (check your default browser)."
    except Exception as e:
        return f"Failed to open browser: {str(e)}"


def safe_type_text(text: str) -> str:
    """
    Types text into the active window with a delay buffer and error handling.
    PyAutoGUI fail-safe is preserved: slam mouse into any corner to abort.
    """
    if pyautogui is None:
        return "Error: PyAutoGUI is not installed or unavailable."

    is_valid, clean_text, err = validate_typing_text(text)
    if not is_valid:
        return f"Typing Error: {err}"

    time.sleep(2)  # Delay buffer allowing user to focus target window

    try:
        # First attempt standard write
        pyautogui.write(clean_text, interval=0.03)
        pyautogui.press('enter')
        return f"Successfully typed text into the active window."
    except pyautogui.FailSafeException:
        return "Aborted: PyAutoGUI FailSafe triggered by mouse movement to screen corner."
    except KeyError:
        # Character not mapped on keyboard layout: fallback to clipboard paste if possible
        try:
            import pyperclip
            pyperclip.copy(clean_text)
            pyautogui.hotkey('ctrl' if SYSTEM_OS != "Darwin" else 'command', 'v')
            pyautogui.press('enter')
            return f"Typed text into active window via clipboard fallback."
        except Exception as e:
            return f"Typing Error: Text contains unsupported keyboard characters: {str(e)}"
    except Exception as e:
        return f"Typing Error: {str(e)}"


# --- OLLAMA INTEGRATION & TOOL PARSING ---

def check_ollama_health(model_name: str = MODEL_NAME) -> Tuple[bool, str]:
    """
    Verifies that Ollama server is running and the specified model is installed.
    Returns (is_ready, message).
    """
    if ollama is None:
        return False, "Ollama Python library is not installed. Run 'pip install ollama'."

    try:
        model_list = ollama.list()
        # Parse installed models
        models = []
        if isinstance(model_list, dict) and "models" in model_list:
            models = [m.get("name", "") for m in model_list["models"]]
        elif hasattr(model_list, "models"):
            models = [getattr(m, "model", getattr(m, "name", "")) for m in model_list.models]

        # Check if requested model or matching prefix exists
        found = any(m.startswith(model_name) or model_name.startswith(m) for m in models)
        if not found and models:
            return True, f"Warning: Model '{model_name}' not found. Available models: {', '.join(models[:3])}"
        elif not found:
            return False, f"Ollama is running, but model '{model_name}' is not pulled. Run 'ollama pull {model_name}'."

        return True, f"Ollama is connected and model '{model_name}' is ready."
    except Exception as e:
        return False, f"Cannot connect to Ollama server at http://localhost:11434. Please start it with 'ollama serve'. Error: {str(e)}"


def parse_tool_call(response_msg: dict) -> Tuple[Optional[str], Optional[dict]]:
    """
    Robustly extracts and validates tool calls from Ollama response.
    Supports both native tool_calls structure and fallback JSON in text content.
    Returns (tool_name, tool_arguments_dict).
    """
    if not isinstance(response_msg, dict):
        return None, None

    # 1. Check native tool calls from Ollama
    tool_calls = response_msg.get("tool_calls")
    if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
        call = tool_calls[0]
        if isinstance(call, dict) and "function" in call:
            fn = call["function"]
            name = fn.get("name")
            args = fn.get("arguments", {})

            # In some Ollama versions arguments can be a JSON string
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            if isinstance(args, dict) and name in ("execute_command", "launch_app", "open_website", "type_in_active_window"):
                return name, args

    # 2. Fallback: Parse raw JSON inside content
    content = response_msg.get("content")
    if content and isinstance(content, str):
        name, args = extract_fallback_tool_from_text(content)
        if name and args is not None:
            return name, args

    return None, None


def extract_fallback_tool_from_text(text: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Carefully parses JSON tool call from raw text without executing arbitrary code.
    Validates tool names against allowed schemas.
    """
    if not text or "{" not in text or "}" not in text:
        return None, None

    try:
        # Find json bounds
        start = text.find("{")
        end = text.rfind("}") + 1
        json_str = text[start:end]
        data = json.loads(json_str)

        if not isinstance(data, dict):
            return None, None

        name = data.get("name")
        args = data.get("arguments", data.get("parameters", {}))

        if not isinstance(args, dict):
            # Sometimes arguments is stringified
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            else:
                args = {}

        allowed_tools = ["execute_command", "launch_app", "open_website", "type_in_active_window"]
        if name in allowed_tools and isinstance(args, dict):
            return name, args

    except Exception:
        pass

    return None, None


def dispatch_tool_call(
    tool_name: str,
    tool_args: dict,
    confirm_callback: Optional[Callable[[str, str], bool]] = None
) -> str:
    """Dispatches a validated tool call to the corresponding secure implementation."""
    if not isinstance(tool_args, dict):
        return f"Error: Tool arguments must be a dictionary. Got {type(tool_args).__name__}."

    if tool_name == "execute_command":
        cmd = tool_args.get("command")
        if not cmd or not isinstance(cmd, str):
            return "Error: Missing or invalid 'command' string argument."
        return execute_shell_command(cmd, confirm_callback=confirm_callback)

    elif tool_name == "launch_app":
        app = tool_args.get("app_name")
        if not app or not isinstance(app, str):
            return "Error: Missing or invalid 'app_name' string argument."
        return safe_launch_application(app, confirm_callback=confirm_callback)

    elif tool_name == "open_website":
        url = tool_args.get("url")
        if not url or not isinstance(url, str):
            return "Error: Missing or invalid 'url' string argument."
        return safe_open_web_page(url)

    elif tool_name == "type_in_active_window":
        text = tool_args.get("text")
        if text is None or not isinstance(text, str):
            return "Error: Missing or invalid 'text' string argument."
        return safe_type_text(text)

    return f"Error: Unsupported tool '{tool_name}'."


def clean_display_text(text: str) -> str:
    """Removes leaked tool call JSON, XML tags, or raw formatting from user-facing text."""
    if not text:
        return ""

    # Remove <think>...</think> and <tool_call>...</tool_call> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)

    stripped = text.strip()
    # If the text contains or is a tool call JSON object, filter it out
    if "{" in stripped and "}" in stripped:
        try:
            start = stripped.find("{")
            end = stripped.rfind("}") + 1
            json_str = stripped[start:end]
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and ("name" in parsed or "arguments" in parsed or "parameters" in parsed or "app_name" in parsed):
                remaining = (stripped[:start] + stripped[end:]).strip()
                return remaining
        except Exception:
            pass

    return text.strip()


def fast_match_intent(user_text: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Instantly detects common deterministic direct commands (open app, open website)
    without waiting for slow LLM inference on CPU.
    Returns (tool_name, tool_args) or (None, None).
    """
    if not user_text or not isinstance(user_text, str):
        return None, None

    text = user_text.lower().strip()
    # Strip leading polite words
    for filler in ["please ", "can you ", "could you ", "lunar "]:
        if text.startswith(filler):
            text = text[len(filler):].strip()

    # 1. App Launching direct patterns
    for prefix in ["open ", "launch ", "start ", "run "]:
        if text.startswith(prefix):
            target = text[len(prefix):].strip().rstrip(".!?,")

            known_names = {
                "chrome": "chrome",
                "google chrome": "chrome",
                "notepad": "notepad",
                "text editor": "notepad",
                "calc": "calc",
                "calculator": "calc",
                "code": "code",
                "vs code": "code",
                "vscode": "code",
                "visual studio code": "code",
                "edge": "edge",
                "msedge": "edge",
                "microsoft edge": "edge",
                "explorer": "explorer",
                "file explorer": "explorer",
                "files": "explorer",
                "cmd": "cmd",
                "terminal": "cmd" if SYSTEM_OS == "Windows" else "terminal",
                "powershell": "powershell",
                "paint": "paint",
                "mspaint": "paint",
                "taskmgr": "taskmgr",
                "task manager": "taskmgr",
            }
            if target in known_names:
                return "launch_app", {"app_name": known_names[target]}

            # Dynamically check if target is an installed application executable on the user's OS
            if find_system_executable(target):
                return "launch_app", {"app_name": target}

            popular_sites = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "github": "https://www.github.com",
                "reddit": "https://www.reddit.com",
                "twitter": "https://x.com",
                "x": "https://x.com",
                "gmail": "https://mail.google.com",
                "chatgpt": "https://chatgpt.com",
                "netflix": "https://www.netflix.com",
            }
            if target in popular_sites:
                return "open_website", {"url": popular_sites[target]}
            if "." in target and not target.endswith(".exe"):
                return "open_website", {"url": f"https://{target}" if not target.startswith("http") else target}

    # 2. Web navigation direct patterns
    for prefix in ["go to ", "visit ", "navigate to ", "browse to "]:
        if text.startswith(prefix):
            target = text[len(prefix):].strip().rstrip(".!?,")
            popular_sites = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "github": "https://www.github.com",
                "reddit": "https://www.reddit.com",
                "twitter": "https://x.com",
                "x": "https://x.com",
            }
            if target in popular_sites:
                return "open_website", {"url": popular_sites[target]}
            return "open_website", {"url": f"https://{target}" if not target.startswith("http") else target}

    return None, None

