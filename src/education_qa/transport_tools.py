from __future__ import annotations

import re
from typing import Any, Callable

from .geo_tools import city_center, haversine_km


INTERCITY_MODES = ["高铁/火车", "飞机", "长途大巴", "自驾", "骑行"]
LOCAL_MODES = ["公共交通优先", "步行优先", "共享单车优先", "打车优先", "自驾"]

KNOWN_INTERCITY: dict[tuple[str, str], dict[str, dict[str, Any]]] = {
    ("重庆", "成都"): {
        "高铁/火车": {"one_way_cost": 160, "duration_min": 115, "distance_km": 310},
        "长途大巴": {"one_way_cost": 115, "duration_min": 250, "distance_km": 310},
        "自驾": {"one_way_cost": 260, "duration_min": 250, "distance_km": 310},
        "飞机": {"one_way_cost": 520, "duration_min": 210, "distance_km": 310, "not_recommended": True},
        "骑行": {"one_way_cost": 35, "duration_min": 2100, "distance_km": 310, "not_recommended": True},
    },
}

CITY_MOBILITY_RULES: dict[str, dict[str, Any]] = {
    "成都": {
        "motorcycle_policy": "中心城区存在摩托车/电动车通行限制，旅游规划不默认推荐摩托或电动车。",
        "shared_bike_policy": "共享单车适合短距离接驳，跨区或景区内部请以现场停放规则为准。",
        "driving_policy": "热门景区周边停车和限行不稳定，自驾只作为备选。",
        "discouraged_modes": ["摩托车", "电动车"],
    },
    "杭州": {
        "motorcycle_policy": "主城区对摩托车通行较谨慎，景区周边不默认推荐摩托或电动车。",
        "shared_bike_policy": "共享单车适合西湖周边短距离接驳，部分景区入口需按停放点停车。",
        "driving_policy": "西湖景区可能有交通管控，自驾需提前确认。",
        "discouraged_modes": ["摩托车", "电动车"],
    },
}


def estimate_intercity_transport(
    origin: str,
    destination: str,
    *,
    modes: list[str] | None = None,
    include_round_trip: bool = True,
    included_in_budget: bool = False,
    travel_date: Any = None,
    return_date: Any = None,
    railway_lookup: Callable[[str, str, Any], dict[str, Any] | None] | None = None,
    selected_train_index: Any = None,
    selected_train_ticket: Any = None,
    selected_return_train_index: Any = None,
    selected_return_train_ticket: Any = None,
    departure_time: Any = None,
) -> dict[str, Any]:
    if not origin or origin == destination:
        return {
            "origin": origin,
            "destination": destination,
            "selected_mode": "未涉及",
            "included_in_budget": included_in_budget,
            "options": [],
            "summary": "未识别到出发地，暂不估算往返城际交通。",
            "source": "fallback_estimate",
        }

    normalized_modes = _normalize_intercity_modes(modes)
    if not normalized_modes:
        return {
            "origin": origin,
            "destination": destination,
            "selected_mode": "未确定",
            "included_in_budget": included_in_budget,
            "options": [],
            "selected": None,
            "summary": "已识别出发地和目的地，但未确认高铁、飞机、大巴、自驾等城际交通方式，暂不估算往返费用。",
            "source": "fallback_estimate",
        }

    pair_data = _known_pair(origin, destination)
    options = []
    requested_train_index = _coerce_selected_train_index(selected_train_index)
    requested_train_ticket = _coerce_selected_train_ticket(selected_train_ticket)
    requested_return_train_index = _coerce_selected_train_index(selected_return_train_index)
    requested_return_train_ticket = _coerce_selected_train_ticket(selected_return_train_ticket)
    for mode in normalized_modes:
        base = dict(pair_data.get(mode) or _estimate_intercity_by_distance(origin, destination, mode))
        realtime = _lookup_realtime_train(origin, destination, travel_date, mode, railway_lookup)
        return_realtime = (
            _lookup_realtime_train(destination, origin, return_date, mode, railway_lookup)
            if include_round_trip and return_date
            else None
        )
        if mode == "高铁/火车":
            if realtime and realtime.get("train_tickets"):
                base = _merge_train_ticket_candidates(base, realtime)
                if requested_train_index is not None or requested_train_ticket is not None:
                    base = _apply_selected_train_ticket(base, requested_train_index, requested_train_ticket)
            elif requested_train_ticket is not None:
                if realtime:
                    base = _merge_transport_data(base, realtime)
                    if realtime.get("ticket_query_source") == "12306_mcp":
                        base["source"] = "12306_mcp"
                base = _apply_selected_train_ticket(base, requested_train_index, requested_train_ticket)
            elif realtime:
                base = _merge_transport_data(base, realtime)
                if realtime.get("ticket_query_source") == "12306_mcp":
                    base["source"] = "12306_mcp"
            elif railway_lookup is None:
                base = {
                    **base,
                    "ticket_query_source": "not_configured",
                    "ticket_query_error": "12306-MCP未启用，当前没有查询当天车票。",
                    "notice": "未启用12306-MCP，当前只按距离估算；请启动12306-MCP后重新生成，或改为自驾/其他方式。",
                }
            base = _attach_return_train_options(
                base,
                return_realtime,
                return_date,
                requested_return_train_index,
                requested_return_train_ticket,
                railway_lookup is None,
            )
        elif mode == "飞机":
            base = _merge_flight_time_candidates(base, origin, destination, travel_date)
            if requested_train_index is not None or requested_train_ticket is not None:
                base = _apply_selected_train_ticket(base, requested_train_index, requested_train_ticket)
            base = _attach_return_flight_options(
                base,
                destination,
                origin,
                return_date,
                requested_return_train_index,
                requested_return_train_ticket,
            )
        elif realtime:
            base = _merge_transport_data(base, realtime)
        base = _apply_manual_departure_time(base, mode, departure_time)
        one_way_cost = int(base["one_way_cost"])
        return_one_way_cost = _coerce_positive_int(base.get("return_one_way_cost"), one_way_cost)
        total_cost = one_way_cost + return_one_way_cost if include_round_trip else one_way_cost
        duration_min = int(base["duration_min"])
        option = {
            "mode": mode,
            "one_way_cost": one_way_cost,
            "estimated_cost": total_cost,
            "duration_min": duration_min,
            "duration_text": _duration_text(duration_min),
            "distance_km": round(float(base["distance_km"]), 1),
            "included_in_budget": included_in_budget,
            "source": base.get("source", "fallback_estimate"),
            "notice": base.get("notice") or _intercity_notice(mode, bool(base.get("not_recommended"))),
            "not_recommended": bool(base.get("not_recommended")),
        }
        for key in (
            "train_code",
            "flight_code",
            "seat_type",
            "ticket_status",
            "depart_time",
            "arrive_time",
            "from_station",
            "to_station",
            "query_date",
            "flight_tickets",
            "ticket_query_source",
            "ticket_query_transport",
            "ticket_query_error",
            "train_tickets",
            "selected_train_index",
            "ticket_selection_required",
            "arrival_day_offset",
            "departure_time_error",
            "transfer_note",
            "segments",
            "return_query_date",
            "return_train_tickets",
            "return_flight_tickets",
            "selected_return_train_index",
            "return_ticket_selection_required",
            "return_ticket_query_source",
            "return_ticket_query_transport",
            "return_ticket_query_error",
            "return_train_code",
            "return_flight_code",
            "return_seat_type",
            "return_ticket_status",
            "return_depart_time",
            "return_arrive_time",
            "return_from_station",
            "return_to_station",
            "return_duration_min",
            "return_duration_text",
            "return_one_way_cost",
            "return_transfer_note",
            "return_segments",
            "return_notice",
        ):
            if key in base and base.get(key) not in (None, "", []):
                option[key] = base[key]
        options.append(option)

    selected = next((item for item in options if not item["not_recommended"]), options[0] if options else None)
    return {
        "origin": origin,
        "destination": destination,
        "selected_mode": selected["mode"] if selected else "未确定",
        "included_in_budget": included_in_budget,
        "include_round_trip": include_round_trip,
        "options": options,
        "selected": selected,
        "summary": _intercity_summary(origin, destination, selected, included_in_budget),
        "source": selected.get("source", "fallback_estimate") if selected else "fallback_estimate",
    }


def build_mobility_policy(city: str, preference: str, constraints: list[str] | None = None) -> dict[str, Any]:
    constraints = constraints or []
    rules = CITY_MOBILITY_RULES.get(
        city,
        {
            "motorcycle_policy": "未接入城市禁摩/限摩官方数据，默认不推荐摩托或电动车作为主方案。",
            "shared_bike_policy": "共享单车仅作短距离接驳建议，需以现场停放规则为准。",
            "driving_policy": "景区周边停车和限行需以当天实际公告为准。",
            "discouraged_modes": ["摩托车", "电动车"],
        },
    )
    notes = [rules["motorcycle_policy"], rules["shared_bike_policy"]]
    if "不打车" in constraints:
        notes.append("用户不希望打车，路线会优先公交、地铁、步行或共享单车。")
    if "少走路" in constraints:
        notes.append("用户不希望走太远，超过约1.5公里会避免纯步行。")
    if "少绕路" in constraints:
        notes.append("用户希望通勤方便、少绕路，路线会优先按相邻点位顺序衔接。")
    if "骑行" in preference or "共享单车" in preference:
        notes.append("共享单车只会用于短距离，跨区和景区内部会自动降级为公交/步行建议。")
    if "摩托" in preference or "电动车" in preference:
        notes.append("由于城市禁摩/限摩不稳定，摩托和电动车不会作为默认路线。")

    return {
        "city": city,
        "preference": preference,
        "constraints": constraints,
        "discouraged_modes": rules.get("discouraged_modes", []),
        "notes": notes,
        "source": "fallback_policy",
    }


def estimate_local_route(
    start: dict[str, Any],
    end: dict[str, Any],
    *,
    preference: str,
    mobility_policy: dict[str, Any],
    budget_level: str = "standard",
) -> dict[str, Any]:
    distance_km = haversine_km(start["location"], end["location"])
    constraints = set(mobility_policy.get("constraints") or [])
    warnings: list[str] = []
    pref = preference or ""

    if ("摩托" in pref or "电动车" in pref) and mobility_policy.get("discouraged_modes"):
        warnings.append("已避开摩托/电动车，因为城市禁摩或景区通行规则可能影响路线。")
        pref = "公共交通优先"

    if "步行" in pref and distance_km > 3:
        warnings.append("两站距离较远，未强制纯步行，避免行程过累。")
    if "共享单车" in pref and distance_km > 5:
        warnings.append("两站距离超过共享单车舒适范围，改用公共交通估算。")
    if "少走路" in constraints and distance_km > 1.5:
        warnings.append("已根据少走路偏好避开长距离步行。")

    if "步行" in pref and distance_km <= 3 and "少走路" not in constraints:
        mode = "步行"
        duration = max(8, round(distance_km / 4.2 * 60))
        cost = 0
    elif "共享单车" in pref and distance_km <= 5 and "不骑车" not in constraints:
        mode = "共享单车"
        duration = max(10, round(distance_km / 10 * 60))
        cost = max(2, round(duration / 30 * 2))
    elif ("打车" in pref or distance_km > 8) and "不打车" not in constraints and budget_level != "tight":
        mode = "打车/网约车"
        duration = max(12, round(distance_km / 24 * 60 + 8))
        cost = max(12, round(10 + distance_km * 2.4))
    elif distance_km <= 1.2 and "少走路" not in constraints:
        mode = "步行"
        duration = max(8, round(distance_km / 4.2 * 60))
        cost = 0
    else:
        mode = "地铁/公交"
        duration = max(18, round(distance_km / 18 * 60 + 10))
        cost = max(2, min(10, round(2 + distance_km * 0.6)))

    return {
        "from": start["name"],
        "to": end["name"],
        "mode": mode,
        "distance_km": round(distance_km, 2),
        "duration_min": int(duration),
        "estimated_cost": int(cost),
        "description": f"{start['name']} → {end['name']}，建议{mode}，约{distance_km:.1f}公里，{duration}分钟。",
        "warnings": warnings,
        "is_estimated": True,
    }


def _normalize_intercity_modes(modes: list[str] | None) -> list[str]:
    cleaned = []
    for mode in modes or []:
        normalized = _normalize_intercity_mode(mode)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _normalize_intercity_mode(mode: str) -> str:
    if "飞" in mode or "机" in mode:
        return "飞机"
    if "大巴" in mode or "客车" in mode or "汽车" in mode:
        return "长途大巴"
    if "自驾" in mode or "开车" in mode:
        return "自驾"
    if "骑" in mode or "自行车" in mode:
        return "骑行"
    if "高铁" in mode or "火车" in mode or "动车" in mode:
        return "高铁/火车"
    if mode in INTERCITY_MODES:
        return mode
    return ""


def _coerce_selected_train_index(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        index = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return index if index >= 0 else None


def _coerce_selected_train_ticket(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    keys = (
        "train_code",
        "flight_code",
        "seat_type",
        "ticket_status",
        "depart_time",
        "arrive_time",
        "duration_min",
        "duration_text",
        "from_station",
        "to_station",
        "one_way_cost",
        "round_trip_cost",
        "transfer_note",
        "query_date",
        "available",
        "arrival_day_offset",
        "source",
        "ticket_query_source",
        "ticket_query_transport",
    )
    ticket = {key: value.get(key) for key in keys if value.get(key) not in (None, "", [])}
    if "available" in value:
        ticket["available"] = bool(value.get("available"))

    segments = value.get("segments")
    if isinstance(segments, list):
        cleaned_segments = [
            cleaned
            for segment in segments
            if isinstance(segment, dict)
            if (cleaned := _coerce_selected_train_ticket(segment))
        ]
        if cleaned_segments:
            ticket["segments"] = cleaned_segments

    identity_fields = ("train_code", "flight_code", "depart_time", "arrive_time", "from_station", "to_station")
    return ticket if any(ticket.get(key) for key in identity_fields) else None


def _apply_manual_departure_time(base: dict[str, Any], mode: str, departure_time: Any) -> dict[str, Any]:
    if mode not in {"自驾", "骑行"} or not departure_time:
        return base
    depart_min = _parse_clock_min(departure_time)
    if depart_min is None:
        return {
            **base,
            "departure_time_error": "出发时间格式无效，请使用 08:30 这种时间。",
        }
    duration_min = _coerce_positive_int(base.get("duration_min"))
    if duration_min <= 0:
        return base
    arrive_abs = depart_min + duration_min
    day_offset = arrive_abs // (24 * 60)
    arrive_min = arrive_abs % (24 * 60)
    return {
        **base,
        "depart_time": _format_clock_min(depart_min),
        "arrive_time": _format_clock_min(arrive_min),
        "arrival_day_offset": day_offset,
        "notice": f"{mode}已按{_format_clock_min(depart_min)}出发估算，预计{_format_clock_min(arrive_min)}到达；路况、停车和限行需以当天实际情况为准。",
    }


def _parse_clock_min(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.match(r"^(\d{1,2})[:：](\d{1,2})$", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _format_clock_min(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _attach_return_train_options(
    base: dict[str, Any],
    realtime: dict[str, Any] | None,
    return_date: Any,
    selected_index: int | None,
    selected_ticket: dict[str, Any] | None,
    railway_not_configured: bool,
) -> dict[str, Any]:
    if not return_date and realtime is None and selected_ticket is None:
        return base

    fallback = {
        "one_way_cost": base.get("one_way_cost"),
        "duration_min": base.get("duration_min"),
        "distance_km": base.get("distance_km"),
    }
    return_base = dict(fallback)
    if realtime and realtime.get("train_tickets"):
        return_base = _merge_train_ticket_candidates(return_base, realtime)
        if selected_index is not None or selected_ticket is not None:
            return_base = _apply_selected_train_ticket(return_base, selected_index, selected_ticket)
    elif selected_ticket is not None:
        if realtime:
            return_base = _merge_transport_data(return_base, realtime)
        return_base = _apply_selected_train_ticket(return_base, selected_index, selected_ticket)
    elif realtime:
        return_base = _merge_transport_data(return_base, realtime)
    elif railway_not_configured:
        return_base = {
            **return_base,
            "ticket_query_source": "not_configured",
            "ticket_query_error": "12306-MCP未启用，当前没有查询返程车票。",
        }
    else:
        return_base = {**return_base, "ticket_query_error": "暂未查询到返程车票候选。"}

    updated = {
        **base,
        "return_query_date": return_base.get("query_date") or _format_query_date(return_date),
    }
    mapping = {
        "train_tickets": "return_train_tickets",
        "selected_train_index": "selected_return_train_index",
        "ticket_selection_required": "return_ticket_selection_required",
        "ticket_query_source": "return_ticket_query_source",
        "ticket_query_transport": "return_ticket_query_transport",
        "ticket_query_error": "return_ticket_query_error",
        "train_code": "return_train_code",
        "seat_type": "return_seat_type",
        "ticket_status": "return_ticket_status",
        "depart_time": "return_depart_time",
        "arrive_time": "return_arrive_time",
        "from_station": "return_from_station",
        "to_station": "return_to_station",
        "duration_min": "return_duration_min",
        "duration_text": "return_duration_text",
        "one_way_cost": "return_one_way_cost",
        "transfer_note": "return_transfer_note",
        "segments": "return_segments",
        "notice": "return_notice",
    }
    for source_key, target_key in mapping.items():
        value = return_base.get(source_key)
        if value not in (None, "", []):
            updated[target_key] = value
    if "return_duration_min" in updated and "return_duration_text" not in updated:
        updated["return_duration_text"] = _duration_text(int(updated["return_duration_min"]))
    return updated


def _attach_return_flight_options(
    base: dict[str, Any],
    origin: str,
    destination: str,
    return_date: Any,
    selected_index: int | None,
    selected_ticket: dict[str, Any] | None,
) -> dict[str, Any]:
    if not return_date and selected_ticket is None:
        return base

    fallback = {
        "one_way_cost": base.get("one_way_cost"),
        "duration_min": base.get("duration_min"),
        "distance_km": base.get("distance_km"),
    }
    return_base = _merge_flight_time_candidates(fallback, origin, destination, return_date, is_return=True)
    if selected_index is not None or selected_ticket is not None:
        return_base = _apply_selected_train_ticket(return_base, selected_index, selected_ticket)

    updated = {
        **base,
        "return_query_date": return_base.get("query_date") or _format_query_date(return_date),
    }
    mapping = {
        "train_tickets": "return_train_tickets",
        "flight_tickets": "return_flight_tickets",
        "selected_train_index": "selected_return_train_index",
        "ticket_selection_required": "return_ticket_selection_required",
        "ticket_query_source": "return_ticket_query_source",
        "ticket_query_transport": "return_ticket_query_transport",
        "ticket_query_error": "return_ticket_query_error",
        "train_code": "return_train_code",
        "flight_code": "return_flight_code",
        "seat_type": "return_seat_type",
        "ticket_status": "return_ticket_status",
        "depart_time": "return_depart_time",
        "arrive_time": "return_arrive_time",
        "from_station": "return_from_station",
        "to_station": "return_to_station",
        "duration_min": "return_duration_min",
        "duration_text": "return_duration_text",
        "one_way_cost": "return_one_way_cost",
        "transfer_note": "return_transfer_note",
        "segments": "return_segments",
        "notice": "return_notice",
    }
    for source_key, target_key in mapping.items():
        value = return_base.get(source_key)
        if value not in (None, "", []):
            updated[target_key] = value
    if "return_duration_min" in updated and "return_duration_text" not in updated:
        updated["return_duration_text"] = _duration_text(int(updated["return_duration_min"]))
    return updated


def _format_query_date(value: Any) -> str:
    if value is None:
        return ""
    formatter = getattr(value, "isoformat", None)
    if callable(formatter):
        return str(formatter())
    return str(value)


def _apply_selected_train_ticket(
    base: dict[str, Any],
    selected_index: int | None,
    selected_ticket: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tickets = base.get("train_tickets") or []
    ticket_label = _ticket_label(base, selected_ticket)
    matched_index = _find_selected_train_ticket_index(tickets, selected_ticket)
    if matched_index is not None:
        return _apply_train_ticket_to_base(base, tickets[matched_index], matched_index)

    if selected_ticket is not None:
        if not _selected_ticket_available(selected_ticket):
            return {
                **base,
                "selected_train_index": None,
                "ticket_selection_required": True,
                "ticket_query_error": f"选择的{ticket_label}当前不可用，请换一个可用{ticket_label}。",
            }
        locked_ticket = {**selected_ticket, "available": selected_ticket.get("available", True)}
        refreshed_tickets = [locked_ticket]
        refreshed_tickets.extend(
            ticket
            for ticket in tickets
            if not (isinstance(ticket, dict) and _same_train_ticket(ticket, locked_ticket))
        )
        locked_base = {
            **base,
            "train_tickets": refreshed_tickets,
        }
        return _apply_train_ticket_to_base(
            locked_base,
            locked_ticket,
            0,
            notice=(
                "已按用户选择的航班候选时刻锁定排程；候选列表刷新时以所选航班为准，实际航班、时刻和票价请以航司/航旅纵横/携程等平台为准。"
                if ticket_label == "航班"
                else "已按用户选择的车次锁定排程；候选列表刷新时以所选车次为准，购票和最终票价仍以12306官方为准。"
            ),
        )

    if selected_index is None or selected_index >= len(tickets):
        return {
            **base,
            "selected_train_index": None,
            "ticket_selection_required": True,
            "ticket_query_error": f"选择的{ticket_label}序号无效，请重新选择当天{ticket_label}。",
        }
    ticket = tickets[selected_index]
    if not isinstance(ticket, dict) or not ticket.get("available"):
        return {
            **base,
            "selected_train_index": None,
            "ticket_selection_required": True,
            "ticket_query_error": f"选择的{ticket_label}当前不可用，请换一个可用{ticket_label}。",
        }

    return _apply_train_ticket_to_base(base, ticket, selected_index)


def _ticket_label(base: dict[str, Any], selected_ticket: dict[str, Any] | None = None) -> str:
    if base.get("flight_tickets") or (selected_ticket and selected_ticket.get("flight_code")):
        return "航班"
    return "车次"


def _find_selected_train_ticket_index(tickets: list[Any], selected_ticket: dict[str, Any] | None) -> int | None:
    if not selected_ticket:
        return None
    for index, ticket in enumerate(tickets):
        if isinstance(ticket, dict) and ticket.get("available") and _same_train_ticket(ticket, selected_ticket):
            return index
    return None


def _same_train_ticket(ticket: dict[str, Any], selected_ticket: dict[str, Any]) -> bool:
    ticket_code = ticket.get("train_code") or ticket.get("flight_code")
    selected_code = selected_ticket.get("train_code") or selected_ticket.get("flight_code")
    if not _same_ticket_value(ticket_code, selected_code):
        return False
    if not all(_same_ticket_value(ticket.get(key), selected_ticket.get(key)) for key in ("depart_time", "arrive_time")):
        return False
    for key in ("from_station", "to_station"):
        if selected_ticket.get(key) and ticket.get(key) and not _same_ticket_value(ticket.get(key), selected_ticket.get(key)):
            return False
    return True


def _same_ticket_value(left: Any, right: Any) -> bool:
    return str(left or "").strip().lower() == str(right or "").strip().lower()


def _selected_ticket_available(ticket: dict[str, Any]) -> bool:
    return ticket.get("available", True) is not False


def _apply_train_ticket_to_base(
    base: dict[str, Any],
    ticket: dict[str, Any],
    selected_index: int,
    *,
    notice: str | None = None,
) -> dict[str, Any]:
    one_way_cost = _coerce_positive_int(ticket.get("one_way_cost"), base.get("one_way_cost"))
    duration_min = _coerce_positive_int(ticket.get("duration_min"), base.get("duration_min"))
    if one_way_cost <= 0 or duration_min <= 0:
        return base

    is_flight = bool(ticket.get("flight_code") or base.get("flight_tickets") or ticket.get("ticket_query_transport") == "fallback_flight_time")
    source = ticket.get("source") or base.get("source") or ("flight_time_candidates" if is_flight else "12306_mcp")
    default_notice = (
        "已按用户选择的航班候选时刻更新预算和到达时间；当前未接入实时航班出票接口，实际航班号、时刻和票价请以航司/航旅纵横/携程等平台为准。"
        if is_flight
        else "已按用户选择的12306-MCP车次更新预算和到达时间；购票和最终票价仍以12306官方为准。"
    )
    code = ticket.get("train_code") or ticket.get("flight_code") or base.get("train_code")
    updated = {
        **base,
        "one_way_cost": one_way_cost,
        "duration_min": duration_min,
        "train_code": code,
        "flight_code": ticket.get("flight_code") or (code if is_flight else base.get("flight_code")),
        "seat_type": ticket.get("seat_type") or base.get("seat_type"),
        "ticket_status": ticket.get("ticket_status") or base.get("ticket_status"),
        "depart_time": ticket.get("depart_time") or base.get("depart_time"),
        "arrive_time": ticket.get("arrive_time") or base.get("arrive_time"),
        "from_station": ticket.get("from_station") or base.get("from_station"),
        "to_station": ticket.get("to_station") or base.get("to_station"),
        "selected_train_index": selected_index,
        "ticket_selection_required": False,
        "source": source,
        "notice": notice or default_notice,
    }
    for key in ("transfer_note", "segments", "arrival_day_offset", "query_date", "ticket_query_source", "ticket_query_transport"):
        if ticket.get(key) not in (None, "", []):
            updated[key] = ticket[key]
    return updated


def _coerce_positive_int(value: Any, fallback: Any = 0) -> int:
    for candidate in (value, fallback):
        try:
            number = int(round(float(str(candidate).strip())))
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return 0


def _merge_train_ticket_candidates(base: dict[str, Any], realtime: dict[str, Any]) -> dict[str, Any]:
    merged = {
        **base,
        "source": "12306_mcp",
        "ticket_selection_required": True,
        "notice": "已通过12306-MCP查到当天候选车次；请选择具体车次后，系统会按到达时间重排行程。未选择前按08:30开始游玩。",
    }
    for key in (
        "train_tickets",
        "ticket_query_source",
        "ticket_query_transport",
        "ticket_query_error",
        "query_date",
    ):
        if key in realtime and realtime.get(key) not in (None, "", []):
            merged[key] = realtime[key]
    return merged


def _merge_flight_time_candidates(
    base: dict[str, Any],
    origin: str,
    destination: str,
    travel_date: Any,
    *,
    is_return: bool = False,
) -> dict[str, Any]:
    tickets = _generate_flight_time_candidates(origin, destination, travel_date, base, is_return=is_return)
    return {
        **base,
        "source": "flight_time_candidates",
        "ticket_selection_required": True,
        "ticket_query_source": "flight_time_candidates",
        "ticket_query_transport": "fallback_flight_time",
        "query_date": _format_query_date(travel_date),
        "train_tickets": tickets,
        "flight_tickets": tickets,
        "notice": "当前未接入实时航班MCP/API，先提供航班号和起降时间候选用于排期；实际航班、时刻和票价请以航司/航旅纵横/携程等平台为准。",
    }


def _generate_flight_time_candidates(
    origin: str,
    destination: str,
    travel_date: Any,
    base: dict[str, Any],
    *,
    is_return: bool = False,
) -> list[dict[str, Any]]:
    distance = float(base.get("distance_km") or 0) or max(30.0, haversine_km(city_center(origin), city_center(destination)) * 1.25)
    flight_duration = max(45, min(260, round(distance / 720 * 60 + 35)))
    base_cost = _coerce_positive_int(base.get("one_way_cost"), max(320, round(distance * 0.85)))
    depart_slots = (9 * 60 + 20, 13 * 60 + 10, 17 * 60 + 35, 20 * 60 + 15) if is_return else (8 * 60 + 15, 11 * 60 + 30, 15 * 60 + 45, 19 * 60 + 5)
    carriers = ("MU", "CA", "CZ", "HU", "3U", "FM")
    seed = _stable_route_seed(origin, destination, travel_date)
    tickets: list[dict[str, Any]] = []
    for index, depart_min in enumerate(depart_slots):
        arrival_abs = depart_min + flight_duration
        arrive_min = arrival_abs % (24 * 60)
        carrier = carriers[(seed + index) % len(carriers)]
        flight_code = f"{carrier}{1000 + ((seed + index * 137) % 8000)}"
        price = max(260, round((base_cost * (0.88 + index * 0.12)) / 10) * 10)
        tickets.append(
            {
                "train_code": flight_code,
                "flight_code": flight_code,
                "seat_type": "经济舱参考",
                "ticket_status": "候选时刻",
                "depart_time": _format_clock_min(depart_min),
                "arrive_time": _format_clock_min(arrive_min),
                "from_station": _flight_airport_name(origin),
                "to_station": _flight_airport_name(destination),
                "one_way_cost": price,
                "duration_min": flight_duration,
                "duration_text": _duration_text(flight_duration),
                "available": True,
                "arrival_day_offset": arrival_abs // (24 * 60),
                "query_date": _format_query_date(travel_date),
                "source": "flight_time_candidates",
                "ticket_query_source": "flight_time_candidates",
                "ticket_query_transport": "fallback_flight_time",
            }
        )
    return tickets


def _stable_route_seed(origin: str, destination: str, travel_date: Any) -> int:
    text = f"{origin}-{destination}-{_format_query_date(travel_date)}"
    return sum((index + 1) * ord(char) for index, char in enumerate(text))


def _flight_airport_name(city: str) -> str:
    airports = {
        "北京": "北京首都/大兴机场",
        "上海": "上海虹桥/浦东机场",
        "广州": "广州白云机场",
        "深圳": "深圳宝安机场",
        "杭州": "杭州萧山机场",
        "南京": "南京禄口机场",
        "合肥": "合肥新桥机场",
        "六安": "合肥新桥机场(六安周边)",
        "铜陵": "池州九华山机场(铜陵周边)",
        "池州": "池州九华山机场",
        "芜湖": "芜湖宣州机场",
        "成都": "成都天府/双流机场",
        "重庆": "重庆江北机场",
        "西安": "西安咸阳机场",
        "武汉": "武汉天河机场",
        "长沙": "长沙黄花机场",
        "昆明": "昆明长水机场",
        "大理": "大理凤仪机场",
        "丽江": "丽江三义机场",
        "厦门": "厦门高崎机场",
        "青岛": "青岛胶东机场",
        "济南": "济南遥墙机场",
        "淄博": "济南遥墙机场(淄博周边)",
        "天津": "天津滨海机场",
        "太原": "太原武宿机场",
        "南昌": "南昌昌北机场",
        "福州": "福州长乐机场",
        "郑州": "郑州新郑机场",
        "贵阳": "贵阳龙洞堡机场",
        "海口": "海口美兰机场",
        "三亚": "三亚凤凰机场",
    }
    return airports.get(city, f"{city}周边机场")


def _merge_transport_data(base: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        **{key: value for key, value in data.items() if value not in (None, "", 0, []) or key == "one_way_cost"},
    }


def _known_pair(origin: str, destination: str) -> dict[str, dict[str, Any]]:
    return KNOWN_INTERCITY.get((origin, destination)) or KNOWN_INTERCITY.get((destination, origin)) or {}


def _lookup_realtime_train(
    origin: str,
    destination: str,
    travel_date: Any,
    mode: str,
    railway_lookup: Callable[[str, str, Any], dict[str, Any] | None] | None,
) -> dict[str, Any] | None:
    if mode != "高铁/火车" or railway_lookup is None:
        return None
    try:
        return railway_lookup(origin, destination, travel_date)
    except Exception:
        return {
            "ticket_query_source": "12306_mcp",
            "ticket_query_transport": "unavailable",
            "ticket_query_error": "12306-MCP调用异常，暂未拿到当天车票列表。",
            "notice": "12306-MCP调用异常，当前按距离估算；请确认本地12306-MCP服务是否运行。",
        }


def _estimate_intercity_by_distance(origin: str, destination: str, mode: str) -> dict[str, Any]:
    distance = max(30.0, haversine_km(city_center(origin), city_center(destination)) * 1.25)
    if mode == "飞机":
        return {
            "one_way_cost": max(320, round(distance * 0.85)),
            "duration_min": round(distance / 650 * 60 + 130),
            "distance_km": distance,
            "not_recommended": distance < 350,
        }
    if mode == "长途大巴":
        return {"one_way_cost": max(35, round(distance * 0.32)), "duration_min": round(distance / 75 * 60 + 35), "distance_km": distance}
    if mode == "自驾":
        return {"one_way_cost": max(60, round(distance * 0.85)), "duration_min": round(distance / 85 * 60 + 25), "distance_km": distance}
    if mode == "骑行":
        return {
            "one_way_cost": max(20, round(distance * 0.08)),
            "duration_min": round(distance / 12 * 60),
            "distance_km": distance,
            "not_recommended": distance > 60,
        }
    return {"one_way_cost": max(35, round(distance * 0.45)), "duration_min": round(distance / 180 * 60 + 30), "distance_km": distance}


def _duration_text(duration_min: int) -> str:
    hours = duration_min // 60
    minutes = duration_min % 60
    if hours and minutes:
        return f"{hours}小时{minutes}分钟"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分钟"


def _intercity_notice(mode: str, not_recommended: bool) -> str:
    notices = {
        "高铁/火车": "未接入12306实时票价，当前为兜底估算；真实班次和余票需以12306为准。",
        "飞机": "未接入航班实时MCP/API，当前仅提供航班号和起降时间候选用于排期；真实航班、时刻和票价请以航司平台为准。",
        "长途大巴": "未接入客运站实时班次，价格和发车时间需以当地平台为准。",
        "自驾": "费用含油费/高速费估算，不含停车费、限行和拥堵成本。",
        "骑行": "跨城骑行强度和安全风险较高，仅作为用户明确要求时的参考。",
    }
    text = notices.get(mode, "当前为兜底估算。")
    if not_recommended:
        text += " 系统不推荐把它作为默认方案。"
    return text


def _intercity_summary(origin: str, destination: str, selected: dict[str, Any] | None, include_round_trip: bool) -> str:
    if not selected:
        return "未生成城际交通估算。"
    if selected.get("ticket_selection_required"):
        if selected.get("mode") == "飞机" or selected.get("source") == "flight_time_candidates":
            return (
                f"{origin}到{destination}已生成航班号和起降时间候选，请先选择去返程航班；"
                "未选择前，首日行程按08:30开始游玩。实际航班以航司/航旅纵横/携程等平台为准。"
            )
        return (
            f"{origin}到{destination}已通过12306-MCP查到候选车次，请先选择具体车次；"
            "未选择前，首日行程按08:30开始游玩。"
        )
    if selected.get("ticket_query_error") and selected.get("mode") == "高铁/火车":
        return f"{origin}到{destination}高铁/火车未拿到12306候选车次，当前暂按兜底费用与时长估算。"
    scope = "已计入预算" if include_round_trip else "未计入当地预算"
    return (
        f"{origin}到{destination}建议优先参考{selected['mode']}，往返约{selected['estimated_cost']}元，"
        f"单程约{selected['duration_text']}，{scope}。"
    )
