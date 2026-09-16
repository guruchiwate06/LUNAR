import os
import platform
import subprocess
import json
import time
import webbrowser
import pyautogui
import ollama

MODEL_NAME = "qwen2.5-coder:7b"

# Enable PyAutoGUI fail-safe: move mouse to any screen corner to stop execution
pyautogui.FAILSAFE = True

# Define tool schemas for Ollama
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Executes a native system shell command (e.g., mkdir, touch, dir, ls) for file or directory management.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact OS shell command to run."
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
                        "description": "Common name of the app (e.g., 'notepad', 'code', 'chrome', 'calc')."
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
            "description": "Opens a web URL or platform directly in the browser (e.g., YouTube, Google).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full website URL or platform name (e.g., 'https://www.youtube.com')."
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
            "description": "Types text directly into whichever desktop window or application currently has focus using PyAutoGUI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The string to type out into the active text area."
                    }
                },
                "required": ["text"]
            }
        }
    }
]

# --- TOOL IMPLEMENTATIONS ---

def run_shell_command(command: str) -> str:
    print(f"\n[Action Request]: Execute Shell Command -> {command}")
    confirm = input("Allow execution? (y/n): ").strip().lower()
    if confirm != 'y':
        return "Execution cancelled by user."

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        return output if output else "Command executed successfully with no terminal output."
    except Exception as e:
        return f"Shell execution error: {str(e)}"

def launch_application(app_name: str) -> str:
    print(f"\n[Action Request]: Launch Application -> {app_name}")
    confirm = input(f"Allow opening '{app_name}'? (y/n): ").strip().lower()
    if confirm != 'y':
        return "Launch cancelled by user."

    system = platform.system()
    app = app_name.lower().strip()

    try:
        if system == "Windows":
            win_apps = {
                "notepad": "notepad.exe",
                "calculator": "calc.exe",
                "calc": "calc.exe",
                "vs code": "code",
                "vscode": "code",
                "code": "code",
                "chrome": "start chrome",
                "edge": "start msedge"
            }
            target = win_apps.get(app, app)
            subprocess.Popen(target, shell=True)

        elif system == "Darwin":  # macOS
            mac_apps = {"vs code": "Visual Studio Code", "vscode": "Visual Studio Code"}
            target = mac_apps.get(app, app)
            subprocess.Popen(["open", "-a", target])

        else:  # Linux
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return f"Application '{app_name}' launched."
    except Exception as e:
        return f"Failed to launch '{app_name}': {str(e)}"

def open_web_page(url: str) -> str:
    print(f"\n[Action Request]: Web Navigation -> {url}")
    target_url = url.strip()
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"https://{target_url}"

    try:
        webbrowser.open(target_url)
        return f"Opened browser and navigated to {target_url}."
    except Exception as e:
        return f"Failed to open browser: {str(e)}"

def type_text(text: str) -> str:
    print(f"\n[Action Request]: PyAutoGUI Typing -> '{text}'")
    print("Focus your target window now! Typing begins in 2 seconds...")
    time.sleep(2)

    try:
        pyautogui.write(text, interval=0.04)
        pyautogui.press('enter')
        return f"Successfully typed '{text}' into the focused window."
    except Exception as e:
        return f"GUI typing error: {str(e)}"

# --- PARSING AND ROUTING ---

def extract_tool_from_text(text: str):
    """Fallback JSON parser if model outputs raw tool call JSON inside content."""
    try:
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            json_str = text[start:end]
            data = json.loads(json_str)
            
            name = data.get("name")
            args = data.get("arguments", data.get("parameters", {}))

            if name == "execute_command":
                return "execute_command", args.get("command")
            if name == "launch_app":
                return "launch_app", args.get("app_name")
            if name == "open_website":
                return "open_website", args.get("url")
            if name == "type_in_active_window":
                return "type_in_active_window", args.get("text")
    except Exception:
        pass
    return None, None

def dispatch_tool(tool_type: str, arg: str) -> str:
    if tool_type == "execute_command":
        return run_shell_command(arg)
    elif tool_type == "launch_app":
        return launch_application(arg)
    elif tool_type == "open_website":
        return open_web_page(arg)
    elif tool_type == "type_in_active_window":
        return type_text(arg)
    return "Unknown tool type."

# --- MAIN ASSISTANT LOOP ---

def start_assistant():
    print("=== Integrated Local OS Assistant Initialized ===")
    
    system_prompt = (
        "You are an OS automation agent. Perform tasks using tools:\n"
        "- Use 'execute_command' for shell files/folders.\n"
        "- Use 'launch_app' to launch local software executables.\n"
        "- Use 'open_website' for navigating to websites or web platforms like YouTube.\n"
        "- Use 'type_in_active_window' to type keyboard text into active windows."
    )
    
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        messages.append({"role": "user", "content": user_input})

        response = ollama.chat(model=MODEL_NAME, messages=messages, tools=tools)
        response_msg = response["message"]
        messages.append(response_msg)

        tool_type = None
        tool_arg = None

        # 1. Check native tool calls from Ollama
        if response_msg.get("tool_calls"):
            for call in response_msg["tool_calls"]:
                tool_type = call["function"]["name"]
                args = call["function"]["arguments"]
                
                if tool_type == "execute_command":
                    tool_arg = args.get("command")
                elif tool_type == "launch_app":
                    tool_arg = args.get("app_name")
                elif tool_type == "open_website":
                    tool_arg = args.get("url")
                elif tool_type == "type_in_active_window":
                    tool_arg = args.get("text")

        # 2. Fallback check for raw JSON inside text content
        if not tool_type and response_msg.get("content"):
            tool_type, tool_arg = extract_tool_from_text(response_msg["content"])

        # Run tool if extracted
        if tool_type and tool_arg:
            tool_result = dispatch_tool(tool_type, tool_arg)
            messages.append({"role": "tool", "content": tool_result})

            final_response = ollama.chat(model=MODEL_NAME, messages=messages)
            print(f"\nAssistant: {final_response['message']['content']}")
            messages.append(final_response["message"])
        else:
            print(f"\nAssistant: {response_msg['content']}")

if __name__ == "__main__":
    start_assistant()