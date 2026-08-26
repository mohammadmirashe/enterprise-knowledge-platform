from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


class Retriever:
    def __init__(
        self,
        db: Any,
        fetch_k: int = 12,
        final_k: int = 5,
        minimum_score: float = 0.30,
    ) -> None:
        self.db = db
        self.fetch_k = fetch_k
        self.final_k = final_k
        self.minimum_score = minimum_score

    @staticmethod
    def _distance_to_cosine(distance: float) -> float:
        score = 1.0 - float(distance) / 2.0
        return round(max(0.0, min(1.0, score)), 4)

    def retrieve(self, query: str) -> list[Document]:
        query = query.strip()
        if not query:
            return []

        results = self.db.similarity_search_with_score(query, k=self.fetch_k)
        accepted: list[Document] = []
        for rank, (document, distance) in enumerate(results, start=1):
            score = self._distance_to_cosine(distance)
            document.metadata = dict(document.metadata)
            document.metadata.update(
                distance=round(float(distance), 4),
                relevance_score=score,
                retrieval_rank=rank,
            )
            if score >= self.minimum_score:
                accepted.append(document)

        accepted.sort(
            key=lambda document: document.metadata.get("relevance_score", 0.0),
            reverse=True,
        )
        return accepted[: self.final_k]

    @staticmethod
    def analyze_relevance(documents: list[Document]) -> dict[str, object]:
        if not documents:
            return {
                "level": "none",
                "best_score": 0.0,
                "average_score": 0.0,
                "document_count": 0,
                "reason": "No document passed the relevance threshold.",
            }
        scores = [float(d.metadata.get("relevance_score", 0.0)) for d in documents]
        best = max(scores)
        average = sum(scores) / len(scores)
        if best >= 0.65 and average >= 0.45:
            level, reason = "strong", "Retrieved documents are strongly related."
        elif best >= 0.42:
            level, reason = "partial", "Retrieved documents are partially related."
        else:
            level, reason = "weak", "Retrieved documents have weak semantic similarity."
        return {
            "level": level,
            "best_score": round(best, 4),
            "average_score": round(average, 4),
            "document_count": len(documents),
            "reason": reason,
        }
