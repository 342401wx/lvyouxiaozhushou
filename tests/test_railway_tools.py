import json as json_module
from datetime import date

from education_qa.app_config import AppConfig
from education_qa.railway_tools import Railway12306Client


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


def test_railway_12306_client_selects_available_second_class(monkeypatch) -> None:
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        tickets = [
            {
                "start_train_code": "G1",
                "start_time": "08:00",
                "arrive_time": "09:05",
                "lishi": "01:05",
                "from_station": "六安",
                "to_station": "铜陵",
                "prices": [
                    {"seat_name": "二等座", "num": "无", "price": 50},
                    {"seat_name": "一等座", "num": "有", "price": 40},
                ],
            },
            {
                "start_train_code": "G2",
                "start_time": "10:00",
                "arrive_time": "11:04",
                "lishi": "01:04",
                "from_station": "六安",
                "to_station": "铜陵",
                "prices": [{"seat_name": "二等座", "num": "有", "price": 56}],
            },
        ]
        return FakeResponse(
            {
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json_module.dumps(tickets, ensure_ascii=False),
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("education_qa.railway_tools.requests.post", fake_post)
    client = Railway12306Client(
        AppConfig(
            railway_provider="12306_mcp",
            railway_mcp_url="http://127.0.0.1:8765",
        )
    )

    result = client.query_train_option("六安", "铜陵", date(2026, 6, 5))

    assert result is not None
    assert result["one_way_cost"] == 56
    assert result["duration_min"] == 64
    assert result["train_code"] == "G2"
    assert result["seat_type"] == "二等座"
    assert result["source"] == "12306_mcp"
    assert len(result["train_tickets"]) == 2
    assert result["selected_train_index"] == 1
    assert result["train_tickets"][0]["available"] is True
    assert result["train_tickets"][0]["seat_type"] == "一等座"
    assert result["train_tickets"][1]["round_trip_cost"] == 112
    assert calls[0]["url"] == "http://127.0.0.1:8765/mcp"
    assert calls[0]["json"]["params"]["name"] == "get-tickets"
    assert calls[0]["json"]["params"]["arguments"]["trainFilterFlags"] == "GD"


def test_railway_12306_client_returns_none_when_disabled(monkeypatch) -> None:
    def fail_post(*args, **kwargs):
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr("education_qa.railway_tools.requests.post", fail_post)
    client = Railway12306Client(AppConfig())

    assert client.query_train_option("六安", "铜陵", date(2026, 6, 5)) is None


def test_railway_12306_client_keeps_sold_out_ticket_list(monkeypatch) -> None:
    def fake_post(url, *, headers, json, timeout):
        tickets = [
            {
                "start_train_code": "G9",
                "start_time": "12:00",
                "arrive_time": "13:10",
                "lishi": "01:10",
                "from_station": "六安",
                "to_station": "铜陵",
                "prices": [{"seat_name": "二等座", "num": "无", "price": 56}],
            }
        ]
        return FakeResponse(
            {
                "result": {
                    "content": [{"type": "text", "text": json_module.dumps(tickets, ensure_ascii=False)}]
                }
            }
        )

    monkeypatch.setattr("education_qa.railway_tools.requests.post", fake_post)
    client = Railway12306Client(AppConfig(railway_provider="12306_mcp", railway_mcp_url="http://127.0.0.1:8765"))

    result = client.query_train_option("六安", "铜陵", date(2026, 6, 5))

    assert result is not None
    assert "one_way_cost" not in result
    assert result["train_tickets"][0]["available"] is False
    assert result["train_tickets"][0]["ticket_status"] == "无票"


def test_railway_12306_client_falls_back_to_stdio_when_http_fails(monkeypatch) -> None:
    def broken_post(*args, **kwargs):
        raise RuntimeError("Already connected to a transport")

    def fake_stdio(self, name, arguments):
        assert name == "get-tickets"
        assert arguments["fromStation"] == "六安"
        tickets = [
            {
                "start_train_code": "G88",
                "start_time": "09:00",
                "arrive_time": "10:20",
                "lishi": "01:20",
                "from_station": "六安",
                "to_station": "铜陵",
                "prices": [{"seat_name": "二等座", "num": "有", "price": 72}],
            }
        ]
        return {
            "_transport": "stdio",
            "content": [{"type": "text", "text": json_module.dumps(tickets, ensure_ascii=False)}],
        }

    monkeypatch.setattr("education_qa.railway_tools.requests.post", broken_post)
    monkeypatch.setattr(Railway12306Client, "_call_stdio_tool", fake_stdio)
    client = Railway12306Client(AppConfig(railway_provider="12306_mcp", railway_mcp_url="http://127.0.0.1:8765"))

    result = client.query_train_option("六安", "铜陵", date(2026, 6, 5))

    assert result is not None
    assert result["one_way_cost"] == 72
    assert result["train_code"] == "G88"
    assert result["ticket_query_transport"] == "stdio"
