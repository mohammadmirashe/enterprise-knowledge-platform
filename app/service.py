from __future__ import annotations

import threading
from collections.abc import Iterator
from config import settings
from app.indexing import get_embedding
from src.vector_store import VectorStore
from src.retriever import Retriever
from src.llm import AvalAILLM
from src.prompt import PromptBuilder

_lock = threading.RLock()
_cached_db = None
_cached_index_mtime = None
_cached_llm = None


def invalidate_vector_cache() -> None:
    global _cached_db, _cached_index_mtime
    with _lock:
        _cached_db = None
        _cached_index_mtime = None


def get_db():
    global _cached_db, _cached_index_mtime
    index_path = settings.vector_dir / "index.faiss"
    if not index_path.exists():
        raise FileNotFoundError("هنوز هیچ سندی ایندکس نشده است.")
    mtime = index_path.stat().st_mtime_ns
    with _lock:
        if _cached_db is None or _cached_index_mtime != mtime:
            _cached_db = VectorStore(get_embedding()).load(settings.vector_dir)
            _cached_index_mtime = mtime
        return _cached_db


def get_llm() -> AvalAILLM:
    global _cached_llm
    if not settings.api_key:
        raise RuntimeError("AVALAI_API_KEY is not configured")
    with _lock:
        if _cached_llm is None:
            _cached_llm = AvalAILLM(settings.api_key, settings.model, settings.base_url)
        return _cached_llm


def prepare(question: str):
    db = get_db()
    retriever = Retriever(db, settings.fetch_k, settings.final_k, settings.min_score)
    docs = retriever.retrieve(question)
    relevance = retriever.analyze_relevance(docs)
    prompt = PromptBuilder.build(question, docs, relevance, "")
    return prompt, docs, relevance


def ask(question: str):
    prompt, docs, relevance = prepare(question)
    return get_llm().generate(prompt), docs, relevance


def ask_stream(question: str) -> tuple[Iterator[str], list, dict]:
    prompt, docs, relevance = prepare(question)
    return get_llm().stream(prompt), docs, relevance
