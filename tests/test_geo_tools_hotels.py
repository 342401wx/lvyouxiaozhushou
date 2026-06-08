from education_qa.geo_tools import _is_valid_hotel_poi


def test_filters_study_apartment_from_hotels() -> None:
    poi = {
        "name": "岸上考研学习公寓",
        "type": "住宿服务;旅馆招待所",
        "address": "铜陵市大通古镇附近",
    }

    assert _is_valid_hotel_poi(poi) is False


def test_keeps_real_tourism_lodging() -> None:
    assert _is_valid_hotel_poi({"name": "天井湖精品酒店", "type": "住宿服务;宾馆酒店"}) is True
    assert _is_valid_hotel_poi({"name": "铜陵老街民宿公寓", "type": "住宿服务;旅馆招待所"}) is True


def test_filters_education_poi_from_hotels() -> None:
    poi = {
        "name": "铜陵培训学校",
        "type": "科教文化服务;培训机构",
        "address": "铜陵市",
    }

    assert _is_valid_hotel_poi(poi) is False
