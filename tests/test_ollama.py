"""
Unit tests for Ollama connectivity and error handling in LUNAR Core.
"""

from unittest.mock import patch, MagicMock
from lunar_core import check_ollama_health


class TestOllamaHealthCheck:
    def test_ollama_connected_and_model_found(self):
        mock_response = {
            "models": [
                {"name": "qwen2.5-coder:7b"},
                {"name": "llama3:latest"}
            ]
        }
        with patch("ollama.list", return_value=mock_response):
            is_ready, msg = check_ollama_health("qwen2.5-coder:7b")
            assert is_ready is True
            assert "ready" in msg

    def test_ollama_running_but_model_missing(self):
        mock_response = {
            "models": [
                {"name": "mistral:latest"}
            ]
        }
        with patch("ollama.list", return_value=mock_response):
            is_ready, msg = check_ollama_health("qwen2.5-coder:7b")
            assert is_ready is True
            assert "Warning: Model 'qwen2.5-coder:7b' not found" in msg

    def test_ollama_server_offline(self):
        with patch("ollama.list", side_effect=ConnectionRefusedError("Connection refused")):
            is_ready, msg = check_ollama_health("qwen2.5-coder:7b")
            assert is_ready is False
            assert "Cannot connect to Ollama server" in msg
