import os
from unittest.mock import MagicMock, patch

import pytest

from zppy.ai_agents.llm_client import LLMClient


class TestLLMClientProviderDetection:
    def test_anthropic_selected_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("ZPPY_AI_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "anthropic"

    def test_openai_selected_when_no_anthropic_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ZPPY_AI_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "openai"

    def test_provider_arg_overrides_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        client = LLMClient(provider="openai", api_key="sk-openai")
        assert client.provider == "openai"

    def test_shortcut_groq_maps_to_openai(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(provider="groq", api_key="gsk-test")
        assert client.provider == "openai"
        assert "groq.com" in client.base_url

    def test_shortcut_ollama_sets_default_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(provider="ollama", model="llama3")
        assert client.provider == "openai"
        assert "11434" in client.base_url
        assert client.api_key == "ollama"

    def test_model_default_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("ZPPY_AI_MODEL", raising=False)
        client = LLMClient()
        assert client.model == "claude-sonnet-4-6"

    def test_model_env_override(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("ZPPY_AI_MODEL", "claude-opus-4-7")
        client = LLMClient()
        assert client.model == "claude-opus-4-7"


class TestLLMClientCall:
    def test_anthropic_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ZPPY_AI_API_KEY", raising=False)
        client = LLMClient(provider="anthropic")
        with pytest.raises(ValueError, match="API key not set"):
            client.call("system", "user")

    def test_anthropic_missing_package_raises(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        client = LLMClient(provider="anthropic")
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic package"):
                client.call("system", "user")

    def test_openai_missing_package_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(provider="openai", api_key="sk-test")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai package"):
                client.call("system", "user")

    def test_anthropic_call_returns_text(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        client = LLMClient(provider="anthropic")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="mocked answer")]

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = client.call("system prompt", "user message")

        assert result == "mocked answer"

    def test_openai_call_returns_text(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(provider="openai", api_key="sk-test")

        mock_choice = MagicMock()
        mock_choice.message.content = "mocked openai answer"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = client.call("system prompt", "user message")

        assert result == "mocked openai answer"


class TestLLMClientCheckAvailable:
    def test_anthropic_ok(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        client = LLMClient(provider="anthropic")
        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            ok, msg = client.check_available()
        assert ok
        assert "anthropic" in msg

    def test_anthropic_no_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ZPPY_AI_API_KEY", raising=False)
        client = LLMClient(provider="anthropic")
        ok, msg = client.check_available()
        assert not ok
        assert "ANTHROPIC_API_KEY" in msg
