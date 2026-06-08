import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.dataset import prepare_dataset
from education_qa.paths import PROCESSED_DATASET, RAW_CEVAL_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize C-Eval style CSV files into JSONL.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_CEVAL_DIR)
    parser.add_argument("--out", type=Path, default=PROCESSED_DATASET)
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument("--allow-missing-answer", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = prepare_dataset(
        raw_dir=args.raw_dir,
        output_path=args.out,
        subjects=args.subjects,
        require_answer=not args.allow_missing_answer,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
