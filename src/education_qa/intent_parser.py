from __future__ import annotations

import json
import re
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

from .app_config import AppConfig, get_config
from .deepseek_client import DeepSeekClient
from .geo_tools import CITY_CENTERS
from .paths import TOURISM_VECTORSTORE_PATH
from .retriever import TfidfRagStore
from .tourism import search_tourism_records
from .trip_planner import (
    _clean,
    _extract_user_place_names,
    _filter_user_place_names,
    _normalize_interests,
    _resolve_semantic_requested_places,
)
from .transport_tools import INTERCITY_MODES, LOCAL_MODES


CN_NUMBERS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

DESTINATION_ALIASES = {
    "四川": "成都",
    "川西": "成都",
    "浙江": "杭州",
    "陕西": "西安",
    "江苏": "南京",
}

ACCOMMODATION_OPTIONS = [
    ("民宿", "民宿"),
    ("豪华", "豪华酒店"),
    ("高端", "豪华酒店"),
    ("舒适", "舒适型酒店"),
    ("宾馆", "经济型酒店"),
    ("经济", "经济型酒店"),
    ("便宜", "经济型酒店"),
    ("青旅", "经济型酒店"),
]

TRANSPORTATION_OPTIONS = [
    ("自驾", "自驾"),
    ("打车", "打车优先"),
    ("网约车", "打车优先"),
    ("步行", "步行优先"),
    ("地铁", "公共交通优先"),
    ("公交", "公共交通优先"),
    ("公共交通", "公共交通优先"),
]

LONG_DISTANCE_TERMS = ("高铁", "火车", "动车", "机票", "飞机", "大巴", "客车", "自驾", "骑行", "往返", "大交通", "城际")
UNSUPPORTED_INTERCITY_MODES = {"飞机"}
RETURN_NEXT_DAY_TERMS = (
    "玩好了后走",
    "玩好后走",
    "玩完后走",
    "玩完了再走",
    "玩完再走",
    "玩好了再走",
    "玩好再走",
    "最后一天玩完",
    "最后一天玩好了",
    "最后一天玩好",
    "最后一天玩完再回",
    "多住一晚",
    "住一晚再走",
    "第二天回",
    "次日回",
    "隔天回",
)


def parse_travel_intent(
    text: str,
    *,
    config: AppConfig | None = None,
    llm_client: DeepSeekClient | None = None,
) -> dict[str, Any]:
    config = config or get_config()
    llm_client = llm_client or DeepSeekClient(config)
    llm_intent = _llm_intent(text, llm_client)
    fallback = _rule_based_intent(text)
    intent = _merge_intents(fallback, llm_intent)
    intent["cards"] = _build_cards(intent)
    intent["plan_payload"] = _build_plan_payload(intent)
    intent["tool_status"] = {
        "deepseek": llm_client.enabled and bool(llm_intent),
        "fallback_parser": not bool(llm_intent),
        "intent_source": "deepseek" if llm_intent else "rule_fallback",
    }
    return intent


def _rule_based_intent(text: str) -> dict[str, Any]:
    raw_text = _clean(text)
    city = _extract_city(raw_text)
    days = _extract_days(raw_text)
    budget, budget_is_explicit = _extract_budget_value(raw_text)
    budget_scope, include_long_distance = _extract_budget_scope(raw_text, budget)
    intercity_options = _extract_intercity_options(raw_text)
    local_transportation = _extract_transportation(raw_text)
    mobility_constraints = _extract_mobility_constraints(raw_text)
    start_date = _extract_start_date(raw_text)
    return_date_policy = _extract_return_date_policy(raw_text)
    return_date = _return_date_from(start_date, days, return_date_policy)
    interests = _normalize_interests(None, raw_text)
    requested_places = _filter_user_place_names(
        city,
        [*_extract_user_place_names(city, raw_text), *_rag_semantic_requested_places(city, raw_text)],
    )

    return {
        "original_text": raw_text,
        "city": city,
        "origin": _extract_origin(raw_text, city),
        "days": days,
        "start_date": start_date,
        "return_date": return_date,
        "return_date_policy": return_date_policy,
        "budget": budget,
        "budget_is_explicit": budget_is_explicit,
        "budget_scope": budget_scope,
        "budget_includes_intercity_transport": include_long_distance,
        "budget_includes_long_distance": include_long_distance,
        "intercity_transportation": _selected_intercity_transportation(intercity_options),
        "intercity_options": intercity_options,
        "interests": interests,
        "requested_places": requested_places,
        "transportation": local_transportation,
        "local_transportation": local_transportation,
        "mobility_constraints": mobility_constraints,
        "accommodation": _extract_accommodation(raw_text),
        "free_text": raw_text,
        "confidence": "rule-based",
        "needs_confirmation": _needs_confirmation(budget, include_long_distance),
    }


def _llm_intent(text: str, llm_client: DeepSeekClient) -> dict[str, Any]:
    if not llm_client.enabled:
        return {}

    schema = {
        "city": "目的地城市，必须是中文城市名",
        "origin": "出发地，没有则空字符串",
        "days": "旅行天数，整数",
        "start_date": "YYYY-MM-DD，没有则空字符串",
        "return_date": "返程日期 YYYY-MM-DD，没有则空字符串",
        "return_date_policy": "返程日期规则：last_day 或 next_day_after_last_day",
        "budget": "数字预算，没有则0",
        "budget_scope": "预算范围说明，例如仅目的地内消费/包含往返城际交通/未说明",
        "budget_includes_intercity_transport": "true/false/null",
        "budget_includes_long_distance": "兼容字段，true/false/null",
        "intercity_transportation": "高铁/火车/长途大巴/自驾/骑行/未确定",
        "intercity_options": ["用户可接受的城际交通方式"],
        "interests": ["历史", "美食"],
        "requested_places": ["用户明确想去的地点"],
        "transportation": "目的地内交通偏好：公共交通优先/步行优先/共享单车优先/打车优先/自驾",
        "local_transportation": "同 transportation",
        "mobility_constraints": ["不打车", "少走路", "不骑车"],
        "accommodation": "经济型酒店/舒适型酒店/豪华酒店/民宿",
    }
    reply = llm_client.complete(
        [
            {
                "role": "system",
                "content": (
                    "你是旅游助手的意图识别器。只输出一个 JSON 对象，不要解释。"
                    "你必须直接理解用户原话并抽取字段；不要把整句话、请求动作或客套话当成地点。"
                    "requested_places 只填用户明确点名的景点/场馆/街区/商圈等专名，没有明确地点就填空数组。"
                    "如果用户说看小动物、小动物或想去看动物，requested_places 应理解为“目的地城市+动物园”。"
                    "如果用户说坐高铁、火车或动车去目的地，intercity_transportation 必须填“高铁/火车”，"
                    "intercity_options 必须包含“高铁/火车”。"
                    "当前系统不支持飞机/机票/航班查询；用户提到飞机时，intercity_transportation 填“未确定”，"
                    "intercity_options 填空数组。"
                    "预算是否包含从出发地到目的地的高铁、机票、火车等大交通，如果用户没说清楚，"
                    "budget_includes_intercity_transport 必须是 null，budget_scope 写“未说明是否包含往返城际交通”。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"user_text": text, "schema": schema}, ensure_ascii=False),
            },
        ],
        temperature=0.0,
    )
    return _parse_json_object(reply)


def _parse_json_object(text: str) -> dict[str, Any]:
    if not text:
        return {}
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _merge_intents(fallback: dict[str, Any], llm_intent: dict[str, Any]) -> dict[str, Any]:
    if not llm_intent:
        return fallback

    merged = dict(fallback)
    for key in (
        "city",
        "origin",
        "start_date",
        "budget_scope",
        "transportation",
        "local_transportation",
        "accommodation",
    ):
        value = _clean(llm_intent.get(key))
        if value:
            merged[key] = value

    intercity_transportation = _clean(llm_intent.get("intercity_transportation"))
    if intercity_transportation and intercity_transportation != "未确定":
        merged["intercity_transportation"] = intercity_transportation

    days = _as_int(llm_intent.get("days"), default=0)
    if days:
        merged["days"] = max(1, min(7, days))

    if "budget" in llm_intent:
        budget = _as_int(llm_intent.get("budget"), default=0)
        merged["budget"] = max(0, min(100000, budget))
        merged["budget_is_explicit"] = bool(merged["budget"])

    has_budget_scope_flag = (
        "budget_includes_intercity_transport" in llm_intent or "budget_includes_long_distance" in llm_intent
    )
    include_long_distance = llm_intent.get(
        "budget_includes_intercity_transport",
        llm_intent.get("budget_includes_long_distance"),
    )
    if has_budget_scope_flag and (isinstance(include_long_distance, bool) or include_long_distance is None):
        merged["budget_includes_intercity_transport"] = include_long_distance
        merged["budget_includes_long_distance"] = include_long_distance

    for key in ("interests", "requested_places", "intercity_options", "mobility_constraints"):
        value = llm_intent.get(key)
        if isinstance(value, list):
            cleaned = [_clean(item) for item in value if _clean(item)]
            if key == "requested_places":
                cleaned = _filter_user_place_names(merged.get("city", ""), [*(merged.get("requested_places") or []), *cleaned])
                if not cleaned:
                    continue
            if key == "intercity_options":
                cleaned = _normalize_intercity_options(cleaned)
            merged[key] = cleaned[:8]

    merged["intercity_options"] = _normalize_intercity_options(merged.get("intercity_options") or [])
    if not merged["intercity_options"]:
        merged["intercity_options"] = _normalize_intercity_options(
            _extract_intercity_options(merged.get("intercity_transportation", ""))
        )
    if not merged["intercity_options"]:
        merged["intercity_options"] = fallback.get("intercity_options", [])
    merged["intercity_transportation"] = _selected_intercity_transportation(
        merged["intercity_options"] or [merged.get("intercity_transportation", "")]
    )
    relative_start_date = _extract_relative_start_date(merged.get("free_text") or merged.get("original_text") or "")
    if relative_start_date:
        merged["start_date"] = relative_start_date
    text = merged.get("free_text") or merged.get("original_text") or ""
    rule_return_date_policy = _extract_return_date_policy(text)
    return_date_policy = _clean(llm_intent.get("return_date_policy")) or rule_return_date_policy
    if return_date_policy not in {"last_day", "next_day_after_last_day"}:
        return_date_policy = rule_return_date_policy
    if rule_return_date_policy == "next_day_after_last_day":
        return_date_policy = rule_return_date_policy
    computed_return_date = _return_date_from(
        merged.get("start_date") or fallback.get("start_date"),
        int(merged.get("days") or fallback.get("days") or 1),
        return_date_policy,
    )
    if rule_return_date_policy == "next_day_after_last_day":
        return_date = computed_return_date
    else:
        return_date = _clean(llm_intent.get("return_date")) or computed_return_date
    merged["return_date_policy"] = return_date_policy
    merged["return_date"] = return_date
    merged["local_transportation"] = merged.get("local_transportation") or merged.get("transportation") or "公共交通优先"
    merged["transportation"] = merged["local_transportation"]
    merged["confidence"] = "llm"
    merged["needs_confirmation"] = _needs_confirmation(
        merged.get("budget"),
        merged.get("budget_includes_intercity_transport"),
    )
    return merged


def _rag_semantic_requested_places(city: str, text: str) -> list[str]:
    store = _tourism_store()
    if not store or not city or not text:
        return []
    results = search_tourism_records(f"{city} {text} 景点 活动 观光", store, city=city, top_k=16)
    return _resolve_semantic_requested_places(city, text, results)


@lru_cache(maxsize=1)
def _tourism_store() -> TfidfRagStore | None:
    if not TOURISM_VECTORSTORE_PATH.exists():
        return None
    try:
        return TfidfRagStore.load(TOURISM_VECTORSTORE_PATH)
    except Exception:
        return None


def _build_cards(intent: dict[str, Any]) -> list[dict[str, Any]]:
    cards = [
        {
            "key": "original_text",
            "label": "用户原话",
            "value": intent["original_text"] or "未输入",
            "tone": "plain",
        },
        {"key": "city", "label": "目的地", "value": intent["city"] or "待填写", "tone": "primary"},
        {"key": "origin", "label": "出发地", "value": intent.get("origin", "") or "未指定", "tone": "plain"},
        {"key": "days", "label": "行程天数", "value": f"{intent['days']}天", "tone": "plain"},
        {"key": "start_date", "label": "出发日期", "value": _display_date(intent.get("start_date")), "tone": "plain"},
        {
            "key": "return_date",
            "label": "返程日期",
            "value": _display_date(intent.get("return_date")),
            "tone": "plain",
            "note": _return_date_note(intent.get("return_date_policy")),
        },
        {
            "key": "intercity_transportation",
            "label": "城际交通",
            "value": intent.get("intercity_transportation") or "未确定",
            "tone": "warning" if intent.get("intercity_transportation") == "未确定" else "plain",
        },
        {
            "key": "budget",
            "label": "预算",
            "value": f"{intent['budget']}元" if intent["budget"] else "未提供",
            "tone": "warning" if intent.get("budget_includes_intercity_transport") is None else "plain",
            "note": intent["budget_scope"],
        },
        {
            "key": "interests",
            "label": "偏好",
            "value": "、".join(intent["interests"]),
            "tone": "plain",
        },
        {
            "key": "requested_places",
            "label": "想去地点",
            "value": "、".join(intent["requested_places"]) if intent["requested_places"] else "未指定",
            "tone": "plain",
        },
        {"key": "transportation", "label": "当地交通", "value": intent["local_transportation"], "tone": "plain"},
        {
            "key": "mobility_constraints",
            "label": "交通约束",
            "value": "、".join(intent.get("mobility_constraints") or ["无硬性限制"]),
            "tone": "plain",
        },
        {"key": "accommodation", "label": "住宿", "value": intent["accommodation"], "tone": "plain"},
    ]
    return cards


def _build_plan_payload(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": intent["city"],
        "origin": intent.get("origin", ""),
        "days": intent["days"],
        "start_date": intent["start_date"],
        "return_date": intent.get("return_date") or _return_date_from(
            intent["start_date"],
            intent["days"],
            intent.get("return_date_policy") or "last_day",
        ),
        "return_date_policy": intent.get("return_date_policy") or "last_day",
        "budget": intent["budget"],
        "budget_is_explicit": intent.get("budget_is_explicit", False),
        "budget_scope": intent["budget_scope"],
        "budget_includes_intercity_transport": intent.get("budget_includes_intercity_transport"),
        "budget_includes_long_distance": intent.get("budget_includes_long_distance"),
        "intercity_transportation": intent.get("intercity_transportation", "未确定"),
        "intercity_options": intent.get("intercity_options", []),
        "interests": intent["interests"],
        "requested_places": intent.get("requested_places", []),
        "transportation": intent["local_transportation"],
        "local_transportation": intent["local_transportation"],
        "mobility_constraints": intent.get("mobility_constraints", []),
        "accommodation": intent["accommodation"],
        "free_text": intent["free_text"],
    }


def _extract_city(text: str) -> str:
    destination = _extract_destination_from_phrase(text)
    if destination:
        return destination

    for city in sorted(CITY_CENTERS, key=len, reverse=True):
        if city in text:
            return city
    for alias, city in DESTINATION_ALIASES.items():
        if alias in text:
            return city
    return ""


def _extract_destination_from_phrase(text: str) -> str:
    patterns = [
        r"(?:去|到|前往|抵达)([\u4e00-\u9fff]{2,8}?)(?=玩|旅游|旅行|游玩|看|逛|住|出差|，|,|。|；|;|\s|$)",
        r"(?:在)([\u4e00-\u9fff]{2,8}?)(?=玩|旅游|旅行|游玩)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        city = _clean_city_candidate(match.group(1))
        if city:
            return DESTINATION_ALIASES.get(city, city)
    return ""


def _clean_city_candidate(value: str) -> str:
    city = _clean(value)
    city = re.sub(r"(?:玩|游玩|旅游|旅行)?[一二两三四五六七八九十\d]+(?:天|日|晚).*$", "", city)
    city = re.sub(r"(市|地区|景区|附近|周边)$", "", city)
    bad_words = {"哪里", "哪些", "那里", "这里", "景区", "地方"}
    if city in bad_words or len(city) < 2:
        return ""
    return city


def _extract_origin(text: str, city: str) -> str:
    patterns = [
        r"(?:从|我从|出发地(?:是|在)?)([\u4e00-\u9fffA-Za-z]{1,12})(?:出发|去|到|过去)",
        r"([\u4e00-\u9fffA-Za-z]{1,12})(?:出发)(?:去|到)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        origin = _clean(match.group(1))
        if origin and origin != city:
            return origin
    return ""


def _extract_days(text: str) -> int:
    match = re.search(r"([1-7一二两三四五六七])\s*(?:天|日|晚)", text)
    if match:
        raw = match.group(1)
        return int(raw) if raw.isdigit() else CN_NUMBERS.get(raw, 2)
    if "周末" in text:
        return 2
    return 2


def _extract_budget(text: str) -> int:
    budget, _ = _extract_budget_value(text)
    return budget


def _extract_budget_value(text: str) -> tuple[int, bool]:
    amount_chars = r"\d{2,6}|[零〇一二两三四五六七八九十百千万]{1,12}"
    patterns = [
        rf"(?:预算|花费|费用|人均|总共|总预算)[^\d零〇一二两三四五六七八九十百千万]{{0,8}}({amount_chars})",
        rf"({amount_chars})\s*(?:元|块钱|块|人民币)(?:以内|左右|上下|预算)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _parse_budget_amount(match.group(1))
            if value:
                return max(0, min(100000, value)), True
    return 0, False


def _parse_budget_amount(value: str) -> int:
    text = _clean(value)
    if not text:
        return 0
    if text.isdigit():
        return int(text)

    def digit(raw: str) -> int:
        return int(raw) if raw.isdigit() else CN_NUMBERS.get(raw, 0)

    colloquial = re.fullmatch(r"([1-9一二两三四五六七八九])千([1-9一二两三四五六七八九])", text)
    if colloquial:
        return digit(colloquial.group(1)) * 1000 + digit(colloquial.group(2)) * 100

    colloquial = re.fullmatch(r"([1-9一二两三四五六七八九])万([1-9一二两三四五六七八九])", text)
    if colloquial:
        return digit(colloquial.group(1)) * 10000 + digit(colloquial.group(2)) * 1000

    total = 0
    section = 0
    number = 0
    units = {"十": 10, "百": 100, "千": 1000}
    for char in text:
        if char.isdigit() or char in CN_NUMBERS:
            number = digit(char)
            continue
        if char in units:
            section += (number or 1) * units[char]
            number = 0
            continue
        if char == "万":
            total += (section + number or 1) * 10000
            section = 0
            number = 0
    return total + section + number


def _extract_budget_scope(text: str, budget: int) -> tuple[str, bool | None]:
    if not budget:
        return "未提供预算", None

    mentions_long_distance = any(term in text for term in LONG_DISTANCE_TERMS)
    if mentions_long_distance and re.search(r"(不确定|不知道|不清楚|没说清|包不包括|包不包含|含不含)", text):
        return "提到了城际交通，但是否计入预算仍需确认", None
    if mentions_long_distance and re.search(r"(不包含|不包括|不含|另算|不算)", text):
        return "仅目的地内消费，不含往返城际交通", False
    if mentions_long_distance and re.search(r"(包含|包括|含|算上|加上)", text):
        return "包含往返城际交通", True
    if mentions_long_distance:
        return "提到了城际交通，但是否计入预算仍需确认", None
    return "未说明是否包含往返城际交通", None


def _extract_start_date(text: str) -> str:
    relative = _extract_relative_start_date(text)
    if relative:
        return relative
    full = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})", text)
    if full:
        return _safe_date(int(full.group(1)), int(full.group(2)), int(full.group(3)))
    month_day = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", text)
    if month_day:
        today = date.today()
        return _safe_date(today.year, int(month_day.group(1)), int(month_day.group(2)))
    return date.today().isoformat()


def _extract_return_date_policy(text: str) -> str:
    return "next_day_after_last_day" if any(term in text for term in RETURN_NEXT_DAY_TERMS) else "last_day"


def _return_date_from(start_date: str, days: int, policy: str) -> str:
    try:
        start = date.fromisoformat(str(start_date))
    except (TypeError, ValueError):
        start = date.today()
    offset = max(0, int(days or 1) - 1)
    if policy == "next_day_after_last_day":
        offset += 1
    return (start + timedelta(days=offset)).isoformat()


def _display_date(value: Any) -> str:
    text = _clean(value)
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return text or "未确定"
    return parsed.strftime("%Y.%m.%d")


def _return_date_note(policy: str | None) -> str:
    if policy == "next_day_after_last_day":
        return "按玩好后次日返程查询。"
    return "默认按最后一天返程查询。"


def _extract_relative_start_date(text: str) -> str:
    today = date.today()
    if "后天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "明天" in text or "明日" in text:
        return (today + timedelta(days=1)).isoformat()
    if "今天" in text or "今日" in text:
        return today.isoformat()
    return ""


def _extract_intercity_options(text: str) -> list[str]:
    options: list[str] = []
    mapping = [
        (("高铁", "火车", "动车", "铁路"), "高铁/火车"),
        (("大巴", "客车", "长途汽车", "汽车"), "长途大巴"),
        (("自驾", "开车"), "自驾"),
        (("骑行", "骑车", "自行车"), "骑行"),
    ]
    for keywords, option in mapping:
        if any(keyword in text for keyword in keywords) and option not in options:
            options.append(option)
    return options


def _normalize_intercity_options(options: list[str]) -> list[str]:
    normalized: list[str] = []
    for option in options:
        if option in UNSUPPORTED_INTERCITY_MODES:
            continue
        values = _extract_intercity_options(option)
        if not values and option in INTERCITY_MODES:
            values = [option]
        for value in values:
            if value not in UNSUPPORTED_INTERCITY_MODES and value not in normalized:
                normalized.append(value)
    return normalized


def _selected_intercity_transportation(options: list[str]) -> str:
    cleaned = _normalize_intercity_options(options)
    if not cleaned:
        return "未确定"
    if len(cleaned) == 1:
        return cleaned[0]
    return " / ".join(cleaned)


def _extract_mobility_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    checks = [
        (("不打车", "不要打车", "不想打车", "少打车"), "不打车"),
        (("不要走太远", "少走路", "不想走太多", "走路少一点"), "少走路"),
        (("不骑车", "不要骑车", "不坐共享单车"), "不骑车"),
        (("禁摩", "限摩", "摩托", "电动车"), "避开摩托/电动车"),
        (("不要绕路", "不绕路", "少绕路", "避免绕路", "通勤方便"), "少绕路"),
        (("省钱", "预算紧", "便宜"), "预算优先"),
        (("时间紧", "赶时间"), "时间优先"),
    ]
    for keywords, value in checks:
        if any(keyword in text for keyword in keywords) and value not in constraints:
            constraints.append(value)
    return constraints


def _safe_date(year: int, month: int, day: int) -> str:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return date.today().isoformat()


def _extract_transportation(text: str) -> str:
    if "共享单车" in text or "单车" in text or "骑车" in text:
        return "共享单车优先"
    for keyword, value in TRANSPORTATION_OPTIONS:
        if keyword in text:
            return value
    return "公共交通优先"


def _extract_accommodation(text: str) -> str:
    for keyword, value in ACCOMMODATION_OPTIONS:
        if keyword in text:
            return value
    return "经济型酒店"


def _needs_confirmation(budget: int, include_long_distance: bool | None) -> list[str]:
    needs = []
    if budget and include_long_distance is None:
        needs.append("预算是否包含往返城际交通")
    return needs


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default
