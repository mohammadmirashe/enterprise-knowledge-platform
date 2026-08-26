from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class VectorStore:
    def __init__(self, embedding) -> None:
        self.embedding = embedding

    def build(self, chunks: list[Document]) -> FAISS:
        if not chunks:
            raise ValueError("Cannot build a vector database from an empty chunk list.")
        return FAISS.from_documents(chunks, self.embedding)

    @staticmethod
    def save(db: FAISS, path: str | Path) -> None:
        destination = Path(path)
        destination.mkdir(parents=True, exist_ok=True)
        db.save_local(str(destination))

    def load(self, path: str | Path) -> FAISS:
        source = Path(path)
        if not (source / "index.faiss").exists() or not (source / "index.pkl").exists():
            raise FileNotFoundError(f"FAISS index is incomplete at {source}. Run: python build_index.py")
        return FAISS.load_local(
            str(source),
            self.embedding,
            allow_dangerous_deserialization=True,
        )
