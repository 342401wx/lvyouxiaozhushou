from __future__ import annotations

from datetime import date
from typing import Any


KNOWN_SCENIC_STATUS: dict[str, dict[str, Any]] = {
    "武侯祠": {"ticket_price": 50, "open_status": "通常开放", "announcement": "节假日可能限流，建议以官方购票页面为准。"},
    "锦里古街": {"ticket_price": 0, "open_status": "通常开放", "announcement": "街区开放时间较长，商户营业时间不同。"},
    "宽窄巷子": {"ticket_price": 0, "open_status": "通常开放", "announcement": "街区免费，热门时段人流较多。"},
    "成都博物馆": {"ticket_price": 0, "open_status": "需预约", "announcement": "博物馆类场馆常见周一闭馆或预约入馆。"},
    "人民公园": {"ticket_price": 0, "open_status": "通常开放", "announcement": "公园免费，茶馆消费另计。"},
    "都江堰": {"ticket_price": 80, "open_status": "通常开放", "announcement": "水利景区票价和开放时间可能随季节调整。"},
    "熊猫基地": {"ticket_price": 55, "open_status": "通常开放", "announcement": "建议上午参观，节假日可能限流或预约。"},
    "春熙路": {"ticket_price": 0, "open_status": "通常开放", "announcement": "商业街免费，商户营业时间不同。"},
    "天井湖公园": {"ticket_price": 0, "open_status": "通常开放", "announcement": "城市公园通常免费开放，实际以现场公告为准。"},
    "铜陵博物馆": {"ticket_price": 0, "open_status": "可能需预约", "announcement": "博物馆类场馆通常免费但可能需要预约，注意闭馆日。"},
}


OFFICIAL_CHECK_NOTE = "景区是否开放、是否闭园、是否限流和最终票价，请出行前以景区官网或官方购票平台为准。"


def scenic_status_for_stop(stop: dict[str, Any], city: str, *, search_client: Any | None = None) -> dict[str, Any]:
    name = str(stop.get("name", ""))
    known = _lookup_known_status(name)
    category = str(stop.get("category", ""))
    knowledge_price = int(stop.get("ticket_price") or 0)
    web_result = search_client.search_scenic_status(name, city) if search_client and search_client.enabled else None
    ticket_price: int
    ticket_source: str
    ticket_price_is_estimated = False
    price_note = ""

    if web_result and web_result.get("ticket_price") is not None:
        ticket_price = int(web_result.get("ticket_price") or 0)
        ticket_source = "web_search"
        price_note = "票价来自联网搜索摘要，仍需以官方购票平台为准。"
    elif knowledge_price:
        ticket_price = knowledge_price
        ticket_source = "knowledge_base"
        price_note = "票价来自知识库抽取，需出行前核验。"
    elif known is not None:
        ticket_price = int(known.get("ticket_price", 0))
        ticket_source = "fallback_known"
        price_note = "票价来自本项目预设参考，需出行前核验。"
    else:
        ticket_price = _reference_ticket_price(category, name)
        ticket_source = "reference_estimate"
        ticket_price_is_estimated = True
        price_note = "未查到可靠票价，已按景点类型给出预算参考价，最终以官方为准。"

    if web_result:
        open_status = web_result.get("open_status") or (known or {}).get("open_status") or _fallback_status(category, name)
        announcement = web_result.get("announcement") or (known or {}).get("announcement") or _fallback_announcement(category, name)
        source = "web_search"
    else:
        if known:
            open_status = known.get("open_status", "通常开放")
            announcement = known.get("announcement", "以官方公告为准。")
            source = "fallback_known"
        else:
            open_status = _fallback_status(category, name)
            announcement = _fallback_announcement(category, name)
            source = "fallback_rule"

    return {
        "name": name,
        "city": city,
        "ticket_price": int(ticket_price or 0),
        "budget_ticket_price": int(ticket_price or 0),
        "ticket_source": ticket_source,
        "ticket_price_is_estimated": ticket_price_is_estimated,
        "price_note": price_note,
        "open_status": open_status,
        "announcement": announcement,
        "official_check_note": OFFICIAL_CHECK_NOTE,
        "source": source,
        "web_source_title": (web_result or {}).get("source_title", ""),
        "web_source_url": (web_result or {}).get("source_url", ""),
        "checked_date": date.today().isoformat(),
        "needs_official_check": True,
    }


def summarize_scenic_status(days: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [stop.get("scenic_status", {}) for day in days for stop in day.get("stops", [])]
    warnings = []
    estimated_count = 0
    for status in statuses:
        text = f"{status.get('name')}：{status.get('open_status')}，{status.get('announcement')}"
        if any(token in text for token in ("预约", "闭馆", "限流", "调整", "官方")):
            warnings.append(text)
        if status.get("ticket_price_is_estimated"):
            estimated_count += 1
    return {
        "source": "fallback_scenic_status",
        "checked_date": date.today().isoformat(),
        "warnings": warnings[:6],
        "estimated_ticket_count": estimated_count,
        "summary": f"景区票价、开放状态和公告来自联网搜索、知识库或参考价规则；{OFFICIAL_CHECK_NOTE}",
    }


def _ticket_source(knowledge_price: int, known: dict[str, Any] | None) -> str:
    if knowledge_price:
        return "knowledge_base"
    if known:
        return "fallback_known"
    return "fallback_rule"


def _reference_ticket_price(category: str, name: str) -> int:
    combined = f"{category} {name}"
    if any(token in combined for token in ("动物园", "乐园", "游乐")):
        return 45
    if any(token in combined for token in ("度假区", "风景区", "景区", "温泉")):
        return 60
    if any(token in combined for token in ("水镇", "古镇", "古街", "街区", "步行街", "夜市", "市场", "商场")):
        return 20
    if any(token in combined for token in ("山", "湖", "湿地", "自然")) and "公园" not in combined:
        return 30
    if any(token in combined for token in ("博物馆", "纪念馆", "公园", "广场")):
        return 0
    return 30


def _lookup_known_status(name: str) -> dict[str, Any] | None:
    if name in KNOWN_SCENIC_STATUS:
        return KNOWN_SCENIC_STATUS[name]
    for key, value in KNOWN_SCENIC_STATUS.items():
        if key in name or name in key:
            return value
    return None


def _fallback_status(category: str, name: str) -> str:
    if "博物馆" in category or "博物馆" in name or "纪念馆" in name:
        return "可能需预约"
    if "街" in name or "商场" in name or "市场" in name:
        return "通常开放"
    return "开放状态待官方确认"


def _fallback_announcement(category: str, name: str) -> str:
    if "博物馆" in category or "博物馆" in name or "纪念馆" in name:
        return "博物馆类场馆可能周一闭馆或预约入馆。"
    if "自然" in category or "山" in name or "湖" in name:
        return "自然景区可能受天气、维护或限流影响。"
    return "未接入实时公告，建议出行前查看官方平台。"
