import argparse
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.assistant import answer_question
from education_qa.paths import VECTORSTORE_PATH
from education_qa.retriever import TfidfRagStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask the education QA assistant.")
    parser.add_argument("query")
    parser.add_argument("--index", type=Path, default=VECTORSTORE_PATH)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = TfidfRagStore.load(args.index)
    print(answer_question(args.query, store, top_k=args.top_k))


if __name__ == "__main__":
    main()
