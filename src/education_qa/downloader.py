from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

import requests

from .paths import RAW_CEVAL_DIR

DEFAULT_URLS = [
    "https://huggingface.co/datasets/ceval/ceval-exam/resolve/main/ceval-exam.zip",
]


def download_file(url: str, destination: Path, force: bool = False) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return destination

    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            shutil.copyfileobj(response.raw, handle)
    return destination


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(output_dir)


def download_and_extract(raw_dir: Path, url: str | None = None, force: bool = False) -> Path:
    selected_url = url or DEFAULT_URLS[0]
    zip_path = raw_dir / "ceval-exam.zip"
    downloaded = download_file(selected_url, zip_path, force=force)
    extract_zip(downloaded, raw_dir)
    return downloaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download and extract the C-Eval dataset.")
    parser.add_argument("--out-dir", type=Path, default=RAW_CEVAL_DIR)
    parser.add_argument("--url", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--extract-only", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.extract_only:
        extract_zip(args.extract_only, args.out_dir)
        print(f"Extracted {args.extract_only} to {args.out_dir}")
        return

    zip_path = download_and_extract(args.out_dir, url=args.url, force=args.force)
    print(f"Downloaded and extracted {zip_path}")


if __name__ == "__main__":
    main()
