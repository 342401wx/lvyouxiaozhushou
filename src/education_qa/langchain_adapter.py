from __future__ import annotations

from pathlib import Path

from .dataset import load_jsonl


def load_langchain_documents(dataset_path: Path):
    try:
        from langchain_core.documents import Document
    except ImportError as exc:
        raise RuntimeError("Please install requirements-optional.txt to use LangChain documents.") from exc

    documents = []
    for record in load_jsonl(dataset_path):
        documents.append(
            Document(
                page_content=record["document"],
                metadata=record.get("metadata", {}),
            )
        )
    return documents


def build_chroma_vectorstore(
    dataset_path: Path,
    persist_dir: Path,
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
):
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import Chroma
    except ImportError as exc:
        raise RuntimeError("Please install requirements-optional.txt to build the Chroma index.") from exc

    documents = load_langchain_documents(dataset_path)
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(persist_dir),
        collection_name="education_qa",
    )
