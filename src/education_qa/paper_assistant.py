from __future__ import annotations

import re

from .retriever import RetrievedDocument, TfidfRagStore


def _query_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z0-9_.:@+-]+|[\u4e00-\u9fff]{2,}", query)
    generic = {"这篇", "论文", "主要", "什么", "多少", "作用", "研究"}
    return [term for term in terms if term not in generic]


def _compact(text: str, query: str = "", limit: int = 450) -> str:
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    anchors = _query_terms(query) + ["中文摘要", "摘要", "关键词", "本文", "本研究", "本系统", "驾驶行为", "课题", "结论", "总结"]
    positions = [text.find(anchor) for anchor in anchors if anchor and text.find(anchor) >= 0]
    if positions:
        start = max(min(positions) - 80, 0)
        text = text[start:]
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _format_hit(hit: RetrievedDocument, index: int, query: str) -> str:
    record = hit.record
    return "\n".join(
        [
            f"{index}. 相似度 {hit.score:.3f} | 片段 {record.get('chunk_index')} | {record.get('title')}",
            f"来源：{record.get('source')}",
            f"摘录：{_compact(record.get('text', ''), query=query)}",
        ]
    )


def answer_paper_question(query: str, store: TfidfRagStore, top_k: int = 4) -> str:
    expanded_query = query
    if re.search(r"主要研究|研究了什么|总结|摘要|创新点|结论|研究内容", query):
        expanded_query = f"{query} 中文摘要 关键词 研究内容 系统设计 实现 结论"

    hits = store.search(expanded_query, top_k=top_k, min_score=0.01)
    if not hits:
        return "论文库中暂未检索到足够相关的片段，请换一个关键词再试。"

    lines = [
        f"问题：{query}",
        "",
        "根据论文库检索到的相关片段：",
    ]
    lines.extend(_format_hit(hit, index, query) for index, hit in enumerate(hits, start=1))
    lines.extend(
        [
            "",
            "提示：当前离线版本负责检索和摘录，接入 LLM 后可把这些片段作为 RAG 上下文生成完整回答。",
        ]
    )
    return "\n\n".join(lines)
