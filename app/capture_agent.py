from __future__ import annotations

import json
import re
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any

from config import settings


class CaptureState(str, Enum):
    NEW = "new"
    EXTRACTING = "extracting"
    CLARIFYING_CONFLICT = "clarifying_conflict"
    COLLECTING_REQUIRED = "collecting_required"
    DRAFT_READY = "draft_ready"
    EXPERT_ENRICHMENT = "expert_enrichment"  # legacy compatibility
    READY_TO_SUBMIT = "ready_to_submit"
    SAVED = "saved"


# The keys remain backward compatible with older records, but their labels and
# semantics are deliberately organization-wide rather than maintenance-specific.
FORM_SCHEMA: dict[str, dict[str, Any]] = {
    "knowledge_type": {
        "label": "نوع دانش",
        "required": True,
        "weight": 5,
        "priority": 5,
        "source": "generated",
        "options": [
            "lesson_learned",
            "procedure",
            "technical_guide",
            "policy",
            "decision_record",
            "report",
            "faq",
            "reference",
            "other",
        ],
    },
    "problem": {
        "label": "موضوع، نیاز یا وضعیت",
        "required": True,
        "weight": 20,
        "priority": 10,
        "source": "extract",
    },
    "occurrence_conditions": {
        "label": "زمینه و شرایط کاربرد",
        "required": False,
        "weight": 5,
        "priority": 50,
        "source": "extract",
    },
    "symptoms": {
        "label": "داده‌ها، نشانه‌ها یا ورودی‌های مرتبط",
        "required": False,
        "weight": 5,
        "priority": 55,
        "source": "extract",
    },
    "equipment_tag": {
        "label": "شناسه تجهیز، سامانه یا دارایی",
        "required": False,
        "weight": 2,
        "priority": 70,
        "source": "extract",
    },
    "initial_hypothesis": {
        "label": "فرضیات یا گزینه‌های اولیه",
        "required": False,
        "weight": 3,
        "priority": 65,
        "source": "extract",
    },
    "investigation_steps": {
        "label": "بررسی‌ها، تحلیل‌ها یا منابع استفاده‌شده",
        "required": False,
        "weight": 5,
        "priority": 60,
        "source": "extract",
    },
    "root_cause": {
        "label": "علت، منطق یا مبنای تصمیم",
        "required": False,
        "weight": 6,
        "priority": 45,
        "source": "extract",
    },
    "root_cause_status": {
        "label": "وضعیت اعتبار تحلیل",
        "required": False,
        "weight": 2,
        "priority": 75,
        "source": "infer",
    },
    "action_taken": {
        "label": "شرح دانش، راهکار یا روش اصلی",
        "required": True,
        "weight": 25,
        "priority": 15,
        "source": "extract",
    },
    "action_steps": {
        "label": "مراحل اجرا یا استفاده",
        "required": False,
        "weight": 6,
        "priority": 40,
        "source": "extract",
    },
    "verification": {
        "label": "روش کنترل، ارزیابی یا تأیید",
        "required": False,
        "weight": 4,
        "priority": 68,
        "source": "extract",
    },
    "result": {
        "label": "نتیجه، خروجی یا اثر",
        "required": False,
        "weight": 8,
        "priority": 35,
        "source": "extract",
    },
    "lesson_learned": {
        "label": "نکات کلیدی و توصیه‌ها",
        "required": False,
        "weight": 7,
        "priority": 38,
        "source": "extract",
    },
    "unit": {
        "label": "واحد سازمانی",
        "required": True,
        "weight": 8,
        "priority": 80,
        "source": "governance",
    },
    "owner_user_id": {
        "label": "مالک دانش",
        "required": True,
        "weight": 7,
        "priority": 82,
        "source": "governance",
    },
    "sensitivity": {
        "label": "سطح دسترسی",
        "required": True,
        "weight": 5,
        "priority": 84,
        "source": "governance",
        "options": ["internal", "restricted", "confidential"],
    },
    "evidence": {
        "label": "منابع و مستندات",
        "required": False,
        "weight": 5,
        "priority": 72,
        "source": "upload",
        "upload": True,
    },
    "safety_notes": {
        "label": "ریسک‌ها، کنترل‌ها و ملاحظات مهم",
        "required": False,
        "weight": 4,
        "priority": 74,
        "source": "extract",
    },
    "limitations": {
        "label": "محدودیت‌ها، استثناها و شرایط عدم کاربرد",
        "required": False,
        "weight": 4,
        "priority": 76,
        "source": "generated",
    },
    "project": {
        "label": "پروژه، فرایند یا سامانه مرتبط",
        "required": False,
        "weight": 3,
        "priority": 78,
        "source": "extract",
    },
    # Kept only so older records remain readable. They are not asked in the new UI.
    "first_check": {"label": "نقطه شروع پیشنهادی", "required": False, "weight": 1, "priority": 95, "source": "legacy"},
    "novice_mistake": {"label": "خطاهای رایج", "required": False, "weight": 1, "priority": 96, "source": "legacy"},
    "early_warning": {"label": "نشانه‌های هشدار", "required": False, "weight": 1, "priority": 97, "source": "legacy"},
    "transfer_message": {
        "label": "پیام انتقال دانش",
        "required": False,
        "weight": 2,
        "priority": 94,
        "source": "generated",
    },
    "title": {"label": "عنوان", "required": False, "weight": 3, "priority": 98, "source": "generated"},
    "summary": {"label": "خلاصه", "required": False, "weight": 3, "priority": 99, "source": "generated"},
    "tags": {"label": "برچسب‌ها", "required": False, "weight": 2, "priority": 100, "source": "generated"},
}

REQUIRED = [key for key, spec in FORM_SCHEMA.items() if spec["required"]]
DRAFT_CORE = ["problem", "action_taken"]
LABELS = {key: spec["label"] for key, spec in FORM_SCHEMA.items()}

QUESTIONS = {
    "problem": "موضوع یا نیاز اصلی این دانش چیست؟",
    "action_taken": "شرح اصلی دانش، روش یا راهکار چیست؟",
}

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٫", "0123456789.")
ACTION_VERBS = (
    "اصلاح",
    "تنظیم",
    "تعویض",
    "تمیز",
    "پاکسازی",
    "رفع",
    "تعمیر",
    "جایگزین",
    "طراحی",
    "پیاده‌سازی",
    "ایجاد",
    "تعریف",
    "ثبت",
    "محاسبه",
    "تحلیل",
    "تهیه",
    "ارسال",
    "تأیید",
    "تایید",
    "استخدام",
    "ارزیابی",
    "پرداخت",
    "گزارش",
    "برنامه‌ریزی",
    "پیکربندی",
    "نصب",
    "به‌روزرسانی",
    "به روزرسانی",
    "مستندسازی",
    "اجرا",
    "اعمال",
    "تدوین",
    "بازطراحی",
)
INVESTIGATION_MARKERS = (
    "بررسی",
    "اندازه‌گیری",
    "بازدید",
    "کنترل",
    "پایش",
    "آزمایش",
    "تست",
    "تحلیل",
    "مقایسه",
    "مصاحبه",
    "ممیزی",
    "ارزیابی",
    "مطالعه",
    "گزارش",
    "داده",
    "لاگ",
    "log",
)
RESULT_MARKERS = (
    "کاهش یافت",
    "افزایش یافت",
    "به حالت عادی",
    "برطرف شد",
    "بازگشت",
    "حذف شد",
    "پایدار شد",
    "منجر شد",
    "نتیجه",
    "خروجی",
    "بهبود یافت",
    "تکمیل شد",
    "تحویل شد",
    "تصویب شد",
    "موفق شد",
    "صرفه‌جویی",
    "کاهش هزینه",
    "افزایش درآمد",
    "کاهش زمان",
    "افزایش کیفیت",
)
CAUSE_MARKERS = (
    "مشخص شد",
    "نشان داد",
    "علت ریشه‌ای",
    "ناشی از",
    "به دلیل",
    "علت اصلی",
    "مبنای تصمیم",
    "دلیل",
    "بر اساس",
    "با توجه به",
    "ریشه",
    "عامل",
    "منطق",
)
HYPOTHESIS_MARKERS = ("فکر کردیم", "تصور کردیم", "احتمال دادیم", "فرض کردیم", "گمان کردیم", "گزینه اولیه")
LESSON_MARKERS = ("درس‌آموخته", "توصیه", "بهتر است", "باید", "ضروری است", "لازم است", "نکته کلیدی")
RISK_MARKERS = (
    "ایمنی",
    "ریسک",
    "خطر",
    "محرمانه",
    "کنترل دسترسی",
    "LOTO",
    "قفل‌گذاری",
    "PPE",
    "تعارض منافع",
    "انطباق",
    "قانون",
    "مقررات",
    "امنیت",
    "پشتیبان",
    "backup",
)
LIMIT_MARKERS = ("محدودیت", "استثنا", "قابل استفاده نیست", "فقط در", "به‌جز", "به جز", "در صورت", "مشروط به")

STOP_WORDS = {
    "این",
    "آن",
    "است",
    "هست",
    "بود",
    "شد",
    "شده",
    "برای",
    "از",
    "به",
    "در",
    "با",
    "که",
    "را",
    "یک",
    "و",
    "یا",
    "تا",
    "اگر",
    "اما",
    "هم",
    "نیز",
    "می",
    "شود",
    "کرد",
    "کرده",
    "دارد",
    "دارند",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "using",
    "use",
}


def present(value: Any) -> bool:
    return value not in (None, "", [], {}) and not (isinstance(value, str) and not value.strip())


def normalize(text: str) -> str:
    return (text or "").translate(PERSIAN_DIGITS).replace("ي", "ی").replace("ك", "ک")


def clean_sentence(text: str, limit: int = 1100) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip(" .،؛:\n")[:limit]


def sentences(text: str) -> list[str]:
    normalized = re.sub(r"[\r\n]+", " ", text or "")
    parts = re.split(r"(?<=[.!؟])\s+|[؛;]\s*", normalized)
    return [clean_sentence(part) for part in parts if clean_sentence(part)]


def last_asked(conversation: list[dict[str, Any]]) -> str | None:
    for message in reversed(conversation):
        if message.get("role") == "assistant" and message.get("asked_field"):
            return str(message["asked_field"])
    return None


def _join_unique(items: list[str], limit: int = 2400) -> str:
    unique: list[str] = []
    for item in items:
        value = clean_sentence(item)
        if value and value not in unique:
            unique.append(value)
    return "\n".join(unique)[:limit]


def _field_confidence(data: dict[str, Any], field: str, confidence: float) -> None:
    confidence_map = data.setdefault("_field_confidence", {})
    confidence_map[field] = max(float(confidence_map.get(field, 0)), round(confidence, 2))


def _source_span(data: dict[str, Any], field: str, sentence: str) -> None:
    spans = data.setdefault("_source_spans", {})
    spans[field] = clean_sentence(sentence, 500)


def _extract_numeric_result(text: str) -> tuple[str | None, float]:
    t = normalize(text)
    values = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*(?:درجه|سانتی.?گراد|°\s*c)", t, re.IGNORECASE)
    if len(values) >= 3 and any(marker in text for marker in RESULT_MARKERS):
        numeric = [float(value) for value in values]
        final = numeric[-1]
        peak = max(numeric[:-1])
        if peak != final:
            return f"کاهش دما از {peak:g} به {final:g} درجه سانتی‌گراد", 0.99
    pair = re.search(
        r"از\s*(?:مقدار\s*(?:عادی\s*)?(?:حدود\s*)?)?([0-9]+(?:\.[0-9]+)?)\s*"
        r"(?:درجه|سانتی.?گراد|°\s*c|درصد|٪|ساعت|روز|دقیقه|ریال|تومان)?\s*(?:به|تا)\s*"
        r"([0-9]+(?:\.[0-9]+)?)",
        t,
        re.IGNORECASE,
    )
    if pair:
        before, after = pair.group(1), pair.group(2)
        direction = "کاهش" if float(after) < float(before) else "افزایش"
        return f"{direction} مقدار از {before} به {after}", 0.94
    return None, 0.0


def _extract_tag(text: str) -> str | None:
    match = re.search(r"\b([A-Za-z]{1,12}[-_/]?\d{1,12})\b", text or "")
    return match.group(1).upper() if match else None


def _semantic_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", normalize(text).lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def semantically_similar(a: str, b: str) -> bool:
    ta, tb = _semantic_tokens(a), _semantic_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / max(1, min(len(ta), len(tb))) >= 0.45


def classify_knowledge_type(text: str, filename: str = "") -> str:
    joined = f"{filename} {text}".lower()
    if any(x in joined for x in ("سیاست", "policy", "آیین نامه", "آیین‌نامه", "دستورالعمل سازمانی")):
        return "policy"
    if any(x in joined for x in ("صورتجلسه", "تصمیم", "مصوبه", "decision", "تصمیم‌گیری")):
        return "decision_record"
    if any(x in joined for x in ("گزارش", "report", "تحلیل عملکرد", "داشبورد")):
        return "report"
    if any(x in joined for x in ("سؤال", "پرسش", "faq", "پاسخ")):
        return "faq"
    if any(x in joined for x in ("مراحل", "فرایند", "فرآیند", "روش اجرا", "procedure", "رویه")):
        return "procedure"
    if any(x in joined for x in ("کد", "api", "پایتون", "python", "نصب", "پیکربندی", "خطای نرم‌افزار")):
        return "technical_guide"
    if any(x in joined for x in ("درس‌آموخته", "تجربه", "مشکل", "رفع", "بهبود")):
        return "lesson_learned"
    if any(x in joined for x in ("مرجع", "reference", "استاندارد", "راهنما")):
        return "reference"
    return "other"


def _answer_is_compatible(field: str, answer: str) -> bool:
    value = clean_sentence(answer)
    if not value or value in {"نمی‌دانم", "نامشخص", "اطلاعی ندارم"}:
        return False
    if field == "sensitivity":
        return any(x in value for x in ("داخلی", "محدود", "محرمانه", "internal", "restricted", "confidential"))
    if field == "unit":
        return len(value) <= 120
    if field == "owner_user_id":
        return len(value) <= 150
    if field == "project":
        return len(value) <= 180 and not any(marker in value for marker in LESSON_MARKERS)
    return len(value) > 5


def _map_answer_to_asked_field(
    answer: str, current: dict[str, Any], conversation: list[dict[str, Any]]
) -> dict[str, Any]:
    asked = last_asked(conversation[:-1])
    if not asked or present(current.get(asked)) or not _answer_is_compatible(asked, answer):
        return {}
    value = clean_sentence(answer)
    if asked == "owner_user_id":
        return {"owner_text": value}
    if asked == "sensitivity":
        if "محرمانه" in value or "confidential" in value:
            value = "confidential"
        elif "محدود" in value or "restricted" in value:
            value = "restricted"
        else:
            value = "internal"
    return {asked: value}


def _multi_pass_heuristic(text: str, current: dict[str, Any], conversation: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    text = clean_sentence(text, 12000)
    text_sentences = sentences(text)
    if not text:
        return result

    result["knowledge_type"] = classify_knowledge_type(text)
    _field_confidence(result, "knowledge_type", 0.75)

    tag = _extract_tag(text)
    if tag:
        result["equipment_tag"] = tag
        _field_confidence(result, "equipment_tag", 0.99)

    conditions = [
        sentence
        for sentence in text_sentences
        if any(
            marker in sentence
            for marker in ("در زمان", "هنگام", "پس از", "قبل از", "در پروژه", "در واحد", "در فرایند", "در فرآیند")
        )
    ]
    if conditions:
        result["occurrence_conditions"] = _join_unique(conditions[:3], 1200)
        _field_confidence(result, "occurrence_conditions", 0.72)

    problem_markers = (
        "مسئله",
        "مشکل",
        "نیاز",
        "هدف",
        "موضوع",
        "چالش",
        "خطا",
        "خرابی",
        "ریسک",
        "درخواست",
        "ابهام",
        "کمبود",
        "افزایش",
        "کاهش",
        "تاخیر",
        "تأخیر",
        "عدم",
        "ضرورت",
    )
    problem_sentences = [s for s in text_sentences if any(marker in s for marker in problem_markers)]
    if not problem_sentences and text_sentences:
        problem_sentences = [text_sentences[0]]
    if problem_sentences:
        result["problem"] = _join_unique(problem_sentences[:3], 1200)
        _field_confidence(
            result, "problem", 0.82 if any(marker in problem_sentences[0] for marker in problem_markers) else 0.68
        )
        _source_span(result, "problem", problem_sentences[0])

    symptom_sentences = [
        s
        for s in text_sentences
        if re.search(r"\d", normalize(s))
        or any(x in s for x in ("نشانه", "داده", "ورودی", "شاخص", "وضعیت", "لاگ", "علامت"))
    ]
    if symptom_sentences:
        result["symptoms"] = _join_unique(symptom_sentences[:5], 1600)
        _field_confidence(result, "symptoms", 0.74)

    hypotheses = [s for s in text_sentences if any(marker in s for marker in HYPOTHESIS_MARKERS)]
    investigations = [
        s
        for s in text_sentences
        if any(marker in s for marker in INVESTIGATION_MARKERS) and not any(marker in s for marker in RESULT_MARKERS)
    ]
    cause_sentences = [s for s in text_sentences if any(marker in s for marker in CAUSE_MARKERS)]
    if hypotheses:
        result["initial_hypothesis"] = _join_unique(hypotheses, 1200)
        _field_confidence(result, "initial_hypothesis", 0.88)
    if investigations:
        result["investigation_steps"] = _join_unique(investigations[:8], 2200)
        _field_confidence(result, "investigation_steps", 0.78)
    if cause_sentences:
        confirmed = [
            s
            for s in cause_sentences
            if any(x in s for x in ("مشخص شد", "نشان داد", "تأیید شد", "تایید شد", "علت ریشه‌ای"))
        ]
        selected = confirmed or cause_sentences
        result["root_cause"] = _join_unique(selected[:5], 1600)
        result["root_cause_status"] = "confirmed" if confirmed else "probable"
        _field_confidence(result, "root_cause", 0.90 if confirmed else 0.72)
        _source_span(result, "root_cause", selected[0])

    action_sentences = [s for s in text_sentences if any(verb in s for verb in ACTION_VERBS)]
    if action_sentences:
        result["action_taken"] = _join_unique(action_sentences[:12], 3600)
        result["action_steps"] = _join_unique(action_sentences[:12], 3600)
        _field_confidence(result, "action_taken", 0.86)
        _field_confidence(result, "action_steps", 0.76)
        _source_span(result, "action_taken", action_sentences[0])
    else:
        # Generic document or explanatory knowledge: preserve the substantive content
        # rather than forcing a failure because no maintenance-style action verb exists.
        result["action_taken"] = text[:6000]
        _field_confidence(result, "action_taken", 0.64)
        _source_span(result, "action_taken", text_sentences[0] if text_sentences else text)

    numeric_result, numeric_confidence = _extract_numeric_result(text)
    result_sentences = [s for s in text_sentences if any(marker in s for marker in RESULT_MARKERS)]
    if numeric_result:
        supporting = _join_unique(result_sentences[:4], 1000)
        result["result"] = numeric_result + (
            f"؛ {supporting}" if supporting and numeric_result not in supporting else ""
        )
        _field_confidence(result, "result", numeric_confidence)
    elif result_sentences:
        result["result"] = _join_unique(result_sentences[:6], 1600)
        _field_confidence(result, "result", 0.78)

    verification_sentences = [
        s
        for s in text_sentences
        if any(x in s for x in ("تأیید شد", "تایید شد", "کنترل شد", "بازبینی شد", "آزمون شد", "پایش شد", "اعتبارسنجی"))
    ]
    if verification_sentences:
        result["verification"] = _join_unique(verification_sentences[:5], 1400)
        _field_confidence(result, "verification", 0.82)

    lessons = [s for s in text_sentences if any(marker in s for marker in LESSON_MARKERS)]
    if lessons:
        result["lesson_learned"] = _join_unique(lessons[:6], 1600)
        _field_confidence(result, "lesson_learned", 0.84)

    risks = [s for s in text_sentences if any(marker in s for marker in RISK_MARKERS)]
    if risks:
        result["safety_notes"] = _join_unique(risks[:6], 1600)
        _field_confidence(result, "safety_notes", 0.82)

    limits = [s for s in text_sentences if any(marker in s for marker in LIMIT_MARKERS)]
    if limits:
        result["limitations"] = _join_unique(limits[:6], 1600)
        _field_confidence(result, "limitations", 0.80)

    project_match = re.search(r"(?:پروژه|سامانه|فرایند|فرآیند)\s+([^،.؛\n]{3,100})", text)
    if project_match:
        result["project"] = clean_sentence(project_match.group(0), 140)
        _field_confidence(result, "project", 0.72)

    mapped = _map_answer_to_asked_field(text, current, conversation)
    result.update(mapped)
    for key in mapped:
        _field_confidence(result, "owner_text" if key == "owner_text" else key, 0.98)

    return result


def _llm_extract(conversation: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    if not settings.api_key:
        return {}
    from src.llm import AvalAILLM

    public_schema = {
        key: {
            "label": spec["label"],
            "description": {
                "problem": "موضوع، نیاز، مسئله، هدف یا زمینه اصلی دانش",
                "action_taken": "محتوای اصلی دانش؛ می‌تواند روش، راهکار، رویه، تصمیم، تحلیل، کد یا راهنما باشد",
                "root_cause": "علت، منطق، مبنا یا استدلال؛ فقط اگر در متن وجود دارد",
                "result": "نتیجه، خروجی، اثر یا کاربرد؛ فقط اگر در متن وجود دارد",
                "limitations": "محدودیت، استثنا یا شرایط عدم کاربرد؛ از متن استنباط محتاطانه شود",
                "safety_notes": "هر نوع ریسک، کنترل، انطباق، امنیت یا ملاحظه حساس",
            }.get(key, spec["label"]),
        }
        for key, spec in FORM_SCHEMA.items()
        if key not in {"owner_user_id", "unit", "sensitivity", "first_check", "novice_mistake", "early_warning"}
    }
    prompt = f"""
فقط یک JSON معتبر برگردان و هیچ متن دیگری ننویس.
نقش تو استخراج‌گر عمومی دانش سازمانی است. متن می‌تواند متعلق به تعمیرات، منابع انسانی، مالی، نرم‌افزار، حقوقی، فروش، عملیات، پروژه یا هر حوزه دیگری باشد.
قواعد قطعی:
1) ساختار را بر اساس جنس دانش انتخاب کن؛ همه دانش‌ها گزارش خرابی نیستند.
2) اطلاعات را حدس نزن. فیلد ناموجود را ننویس.
3) عنوان، خلاصه، نوع دانش و برچسب‌ها را خودکار تولید کن.
4) شرح اصلی دانش را در action_taken قرار بده؛ این فیلد می‌تواند روش، رویه، راهکار، تصمیم، تحلیل یا راهنمای استفاده باشد.
5) root_cause، result، lesson_learned، limitations و safety_notes اختیاری‌اند و نباید برای پرشدن اجباری شوند.
6) شرح شواهد را از نام و محتوای سند استخراج کن؛ از کاربر نخواه آن را دوباره تایپ کند.
7) اگر اطلاعات جدید با مقدار فعلی تناقض جدی دارد، conflict بده.
8) برای هر فیلد استخراج‌شده confidence بین 0 و 1 بده.
خروجی:
{{"fields":{{...}},"confidence":{{...}},"conflict":null|{{"field":"...","old":"...","new":"...","question":"..."}}}}
schema={json.dumps(public_schema, ensure_ascii=False)}
current={json.dumps(public_form_data(current), ensure_ascii=False)}
conversation={json.dumps(conversation, ensure_ascii=False)}
"""
    try:
        raw = AvalAILLM(settings.api_key, settings.model, settings.base_url, temperature=0).generate(prompt)
        match = re.search(r"\{.*\}", raw, re.S)
        parsed = json.loads(match.group()) if match else {}
        if "fields" not in parsed:
            parsed = {"fields": parsed, "confidence": {}}
        return parsed
    except Exception:
        return {}


def _merge_extractions(current: dict[str, Any], heuristic: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    llm_fields = llm.get("fields", {}) if isinstance(llm, dict) else {}
    llm_conf = llm.get("confidence", {}) if isinstance(llm, dict) else {}

    # LLM richness first; deterministic extraction then protects concrete values.
    for source in (llm_fields, heuristic):
        for key, value in source.items():
            if key.startswith("_") or (key not in FORM_SCHEMA and key != "owner_text"):
                continue
            if present(value):
                output[key] = value

    confidence_map: dict[str, float] = {}
    confidence_map.update(current.get("_field_confidence", {}))
    confidence_map.update({key: float(value) for key, value in llm_conf.items() if isinstance(value, (int, float))})
    confidence_map.update(heuristic.get("_field_confidence", {}))
    output["_field_confidence"] = confidence_map
    output["_source_spans"] = {**current.get("_source_spans", {}), **heuristic.get("_source_spans", {})}

    conflict = llm.get("conflict") if isinstance(llm, dict) else None
    current_core = current.get("action_taken")
    new_core = output.get("action_taken")
    if (
        current_core
        and new_core
        and len(str(current_core)) > 80
        and len(str(new_core)) > 80
        and not semantically_similar(str(current_core), str(new_core))
    ):
        conflict = conflict or {
            "field": "action_taken",
            "old": str(current_core),
            "new": str(new_core),
            "question": "محتوای جدید با شرح قبلی تفاوت جدی دارد. کدام نسخه باید مبنای دانش باشد؟",
        }
        output.pop("action_taken", None)
    if conflict:
        output["_conflict"] = conflict
    return output


def _keywords(data: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(data.get(key, ""))
        for key in ("title", "problem", "action_taken", "root_cause", "result", "lesson_learned", "unit", "project")
    )
    tokens = [
        token
        for token in re.findall(r"[\u0600-\u06FFA-Za-z0-9_-]+", normalize(text).lower())
        if len(token) > 2 and token not in STOP_WORDS and not token.isdigit()
    ]
    candidates = [str(data["equipment_tag"])] if present(data.get("equipment_tag")) else []
    candidates.extend(token for token, _ in Counter(tokens).most_common(14))
    if present(data.get("unit")):
        candidates.append(str(data["unit"]))
    return list(dict.fromkeys(candidates))[:12]


def auto_metadata(data: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if not data.get("knowledge_type"):
        output["knowledge_type"] = classify_knowledge_type(
            " ".join(str(data.get(key, "")) for key in ("problem", "action_taken", "result", "lesson_learned")),
            str(data.get("source_filename", "")),
        )

    problem = clean_sentence(str(data.get("problem", "")), 180)
    core = clean_sentence(str(data.get("action_taken", "")), 260)
    result = clean_sentence(str(data.get("result", "")), 180)
    filename = str(data.get("source_filename", ""))

    if not data.get("title"):
        if filename:
            stem = clean_sentence(Path(filename).stem.replace("_", " ").replace("-", " "), 120)
            if stem:
                output["title"] = stem
        if not output.get("title") and problem:
            output["title"] = problem[:120]
        if not output.get("title") and core:
            output["title"] = core[:120]

    if not data.get("summary") and (problem or core):
        parts = []
        if problem:
            parts.append(f"موضوع: {problem}")
        if core:
            parts.append(f"محتوای اصلی: {core}")
        if result:
            parts.append(f"نتیجه یا کاربرد: {result}")
        output["summary"] = ". ".join(parts)[:1200]

    if not data.get("tags"):
        output["tags"] = "، ".join(_keywords({**data, **output}))

    if not data.get("transfer_message"):
        takeaway = clean_sentence(str(data.get("lesson_learned") or data.get("action_taken") or ""), 220)
        if takeaway:
            output["transfer_message"] = takeaway
    return output


def extract_fields(conversation: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any]:
    latest = next(
        (message.get("content", "") for message in reversed(conversation) if message.get("role") == "user"), ""
    )
    heuristic = _multi_pass_heuristic(latest, current, conversation)
    llm = _llm_extract(conversation, current)
    output = _merge_extractions(current, heuristic, llm)
    merged = {**current, **{key: value for key, value in output.items() if not key.startswith("_")}}
    output.update(auto_metadata(merged))
    return output


def extract_document_fields(text: str, filename: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    current = dict(current or {})
    if not (text or "").strip():
        stem = clean_sentence(Path(filename).stem.replace("_", " ").replace("-", " "), 120) or "سند بارگذاری‌شده"
        return {
            "source_filename": filename,
            "knowledge_type": classify_knowledge_type("", filename),
            "title": stem,
            "problem": f"ثبت و مدیریت دانش موجود در سند «{filename}»",
            "action_taken": (
                f"محتوای اصلی این دانش در سند پیوست‌شده «{filename}» قرار دارد. "
                "متن سند در این اجرا قابل استخراج نبوده و باید در مرحله بازبینی از روی فایل اصلی کنترل شود."
            ),
            "summary": f"دانش ثبت‌شده بر مبنای سند پیوست «{filename}»؛ نیازمند کنترل محتوای فایل در بازبینی.",
            "evidence": f"سند اصلی «{filename}» به رکورد دانش متصل شده است.",
            "tags": stem,
            "_field_confidence": {"problem": 0.45, "action_taken": 0.35, "knowledge_type": 0.50},
        }
    conversation = [{"role": "user", "content": f"نام سند: {filename}\n\n{text[:18000]}"}]
    extracted = extract_fields(conversation, current)
    extracted["source_filename"] = filename
    extracted["evidence"] = f"محتوا از سند «{filename}» استخراج و به این دانش متصل شده است."
    merged = {**current, **{key: value for key, value in extracted.items() if not key.startswith("_")}}
    metadata = auto_metadata(merged)
    extracted.update(metadata)
    if not present(extracted.get("title")):
        extracted["title"] = clean_sentence(Path(filename).stem.replace("_", " "), 120) or "دانش استخراج‌شده از سند"
    if not present(extracted.get("problem")):
        first = sentences(text)
        extracted["problem"] = first[0] if first else f"محتوای سند {filename}"
    if not present(extracted.get("action_taken")):
        extracted["action_taken"] = clean_sentence(text, 6000)
    return extracted


def _specificity_score(value: Any, *, numeric_bonus: bool = False, min_length: int = 30) -> float:
    if not present(value):
        return 0.0
    text = clean_sentence(str(value), 5000)
    score = min(1.0, len(text) / max(1, min_length))
    if numeric_bonus and re.search(r"\d", normalize(text)):
        score = min(1.0, score + 0.20)
    return score


def evaluate(
    data: dict[str, Any], attachments_count: int = 0, mode: str = "fast", question_count: int = 0
) -> dict[str, Any]:
    missing_required = [
        field
        for field in REQUIRED
        if not present(data.get(field)) and not (field == "owner_user_id" and present(data.get("owner_text")))
    ]
    total_weight = sum(FORM_SCHEMA[field]["weight"] for field in REQUIRED)
    done_weight = sum(FORM_SCHEMA[field]["weight"] for field in REQUIRED if field not in missing_required)
    completeness = round(100 * done_weight / total_weight, 1)

    quality_components = {
        "topic_clarity": 20 * _specificity_score(data.get("problem"), min_length=35),
        "content_usefulness": 35 * _specificity_score(data.get("action_taken"), min_length=90),
        "structure_and_method": 15
        * min(
            1.0,
            _specificity_score(data.get("action_steps"), min_length=45)
            + 0.6 * _specificity_score(data.get("investigation_steps"), min_length=45),
        ),
        "outcome_or_application": 10 * _specificity_score(data.get("result"), numeric_bonus=True, min_length=35),
        "transferability": 10
        * _specificity_score(data.get("lesson_learned") or data.get("transfer_message"), min_length=35),
        "evidence_and_limits": 10
        * min(
            1.0,
            0.6 * _specificity_score(data.get("evidence"), min_length=20)
            + 0.5 * _specificity_score(data.get("limitations"), min_length=30)
            + 0.5 * _specificity_score(data.get("verification"), min_length=25),
        ),
    }
    quality_score = round(sum(quality_components.values()))

    evidence_score = 0
    if attachments_count:
        evidence_score += min(45, 30 + 5 * attachments_count)
    if present(data.get("evidence")):
        evidence_score += 20
    if present(data.get("verification")):
        evidence_score += 15
    if present(data.get("result")):
        evidence_score += 10
    if data.get("root_cause_status") == "confirmed":
        evidence_score += 10
    evidence_score = min(100, evidence_score)

    confidence_values = [
        float(value) for value in data.get("_field_confidence", {}).values() if isinstance(value, (int, float))
    ]
    confidence_score = round(100 * sum(confidence_values) / len(confidence_values)) if confidence_values else 55

    critical_present = all(present(data.get(field)) for field in DRAFT_CORE)
    can_build_draft = critical_present and completeness >= 65 and not data.get("_active_conflict")
    ready_to_submit = not missing_required and not data.get("_active_conflict")

    field_status = {
        key: {
            "label": spec["label"],
            "filled": present(data.get(key)) or (key == "owner_user_id" and present(data.get("owner_text"))),
            "required": spec["required"],
            "source": spec.get("source"),
            "value": data.get(key) if key != "owner_user_id" else data.get("owner_text") or data.get("owner_user_id"),
        }
        for key, spec in FORM_SCHEMA.items()
    }

    next_field = None
    next_question = None
    conflict = data.get("_active_conflict")
    if conflict:
        state = CaptureState.CLARIFYING_CONFLICT.value
        next_field = conflict.get("field", "action_taken")
        next_question = conflict.get("question")
    elif ready_to_submit:
        state = CaptureState.READY_TO_SUBMIT.value
    elif can_build_draft:
        state = CaptureState.DRAFT_READY.value
    else:
        state = CaptureState.COLLECTING_REQUIRED.value
        # The new UI has no specialist chat. Keep the legacy endpoint bounded and
        # never continue questioning after the configured quick-capture limit.
        if question_count < 3:
            for candidate in DRAFT_CORE:
                if not present(data.get(candidate)):
                    next_field = candidate
                    next_question = QUESTIONS[candidate]
                    break

    return {
        "state": state,
        "missing_required_fields": missing_required,
        "missing_required_labels": [LABELS[field] for field in missing_required],
        "essential_completion": completeness,
        "completion_score": completeness,
        "quality_score": quality_score,
        "quality_components": {key: round(value, 1) for key, value in quality_components.items()},
        "evidence_score": evidence_score,
        "confidence_score": confidence_score,
        "can_build_draft": can_build_draft,
        "ready_to_save": can_build_draft,
        "ready_to_submit": ready_to_submit,
        "next_field": next_field,
        "next_question": next_question,
        "question_options": [],
        "question_type": "text",
        "field_status": field_status,
        "optional_remaining": [
            LABELS[field]
            for field, spec in FORM_SCHEMA.items()
            if not spec["required"]
            and not present(data.get(field))
            and spec.get("source") not in {"generated", "legacy"}
        ][:6],
    }


def _preview_lines(data: dict[str, Any]) -> list[str]:
    preferred = ("knowledge_type", "problem", "action_taken", "result", "lesson_learned")
    lines = []
    for field in preferred:
        if present(data.get(field)):
            value = clean_sentence(str(data[field]), 150)
            lines.append(f"✓ {LABELS[field]}: {value}")
    return lines[:5]


def assistant_message(
    evaluation: dict[str, Any], extracted: dict[str, Any] | None = None, data: dict[str, Any] | None = None
) -> str:
    data = data or {}
    extracted = extracted or {}
    lines: list[str] = []

    conflict = extracted.get("_conflict") or data.get("_active_conflict")
    if conflict:
        lines.append("⚠️ محتوای جدید با مقدار قبلی تفاوت جدی دارد و باید در فرم بازبینی شود.")

    acknowledgements = [
        f"{LABELS[key]} تکمیل شد"
        for key, value in extracted.items()
        if key in LABELS
        and present(value)
        and key not in {"title", "summary", "tags", "action_steps", "transfer_message"}
    ]
    if acknowledgements:
        lines.append("، ".join(acknowledgements[:5]) + ".")

    preview = _preview_lines(data)
    if preview:
        lines.append("نمای فعلی فرم:\n" + "\n".join(preview))

    lines.append(
        f"تکمیل اطلاعات ضروری: {evaluation['essential_completion']}٪ | "
        f"کیفیت محتوا: {evaluation['quality_score']}٪ | "
        f"اعتبار مستندات: {evaluation['evidence_score']}٪ | "
        f"اطمینان استخراج: {evaluation['confidence_score']}٪"
    )

    if evaluation["state"] == CaptureState.READY_TO_SUBMIT.value:
        lines.append("اطلاعات لازم کامل است و پیش‌نویس آماده ذخیره و ارسال برای بازبینی است.")
    elif evaluation["state"] == CaptureState.DRAFT_READY.value:
        remaining = "، ".join(evaluation["missing_required_labels"])
        lines.append("محتوای دانش برای ساخت پیش‌نویس کافی است.")
        if remaining:
            lines.append(f"فقط اطلاعات حاکمیتی باقی‌مانده را در فرم تکمیل کنید: {remaining}.")
    elif evaluation.get("next_question"):
        lines.append(evaluation["next_question"])
    return "\n\n".join(lines)


def public_form_data(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if not key.startswith("_")}


def build_content(data: dict[str, Any]) -> str:
    order = [
        "problem",
        "occurrence_conditions",
        "symptoms",
        "action_taken",
        "action_steps",
        "investigation_steps",
        "initial_hypothesis",
        "root_cause",
        "verification",
        "result",
        "lesson_learned",
        "limitations",
        "safety_notes",
        "evidence",
        "project",
        "transfer_message",
    ]
    clean = public_form_data(data)
    return "\n\n".join(f"## {LABELS[field]}\n{clean[field]}" for field in order if present(clean.get(field)))


def knowledge_graph(data: dict[str, Any]) -> dict[str, Any]:
    clean = public_form_data(data)
    title = clean_sentence(str(clean.get("title") or clean.get("problem") or "دانش سازمانی"), 180)
    nodes: list[dict[str, str]] = [{"id": "knowledge", "type": "knowledge", "label": title}]
    edges: list[dict[str, str]] = []

    field_types = (
        ("knowledge_type", "knowledge_type"),
        ("unit", "unit"),
        ("problem", "topic"),
        ("initial_hypothesis", "option"),
        ("root_cause", "rationale"),
        ("action_taken", "method"),
        ("result", "outcome"),
        ("project", "context"),
        ("equipment_tag", "asset"),
    )
    for field, entity_type in field_types:
        if present(clean.get(field)):
            nodes.append({"id": field, "type": entity_type, "label": clean_sentence(str(clean[field]), 180)})

    node_ids = {node["id"] for node in nodes}
    generic_relations = (
        ("knowledge", "knowledge_type", "HAS_TYPE"),
        ("knowledge", "unit", "BELONGS_TO_UNIT"),
        ("knowledge", "problem", "COVERS_TOPIC"),
        ("problem", "initial_hypothesis", "CONSIDERS"),
        ("problem", "root_cause", "EXPLAINED_BY"),
        ("knowledge", "action_taken", "DESCRIBES"),
        ("action_taken", "result", "PRODUCES"),
        ("knowledge", "project", "RELATED_TO"),
        ("equipment_tag", "knowledge", "RELATED_ASSET"),
    )
    for source, target, relation in generic_relations:
        if source in node_ids and target in node_ids:
            edges.append({"source": source, "target": target, "relation": relation})

    # Backward-compatible diagnostic chain when such fields exist.
    legacy_relations = (
        ("equipment_tag", "problem", "HAS_PROBLEM"),
        ("problem", "initial_hypothesis", "INITIALLY_SUSPECTED"),
        ("problem", "root_cause", "CAUSED_BY"),
        ("root_cause", "action_taken", "RESOLVED_BY"),
        ("action_taken", "result", "PRODUCED"),
    )
    for source, target, relation in legacy_relations:
        if source in node_ids and target in node_ids:
            edges.append({"source": source, "target": target, "relation": relation})
    return {"nodes": nodes, "edges": edges}


def analyze_value(data: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0
    if present(data.get("action_taken")):
        score += 30
        reasons.append("دارای محتوای قابل استفاده")
    if present(data.get("action_steps")):
        score += 15
        reasons.append("دارای مراحل اجرایی")
    if present(data.get("result")):
        score += 15
        reasons.append("دارای نتیجه یا کاربرد مشخص")
    if present(data.get("lesson_learned")):
        score += 15
        reasons.append("قابل انتقال به دیگران")
    if present(data.get("evidence")):
        score += 15
        reasons.append("دارای منبع یا مستند")
    if present(data.get("limitations") or data.get("safety_notes")):
        score += 10
        reasons.append("دارای ملاحظات و محدودیت‌ها")
    return {
        "score": min(100, score),
        "level": "بالا" if score >= 70 else "متوسط" if score >= 40 else "پایین",
        "reasons": reasons,
    }
