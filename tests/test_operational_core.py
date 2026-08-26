from pathlib import Path

from app.capture_agent import evaluate, extract_fields, public_form_data
from app.database import (
    create_capture_session,
    create_knowledge,
    get_capture_session,
    get_knowledge,
    init_db,
    update_capture_session,
)
from app.pdf_export import make_pdf
from config import settings


RICH_CASE = (
    "بعد از تعمیر پمپ P-101 دمای یاتاقان به 92 درجه رسید. "
    "اندازه‌گیری نشان داد هم‌راستایی موتور و پمپ به هم خورده است. "
    "کوپلینگ را تنظیم کردیم و دما از 92 به 68 درجه کاهش یافت. "
    "پس از تعمیر باید هم‌راستایی کنترل شود."
)


def _temporary_database(tmp_path: Path):
    original = settings.sqlite_path
    object.__setattr__(settings, "sqlite_path", tmp_path / "knowledge_test.db")
    init_db()
    return original


def test_session_and_structured_form_persist(tmp_path):
    original = _temporary_database(tmp_path)
    try:
        session = create_capture_session("KC-TEST", 4, "fast")
        data = extract_fields([{"role": "user", "content": RICH_CASE}], {})
        evaluation = evaluate(data, mode="fast")
        update_capture_session(
            session["id"],
            form_data=data,
            completion_score=evaluation["essential_completion"],
            quality_score=evaluation["quality_score"],
            evidence_score=evaluation["evidence_score"],
            confidence_score=evaluation["confidence_score"],
        )
        restored = get_capture_session(session["id"])
        assert restored["form_data"]["equipment_tag"] == "P-101"
        assert "92" in restored["form_data"]["result"]
    finally:
        object.__setattr__(settings, "sqlite_path", original)


def test_knowledge_record_and_pdf_are_rebuildable(tmp_path):
    original = _temporary_database(tmp_path)
    try:
        data = extract_fields([{"role": "user", "content": RICH_CASE}], {})
        data.update({"unit": "تعمیرات مکانیک", "owner_user_id": 3, "sensitivity": "internal"})
        evaluation = evaluate(data, mode="fast")
        public = public_form_data(data)
        knowledge_id, _ = create_knowledge(
            {
                **public,
                "structured_data": public,
                "title": public["title"],
                "summary": public["summary"],
                "content": "content",
                "quality_score": evaluation["quality_score"],
                "completeness_score": evaluation["essential_completion"],
                "evidence_score": evaluation["evidence_score"],
                "confidence_score": evaluation["confidence_score"],
            }
        )
        knowledge = get_knowledge(knowledge_id)
        assert knowledge is not None
        assert knowledge["structured_data"]["action_taken"]
        pdf = make_pdf(knowledge)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 5000
    finally:
        object.__setattr__(settings, "sqlite_path", original)
