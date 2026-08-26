from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from PIL import Image

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def quality(text: str) -> float:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return 0.0
    valid = sum(ch.isalnum() or "\u0600" <= ch <= "\u06ff" for ch in compact)
    return round(100 * valid / len(compact), 1)


def ocr_image(path: Path, lang: str = "fas+eng") -> str:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("pytesseract is not installed") from exc
    return pytesseract.image_to_string(Image.open(path), lang=lang).strip()


def _extract_docx(path: Path) -> list[Document]:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise RuntimeError("python-docx is not installed") from exc
    document = DocxDocument(path)
    blocks: list[str] = []
    blocks.extend(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells]
            if any(values):
                blocks.append(" | ".join(values))
    text = "\n".join(blocks).strip()
    return (
        [
            Document(
                page_content=text,
                metadata={"source": path.name, "page": 1, "method": "docx", "quality_score": quality(text)},
            )
        ]
        if text
        else []
    )


def _extract_xlsx(path: Path) -> list[Document]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is not installed") from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    docs: list[Document] = []
    for index, sheet in enumerate(workbook.worksheets, start=1):
        lines: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            values = [str(value).strip() if value is not None else "" for value in row]
            if any(values):
                lines.append(" | ".join(values))
        text = "\n".join(lines).strip()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": path.name,
                        "page": index,
                        "sheet": sheet.title,
                        "method": "xlsx",
                        "quality_score": quality(text),
                    },
                )
            )
    workbook.close()
    return docs


def extract(path: Path) -> list[Document]:
    ext = path.suffix.lower()
    docs: list[Document] = []
    if ext == ".pdf":
        import fitz

        pdf = fitz.open(path)
        try:
            for idx, page in enumerate(pdf, start=1):
                text = page.get_text().strip()
                method = "direct_text"
                if not text:
                    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        temp = Path(tmp.name)
                    try:
                        pix.save(temp)
                        text = ocr_image(temp)
                    finally:
                        temp.unlink(missing_ok=True)
                    method = "ocr"
                if text:
                    docs.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": path.name,
                                "page": idx,
                                "method": method,
                                "quality_score": quality(text),
                            },
                        )
                    )
        finally:
            pdf.close()
    elif ext in IMAGE_EXT:
        text = ocr_image(path)
        if text:
            docs = [
                Document(
                    page_content=text,
                    metadata={"source": path.name, "page": 1, "method": "ocr", "quality_score": quality(text)},
                )
            ]
    elif ext in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            docs = [
                Document(
                    page_content=text,
                    metadata={"source": path.name, "page": 1, "method": "text", "quality_score": quality(text)},
                )
            ]
    elif ext == ".docx":
        docs = _extract_docx(path)
    elif ext == ".xlsx":
        docs = _extract_xlsx(path)
    elif ext == ".jsonl":
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                item = json.loads(line)
                text = str(item.get("text", "")).strip()
                if text:
                    docs.append(
                        Document(
                            page_content=text,
                            metadata={
                                **{key: value for key, value in item.items() if key != "text"},
                                "source": item.get("source", path.name),
                                "page": item.get("page", i),
                                "quality_score": quality(text),
                            },
                        )
                    )
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return [document for document in docs if document.page_content.strip()]


def save_jsonl(documents: Iterable[Document], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps({**document.metadata, "text": document.page_content}, ensure_ascii=False) + "\n")
