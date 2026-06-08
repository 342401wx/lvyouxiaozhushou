from __future__ import annotations

from .retriever import RetrievedDocument, TfidfRagStore


def _answer_text(record: dict) -> str:
    answer = record.get("answer", "")
    option_text = record.get("options", {}).get(answer, "")
    return f"{answer}. {option_text}".strip()


def format_result(result: RetrievedDocument, index: int) -> str:
    record = result.record
    explanation = record.get("explanation") or "暂无解析"
    return "\n".join(
        [
            f"{index}. [{record.get('subject_label', record.get('subject'))}] 相似度 {result.score:.3f}",
            f"题目：{record.get('question')}",
            f"答案：{_answer_text(record)}",
            f"解析：{explanation}",
            f"来源：{record.get('source')}",
        ]
    )


def answer_question(query: str, store: TfidfRagStore, top_k: int = 3) -> str:
    results = store.search(query, top_k=top_k, min_score=0.01)
    if not results:
        return "题库中暂未检索到足够相关的内容，请换一个关键词或补充更多数据。"

    best = results[0].record
    lines = [
        f"问题：{query}",
        "",
        "根据题库检索，最相关的知识点如下：",
        f"科目：{best.get('subject_label', best.get('subject'))}",
        f"题目：{best.get('question')}",
        f"答案：{_answer_text(best)}",
        f"解析：{best.get('explanation') or '暂无解析'}",
        f"来源：{best.get('source')}",
    ]

    if len(results) > 1:
        lines.extend(["", "相关题目："])
        lines.extend(format_result(result, index) for index, result in enumerate(results[1:], start=1))

    return "\n".join(lines)
