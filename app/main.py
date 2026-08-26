from __future__ import annotations

import json
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from config import settings
from app.capture_agent import (
    CaptureState,
    analyze_value,
    assistant_message,
    auto_metadata,
    build_content,
    evaluate,
    extract_document_fields,
    extract_fields,
    knowledge_graph,
    present,
    public_form_data,
)
from app.database import *
from app.pdf_export import make_pdf


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    if settings.demo_mode:
        from app.demo import seed_demo_data

        seed_demo_data()
    yield


app = FastAPI(title=settings.app_name, version="0.9.0", lifespan=lifespan)


class DomainIn(BaseModel):
    name: str
    parent_id: int | None = None
    owner_user_id: int | None = None
    review_days: int = 180
    access_level: str = "internal"


class CaptureSessionIn(BaseModel):
    user_id: int = 4
    mode: str = "fast"


class CaptureMessageIn(BaseModel):
    message: str


class CaptureFormIn(BaseModel):
    form_data: dict[str, Any]


class CaptureActionIn(BaseModel):
    action: str


class ReviewIn(BaseModel):
    decision: str
    comment: str = ""
    reviewer_user_id: int = 2
    field_comments: dict[str, Any] = Field(default_factory=dict)


class UpdateIn(BaseModel):
    data: dict[str, Any]
    change_reason: str = "ویرایش"


class ChatRequest(BaseModel):
    question: str


class GapIn(BaseModel):
    question: str
    domain_id: int | None = None
    assigned_expert_id: int | None = None
    priority: str = "medium"


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "version": "0.9.0", "demo_mode": settings.demo_mode}


@app.get("/demo/status")
def demo_status() -> dict[str, Any]:
    from app.demo import DEMO_QUESTIONS

    return {
        "enabled": settings.demo_mode,
        "sample_questions": DEMO_QUESTIONS if settings.demo_mode else [],
        "external_ai_required": not settings.demo_mode,
        "answer_engine": "local_grounded_demo" if settings.demo_mode else "configured_rag",
    }


@app.get("/users")
def users() -> list[dict[str, Any]]:
    return list_users()


@app.get("/domains")
def domains() -> list[dict[str, Any]]:
    return list_domains()


@app.post("/domains")
def domains_create(payload: DomainIn) -> dict[str, int]:
    return {"id": create_domain(payload.model_dump())}


@app.get("/knowledge")
def knowledge(status: str | None = None) -> list[dict[str, Any]]:
    return list_knowledge(status)


@app.get("/knowledge/{knowledge_id}")
def knowledge_get(knowledge_id: int) -> dict[str, Any]:
    item = get_knowledge(knowledge_id)
    if not item:
        raise HTTPException(404, "دانش یافت نشد")
    return item


@app.patch("/knowledge/{knowledge_id}")
def knowledge_update(knowledge_id: int, payload: UpdateIn) -> dict[str, Any]:
    structured = payload.data.get("structured_data", payload.data)
    evaluation = evaluate(structured)
    update_payload = {
        **payload.data,
        "quality_score": evaluation["quality_score"],
        "completeness_score": evaluation["essential_completion"],
        "evidence_score": evaluation["evidence_score"],
        "confidence_score": evaluation["confidence_score"],
        "content": build_content(structured),
    }
    item = update_knowledge(knowledge_id, update_payload, 1, payload.change_reason)
    if not item:
        raise HTTPException(404, "دانش یافت نشد")
    return item


@app.post("/knowledge/{knowledge_id}/submit")
def submit(knowledge_id: int) -> dict[str, bool]:
    item = get_knowledge(knowledge_id)
    if not item:
        raise HTTPException(404, "دانش یافت نشد")
    evaluation = evaluate(item["structured_data"])
    if not evaluation["ready_to_submit"]:
        raise HTTPException(
            422,
            {
                "message": "برای ارسال به بازبینی، فیلدهای حاکمیتی ضروری باید تکمیل شوند.",
                "missing": evaluation["missing_required_fields"],
                "missing_labels": evaluation["missing_required_labels"],
            },
        )
    submit_knowledge(knowledge_id)
    return {"ok": True}


def _index_published_knowledge(knowledge_id: int) -> dict[str, Any]:
    """Register approved knowledge as documents, then attempt RAG indexing.

    Registration uses only the standard library. Therefore missing LangChain,
    embedding models or FAISS cannot prevent the item from entering Documents.
    """
    item = get_knowledge(knowledge_id)
    if not item:
        return {"documents": 0, "chunks_added": 0}

    attachment_document_ids: list[int] = []
    for attachment in item.get("attachments", []):
        attachment_document_ids.append(
            add_document(
                attachment.get("filename") or Path(attachment["stored_path"]).name,
                attachment["stored_path"],
                attachment.get("mime_type"),
                attachment.get("category") or "evidence",
                item.get("tags", ""),
                "linked_to_published_knowledge",
                0,
                0,
                knowledge_id,
            )
        )

    text = "\n\n".join(
        part for part in (item.get("title", ""), item.get("summary", ""), item.get("content", "")) if part
    )
    if not text.strip():
        return {"documents": len(attachment_document_ids), "chunks_added": 0}

    metadata = {
        "source": f"knowledge_{knowledge_id}",
        "knowledge_id": knowledge_id,
        "title": item.get("title"),
        "status": item.get("status"),
        "sensitivity": item.get("sensitivity"),
        "knowledge_type": item.get("knowledge_type"),
        "unit": item.get("unit"),
        "page": 1,
        "quality_score": item.get("quality_score", 0),
    }
    destination = settings.processed_dir / f"knowledge_{knowledge_id}.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({**metadata, "text": text}, ensure_ascii=False) + "\n", encoding="utf-8")

    generated_document_id = add_document(
        f"knowledge_{knowledge_id}_v{item['version']}.jsonl",
        str(destination),
        "application/x-ndjson",
        "published_knowledge",
        item.get("tags", ""),
        "pending_index",
        1,
        float(item.get("quality_score", 0) or 0),
        knowledge_id,
    )

    if settings.demo_mode:
        update_document_status(generated_document_id, "demo_ready")
        return {
            "documents": 1,
            "chunks_added": 1,
            "document_id": generated_document_id,
            "linked_attachments": len(attachment_document_ids),
            "demo": True,
        }

    try:
        from app.indexing import add_to_index
        from app.service import invalidate_vector_cache

        stats = add_to_index(destination)
        update_document_status(generated_document_id, "indexed")
        invalidate_vector_cache()
        return {
            **stats,
            "document_id": generated_document_id,
            "linked_attachments": len(attachment_document_ids),
        }
    except Exception:
        update_document_status(generated_document_id, "index_failed")
        raise


@app.post("/knowledge/{knowledge_id}/review")
def review(knowledge_id: int, payload: ReviewIn) -> dict[str, Any]:
    if not get_knowledge(knowledge_id):
        raise HTTPException(404, "دانش یافت نشد")
    status = review_knowledge(
        knowledge_id,
        payload.decision,
        payload.comment,
        payload.reviewer_user_id,
        payload.field_comments,
    )
    index_stats = None
    if status == "published":
        try:
            index_stats = _index_published_knowledge(knowledge_id)
        except Exception as exc:
            # Publication must not be rolled back because local embedding dependencies are unavailable.
            audit("INDEX_FAILED", "knowledge", knowledge_id, str(exc), payload.reviewer_user_id)
            index_stats = {"error": str(exc)}
    return {"ok": True, "status": status, "index": index_stats}


@app.get("/knowledge/{knowledge_id}/pdf")
def pdf(knowledge_id: int) -> Response:
    item = get_knowledge(knowledge_id)
    if not item:
        raise HTTPException(404, "دانش یافت نشد")
    return Response(
        make_pdf(item),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="knowledge_{knowledge_id}_v{item["version"]}.pdf"'},
    )


@app.post("/knowledge-capture/sessions")
def new_session(payload: CaptureSessionIn) -> dict[str, Any]:
    session_id = "KC-" + uuid.uuid4().hex[:12].upper()
    return create_capture_session(session_id, payload.user_id, payload.mode)


@app.get("/knowledge-capture/sessions/{session_id}")
def session(session_id: str) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    return item


@app.patch("/knowledge-capture/sessions/{session_id}/form")
def session_form(session_id: str, payload: CaptureFormIn) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    form_data = {**item["form_data"], **payload.form_data}
    # Recompute generated metadata only when still empty; manual edits are preserved.
    form_data.update(auto_metadata(form_data))
    evaluation = evaluate(
        form_data,
        attachments_count=len(item.get("attachments", [])),
        mode=item.get("mode", "fast"),
        question_count=int(item.get("question_count", 0)),
    )
    return (
        update_capture_session(
            session_id,
            form_data=form_data,
            missing_fields=evaluation["missing_required_fields"],
            completion_score=evaluation["essential_completion"],
            quality_score=evaluation["quality_score"],
            evidence_score=evaluation["evidence_score"],
            confidence_score=evaluation["confidence_score"],
            state=evaluation["state"],
            status="ready" if evaluation["can_build_draft"] else "collecting",
        )
        or {}
    )


def _previous_assistant_asked(conversation: list[dict[str, Any]], field: str) -> bool:
    for message in reversed(conversation):
        if message.get("role") == "assistant":
            return message.get("asked_field") == field
    return False


@app.post("/knowledge-capture/sessions/{session_id}/messages")
def session_message(session_id: str, payload: CaptureMessageIn) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    message = payload.message.strip()
    if not message:
        raise HTTPException(422, "پیام خالی است")

    form_data = dict(item["form_data"])
    conversation = item["conversation"] + [{"role": "user", "content": message}]

    # Explicit conflict clarification has priority over normal extraction.
    active_conflict = form_data.get("_active_conflict") or {}
    conflict_field = active_conflict.get("field")
    if conflict_field and _previous_assistant_asked(item["conversation"], conflict_field):
        form_data[conflict_field] = message
        if conflict_field == "root_cause":
            form_data["root_cause_status"] = "confirmed"
        form_data.setdefault("_field_confidence", {})[conflict_field] = 0.98
        form_data.pop("_active_conflict", None)
        extracted = {conflict_field: message}
        if conflict_field == "root_cause":
            extracted["root_cause_status"] = "confirmed"
    else:
        extracted = extract_fields(conversation, form_data)
        if extracted.get("_conflict"):
            form_data["_active_conflict"] = extracted["_conflict"]
        for key, value in extracted.items():
            if key == "_conflict":
                continue
            if key.startswith("_"):
                if isinstance(value, dict):
                    form_data[key] = {**form_data.get(key, {}), **value}
                else:
                    form_data[key] = value
            else:
                form_data[key] = value

    question_count = int(item.get("question_count", 0))
    evaluation = evaluate(
        form_data,
        attachments_count=len(item.get("attachments", [])),
        mode=item.get("mode", "fast"),
        question_count=question_count,
    )
    assistant_text = assistant_message(evaluation, extracted, form_data)
    asked_field = evaluation.get("next_field")
    if asked_field:
        question_count += 1
    conversation.append(
        {
            "role": "assistant",
            "content": assistant_text,
            "asked_field": asked_field,
            "question_type": evaluation.get("question_type", "text"),
            "state": evaluation["state"],
        }
    )
    updated = update_capture_session(
        session_id,
        form_data=form_data,
        conversation=conversation,
        missing_fields=evaluation["missing_required_fields"],
        completion_score=evaluation["essential_completion"],
        quality_score=evaluation["quality_score"],
        evidence_score=evaluation["evidence_score"],
        confidence_score=evaluation["confidence_score"],
        question_count=question_count,
        state=evaluation["state"],
        status="ready" if evaluation["can_build_draft"] else "collecting",
    )
    return {"assistant_message": assistant_text, "extracted_fields": extracted, "session": updated, **evaluation}


@app.post("/knowledge-capture/sessions/{session_id}/actions")
def session_action(session_id: str, payload: CaptureActionIn) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    if payload.action == "continue_expert":
        evaluation = evaluate(
            item["form_data"],
            attachments_count=len(item.get("attachments", [])),
            mode="expert",
            question_count=int(item.get("question_count", 0)),
        )
        conversation = list(item.get("conversation", []))
        question_count = int(item.get("question_count", 0))
        if evaluation.get("next_question"):
            text = assistant_message(evaluation, {}, item["form_data"])
            conversation.append(
                {
                    "role": "assistant",
                    "content": text,
                    "asked_field": evaluation.get("next_field"),
                    "question_type": evaluation.get("question_type", "text"),
                    "state": evaluation["state"],
                }
            )
            question_count += 1
        return (
            update_capture_session(
                session_id,
                mode="expert",
                max_questions=12,
                question_count=question_count,
                conversation=conversation,
                state=CaptureState.EXPERT_ENRICHMENT.value,
                status="collecting",
            )
            or {}
        )
    if payload.action == "switch_fast":
        return (
            update_capture_session(
                session_id,
                mode="fast",
                max_questions=3,
                state=CaptureState.DRAFT_READY.value,
            )
            or {}
        )
    if payload.action == "prepare_draft":
        evaluation = evaluate(
            item["form_data"], len(item.get("attachments", [])), item.get("mode", "fast"), item.get("question_count", 0)
        )
        if not evaluation["can_build_draft"]:
            raise HTTPException(
                422,
                {
                    "message": "موضوع و شرح اصلی دانش هنوز برای ساخت پیش‌نویس کافی نیست.",
                    "missing": evaluation["missing_required_fields"],
                },
            )
        return update_capture_session(session_id, state=CaptureState.DRAFT_READY.value, status="ready") or {}
    raise HTTPException(422, "action نامعتبر است")


@app.post("/knowledge-capture/sessions/{session_id}/validate")
def validate(session_id: str) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    evaluation = evaluate(
        item["form_data"],
        attachments_count=len(item.get("attachments", [])),
        mode=item.get("mode", "fast"),
        question_count=int(item.get("question_count", 0)),
    )
    return {
        **evaluation,
        "knowledge_graph": knowledge_graph(item["form_data"]),
        "knowledge_value": analyze_value(item["form_data"]),
        "mode": item.get("mode", "fast"),
        "question_count": item.get("question_count", 0),
        "max_questions": item.get("max_questions", 3),
    }


@app.get("/knowledge-capture/sessions/{session_id}/pdf")
def session_pdf(session_id: str) -> Response:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    data = public_form_data(item["form_data"])
    evaluation = evaluate(
        item["form_data"],
        attachments_count=len(item.get("attachments", [])),
        mode=item.get("mode", "fast"),
        question_count=int(item.get("question_count", 0)),
    )
    preview = {
        "id": session_id,
        "title": data.get("title") or "پیش‌نمایش فرم دانش",
        "summary": data.get("summary", ""),
        "structured_data": data,
        "version": 0,
        "status": "preview",
        "unit": data.get("unit", ""),
        "equipment_tag": data.get("equipment_tag", ""),
        "owner_text": data.get("owner_text", ""),
        "sensitivity": data.get("sensitivity", ""),
        "completeness_score": evaluation.get("completeness_score", 0),
        "quality_score": evaluation.get("quality_score", 0),
        "evidence_score": evaluation.get("evidence_score", 0),
        "attachments": item.get("attachments", []),
        "reviews": [],
    }
    return Response(
        make_pdf(preview),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="knowledge_preview_{session_id}.pdf"'},
    )


@app.post("/knowledge-capture/sessions/{session_id}/confirm")
def confirm(session_id: str) -> dict[str, Any]:
    item = get_capture_session(session_id)
    if not item:
        raise HTTPException(404, "نشست یافت نشد")
    evaluation = evaluate(
        item["form_data"],
        attachments_count=len(item.get("attachments", [])),
        mode=item.get("mode", "fast"),
        question_count=int(item.get("question_count", 0)),
    )
    if not evaluation["can_build_draft"]:
        raise HTTPException(422, {"missing": evaluation["missing_required_fields"]})
    data = public_form_data(item["form_data"])
    payload = {
        **data,
        "structured_data": data,
        "content": build_content(data),
        "status": "draft",
        "quality_score": evaluation["quality_score"],
        "completeness_score": evaluation["essential_completion"],
        "evidence_score": evaluation["evidence_score"],
        "confidence_score": evaluation["confidence_score"],
    }
    knowledge_id, quality = create_knowledge(payload, item.get("user_id") or 4)
    bind_session_attachments(session_id, knowledge_id)
    update_capture_session(
        session_id,
        status="saved_as_draft",
        state=CaptureState.SAVED.value,
        knowledge_id=knowledge_id,
    )
    return {
        "knowledge_id": knowledge_id,
        "quality_score": quality,
        "completeness_score": evaluation["essential_completion"],
        "ready_to_submit": evaluation["ready_to_submit"],
        "missing_required_labels": evaluation["missing_required_labels"],
    }


ALLOWED_UPLOADS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".docx", ".xlsx"}


@app.post("/attachments/upload")
def attachment_upload(
    file: UploadFile = File(...),
    knowledge_id: int | None = Form(None),
    session_id: str | None = Form(None),
    category: str = Form("evidence"),
) -> dict[str, Any]:
    if not knowledge_id and not session_id:
        raise HTTPException(422, "knowledge_id یا session_id الزامی است")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOADS:
        raise HTTPException(415, f"نوع فایل {suffix or 'نامشخص'} پشتیبانی نمی‌شود")
    stored = settings.uploads_dir / f"{uuid.uuid4().hex}{suffix}"
    with stored.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    attachment_id = add_attachment(
        file.filename or stored.name, str(stored), file.content_type, knowledge_id, session_id, category
    )

    extracted_field_names: list[str] = []
    extraction_error: str | None = None
    if session_id:
        item = get_capture_session(session_id)
        if item:
            form_data = dict(item["form_data"])
            filenames = [attachment["filename"] for attachment in list_session_attachments(session_id)]
            form_data["evidence"] = "فایل‌های پیوست‌شده و تحلیل‌شده: " + "، ".join(filenames)
            try:
                from app.ingestion import extract

                documents = extract(stored)
                document_text = "\n\n".join(
                    document.page_content for document in documents if document.page_content.strip()
                )
                if document_text.strip():
                    extracted = extract_document_fields(document_text, file.filename or stored.name, form_data)
                    for key, value in extracted.items():
                        if key.startswith("_"):
                            if isinstance(value, dict):
                                form_data[key] = {**form_data.get(key, {}), **value}
                            continue
                        # Preserve explicit user edits; fill missing fields and always refresh source metadata.
                        if not present(form_data.get(key)) or key in {"evidence", "source_filename"}:
                            form_data[key] = value
                            extracted_field_names.append(key)
                    form_data.update(auto_metadata(form_data))
                else:
                    extraction_error = "متن قابل استخراجی در سند یافت نشد؛ فایل همچنان به دانش متصل شد."
            except Exception as exc:
                extraction_error = str(exc)

            # A file-only submission must still be able to enter the workflow even
            # when OCR/text extraction is unavailable. Use transparent placeholders
            # tied to the attached filename; the reviewer can inspect the original.
            if not present(form_data.get("problem")) or not present(form_data.get("action_taken")):
                fallback = extract_document_fields("", file.filename or stored.name, form_data)
                for key, value in fallback.items():
                    if key.startswith("_"):
                        continue
                    if not present(form_data.get(key)) or key in {"evidence", "source_filename"}:
                        form_data[key] = value
                        extracted_field_names.append(key)
                form_data.update(auto_metadata(form_data))

            evaluation = evaluate(
                form_data,
                attachments_count=len(list_session_attachments(session_id)),
                mode=item.get("mode", "fast"),
                question_count=int(item.get("question_count", 0)),
            )
            update_capture_session(
                session_id,
                form_data=form_data,
                missing_fields=evaluation["missing_required_fields"],
                completion_score=evaluation["essential_completion"],
                quality_score=evaluation["quality_score"],
                evidence_score=evaluation["evidence_score"],
                confidence_score=evaluation["confidence_score"],
                state=evaluation["state"],
                status="ready" if evaluation["can_build_draft"] else "collecting",
            )
    return {
        "id": attachment_id,
        "filename": file.filename,
        "extracted_fields": sorted(set(extracted_field_names)),
        "extraction_error": extraction_error,
    }


@app.get("/attachments/{attachment_id}/download")
def attachment_download(attachment_id: int) -> FileResponse:
    attachment = one("SELECT * FROM attachments WHERE id=?", (attachment_id,))
    if not attachment:
        raise HTTPException(404, "پیوست یافت نشد")
    return FileResponse(attachment["stored_path"], filename=attachment["filename"], media_type=attachment["mime_type"])


@app.get("/knowledge-map")
def knowledge_map() -> dict[str, Any]:
    return map_data()


@app.get("/dashboard")
def dash() -> dict[str, Any]:
    return dashboard()


@app.get("/audit")
def audit_events() -> list[dict[str, Any]]:
    return list_audit()


@app.get("/gaps")
def gaps() -> list[dict[str, Any]]:
    return list_gaps()


@app.post("/gaps")
def gap(payload: GapIn) -> dict[str, int]:
    return {"id": create_gap(payload.model_dump())}


@app.get("/documents")
def documents() -> list[dict[str, Any]]:
    return list_documents()


@app.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    tags: str = Form(""),
    knowledge_id: int | None = Form(None),
) -> dict[str, Any]:
    from app.ingestion import extract, save_jsonl
    from app.indexing import add_to_index
    from app.service import invalidate_vector_cache

    suffix = Path(file.filename or "").suffix.lower()
    stored = settings.uploads_dir / f"{uuid.uuid4().hex}{suffix}"
    with stored.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    extracted_documents = extract(stored)
    for document in extracted_documents:
        document.metadata.update(
            {"original_filename": file.filename, "category": category, "tags": tags, "knowledge_id": knowledge_id}
        )
    processed = settings.processed_dir / f"{stored.stem}.jsonl"
    save_jsonl(extracted_documents, processed)
    average_quality = (
        sum(float(document.metadata.get("quality_score", 0)) for document in extracted_documents)
        / len(extracted_documents)
        if extracted_documents
        else 0
    )
    document_id = add_document(
        file.filename or stored.name,
        str(stored),
        file.content_type,
        category,
        tags,
        "indexed",
        len(extracted_documents),
        average_quality,
        knowledge_id,
    )
    stats = add_to_index(processed)
    invalidate_vector_cache()
    return {"id": document_id, "pages": len(extracted_documents), "index": stats}


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    if settings.demo_mode:
        from app.demo import demo_chat

        return demo_chat(payload.question)
    try:
        from app.service import ask

        answer, documents, relevance = ask(payload.question)
        sources = [
            {
                "source": document.metadata.get("source"),
                "knowledge_id": document.metadata.get("knowledge_id"),
                "page": document.metadata.get("page"),
                "score": document.metadata.get("relevance_score"),
                "excerpt": document.page_content[:350],
            }
            for document in documents
        ]
        best_score = float(relevance.get("best_score", 0.0))
        if not documents or best_score < 0.25:
            gap_id = create_gap({"question": payload.question})
            return {
                "answer": "منبع معتبر کافی یافت نشد. پرسش به‌عنوان شکاف دانشی ثبت شد.",
                "sources": [],
                "gap_id": gap_id,
                "relevance": relevance,
            }
        return {"answer": answer, "sources": sources, "relevance": relevance}
    except (FileNotFoundError, RuntimeError) as exc:
        # Technical configuration errors are not knowledge gaps.
        raise HTTPException(503, f"سرویس پاسخ‌گویی آماده نیست: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"خطای فنی در سرویس پاسخ‌گویی: {exc}") from exc
