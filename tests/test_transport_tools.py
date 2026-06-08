from datetime import date

from education_qa.transport_tools import build_mobility_policy, estimate_intercity_transport, estimate_local_route


def test_estimate_intercity_transport_returns_multiple_modes() -> None:
    result = estimate_intercity_transport(
        "重庆",
        "成都",
        modes=["高铁/火车", "长途大巴"],
        included_in_budget=True,
    )

    assert result["selected_mode"] == "高铁/火车"
    assert result["included_in_budget"] is True
    assert len(result["options"]) == 2
    assert result["options"][0]["estimated_cost"] > 0


def test_estimate_intercity_transport_does_not_default_to_train_without_mode() -> None:
    result = estimate_intercity_transport("六安", "铜陵", modes=[])

    assert result["selected_mode"] == "未确定"
    assert result["options"] == []
    assert "未确认" in result["summary"]


def test_estimate_intercity_transport_uses_railway_lookup_for_train() -> None:
    def fake_lookup(origin: str, destination: str, travel_date: date):
        assert origin == "六安"
        assert destination == "铜陵"
        assert travel_date == date(2026, 6, 5)
        return {
            "one_way_cost": 56,
            "duration_min": 64,
            "train_code": "G7721",
            "seat_type": "二等座",
            "depart_time": "09:10",
            "arrive_time": "10:14",
            "source": "12306_mcp",
            "notice": "以12306为准",
            "train_tickets": [
                {
                    "train_code": "G7721",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "09:10",
                    "arrive_time": "10:14",
                    "duration_min": 64,
                    "duration_text": "1小时4分钟",
                    "from_station": "六安",
                    "to_station": "铜陵",
                    "one_way_cost": 56,
                    "available": True,
                }
            ],
        }

    result = estimate_intercity_transport(
        "六安",
        "铜陵",
        modes=["高铁/火车"],
        included_in_budget=True,
        travel_date=date(2026, 6, 5),
        railway_lookup=fake_lookup,
    )

    selected = result["selected"]
    assert selected["source"] == "12306_mcp"
    assert selected["ticket_selection_required"] is True
    assert selected["estimated_cost"] > 0
    assert "train_code" not in selected
    assert selected["train_tickets"][0]["train_code"] == "G7721"
    assert result["source"] == "12306_mcp"


def test_estimate_intercity_transport_respects_selected_train_index() -> None:
    def fake_lookup(origin: str, destination: str, travel_date: date):
        return {
            "one_way_cost": 56,
            "duration_min": 64,
            "train_code": "G7721",
            "seat_type": "二等座",
            "depart_time": "09:10",
            "arrive_time": "10:14",
            "source": "12306_mcp",
            "train_tickets": [
                {
                    "train_code": "G7721",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "09:10",
                    "arrive_time": "10:14",
                    "duration_min": 64,
                    "duration_text": "1小时4分钟",
                    "from_station": "六安",
                    "to_station": "铜陵",
                    "one_way_cost": 56,
                    "available": True,
                },
                {
                    "train_code": "G7799",
                    "seat_type": "一等座",
                    "ticket_status": "有票",
                    "depart_time": "12:01",
                    "arrive_time": "13:08",
                    "duration_min": 67,
                    "duration_text": "1小时7分钟",
                    "from_station": "六安",
                    "to_station": "铜陵",
                    "one_way_cost": 88,
                    "available": True,
                },
            ],
            "selected_train_index": 0,
        }

    result = estimate_intercity_transport(
        "六安",
        "铜陵",
        modes=["高铁/火车"],
        included_in_budget=True,
        travel_date=date(2026, 6, 5),
        railway_lookup=fake_lookup,
        selected_train_index=1,
    )

    selected = result["selected"]
    assert selected["train_code"] == "G7799"
    assert selected["arrive_time"] == "13:08"
    assert selected["estimated_cost"] == 176
    assert selected["selected_train_index"] == 1


def test_estimate_intercity_transport_queries_return_train_date_and_cost() -> None:
    calls = []

    def fake_lookup(origin: str, destination: str, travel_date: date):
        calls.append((origin, destination, travel_date))
        if origin == "六安":
            return {
                "one_way_cost": 56,
                "duration_min": 64,
                "source": "12306_mcp",
                "train_tickets": [
                    {
                        "train_code": "G7721",
                        "seat_type": "二等座",
                        "ticket_status": "有票",
                        "depart_time": "09:10",
                        "arrive_time": "10:14",
                        "duration_min": 64,
                        "duration_text": "1小时4分钟",
                        "from_station": "六安",
                        "to_station": "铜陵",
                        "one_way_cost": 56,
                        "available": True,
                    }
                ],
            }
        return {
            "one_way_cost": 66,
            "duration_min": 70,
            "source": "12306_mcp",
            "train_tickets": [
                {
                    "train_code": "G8898",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "18:20",
                    "arrive_time": "19:30",
                    "duration_min": 70,
                    "duration_text": "1小时10分钟",
                    "from_station": "铜陵",
                    "to_station": "六安",
                    "one_way_cost": 66,
                    "available": True,
                }
            ],
        }

    result = estimate_intercity_transport(
        "六安",
        "铜陵",
        modes=["高铁/火车"],
        travel_date=date(2026, 6, 8),
        return_date=date(2026, 6, 10),
        railway_lookup=fake_lookup,
        selected_train_index=0,
        selected_return_train_index=0,
    )

    selected = result["selected"]
    assert calls == [("六安", "铜陵", date(2026, 6, 8)), ("铜陵", "六安", date(2026, 6, 10))]
    assert selected["train_code"] == "G7721"
    assert selected["return_train_code"] == "G8898"
    assert selected["return_query_date"] == "2026-06-10"
    assert selected["return_one_way_cost"] == 66
    assert selected["estimated_cost"] == 122


def test_estimate_intercity_transport_locks_selected_train_ticket_when_candidates_refresh() -> None:
    selected_ticket = {
        "train_code": "G7762/G3368",
        "seat_type": "二等座",
        "ticket_status": "有票",
        "depart_time": "08:48",
        "arrive_time": "16:46",
        "duration_min": 478,
        "duration_text": "7小时58分钟",
        "from_station": "合肥南",
        "to_station": "合肥西",
        "one_way_cost": 246,
        "round_trip_cost": 492,
        "transfer_note": "合肥换乘，等待以12306为准",
        "available": True,
    }

    def fake_lookup(origin: str, destination: str, travel_date: date):
        return {
            "one_way_cost": 188,
            "duration_min": 348,
            "source": "12306_mcp",
            "train_tickets": [
                {
                    "train_code": "D2198/G3006",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "08:24",
                    "arrive_time": "14:12",
                    "duration_min": 348,
                    "duration_text": "5小时48分钟",
                    "from_station": "六安",
                    "to_station": "淄博",
                    "one_way_cost": 188,
                    "available": True,
                },
                {
                    "train_code": "G2556/G1068",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "09:06",
                    "arrive_time": "15:01",
                    "duration_min": 355,
                    "duration_text": "5小时55分钟",
                    "from_station": "六安",
                    "to_station": "淄博",
                    "one_way_cost": 205,
                    "available": True,
                },
            ],
        }

    result = estimate_intercity_transport(
        "六安",
        "淄博",
        modes=["高铁/火车"],
        included_in_budget=True,
        travel_date=date(2026, 6, 5),
        railway_lookup=fake_lookup,
        selected_train_index=1,
        selected_train_ticket=selected_ticket,
    )

    selected = result["selected"]
    assert selected["train_code"] == "G7762/G3368"
    assert selected["depart_time"] == "08:48"
    assert selected["arrive_time"] == "16:46"
    assert selected["estimated_cost"] == 492
    assert selected["selected_train_index"] == 0
    assert selected["train_tickets"][0]["train_code"] == "G7762/G3368"


def test_estimate_intercity_transport_keeps_selected_train_ticket_when_final_lookup_has_no_candidates() -> None:
    selected_ticket = {
        "train_code": "G7762/G3368",
        "seat_type": "二等座",
        "ticket_status": "有票",
        "depart_time": "08:48",
        "arrive_time": "16:46",
        "duration_min": 478,
        "duration_text": "7小时58分钟",
        "from_station": "合肥南",
        "to_station": "合肥西",
        "one_way_cost": 246,
        "available": True,
    }

    def empty_lookup(origin: str, destination: str, travel_date: date):
        return {
            "ticket_query_source": "12306_mcp",
            "ticket_query_error": "最终查询暂未返回候选车次",
        }

    result = estimate_intercity_transport(
        "六安",
        "淄博",
        modes=["高铁/火车"],
        travel_date=date(2026, 6, 5),
        railway_lookup=empty_lookup,
        selected_train_index=1,
        selected_train_ticket=selected_ticket,
    )

    selected = result["selected"]
    assert selected["train_code"] == "G7762/G3368"
    assert selected["arrive_time"] == "16:46"
    assert selected["selected_train_index"] == 0
    assert selected["ticket_selection_required"] is False


def test_estimate_intercity_transport_uses_self_drive_departure_time() -> None:
    result = estimate_intercity_transport(
        "重庆",
        "成都",
        modes=["自驾"],
        departure_time="08:00",
    )

    selected = result["selected"]
    assert selected["mode"] == "自驾"
    assert selected["depart_time"] == "08:00"
    assert selected["arrive_time"] == "12:10"
    assert selected["arrival_day_offset"] == 0


def test_estimate_intercity_transport_falls_back_when_railway_lookup_fails() -> None:
    def broken_lookup(origin: str, destination: str, travel_date: date):
        raise RuntimeError("mcp unavailable")

    result = estimate_intercity_transport(
        "六安",
        "铜陵",
        modes=["高铁/火车"],
        travel_date=date(2026, 6, 5),
        railway_lookup=broken_lookup,
    )

    assert result["selected"]["source"] == "12306_mcp"
    assert result["selected"]["ticket_query_source"] == "12306_mcp"
    assert result["selected"]["ticket_query_error"]
    assert result["selected"]["estimated_cost"] > 0


def test_estimate_local_route_avoids_long_walk_and_taxi_when_constrained() -> None:
    policy = build_mobility_policy("成都", "步行优先", ["少走路", "不打车"])
    route = estimate_local_route(
        {"name": "A", "location": {"longitude": 104.0, "latitude": 30.6}},
        {"name": "B", "location": {"longitude": 104.09, "latitude": 30.6}},
        preference="步行优先",
        mobility_policy=policy,
        budget_level="tight",
    )

    assert route["mode"] == "地铁/公交"
    assert route["warnings"]
