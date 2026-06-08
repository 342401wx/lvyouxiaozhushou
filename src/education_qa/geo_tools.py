from __future__ import annotations

import math
from typing import Any

import requests

from .app_config import AppConfig, get_config


CITY_CENTERS: dict[str, dict[str, float]] = {
    "成都": {"longitude": 104.0668, "latitude": 30.5728},
    "杭州": {"longitude": 120.1551, "latitude": 30.2741},
    "北京": {"longitude": 116.4074, "latitude": 39.9042},
    "上海": {"longitude": 121.4737, "latitude": 31.2304},
    "西安": {"longitude": 108.9398, "latitude": 34.3416},
    "广州": {"longitude": 113.2644, "latitude": 23.1291},
    "重庆": {"longitude": 106.5516, "latitude": 29.5630},
    "南京": {"longitude": 118.7969, "latitude": 32.0603},
    "苏州": {"longitude": 120.5853, "latitude": 31.2989},
    "厦门": {"longitude": 118.0894, "latitude": 24.4798},
    "六安": {"longitude": 116.5197, "latitude": 31.7359},
    "铜陵": {"longitude": 117.8121, "latitude": 30.9454},
}

HOTEL_INCLUDE_KEYWORDS = ("酒店", "宾馆", "旅馆", "旅社", "客栈", "民宿", "住宿", "招待所", "青年旅舍")
HOTEL_APARTMENT_INCLUDE_KEYWORDS = ("酒店式公寓", "公寓酒店", "民宿公寓")
HOTEL_EXCLUDE_KEYWORDS = (
    "考研",
    "培训",
    "学习",
    "自习",
    "学校",
    "教育",
    "学院",
    "大学",
    "中学",
    "小学",
    "幼儿园",
    "辅导",
    "托管",
    "机构",
    "宿舍",
    "学生公寓",
    "人才公寓",
    "教师公寓",
    "员工公寓",
)
HOTEL_TYPE_INCLUDE_KEYWORDS = ("住宿服务", "宾馆酒店", "旅馆招待所")
HOTEL_TYPE_EXCLUDE_KEYWORDS = ("科教文化服务", "培训机构", "学校", "科研机构")


def city_center(city: str) -> dict[str, float]:
    return dict(CITY_CENTERS.get(city, {"longitude": 116.3971, "latitude": 39.9165}))


def fallback_location(city: str, index: int) -> dict[str, float]:
    center = city_center(city)
    angle = (index * 137.5) * math.pi / 180
    radius = 0.018 + (index % 4) * 0.006
    return {
        "longitude": round(center["longitude"] + math.cos(angle) * radius, 6),
        "latitude": round(center["latitude"] + math.sin(angle) * radius, 6),
    }


def haversine_km(start: dict[str, float], end: dict[str, float]) -> float:
    lon1, lat1 = math.radians(float(start["longitude"])), math.radians(float(start["latitude"]))
    lon2, lat2 = math.radians(float(end["longitude"])), math.radians(float(end["latitude"]))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def estimate_route(
    start: dict[str, Any],
    end: dict[str, Any],
    *,
    preference: str = "公共交通优先",
) -> dict[str, Any]:
    start_loc = start["location"]
    end_loc = end["location"]
    distance_km = haversine_km(start_loc, end_loc)
    pref = preference or ""

    if "步行" in pref and distance_km <= 2.5:
        mode = "步行"
        duration = max(8, round(distance_km / 4.2 * 60))
        cost = 0
    elif "打车" in pref or "自驾" in pref or distance_km > 8:
        mode = "打车/网约车" if "自驾" not in pref else "自驾"
        duration = max(12, round(distance_km / 24 * 60 + 8))
        cost = max(12, round(10 + distance_km * 2.4))
    elif distance_km <= 1.2:
        mode = "步行"
        duration = max(8, round(distance_km / 4.2 * 60))
        cost = 0
    else:
        mode = "地铁/公交"
        duration = max(18, round(distance_km / 18 * 60 + 10))
        cost = max(2, min(8, round(2 + distance_km * 0.6)))

    return {
        "from": start["name"],
        "to": end["name"],
        "mode": mode,
        "distance_km": round(distance_km, 2),
        "duration_min": int(duration),
        "estimated_cost": int(cost),
        "description": f"{start['name']} → {end['name']}，建议{mode}，约{distance_km:.1f}公里，{duration}分钟。",
        "is_estimated": True,
    }


class AmapClient:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()

    @property
    def enabled(self) -> bool:
        return self.config.has_amap_web_service

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {}
        full_params = {
            "key": self.config.amap_api_key,
            "output": "JSON",
            **params,
        }
        url = f"https://restapi.amap.com{path}"
        try:
            response = requests.get(url, params=full_params, timeout=self.config.request_timeout)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return {}
        if str(data.get("status")) != "1":
            return {}
        return data

    @staticmethod
    def _parse_location(value: str) -> dict[str, float] | None:
        if not value or "," not in value:
            return None
        lon, lat = value.split(",", maxsplit=1)
        try:
            return {"longitude": float(lon), "latitude": float(lat)}
        except ValueError:
            return None

    def search_poi(self, keywords: str, city: str, *, limit: int = 8) -> list[dict[str, Any]]:
        data = self._get(
            "/v3/place/text",
            {
                "keywords": keywords,
                "city": city,
                "citylimit": "true",
                "offset": limit,
                "extensions": "all",
            },
        )
        return [poi for poi in (self._normalize_poi(item) for item in data.get("pois", [])) if poi]

    def around_poi(
        self,
        location: dict[str, float],
        *,
        keywords: str,
        radius: int = 1800,
        limit: int = 6,
        types: str = "",
    ) -> list[dict[str, Any]]:
        data = self._get(
            "/v3/place/around",
            {
                "location": f"{location['longitude']},{location['latitude']}",
                "keywords": keywords,
                "types": types,
                "radius": radius,
                "offset": limit,
                "extensions": "all",
            },
        )
        return [poi for poi in (self._normalize_poi(item) for item in data.get("pois", [])) if poi]

    def weather(self, city: str) -> list[dict[str, Any]]:
        data = self._get(
            "/v3/weather/weatherInfo",
            {
                "city": city,
                "extensions": "all",
            },
        )
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return []
        return [
            {
                "date": item.get("date", ""),
                "day_weather": item.get("dayweather", ""),
                "night_weather": item.get("nightweather", ""),
                "day_temp": _safe_int(item.get("daytemp")),
                "night_temp": _safe_int(item.get("nighttemp")),
                "wind_direction": item.get("daywind", ""),
                "wind_power": item.get("daypower", ""),
                "source": "amap",
            }
            for item in forecasts[0].get("casts", [])
        ]

    def geocode_best(self, name: str, city: str, *, fallback_index: int = 0) -> dict[str, float]:
        pois = self.search_poi(name, city, limit=1)
        if pois and pois[0].get("location"):
            return pois[0]["location"]
        return fallback_location(city, fallback_index)

    def nearby_hotels(
        self,
        location: dict[str, float],
        city: str,
        *,
        accommodation: str = "经济型酒店",
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        keywords = "民宿" if "民宿" in accommodation else "酒店"
        hotels = self.around_poi(location, keywords=keywords, radius=2200, limit=limit, types="100000")
        hotels = [item for item in hotels if _is_valid_hotel_poi(item)]
        if hotels:
            return [_hotel_from_poi(item, accommodation=accommodation) for item in hotels[:limit]]
        return []

    def _normalize_poi(self, item: dict[str, Any]) -> dict[str, Any] | None:
        loc = self._parse_location(str(item.get("location", "")))
        if not loc:
            return None
        rating = _first_value(item.get("biz_ext", {}).get("rating"))
        cost = _first_value(item.get("biz_ext", {}).get("cost"))
        return {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "address": _first_value(item.get("address")),
            "tel": _first_value(item.get("tel")),
            "location": loc,
            "rating": rating,
            "cost": cost,
            "distance": _safe_float(item.get("distance")),
            "source": "amap",
        }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    if value is None:
        return ""
    return str(value)


def _hotel_from_poi(poi: dict[str, Any], *, accommodation: str) -> dict[str, Any]:
    cost = _safe_int(poi.get("cost"), default=0)
    estimated_cost = cost or _base_hotel_price(accommodation)
    distance = poi.get("distance")
    distance_text = f"约{int(distance)}米" if isinstance(distance, (float, int)) else "距离以地图为准"
    return {
        "name": poi.get("name", ""),
        "address": poi.get("address", ""),
        "location": poi.get("location"),
        "price_range": f"{max(120, estimated_cost - 80)}-{estimated_cost + 120}元/晚",
        "rating": poi.get("rating") or "暂无评分",
        "distance": distance_text,
        "type": accommodation,
        "estimated_cost": estimated_cost,
        "tel": poi.get("tel", ""),
        "source": poi.get("source", "amap"),
    }


def _is_valid_hotel_poi(poi: dict[str, Any]) -> bool:
    name = str(poi.get("name") or "")
    poi_type = str(poi.get("type") or "")
    address = str(poi.get("address") or "")
    combined = f"{name} {poi_type} {address}"

    if any(keyword in combined for keyword in HOTEL_TYPE_EXCLUDE_KEYWORDS):
        return False
    if any(keyword in combined for keyword in HOTEL_EXCLUDE_KEYWORDS):
        return False

    has_hotel_name = any(keyword in name for keyword in HOTEL_INCLUDE_KEYWORDS)
    has_hotel_type = any(keyword in poi_type for keyword in HOTEL_TYPE_INCLUDE_KEYWORDS)
    has_valid_apartment_name = any(keyword in name for keyword in HOTEL_APARTMENT_INCLUDE_KEYWORDS)

    if "公寓" in name and not (has_hotel_name or has_valid_apartment_name):
        return False
    return has_hotel_name or has_hotel_type or has_valid_apartment_name


def _base_hotel_price(accommodation: str) -> int:
    if "豪华" in accommodation:
        return 680
    if "舒适" in accommodation:
        return 380
    if "民宿" in accommodation:
        return 260
    return 220


def fallback_hotels(
    stop_name: str,
    city: str,
    *,
    accommodation: str,
    budget_level: str = "standard",
    count: int = 3,
) -> list[dict[str, Any]]:
    base = _base_hotel_price(accommodation)
    if budget_level == "tight":
        base = max(120, int(base * 0.75))
    elif budget_level == "relaxed":
        base = int(base * 1.25)

    suffixes = ["精选酒店", "城市民宿", "便捷宾馆"]
    hotels: list[dict[str, Any]] = []
    for index in range(count):
        price = base + index * 45
        hotels.append(
            {
                "name": f"{stop_name}附近{suffixes[index % len(suffixes)]}",
                "address": f"{city}{stop_name}周边",
                "location": None,
                "price_range": f"{max(100, price - 60)}-{price + 80}元/晚",
                "rating": f"{4.3 + index * 0.1:.1f}",
                "distance": f"约{450 + index * 350}米",
                "type": accommodation,
                "estimated_cost": price,
                "tel": "",
                "source": "fallback",
            }
        )
    return hotels
