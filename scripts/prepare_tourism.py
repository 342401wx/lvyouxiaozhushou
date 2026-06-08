import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.paths import TOURISM_DATASET, TRAVEL_REVIEWS_ZIP_PATH, WIKIVOYAGE_DUMP_PATH
from education_qa.tourism import prepare_tourism_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Wikivoyage tourism data into JSONL.")
    parser.add_argument("--wikivoyage", type=Path, default=WIKIVOYAGE_DUMP_PATH)
    parser.add_argument("--reviews-zip", type=Path, default=TRAVEL_REVIEWS_ZIP_PATH)
    parser.add_argument("--out", type=Path, default=TOURISM_DATASET)
    parser.add_argument("--titles", nargs="*", default=None, help="Only keep selected destination page titles.")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-chars", type=int, default=900)
    parser.add_argument("--min-chars", type=int, default=80)
    parser.add_argument("--no-reviews", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = prepare_tourism_dataset(
        args.out,
        wikivoyage_dump=args.wikivoyage,
        travel_reviews_zip=args.reviews_zip,
        titles=args.titles,
        max_pages=args.max_pages,
        max_chars=args.max_chars,
        min_chars=args.min_chars,
        include_reviews=not args.no_reviews,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
