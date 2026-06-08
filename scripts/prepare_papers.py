import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.papers import PAPER_JSONL, prepare_papers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and chunk local paper PDFs.")
    parser.add_argument("--raw-dir", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=PAPER_JSONL)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = prepare_papers(args.raw_dir, args.out)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
