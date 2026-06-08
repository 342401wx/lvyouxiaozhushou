import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.paths import PROCESSED_DATASET, VECTORSTORE_PATH
from education_qa.retriever import TfidfRagStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the TF-IDF vector index.")
    parser.add_argument("--dataset", type=Path, default=PROCESSED_DATASET)
    parser.add_argument("--out", type=Path, default=VECTORSTORE_PATH)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = TfidfRagStore.from_jsonl(args.dataset)
    store.save(args.out)
    print(
        json.dumps(
            {
                "records": len(store.records),
                "index": str(args.out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
