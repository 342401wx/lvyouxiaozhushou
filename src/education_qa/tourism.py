from __future__ import annotations

import bz2
import csv
import html
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .paths import PROJECT_ROOT, TRAVEL_REVIEWS_ZIP_PATH, WIKIVOYAGE_DUMP_PATH
from .retriever import RetrievedDocument, TfidfRagStore

HEADING_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
LANG_CONVERTER_RE = re.compile(r"-\{([^{}]+)\}-")
EXTERNAL_LINK_RE = re.compile(r"\[(https?://[^\s\]]+)(?:\s+([^\]]+))?\]")
TAG_RE = re.compile(r"<[^>]+>")
REF_RE = re.compile(r"<ref\b[^>/]*(?:/>|>.*?</ref>)", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TABLE_LINE_RE = re.compile(r"^\s*(\{\||\|\}|\|-|!|\|)")

IGNORED_TEMPLATES = {
    "pagebanner",
    "mapframe",
    "geo",
    "ispartof",
    "outlinecity",
    "outlinecountry",
    "usablecity",
    "usablecountry",
    "guidecity",
    "guidecountry",
    "starcity",
    "starnationalpark",
    "templatestyles",
    "quickbar",
    "infobox",
    "stub",
    "delete",
    "disambig",
}

LISTING_TEMPLATES = {
    "listing",
    "see",
    "do",
    "buy",
    "eat",
    "drink",
    "sleep",
    "go",
}

LISTING_TYPE_LABELS = {
    "go": "交通",
    "see": "观光",
    "do": "活动",
    "buy": "购物",
    "eat": "饮食",
    "drink": "夜生活",
    "sleep": "住宿",
    "listing": "地点",
}

SIMPLE_TEMPLATE_LABELS = {
    "航空": "航空",
    "铁路": "铁路",
    "客车": "客车",
    "客轮": "客轮",
    "地铁": "地铁",
    "iata": "",
    "icao": "",
}

TRAVEL_CATEGORY_LABELS = {
    "Category 1": "旅游类别1",
    "Category 2": "旅游类别2",
    "Category 3": "旅游类别3",
    "Category 4": "旅游类别4",
    "Category 5": "旅游类别5",
    "Category 6": "旅游类别6",
    "Category 7": "旅游类别7",
    "Category 8": "旅游类别8",
    "Category 9": "旅游类别9",
    "Category 10": "旅游类别10",
}

SECTION_KEYWORDS = {
    "景点": ("观光", "旅游景点"),
    "观光": ("观光",),
    "美食": ("饮食", "用餐", "餐厅"),
    "吃": ("饮食", "用餐", "餐厅"),
    "餐厅": ("饮食", "用餐", "餐厅"),
    "用餐": ("饮食", "用餐", "餐厅"),
    "住宿": ("住宿",),
    "酒店": ("住宿",),
    "交通": ("抵达", "周游", "航空", "铁路", "客车"),
    "机场": ("抵达", "航空"),
    "购物": ("购物",),
    "夜生活": ("夜生活",),
    "活动": ("活动",),
}


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def relative_path(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def _template_key(name: str) -> str:
    return normalize_text(name).split(":", maxsplit=1)[-1].strip().lower()


def split_template_parts(content: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    brace_depth = 0
    link_depth = 0
    i = 0
    while i < len(content):
        if content.startswith("{{", i):
            brace_depth += 1
            current.append("{{")
            i += 2
        elif content.startswith("}}", i):
            brace_depth = max(0, brace_depth - 1)
            current.append("}}")
            i += 2
        elif content.startswith("[[", i):
            link_depth += 1
            current.append("[[")
            i += 2
        elif content.startswith("]]", i):
            link_depth = max(0, link_depth - 1)
            current.append("]]")
            i += 2
        elif content[i] == "|" and brace_depth == 0 and link_depth == 0:
            parts.append("".join(current).strip())
            current = []
            i += 1
        else:
            current.append(content[i])
            i += 1
    parts.append("".join(current).strip())
    return parts


def parse_template(content: str) -> tuple[str, dict[str, str], list[str]]:
    parts = split_template_parts(content)
    if not parts:
        return "", {}, []

    name = parts[0].strip()
    params: dict[str, str] = {}
    positional: list[str] = []
    for part in parts[1:]:
        key, sep, value = part.partition("=")
        if sep and re.match(r"^[\w\u4e00-\u9fff -]{1,32}$", key.strip()):
            params[key.strip().lower()] = value.strip()
        elif part:
            positional.append(part)
    return name, params, positional


def _replace_templates(text: str, *, for_heading: bool = False, depth: int = 0) -> str:
    if depth > 6:
        return ""

    output: list[str] = []
    i = 0
    while i < len(text):
        if not text.startswith("{{", i):
            output.append(text[i])
            i += 1
            continue

        start = i + 2
        i = start
        brace_depth = 1
        while i < len(text) and brace_depth:
            if text.startswith("{{", i):
                brace_depth += 1
                i += 2
            elif text.startswith("}}", i):
                brace_depth -= 1
                if brace_depth == 0:
                    inner = text[start:i]
                    i += 2
                    output.append(render_template(inner, for_heading=for_heading, depth=depth + 1))
                    break
                i += 2
            else:
                i += 1
        else:
            output.append(text[start - 2 :])
            break
    return "".join(output)


def _replace_language_converter(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group(1)
        zh_cn = re.search(r"zh-cn:([^;|]+)", body, re.IGNORECASE)
        if zh_cn:
            return zh_cn.group(1).strip()
        if "|" in body:
            body = body.split("|", maxsplit=1)[-1]
        return re.sub(r"[a-z-]+:", "", body, flags=re.IGNORECASE).replace(";", " ").strip()

    return LANG_CONVERTER_RE.sub(replace, text)


def _replace_links(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group(1)
        target = body.split("|", maxsplit=1)[0].strip()
        prefix = target.split(":", maxsplit=1)[0].lower()
        if prefix in {"file", "image", "category", "文件", "图像", "分類", "分类"}:
            return ""
        return body.split("|")[-1].strip()

    return re.sub(r"\[\[([^\[\]]+)\]\]", replace, text)


def _clean_lines(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or TABLE_LINE_RE.match(line):
            continue
        line = re.sub(r"^[*#:;]+\s*", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def clean_markup(text: str, *, for_heading: bool = False, depth: int = 0) -> str:
    text = html.unescape(text or "")
    text = COMMENT_RE.sub(" ", text)
    text = REF_RE.sub(" ", text)
    text = _replace_templates(text, for_heading=for_heading, depth=depth)
    text = _replace_language_converter(text)
    text = _replace_links(text)
    text = EXTERNAL_LINK_RE.sub(lambda match: match.group(2) or match.group(1), text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("'''", "").replace("''", "")
    text = text.replace("__NOEDITSECTION__", " ").replace("__NOTOC__", " ")
    return _clean_lines(text)


def render_listing(template_name: str, params: dict[str, str], *, depth: int) -> str:
    listing_type = _template_key(params.get("type") or template_name)
    label = LISTING_TYPE_LABELS.get(listing_type, LISTING_TYPE_LABELS.get(_template_key(template_name), "地点"))
    item_name = clean_markup(params.get("name") or params.get("名称") or "", depth=depth + 1)
    content = clean_markup(
        params.get("content") or params.get("description") or params.get("说明") or "",
        depth=depth + 1,
    )

    details: list[str] = []
    if item_name:
        details.append(f"{label}：{item_name}")
    for key, title in (
        ("address", "地址"),
        ("directions", "到达方式"),
        ("hours", "开放时间"),
        ("price", "费用"),
        ("phone", "电话"),
        ("url", "网址"),
    ):
        value = clean_markup(params.get(key) or "", depth=depth + 1)
        if value:
            details.append(f"{title}：{value}")

    lat = normalize_text(params.get("lat"))
    long = normalize_text(params.get("long") or params.get("lng"))
    if lat and long:
        details.append(f"坐标：{lat},{long}")
    if content:
        details.append(f"说明：{content}")
    return "；".join(details)


def render_template(content: str, *, for_heading: bool = False, depth: int = 0) -> str:
    template_name, params, positional = parse_template(content)
    key = _template_key(template_name)
    if not key or key in IGNORED_TEMPLATES:
        return ""

    has_listing_fields = any(field in params for field in ("name", "名称", "content", "address", "lat", "long"))
    if key in LISTING_TEMPLATES or has_listing_fields:
        return render_listing(template_name, params, depth=depth)

    if key in SIMPLE_TEMPLATE_LABELS:
        if positional:
            return clean_markup(positional[0], for_heading=for_heading, depth=depth + 1)
        return SIMPLE_TEMPLATE_LABELS[key] or template_name.strip()

    if for_heading:
        if positional:
            return clean_markup(positional[-1], for_heading=True, depth=depth + 1)
        return template_name.strip()

    return ""


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = [("概览", [])]
    heading_stack: list[tuple[int, str]] = []

    for line in (wikitext or "").splitlines():
        match = HEADING_RE.match(line.strip())
        if not match:
            sections[-1][1].append(line)
            continue

        level = len(match.group(1))
        heading = clean_markup(match.group(2), for_heading=True).strip()
        if not heading:
            continue
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, heading))
        sections.append((" / ".join(item[1] for item in heading_stack), []))

    return [(title, "\n".join(lines)) for title, lines in sections]


def split_into_chunks(text: str, max_chars: int = 900, min_chars: int = 80) -> list[str]:
    units = [unit.strip() for unit in re.split(r"\n+|(?<=[。！？；.!?])\s*", text) if unit.strip()]
    chunks: list[str] = []
    current = ""

    for unit in units:
        if len(unit) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(unit), max_chars):
                chunks.append(unit[start : start + max_chars].strip())
            continue

        candidate = f"{current}{unit}" if not current else f"{current}\n{unit}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = unit

    if current:
        chunks.append(current.strip())

    long_enough = [chunk for chunk in chunks if len(chunk) >= min_chars]
    return long_enough or chunks[:1]


def build_tourism_document(record: dict) -> str:
    return "\n".join(
        [
            "资料类型：旅游规划知识库",
            f"目的地：{record.get('title', '')}",
            f"栏目：{record.get('section', '')}",
            f"内容：{record.get('text', '')}",
            f"来源：{record.get('source', '')}",
        ]
    )


def enrich_tourism_record(record: dict) -> dict:
    enriched = dict(record)
    enriched["document"] = build_tourism_document(record)
    enriched["metadata"] = {
        "id": record["id"],
        "source_type": record.get("source_type"),
        "title": record.get("title"),
        "section": record.get("section"),
        "source": record.get("source"),
        "chunk_index": record.get("chunk_index"),
    }
    return enriched


def records_from_wikivoyage_page(
    title: str,
    page_id: str,
    wikitext: str,
    *,
    source: str,
    max_chars: int = 900,
    min_chars: int = 80,
) -> list[dict]:
    records: list[dict] = []
    for section, section_text in split_sections(wikitext):
        clean_text = clean_markup(section_text).strip()
        if len(clean_text) < min_chars and section != "概览":
            continue
        for chunk_index, chunk in enumerate(split_into_chunks(clean_text, max_chars=max_chars, min_chars=min_chars)):
            if not chunk:
                continue
            records.append(
                {
                    "id": f"wikivoyage:{page_id}:{len(records)}",
                    "source_type": "wikivoyage",
                    "title": title,
                    "section": section,
                    "text": chunk,
                    "source": source,
                    "page_id": page_id,
                    "chunk_index": chunk_index,
                }
            )
    return records


def _open_xml_dump(path: Path):
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    return Path(path).open("rb")


def iter_wikivoyage_records(
    dump_path: Path,
    *,
    titles: Iterable[str] | None = None,
    max_pages: int | None = None,
    max_chars: int = 900,
    min_chars: int = 80,
) -> Iterator[dict]:
    title_filter = set(titles or [])
    source = relative_path(dump_path)
    parsed_pages = 0

    with _open_xml_dump(dump_path) as handle:
        for _, elem in ET.iterparse(handle, events=("end",)):
            if not elem.tag.endswith("page"):
                continue

            ns = elem.tag[: -len("page")]
            title = elem.findtext(f"{ns}title") or ""
            namespace = elem.findtext(f"{ns}ns")
            page_id = elem.findtext(f"{ns}id") or title
            text = elem.findtext(f"{ns}revision/{ns}text") or ""
            redirect = elem.find(f"{ns}redirect") is not None

            if (
                namespace == "0"
                and not redirect
                and title
                and text.strip()
                and title not in {"首页", "Main Page"}
                and not text.lstrip().lower().startswith("#redirect")
                and not text.lstrip().startswith("#重定向")
                and (not title_filter or title in title_filter)
            ):
                for record in records_from_wikivoyage_page(
                    title,
                    page_id,
                    text,
                    source=source,
                    max_chars=max_chars,
                    min_chars=min_chars,
                ):
                    yield record
                parsed_pages += 1
                if max_pages is not None and parsed_pages >= max_pages:
                    elem.clear()
                    break
            elem.clear()


def build_travel_review_summary(zip_path: Path) -> dict | None:
    if not Path(zip_path).exists():
        return None

    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            return None
        with archive.open(csv_names[0]) as handle:
            frame = pd.read_csv(handle)

    numeric_columns = [column for column in frame.columns if column != "User ID"]
    means = frame[numeric_columns].apply(pd.to_numeric, errors="coerce").mean().sort_values(ascending=False)
    lines = [
        f"样本量：{len(frame)} 位用户。",
        "各旅游偏好类别平均评分如下：",
    ]
    for column, score in means.items():
        label = TRAVEL_CATEGORY_LABELS.get(str(column), str(column))
        lines.append(f"{label}（{column}）：{score:.2f}")

    return {
        "id": "travel_reviews:summary",
        "source_type": "travel_reviews",
        "title": "旅行偏好评分汇总",
        "section": "结构化评分",
        "text": "\n".join(lines),
        "source": relative_path(zip_path),
        "page_id": "travel_reviews",
        "chunk_index": 0,
    }


def write_jsonl(records: Iterable[dict], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with Path(output_path).open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(enrich_tourism_record(record), ensure_ascii=False) + "\n")
            count += 1
    return count


def prepare_tourism_dataset(
    output_path: Path,
    *,
    wikivoyage_dump: Path = WIKIVOYAGE_DUMP_PATH,
    travel_reviews_zip: Path | None = TRAVEL_REVIEWS_ZIP_PATH,
    titles: Iterable[str] | None = None,
    max_pages: int | None = None,
    max_chars: int = 900,
    min_chars: int = 80,
    include_reviews: bool = True,
) -> dict:
    records = list(
        iter_wikivoyage_records(
            wikivoyage_dump,
            titles=titles,
            max_pages=max_pages,
            max_chars=max_chars,
            min_chars=min_chars,
        )
    )
    if include_reviews and travel_reviews_zip is not None:
        summary = build_travel_review_summary(travel_reviews_zip)
        if summary is not None:
            records.append(summary)

    count = write_jsonl(records, output_path)
    source_counts = Counter(record["source_type"] for record in records)
    title_counts = Counter(record["title"] for record in records if record.get("source_type") == "wikivoyage")
    return {
        "records": count,
        "sources": dict(sorted(source_counts.items())),
        "destinations": len(title_counts),
        "top_destinations": dict(title_counts.most_common(10)),
        "output": relative_path(output_path),
    }


def _shorten(text: str, limit: int = 320) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _mentioned_titles(query: str, records: list[dict], limit: int = 3) -> list[str]:
    titles = {
        record.get("title", "")
        for record in records
        if record.get("source_type") == "wikivoyage" and len(record.get("title", "")) >= 2
    }
    matches = [title for title in titles if title in query]
    return sorted(matches, key=len, reverse=True)[:limit]


def _section_bonus(query: str, record: dict) -> float:
    section = str(record.get("section", ""))
    bonus = 0.0
    for keyword, section_names in SECTION_KEYWORDS.items():
        if keyword in query and any(name in section for name in section_names):
            bonus += 0.08 if keyword in {"美食", "吃", "餐厅", "用餐"} else 0.04
    return bonus


def _search_tourism(
    query: str,
    store: TfidfRagStore,
    *,
    top_k: int,
    min_score: float,
    titles: list[str] | None = None,
) -> list[RetrievedDocument]:
    title_filter = set(titles or [])
    candidate_indices = [
        index
        for index, record in enumerate(store.records)
        if not title_filter or record.get("title") in title_filter
    ]
    if not candidate_indices:
        return []

    query_vector = store.vectorizer.transform([query])
    scores = cosine_similarity(query_vector, store.matrix[candidate_indices]).ravel()
    ranked = sorted(
        (
            (
                float(scores[offset]) + _section_bonus(query, store.records[record_index]),
                record_index,
            )
            for offset, record_index in enumerate(candidate_indices)
        ),
        reverse=True,
    )

    results: list[RetrievedDocument] = []
    for score, record_index in ranked:
        if score < min_score:
            continue
        results.append(RetrievedDocument(score=score, record=store.records[record_index]))
        if len(results) >= top_k:
            break
    return results


def answer_tourism_question(query: str, store: TfidfRagStore, top_k: int = 5) -> str:
    titles = _mentioned_titles(query, store.records)
    results = _search_tourism(query, store, top_k=top_k, min_score=0.005, titles=titles)
    if len(results) < top_k and titles:
        fallback = _search_tourism(query, store, top_k=top_k, min_score=0.005)
        seen_ids = {result.record.get("id") for result in results}
        results.extend(result for result in fallback if result.record.get("id") not in seen_ids)
        results = results[:top_k]
    if not results:
        return "旅游知识库里暂时没有检索到足够相关的内容，可以换一个城市、景点或旅行主题再试。"

    lines = [
        f"问题：{query}",
        "",
        "根据旅游知识库，最相关的资料如下：",
    ]
    for index, result in enumerate(results, start=1):
        record = result.record
        lines.extend(
            [
                "",
                f"{index}. {record.get('title')} / {record.get('section')}（相似度 {result.score:.3f}）",
                _shorten(record.get("text", "")),
                f"来源：{record.get('source')}",
            ]
        )
    return "\n".join(lines)


def search_tourism_records(
    query: str,
    store: TfidfRagStore,
    *,
    city: str | None = None,
    top_k: int = 12,
    min_score: float = 0.005,
) -> list[RetrievedDocument]:
    """Search tourism records with an optional destination filter."""
    titles = [city] if city else _mentioned_titles(query, store.records)
    results = _search_tourism(query, store, top_k=top_k, min_score=min_score, titles=titles)
    if results or not titles:
        return results
    return _search_tourism(query, store, top_k=top_k, min_score=min_score)
