from __future__ import annotations

import re
from typing import Any

import requests

from .app_config import AppConfig, get_config


PRICE_RE = re.compile(
    r"(?:门票|票价|成人票|全价票|参考价|价格)"
    r"[^0-9¥￥。；;，,\n]{0,24}?"
    r"(?:¥|￥)?\s*(\d{1,3})(?!\d)(?=\s*(?:元|圆|/人|起))"
)
FREE_TICKET_RE = re.compile(r"(?:门票|票价|入园|景区)[^。；;，,\n]{0,16}(?:免费|免票|无需门票)")
STATUS_RULES = [
    (("闭园", "暂停开放", "暂停营业", "停业", "关闭"), "可能暂停开放"),
    (("预约", "实名预约", "需预约"), "可能需预约"),
    (("限流", "客流管控"), "可能限流"),
    (("开放", "营业"), "通常开放"),
]


class WebSearchClient:
    """Optional web search client for scenic ticket/status snippets."""

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()

    @property
    def enabled(self) -> bool:
        return self.config.has_search_api

    def search_scenic_status(self, scenic_name: str, city: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        query = f"{city} {scenic_name} 门票 票价 开放时间 公告 闭园 预约 小红书 携程 马蜂窝 大众点评"
        results = self._search(query)
        if not results:
            return None
        return _extract_scenic_status(query, results)

    def _search(self, query: str) -> list[dict[str, str]]:
        provider = self.config.search_provider
        try:
            if provider == "bing":
                return self._bing(query)
            if provider == "serpapi":
                return self._serpapi(query)
            return self._tavily(query)
        except Exception:
            return []

    def _tavily(self, query: str) -> list[dict[str, str]]:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.config.search_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
            },
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", "")),
            }
            for item in data.get("results", [])
        ]

    def _bing(self, query: str) -> list[dict[str, str]]:
        response = requests.get(
            "https://api.bing.microsoft.com/v7.0/search",
            headers={"Ocp-Apim-Subscription-Key": self.config.search_api_key},
            params={"q": query, "mkt": "zh-CN", "count": 5},
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": str(item.get("name", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("snippet", "")),
            }
            for item in data.get("webPages", {}).get("value", [])
        ]

    def _serpapi(self, query: str) -> list[dict[str, str]]:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "api_key": self.config.search_api_key, "hl": "zh-cn", "num": 5},
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("link", "")),
                "snippet": str(item.get("snippet", "")),
            }
            for item in data.get("organic_results", [])
        ]


def _extract_scenic_status(query: str, results: list[dict[str, str]]) -> dict[str, Any]:
    combined = "\n".join(f"{item.get('title', '')} {item.get('snippet', '')}" for item in results)
    price = _extract_price(combined)
    status = _extract_status(combined)
    top = results[0]
    return {
        "query": query,
        "ticket_price": price,
        "open_status": status,
        "announcement": _short_snippet(top.get("snippet", "")),
        "source_title": top.get("title", ""),
        "source_url": top.get("url", ""),
        "source": "web_search",
        "confidence": "medium" if price or status != "开放状态待官方确认" else "low",
        "raw_results": results[:3],
    }


def _extract_price(text: str) -> int | None:
    match = PRICE_RE.search(text)
    if not match:
        if "免费" in text:
            return 0
        return None
    return int(match.group(1))


def _extract_status(text: str) -> str:
    for keywords, status in STATUS_RULES:
        if any(keyword in text for keyword in keywords):
            return status
    return "开放状态待官方确认"


def _short_snippet(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."
