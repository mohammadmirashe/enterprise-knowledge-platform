from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Enterprise Knowledge Platform")
    api_key: str = os.getenv("AVALAI_API_KEY", "").strip()
    base_url: str = os.getenv("AVALAI_BASE_URL", "https://api.avalai.ir/v1").strip()
    model: str = os.getenv("AVALAI_MODEL", "gpt-4o-mini").strip()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    chunk_size: int = env_int("CHUNK_SIZE", 700)
    chunk_overlap: int = env_int("CHUNK_OVERLAP", 150)
    fetch_k: int = env_int("RETRIEVER_FETCH_K", 12)
    final_k: int = env_int("RETRIEVER_FINAL_K", 5)
    min_score: float = env_float("RETRIEVER_MIN_SCORE", 0.30)
    demo_mode: bool = env_bool("DEMO_MODE", False)
    uploads_dir: Path = env_path("UPLOADS_DIR", BASE_DIR / "data/uploads")
    processed_dir: Path = env_path("PROCESSED_DIR", BASE_DIR / "data/processed")
    vector_dir: Path = env_path("VECTOR_DIR", BASE_DIR / "storage/vector_db")
    sqlite_path: Path = env_path("SQLITE_PATH", BASE_DIR / "storage/knowledge.db")


settings = Settings()
