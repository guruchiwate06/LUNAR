"""
LUNAR - CLI Assistant Mode
Command-line interface with human-in-the-loop approvals,
safety checks, and local Ollama automation.
"""

import sys
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


def cli_confirm(action_desc: str, details: str) -> bool:
    """Prompts the user in the terminal for explicit authorization."""
    print(f"\n🛡️  [Action Authorization Required]")
    print(f"Action:  {action_desc}")
    print(f"Details: {details}")
    try:
        confirm = input("Allow execution? (y/N): ").strip().lower()
        return confirm == "y"
    except (KeyboardInterrupt, EOFError):
        print("\nAction aborted.")
        return False


def start_assistant():
    print("=" * 55)
    print("🌙 LUNAR — Local Neural Automation & Robotics Copilot")
    print("Mode: Terminal / CLI")
    print("Type 'exit' or 'quit' to close.")
    print("=" * 55)

    # Pre-flight health check
    is_ready, health_msg = check_ollama_health(MODEL_NAME)
    print(f"Status: {health_msg}\n")
    if not is_ready:
        print("⚠️  Warning: Ollama service issue detected. LUNAR may not generate responses until resolved.\n")

    system_prompt = (
        "You are LUNAR, an autonomous local OS copilot. Execute system, file, browser, "
        "and typing actions using tools when requested. Keep answers direct and concise."
    )
    messages = [{"role": "system", "content": system_prompt}]

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # 1. Fast Path for direct app launch or web navigation
            fast_tool, fast_args = fast_match_intent(user_input)
            if fast_tool and fast_args:
                result = dispatch_tool_call(fast_tool, fast_args, confirm_callback=cli_confirm)
                print(f"\nAssistant: {result}")
                messages.append({"role": "user", "content": user_input})
                messages.append({"role": "assistant", "content": result})
                continue

            # 2. General LLM Inference Path
            messages.append({"role": "user", "content": user_input})
            context = [messages[0]] + messages[-6:] if len(messages) > 7 else messages

            print("⏳ Thinking...")
            try:
                response = ollama.chat(
                    model=MODEL_NAME,
                    messages=context,
                    tools=TOOL_SCHEMAS,
                    options={"temperature": 0.1, "num_predict": 256}
                )
            except Exception as e:
                print(f"\n❌ Ollama Error: {str(e)}")
                print("Make sure Ollama is running ('ollama serve') and the model is pulled.")
                continue

            response_msg = response.get("message", {})
            messages.append(response_msg)

            # Parse tool calls safely
            tool_name, tool_args = parse_tool_call(response_msg)

            if tool_name and tool_args is not None:
                tool_result = dispatch_tool_call(tool_name, tool_args, confirm_callback=cli_confirm)
                print(f"\nAssistant: {tool_result}")
                messages.append({"role": "assistant", "content": f"Action result: {tool_result}"})
            else:
                reply = response_msg.get("content", "").strip()
                fallback_tool, fallback_args = extract_fallback_tool_from_text(reply)
                if fallback_tool and fallback_args:
                    tool_result = dispatch_tool_call(fallback_tool, fallback_args, confirm_callback=cli_confirm)
                    print(f"\nAssistant: {tool_result}")
                    messages.append({"role": "assistant", "content": f"Action result: {tool_result}"})
                else:
                    clean_reply = clean_display_text(reply)
                    print(f"\nAssistant: {clean_reply if clean_reply else 'Task completed.'}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting LUNAR CLI.")
            break
        except Exception as e:
            logger.error(f"Unexpected CLI error: {e}")
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    start_assistant()