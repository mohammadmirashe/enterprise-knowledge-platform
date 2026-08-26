from __future__ import annotations

import re
from copy import deepcopy

from langchain_core.documents import Document


class TextCleaner:
    def clean(self, documents: list[Document]) -> list[Document]:
        cleaned: list[Document] = []
        for document in documents:
            text = document.page_content.replace("\u200c", " ")
            text = re.sub(r"\r\n?", "\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if not text:
                continue
            copied = deepcopy(document)
            copied.page_content = text
            cleaned.append(copied)
        return cleaned
