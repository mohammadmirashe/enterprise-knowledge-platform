from __future__ import annotations

import re
from typing import Any

from app.capture_agent import build_content, evaluate
from app.database import (
    add_document,
    connect,
    create_gap,
    create_knowledge,
    get_knowledge,
    one,
    review_knowledge,
)

DEMO_SEED_TAG = "demo-seed-v1"

DEMO_QUESTIONS = [
    "برای جلوگیری از افزایش دمای یاتاقان پمپ P-101 چه کاری باید انجام شود؟",
    "فرآیند درخواست مرخصی کارکنان چگونه است؟",
    "در رخداد امنیتی حساب کاربری مشکوک چه اقداماتی لازم است؟",
    "تأمین‌کننده راهبردی را با چه معیارهایی ارزیابی کنیم؟",
]

DEMO_KNOWLEDGE: list[dict[str, Any]] = [
    {
        "title": "کنترل افزایش دمای یاتاقان پمپ P-101 پس از تعمیرات",
        "summary": "پس از تعمیرات، کنترل هم‌راستایی موتور و پمپ پیش از راه‌اندازی از افزایش دما و لرزش جلوگیری می‌کند.",
        "knowledge_type": "lesson_learned",
        "unit": "نگهداری و تعمیرات",
        "domain": "تجهیزات دوار",
        "project": "برنامه قابلیت اطمینان تجهیزات",
        "equipment_tag": "P-101",
        "problem": "در نخستین راه‌اندازی پس از تعمیرات، دمای یاتاقان پمپ P-101 از 68 به 92 درجه سانتی‌گراد رسید و لرزش افزایش یافت.",
        "occurrence_conditions": "راه‌اندازی سرد پس از باز و بست کوپلینگ و پایان تعمیرات اساسی پمپ.",
        "symptoms": "روند افزایشی دما، ارتعاش بالاتر از خط مبنا و صدای غیرعادی در ناحیه کوپلینگ.",
        "initial_hypothesis": "کمبود روانکار یا خرابی یاتاقان به‌عنوان فرضیه اولیه بررسی شد.",
        "investigation_steps": "سطح و فشار روغن کنترل شد؛ سپس ارتعاش، soft foot و هم‌راستایی لیزری موتور و پمپ اندازه‌گیری شد.",
        "root_cause": "انحراف زاویه‌ای کوپلینگ و soft foot یکی از پایه‌های موتور پس از مونتاژ.",
        "root_cause_status": "confirmed",
        "action_taken": "تجهیز مطابق LOTO ایمن‌سازی شد، soft foot اصلاح و هم‌راستایی لیزری با تلرانس دستورالعمل سازنده انجام گرفت.",
        "action_steps": "1) توقف و LOTO؛ 2) ثبت خط مبنای ارتعاش؛ 3) کنترل پایه‌ها؛ 4) اصلاح soft foot؛ 5) هم‌راستایی لیزری؛ 6) راه‌اندازی و پایش دو ساعته.",
        "verification": "دما و ارتعاش در بازه‌های 15 دقیقه‌ای طی دو ساعت ثبت و با baseline پیش از تعمیر مقایسه شد.",
        "result": "دمای یاتاقان از 92 به 68 درجه بازگشت و ارتعاش در محدوده مجاز تثبیت شد.",
        "lesson_learned": "پس از هر باز و بست کوپلینگ، کنترل soft foot و هم‌راستایی باید پیش‌شرط مجوز راه‌اندازی باشد.",
        "evidence": "گزارش هم‌راستایی لیزری، trend دما و برگه اندازه‌گیری ارتعاش در پرونده تعمیراتی ثبت شده است.",
        "safety_notes": "اجرای LOTO و تأیید نبود انرژی پیش از باز کردن guard کوپلینگ الزامی است.",
        "limitations": "مقادیر تلرانس باید با سرعت، توان و دستورالعمل سازنده هر تجهیز تطبیق داده شود.",
        "tags": "پمپ، P-101، هم‌راستایی، یاتاقان، ارتعاش، demo-seed-v1",
        "owner_user_id": 3,
        "sensitivity": "internal",
        "status": "published",
    },
    {
        "title": "فرآیند استاندارد درخواست و تأیید مرخصی کارکنان",
        "summary": "درخواست مرخصی باید پس از کنترل مانده و جانشین، ابتدا توسط مدیر مستقیم و سپس منابع انسانی بررسی شود.",
        "knowledge_type": "procedure",
        "unit": "منابع انسانی",
        "domain": "منابع انسانی",
        "project": "سامانه خدمات کارکنان",
        "problem": "درخواست‌های مرخصی ناقص یا بدون جانشین باعث تأخیر در تأیید و اختلال در برنامه شیفت می‌شد.",
        "occurrence_conditions": "تمام درخواست‌های مرخصی استحقاقی، استعلاجی و بدون حقوق کارکنان.",
        "action_taken": "کارمند نوع مرخصی، تاریخ شروع و پایان و جانشین پیشنهادی را ثبت می‌کند؛ سامانه مانده را کنترل و درخواست را برای مدیر مستقیم و سپس منابع انسانی ارسال می‌کند.",
        "action_steps": "1) کنترل مانده؛ 2) انتخاب نوع و بازه؛ 3) معرفی جانشین؛ 4) تأیید مدیر؛ 5) کنترل منابع انسانی؛ 6) اعلام نتیجه به کارمند.",
        "verification": "درخواست تأییدشده باید در تقویم تیم، پرونده حضور و غیاب و اعلان کارمند هم‌زمان ثبت شود.",
        "result": "زمان متوسط تعیین تکلیف درخواست کاهش یافت و وضعیت جانشینی پیش از شروع مرخصی شفاف شد.",
        "lesson_learned": "کنترل خودکار مانده و الزام جانشین از رفت‌وبرگشت غیرضروری درخواست جلوگیری می‌کند.",
        "evidence": "رویه HR-PR-07 و گزارش گردش درخواست‌های سه‌ماهه مبنای این دانش است.",
        "limitations": "مرخصی استعلاجی تابع مدارک و الزامات قانونی مستقل است.",
        "tags": "منابع انسانی، مرخصی، گردش کار، جانشین، demo-seed-v1",
        "owner_user_id": 2,
        "sensitivity": "internal",
        "status": "published",
    },
    {
        "title": "پاسخ اولیه به رخداد حساب کاربری مشکوک",
        "summary": "در رخداد مشکوک، مهار حساب، حفظ شواهد، بررسی دامنه اثر و بازیابی کنترل‌شده باید به‌ترتیب انجام شود.",
        "knowledge_type": "technical_guide",
        "unit": "فناوری اطلاعات و نرم‌افزار",
        "domain": "فناوری اطلاعات و نرم‌افزار",
        "project": "مدیریت رخداد امنیت اطلاعات",
        "equipment_tag": "IAM/SIEM",
        "problem": "ورود غیرعادی از موقعیت جدید و ایجاد چند نشست هم‌زمان برای یک حساب سازمانی مشاهده شده است.",
        "symptoms": "هشدار impossible travel، افزایش خطای MFA و دسترسی خارج از الگوی زمانی کاربر.",
        "action_taken": "حساب و نشست‌های فعال موقتاً مهار، tokenها ابطال، شواهد ثبت و دامنه دسترسی بررسی می‌شود؛ بازیابی تنها پس از تأیید تیم امنیت انجام می‌گیرد.",
        "action_steps": "1) ثبت incident؛ 2) حفظ log؛ 3) غیرفعال‌سازی موقت؛ 4) ابطال نشست‌ها؛ 5) بررسی تغییرات؛ 6) reset امن؛ 7) پایش تقویت‌شده.",
        "verification": "SIEM باید نبود نشست ناشناس و توقف تلاش‌های ناموفق را پس از بازیابی تأیید کند.",
        "result": "مهار سریع، احتمال گسترش دسترسی و از دست رفتن شواهد را کاهش می‌دهد.",
        "lesson_learned": "بازنشانی رمز بدون ابطال token و بررسی نشست‌های فعال، مهار کامل محسوب نمی‌شود.",
        "evidence": "Runbook امنیتی IR-AC-02 و رخدادهای شبیه‌سازی‌شده tabletop.",
        "safety_notes": "از حذف log یا خاموش کردن منبع شواهد پیش از هماهنگی با تیم پاسخ به رخداد خودداری شود.",
        "limitations": "این راهنما جایگزین playbook مصوب، الزامات حقوقی یا forensic procedure نیست.",
        "tags": "امنیت، پاسخ به رخداد، حساب کاربری، SIEM، MFA، demo-seed-v1",
        "owner_user_id": 1,
        "sensitivity": "restricted",
        "status": "published",
    },
    {
        "title": "چارچوب ارزیابی تأمین‌کنندگان راهبردی",
        "summary": "ارزیابی تأمین‌کننده باید کیفیت، تحویل، ریسک تداوم، انطباق و هزینه کل مالکیت را هم‌زمان پوشش دهد.",
        "knowledge_type": "decision_record",
        "unit": "زنجیره تأمین و تدارکات",
        "domain": "زنجیره تأمین و تدارکات",
        "project": "تاب‌آوری زنجیره تأمین",
        "problem": "انتخاب صرفاً بر مبنای کمترین قیمت، ریسک تأخیر، افت کیفیت و توقف عملیات را پنهان می‌کرد.",
        "action_taken": "مدل امتیازدهی چندمعیاره با وزن کیفیت 30٪، تحویل 25٪، ریسک تداوم 20٪، انطباق 15٪ و هزینه کل مالکیت 10٪ استفاده می‌شود.",
        "action_steps": "1) تعیین criticality؛ 2) گردآوری عملکرد 12 ماهه؛ 3) امتیازدهی شواهد؛ 4) جلسه cross-functional؛ 5) برنامه بهبود یا منبع جایگزین.",
        "verification": "امتیازها باید با NCR، تحویل به‌موقع، audit و سوابق مالی قابل ردیابی باشند.",
        "result": "تصمیم خرید از مقایسه قیمت واحد به ارزیابی ریسک و ارزش چرخه عمر تغییر می‌کند.",
        "lesson_learned": "وزن معیارها باید پیش از مشاهده پیشنهادهای تجاری تصویب شود تا سوگیری پسینی کاهش یابد.",
        "evidence": "scorecard تأمین‌کننده، گزارش کیفیت ورودی و داده تحویل 12 ماهه.",
        "limitations": "برای اقلام غیرراهبردی می‌توان نسخه ساده‌شده مدل را استفاده کرد.",
        "tags": "تأمین‌کننده، ارزیابی، ریسک، کیفیت، تحویل، demo-seed-v1",
        "owner_user_id": 2,
        "sensitivity": "internal",
        "status": "published",
    },
    {
        "title": "درس‌آموخته مهاجرت سرویس گزارش‌گیری به زیرساخت جدید",
        "summary": "این رکورد نمونه برای نمایش صف بازبینی آماده شده و هنوز منتشر نشده است.",
        "knowledge_type": "lesson_learned",
        "unit": "فناوری اطلاعات و نرم‌افزار",
        "domain": "فناوری اطلاعات و نرم‌افزار",
        "project": "نوسازی زیرساخت داده",
        "problem": "در مهاجرت آزمایشی، jobهای زمان‌بندی‌شده به timezone پیش‌فرض سرور وابسته بودند و گزارش‌ها با تأخیر تولید شدند.",
        "root_cause": "timezone به‌صورت explicit در scheduler و container تعریف نشده بود.",
        "action_taken": "timezone برنامه و container صریح شد و آزمون smoke برای زمان اجرای job به pipeline استقرار اضافه گردید.",
        "verification": "سه چرخه زمان‌بندی در محیط staging با زمان مرجع سازمان مقایسه شد.",
        "result": "زمان تولید گزارش‌ها در آزمون staging با برنامه مصوب منطبق شد.",
        "lesson_learned": "وابستگی زمانی باید در configuration-as-code ثبت و در تست استقرار کنترل شود.",
        "evidence": "گزارش آزمون staging و change request پروژه.",
        "tags": "مهاجرت، timezone، scheduler، بازبینی، demo-seed-v1",
        "owner_user_id": 3,
        "sensitivity": "internal",
        "status": "pending_review",
    },
]


def seed_demo_data() -> dict[str, int]:
    """Populate a new demo database through the real governance model."""
    created = 0
    published = 0
    for item in DEMO_KNOWLEDGE:
        existing = one(
            "SELECT id,status FROM knowledge_items WHERE title=? AND tags LIKE ?",
            (item["title"], f"%{DEMO_SEED_TAG}%"),
        )
        if existing:
            continue

        domain = one("SELECT id FROM knowledge_domains WHERE name=?", (item["domain"],))
        structured = {key: value for key, value in item.items() if key not in {"domain", "status"}}
        structured["domain_id"] = domain["id"] if domain else None
        evaluation = evaluate(structured, attachments_count=1)
        knowledge_id, _ = create_knowledge(
            {
                **structured,
                "structured_data": structured,
                "content": build_content(structured),
                "domain_id": structured["domain_id"],
                "status": "pending_review" if item["status"] == "published" else item["status"],
                "quality_score": evaluation["quality_score"],
                "completeness_score": evaluation["essential_completion"],
                "evidence_score": evaluation["evidence_score"],
                "confidence_score": 96,
            },
            actor_id=4,
        )
        created += 1
        if item["status"] == "published":
            review_knowledge(knowledge_id, "approve", "تأیید خودکار داده نمونه دمو", reviewer=2)
            add_document(
                filename=f"demo_knowledge_{knowledge_id}.jsonl",
                stored_path=f"demo://knowledge/{knowledge_id}",
                mime_type="application/x-ndjson",
                category="demo_knowledge",
                tags=structured["tags"],
                status="demo_ready",
                page_count=1,
                quality_score=evaluation["quality_score"],
                knowledge_id=knowledge_id,
            )
            published += 1

    gap_question = "چگونه دانش افراد در آستانه بازنشستگی به‌صورت برنامه‌ریزی‌شده منتقل شود؟"
    if one("SELECT id FROM knowledge_gaps WHERE question=?", (gap_question,)) is None:
        create_gap({"question": gap_question, "priority": "high"})

    return {"created": created, "published": published}


def _tokens(text: str) -> set[str]:
    normalized = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("‌", " ").lower()
    stop_words = {"برای", "چه", "چگونه", "است", "شود", "باید", "این", "آن", "در", "از", "به", "را", "و", "با"}
    return {
        token
        for token in re.findall(r"[\u0600-\u06FFA-Za-z0-9-]+", normalized)
        if len(token) > 1 and token not in stop_words
    }


def demo_chat(question: str) -> dict[str, Any]:
    """Return a deterministic, source-grounded answer without external AI calls."""
    query_tokens = _tokens(question)
    candidates: list[tuple[float, dict[str, Any]]] = []
    with connect() as connection:
        rows = connection.execute(
            "SELECT id,title,summary,content,structured_data FROM knowledge_items WHERE status='published'"
        ).fetchall()
    for row in rows:
        item = get_knowledge(int(row["id"]))
        if not item:
            continue
        structured = item.get("structured_data", {})
        title_tokens = _tokens(item.get("title", ""))
        body_tokens = _tokens(
            " ".join(
                str(structured.get(field, ""))
                for field in ("summary", "problem", "action_taken", "result", "lesson_learned", "tags")
            )
        )
        title_overlap = len(query_tokens & title_tokens)
        body_overlap = len(query_tokens & body_tokens)
        score = min(1.0, (2.5 * title_overlap + body_overlap) / max(4, len(query_tokens) + 1))
        if score > 0:
            candidates.append((score, item))

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    if not candidates or candidates[0][0] < 0.18:
        gap_id = create_gap({"question": question})
        return {
            "answer": "در دانش‌های منتشرشده دمو، منبع کافی برای پاسخ معتبر پیدا نشد. پرسش به‌عنوان شکاف دانشی ثبت شد.",
            "sources": [],
            "gap_id": gap_id,
            "relevance": {"level": "none", "best_score": 0.0, "average_score": 0.0, "document_count": 0},
            "demo": True,
        }

    selected = candidates[:3]
    best_score, best = selected[0]
    data = best["structured_data"]
    answer_parts = [f"بر اساس دانش تأییدشده «{best['title']}»: ", best.get("summary", "")]
    if data.get("action_taken"):
        answer_parts.append(f"\n\n**روش پیشنهادی:** {data['action_taken']}")
    if data.get("action_steps"):
        answer_parts.append(f"\n\n**مراحل اجرا:** {data['action_steps']}")
    if data.get("result") or data.get("lesson_learned"):
        answer_parts.append(f"\n\n**نکته کلیدی:** {data.get('lesson_learned') or data.get('result')}")
    answer_parts.append("\n\n_این پاسخ در Demo Mode به‌صورت محلی و فقط از دانش‌های منتشرشده ساخته شده است._")

    scores = [score for score, _item in selected]
    sources = [
        {
            "source": f"demo_knowledge_{item['id']}",
            "knowledge_id": item["id"],
            "page": 1,
            "score": round(score, 4),
            "excerpt": item.get("summary", "")[:350],
        }
        for score, item in selected
    ]
    return {
        "answer": "".join(answer_parts),
        "sources": sources,
        "relevance": {
            "level": "strong" if best_score >= 0.55 else "partial",
            "best_score": round(best_score, 4),
            "average_score": round(sum(scores) / len(scores), 4),
            "document_count": len(selected),
        },
        "demo": True,
    }
