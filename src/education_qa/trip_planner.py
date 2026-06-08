from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .app_config import AppConfig, get_config
from .deepseek_client import DeepSeekClient
from .geo_tools import AmapClient, fallback_hotels, fallback_location, haversine_km
from .hotel_reviews import load_hotel_review_insights
from .paths import TOURISM_VECTORSTORE_PATH
from .railway_tools import Railway12306Client
from .retriever import TfidfRagStore
from .scenic_status import scenic_status_for_stop, summarize_scenic_status
from .search_tools import WebSearchClient
from .transport_tools import build_mobility_policy, estimate_intercity_transport, estimate_local_route
from .tourism import search_tourism_records


LISTING_RE = re.compile(r"(观光|活动|饮食|用餐|购物|夜生活|住宿|地点)：([^；\n]{2,60})")
PRICE_RE = re.compile(r"(费用|门票|票价)：?[^0-9¥￥]*(?:¥|￥)?\s*(\d{1,4})")
ADDRESS_RE = re.compile(r"地址：([^；\n]+)")
HOURS_RE = re.compile(r"开放时间：([^；\n]+)")
FOOD_RE = re.compile(r"著名食物有：([^。；\n]+)")
USER_PLACE_HINT_RE = re.compile(
    r"(?:想去|想看|想逛|想要看|想去看|去看|必去|必须去|一定要去|要去|要看|打卡|安排|包含|包括)"
    r"([^。；;，,\n]{2,80})"
)
EXPLICIT_STOP_RE = re.compile(
    r"[\u4e00-\u9fffA-Za-z0-9·]{2,20}"
    r"(?:博物馆|纪念馆|古街|巷子|公园|寺|祠|宫|塔|山|湖|湿地|基地|景区|遗址|街区|广场|古镇|乐园|动物园|植物园|夜市|市场|商场|步行街|茶馆)"
)
GENERIC_PLACE_NAMES = {"低廉", "中等", "高級", "高级", "奢侈", "經濟級", "经济级", "概况", "概览"}
GENERIC_USER_PLACE_NAMES = {
    "观光",
    "历史",
    "文化",
    "美食",
    "自然",
    "购物",
    "亲子",
    "路线",
    "天气",
    "预算",
    "酒店",
    "住宿",
    "交通",
    "攻略",
    "景区",
    "景点",
    "地方",
    "玩的地方",
    "美食街区",
    "历史街区",
    "观光景点",
    "景点和美食",
    "美食和景点",
    "景区和美食",
    "景点美食",
    "美食景点",
    "最好是景区",
    "然后最好是景区",
}

INTEREST_KEYWORDS = {
    "观光": ["观光", "景点", "景区", "游玩", "玩", "风景", "公园", "广场", "塔", "湖", "山"],
    "历史": ["历史", "文化", "博物馆", "遗址", "古", "祠", "寺", "宫", "城", "街"],
    "美食": ["美食", "用餐", "饮食", "餐", "小吃", "茶", "面", "火锅"],
    "自然": ["自然", "公园", "山", "湖", "湿地", "动物", "植物"],
    "购物": ["购物", "商场", "市场", "街"],
    "夜生活": ["夜生活", "酒吧", "夜市"],
    "亲子": ["亲子", "动物", "博物馆", "乐园", "公园"],
}

SEMANTIC_PLACE_INTENTS = [
    {
        "tokens": ("小动物", "看动物", "动物", "亲子动物"),
        "terms": ("动物园", "野生动物", "海洋世界", "熊猫", "动物"),
        "fallback": "动物园",
    },
    {
        "tokens": ("玩水", "水上", "水世界", "水乐园", "水公园", "漂流", "游泳", "亲水"),
        "terms": ("水世界", "水上", "水乐园", "水公园", "漂流", "海洋", "温泉", "沙滩", "泳"),
        "fallback": "水世界",
    },
]

FALLBACK_ATTRACTIONS = {
    "成都": [
        ("武侯祠", "历史文化", "三国文化主题景点，适合了解蜀汉历史。"),
        ("锦里古街", "街区美食", "传统街区和小吃集中，适合晚间散步。"),
        ("宽窄巷子", "历史街区", "成都老街区改造后的休闲街区。"),
        ("成都博物馆", "博物馆", "适合室内历史文化参观。"),
        ("人民公园", "城市休闲", "茶馆和慢生活体验集中。"),
        ("都江堰", "历史工程", "世界文化遗产，适合安排半日到一日。"),
    ],
    "杭州": [
        ("西湖", "自然观光", "杭州经典景观，适合步行和骑行。"),
        ("灵隐寺", "历史文化", "杭州知名寺院和文化景点。"),
        ("西溪湿地", "自然风光", "城市湿地公园，适合慢游。"),
        ("清河坊", "历史街区", "老街区、美食和伴手礼集中。"),
        ("大运河", "历史文化", "世界文化遗产相关水系和仓储遗迹。"),
    ],
    "铜陵": [
        ("天井湖公园", "自然观光", "铜陵城市湖景公园，适合散步和轻松观光。"),
        ("铜陵博物馆", "历史文化", "适合了解铜文化、地方历史和城市发展。"),
        ("大通古镇", "历史街区", "临江古镇街区，适合慢游和拍照。"),
        ("永泉旅游度假区", "自然休闲", "适合安排半日休闲游，注意以实际开放信息为准。"),
        ("犁桥水镇", "街区观光", "水乡风格街区，适合傍晚散步和夜景。"),
        ("铜官山", "城市观光", "与铜陵铜文化相关的城市地标区域。"),
    ],
}


@dataclass
class PlannerContext:
    config: AppConfig
    map_client: AmapClient
    llm_client: DeepSeekClient
    search_client: WebSearchClient
    railway_client: Railway12306Client


class TourismTripPlanner:
    def __init__(
        self,
        store_path: Path = TOURISM_VECTORSTORE_PATH,
        *,
        config: AppConfig | None = None,
        map_client: AmapClient | None = None,
        llm_client: DeepSeekClient | None = None,
    ):
        self.store_path = store_path
        self.config = config or get_config()
        self.store = TfidfRagStore.load(store_path)
        self.context = PlannerContext(
            config=self.config,
            map_client=map_client or AmapClient(self.config),
            llm_client=llm_client or DeepSeekClient(self.config),
            search_client=WebSearchClient(self.config),
            railway_client=Railway12306Client(self.config),
        )

    def plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        city = _clean(payload.get("city")) or "成都"
        days = _coerce_int(payload.get("days") or payload.get("travel_days"), default=2, minimum=1, maximum=7)
        budget = _coerce_int(payload.get("budget"), default=1200, minimum=0, maximum=100000)
        start_date = _parse_start_date(payload.get("start_date"))
        return_date_policy = _clean(payload.get("return_date_policy")) or "last_day"
        return_date = _parse_return_date(payload.get("return_date"), start_date, days, return_date_policy)
        origin = _clean(payload.get("origin"))
        budget_scope = _clean(payload.get("budget_scope")) or "未说明是否包含往返城际交通"
        include_intercity_budget = _coerce_optional_bool(
            payload.get("budget_includes_intercity_transport", payload.get("budget_includes_long_distance"))
        )
        intercity_options = _normalize_list(payload.get("intercity_options"))
        intercity_transportation = _clean(payload.get("intercity_transportation"))
        if intercity_transportation and intercity_transportation != "未确定":
            intercity_options.extend(re.split(r"\s*/\s*|、|,|，", intercity_transportation))
        selected_train_index = _coerce_optional_int(payload.get("selected_train_index"))
        selected_train_ticket = payload.get("selected_train_ticket") if isinstance(payload.get("selected_train_ticket"), dict) else None
        selected_return_train_index = _coerce_optional_int(payload.get("selected_return_train_index"))
        selected_return_train_ticket = (
            payload.get("selected_return_train_ticket") if isinstance(payload.get("selected_return_train_ticket"), dict) else None
        )
        intercity_departure_time = _clean(payload.get("intercity_departure_time") or payload.get("departure_time"))
        local_transportation = _clean(payload.get("local_transportation") or payload.get("transportation")) or "公共交通优先"
        mobility_constraints = _normalize_list(payload.get("mobility_constraints"))
        transportation = local_transportation
        accommodation = _clean(payload.get("accommodation")) or "经济型酒店"
        interests = _normalize_interests(payload.get("interests"), payload.get("free_text"))
        free_text = _clean(payload.get("free_text"))

        query = " ".join([city, *interests, free_text, "旅游 攻略 景点 用餐 住宿 交通"])
        retrieved = search_tourism_records(query, self.store, city=city, top_k=24)
        requested_places = _merge_unique_lists(
            _normalize_list(payload.get("requested_places")),
            _extract_user_place_names(city, free_text),
            _resolve_semantic_requested_places(city, free_text, retrieved),
        )
        requested_places = _filter_user_place_names(city, requested_places)
        candidates = self._extract_candidates(city, retrieved, interests)
        candidates = self._add_user_requested_candidates(city, candidates, requested_places, retrieved, interests)
        candidates = self._ensure_candidates(city, candidates, interests)
        enriched = self._enrich_candidates(city, candidates)

        selected = _select_stops(enriched, days)
        weather = self._build_weather(city, start_date, days)
        review_insights = load_hotel_review_insights()
        budget_level = _budget_level(budget, days)
        meal_suggestions = self._meal_suggestions(retrieved, city)
        mobility_policy = build_mobility_policy(city, local_transportation, mobility_constraints)
        railway_lookup = self.context.railway_client.query_train_option if self.context.railway_client.enabled else None
        intercity_transport = estimate_intercity_transport(
            origin,
            city,
            modes=intercity_options,
            include_round_trip=True,
            included_in_budget=bool(include_intercity_budget),
            travel_date=start_date,
            return_date=return_date,
            railway_lookup=railway_lookup,
            selected_train_index=selected_train_index,
            selected_train_ticket=selected_train_ticket,
            selected_return_train_index=selected_return_train_index,
            selected_return_train_ticket=selected_return_train_ticket,
            departure_time=intercity_departure_time,
        )

        day_plans = []
        for day_index in range(days):
            day_stops = selected[day_index * 3 : (day_index + 1) * 3]
            day_stops = _order_day_stops(day_stops)
            for stop_index, stop in enumerate(day_stops):
                hotels = self.context.map_client.nearby_hotels(
                    stop["location"],
                    city,
                    accommodation=accommodation,
                    limit=4,
                )
                if not hotels:
                    hotels = fallback_hotels(
                        stop["name"],
                        city,
                        accommodation=accommodation,
                        budget_level=budget_level,
                )
                hotels = _attach_hotel_review_profiles(hotels, review_insights, accommodation)
                stop["nearby_hotels"] = hotels
                stop["order"] = stop_index + 1
                stop["business_hours"] = _visit_window_label(stop)
                stop["scenic_status"] = scenic_status_for_stop(
                    stop,
                    city,
                    search_client=self.context.search_client,
                )
                stop["ticket_price"] = stop["scenic_status"]["ticket_price"]

            routes = [
                estimate_local_route(
                    day_stops[index],
                    day_stops[index + 1],
                    preference=local_transportation,
                    mobility_policy=mobility_policy,
                    budget_level=budget_level,
                )
                for index in range(max(0, len(day_stops) - 1))
            ]
            hotel = day_stops[0]["nearby_hotels"][0] if day_stops and day_stops[0].get("nearby_hotels") else None
            meals = _build_meals(meal_suggestions, day_index, budget_level)
            _attach_meal_context(meals, day_stops, self.context.map_client, city)
            hotel_transfers = _build_hotel_transfers(
                hotel,
                day_stops,
                preference=local_transportation,
                mobility_policy=mobility_policy,
                budget_level=budget_level,
            )
            timeline_info = _build_day_timeline(
                city=city,
                day_index=day_index,
                stops=day_stops,
                routes=routes,
                meals=meals,
                hotel=hotel,
                hotel_transfers=hotel_transfers,
                intercity_transport=intercity_transport,
            )
            day_plans.append(
                {
                    "date": (start_date + timedelta(days=day_index)).isoformat(),
                    "day_index": day_index,
                    "title": f"第{day_index + 1}天",
                    "theme": _day_theme(day_stops, interests),
                    "city": city,
                    "transportation": transportation,
                    "hotel": hotel,
                    "stops": day_stops,
                    "routes": routes,
                    "meals": meals,
                    "hotel_transfers": hotel_transfers,
                    "timeline": timeline_info["items"],
                    "time_note": timeline_info["note"],
                    "day_start_time": timeline_info["day_start_time"],
                    "day_end_time": timeline_info["day_end_time"],
                }
            )

        scenic_status_summary = summarize_scenic_status(day_plans)
        budget_detail = _build_budget(
            day_plans,
            budget=budget,
            intercity_transport=intercity_transport,
            include_intercity=bool(include_intercity_budget),
        )
        budget_note = _budget_note(budget_scope, include_intercity_budget)
        suggestions = self._build_suggestions(city, interests, budget, day_plans, weather, meal_suggestions)
        rag_context = _build_location_rag_context(city, day_plans, self.store, retrieved)

        return {
            "success": True,
            "message": "规划完成",
            "data": {
                "city": city,
                "days_count": days,
                "start_date": start_date.isoformat(),
                "end_date": (start_date + timedelta(days=days - 1)).isoformat(),
                "return_date": return_date.isoformat(),
                "return_date_policy": return_date_policy,
                "origin": origin,
                "interests": interests,
                "transportation": local_transportation,
                "local_transportation": local_transportation,
                "mobility_constraints": mobility_constraints,
                "mobility_policy": mobility_policy,
                "intercity_transportation": intercity_transport.get("selected_mode"),
                "intercity_transport": intercity_transport,
                "accommodation": accommodation,
                "budget_limit": budget,
                "budget_scope": budget_scope,
                "budget_includes_intercity_transport": include_intercity_budget,
                "budget_note": budget_note,
                "overall_suggestions": suggestions,
                "weather_info": weather,
                "days": day_plans,
                "budget": budget_detail,
                "scenic_status_summary": scenic_status_summary,
                "hotel_review_insights": review_insights,
                "rag_context": rag_context,
                "tool_status": {
                    "rag": True,
                    "amap_web_service": self.context.map_client.enabled,
                    "amap_js": self.config.has_amap_js,
                    "deepseek": self.context.llm_client.enabled,
                    "intercity_transport": _intercity_tool_status(intercity_transport),
                    "mobility_policy": "fallback-policy",
                    "scenic_status": "web-search" if self.config.has_search_api else "fallback-status",
                    "route": "policy-distance-estimate",
                },
            },
        }

    def preview_intercity(self, payload: dict[str, Any]) -> dict[str, Any]:
        city = _clean(payload.get("city"))
        origin = _clean(payload.get("origin"))
        start_date = _parse_start_date(payload.get("start_date"))
        days = _coerce_int(payload.get("days") or payload.get("travel_days"), default=1, minimum=1, maximum=7)
        return_date_policy = _clean(payload.get("return_date_policy")) or "last_day"
        return_date = _parse_return_date(payload.get("return_date"), start_date, days, return_date_policy)
        include_intercity_budget = _coerce_optional_bool(
            payload.get("budget_includes_intercity_transport", payload.get("budget_includes_long_distance"))
        )
        intercity_options = _normalize_list(payload.get("intercity_options"))
        intercity_transportation = _clean(payload.get("intercity_transportation"))
        if intercity_transportation and intercity_transportation != "未确定":
            intercity_options.extend(re.split(r"\s*/\s*|、|,|，", intercity_transportation))
        selected_train_index = _coerce_optional_int(payload.get("selected_train_index"))
        selected_train_ticket = payload.get("selected_train_ticket") if isinstance(payload.get("selected_train_ticket"), dict) else None
        selected_return_train_index = _coerce_optional_int(payload.get("selected_return_train_index"))
        selected_return_train_ticket = (
            payload.get("selected_return_train_ticket") if isinstance(payload.get("selected_return_train_ticket"), dict) else None
        )
        departure_time = _clean(payload.get("intercity_departure_time") or payload.get("departure_time"))
        railway_lookup = self.context.railway_client.query_train_option if self.context.railway_client.enabled else None
        intercity = estimate_intercity_transport(
            origin,
            city,
            modes=intercity_options,
            include_round_trip=True,
            included_in_budget=bool(include_intercity_budget),
            travel_date=start_date,
            return_date=return_date,
            railway_lookup=railway_lookup,
            selected_train_index=selected_train_index,
            selected_train_ticket=selected_train_ticket,
            selected_return_train_index=selected_return_train_index,
            selected_return_train_ticket=selected_return_train_ticket,
            departure_time=departure_time,
        )
        return {"success": True, "message": "城际交通候选已生成", "data": intercity}

    def refresh_plan_rag_context(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        city = _clean(plan.get("city"))
        days = plan.get("days") if isinstance(plan.get("days"), list) else []
        context = _build_location_rag_context(city, days, self.store, [])
        plan["rag_context"] = context
        return context

    def _extract_candidates(self, city: str, results: list[Any], interests: list[str]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for result in results:
            record = result.record
            section = str(record.get("section", ""))
            text = str(record.get("text", ""))
            if record.get("title") != city:
                continue

            matches = list(LISTING_RE.finditer(text))
            if matches:
                for match in matches:
                    label, name = match.group(1), _clean_place_name(match.group(2))
                    if not _is_place_name(name):
                        continue
                    excerpt = _excerpt_around(text, match.start(), match.end())
                    candidates.append(
                        {
                            "name": name,
                            "category": _category_from(label, section, excerpt),
                            "section": section,
                            "description": _clean(excerpt),
                            "address": _extract_first(ADDRESS_RE, excerpt),
                            "open_time": _extract_first(HOURS_RE, excerpt),
                            "ticket_price": _extract_price(excerpt),
                            "source": record.get("source"),
                            "rag_score": result.score,
                            "interest_score": _interest_score(name, section, excerpt, interests),
                        }
                    )
            elif any(token in section for token in ("观光", "历史", "用餐", "购物", "活动")):
                name = section.split("/")[-1].strip()
                if name and name not in {"观光", "用餐", "购物", "活动"} and _is_place_name(name):
                    candidates.append(
                        {
                            "name": name,
                            "category": _category_from("", section, text),
                            "section": section,
                            "description": _short(text, 240),
                            "address": "",
                            "open_time": "",
                            "ticket_price": _extract_price(text),
                            "source": record.get("source"),
                            "rag_score": result.score,
                            "interest_score": _interest_score(name, section, text, interests),
                        }
                    )

        return _dedupe_candidates(candidates)

    def _ensure_candidates(self, city: str, candidates: list[dict[str, Any]], interests: list[str]) -> list[dict[str, Any]]:
        desired = 9
        for name, category, description in FALLBACK_ATTRACTIONS.get(city, []):
            candidates.append(
                {
                    "name": name,
                    "category": category,
                    "section": "兜底景点",
                    "description": description,
                    "address": "",
                    "open_time": "",
                    "ticket_price": 0,
                    "source": "fallback",
                    "rag_score": 0.02,
                    "interest_score": 1.9 + _interest_score(name, category, description, interests),
                }
            )
        if len(_dedupe_candidates(candidates)) < desired:
            candidates.extend(self._map_attraction_candidates(city, interests, limit=desired + 6))
        return _dedupe_candidates(candidates)[: max(desired, len(candidates))]

    def _map_attraction_candidates(self, city: str, interests: list[str], *, limit: int = 12) -> list[dict[str, Any]]:
        if not city or not self.context.map_client.enabled:
            return []

        keywords = _map_attraction_keywords(city, interests)
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        for keyword in keywords:
            pois = self.context.map_client.search_poi(keyword, city, limit=8)
            for poi in pois:
                if not _is_valid_attraction_poi(poi):
                    continue
                key = _place_key(poi.get("name", ""), city)
                if not key or key in seen:
                    continue
                seen.add(key)
                poi_type = str(poi.get("type") or "")
                address = str(poi.get("address") or "")
                description = f"高德地图返回的{city}本地候选点：{poi_type or '景点'}。地址：{address or '以地图为准'}。"
                candidates.append(
                    {
                        "name": poi.get("name") or keyword,
                        "category": _category_from("", poi.get("name", ""), f"{poi_type} {address}"),
                        "section": "高德地图候选",
                        "description": description,
                        "address": address,
                        "open_time": "",
                        "ticket_price": 0,
                        "source": "amap_poi_fallback",
                        "rag_score": 0.01,
                        "interest_score": 1.2 + _interest_score(poi.get("name", ""), poi_type, address, interests),
                    }
                )
                if len(candidates) >= limit:
                    return candidates
        return candidates

    def _add_user_requested_candidates(
        self,
        city: str,
        candidates: list[dict[str, Any]],
        requested_places: list[str],
        results: list[Any],
        interests: list[str],
    ) -> list[dict[str, Any]]:
        if not requested_places:
            return candidates

        by_key = {_place_key(item.get("name", ""), city): item for item in candidates}
        for index, name in enumerate(requested_places):
            key = _place_key(name, city)
            if not key:
                continue
            existing = by_key.get(key)
            if existing:
                existing["interest_score"] = float(existing.get("interest_score", 0)) + 5.0
                existing["section"] = existing.get("section") or "用户指定地点"
                existing["required"] = True
                existing["required_priority"] = min(int(existing.get("required_priority", index) or index), index)
                continue

            excerpt = _find_excerpt_for_name(results, city, name)
            candidates.append(
                {
                    "name": name,
                    "category": _category_from("", name, excerpt),
                    "section": "用户指定地点",
                    "description": excerpt or f"用户在补充需求中指定想去{name}，已优先纳入路线。",
                    "address": "",
                    "open_time": "",
                    "ticket_price": 0,
                    "source": "user_request",
                    "required": True,
                    "required_priority": index,
                    "rag_score": 0.05,
                    "interest_score": 5.0 + len(requested_places) - index + _interest_score(name, name, excerpt, interests),
                }
            )
        return candidates

    def _enrich_candidates(self, city: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = sorted(
            candidates,
            key=lambda item: (float(item.get("interest_score", 0)), float(item.get("rag_score", 0))),
            reverse=True,
        )
        enriched: list[dict[str, Any]] = []
        for index, item in enumerate(ranked[:18]):
            poi = None
            pois = self.context.map_client.search_poi(item["name"], city, limit=1)
            if pois:
                poi = pois[0]
            location = poi["location"] if poi and poi.get("location") else fallback_location(city, index)
            address = item.get("address") or (poi.get("address") if poi else "")
            enriched.append(
                {
                    **item,
                    "address": address or f"{city}{item['name']}附近",
                    "location": location,
                    "poi_id": poi.get("id", "") if poi else "",
                    "tel": poi.get("tel", "") if poi else "",
                    "rating": poi.get("rating", "") if poi else "",
                    "visit_duration": _visit_duration(item),
                    "map_source": poi.get("source", "fallback") if poi else "fallback",
                    "city": city,
                    "nearby_hotels": [],
                }
            )
        return enriched

    def _build_weather(self, city: str, start_date: date, days: int) -> list[dict[str, Any]]:
        weather = self.context.map_client.weather(city)
        if weather:
            return _align_weather(weather, start_date, days, city)

        patterns = [
            ("多云", "多云", 25, 18, "东南", "1-3级"),
            ("晴", "晴", 28, 19, "南", "1-3级"),
            ("小雨", "阴", 22, 17, "北", "1-3级"),
            ("阴", "多云", 24, 18, "东", "1-3级"),
        ]
        fallback = []
        for index in range(days):
            day_weather, night_weather, day_temp, night_temp, wind, power = patterns[index % len(patterns)]
            fallback.append(
                {
                    "date": (start_date + timedelta(days=index)).isoformat(),
                    "city": city,
                    "day_weather": day_weather,
                    "night_weather": night_weather,
                    "day_temp": day_temp,
                    "night_temp": night_temp,
                    "wind_direction": wind,
                    "wind_power": power,
                    "source": "fallback",
                }
            )
        return fallback

    def _meal_suggestions(self, results: list[Any], city: str) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []
        seen: set[str] = set()
        for result in results:
            record = result.record
            if record.get("title") != city:
                continue
            text = str(record.get("text", ""))
            match = FOOD_RE.search(text)
            if match:
                for part in re.split(r"[、,，]", match.group(1)):
                    food = _clean(part)
                    if food and food not in seen:
                        suggestions.append({"food": food, "source": "knowledge_base", "section": str(record.get("section", ""))})
                        seen.add(food)
            if "用餐" in str(record.get("section", "")) and not match:
                for food in _extract_food_names(text):
                    if food and food not in seen:
                        suggestions.append({"food": food, "source": "knowledge_base", "section": str(record.get("section", ""))})
                        seen.add(food)
        if suggestions:
            return suggestions[:8]
        return self._map_meal_suggestions(city)

    def _map_meal_suggestions(self, city: str) -> list[dict[str, str]]:
        if not city or not self.context.map_client.enabled:
            return []
        keywords = [f"{city}早餐", f"{city}小吃", f"{city}本地餐厅", f"{city}特色美食", f"{city}烧烤"]
        suggestions: list[dict[str, str]] = []
        seen: set[str] = set()
        for keyword in keywords:
            keyword_count = 0
            pois = self.context.map_client.search_poi(keyword, city, limit=6)
            for poi in pois:
                if not _is_valid_meal_poi(poi):
                    continue
                name = _clean(poi.get("name"))
                if not name or name in seen:
                    continue
                seen.add(name)
                suggestions.append(
                    {
                        "food": _infer_food_from_meal_poi(city, name, keyword),
                        "place": name,
                        "place_address": _clean(poi.get("address")),
                        "source": "amap",
                        "section": "高德地图餐饮候选",
                    }
                )
                keyword_count += 1
                if len(suggestions) >= 12:
                    return suggestions
                if keyword_count >= 2:
                    break
        return suggestions

    def _build_suggestions(
        self,
        city: str,
        interests: list[str],
        budget: int,
        day_plans: list[dict[str, Any]],
        weather: list[dict[str, Any]],
        meal_suggestions: list[dict[str, str]],
    ) -> str:
        stop_names = [stop["name"] for day in day_plans for stop in day.get("stops", [])][:8]
        rainy = any("雨" in item.get("day_weather", "") for item in weather)
        fallback = (
            f"{city}行程已按{','.join(interests)}偏好安排，建议每天保留30-60分钟机动时间。"
            f"{_budget_suggestion_text(budget)}住宿和交通费用为估算值；酒店请以实际平台价格为准。"
        )
        if "美食" in interests:
            if meal_suggestions:
                foods = "、".join(item["food"] for item in meal_suggestions[:4])
                fallback += f" 知识库中可参考的饮食线索：{foods}；具体店铺和营业状态仍需以地图或现场核验。"
            else:
                fallback += f" 知识库未找到{city}合适的特色美食或具体就餐信息，请自行查阅，不把未核验菜品当推荐。"
        if rainy:
            fallback += " 天气中可能有雨，建议把博物馆、街区和茶馆作为雨天备选。"

        llm = self.context.llm_client
        if not llm.enabled or ("美食" in interests and not meal_suggestions):
            return fallback

        content = {
            "city": city,
            "interests": interests,
            "budget": budget,
            "stops": stop_names,
            "weather": weather[:3],
            "meal_suggestions": meal_suggestions[:6],
        }
        reply = llm.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "你是旅行规划助手，请用中文给出简短、可执行的总体建议，不要编造未提供的信息。"
                        "餐饮建议只能使用 meal_suggestions 里的知识库内容；如果为空，就明确说知识库未找到合适就餐信息。"
                    ),
                },
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        return reply or fallback


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_place_name(value: str) -> str:
    name = _clean(value)
    name = name.split("|")[-1]
    name = re.sub(r"[\[\]{}]", "", name)
    return name.strip(" ：:。；,，")


def _is_place_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 32:
        return False
    if name in GENERIC_PLACE_NAMES:
        return False
    bad_tokens = ("http", "坐标", "电话", "开放时间", "地址", "费用", "说明")
    return not any(token in name for token in bad_tokens)


def _extract_user_place_names(city: str, free_text: str) -> list[str]:
    text = _clean(free_text)
    if not text:
        return []

    names: list[str] = []
    for match in EXPLICIT_STOP_RE.finditer(text):
        names.extend(_split_user_place_segment(city, match.group(0)))
    for match in USER_PLACE_HINT_RE.finditer(text):
        segment = re.sub(r"^(一下|一些|几个|有关|关于)", "", _clean(match.group(1)))
        names.extend(_split_user_place_segment(city, segment))
    if "小动物" in text:
        names.append("动物园")

    return _filter_user_place_names(city, names)[:8]


def _resolve_semantic_requested_places(city: str, free_text: str, results: list[Any]) -> list[str]:
    text = _clean(free_text)
    if not city or not text:
        return []

    resolved: list[str] = []
    for spec in SEMANTIC_PLACE_INTENTS:
        if not any(token in text for token in spec["tokens"]):
            continue
        candidate = _best_semantic_place_from_results(city, results, spec["terms"])
        resolved.append(candidate or f"{city}{spec['fallback']}")
    return _filter_user_place_names(city, resolved)


def _best_semantic_place_from_results(city: str, results: list[Any], terms: tuple[str, ...]) -> str:
    candidates: list[tuple[float, str]] = []
    for result in results:
        record = result.record
        if record.get("title") != city:
            continue
        section = str(record.get("section", ""))
        text = str(record.get("text", ""))
        for match in LISTING_RE.finditer(text):
            name = _clean_place_name(match.group(2))
            if not _is_place_name(name):
                continue
            excerpt = _excerpt_around(text, match.start(), match.end(), radius=120)
            combined = f"{name} {section} {excerpt}"
            if not any(term in combined for term in terms):
                continue
            score = float(getattr(result, "score", 0.0) or 0.0)
            if any(term in name for term in terms):
                score += 3.0
            if any(term in section for term in terms):
                score += 1.0
            candidates.append((score, name))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _filter_user_place_names(city: str, names: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        name = _clean_user_place_name(name)
        if name == "动物园" and city:
            name = f"{city}动物园"
        if not _looks_like_user_place(city, name):
            continue
        key = _place_key(name, city)
        if key and key not in seen:
            unique.append(name)
            seen.add(key)
    return unique[:8]


def _split_user_place_segment(city: str, segment: str) -> list[str]:
    names = []
    for part in re.split(r"[,，、/和与及\s]+", segment):
        name = _clean_user_place_name(part)
        if _looks_like_user_place(city, name):
            names.append(name)
    if names:
        return names

    name = _clean_user_place_name(segment)
    return [name] if _looks_like_user_place(city, name) else []


def _clean_user_place_name(value: str) -> str:
    name = _clean(value)
    prefix_re = re.compile(
        r"^(然后|最后|最好是|最好|请|麻烦|帮我|给我|我想|我们想|我准备|我们准备|我打算|我们打算|我|我们|本人|"
        r"想去|想看|想逛|要去|要看|必须去|一定要去|必去|可以去|希望去|希望看|希望有|安排|包含|包括|去|看|逛|打卡|了解|参观|体验|附近|晚上|白天|下午|上午)"
    )
    while True:
        cleaned = prefix_re.sub("", name, count=1).strip()
        if cleaned == name:
            break
        name = cleaned
    name = re.sub(r"(?:玩|游玩|逛|看|打卡|参观|体验)?[一二两三四五六七八九十\d]+(?:天|日|晚)$", "", name)
    name = re.sub(r"(?:玩|游玩|逛|看|打卡|参观|体验)$", "", name)
    name = re.sub(r"(附近|周边|相关|一类|之类|这些|这些地方)$", "", name)
    return _normalize_user_place_alias(name.strip(" ：:。；,，、"))


def _normalize_user_place_alias(name: str) -> str:
    if "小动物" in name and "动物园" not in name:
        return "动物园"
    if "动物园" in name:
        match = re.search(r"(?:[\u4e00-\u9fffA-Za-z0-9]{2,8})?动物园", name)
        if match:
            return match.group(0)
    return name


def _place_key(name: str, city: str = "") -> str:
    normalized = _normalize_user_place_alias(_clean(name))
    key = re.sub(r"\W+", "", normalized)
    city_key = re.sub(r"\W+", "", city)
    if city_key and key.startswith(city_key) and len(key) > len(city_key):
        key = key[len(city_key) :]
    return key


def _looks_like_user_place(city: str, name: str) -> bool:
    if not name or name == city:
        return False
    if name in GENERIC_USER_PLACE_NAMES:
        return False
    if re.fullmatch(r"(?:玩|游玩)?[一二两三四五六七八九十\d]+(?:天|日|晚)", name):
        return False
    if len(name) < 2 or len(name) > 24:
        return False
    bad_tokens = (
        "预算",
        "路线",
        "交通",
        "天气",
        "酒店",
        "住宿",
        "攻略",
        "不要",
        "优先",
        "不太赶",
        "费用",
        "希望",
        "请",
        "帮我",
        "最好",
        "然后",
        "最后",
        "可以",
        "规划",
        "一下",
        "适合",
        "方便",
        "通勤",
        "绕路",
        "省事",
        "哪些",
        "看看",
        "有没有",
        "可以玩",
        "玩的地方",
    )
    if any(token in name for token in bad_tokens):
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", name))


def _find_excerpt_for_name(results: list[Any], city: str, name: str) -> str:
    for result in results:
        record = result.record
        if record.get("title") != city:
            continue
        text = str(record.get("text", ""))
        index = text.find(name)
        if index >= 0:
            return _excerpt_around(text, index, index + len(name), radius=180)
    return ""


def _extract_first(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return _clean(match.group(1)) if match else ""


def _extract_price(text: str) -> int:
    match = PRICE_RE.search(text)
    if not match:
        if "免费" in text:
            return 0
        return 0
    return _coerce_int(match.group(2), default=0, minimum=0, maximum=2000)


def _excerpt_around(text: str, start: int, end: int, radius: int = 160) -> str:
    return _clean(text[max(0, start - 30) : min(len(text), end + radius)])


def _short(text: str, limit: int) -> str:
    text = _clean(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _build_location_rag_context(
    city: str,
    day_plans: list[dict[str, Any]],
    store: TfidfRagStore,
    fallback_results: list[Any],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    places = _planned_place_names(city, day_plans)
    if not places:
        return []

    best_by_id: dict[str, dict[str, Any]] = {}
    for place in places:
        query = f"{city} {place} {place} 观光 景点 用餐 地址 开放时间"
        results = search_tourism_records(query, store, city=city, top_k=8, min_score=0.001)
        _merge_location_rag_hits(best_by_id, results, city, [place])

    if fallback_results:
        _merge_location_rag_hits(best_by_id, fallback_results, city, places)

    if not best_by_id:
        place_query = " ".join([city, *places[:6], "观光 景点 用餐 购物"])
        fallback = search_tourism_records(place_query, store, city=city, top_k=limit, min_score=0.001)
        _merge_city_place_rag_hits(best_by_id, [*fallback, *fallback_results], city)

    refs = sorted(
        best_by_id.values(),
        key=lambda item: (float(item.get("score", 0)), len(item.get("matched_places", []))),
        reverse=True,
    )
    return refs[:limit]


def _merge_location_rag_hits(
    best_by_id: dict[str, dict[str, Any]],
    results: list[Any],
    city: str,
    places: list[str],
) -> None:
    for result in results:
        record = result.record
        matched = _matched_plan_places(record, city, places)
        if not matched:
            continue

        score = _location_rag_score(float(getattr(result, "score", 0.0) or 0.0), record, city, matched)
        if score <= 0:
            continue

        record_id = str(record.get("id") or f"{record.get('title')}::{record.get('section')}")
        item = {
            "id": record_id,
            "title": record.get("title"),
            "section": record.get("section"),
            "category": record.get("section") or "地点资料",
            "text": _short(record.get("text", ""), 260),
            "score": round(score, 3),
            "raw_score": round(float(getattr(result, "score", 0.0) or 0.0), 3),
            "matched_places": matched,
            "score_basis": "planned_places",
        }
        old = best_by_id.get(record_id)
        if old is None or float(item["score"]) > float(old.get("score", 0)):
            best_by_id[record_id] = item


def _merge_city_place_rag_hits(
    best_by_id: dict[str, dict[str, Any]],
    results: list[Any],
    city: str,
) -> None:
    for result in results:
        record = result.record
        if record.get("title") != city:
            continue
        section = str(record.get("section", ""))
        if not _is_place_reference_section(section):
            continue

        score = _city_place_rag_score(float(getattr(result, "score", 0.0) or 0.0), section)
        record_id = str(record.get("id") or f"{record.get('title')}::{record.get('section')}")
        item = {
            "id": record_id,
            "title": record.get("title"),
            "section": section,
            "category": section or "地点资料",
            "text": _short(record.get("text", ""), 260),
            "score": round(score, 3),
            "raw_score": round(float(getattr(result, "score", 0.0) or 0.0), 3),
            "matched_places": [],
            "score_basis": "planned_places_city_section",
        }
        old = best_by_id.get(record_id)
        if old is None or float(item["score"]) > float(old.get("score", 0)):
            best_by_id[record_id] = item


def _planned_place_names(city: str, day_plans: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for day in day_plans:
        for stop in day.get("stops") or []:
            if not isinstance(stop, dict) or stop.get("scheduled") is False:
                continue
            name = _clean(stop.get("name"))
            if name and not _is_generic_rag_place(name):
                names.append(name)
        for meal in day.get("meals") or []:
            if not isinstance(meal, dict):
                continue
            place = _clean(meal.get("place") or meal.get("restaurant") or meal.get("name"))
            if place and not _is_generic_rag_place(place):
                names.append(place)

    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = _place_key(name, city)
        if key and key not in seen:
            unique.append(name)
            seen.add(key)
    return unique[:12]


def _matched_plan_places(record: dict[str, Any], city: str, places: list[str]) -> list[str]:
    text = f"{record.get('title', '')} {record.get('section', '')} {record.get('text', '')}"
    matched: list[str] = []
    for place in places:
        keys = _rag_place_keys(place, city)
        if not keys:
            continue
        if any(key in text for key in keys):
            label = keys[0]
            if label not in matched:
                matched.append(label)
    return matched


def _rag_place_keys(place: str, city: str) -> list[str]:
    cleaned = _clean(place)
    if not cleaned:
        return []

    chunks = {cleaned}
    for separator in ("附近", "周边", "旁边", "周围", "/", "／", "·", "-", "—"):
        if separator in cleaned:
            chunks.update(_clean(part) for part in cleaned.split(separator) if _clean(part))

    normalized: set[str] = set()
    for chunk in chunks:
        chunk = re.sub(r"(精选酒店|酒店|小吃街|商圈|附近|周边|夜间街区)$", "", chunk).strip()
        if city and chunk.startswith(city) and len(chunk) > len(city):
            normalized.add(chunk[len(city) :])
        normalized.add(chunk)

    return sorted(
        {
            key
            for key in normalized
            if len(key) >= 2
            and key != city
            and not _is_generic_rag_place(key)
            and not any(token in key for token in ("高铁", "火车", "车次", "预算", "交通", "住宿"))
        },
        key=len,
        reverse=True,
    )


def _location_rag_score(raw_score: float, record: dict[str, Any], city: str, matched_places: list[str]) -> float:
    section = str(record.get("section", ""))
    text = str(record.get("text", ""))
    score = 0.66 + min(max(raw_score, 0.0), 0.12) * 1.6

    if any(place in section for place in matched_places):
        score += 0.16
    if any(f"：{place}" in text or f"{place}；" in text for place in matched_places):
        score += 0.12
    if str(record.get("title", "")) == city:
        score += 0.04
    if len(matched_places) >= 2:
        score += 0.04

    return min(score, 0.98)


def _city_place_rag_score(raw_score: float, section: str) -> float:
    if any(token in section for token in ("观光", "景点", "用餐", "饮食", "购物", "活动", "夜生活")):
        return min(0.82, 0.58 + min(max(raw_score, 0.0), 0.12) * 1.8)
    return min(0.62, 0.4 + min(max(raw_score, 0.0), 0.12) * 1.2)


def _is_place_reference_section(section: str) -> bool:
    if any(token in section for token in ("交通", "抵达", "乘火车", "乘飞机", "长途汽车", "签证", "出入境", "住宿")):
        return False
    return section == "概览" or any(token in section for token in ("观光", "景点", "用餐", "饮食", "购物", "活动", "夜生活"))


def _is_generic_rag_place(name: str) -> bool:
    generic_tokens = (
        "酒店",
        "住宿",
        "小吃街",
        "商圈",
        "夜间街区",
        "地图候选",
        "当地早餐",
        "本地小吃",
        "简餐",
        "自由活动",
    )
    return name in GENERIC_USER_PLACE_NAMES or any(token == name for token in generic_tokens)


def _extract_food_names(text: str) -> list[str]:
    cleaned = _clean(text)
    names: list[str] = []
    for part in re.split(r"[、,，；;。]", cleaned):
        part = _clean(part)
        part = re.sub(r"^(?:著名食物有|特色美食有|推荐|包括|有|可以吃到)[:：]?", "", part)
        if 2 <= len(part) <= 12 and not any(token in part for token in ("坐标", "地址", "说明", "电话", "开放", "交通")):
            names.append(part)
    return names[:8]


def _category_from(label: str, section: str, text: str) -> str:
    combined = f"{label} {section} {text}"
    if any(token in combined for token in ("历史", "博物馆", "遗址", "古", "祠", "寺", "宫")):
        return "历史文化"
    if any(token in combined for token in ("用餐", "饮食", "餐", "美食")):
        return "美食用餐"
    if any(token in combined for token in ("公园", "山", "湖", "湿地", "动物", "植物")):
        return "自然观光"
    if any(token in combined for token in ("购物", "商场", "市场")):
        return "购物休闲"
    if any(token in combined for token in ("夜生活", "酒吧")):
        return "夜生活"
    return "城市观光"


def _interest_score(name: str, section: str, text: str, interests: list[str]) -> float:
    combined = f"{name} {section} {text}"
    score = 0.0
    for interest in interests:
        keywords = INTEREST_KEYWORDS.get(interest, [interest])
        if any(keyword in combined for keyword in keywords):
            score += 1.0
    if "观光" in section:
        score += 0.4
    if "用餐" in section:
        score += 0.2
    return score


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in candidates:
        key = re.sub(r"\W+", "", item.get("name", ""))
        if not key:
            continue
        old = best.get(key)
        if old is None or (item.get("interest_score", 0), item.get("rag_score", 0)) > (
            old.get("interest_score", 0),
            old.get("rag_score", 0),
        ):
            best[key] = item
    return list(best.values())


def _normalize_interests(raw: Any, free_text: Any = "") -> list[str]:
    values: list[str] = []
    if isinstance(raw, list):
        values.extend(_clean(item) for item in raw)
    elif raw:
        values.extend(_clean(item) for item in re.split(r"[,，、\s]+", str(raw)) if _clean(item))
    text = _clean(free_text)
    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            values.append(interest)
    normalized = []
    for value in values:
        if value in {"景点", "打卡", "城市"}:
            value = "观光"
        if value in {"文化", "博物馆"}:
            value = "历史"
        if value and value not in normalized:
            normalized.append(value)
    return normalized or ["观光", "历史", "美食"]


def _normalize_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = [_clean(item) for item in raw if _clean(item)]
    elif raw:
        values = [_clean(item) for item in re.split(r"[,，、\s]+", str(raw)) if _clean(item)]
    else:
        values = []
    normalized = []
    for value in values:
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _merge_unique_lists(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for value in group:
            if value and value not in merged:
                merged.append(value)
    return merged


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = _clean(value).lower()
    if text in {"true", "1", "yes", "y", "包含", "包括", "含"}:
        return True
    if text in {"false", "0", "no", "n", "不包含", "不包括", "不含"}:
        return False
    return None


def _coerce_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _parse_start_date(value: Any) -> date:
    text = _clean(value)
    if not text:
        return date.today()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _parse_return_date(value: Any, start_date: date, days: int, policy: str = "last_day") -> date:
    text = _clean(value)
    if text:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            pass
    offset = max(0, int(days or 1) - 1)
    if policy == "next_day_after_last_day":
        offset += 1
    return start_date + timedelta(days=offset)


def _budget_level(budget: int, days: int) -> str:
    if not budget:
        return "standard"
    per_day = budget / max(days, 1)
    if per_day <= 350:
        return "tight"
    if per_day >= 900:
        return "relaxed"
    return "standard"


def _budget_suggestion_text(budget: int) -> str:
    if budget:
        return f"预算上限约{budget}元，"
    return "未设置明确预算上限，"


def _select_stops(candidates: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    desired = max(3, days * 3)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    bucket_counts: dict[str, int] = {}

    required = sorted(
        [item for item in candidates if item.get("required")],
        key=lambda item: _coerce_int(item.get("required_priority"), default=999, minimum=0, maximum=999),
    )
    optional = [item for item in candidates if not item.get("required")]

    def add(item: dict[str, Any], *, enforce_diversity: bool) -> None:
        if len(selected) >= desired:
            return
        key = _place_key(item.get("name", ""), item.get("city", ""))
        if not key or key in seen or _is_nearby_placeholder(item):
            return
        bucket = _stop_bucket(item)
        if enforce_diversity and not _bucket_has_room(bucket, bucket_counts, days):
            return
        selected.append(item)
        seen.add(key)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    for item in required:
        add(item, enforce_diversity=True)
    for item in optional:
        add(item, enforce_diversity=True)
    for item in optional:
        add(item, enforce_diversity=False)
    return selected


def _is_nearby_placeholder(item: dict[str, Any]) -> bool:
    name = str(item.get("name") or "")
    return name.endswith("周边") or name.endswith("附近")


def _bucket_has_room(bucket: str, counts: dict[str, int], days: int) -> bool:
    limits = {
        "museum": max(1, days),
        "animal": max(1, days),
        "water": max(1, days),
        "culture": max(1, days + 1),
    }
    limit = limits.get(bucket)
    return limit is None or counts.get(bucket, 0) < limit


def _stop_bucket(item: dict[str, Any]) -> str:
    combined = f"{item.get('name') or ''} {item.get('category') or ''} {item.get('section') or ''}"
    if any(token in combined for token in ("博物馆", "纪念馆")):
        return "museum"
    if any(token in combined for token in ("动物园", "熊猫基地", "大熊猫", "海洋世界")):
        return "animal"
    if any(token in combined for token in ("水世界", "水上", "水乐园", "水公园", "漂流")):
        return "water"
    if "乐园" in combined:
        return "theme"
    if any(token in combined for token in ("用餐", "饮食", "美食", "小吃")):
        return "food"
    if any(token in combined for token in ("街", "古镇", "水镇", "夜市", "商场", "市场")):
        return "street"
    if any(token in combined for token in ("公园", "湿地", "湖", "山", "自然")):
        return "nature"
    if any(token in combined for token in ("历史", "文化", "遗址", "寺", "祠", "宫", "塔")):
        return "culture"
    return "other"


def _map_attraction_keywords(city: str, interests: list[str]) -> list[str]:
    keywords = [
        f"{city} 景点",
        f"{city} 旅游景区",
        f"{city} 公园",
        f"{city} 古城 古镇 古商城",
        f"{city} 风景区",
    ]
    interest_text = " ".join(interests)
    if any(token in interest_text for token in ("历史", "文化", "博物馆")):
        keywords.extend([f"{city} 博物馆", f"{city} 历史文化景点"])
    if any(token in interest_text for token in ("亲子", "动物", "玩水")):
        keywords.extend([f"{city} 动物园", f"{city} 乐园", f"{city} 水世界"])
    if any(token in interest_text for token in ("美食", "购物", "夜生活")):
        keywords.extend([f"{city} 夜市", f"{city} 美食街", f"{city} 商业街"])
    return _merge_unique_lists(keywords)


def _is_valid_attraction_poi(poi: dict[str, Any]) -> bool:
    name = _clean(poi.get("name"))
    poi_type = _clean(poi.get("type"))
    address = _clean(poi.get("address"))
    combined = f"{name} {poi_type} {address}"
    if not name:
        return False
    exclude = (
        "公交站",
        "地铁站",
        "停车场",
        "停车区",
        "游客中心",
        "售票",
        "入口",
        "出口",
        "卫生间",
        "管理处",
        "派出所",
        "公交车站",
        "交通设施",
        "道路附属",
        "生活服务",
        "公司",
        "住宅",
        "小区",
        "餐饮服务",
        "购物服务",
        "医疗",
        "银行",
    )
    if any(token in combined for token in exclude):
        return False
    include = (
        "风景名胜",
        "国家级景点",
        "旅游景点",
        "公园",
        "植物园",
        "动物园",
        "博物馆",
        "纪念馆",
        "文化场所",
        "古商城",
        "古镇",
        "古城",
        "街区",
        "夜市",
        "美食街",
    )
    return any(token in combined for token in include)


def _is_valid_meal_poi(poi: dict[str, Any]) -> bool:
    name = _clean(poi.get("name"))
    poi_type = _clean(poi.get("type"))
    if not name:
        return False
    if any(token in name for token in ("公司", "培训", "学校", "公交", "停车", "入口", "出口")):
        return False
    return "餐饮服务" in poi_type or any(token in name for token in ("烧烤", "餐厅", "小吃", "饭店", "火锅", "面馆"))


def _infer_food_from_meal_poi(city: str, name: str, keyword: str) -> str:
    if "早餐" in keyword:
        return "当地早餐/简餐"
    if "小吃" in keyword:
        return "本地小吃"
    if "烧烤" in name or "烧烤" in keyword:
        return f"{city}烧烤"
    for token in ("火锅", "小吃", "面", "饺子", "菜馆", "烤肉"):
        if token in name:
            return token
    return "本地餐饮"


def _nearest_order(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(stops) <= 2:
        return stops
    remaining = stops[:]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]["location"]
        next_index = min(range(len(remaining)), key=lambda idx: haversine_km(last, remaining[idx]["location"]))
        ordered.append(remaining.pop(next_index))
    return ordered


def _order_day_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(stops) <= 1:
        return stops
    required = [stop for stop in stops if stop.get("required")]
    if not required:
        return _nearest_order(stops)

    first = required[0]
    remaining = [stop for stop in stops if stop is not first]
    ordered = [first]
    while remaining:
        last = ordered[-1]["location"]
        next_index = min(range(len(remaining)), key=lambda idx: haversine_km(last, remaining[idx]["location"]))
        ordered.append(remaining.pop(next_index))
    return ordered


def _visit_duration(item: dict[str, Any]) -> int:
    category = item.get("category", "")
    if "美食" in category or "购物" in category:
        return 90
    if "历史" in category or "博物馆" in category:
        return 120
    if "自然" in category:
        return 150
    return 100


def _day_theme(stops: list[dict[str, Any]], interests: list[str]) -> str:
    if not stops:
        return "自由活动"
    categories = [stop.get("category", "城市观光") for stop in stops]
    if any("美食" in category for category in categories):
        return "美食与街区"
    if any("历史" in category for category in categories):
        return "历史文化"
    return interests[0] if interests else "城市观光"


DEFAULT_DAY_START_MIN = 8 * 60 + 30
DAY_END_TARGET_MIN = 20 * 60 + 30
OUTDOOR_LATEST_START_MIN = 17 * 60
OUTDOOR_LATEST_END_MIN = 18 * 60 + 30
MEAL_WINDOWS = {
    "breakfast": {"target": 7 * 60 + 30, "latest": 9 * 60 + 30, "duration": 45, "label": "早餐"},
    "lunch": {"target": 12 * 60, "latest": 14 * 60 + 30, "duration": 60, "label": "午餐"},
    "dinner": {"target": 18 * 60, "latest": 20 * 60 + 30, "duration": 70, "label": "晚餐"},
}


def _visit_window_for_stop(stop: dict[str, Any]) -> dict[str, Any]:
    explicit = _parse_open_time_window(stop.get("open_time"))
    if explicit:
        return {
            "start": explicit[0],
            "end": explicit[1],
            "label": f"{_format_clock(explicit[0])}-{_format_clock(explicit[1])}",
            "source": "知识库开放时间",
            "note": "按知识库抽取到的开放时间排程，出行前仍需官方核验。",
        }

    combined = f"{stop.get('name') or ''} {stop.get('category') or ''} {stop.get('section') or ''}"
    if any(token in combined for token in ("夜市", "夜游")):
        return _fallback_visit_window(17 * 60, 23 * 60, "夜间街区参考营业时间")
    if any(token in combined for token in ("商场", "市场", "步行街")):
        return _fallback_visit_window(10 * 60, 22 * 60, "商业街区参考营业时间")
    if any(token in combined for token in ("古镇", "水镇", "古街", "街区", "锦里", "宽窄巷子")):
        return _fallback_visit_window(9 * 60, 21 * 60 + 30, "街区参考开放时间")
    if any(token in combined for token in ("动物园", "熊猫基地", "海洋世界")):
        return _fallback_visit_window(8 * 60 + 30, 17 * 60 + 30, "动物园类参考开放时间")
    if any(token in combined for token in ("水世界", "水上", "水乐园", "水公园", "漂流")):
        return _fallback_visit_window(10 * 60, 18 * 60, "水上项目参考开放时间")
    if any(token in combined for token in ("博物馆", "纪念馆")):
        return _fallback_visit_window(9 * 60, 17 * 60, "博物馆类参考开放时间")
    if any(token in combined for token in ("寺", "祠", "宫", "塔", "遗址", "历史")):
        return _fallback_visit_window(8 * 60 + 30, 17 * 60 + 30, "历史场馆参考开放时间")
    if _is_daylight_stop(stop):
        return _fallback_visit_window(7 * 60, OUTDOOR_LATEST_END_MIN, "户外景点参考适游时间")
    return _fallback_visit_window(DEFAULT_DAY_START_MIN, 18 * 60 + 45, "普通景点参考开放时间")


def _fallback_visit_window(start: int, end: int, source: str) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "label": f"{_format_clock(start)}-{_format_clock(end)}",
        "source": source,
        "note": "未查到精确营业时间，按景点类型参考窗口排程，出行前需官方核验。",
    }


def _parse_open_time_window(value: Any) -> tuple[int, int] | None:
    text = _clean(value)
    if not text:
        return None
    if any(token in text for token in ("全天", "24小时", "24 小时")):
        return (0, 24 * 60)

    matches = re.findall(r"(\d{1,2})[:：](\d{2})", text)
    if len(matches) >= 2:
        start = int(matches[0][0]) * 60 + int(matches[0][1])
        end = int(matches[1][0]) * 60 + int(matches[1][1])
        if 0 <= start < 24 * 60 and 0 <= end <= 24 * 60:
            if end <= start and end <= 6 * 60:
                end += 24 * 60
            return (start, end)

    hour_matches = re.findall(r"(\d{1,2})(?:点|时)(半)?", text)
    if len(hour_matches) >= 2:
        start = int(hour_matches[0][0]) * 60 + (30 if hour_matches[0][1] else 0)
        end = int(hour_matches[1][0]) * 60 + (30 if hour_matches[1][1] else 0)
        if "下午" in text or "晚上" in text:
            if end <= 12 * 60:
                end += 12 * 60
        if 0 <= start < 24 * 60 and 0 < end <= 24 * 60:
            return (start, end)
    return None


def _next_visit_start(stop: dict[str, Any], cursor: int, duration: int) -> int | None:
    window = _visit_window_for_stop(stop)
    start = max(cursor, int(window["start"]))
    if start + duration <= int(window["end"]):
        return start
    return None


def _visit_window_label(stop: dict[str, Any]) -> str:
    window = _visit_window_for_stop(stop)
    return f"{window['label']}（{window['source']}）"


def _build_hotel_transfers(
    hotel: dict[str, Any] | None,
    stops: list[dict[str, Any]],
    *,
    preference: str,
    mobility_policy: dict[str, Any],
    budget_level: str,
) -> list[dict[str, Any]]:
    if not hotel or not stops:
        return []
    transfers = [
        _estimate_lodging_transfer(
            hotel,
            stops[0],
            preference=preference,
            mobility_policy=mobility_policy,
            budget_level=budget_level,
            phase="outbound",
        ),
        _estimate_lodging_transfer(
            stops[-1],
            hotel,
            preference=preference,
            mobility_policy=mobility_policy,
            budget_level=budget_level,
            phase="return",
        ),
    ]
    return [transfer for transfer in transfers if transfer]


def _attach_hotel_review_profiles(
    hotels: list[dict[str, Any]],
    review_insights: dict[str, Any],
    accommodation: str,
) -> list[dict[str, Any]]:
    if not hotels or not review_insights.get("available"):
        return hotels
    return [
        {
            **hotel,
            "review_profile": _hotel_review_profile(hotel, review_insights, accommodation),
        }
        for hotel in hotels
    ]


def _hotel_review_profile(
    hotel: dict[str, Any],
    review_insights: dict[str, Any],
    accommodation: str,
) -> dict[str, Any]:
    hotel_name = _clean(hotel.get("name")) or "该酒店"
    return {
        "title": "住客评论知识库参考",
        "summary": (
            f"{hotel_name} 是地图候选酒店，评论知识库用于提示订房时要核对的细节，"
            "不代表这家酒店的实时评论。"
        ),
        "focus_points": _hotel_focus_points(accommodation, review_insights),
        "sections": (review_insights.get("detail_sections") or [])[:5],
        "booking_tips": review_insights.get("booking_tips") or [],
        "source_note": "评论摘录来自本地酒店评论知识库；具体酒店请以订房平台的最新评价、实拍图和退改规则为准。",
    }


def _hotel_focus_points(accommodation: str, review_insights: dict[str, Any]) -> list[str]:
    defaults = ["位置与通勤", "卫生与舒适度", "噪音与睡眠", "服务响应"]
    if "民宿" in accommodation:
        defaults = ["位置与通勤", "卫生与舒适度", "服务响应", "额外费用"]
    elif "经济" in accommodation:
        defaults = ["位置与通勤", "卫生与舒适度", "噪音与睡眠", "停车与额外费用"]
    elif "豪华" in accommodation:
        defaults = ["服务响应", "卫生与舒适度", "噪音与睡眠", "额外费用"]

    extra = [
        str(item)
        for item in review_insights.get("focus_points", [])
        if item and str(item) not in defaults
    ]
    return [*defaults, *extra[:2]]


def _estimate_lodging_transfer(
    start: dict[str, Any],
    end: dict[str, Any],
    *,
    preference: str,
    mobility_policy: dict[str, Any],
    budget_level: str,
    phase: str,
) -> dict[str, Any]:
    start_point = {"name": start.get("name") or "酒店", "location": start.get("location")}
    end_point = {"name": end.get("name") or "酒店", "location": end.get("location")}
    if start_point.get("location") and end_point.get("location"):
        route = estimate_local_route(
            start_point,
            end_point,
            preference=preference,
            mobility_policy=mobility_policy,
            budget_level=budget_level,
        )
    else:
        route = _fallback_lodging_transfer(start_point["name"], end_point["name"], preference)
    route["kind"] = "hotel_transfer"
    route["phase"] = phase
    return route


def _fallback_lodging_transfer(start_name: str, end_name: str, preference: str) -> dict[str, Any]:
    if "打车" in preference:
        mode, duration, cost = "打车/网约车", 12, 12
    elif "步行" in preference or "共享单车" in preference:
        mode, duration, cost = "步行/短接驳", 15, 0
    else:
        mode, duration, cost = "公交/短接驳", 18, 4
    return {
        "from": start_name,
        "to": end_name,
        "mode": mode,
        "distance_km": 0.8,
        "duration_min": duration,
        "estimated_cost": cost,
        "description": f"{start_name} → {end_name}，酒店缺少精确坐标时按周边短接驳估算，约{duration}分钟。",
        "warnings": ["酒店缺少精确坐标，已按附近接驳时间估算。"],
        "is_estimated": True,
    }


def _build_day_timeline(
    *,
    city: str,
    day_index: int,
    stops: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    meals: list[dict[str, Any]],
    hotel: dict[str, Any] | None,
    hotel_transfers: list[dict[str, Any]],
    intercity_transport: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    scheduled_meals: set[str] = set()
    cursor = DEFAULT_DAY_START_MIN
    note = "未选择到达车次/航班或到达时间，按08:30开始游玩。"

    arrival_min = _first_day_arrival_min(day_index, intercity_transport)
    if arrival_min is not None:
        selected = intercity_transport.get("selected") or {}
        items.append(
            _timeline_entry(
                "arrival",
                arrival_min,
                arrival_min,
                f"抵达{city}",
                _arrival_description(selected),
                related={
                    "mode": selected.get("mode"),
                    "train_code": selected.get("train_code"),
                    "flight_code": selected.get("flight_code"),
                },
            )
        )
        buffer_end = arrival_min + 45
        items.append(
            _timeline_entry(
                "buffer",
                arrival_min,
                buffer_end,
                "抵达后接驳与行李处理",
                f"预留约45分钟用于出站、前往酒店或寄存行李，酒店参考：{(hotel or {}).get('name') or '待确认'}。",
            )
        )
        cursor = max(buffer_end, DEFAULT_DAY_START_MIN)
        note = "已按所选城际交通到达时间顺延当天行程。"
        if cursor <= MEAL_WINDOWS["breakfast"]["latest"]:
            cursor = _schedule_meal(items, meals, "breakfast", cursor, scheduled_meals, force=True)
            cursor = max(cursor, DEFAULT_DAY_START_MIN)
        else:
            _mark_meal_unscheduled(meals, "breakfast", "到达较晚，建议出发前、车上或到站前自行解决。")
    else:
        _schedule_fixed_breakfast(items, meals, scheduled_meals)

    outbound_transfer = hotel_transfers[0] if hotel_transfers else None
    return_transfer = hotel_transfers[1] if len(hotel_transfers) > 1 else None
    last_scheduled_stop_name = ""
    skipped_remaining = False
    for stop in stops:
        stop["scheduled"] = False

    if stops:
        first_visit = int(stops[0].get("visit_duration") or 90)
        transfer_duration = int((outbound_transfer or {}).get("duration_min") or 0)
        cursor = _schedule_meal(items, meals, "lunch", cursor, scheduled_meals, lookahead=transfer_duration + first_visit)
        cursor = _schedule_meal(items, meals, "dinner", cursor, scheduled_meals, lookahead=transfer_duration + first_visit)
        if outbound_transfer:
            cursor = _append_route_item(items, outbound_transfer, cursor, "酒店到首站")

    for index, stop in enumerate(stops):
        visit_duration = int(stop.get("visit_duration") or 90)
        cursor = _schedule_meal(items, meals, "lunch", cursor, scheduled_meals, lookahead=visit_duration)
        cursor = _schedule_meal(items, meals, "dinner", cursor, scheduled_meals, lookahead=visit_duration)
        visit_start = _next_visit_start(stop, cursor, visit_duration)
        if visit_start is None:
            cursor = _append_replacement_activity_item(items, stops, stop, cursor, city, hotel)
            skipped_remaining = True
            break
        cursor = _append_buffer_if_needed(items, cursor, visit_start)
        start = cursor
        end = start + visit_duration
        stop["scheduled"] = True
        items.append(
            _timeline_entry(
                "stop",
                start,
                end,
                stop.get("name") or "景点",
                stop.get("description") or "",
                estimated_cost=stop.get("ticket_price") or 0,
                related={
                    "order": stop.get("order"),
                    "category": stop.get("category"),
                    "business_hours": stop.get("business_hours") or _visit_window_label(stop),
                },
            )
        )
        cursor = end
        last_scheduled_stop_name = stop.get("name") or ""

        if index < len(routes):
            route = routes[index]
            next_stop = stops[index + 1] if index + 1 < len(stops) else {}
            next_visit = int(next_stop.get("visit_duration") or 90)
            route_duration = int(route.get("duration_min") or 0)
            cursor = _schedule_meal(items, meals, "lunch", cursor, scheduled_meals, lookahead=route_duration + next_visit)
            cursor = _schedule_meal(items, meals, "dinner", cursor, scheduled_meals, lookahead=route_duration + next_visit)
            if next_stop and _next_visit_start(next_stop, cursor + route_duration, next_visit) is None:
                cursor = _append_replacement_activity_item(items, stops, next_stop, cursor, city, hotel)
                skipped_remaining = True
                break
            cursor = _append_route_item(items, route, cursor, "景点间交通")

    if "lunch" not in scheduled_meals:
        cursor = _schedule_meal(items, meals, "lunch", cursor, scheduled_meals, force=cursor <= 15 * 60 + 30)
    if "dinner" not in scheduled_meals:
        cursor = _schedule_meal(items, meals, "dinner", cursor, scheduled_meals, force=True)
    if return_transfer and not skipped_remaining and (not last_scheduled_stop_name or return_transfer.get("from") == last_scheduled_stop_name):
        cursor = _append_route_item(items, return_transfer, cursor, "返回酒店")

    day_start = _first_non_meal_time(items) or _format_clock(DEFAULT_DAY_START_MIN)
    day_end = items[-1]["end_time"] if items else _format_clock(cursor)
    return {"items": items, "note": note, "day_start_time": day_start, "day_end_time": day_end}


def _first_day_arrival_min(day_index: int, intercity_transport: dict[str, Any]) -> int | None:
    if day_index != 0:
        return None
    selected = (intercity_transport or {}).get("selected") or {}
    mode = selected.get("mode") or ""
    if selected.get("ticket_selection_required"):
        return None
    if mode == "高铁/火车" and selected.get("selected_train_index") is None:
        return None
    return _parse_clock(selected.get("arrive_time"))


def _arrival_description(selected: dict[str, Any]) -> str:
    if selected.get("mode") == "飞机" or selected.get("flight_code"):
        flight_code = selected.get("flight_code") or selected.get("train_code") or "航班待确认"
        return (
            f"{flight_code} {selected.get('from_station') or ''}→{selected.get('to_station') or ''}，"
            f"{selected.get('depart_time') or '--'}起飞，{selected.get('arrive_time') or '--'}落地。"
            "当前航班时刻为候选排期参考，实际以航司/航旅纵横/携程等平台为准。"
        )
    if selected.get("train_code"):
        return (
            f"{selected.get('train_code')} {selected.get('from_station') or ''}→{selected.get('to_station') or ''}，"
            f"{selected.get('depart_time') or '--'}出发，{selected.get('arrive_time') or '--'}到达。"
        )
    if selected.get("mode") in {"自驾", "骑行"} and selected.get("depart_time") and selected.get("arrive_time"):
        return (
            f"按{selected.get('mode')} {selected.get('depart_time')}出发、"
            f"{selected.get('arrive_time')}到达估算；路况、停车和限行以当天实际情况为准。"
        )
    if selected.get("mode"):
        return f"按已选择的{selected.get('mode')}到达时间安排首日游玩。"
    return "按已选择的到达时间安排首日游玩。"


def _can_visit_stop_at(stop: dict[str, Any], start: int, duration: int) -> bool:
    return _next_visit_start(stop, start, duration) == start


def _is_daylight_stop(stop: dict[str, Any]) -> bool:
    name = str(stop.get("name") or "")
    category = str(stop.get("category") or "")
    combined = f"{name} {category}"
    if any(token in combined for token in ("夜市", "夜游", "古镇", "水镇", "街区", "步行街", "商场")):
        return False
    return any(token in combined for token in ("动物园", "植物园", "公园", "湿地", "湖", "山", "自然"))


def _append_replacement_activity_item(
    items: list[dict[str, Any]],
    stops: list[dict[str, Any]],
    stop: dict[str, Any],
    cursor: int,
    city: str,
    hotel: dict[str, Any] | None,
) -> int:
    stop["scheduled"] = False
    replacement = _late_replacement_stop(city, hotel, stop, stops)
    start = max(cursor, 17 * 60)
    latest_end = 22 * 60
    duration = 90
    if start + duration > latest_end:
        duration = max(45, latest_end - start)
    end = start + duration
    cursor = _append_buffer_if_needed(items, cursor, start)
    replacement["scheduled"] = True
    stops.append(replacement)
    items.append(
        _timeline_entry(
            "stop",
            start,
            end,
            replacement["name"],
            replacement["description"],
            estimated_cost=0,
            related={
                "order": replacement.get("order"),
                "category": replacement.get("category"),
                "business_hours": replacement.get("business_hours"),
            },
        )
    )
    return end


def _late_replacement_stop(
    city: str,
    hotel: dict[str, Any] | None,
    skipped_stop: dict[str, Any],
    stops: list[dict[str, Any]],
) -> dict[str, Any]:
    hotel_name = _clean((hotel or {}).get("name")) or f"{city}酒店"
    hotel_location = (hotel or {}).get("location")
    skipped_name = _clean(skipped_stop.get("name")) or "原景点"
    order = max([int(item.get("order") or 0) for item in stops] or [0]) + 1
    return {
        "name": f"{hotel_name}附近小吃街/商圈",
        "category": "街区美食",
        "section": "晚间替换安排",
        "description": (
            f"{skipped_name}的参考营业/适游时间与当前到达时间不匹配，已改为酒店附近小吃街、"
            "商圈或夜间街区。优先选择仍在营业、距离酒店近的店铺，适合晚到后轻松补给。"
        ),
        "address": _clean((hotel or {}).get("address")) or "酒店附近，以地图搜索营业中的小吃街/商圈为准",
        "open_time": "",
        "business_hours": "17:00-22:00（晚间街区/商圈参考营业时间）",
        "ticket_price": 0,
        "source": "schedule_replacement",
        "rag_score": 0,
        "interest_score": 0,
        "visit_duration": 90,
        "location": hotel_location or skipped_stop.get("location") or fallback_location(city, order + 30),
        "city": city,
        "order": order,
        "nearby_hotels": [hotel] if hotel else [],
        "replacement_for": skipped_name,
    }


def _schedule_fixed_breakfast(items: list[dict[str, Any]], meals: list[dict[str, Any]], scheduled: set[str]) -> None:
    meal = _meal_by_type(meals, "breakfast")
    if not meal:
        return
    start = MEAL_WINDOWS["breakfast"]["target"]
    end = start + MEAL_WINDOWS["breakfast"]["duration"]
    _mark_meal_scheduled(meal, start, end)
    scheduled.add("breakfast")
    items.append(_meal_timeline_entry(meal, start, end))


def _schedule_meal(
    items: list[dict[str, Any]],
    meals: list[dict[str, Any]],
    meal_type: str,
    cursor: int,
    scheduled: set[str],
    *,
    lookahead: int = 0,
    force: bool = False,
) -> int:
    if meal_type in scheduled:
        return cursor
    meal = _meal_by_type(meals, meal_type)
    if not meal:
        return cursor
    window = MEAL_WINDOWS[meal_type]
    if not force and cursor > int(window["latest"]):
        _mark_meal_unscheduled(meals, meal_type, "当天节奏较晚，建议根据现场情况补充简餐。")
        return cursor
    if not force and cursor + lookahead < int(window["target"]):
        return cursor

    start = max(cursor, int(window["target"]))
    if not force and start > int(window["latest"]):
        _mark_meal_unscheduled(meals, meal_type, "当天节奏较晚，建议根据现场情况补充简餐。")
        return cursor
    if force and start > int(window["latest"]) and cursor <= int(window["latest"]) + 90:
        start = cursor
    cursor = _append_buffer_if_needed(items, cursor, start)
    end = start + int(window["duration"])
    _mark_meal_scheduled(meal, start, end)
    scheduled.add(meal_type)
    items.append(_meal_timeline_entry(meal, start, end))
    return end


def _append_buffer_if_needed(items: list[dict[str, Any]], cursor: int, next_start: int) -> int:
    gap = next_start - cursor
    if gap >= 25:
        is_long_gap = gap >= 90
        items.append(
            _timeline_entry(
                "buffer",
                cursor,
                next_start,
                "自由活动/酒店休整" if is_long_gap else "弹性衔接",
                "这段不安排固定景点，建议回酒店休整、附近商圈补给或按现场情况自由活动。"
                if is_long_gap
                else "预留给排队、拍照、步行衔接或临时调整。",
            )
        )
    return next_start


def _append_route_item(items: list[dict[str, Any]], route: dict[str, Any], cursor: int, title: str) -> int:
    start = cursor
    end = start + int(route.get("duration_min") or 0)
    items.append(
        _timeline_entry(
            "route",
            start,
            end,
            title,
            route.get("description") or f"{route.get('from')} → {route.get('to')}",
            estimated_cost=route.get("estimated_cost") or 0,
            related={
                "from": route.get("from"),
                "to": route.get("to"),
                "mode": route.get("mode"),
                "distance_km": route.get("distance_km"),
                "duration_min": route.get("duration_min"),
            },
        )
    )
    return end


def _meal_by_type(meals: list[dict[str, Any]], meal_type: str) -> dict[str, Any] | None:
    return next((meal for meal in meals if meal.get("type") == meal_type), None)


def _mark_meal_scheduled(meal: dict[str, Any], start: int, end: int) -> None:
    meal["scheduled"] = True
    meal["start_time"] = _format_clock(start)
    meal["end_time"] = _format_clock(end)
    meal["time_note"] = f"{meal['start_time']}-{meal['end_time']}"


def _mark_meal_unscheduled(meals: list[dict[str, Any]], meal_type: str, note: str) -> None:
    meal = _meal_by_type(meals, meal_type)
    if not meal or meal.get("scheduled"):
        return
    meal["scheduled"] = False
    meal["time_note"] = note


def _meal_timeline_entry(meal: dict[str, Any], start: int, end: int) -> dict[str, Any]:
    label = MEAL_WINDOWS.get(str(meal.get("type")), {}).get("label") or "用餐"
    return _timeline_entry(
        "meal",
        start,
        end,
        meal.get("name") or str(label),
        meal.get("description") or "",
        estimated_cost=meal.get("estimated_cost") or 0,
        related={"meal_type": meal.get("type"), "label": label},
    )


def _timeline_entry(
    entry_type: str,
    start: int,
    end: int,
    title: str,
    description: str,
    *,
    estimated_cost: Any = 0,
    related: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start_text = _format_clock(start)
    end_text = _format_clock(end)
    return {
        "type": entry_type,
        "start_time": start_text,
        "end_time": end_text,
        "time_range": start_text if start_text == end_text else f"{start_text}-{end_text}",
        "title": title,
        "description": description,
        "estimated_cost": int(estimated_cost or 0),
        "related": related or {},
    }


def _first_non_meal_time(items: list[dict[str, Any]]) -> str | None:
    for item in items:
        if item.get("type") not in {"meal"}:
            return item.get("start_time")
    return items[0]["start_time"] if items else None


def _parse_clock(value: Any) -> int | None:
    text = _clean(value)
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 29 or minute > 59:
        return None
    return hour * 60 + minute


def _format_clock(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _build_meals(suggestions: list[dict[str, str]], day_index: int, budget_level: str) -> list[dict[str, Any]]:
    costs = {"tight": [15, 35, 45], "standard": [25, 55, 75], "relaxed": [45, 100, 150]}[budget_level]
    names = ["早餐", "午餐", "晚餐"]
    result = []
    for index, meal_type in enumerate(["breakfast", "lunch", "dinner"]):
        suggestion = suggestions[(day_index * 3 + index) % len(suggestions)] if suggestions else {}
        food = _clean(suggestion.get("food")) if isinstance(suggestion, dict) else _clean(suggestion)
        source = _clean(suggestion.get("source")) if isinstance(suggestion, dict) else ""
        meal_found = bool(food)
        title = f"{names[index]}：{food}" if meal_found else f"{names[index]}：知识库未找到合适就餐信息"
        if source == "amap" and food:
            title = f"{names[index]}：{food}（地图候选）"
        result.append(
            {
                "type": meal_type,
                "label": names[index],
                "name": title,
                "food": food,
                "place": _clean(suggestion.get("place")) if isinstance(suggestion, dict) else "",
                "place_address": _clean(suggestion.get("place_address")) if isinstance(suggestion, dict) else "",
                "anchor": "",
                "knowledge_found": source == "knowledge_base",
                "meal_source": source or ("knowledge_base" if meal_found else ""),
                "description": "知识库内未找到合适的就餐内容，请自行查阅。" if not meal_found else "结合本地餐饮信息给出的餐饮建议。",
                "estimated_cost": costs[index],
            }
        )
    return result


def _attach_meal_context(
    meals: list[dict[str, Any]],
    stops: list[dict[str, Any]],
    map_client: Any,
    city: str,
) -> None:
    if not meals:
        return
    anchors = {
        "breakfast": stops[0] if stops else None,
        "lunch": stops[min(1, len(stops) - 1)] if stops else None,
        "dinner": stops[-1] if stops else None,
    }
    for meal in meals:
        meal_type = str(meal.get("type") or "")
        anchor = anchors.get(meal_type)
        anchor_name = (anchor or {}).get("name") or city
        meal["anchor"] = anchor_name
        if meal.get("place"):
            restaurant = {"name": meal.get("place"), "address": meal.get("place_address") or ""}
        else:
            restaurant = _find_meal_place(map_client, anchor, meal.get("food") or "餐厅")
        if restaurant:
            meal["place"] = restaurant.get("name") or ""
            meal["place_address"] = restaurant.get("address") or ""
            place_text = f"{meal['place']}（{meal.get('place_address') or '地址以地图为准'}）"
        else:
            place_text = f"{anchor_name}周边"

        if meal.get("knowledge_found"):
            meal["description"] = (
                f"吃什么：{meal.get('food')}。在哪吃：{place_text}。"
                "若店铺未返回或营业状态不确定，请出发前用高德/大众点评二次确认。"
            )
        elif meal.get("meal_source") == "amap" and meal.get("food"):
            meal["description"] = (
                f"吃什么：{meal.get('food')}。在哪吃：{place_text}。"
                "来源为高德地图餐饮候选，营业状态和排队情况请出发前二次确认。"
            )
        else:
            meal["description"] = (
                f"知识库内未找到合适的就餐内容或具体店铺；建议在{anchor_name}周边自行查阅餐厅，"
                "不要把这里当成已核验推荐。"
            )


def _find_meal_place(map_client: Any, anchor: dict[str, Any] | None, keyword: str) -> dict[str, Any] | None:
    if not anchor or not anchor.get("location") or not getattr(map_client, "enabled", False):
        return None
    around = getattr(map_client, "around_poi", None)
    if not callable(around):
        return None
    try:
        pois = around(anchor["location"], keywords=keyword or "餐厅", radius=1800, limit=3, types="050000")
    except Exception:
        return None
    return next((poi for poi in pois if poi.get("name")), None)


def _build_budget(
    day_plans: list[dict[str, Any]],
    *,
    budget: int,
    intercity_transport: dict[str, Any] | None = None,
    include_intercity: bool = False,
) -> dict[str, Any]:
    attractions = sum(
        int(stop.get("ticket_price") or 0)
        for day in day_plans
        for stop in day.get("stops", [])
        if stop.get("scheduled") is not False
    )
    hotels = sum(int(day.get("hotel", {}).get("estimated_cost") or 0) for day in day_plans if day.get("hotel"))
    meals = sum(int(meal.get("estimated_cost") or 0) for day in day_plans for meal in day.get("meals", []))
    transportation = sum(int(route.get("estimated_cost") or 0) for day in day_plans for route in day.get("routes", []))
    transportation += sum(
        int(route.get("estimated_cost") or 0) for day in day_plans for route in day.get("hotel_transfers", [])
    )
    local_total = attractions + hotels + meals + transportation
    selected_intercity = (intercity_transport or {}).get("selected") or {}
    intercity = int(selected_intercity.get("estimated_cost") or 0)
    total = local_total + intercity if include_intercity else local_total
    return {
        "total_attractions": attractions,
        "total_hotels": hotels,
        "total_meals": meals,
        "total_transportation": transportation,
        "total_intercity_transportation": intercity,
        "intercity_included": include_intercity,
        "local_total": local_total,
        "total": total,
        "budget_limit": budget,
        "remaining": budget - total if budget else None,
        "is_over_budget": bool(budget and total > budget),
    }


def _budget_note(scope: str, include_intercity: bool | None) -> str:
    if include_intercity is True:
        return "预算按包含往返城际交通理解；城际交通会优先使用已接入的实时工具，查不到时兜底估算，真实票价需以12306、航班或客运平台为准。"
    if include_intercity is False or "不含" in scope or "目的地内" in scope:
        return "预算按目的地内消费理解，不包含从出发地到目的地的高铁、机票、大巴等往返城际交通。"
    return "预算范围未完全明确，当前总费用不计入高铁、机票、大巴等往返城际交通。"


def _intercity_tool_status(intercity_transport: dict[str, Any]) -> str:
    options = intercity_transport.get("options") or []
    if not options:
        return "not-selected"
    if any(option.get("source") == "flight_time_candidates" for option in options):
        return "flight-time-candidates"
    if any(option.get("ticket_selection_required") for option in options):
        return "12306-mcp-candidates"
    if any(option.get("source") == "12306_mcp" for option in options):
        return "12306-mcp"
    if any(option.get("ticket_query_source") == "12306_mcp" for option in options):
        return "12306-mcp-no-ticket"
    return "fallback-estimate"


def _align_weather(weather: list[dict[str, Any]], start_date: date, days: int, city: str) -> list[dict[str, Any]]:
    aligned = []
    for index in range(days):
        source = weather[index % len(weather)]
        aligned.append(
            {
                **source,
                "date": (start_date + timedelta(days=index)).isoformat(),
                "city": city,
            }
        )
    return aligned
