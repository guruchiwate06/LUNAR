"""
LUNAR - Dedicated Windowed GUI Assistant
CustomTkinter desktop interface with thread-safe inference,
GUI security confirmations, and system automation.
"""

import threading
import tkinter.messagebox as mb
import customtkinter as ctk
import ollama

from lunar_core import (
    MODEL_NAME,
    TOOL_SCHEMAS,
    check_ollama_health,
    parse_tool_call,
    dispatch_tool_call,
    fast_match_intent,
    clean_display_text,
    extract_fallback_tool_from_text,
    logger
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class FloatingAssistantWidget(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.is_running = True
        self.is_processing = False

        # Window Configurations
        self.title("LUNAR")
        self.geometry("400x560+950+120")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Header Title
        self.title_label = ctk.CTkLabel(
            self,
            text="🌙 LUNAR Copilot",
            font=("Segoe UI", 15, "bold")
        )
        self.title_label.pack(pady=(10, 2))

        # Status Badge
        self.status_label = ctk.CTkLabel(
            self,
            text="Checking system status...",
            font=("Segoe UI", 10),
            text_color="#9CA3AF"
        )
        self.status_label.pack(pady=(0, 6))

        # Chat Area
        self.chat_area = ctk.CTkTextbox(
            self,
            width=370,
            height=410,
            corner_radius=10,
            font=("Segoe UI", 11)
        )
        self.chat_area.pack(padx=10, pady=5)
        self.chat_area.configure(state="disabled")

        # Input Frame
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Enter your command or request...",
            width=290,
            font=("Segoe UI", 11)
        )
        self.entry.pack(side="left", padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="Send",
            width=65,
            command=self.send_message
        )
        self.send_btn.pack(side="right")

        # Chat History
        self.messages = [{
            "role": "system",
            "content": (
                "Your name is LUNAR, a desktop OS assistant. Execute system, file, browser, "
                "and typing tasks via tools when requested. Keep answers direct and concise."
            )
        }]

        # Perform async health check on launch
        threading.Thread(target=self.run_startup_check, daemon=True).start()

    def on_close(self):
        """Safely terminates the GUI and cancels any background tasks."""
        self.is_running = False
        self.destroy()

    def run_startup_check(self):
        """Pre-flight check for Ollama and model presence."""
        is_ready, msg = check_ollama_health(MODEL_NAME)
        if not self.is_running:
            return
        if is_ready:
            self.after(0, lambda: self.set_status("● Ready", "#10B981"))
        else:
            self.after(0, lambda: self.set_status("⚠️ Ollama Offline", "#EF4444"))
            self.after(0, lambda: self.append_chat("System", f"Notice: {msg}"))

    def append_chat(self, sender: str, text: str):
        """Thread-safe UI chat append."""
        if not self.is_running:
            return
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"{sender}: {text}\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def set_status(self, text: str, color: str = "#9CA3AF"):
        """Thread-safe status update."""
        if not self.is_running:
            return
        self.status_label.configure(text=text, text_color=color)

    def set_busy(self, is_busy: bool):
        """Updates UI interactive state during model generation."""
        if not self.is_running:
            return
        self.is_processing = is_busy
        if is_busy:
            self.send_btn.configure(state="disabled", text="⏳")
            self.entry.configure(state="disabled")
            self.set_status("⏳ Thinking...", "#F59E0B")
        else:
            self.send_btn.configure(state="normal", text="Send")
            self.entry.configure(state="normal")
            self.set_status("● Ready", "#10B981")

    def gui_confirm(self, action_desc: str, details: str) -> bool:
        """Thread-safe modal confirmation dialog invoked from background worker."""
        if not self.is_running:
            return False

        result = [False]
        done_event = threading.Event()

        def ask():
            try:
                if self.is_running:
                    ans = mb.askyesno(
                        title="LUNAR Security Authorization",
                        message=f"LUNAR requests permission to:\n\n{action_desc}\n\nTarget:\n{details}\n\nAuthorize this operation?",
                        parent=self
                    )
                    result[0] = bool(ans)
            except Exception as e:
                logger.error(f"Confirmation dialog error: {e}")
                result[0] = False
            finally:
                done_event.set()

        self.after(0, ask)
        done_event.wait(timeout=60)
        return result[0]

    def send_message(self):
        """Submits user text to the processing worker."""
        if self.is_processing:
            return

        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.set_busy(True)
        self.entry.delete(0, "end")
        self.append_chat("You", user_text)

        # 1. Fast Path: Instant launch for common app & web navigation commands
        fast_tool, fast_args = fast_match_intent(user_text)
        if fast_tool and fast_args:
            target_desc = fast_args.get("app_name", fast_args.get("url", fast_tool))
            self.set_status(f"⚡ Launching {target_desc}...", "#3B82F6")

            def run_fast():
                try:
                    result = dispatch_tool_call(fast_tool, fast_args, confirm_callback=self.gui_confirm)
                    if self.is_running:
                        self.after(0, lambda: self.append_chat("Assistant", f"✓ {result}"))
                        self.messages.append({"role": "user", "content": user_text})
                        self.messages.append({"role": "assistant", "content": result})
                except Exception as err:
                    logger.error(f"Fast execution error: {err}")
                    if self.is_running:
                        self.after(0, lambda: self.append_chat("Error", f"Error: {str(err)}"))
                finally:
                    if self.is_running:
                        self.after(0, lambda: self.set_busy(False))

            threading.Thread(target=run_fast, daemon=True).start()
            return

        # 2. General Local LLM Inference Path
        self.append_chat("System", "⏳ LUNAR is processing your request...")
        self.messages.append({"role": "user", "content": user_text})

        threading.Thread(target=self.process_ai_request, daemon=True).start()

    def process_ai_request(self):
        """Background worker handling model inference and tool calling."""
        try:
            # Bound context history for speed on CPU (system prompt + last 6 messages)
            context = [self.messages[0]] + self.messages[-6:] if len(self.messages) > 7 else self.messages

            response = ollama.chat(
                model=MODEL_NAME,
                messages=context,
                tools=TOOL_SCHEMAS,
                options={"temperature": 0.1, "num_predict": 256}
            )

            if not self.is_running:
                return

            response_msg = response.get("message", {})
            self.messages.append(response_msg)

            # Parse tool calls safely
            tool_name, tool_args = parse_tool_call(response_msg)

            if tool_name and tool_args is not None:
                self.after(0, lambda: self.set_status(f"⚡ Running {tool_name}...", "#3B82F6"))

                # Execute with GUI confirmation
                result = dispatch_tool_call(tool_name, tool_args, confirm_callback=self.gui_confirm)

                if self.is_running:
                    self.after(0, lambda: self.append_chat("Assistant", f"✓ {result}"))
                    self.messages.append({"role": "assistant", "content": result})
            else:
                reply = response_msg.get("content", "").strip()

                # Check if raw JSON tool call leaked into content
                fallback_tool, fallback_args = extract_fallback_tool_from_text(reply)
                if fallback_tool and fallback_args:
                    self.after(0, lambda: self.set_status(f"⚡ Running {fallback_tool}...", "#3B82F6"))
                    result = dispatch_tool_call(fallback_tool, fallback_args, confirm_callback=self.gui_confirm)
                    if self.is_running:
                        self.after(0, lambda: self.append_chat("Assistant", f"✓ {result}"))
                        self.messages.append({"role": "assistant", "content": result})
                else:
                    clean_reply = clean_display_text(reply)
                    if self.is_running:
                        self.after(0, lambda: self.append_chat("Assistant", clean_reply if clean_reply else "Task completed."))

        except Exception as err:
            logger.error(f"Inference error in GUI: {err}")
            if self.is_running:
                self.after(0, lambda: self.append_chat("Error", f"Error: {str(err)}"))
        finally:
            if self.is_running:
                self.after(0, lambda: self.set_busy(False))


if __name__ == "__main__":
    app = FloatingAssistantWidget()
    app.mainloop()