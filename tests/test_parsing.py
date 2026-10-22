"""
Unit tests for Ollama tool call parsing and fallback extraction in LUNAR Core.
"""

from lunar_core import (
    parse_tool_call,
    extract_fallback_tool_from_text
)


class TestNativeToolCallParsing:
    def test_native_tool_call_dict_args(self):
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "launch_app",
                        "arguments": {"app_name": "notepad"}
                    }
                }
            ]
        }
        tool_name, tool_args = parse_tool_call(msg)
        assert tool_name == "launch_app"
        assert tool_args == {"app_name": "notepad"}

    def test_native_tool_call_stringified_json_args(self):
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "execute_command",
                        "arguments": '{"command": "dir"}'
                    }
                }
            ]
        }
        tool_name, tool_args = parse_tool_call(msg)
        assert tool_name == "execute_command"
        assert tool_args == {"command": "dir"}

    def test_native_tool_call_unsupported_tool_ignored(self):
        msg = {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "unsupported_dangerous_action",
                        "arguments": {"target": "all"}
                    }
                }
            ]
        }
        tool_name, tool_args = parse_tool_call(msg)
        assert tool_name is None
        assert tool_args is None


class TestFallbackJsonParsing:
    def test_fallback_json_in_content(self):
        msg = {
            "role": "assistant",
            "content": 'Certainly! {"name": "open_website", "arguments": {"url": "https://github.com"}}'
        }
        tool_name, tool_args = parse_tool_call(msg)
        assert tool_name == "open_website"
        assert tool_args == {"url": "https://github.com"}

    def test_fallback_json_parameters_alias(self):
        text = '{"name": "launch_app", "parameters": {"app_name": "calc"}}'
        tool_name, tool_args = extract_fallback_tool_from_text(text)
        assert tool_name == "launch_app"
        assert tool_args == {"app_name": "calc"}

    def test_fallback_malformed_json_ignored_safely(self):
        malformed_texts = [
            '{"name": "execute_command", "arguments": {broken json here',
            'Here is some text with { braces } that is not a tool',
            '{ "random": 123 }',
            'Just normal conversational text without braces.',
            '',
            None
        ]
        for text in malformed_texts:
            tool_name, tool_args = extract_fallback_tool_from_text(text)
            assert tool_name is None
            assert tool_args is None

    def test_fallback_unsupported_tool_name_rejected(self):
        text = '{"name": "rm_rf", "arguments": {"path": "/"}}'
        tool_name, tool_args = extract_fallback_tool_from_text(text)
        assert tool_name is None
        assert tool_args is None
