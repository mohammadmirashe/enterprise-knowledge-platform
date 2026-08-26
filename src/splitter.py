from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentSplitter:
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 150) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "، ", " ", ""],
        )

    def split(self, documents: list[Document]) -> list[Document]:
        chunks = self.splitter.split_documents(documents)
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = index
        return chunks
