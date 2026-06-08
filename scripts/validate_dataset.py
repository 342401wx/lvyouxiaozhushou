import argparse
import json
import random
from collections import Counter
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.dataset import OPTION_KEYS, load_jsonl
from education_qa.paths import PROCESSED_DATASET, VECTORSTORE_PATH
from education_qa.retriever import TfidfRagStore

TEST_QUERIES = [
    "操作系统中进程和线程有什么区别？",
    "计算机网络里 TCP 和 UDP 的区别？",
    "Python 函数参数有哪些类型？",
    "Cache 的作用是什么？",
    "DNS 是做什么的？",
]


def validate_records(records: list[dict], sample_size: int) -> dict:
    if not records:
        raise AssertionError("No records found in processed dataset.")

    subject_counts = Counter(record["subject"] for record in records)
    if len(subject_counts) < 3:
        raise AssertionError(f"Expected at least 3 subjects, got {len(subject_counts)}.")

    if len(records) < sample_size:
        raise AssertionError(f"Expected at least {sample_size} records, got {len(records)}.")

    sample = random.Random(7).sample(records, sample_size)
    for record in sample:
        if not record.get("question"):
            raise AssertionError(f"Missing question: {record.get('id')}")
        if record.get("answer") not in OPTION_KEYS:
            raise AssertionError(f"Invalid answer: {record.get('id')}")
        if not all(record.get("options", {}).get(key) for key in OPTION_KEYS):
            raise AssertionError(f"Missing option: {record.get('id')}")

    return {
        "records": len(records),
        "subjects": dict(sorted(subject_counts.items())),
        "sample_checked": sample_size,
    }


def validate_retrieval(store: TfidfRagStore) -> list[dict]:
    results = []
    for query in TEST_QUERIES:
        hits = store.search(query, top_k=1, min_score=0.01)
        if not hits:
            raise AssertionError(f"No retrieval hit for query: {query}")
        results.append(
            {
                "query": query,
                "top_subject": hits[0].record["subject"],
                "score": round(hits[0].score, 4),
                "source": hits[0].record["source"],
            }
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate processed dataset and retrieval quality.")
    parser.add_argument("--dataset", type=Path, default=PROCESSED_DATASET)
    parser.add_argument("--index", type=Path, default=VECTORSTORE_PATH)
    parser.add_argument("--sample-size", type=int, default=20)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    records = load_jsonl(args.dataset)
    store = TfidfRagStore.load(args.index)
    report = validate_records(records, sample_size=args.sample_size)
    report["retrieval"] = validate_retrieval(store)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
