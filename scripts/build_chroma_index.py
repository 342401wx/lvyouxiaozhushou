import argparse
import json
from pathlib import Path

from _bootstrap import SRC  # noqa: F401

from education_qa.langchain_adapter import build_chroma_vectorstore
from education_qa.paths import PROCESSED_DATASET


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an optional LangChain + Chroma index.")
    parser.add_argument("--dataset", type=Path, default=PROCESSED_DATASET)
    parser.add_argument("--persist-dir", type=Path, default=Path("data/vectorstore/chroma"))
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = build_chroma_vectorstore(
        dataset_path=args.dataset,
        persist_dir=args.persist_dir,
        embedding_model=args.embedding_model,
    )
    print(
        json.dumps(
            {
                "collection": store._collection.name,
                "persist_dir": str(args.persist_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
