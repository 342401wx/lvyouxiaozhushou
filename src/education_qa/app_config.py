from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .paths import PROJECT_ROOT


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(path: Path | None = None) -> dict[str, str]:
    """Load a simple KEY=VALUE .env file without adding another dependency."""
    env_path = path or PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_quotes(value)
    return values


@dataclass(frozen=True)
class AppConfig:
    amap_api_key: str = ""
    amap_js_key: str = ""
    amap_security_js_code: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    railway_provider: str = ""
    railway_mcp_url: str = ""
    railway_api_key: str = ""
    flight_api_key: str = ""
    coach_api_key: str = ""
    scenic_status_api_key: str = ""
    search_api_key: str = ""
    search_provider: str = "tavily"
    request_timeout: int = 12
    http_max_workers: int = 32
    http_request_queue_size: int = 128
    plan_concurrency: int = 8
    intent_concurrency: int = 12
    sqlite_timeout: int = 30

    @property
    def has_amap_web_service(self) -> bool:
        return bool(self.amap_api_key)

    @property
    def has_amap_js(self) -> bool:
        return bool(self.amap_js_key)

    @property
    def has_deepseek(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_12306_mcp(self) -> bool:
        return self.railway_provider.replace("-", "_") == "12306_mcp" and bool(self.railway_mcp_url)

    @property
    def has_realtime_intercity(self) -> bool:
        return bool(self.has_12306_mcp or self.railway_api_key or self.flight_api_key or self.coach_api_key)

    @property
    def has_realtime_scenic_status(self) -> bool:
        return bool(self.scenic_status_api_key)

    @property
    def has_search_api(self) -> bool:
        return bool(self.search_api_key)


def get_config(env_path: Path | None = None) -> AppConfig:
    file_values = load_env_file(env_path)

    def get_value(*names: str, default: str = "") -> str:
        for name in names:
            value = os.getenv(name)
            if value:
                return value.strip()
            value = file_values.get(name)
            if value:
                return value.strip()
        return default

    def get_int(name: str, default: int, *, minimum: int = 1, maximum: int = 10000) -> int:
        text = get_value(name, default=str(default))
        try:
            value = int(text)
        except ValueError:
            value = default
        return max(minimum, min(maximum, value))

    timeout = get_int("REQUEST_TIMEOUT", 12, minimum=1, maximum=120)

    return AppConfig(
        amap_api_key=get_value("AMAP_API_KEY", "VITE_AMAP_WEB_KEY"),
        amap_js_key=get_value("AMAP_JS_KEY", "VITE_AMAP_WEB_JS_KEY"),
        amap_security_js_code=get_value("AMAP_SECURITY_JS_CODE", "AMAP_SECURITY_CODE"),
        deepseek_api_key=get_value("DEEPSEEK_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
        deepseek_base_url=get_value(
            "DEEPSEEK_BASE_URL",
            "LLM_BASE_URL",
            "OPENAI_BASE_URL",
            default="https://api.deepseek.com",
        ).rstrip("/"),
        deepseek_model=get_value("DEEPSEEK_MODEL", "LLM_MODEL_ID", "MODEL_NAME", "OPENAI_MODEL", default="deepseek-chat"),
        railway_provider=get_value("RAILWAY_PROVIDER").lower(),
        railway_mcp_url=get_value("RAILWAY_MCP_URL").rstrip("/"),
        railway_api_key=get_value("RAILWAY_API_KEY"),
        flight_api_key=get_value("FLIGHT_API_KEY"),
        coach_api_key=get_value("COACH_API_KEY"),
        scenic_status_api_key=get_value("SCENIC_STATUS_API_KEY"),
        search_api_key=get_value("SEARCH_API_KEY"),
        search_provider=get_value("SEARCH_PROVIDER", default="tavily").lower(),
        request_timeout=timeout,
        http_max_workers=get_int("HTTP_MAX_WORKERS", 32, minimum=4, maximum=256),
        http_request_queue_size=get_int("HTTP_REQUEST_QUEUE_SIZE", 128, minimum=16, maximum=1024),
        plan_concurrency=get_int("PLAN_CONCURRENCY", 8, minimum=1, maximum=64),
        intent_concurrency=get_int("INTENT_CONCURRENCY", 12, minimum=1, maximum=128),
        sqlite_timeout=get_int("SQLITE_TIMEOUT", 30, minimum=5, maximum=120),
    )
