"""
Unit tests for fast intent matching and display cleaning in LUNAR Core.
"""

from lunar_core import fast_match_intent, clean_display_text


class TestFastMatchIntent:
    def test_fast_match_app_launching(self):
        cases = [
            ("open chrome", ("launch_app", {"app_name": "chrome"})),
            ("launch notepad", ("launch_app", {"app_name": "notepad"})),
            ("start calc", ("launch_app", {"app_name": "calc"})),
            ("open vs code", ("launch_app", {"app_name": "code"})),
            ("please open calculator", ("launch_app", {"app_name": "calc"})),
        ]
        for user_input, expected in cases:
            tool_name, tool_args = fast_match_intent(user_input)
            assert tool_name == expected[0], f"Failed for {user_input}"
            assert tool_args == expected[1], f"Failed for {user_input}"

    def test_fast_match_web_navigation(self):
        cases = [
            ("open youtube", ("open_website", {"url": "https://www.youtube.com"})),
            ("go to github.com", ("open_website", {"url": "https://github.com"})),
            ("visit google.com", ("open_website", {"url": "https://google.com"})),
        ]
        for user_input, expected in cases:
            tool_name, tool_args = fast_match_intent(user_input)
            assert tool_name == expected[0], f"Failed for {user_input}"
            assert tool_args == expected[1], f"Failed for {user_input}"

    def test_complex_query_falls_back_to_llm(self):
        complex_queries = [
            "What is the capital of France?",
            "Write a python script to reverse a linked list",
            "Explain quantum computing",
            "Check if my disk is full",
        ]
        for query in complex_queries:
            tool_name, tool_args = fast_match_intent(query)
            assert tool_name is None
            assert tool_args is None


class TestCleanDisplayText:
    def test_hides_raw_tool_json(self):
        raw_jsons = [
            '{"name": "launch_app", "arguments": {"app_name": "chrome"}}',
            '{"name": "execute_command", "arguments": {"command": "dir"}}',
            '<tool_call>{"name": "open_website"}</tool_call>',
            '<think>Thinking about tool...</think>Done!'
        ]
        for text in raw_jsons[:3]:
            cleaned = clean_display_text(text)
            assert "launch_app" not in cleaned
            assert "execute_command" not in cleaned
            assert "open_website" not in cleaned

    def test_preserves_normal_conversational_text(self):
        text = "Hello! I am ready to help you with your operating system."
        assert clean_display_text(text) == text
