from __future__ import annotations

from typing import Any

import requests

from .app_config import AppConfig, get_config


class DeepSeekClient:
    """Small OpenAI-compatible client for optional DeepSeek refinement."""

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()

    @property
    def enabled(self) -> bool:
        return self.config.has_deepseek

    def complete(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        if not self.enabled:
            return ""

        url = _chat_completions_url(self.config.deepseek_base_url)
        payload: dict[str, Any] = {
            "model": self.config.deepseek_model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.config.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.config.request_timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"
