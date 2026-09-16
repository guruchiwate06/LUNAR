import os
import platform
import subprocess
import json
import time
import webbrowser
import threading
import pyautogui
import customtkinter as ctk
import ollama

MODEL_NAME = "qwen2.5-coder:7b"
pyautogui.FAILSAFE = True

# --- SYSTEM TOOL SCHEMAS ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Executes shell commands (mkdir, dir, ls, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launches desktop applications (Notepad, VS Code, Chrome, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Opens URLs directly in the web browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_in_active_window",
            "description": "Types text into the active window using PyAutoGUI.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            }
        }
    }
]

# --- TOOL IMPLEMENTATIONS ---
def run_shell_command(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return res.stdout if res.stdout else (res.stderr if res.stderr else "Done.")
    except Exception as e:
        return f"Error: {e}"

def launch_application(app):
    sys_name = platform.system()
    app_lower = app.lower().strip()
    try:
        if sys_name == "Windows":
            apps = {"notepad": "notepad.exe", "calc": "calc.exe", "vs code": "code", "code": "code", "chrome": "start chrome"}
            subprocess.Popen(apps.get(app_lower, app_lower), shell=True)
        elif sys_name == "Darwin":
            subprocess.Popen(["open", "-a", app])
        else:
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched {app}."
    except Exception as e:
        return f"Launch failed: {e}"

def open_web_page(url):
    target = url if url.startswith("http") else f"https://{url}"
    webbrowser.open(target)
    return f"Opened {target}"

def type_text(text):
    time.sleep(2)
    pyautogui.write(text, interval=0.04)
    pyautogui.press('enter')
    return f"Typed: {text}"

# --- DESKTOP WIDGET UI CLASS ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FloatingAssistantWidget(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configurations
        self.title("LUNAR")
        self.geometry("380x520+1000+150") # Width x Height + X_pos + Y_pos
        self.attributes("-topmost", True)  # Always stay on top of other apps
        self.overrideredirect(False)       # Standard modern borders

        # Top Bar Title
        self.title_label = ctk.CTkLabel(self, text="LUNAR WELCOMES YOU!", font=("Segoe UI", 14, "bold"))
        self.title_label.pack(pady=(10, 5))

        # Chat Area Scrollable
        self.chat_area = ctk.CTkTextbox(self, width=350, height=390, corner_radius=10, font=("Segoe UI", 12))
        self.chat_area.pack(padx=10, pady=5)
        self.chat_area.configure(state="disabled")

        # Input Frame
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="HUKUM MERE AAKA...", width=270)
        self.entry.pack(side="left", padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.send_btn = ctk.CTkButton(self.input_frame, text="Send", width=65, command=self.send_message)
        self.send_btn.pack(side="right")

        # Chat Memory
        self.messages = [{
    "role": "system",
    "content": "Your name is LUNAR, a desktop OS assistant widget. Execute system, file, browser, and typing tasks via tools when requested."
}]

    def append_chat(self, sender, text):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"{sender}: {text}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def send_message(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.append_chat("You", user_text)
        self.messages.append({"role": "user", "content": user_text})

        # Process in thread so GUI doesn't freeze during LLM inference
        threading.Thread(target=self.process_ai_request).start()

    def extract_fallback_tool(self, content):
        try:
            if "{" in content and "}" in content:
                s = content.find("{")
                e = content.rfind("}") + 1
                data = json.loads(content[s:e])
                return data.get("name"), data.get("arguments", data.get("parameters", {}))
        except Exception:
            pass
        return None, None

    def process_ai_request(self):
        try:
            response = ollama.chat(model=MODEL_NAME, messages=self.messages, tools=tools)
            response_msg = response["message"]
            self.messages.append(response_msg)

            tool_name = None
            tool_args = {}

            # Parse tool calls
            if response_msg.get("tool_calls"):
                call = response_msg["tool_calls"][0]["function"]
                tool_name = call["name"]
                tool_args = call["arguments"]
            elif response_msg.get("content"):
                tool_name, tool_args = self.extract_fallback_tool(response_msg["content"])

            # Execute Tool Action
            if tool_name:
                result = ""
                if tool_name == "execute_command":
                    cmd = tool_args.get("command")
                    self.after(0, lambda: self.append_chat("System", f"Running command: `{cmd}`"))
                    result = run_shell_command(cmd)

                elif tool_name == "launch_app":
                    app = tool_args.get("app_name")
                    self.after(0, lambda: self.append_chat("System", f"Launching: {app}"))
                    result = launch_application(app)

                elif tool_name == "open_website":
                    url = tool_args.get("url")
                    self.after(0, lambda: self.append_chat("System", f"Opening: {url}"))
                    result = open_web_page(url)

                elif tool_name == "type_in_active_window":
                    txt = tool_args.get("text")
                    self.after(0, lambda: self.append_chat("System", f"Typing in 2s: '{txt}'"))
                    result = type_text(txt)

                self.messages.append({"role": "tool", "content": result})

                # Follow-up response
                final_res = ollama.chat(model=MODEL_NAME, messages=self.messages)
                bot_text = final_res["message"]["content"]
                self.messages.append(final_res["message"])
                self.after(0, lambda: self.append_chat("Assistant", bot_text))

            else:
                self.after(0, lambda: self.append_chat("Assistant", response_msg["content"]))

        except Exception as err:
            self.after(0, lambda: self.append_chat("Error", str(err)))

if __name__ == "__main__":
    app = FloatingAssistantWidget()
    app.mainloop()