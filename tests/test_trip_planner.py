from pathlib import Path

from education_qa.app_config import AppConfig
from education_qa.retriever import TfidfRagStore
from education_qa.tourism import enrich_tourism_record
from education_qa.trip_planner import TourismTripPlanner, _budget_note, _select_stops


class FakeMapClient:
    enabled = False

    def search_poi(self, keywords: str, city: str, *, limit: int = 8):
        return []

    def nearby_hotels(self, location, city: str, *, accommodation: str = "经济型酒店", limit: int = 4):
        return []

    def weather(self, city: str):
        return []


class FakeLLM:
    enabled = False

    def complete(self, messages, *, temperature: float = 0.2) -> str:
        return ""


class HallucinatingFoodLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.2) -> str:
        return "午餐可以吃铜陵白姜和大通茶干。"


class FakeRailwayClient:
    enabled = True

    def query_train_option(self, origin: str, destination: str, travel_date):
        if origin == "铜陵":
            assert destination == "六安"
            return {
                "one_way_cost": 66,
                "duration_min": 70,
                "train_code": "G8898",
                "seat_type": "二等座",
                "depart_time": "18:20",
                "arrive_time": "19:30",
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
                        "round_trip_cost": 132,
                        "available": True,
                        "seats": [],
                    }
                ],
                "selected_train_index": 0,
                "notice": "以12306为准",
            }
        assert origin == "六安"
        assert destination == "铜陵"
        assert travel_date.isoformat() == "2026-06-05"
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
                    "round_trip_cost": 112,
                    "available": True,
                    "seats": [],
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
                    "round_trip_cost": 176,
                    "available": True,
                    "seats": [],
                },
            ],
            "selected_train_index": 0,
            "notice": "以12306为准",
        }


class FakeLateRailwayClient:
    enabled = True

    def query_train_option(self, origin: str, destination: str, travel_date):
        if origin == "铜陵":
            destination = "六安"
        return {
            "one_way_cost": 80,
            "duration_min": 120,
            "train_code": "G999",
            "seat_type": "二等座",
            "depart_time": "16:30",
            "arrive_time": "18:30",
            "source": "12306_mcp",
            "train_tickets": [
                {
                    "train_code": "G999",
                    "seat_type": "二等座",
                    "ticket_status": "有票",
                    "depart_time": "16:30",
                    "arrive_time": "18:30",
                    "duration_min": 120,
                    "duration_text": "2小时",
                    "from_station": origin,
                    "to_station": destination,
                    "one_way_cost": 80,
                    "round_trip_cost": 160,
                    "available": True,
                    "seats": [],
                },
            ],
            "selected_train_index": 0,
            "notice": "以12306为准",
        }


class FakeAmapPoiClient(FakeMapClient):
    enabled = True

    def search_poi(self, keywords: str, city: str, *, limit: int = 8):
        if "烧烤" in keywords or "餐厅" in keywords or "小吃" in keywords or "特色美食" in keywords:
            return [
                {
                    "name": "牧羊村烧烤",
                    "type": "餐饮服务;中餐厅;特色/地方风味餐厅",
                    "address": "北京路与林泽街路口",
                    "location": {"longitude": 118.05, "latitude": 36.81},
                    "source": "amap",
                }
            ]
        return [
            {
                "name": "周村古商城",
                "type": "风景名胜;风景名胜;国家级景点",
                "address": "新建中路19号",
                "location": {"longitude": 117.85, "latitude": 36.8},
                "source": "amap",
            },
            {
                "name": "淄博聊斋城景区",
                "type": "风景名胜;风景名胜;国家级景点",
                "address": "洪山镇蒲家村466号",
                "location": {"longitude": 117.96, "latitude": 36.62},
                "source": "amap",
            },
            {
                "name": "淄博市植物园",
                "type": "风景名胜;公园广场;植物园",
                "address": "世纪路28号",
                "location": {"longitude": 118.03, "latitude": 36.78},
                "source": "amap",
            },
        ][:limit]

    def around_poi(self, location, *, keywords: str, radius: int = 1800, limit: int = 6, types: str = ""):
        return [
            {
                "name": "牧羊村烧烤",
                "type": "餐饮服务;中餐厅;特色/地方风味餐厅",
                "address": "北京路与林泽街路口",
                "location": {"longitude": 118.05, "latitude": 36.81},
                "source": "amap",
            }
        ][:limit]


def test_select_stops_does_not_create_nearby_or_overfill_museums() -> None:
    candidates = [
        {"name": "甲博物馆", "category": "博物馆", "city": "铜陵"},
        {"name": "乙博物馆", "category": "博物馆", "city": "铜陵"},
        {"name": "丙博物馆", "category": "博物馆", "city": "铜陵"},
        {"name": "天井湖公园", "category": "自然观光", "city": "铜陵"},
        {"name": "犁桥水镇", "category": "街区观光", "city": "铜陵"},
    ]

    selected = _select_stops(candidates, days=1)
    names = [item["name"] for item in selected]

    assert not any(name.endswith("周边") for name in names)
    assert sum("博物馆" in name for name in names) == 1
    assert "天井湖公园" in names


def test_select_stops_keeps_explicit_place_before_semantic_fallback() -> None:
    candidates = [
        {"name": "成都动物园", "category": "自然观光", "city": "成都", "required": True, "required_priority": 1},
        {"name": "熊猫基地", "category": "自然观光", "city": "成都", "required": True, "required_priority": 0},
        {"name": "成都博物馆", "category": "博物馆", "city": "成都"},
    ]

    selected = _select_stops(candidates, days=1)
    names = [item["name"] for item in selected]

    assert "熊猫基地" in names
    assert "成都动物园" not in names


def test_trip_planner_returns_card_ready_schema(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "成都",
                "section": "观光",
                "text": "观光：武侯祠；地址：成都市武侯区；说明：适合了解三国历史。观光：锦里古街；说明：适合美食和街区游览。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:2",
                "source_type": "wikivoyage",
                "title": "成都",
                "section": "用餐",
                "text": "成都的著名食物有：夫妻肺片、担担面、钟水饺、麻婆豆腐等。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 1,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    result = planner.plan(
        {
            "city": "成都",
            "days": 1,
            "budget": 800,
            "origin": "重庆",
            "budget_includes_intercity_transport": True,
            "intercity_options": ["高铁/火车"],
            "interests": ["历史", "美食"],
            "transportation": "共享单车优先",
            "mobility_constraints": ["少走路", "不打车"],
            "accommodation": "经济型酒店",
        }
    )

    data = result["data"]
    assert result["success"] is True
    assert data["city"] == "成都"
    assert data["days"][0]["stops"]
    assert data["days"][0]["stops"][0]["nearby_hotels"]
    assert data["days"][0]["stops"][0]["nearby_hotels"][0]["review_profile"]["sections"]
    assert data["days"][0]["stops"][0]["scenic_status"]
    assert data["intercity_transport"]["selected_mode"] == "高铁/火车"
    assert data["budget"]["intercity_included"] is True
    assert data["mobility_policy"]["constraints"] == ["少走路", "不打车"]
    assert data["scenic_status_summary"]["warnings"]
    assert data["weather_info"][0]["source"] == "fallback"
    assert data["budget"]["total"] > 0
    assert data["days"][0]["day_start_time"] == "08:30"
    assert any(item["type"] == "meal" and "早餐" in item["title"] for item in data["days"][0]["timeline"])
    assert any(item["type"] == "meal" and "午餐" in item["title"] for item in data["days"][0]["timeline"])


def test_trip_planner_uses_map_candidates_when_city_rag_has_no_stops(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:zibo",
                "source_type": "wikivoyage",
                "title": "淄博",
                "section": "概览",
                "text": "淄博市位于山东省。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        )
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(amap_api_key="fake-key"),
        map_client=FakeAmapPoiClient(),
        llm_client=FakeLLM(),
    )
    result = planner.plan(
        {
            "city": "淄博",
            "days": 1,
            "budget": 900,
            "interests": ["观光", "美食"],
            "accommodation": "经济型酒店",
        }
    )

    day = result["data"]["days"][0]
    stop_names = [stop["name"] for stop in day["stops"]]
    assert "周村古商城" in stop_names
    assert day["theme"] != "自由活动"
    assert any(item["type"] == "stop" for item in day["timeline"])
    assert any(meal["meal_source"] == "amap" and meal["place"] == "牧羊村烧烤" for meal in day["meals"])


def test_trip_planner_includes_12306_mcp_train_budget(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：大通古镇；说明：临江古镇街区。观光：铜陵博物馆；说明：适合了解铜文化。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    planner.context.railway_client = FakeRailwayClient()

    result = planner.plan(
        {
            "city": "铜陵",
            "days": 1,
            "budget": 1200,
            "origin": "六安",
            "start_date": "2026-06-05",
            "budget_includes_intercity_transport": True,
            "intercity_options": ["高铁/火车"],
            "interests": ["观光"],
            "selected_train_index": 0,
        }
    )

    data = result["data"]
    assert data["intercity_transport"]["selected"]["source"] == "12306_mcp"
    assert data["intercity_transport"]["selected"]["estimated_cost"] == 112
    assert data["budget"]["total_intercity_transportation"] == 112
    assert data["tool_status"]["intercity_transport"] == "12306-mcp"
    assert data["days"][0]["timeline"][0]["type"] == "arrival"
    assert data["days"][0]["timeline"][0]["start_time"] == "10:14"


def test_trip_planner_waits_for_user_train_choice_before_arrival_timeline(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：铜陵动物园；说明：适合看小动物。观光：天井湖公园；说明：适合城市湖景观光。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    planner.context.railway_client = FakeRailwayClient()

    result = planner.plan(
        {
            "city": "铜陵",
            "days": 1,
            "budget": 1200,
            "origin": "六安",
            "start_date": "2026-06-05",
            "budget_includes_intercity_transport": True,
            "intercity_options": ["高铁/火车"],
            "requested_places": ["看小动物"],
            "interests": ["观光"],
        }
    )

    data = result["data"]
    selected = data["intercity_transport"]["selected"]
    assert selected["ticket_selection_required"] is True
    assert selected["train_tickets"]
    assert data["days"][0]["day_start_time"] == "08:30"
    assert data["days"][0]["timeline"][0]["type"] != "arrival"
    assert data["days"][0]["stops"][0]["name"] == "铜陵动物园"


def test_trip_planner_rebuilds_timeline_from_selected_train(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：大通古镇；说明：临江古镇街区。观光：铜陵博物馆；说明：适合了解铜文化。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:2",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "用餐",
                "text": "铜陵的著名食物有：顺安酥糖、铜陵白姜、江鲜面。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 1,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    planner.context.railway_client = FakeRailwayClient()

    result = planner.plan(
        {
            "city": "铜陵",
            "days": 1,
            "budget": 1200,
            "origin": "六安",
            "start_date": "2026-06-05",
            "budget_includes_intercity_transport": True,
            "intercity_options": ["高铁/火车"],
            "interests": ["观光", "美食"],
            "selected_train_index": 0,
            "selected_train_ticket": {
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
                "round_trip_cost": 176,
                "available": True,
            },
        }
    )

    data = result["data"]
    selected = data["intercity_transport"]["selected"]
    assert selected["train_code"] == "G7799"
    assert selected["arrive_time"] == "13:08"
    assert selected["estimated_cost"] == 176
    assert data["days"][0]["timeline"][0]["start_time"] == "13:08"
    assert "到达较晚" in data["days"][0]["meals"][0]["time_note"]
    assert any(item["type"] == "meal" and "晚餐" in item["title"] for item in data["days"][0]["timeline"])


def test_trip_planner_does_not_schedule_zoo_after_business_hours(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：铜陵动物园；说明：适合看小动物。观光：天井湖公园；说明：适合城市湖景观光。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    planner.context.railway_client = FakeLateRailwayClient()

    result = planner.plan(
        {
            "city": "铜陵",
            "origin": "六安",
            "days": 1,
            "budget": 1200,
            "budget_includes_intercity_transport": True,
            "intercity_options": ["高铁/火车"],
            "requested_places": ["铜陵动物园"],
            "interests": ["亲子"],
            "selected_train_index": 0,
        }
    )

    timeline = result["data"]["days"][0]["timeline"]
    assert not any(item["type"] == "stop" and item["title"] == "铜陵动物园" for item in timeline)
    assert not any(item["type"] == "backup" for item in timeline)
    replacement = next(item for item in timeline if item["type"] == "stop" and "小吃街/商圈" in item["title"])
    assert "营业/适游时间" in replacement["description"]
    assert "铜陵动物园" in replacement["description"]
    assert any(stop["scheduled"] is False and stop["name"] == "铜陵动物园" for stop in result["data"]["days"][0]["stops"])
    assert any(stop["scheduled"] is True and "小吃街/商圈" in stop["name"] for stop in result["data"]["days"][0]["stops"])


def test_trip_planner_uses_self_drive_departure_arrival_time(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "成都",
                "section": "观光",
                "text": "观光：武侯祠；说明：适合了解三国历史。观光：锦里古街；说明：适合街区游览。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    result = planner.plan(
        {
            "city": "成都",
            "origin": "重庆",
            "days": 1,
            "intercity_options": ["自驾"],
            "intercity_departure_time": "08:00",
            "interests": ["历史"],
        }
    )

    timeline = result["data"]["days"][0]["timeline"]
    assert timeline[0]["type"] == "arrival"
    assert timeline[0]["start_time"] == "12:10"
    assert "08:00出发" in timeline[0]["description"]


def test_trip_planner_prioritizes_places_from_free_text(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "成都",
                "section": "观光",
                "text": "观光：武侯祠；说明：适合了解三国历史。观光：锦里古街；说明：适合街区游览。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    result = planner.plan(
        {
            "city": "成都",
            "days": 1,
            "budget": 900,
            "interests": ["历史"],
            "free_text": "想去熊猫基地和武侯祠，路线不要太赶。",
        }
    )

    stop_names = [stop["name"] for stop in result["data"]["days"][0]["stops"]]
    assert "熊猫基地" in stop_names
    assert "武侯祠" in stop_names
    assert "想去熊猫基地" not in stop_names


def test_trip_planner_filters_generic_user_prompt_from_stops(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：天井湖公园；说明：适合城市湖景观光。观光：铜陵博物馆；说明：适合了解铜文化。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=FakeLLM(),
    )
    result = planner.plan(
        {
            "city": "铜陵",
            "origin": "六安",
            "days": 1,
            "budget": 2000,
            "interests": ["观光"],
            "requested_places": ["然后最好是景区"],
            "free_text": "然后最好是景区，想看景点和美食，然后通勤方便，不要绕路",
        }
    )

    stop_names = [stop["name"] for stop in result["data"]["days"][0]["stops"]]
    assert "然后最好是景区" not in stop_names
    assert "最好是景区" not in stop_names
    assert "景点和美食" not in stop_names
    assert "天井湖公园" in stop_names
    assert "知识库未找到合适" in result["data"]["days"][0]["meals"][0]["name"]


def test_trip_planner_does_not_let_llm_invent_food_without_knowledge(tmp_path: Path) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:1",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "观光",
                "text": "观光：天井湖公园；说明：适合城市湖景观光。观光：铜官山；说明：城市地标。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        ),
    ]
    index_path = tmp_path / "tourism.pkl"
    TfidfRagStore.build(records).save(index_path)

    planner = TourismTripPlanner(
        store_path=index_path,
        config=AppConfig(),
        map_client=FakeMapClient(),
        llm_client=HallucinatingFoodLLM(),
    )
    result = planner.plan(
        {
            "city": "铜陵",
            "days": 1,
            "interests": ["美食"],
            "free_text": "想吃特色美食",
        }
    )

    suggestions = result["data"]["overall_suggestions"]
    assert "知识库未找到铜陵合适的特色美食" in suggestions
    assert "铜陵白姜" not in suggestions
    assert "大通茶干" not in suggestions


def test_budget_note_does_not_treat_unclear_scope_as_included() -> None:
    note = _budget_note("未说明是否包含往返城际交通", None)

    assert "未完全明确" in note
    assert "不计入" in note
