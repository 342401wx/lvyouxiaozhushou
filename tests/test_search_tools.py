from education_qa.search_tools import PRICE_RE


def extract_price(text: str) -> int | None:
    match = PRICE_RE.search(text)
    return int(match.group(1)) if match else None


def test_ticket_price_regex_ignores_years() -> None:
    assert extract_price("大通古镇2026年开放公告，门票请以官方为准") is None
    assert extract_price("大通天主教堂钟楼 2026 铜陵旅游攻略") is None
    assert extract_price("大通古镇门票2026元，具体以官方公告为准") is None


def test_ticket_price_regex_requires_ticket_units() -> None:
    assert extract_price("大通古镇成人票 40元，儿童票半价") == 40
    assert extract_price("景区票价￥80起，预约信息以官方为准") == 80
