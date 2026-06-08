from education_qa.scenic_status import scenic_status_for_stop


class FakeSearchClient:
    enabled = True

    def search_scenic_status(self, scenic_name: str, city: str):
        return {
            "ticket_price": 66,
            "open_status": "可能需预约",
            "announcement": "搜索摘要显示需要预约入园。",
            "source_title": "景区官方购票页",
            "source_url": "https://example.com/ticket",
        }


def test_scenic_status_prefers_knowledge_base_ticket_price() -> None:
    status = scenic_status_for_stop(
        {"name": "武侯祠", "category": "历史文化", "ticket_price": 60},
        "成都",
    )

    assert status["ticket_price"] == 60
    assert status["ticket_source"] == "knowledge_base"
    assert "官网" in status["official_check_note"]


def test_scenic_status_uses_web_search_when_available() -> None:
    status = scenic_status_for_stop(
        {"name": "武侯祠", "category": "历史文化", "ticket_price": 60},
        "成都",
        search_client=FakeSearchClient(),
    )

    assert status["ticket_price"] == 66
    assert status["ticket_source"] == "web_search"
    assert status["source"] == "web_search"
    assert status["web_source_title"] == "景区官方购票页"


def test_scenic_status_uses_reference_price_for_unknown_paid_type() -> None:
    status = scenic_status_for_stop(
        {"name": "铜陵动物园", "category": "自然观光", "ticket_price": 0},
        "铜陵",
    )

    assert status["ticket_price"] == 45
    assert status["budget_ticket_price"] == 45
    assert status["ticket_source"] == "reference_estimate"
    assert status["ticket_price_is_estimated"] is True


def test_scenic_status_keeps_known_free_place_as_zero() -> None:
    status = scenic_status_for_stop(
        {"name": "天井湖公园", "category": "自然观光", "ticket_price": 0},
        "铜陵",
    )

    assert status["ticket_price"] == 0
    assert status["ticket_source"] == "fallback_known"
    assert status["ticket_price_is_estimated"] is False
