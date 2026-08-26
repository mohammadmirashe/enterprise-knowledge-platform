from __future__ import annotations

import json
import threading
from pathlib import Path
from langchain_core.documents import Document
from config import settings
from src.cleaner import TextCleaner
from src.splitter import DocumentSplitter
from src.embedding import EmbeddingModel
from src.vector_store import VectorStore

_lock = threading.Lock()
_embedding = None


def get_embedding():
    global _embedding
    if _embedding is None:
        _embedding = EmbeddingModel(
            settings.embedding_model,
            settings.embedding_device,
        ).get_model()
    return _embedding


def load_jsonl(path: Path) -> list[Document]:
    docs: list[Document] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        text = item.pop("text", "").strip()
        if text:
            docs.append(Document(page_content=text, metadata=item))
    return docs


def load_all() -> list[Document]:
    docs: list[Document] = []
    for path in settings.processed_dir.glob("*.jsonl"):
        docs.extend(load_jsonl(path))
    return docs


def _prepare(docs: list[Document]) -> list[Document]:
    cleaned = TextCleaner().clean(docs)
    return DocumentSplitter(settings.chunk_size, settings.chunk_overlap).split(cleaned)


def add_to_index(processed_path: Path) -> dict[str, int]:
    """Embed only the newly uploaded document and append it to FAISS."""
    with _lock:
        docs = load_jsonl(processed_path)
        chunks = _prepare(docs)
        if not chunks:
            return {"documents": 0, "chunks_added": 0}

        embedding = get_embedding()
        store = VectorStore(embedding)
        index_exists = (settings.vector_dir / "index.faiss").exists()

        if index_exists:
            db = store.load(settings.vector_dir)
            db.add_documents(chunks)
        else:
            db = store.build(chunks)

        store.save(db, settings.vector_dir)
        return {"documents": len(docs), "chunks_added": len(chunks)}


def rebuild_index() -> dict[str, int]:
    """Full rebuild, kept for maintenance and recovery."""
    with _lock:
        docs = load_all()
        chunks = _prepare(docs)
        if not chunks:
            return {"documents": 0, "chunks": 0}
        store = VectorStore(get_embedding())
        db = store.build(chunks)
        store.save(db, settings.vector_dir)
        return {"documents": len(docs), "chunks": len(chunks)}
