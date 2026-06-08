import argparse
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.paper_assistant import answer_paper_question
from education_qa.papers import PAPER_INDEX
from education_qa.retriever import TfidfRagStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask questions against the paper RAG index.")
    parser.add_argument("query")
    parser.add_argument("--index", type=Path, default=PAPER_INDEX)
    parser.add_argument("--top-k", type=int, default=4)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = TfidfRagStore.load(args.index)
    print(answer_paper_question(args.query, store, top_k=args.top_k))


if __name__ == "__main__":
    main()
