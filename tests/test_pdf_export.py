from __future__ import annotations

import fitz
import unicodedata

from app.pdf_export import make_pdf


def sample_knowledge() -> dict:
    return {
        "id": "KC-TEST-001",
        "title": "رفع افزایش دمای یاتاقان پمپ P-101 با اصلاح هم‌راستایی",
        "version": 1,
        "status": "preview",
        "unit": "تعمیرات مکانیک",
        "equipment_tag": "P-101",
        "owner_text": "سرپرست تعمیرات مکانیک",
        "sensitivity": "internal",
        "completeness_score": 83,
        "quality_score": 78,
        "evidence_score": 65,
        "structured_data": {
            "summary": "در اولین راه‌اندازی پس از تعمیرات، دمای یاتاقان افزایش یافت و پس از اصلاح هم‌راستایی به مقدار عادی بازگشت.",
            "problem": "دمای یاتاقان از 68 به 92 درجه رسید و لرزش تجهیز افزایش یافت.",
            "occurrence_conditions": "اولین راه‌اندازی پس از تعمیرات",
            "root_cause": "عدم هم‌راستایی موتور و پمپ",
            "action_taken": "اجرای LOTO، کنترل پایه‌ها و اصلاح هم‌راستایی",
            "result": "کاهش دما از 92 به 68 درجه و بازگشت لرزش به محدوده مجاز",
            "lesson_learned": "هم‌راستایی پس از تعمیر باید کنترل و مستند شود.",
            "tags": "P-101، یاتاقان، هم‌راستایی، لرزش، LOTO",
        },
        "attachments": [{"filename": "P101_Alignment_Report.pdf", "category": "گزارش فنی"}],
        "reviews": [],
    }


def test_pdf_is_valid_and_has_visible_content():
    pdf = make_pdf(sample_knowledge())
    assert pdf.startswith(b"%PDF")
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert 1 <= doc.page_count <= 4
    # The document must contain a meaningful amount of searchable text and
    # no practically empty trailing page.
    page_text_lengths = [len(page.get_text().strip()) for page in doc]
    all_text = unicodedata.normalize("NFKC", "\n".join(page.get_text() for page in doc))
    assert sum(page_text_lengths) > 150
    assert min(page_text_lengths) > 10
    for expected in ("درس", "هم", "P-101", "92", "68", "P101_Alignment_Report.pdf"):
        assert expected in all_text
    doc.close()
