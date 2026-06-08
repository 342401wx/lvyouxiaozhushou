import argparse
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.paths import TOURISM_VECTORSTORE_PATH
from education_qa.retriever import TfidfRagStore
from education_qa.tourism import answer_tourism_question


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask the tourism planning assistant.")
    parser.add_argument("query")
    parser.add_argument("--index", type=Path, default=TOURISM_VECTORSTORE_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = TfidfRagStore.load(args.index)
    print(answer_tourism_question(args.query, store, top_k=args.top_k))


if __name__ == "__main__":
    main()
