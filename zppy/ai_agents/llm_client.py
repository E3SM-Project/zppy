"""
LLM client abstraction for zppy AI agents.

Supports two backends:
  anthropic  — native Anthropic SDK with prompt caching
  openai     — OpenAI-compatible interface (Groq, NVIDIA NIM, Ollama, etc.)

Provider selection (highest priority first):
  1. Constructor argument
  2. ZPPY_AI_PROVIDER env var
  3. Auto-detect: anthropic if ANTHROPIC_API_KEY set, else openai

Model / key / base_url follow the same priority: constructor → env var → default.

Shortcut providers (map to openai backend with a preset base_url):
  groq    → https://api.groq.com/openai/v1
  nvidia  → https://integrate.api.nvidia.com/v1
  ollama  → http://localhost:11434/v1  (api_key defaults to "ollama")
"""

import os
from typing import Optional

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
}

_SHORTCUT_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "ollama": "http://localhost:11434/v1",
}


class LLMClient:
    """
    Thin wrapper that normalises Anthropic and OpenAI-compatible providers
    behind a single call(system, user) interface.

    Usage:
        client = LLMClient()                          # auto-detects provider
        reply  = client.call(system="...", user="...")

        # Groq (OpenAI-compatible, free tier)
        client = LLMClient(provider="groq", model="llama-3.3-70b-versatile")

        # Local Ollama
        client = LLMClient(provider="ollama", model="llama3")
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        raw_provider = (
            provider
            or os.environ.get("ZPPY_AI_PROVIDER")
            or ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai")
        )

        if raw_provider in _SHORTCUT_BASE_URLS:
            self.provider = "openai"
            self.base_url = (
                base_url
                or os.environ.get("ZPPY_AI_BASE_URL")
                or _SHORTCUT_BASE_URLS[raw_provider]
            )
            _default_key = "ollama" if raw_provider == "ollama" else None
        else:
            self.provider = raw_provider
            self.base_url = base_url or os.environ.get("ZPPY_AI_BASE_URL")
            _default_key = None

        self.model = (
            model
            or os.environ.get("ZPPY_AI_MODEL")
            or DEFAULT_MODELS.get(self.provider, "gpt-4o")
        )
        self.api_key = (
            api_key
            or os.environ.get("ZPPY_AI_API_KEY")
            or self._env_api_key()
            or _default_key
        )

    def _env_api_key(self) -> Optional[str]:
        if self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY")
        return os.environ.get("OPENAI_API_KEY")

    def call(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """
        Send a single-turn prompt to the LLM.

        Args:
            system:     Static system prompt (cached on Anthropic backend).
            user:       User message — include RAG context + question here.
            max_tokens: Maximum tokens in the response.

        Returns:
            The model's text response.
        """
        if self.provider == "anthropic":
            return self._call_anthropic(system, user, max_tokens)
        return self._call_openai_compatible(system, user, max_tokens)

    def _call_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install 'zppy[ai]'"
            )
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not set. "
                "Export ANTHROPIC_API_KEY or pass api_key= to LLMClient."
            )
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def _call_openai_compatible(self, system: str, user: str, max_tokens: int) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required for non-Anthropic providers. "
                "Install with: pip install openai"
            )
        kwargs: dict = {"api_key": self.api_key or "placeholder"}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    def check_available(self) -> tuple[bool, str]:
        """Return (ok, description) indicating whether the backend is usable."""
        if self.provider == "anthropic":
            if not self.api_key:
                return False, "ANTHROPIC_API_KEY not set"
            try:
                import anthropic  # noqa: F401
            except ImportError:
                return False, "anthropic package not installed (pip install 'zppy[ai]')"
            return True, f"provider=anthropic  model={self.model}"
        else:
            if not self.api_key:
                return False, "API key not set (ZPPY_AI_API_KEY or OPENAI_API_KEY)"
            try:
                from openai import OpenAI  # noqa: F401
            except ImportError:
                return False, "openai package not installed (pip install openai)"
            url_info = f"  base_url={self.base_url}" if self.base_url else ""
            return True, f"provider=openai  model={self.model}{url_info}"
