from pathlib import Path
import sys
import types

from app.capture_agent import evaluate, extract_document_fields, knowledge_graph, public_form_data
from app.database import (
    create_knowledge,
    init_db,
    list_documents,
    map_data,
    review_knowledge,
)
from app.main import _index_published_knowledge
from config import settings


HR_DOCUMENT = """
فرایند درخواست مرخصی کارکنان از طریق سامانه منابع انسانی انجام می‌شود.
کارمند باید نوع مرخصی، تاریخ شروع و پایان و جانشین پیشنهادی را ثبت کند.
درخواست ابتدا برای مدیر مستقیم و سپس برای واحد منابع انسانی ارسال می‌شود.
در صورت تداخل با برنامه شیفت یا کمبود مانده مرخصی، درخواست نیازمند بررسی بیشتر است.
هدف این رویه کاهش خطای ثبت و شفاف شدن وضعیت تأیید درخواست‌ها است.
"""


def _set_temp_paths(tmp_path: Path):
    original = {
        "sqlite_path": settings.sqlite_path,
        "processed_dir": settings.processed_dir,
        "uploads_dir": settings.uploads_dir,
        "vector_dir": settings.vector_dir,
    }
    object.__setattr__(settings, "sqlite_path", tmp_path / "knowledge.db")
    object.__setattr__(settings, "processed_dir", tmp_path / "processed")
    object.__setattr__(settings, "uploads_dir", tmp_path / "uploads")
    object.__setattr__(settings, "vector_dir", tmp_path / "vector")
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    return original


def _restore_paths(original):
    for key, value in original.items():
        object.__setattr__(settings, key, value)


def test_document_only_flow_builds_general_hr_draft():
    data = extract_document_fields(HR_DOCUMENT, "HR_leave_process.docx", {})
    assert data["problem"]
    assert data["action_taken"]
    assert data["title"]
    assert data["evidence"]
    assert data["knowledge_type"] in {"procedure", "other"}

    data.update({"unit": "منابع انسانی", "owner_user_id": 4, "sensitivity": "internal"})
    evaluation = evaluate(data, attachments_count=1)
    assert evaluation["can_build_draft"] is True
    assert evaluation["ready_to_submit"] is True


def test_general_graph_is_not_equipment_dependent():
    graph = knowledge_graph(
        {
            "title": "فرایند مرخصی کارکنان",
            "knowledge_type": "procedure",
            "unit": "منابع انسانی",
            "problem": "ثبت و تأیید درخواست مرخصی",
            "action_taken": "ثبت درخواست و گردش تأیید در سامانه منابع انسانی",
            "result": "شفاف شدن وضعیت درخواست",
        }
    )
    relations = {edge["relation"] for edge in graph["edges"]}
    assert "COVERS_TOPIC" in relations
    assert "DESCRIBES" in relations
    assert "BELONGS_TO_UNIT" in relations
    assert "PRODUCES" in relations


def test_approval_populates_map_and_documents(tmp_path, monkeypatch):
    original = _set_temp_paths(tmp_path)
    try:
        data = extract_document_fields(HR_DOCUMENT, "HR_leave_process.docx", {})
        data.update(
            {
                "unit": "منابع انسانی",
                "owner_user_id": 4,
                "sensitivity": "internal",
                "domain_id": 5,
            }
        )
        evaluation = evaluate(data, attachments_count=1)
        public = public_form_data(data)
        knowledge_id, _ = create_knowledge(
            {
                **public,
                "structured_data": public,
                "content": "محتوای تست",
                "status": "pending_review",
                "quality_score": evaluation["quality_score"],
                "completeness_score": evaluation["essential_completion"],
                "evidence_score": evaluation["evidence_score"],
                "confidence_score": evaluation["confidence_score"],
            }
        )
        assert map_data()["knowledge"] == []

        status = review_knowledge(knowledge_id, "approve", "تأیید", 2)
        assert status == "published"
        mapped = map_data()
        assert any(item["id"] == knowledge_id for item in mapped["knowledge"])
        assert any(item["knowledge_id"] == knowledge_id for item in mapped["relations"])

        class FakeDocument:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata

        fake_documents = types.ModuleType("langchain_core.documents")
        fake_documents.Document = FakeDocument
        fake_langchain = types.ModuleType("langchain_core")
        fake_langchain.documents = fake_documents
        fake_indexing = types.ModuleType("app.indexing")
        fake_indexing.add_to_index = lambda destination: {"documents": 1, "chunks_added": 1}
        fake_service = types.ModuleType("app.service")
        fake_service.invalidate_vector_cache = lambda: None
        monkeypatch.setitem(sys.modules, "langchain_core", fake_langchain)
        monkeypatch.setitem(sys.modules, "langchain_core.documents", fake_documents)
        monkeypatch.setitem(sys.modules, "app.indexing", fake_indexing)
        monkeypatch.setitem(sys.modules, "app.service", fake_service)
        sys.modules.pop("app.ingestion", None)
        stats = _index_published_knowledge(knowledge_id)
        assert stats["chunks_added"] == 1
        documents = list_documents()
        assert any(
            item["knowledge_id"] == knowledge_id and item["category"] == "published_knowledge" for item in documents
        )
    finally:
        _restore_paths(original)
