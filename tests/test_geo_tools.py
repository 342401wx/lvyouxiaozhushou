from education_qa.geo_tools import estimate_route, fallback_hotels, haversine_km


def test_haversine_and_route_estimate() -> None:
    start = {"name": "A", "location": {"longitude": 104.0, "latitude": 30.0}}
    end = {"name": "B", "location": {"longitude": 104.01, "latitude": 30.01}}

    assert haversine_km(start["location"], end["location"]) > 0
    route = estimate_route(start, end, preference="公共交通优先")

    assert route["from"] == "A"
    assert route["to"] == "B"
    assert route["duration_min"] > 0
    assert route["is_estimated"] is True


def test_fallback_hotels_have_display_fields() -> None:
    hotels = fallback_hotels("武侯祠", "成都", accommodation="经济型酒店")

    assert len(hotels) == 3
    assert hotels[0]["name"].startswith("武侯祠")
    assert hotels[0]["estimated_cost"] > 0
