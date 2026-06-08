from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd

from .paths import PROJECT_ROOT

OPTION_KEYS = ("A", "B", "C", "D")
SPLIT_SUFFIX_RE = re.compile(r"_(dev|val|test)$", re.IGNORECASE)

SUBJECT_LABELS = {
    "computer_network": "计算机网络",
    "operating_system": "操作系统",
    "computer_architecture": "计算机组成/体系结构",
    "college_programming": "大学编程",
}


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def infer_subject(csv_path: Path) -> str:
    stem = SPLIT_SUFFIX_RE.sub("", csv_path.stem)
    return stem


def _get_column(row: pd.Series, columns: dict[str, str], *names: str) -> str:
    for name in names:
        column = columns.get(name.lower())
        if column is not None:
            return normalize_text(row.get(column))
    return ""


def normalize_ceval_row(row: pd.Series, csv_path: Path, row_index: int) -> dict:
    columns = {str(column).strip().lower(): column for column in row.index}
    subject = infer_subject(csv_path)
    raw_id = _get_column(row, columns, "id", "index")
    question_id = raw_id or str(row_index + 1)
    options = {key: _get_column(row, columns, key) for key in OPTION_KEYS}
    answer = _get_column(row, columns, "answer", "答案").upper()

    return {
        "id": f"{subject}:{question_id}",
        "subject": subject,
        "subject_label": SUBJECT_LABELS.get(subject, subject),
        "question": _get_column(row, columns, "question", "题目"),
        "options": options,
        "answer": answer,
        "explanation": _get_column(row, columns, "explanation", "analysis", "解析"),
        "source": relative_path(csv_path),
        "row_index": row_index,
    }


def is_usable_record(record: dict, require_answer: bool = True) -> bool:
    has_question = bool(record["question"])
    has_options = all(record["options"].get(key) for key in OPTION_KEYS)
    has_answer = record["answer"] in OPTION_KEYS
    return has_question and has_options and (has_answer or not require_answer)


def iter_ceval_records(
    raw_dir: Path,
    subjects: Iterable[str] | None = None,
    require_answer: bool = True,
) -> Iterable[dict]:
    subject_filter = set(subjects or [])
    for csv_path in sorted(Path(raw_dir).rglob("*.csv")):
        subject = infer_subject(csv_path)
        if subject_filter and subject not in subject_filter:
            continue

        frame = pd.read_csv(csv_path)
        for row_index, row in frame.iterrows():
            record = normalize_ceval_row(row, csv_path, int(row_index))
            if is_usable_record(record, require_answer=require_answer):
                yield record


def build_document_text(record: dict) -> str:
    option_lines = [f"{key}. {record['options'].get(key, '')}" for key in OPTION_KEYS]
    answer_text = record["options"].get(record.get("answer", ""), "")
    explanation = record.get("explanation") or "暂无解析"
    return "\n".join(
        [
            f"科目：{record.get('subject_label') or record.get('subject')}",
            f"题目：{record['question']}",
            "选项：",
            *option_lines,
            f"答案：{record.get('answer', '')}. {answer_text}",
            f"解析：{explanation}",
            f"来源：{record.get('source', '')}",
        ]
    )


def enrich_record(record: dict) -> dict:
    enriched = dict(record)
    enriched["document"] = build_document_text(record)
    enriched["metadata"] = {
        "id": record["id"],
        "subject": record["subject"],
        "subject_label": record.get("subject_label", record["subject"]),
        "source": record["source"],
        "row_index": record["row_index"],
    }
    return enriched


def write_jsonl(records: Iterable[dict], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(enrich_record(record), ensure_ascii=False) + "\n")
            count += 1
    return count


def load_jsonl(path: Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def prepare_dataset(
    raw_dir: Path,
    output_path: Path,
    subjects: Iterable[str] | None = None,
    require_answer: bool = True,
) -> dict:
    records = list(iter_ceval_records(raw_dir, subjects=subjects, require_answer=require_answer))
    count = write_jsonl(records, output_path)
    subject_counts = Counter(record["subject"] for record in records)
    return {
        "records": count,
        "subjects": dict(sorted(subject_counts.items())),
        "output": relative_path(output_path),
    }
