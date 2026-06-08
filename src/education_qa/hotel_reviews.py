from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import zipfile

import pandas as pd

from .paths import HOTEL_REVIEWS_ZIP_PATH


POSITIVE_TERMS = {
    "location": "位置便利",
    "clean": "卫生干净",
    "comfortable": "床品舒适",
    "friendly": "服务友好",
    "breakfast": "早餐体验",
    "quiet": "安静",
}

NEGATIVE_TERMS = {
    "noise": "噪音",
    "parking": "停车费用",
    "small": "房间偏小",
    "dirty": "卫生问题",
    "expensive": "价格偏高",
    "staff": "服务波动",
}


REVIEW_SECTIONS = [
    {
        "title": "位置与通勤",
        "tone": "positive",
        "terms": ("location", "walking distance", "downtown", "shopping", "convenient", "neighborhood"),
        "takeaway": "优先确认酒店到景点、车站和商圈的步行/打车时间，位置便利通常比单看低价更影响体验。",
    },
    {
        "title": "卫生与舒适度",
        "tone": "positive",
        "terms": ("clean", "comfortable", "bed", "bathroom", "housekeeping", "room"),
        "takeaway": "查看近期评论里对房间卫生、床品、浴室和保洁响应的描述，适合判断住一晚是否省心。",
    },
    {
        "title": "噪音与睡眠",
        "tone": "risk",
        "terms": ("noise", "noisy", "soundproof", "loud", "hallway", "doors", "neighbors"),
        "takeaway": "如果行程早起赶车或当天景点密集，要特别避开隔音差、临街或走廊噪音频繁的房间。",
    },
    {
        "title": "停车与额外费用",
        "tone": "risk",
        "terms": ("parking", "charge", "fee", "expensive", "valet", "extra"),
        "takeaway": "自驾或预算紧时要提前看停车、押金、早餐和服务费，避免到店后出现额外支出。",
    },
    {
        "title": "服务响应",
        "tone": "mixed",
        "terms": ("staff", "friendly", "helpful", "desk", "concierge", "service"),
        "takeaway": "服务评论适合看细节：前台响应、行李协助、问题处理和特殊需求是否兑现。",
    },
]

TERM_LABELS = {
    **POSITIVE_TERMS,
    **NEGATIVE_TERMS,
    "walking distance": "步行可达",
    "downtown": "市中心",
    "shopping": "商圈便利",
    "convenient": "交通便利",
    "neighborhood": "周边环境",
    "bed": "床品",
    "bathroom": "浴室",
    "housekeeping": "保洁",
    "room": "房间",
    "noisy": "噪音",
    "soundproof": "隔音",
    "loud": "声音偏大",
    "hallway": "走廊噪音",
    "doors": "门声",
    "neighbors": "邻房干扰",
    "charge": "收费",
    "fee": "费用",
    "valet": "代客泊车",
    "extra": "额外费用",
    "helpful": "服务帮助",
    "desk": "前台",
    "concierge": "礼宾",
    "service": "服务",
}

BOOKING_TIPS = [
    "订房前优先看最近一个月的差评，重点查噪音、卫生、热水、空调和额外收费。",
    "自驾用户单独确认停车场位置、是否收费、夜间是否好进出。",
    "如果第二天赶车或早出门，优先选离车站/首个景点更近且隔音评价稳定的酒店。",
    "评论库只能提供住客评价维度，具体酒店仍要以订房平台的最新评论和实拍图为准。",
]


@lru_cache(maxsize=2)
def load_hotel_review_insights(zip_path: str | Path = HOTEL_REVIEWS_ZIP_PATH) -> dict:
    path = Path(zip_path)
    if not path.exists():
        return {
            "available": False,
            "summary": "未找到酒店评论数据，酒店建议将基于地图信息和预算估算。",
            "positive_focus": [],
            "risk_focus": [],
            "average_rating": None,
            "sample_size": 0,
            "detail_sections": [],
            "booking_tips": BOOKING_TIPS,
        }

    with zipfile.ZipFile(path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            return {
                "available": False,
                "summary": "酒店评论压缩包里没有 CSV 文件。",
                "sample_size": 0,
                "detail_sections": [],
                "booking_tips": BOOKING_TIPS,
            }
        with archive.open(csv_names[0]) as handle:
            frame = pd.read_csv(handle)

    raw_reviews = frame.get("Review", pd.Series(dtype=str)).fillna("").astype(str)
    reviews = raw_reviews.str.lower()
    ratings = pd.to_numeric(frame.get("Rating", pd.Series(dtype=float)), errors="coerce")

    positive_focus = _top_terms(reviews, POSITIVE_TERMS)
    risk_focus = _top_terms(reviews, NEGATIVE_TERMS)
    avg_rating = float(ratings.mean()) if not ratings.empty else 0.0
    detail_sections = _build_detail_sections(frame, raw_reviews, reviews, ratings)
    focus_points = [item["term"] for item in [*positive_focus[:3], *risk_focus[:3]]]

    return {
        "available": True,
        "sample_size": int(len(frame)),
        "average_rating": round(avg_rating, 2),
        "positive_focus": positive_focus,
        "risk_focus": risk_focus,
        "focus_points": focus_points,
        "detail_sections": detail_sections,
        "booking_tips": BOOKING_TIPS,
        "summary": (
            "已接入酒店评论知识库。建议在酒店详情里重点查看位置、卫生、噪音、停车费用和服务响应；"
            "地图酒店列表仅作周边候选，具体入住体验以订房平台最新评论为准。"
        ),
    }


def _top_terms(reviews: pd.Series, mapping: dict[str, str], limit: int = 4) -> list[dict[str, object]]:
    scored = []
    total = max(len(reviews), 1)
    for term, label in mapping.items():
        count = int(reviews.str.contains(term, regex=False).sum())
        if count:
            scored.append({"term": label, "count": count, "share": round(count / total, 3)})
    return sorted(scored, key=lambda item: int(item["count"]), reverse=True)[:limit]


def _build_detail_sections(
    frame: pd.DataFrame,
    raw_reviews: pd.Series,
    reviews: pd.Series,
    ratings: pd.Series,
) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    for section in REVIEW_SECTIONS:
        examples = _review_examples(
            frame,
            raw_reviews,
            reviews,
            ratings,
            section["terms"],
            tone=str(section["tone"]),
            limit=2,
        )
        if examples:
            sections.append(
                {
                    "title": section["title"],
                    "tone": section["tone"],
                    "takeaway": section["takeaway"],
                    "examples": examples,
                }
            )
    return sections


def _review_examples(
    frame: pd.DataFrame,
    raw_reviews: pd.Series,
    reviews: pd.Series,
    ratings: pd.Series,
    terms: tuple[str, ...],
    *,
    tone: str,
    limit: int,
) -> list[dict[str, object]]:
    if frame.empty:
        return []
    mask = pd.Series(False, index=frame.index)
    for term in terms:
        mask = mask | reviews.str.contains(term, regex=False, na=False)
    matched = frame.loc[mask].copy()
    if matched.empty:
        return []

    matched["_rating_num"] = ratings.loc[matched.index]
    matched["_review_text"] = raw_reviews.loc[matched.index]
    if tone == "risk":
        matched = matched.sort_values(["_rating_num"], ascending=True, na_position="last")
    else:
        matched = matched.sort_values(["_rating_num"], ascending=False, na_position="last")

    examples = []
    seen: set[str] = set()
    for _, row in matched.head(limit * 4).iterrows():
        review_text = _clip_review(row.get("_review_text", ""))
        if not review_text or review_text in seen:
            continue
        seen.add(review_text)
        examples.append(
            {
                "rating": _coerce_rating(row.get("_rating_num")),
                "excerpt": review_text,
                "cues": _matched_labels(review_text.lower(), terms),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _matched_labels(text: str, terms: tuple[str, ...], limit: int = 4) -> list[str]:
    labels = []
    for term in terms:
        if term in text:
            labels.append(TERM_LABELS.get(term, term))
    return labels[:limit]


def _clip_review(value: object, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def _coerce_rating(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
