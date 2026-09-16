import os
import sys
import platform
import subprocess
import json
import time
import webbrowser
import threading
import pyautogui
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import ollama

MODEL_NAME = "qwen2.5-coder:7b"
pyautogui.FAILSAFE = True

# --- RESOURCE PATH HELPER (FOR PYINSTALLER & LOCAL DEV) ---
def get_resource_path(relative_path: str) -> str:
    """Gets absolute path to resources, working both in dev and inside PyInstaller .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# --- SYSTEM TOOL SCHEMAS & IMPLEMENTATIONS ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Executes shell commands (mkdir, dir, ls, etc.).",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launches desktop applications.",
            "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Opens URLs in the browser.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_in_active_window",
            "description": "Types text into active window.",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
        }
    }
]

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

# --- MAIN CONTROLLER & STANDING BOT AVATAR ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class StandingBotAvatar(tk.Tk):
    def __init__(self):
        super().__init__()

        # Avatar Window setup
        self.overrideredirect(True)       # Borderless
        self.attributes("-topmost", True)  # Always stay on top of desktop
        
        # Transparent background setup for Windows
        self.config(bg='gray')
        self.wm_attributes('-transparentcolor', 'gray')

        # Default position: Bottom-right corner
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.bot_x = screen_width - 120
        self.bot_y = screen_height - 180
        self.geometry(f"100x120+{self.bot_x}+{self.bot_y}")

        # Load Bot Image (With garbage collection retention fix)
        self.avatar_canvas = tk.Canvas(self, width=100, height=120, bg='gray', highlightthickness=0)
        self.avatar_canvas.pack()

        image_path = get_resource_path("bot_avatar.png")

        if os.path.exists(image_path):
            img = Image.open(image_path).convert("RGBA")
            img = img.resize((90, 110), Image.Resampling.LANCZOS)
            
            # Persistent references attached to self and canvas to prevent garbage collection
            self.bot_img = ImageTk.PhotoImage(img)
            self.canvas_img = self.avatar_canvas.create_image(50, 60, image=self.bot_img)
            self.avatar_canvas.image = self.bot_img 
        else:
            # Fallback graphic if image file is not found
            self.avatar_canvas.create_oval(20, 10, 80, 70, fill="#3B82F6", outline="white", width=2)
            self.avatar_canvas.create_text(50, 40, text="🌙", font=("Segoe UI", 24))
            self.avatar_canvas.create_rectangle(30, 75, 70, 110, fill="#1E293B", outline="white", width=2)

        # Interactivity Binds
        self.avatar_canvas.bind("<Button-1>", self.on_click)
        self.avatar_canvas.bind("<B1-Motion>", self.on_drag)

        # Initialize Chat Popup Widget (Hidden initially)
        self.popup_widget = LunarChatPopup(self)
        self.popup_widget.withdraw()

    def on_click(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.toggle_popup()

    def on_drag(self, event):
        x = self.winfo_x() + (event.x - self.drag_start_x)
        y = self.winfo_y() + (event.y - self.drag_start_y)
        self.geometry(f"+{x}+{y}")
        self.bot_x = x
        self.bot_y = y
        if self.popup_widget.winfo_viewable():
            self.popup_widget.position_next_to_bot()

    def toggle_popup(self):
        if self.popup_widget.winfo_viewable():
            self.popup_widget.withdraw()
        else:
            self.popup_widget.position_next_to_bot()
            self.popup_widget.deiconify()

# --- POPUP CHAT WIDGET ---
class LunarChatPopup(ctk.CTkToplevel):
    def __init__(self, parent_bot):
        super().__init__(parent_bot)
        self.bot = parent_bot

        self.title("LUNAR")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("320x440")

        # Top Drag & Close Bar
        self.top_bar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#1E1E1E")
        self.top_bar.pack(fill="x", side="top")

        self.title_label = ctk.CTkLabel(self.top_bar, text="🌙 LUNAR Assistant", font=("Segoe UI", 11, "bold"))
        self.title_label.pack(side="left", padx=10)

        self.close_btn = ctk.CTkButton(self.top_bar, text="✕", width=20, height=20, fg_color="transparent", hover_color="#C70039", command=self.withdraw)
        self.close_btn.pack(side="right", padx=5)

        # Chat Area
        self.chat_area = ctk.CTkTextbox(self, width=300, height=340, corner_radius=8, font=("Segoe UI", 11))
        self.chat_area.pack(padx=10, pady=5)
        self.chat_area.configure(state="disabled")

        # Entry Bar
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Ask LUNAR...", width=230, font=("Segoe UI", 11))
        self.entry.pack(side="left", padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.send_btn = ctk.CTkButton(self.input_frame, text="→", width=45, command=self.send_message)
        self.send_btn.pack(side="right")

        self.messages = [{
            "role": "system",
            "content": "Your name is LUNAR, an OS desktop assistant avatar. Execute actions via tools when requested."
        }]

    def position_next_to_bot(self):
        # Position popup widget to the left of the standing bot avatar
        popup_x = self.bot.bot_x - 330
        popup_y = self.bot.bot_y - 320
        self.geometry(f"+{max(10, popup_x)}+{max(10, popup_y)}")

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

            if response_msg.get("tool_calls"):
                call = response_msg["tool_calls"][0]["function"]
                tool_name = call["name"]
                tool_args = call["arguments"]
            elif response_msg.get("content"):
                tool_name, tool_args = self.extract_fallback_tool(response_msg["content"])

            if tool_name:
                result = ""
                if tool_name == "execute_command":
                    result = run_shell_command(tool_args.get("command"))
                elif tool_name == "launch_app":
                    result = launch_application(tool_args.get("app_name"))
                elif tool_name == "open_website":
                    result = open_web_page(tool_args.get("url"))
                elif tool_name == "type_in_active_window":
                    result = type_text(tool_args.get("text"))

                self.messages.append({"role": "tool", "content": result})

                final_res = ollama.chat(model=MODEL_NAME, messages=self.messages)
                bot_text = final_res["message"]["content"]
                self.messages.append(final_res["message"])
                self.after(0, lambda: self.append_chat("LUNAR", bot_text))
            else:
                self.after(0, lambda: self.append_chat("LUNAR", response_msg["content"]))

        except Exception as err:
            self.after(0, lambda: self.append_chat("Error", str(err)))

if __name__ == "__main__":
    app = StandingBotAvatar()
    app.mainloop()