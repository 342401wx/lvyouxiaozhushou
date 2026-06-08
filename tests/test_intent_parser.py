from datetime import date

from education_qa.app_config import AppConfig
from education_qa.intent_parser import parse_travel_intent
from education_qa.retriever import TfidfRagStore
from education_qa.tourism import enrich_tourism_record


class FakeLLM:
    enabled = False

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return ""


class AIPrimaryLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","budget":1200,"requested_places":[],"interests":["观光"]}'


class AIHighSpeedAliasLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","origin":"六安","days":5,"budget":3000,"intercity_transportation":"未确定","intercity_options":["高铁"],"requested_places":["铜陵动物园"]}'


class AIMissingIntercityLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","origin":"六安","days":5,"budget":3000,"intercity_transportation":"未确定","intercity_options":[],"requested_places":["铜陵动物园"]}'


class AIEmptyPlacesLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","origin":"六安","days":1,"budget":0,"intercity_transportation":"高铁/火车","intercity_options":["高铁/火车"],"requested_places":[],"interests":["美食"]}'


class AIZooOnlyLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","origin":"六安","days":1,"budget":0,"intercity_transportation":"高铁/火车","intercity_options":["高铁/火车"],"requested_places":["铜陵动物园"],"interests":["亲子"]}'


class AIWrongReturnDateLLM:
    enabled = True

    def complete(self, messages, *, temperature: float = 0.0) -> str:
        return '{"city":"铜陵","origin":"六安","days":3,"start_date":"2026-06-08","return_date":"2026-06-10","return_date_policy":"last_day","intercity_transportation":"高铁/火车","intercity_options":["高铁/火车"]}'


def test_parse_travel_intent_marks_budget_scope_uncertain() -> None:
    intent = parse_travel_intent(
        "我从重庆出发，想去成都玩2天，预算1200，不确定包不包括高铁，想看历史和美食，住民宿。",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["city"] == "成都"
    assert intent["origin"] == "重庆"
    assert intent["days"] == 2
    assert intent["budget"] == 1200
    assert intent["budget_includes_long_distance"] is None
    assert intent["budget_includes_intercity_transport"] is None
    assert "预算是否包含往返城际交通" in intent["needs_confirmation"]
    assert intent["intercity_transportation"] == "高铁/火车"
    assert "历史" in intent["interests"]
    assert "美食" in intent["interests"]
    assert intent["accommodation"] == "民宿"
    assert intent["plan_payload"]["budget_scope"] == "提到了城际交通，但是否计入预算仍需确认"


def test_parse_travel_intent_detects_local_budget_scope() -> None:
    intent = parse_travel_intent(
        "成都两天，预算1000不包括高铁，公共交通优先，想去武侯祠和锦里古街。",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["budget_includes_long_distance"] is False
    assert intent["budget_includes_intercity_transport"] is False
    assert intent["budget_scope"] == "仅目的地内消费，不含往返城际交通"
    assert "武侯祠" in intent["requested_places"]
    assert "锦里古街" in intent["requested_places"]


def test_parse_travel_intent_detects_multiple_intercity_and_local_constraints() -> None:
    intent = parse_travel_intent(
        "从重庆去成都，可以高铁也可以大巴，到了之后尽量共享单车，但不要走太远，也不想打车。",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["intercity_options"] == ["高铁/火车", "长途大巴"]
    assert intent["intercity_transportation"] == "高铁/火车 / 长途大巴"
    assert intent["local_transportation"] == "共享单车优先"
    assert "少走路" in intent["mobility_constraints"]
    assert "不打车" in intent["mobility_constraints"]


def test_parse_travel_intent_extracts_destination_after_go_phrase() -> None:
    intent = parse_travel_intent(
        "我准备从六安出发，去铜陵，想玩三天，帮我看看有哪些景区或者可以玩的地方",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["origin"] == "六安"
    assert intent["city"] == "铜陵"
    assert intent["days"] == 3
    assert "观光" in intent["interests"]
    assert "帮我看看有哪些景区" not in intent["requested_places"]


def test_parse_travel_intent_does_not_include_duration_in_destination() -> None:
    intent = parse_travel_intent(
        "我准备从六安出发，准备去铜陵玩三天，有哪些好玩的地方吗",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["origin"] == "六安"
    assert intent["city"] == "铜陵"
    assert intent["days"] == 3


def test_parse_travel_intent_cleans_requested_place_with_city_prefix() -> None:
    intent = parse_travel_intent(
        "我准备从六安去铜陵玩两天，然后预算是两千多，我想去铜陵动物园，请帮我规划一下",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["origin"] == "六安"
    assert intent["city"] == "铜陵"
    assert intent["days"] == 2
    assert intent["budget"] == 2000
    assert intent["requested_places"] == ["铜陵动物园"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵动物园"]


def test_parse_travel_intent_removes_visit_action_from_requested_place() -> None:
    intent = parse_travel_intent(
        "我准备明天从六安到铜陵玩，想去铜陵动物园玩，然后预算的话是两千，玩三天",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["origin"] == "六安"
    assert intent["city"] == "铜陵"
    assert intent["days"] == 3
    assert intent["budget"] == 2000
    assert intent["requested_places"] == ["铜陵动物园"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵动物园"]


def test_parse_travel_intent_maps_small_animals_to_zoo() -> None:
    intent = parse_travel_intent(
        "我明天从六安去铜陵玩一天，准备坐高铁去，必须去看小动物，其他景点你安排，想吃特色美食。",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["city"] == "铜陵"
    assert intent["intercity_transportation"] == "高铁/火车"
    assert intent["requested_places"] == ["铜陵动物园"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵动物园"]


def test_parse_travel_intent_keeps_rule_place_when_ai_returns_empty_places() -> None:
    intent = parse_travel_intent(
        "我明天从六安去铜陵玩一天，准备坐高铁去，必须去看小动物，其他景点你安排，想吃特色美食。",
        config=AppConfig(),
        llm_client=AIEmptyPlacesLLM(),
    )

    assert intent["confidence"] == "llm"
    assert intent["requested_places"] == ["铜陵动物园"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵动物园"]


def test_parse_travel_intent_uses_rag_for_activity_place(monkeypatch) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:water",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "活动",
                "text": "活动：铜陵水世界；说明：适合夏天玩水和亲子活动。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        )
    ]
    store = TfidfRagStore.build(records)
    monkeypatch.setattr("education_qa.intent_parser._tourism_store", lambda: store)

    intent = parse_travel_intent(
        "我明天从六安去铜陵玩一天，想玩水，准备坐高铁去。",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["requested_places"] == ["铜陵水世界"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵水世界"]


def test_parse_travel_intent_merges_ai_places_with_rag_places(monkeypatch) -> None:
    records = [
        enrich_tourism_record(
            {
                "id": "wikivoyage:test:water",
                "source_type": "wikivoyage",
                "title": "铜陵",
                "section": "活动",
                "text": "活动：铜陵水世界；说明：适合夏天玩水和亲子活动。",
                "source": "memory",
                "page_id": "test",
                "chunk_index": 0,
            }
        )
    ]
    store = TfidfRagStore.build(records)
    monkeypatch.setattr("education_qa.intent_parser._tourism_store", lambda: store)

    intent = parse_travel_intent(
        "我明天从六安去铜陵玩一天，想玩水，也想看小动物，准备坐高铁去。",
        config=AppConfig(),
        llm_client=AIZooOnlyLLM(),
    )

    assert intent["requested_places"] == ["铜陵动物园", "铜陵水世界"]
    assert intent["plan_payload"]["requested_places"] == ["铜陵动物园", "铜陵水世界"]


def test_parse_travel_intent_resolves_tomorrow_for_ticket_date(monkeypatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 5)

    monkeypatch.setattr("education_qa.intent_parser.date", FixedDate)

    intent = parse_travel_intent(
        "我准备明天从六安到铜陵玩，准备坐高铁去",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["start_date"] == "2026-06-06"
    assert intent["plan_payload"]["start_date"] == "2026-06-06"
    assert intent["return_date"] == "2026-06-07"
    assert intent["plan_payload"]["return_date"] == "2026-06-07"


def test_parse_travel_intent_sets_default_return_date_to_last_day(monkeypatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 7)

    monkeypatch.setattr("education_qa.intent_parser.date", FixedDate)

    intent = parse_travel_intent(
        "我明天从六安去铜陵玩三天，准备坐高铁去",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["start_date"] == "2026-06-08"
    assert intent["return_date"] == "2026-06-10"
    assert intent["return_date_policy"] == "last_day"
    assert intent["plan_payload"]["return_date"] == "2026-06-10"


def test_parse_travel_intent_sets_return_date_next_day_when_play_done_then_leave(monkeypatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 7)

    monkeypatch.setattr("education_qa.intent_parser.date", FixedDate)

    intent = parse_travel_intent(
        "我明天从六安去铜陵玩三天，准备坐高铁去，最后一天玩好了后走",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["start_date"] == "2026-06-08"
    assert intent["return_date"] == "2026-06-11"
    assert intent["return_date_policy"] == "next_day_after_last_day"
    assert intent["plan_payload"]["return_date"] == "2026-06-11"


def test_parse_travel_intent_rule_overrides_ai_wrong_return_date_policy(monkeypatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 7)

    monkeypatch.setattr("education_qa.intent_parser.date", FixedDate)

    intent = parse_travel_intent(
        "我明天从六安去铜陵玩三天，准备坐高铁去，最后一天玩好了后走",
        config=AppConfig(),
        llm_client=AIWrongReturnDateLLM(),
    )

    assert intent["return_date"] == "2026-06-11"
    assert intent["return_date_policy"] == "next_day_after_last_day"
    assert intent["plan_payload"]["return_date"] == "2026-06-11"


def test_parse_travel_intent_handles_chinese_budget_and_generic_scenic_preference() -> None:
    intent = parse_travel_intent(
        "我准备明天从六安出发，准备去铜陵玩三天，我想要住在一个酒店，这样我会省很多事，然后最好是景区，然后通勤方便，不要绕路，预算两千块钱",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["origin"] == "六安"
    assert intent["city"] == "铜陵"
    assert intent["days"] == 3
    assert intent["budget"] == 2000
    assert intent["budget_is_explicit"] is True
    assert "观光" in intent["interests"]
    assert intent["requested_places"] == []
    assert intent["plan_payload"]["budget"] == 2000
    assert intent["plan_payload"]["requested_places"] == []


def test_parse_travel_intent_does_not_default_city_when_missing() -> None:
    intent = parse_travel_intent(
        "预算两千，想看历史和美食",
        config=AppConfig(),
        llm_client=FakeLLM(),
    )

    assert intent["city"] == ""
    assert intent["budget"] == 2000


def test_parse_travel_intent_prefers_ai_when_available() -> None:
    intent = parse_travel_intent(
        "从六安出发去铜陵玩三天，预算两千块钱，然后最好是景区",
        config=AppConfig(),
        llm_client=AIPrimaryLLM(),
    )

    assert intent["budget"] == 1200
    assert intent["confidence"] == "llm"
    assert intent["requested_places"] == []
    assert intent["tool_status"]["deepseek"] is True
    assert intent["tool_status"]["fallback_parser"] is False
    assert intent["tool_status"]["intent_source"] == "deepseek"


def test_parse_travel_intent_normalizes_ai_intercity_alias() -> None:
    intent = parse_travel_intent(
        "我准备明天从六安去铜陵玩五天，预算三千，想去铜陵动物园，准备坐高铁去",
        config=AppConfig(),
        llm_client=AIHighSpeedAliasLLM(),
    )

    assert intent["intercity_options"] == ["高铁/火车"]
    assert intent["intercity_transportation"] == "高铁/火车"
    assert intent["tool_status"]["intent_source"] == "deepseek"


def test_parse_travel_intent_fills_intercity_when_ai_misses_explicit_train() -> None:
    intent = parse_travel_intent(
        "我准备明天从六安去铜陵玩五天，预算三千，想去铜陵动物园，准备坐高铁去",
        config=AppConfig(),
        llm_client=AIMissingIntercityLLM(),
    )

    assert intent["intercity_options"] == ["高铁/火车"]
    assert intent["intercity_transportation"] == "高铁/火车"
    assert intent["tool_status"]["intent_source"] == "deepseek"
