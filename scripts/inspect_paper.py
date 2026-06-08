import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.pdf_extract import inspect_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect PDF structure for paper RAG.")
    parser.add_argument("pdf", type=Path, nargs="?", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    pdf = args.pdf or next(Path.cwd().glob("*.pdf"))
    print(json.dumps(inspect_pdf(pdf), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
