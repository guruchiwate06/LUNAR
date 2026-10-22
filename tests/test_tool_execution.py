"""
Unit tests for Tool Execution, Subprocess Handling, and Confirmation Safety in LUNAR Core.
"""

import subprocess
from unittest.mock import patch, MagicMock
import pytest
from lunar_core import (
    execute_shell_command,
    safe_launch_application,
    safe_open_web_page,
    dispatch_tool_call
)


class TestShellCommandExecution:
    def test_execute_safe_command_success(self):
        result = execute_shell_command("echo test_lunar_ok")
        assert "test_lunar_ok" in result

    def test_execute_blocked_command_rejected_before_execution(self):
        with patch("subprocess.run") as mock_run:
            result = execute_shell_command("format C: /fs:ntfs")
            mock_run.assert_not_called()
            assert "Security Error: Command blocked" in result

    def test_confirmation_callback_accepted(self):
        confirm_called = []

        def mock_confirm(desc, details):
            confirm_called.append((desc, details))
            return True

        result = execute_shell_command("echo confirmed_run", confirm_callback=mock_confirm)
        assert len(confirm_called) == 1
        assert "confirmed_run" in result

    def test_confirmation_callback_rejected(self):
        confirm_called = []

        def mock_reject(desc, details):
            confirm_called.append((desc, details))
            return False

        with patch("subprocess.run") as mock_run:
            result = execute_shell_command("echo should_not_run", confirm_callback=mock_reject)
            mock_run.assert_not_called()
            assert "Execution cancelled by user" in result

    def test_command_timeout_handled(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 10", timeout=2)):
            result = execute_shell_command("sleep 10", timeout=2)
            assert "timed out after 2 seconds" in result

    def test_command_non_zero_exit_code_reported(self):
        # Running an invalid command returns error code without reporting false success
        result = execute_shell_command("dir nonexistent_directory_12345_xyz")
        assert "error code" in result or "cannot find" in result.lower() or "not found" in result.lower()


class TestApplicationLaunching:
    def test_launch_known_application(self):
        with patch("subprocess.Popen") as mock_popen:
            result = safe_launch_application("notepad")
            mock_popen.assert_called_once()
            assert "launched successfully" in result

    def test_launch_injection_attempt_blocked(self):
        with patch("subprocess.Popen") as mock_popen:
            injection_payloads = [
                "notepad & calc.exe",
                "calc; whoami",
                "code | powershell",
                "calc > test.txt",
                "notepad`calc`"
            ]
            for payload in injection_payloads:
                result = safe_launch_application(payload)
                mock_popen.assert_not_called()
                assert "Security Error" in result

    def test_launch_empty_or_malformed_app(self):
        assert "must be a non-empty string" in safe_launch_application("")
        assert "must be a non-empty string" in safe_launch_application(None)

    def test_launch_rejected_by_confirmation(self):
        def reject(desc, details):
            return False

        with patch("subprocess.Popen") as mock_popen, patch("lunar_core.find_system_executable", return_value=None):
            result = safe_launch_application("custom_unmapped_app_xyz", confirm_callback=reject)
            mock_popen.assert_not_called()
            assert "Launch cancelled by user" in result

    def test_dynamic_application_discovery(self):
        from lunar_core import find_system_executable
        # Notepad is guaranteed on Windows
        import sys
        if sys.platform == "win32":
            res = find_system_executable("notepad")
            assert res is not None
            assert len(res) >= 1
            assert "notepad" in res[0].lower()

    def test_launch_chrome_dynamic(self):
        with patch("subprocess.Popen") as mock_popen:
            result = safe_launch_application("chrome")
            mock_popen.assert_called_once()
            assert "launched successfully" in result


class TestWebNavigation:
    def test_open_valid_web_page(self):
        with patch("webbrowser.open", return_value=True) as mock_open:
            result = safe_open_web_page("https://github.com")
            mock_open.assert_called_once_with("https://github.com")
            assert "Opened browser" in result

    def test_open_prohibited_protocol(self):
        with patch("webbrowser.open") as mock_open:
            result = safe_open_web_page("file:///etc/passwd")
            mock_open.assert_not_called()
            assert "Browser Error" in result


class TestToolDispatch:
    def test_dispatch_unknown_tool(self):
        result = dispatch_tool_call("delete_hard_drive", {"drive": "C"})
        assert "Unsupported tool" in result

    def test_dispatch_invalid_args_type(self):
        result = dispatch_tool_call("execute_command", "not a dict")
        assert "must be a dictionary" in result

    def test_dispatch_missing_required_arg(self):
        result = dispatch_tool_call("execute_command", {})
        assert "Missing or invalid 'command'" in result

        result = dispatch_tool_call("launch_app", {})
        assert "Missing or invalid 'app_name'" in result

        result = dispatch_tool_call("open_website", {})
        assert "Missing or invalid 'url'" in result

        result = dispatch_tool_call("type_in_active_window", {})
        assert "Missing or invalid 'text'" in result
