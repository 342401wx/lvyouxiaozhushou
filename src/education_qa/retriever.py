from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .dataset import load_jsonl


@dataclass
class RetrievedDocument:
    score: float
    record: dict


class TfidfRagStore:
    def __init__(self, vectorizer: TfidfVectorizer, matrix, records: list[dict]):
        self.vectorizer = vectorizer
        self.matrix = matrix
        self.records = records

    @classmethod
    def build(cls, records: list[dict]) -> "TfidfRagStore":
        documents = [record["document"] for record in records]
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), lowercase=False)
        matrix = vectorizer.fit_transform(documents)
        return cls(vectorizer=vectorizer, matrix=matrix, records=records)

    @classmethod
    def from_jsonl(cls, dataset_path: Path) -> "TfidfRagStore":
        return cls.build(load_jsonl(dataset_path))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("wb") as handle:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "matrix": self.matrix,
                    "records": self.records,
                },
                handle,
            )

    @classmethod
    def load(cls, path: Path) -> "TfidfRagStore":
        with Path(path).open("rb") as handle:
            data = pickle.load(handle)
        return cls(
            vectorizer=data["vectorizer"],
            matrix=data["matrix"],
            records=data["records"],
        )

    def search(self, query: str, top_k: int = 3, min_score: float = 0.0) -> list[RetrievedDocument]:
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        ranked_indices = scores.argsort()[::-1]

        results: list[RetrievedDocument] = []
        for index in ranked_indices:
            score = float(scores[index])
            if score < min_score:
                continue
            results.append(RetrievedDocument(score=score, record=self.records[int(index)]))
            if len(results) >= top_k:
                break
        return results
