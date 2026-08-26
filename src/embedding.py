from __future__ import annotations

from langchain_huggingface import HuggingFaceEmbeddings


class EmbeddingModel:
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self._embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )

    def get_model(self) -> HuggingFaceEmbeddings:
        return self._embedding
