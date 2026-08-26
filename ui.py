from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st


DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
st.set_page_config(
    page_title="دموی پلتفرم مدیریت دانش" if DEMO_MODE else "سامانه مدیریت دانش v0.9",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
DEFAULT_API = os.getenv("API_URL", "http://127.0.0.1:8000")
if DEMO_MODE:
    API = DEFAULT_API.rstrip("/")
else:
    API = st.sidebar.text_input("API URL", DEFAULT_API).rstrip("/")
PUBLIC_API = os.getenv("PUBLIC_API_URL", API).rstrip("/")

st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-family: Tahoma, 'Segoe UI', sans-serif; }
    [data-testid="stAppViewContainer"] {
        direction: rtl;
        background: radial-gradient(circle at 8% 0%, rgba(16, 185, 129, .08), transparent 26%),
                    radial-gradient(circle at 92% 2%, rgba(14, 116, 144, .10), transparent 28%),
                    #f7fafc;
    }
    [data-testid="stSidebar"] {
        direction: rtl;
        background: linear-gradient(180deg, #092f3a 0%, #0b4650 56%, #0f5961 100%);
        color: white;
    }
    [data-testid="stSidebar"] * { color: #eefcfb; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.16); }
    .block-container { max-width: 1500px; padding-top: 1.7rem; padding-bottom: 3rem; }
    .demo-hero {
        position: relative; overflow: hidden; padding: 1.6rem 1.8rem; margin-bottom: 1.25rem;
        color: white; border-radius: 22px;
        background: linear-gradient(125deg, #083344 0%, #0e7490 58%, #10b981 120%);
        box-shadow: 0 18px 45px rgba(8, 51, 68, .16);
    }
    .demo-hero:after {
        content: ''; position: absolute; width: 240px; height: 240px; left: -70px; top: -120px;
        border-radius: 50%; background: rgba(255,255,255,.09);
    }
    .demo-kicker { font-size: .78rem; font-weight: 800; letter-spacing: .12em; opacity: .78; }
    .demo-title { font-size: 2rem; line-height: 1.45; font-weight: 800; margin: .35rem 0; }
    .demo-subtitle { max-width: 850px; font-size: .98rem; opacity: .9; line-height: 1.9; }
    .demo-badge {
        display: inline-block; margin-top: .75rem; padding: .28rem .75rem; border-radius: 999px;
        background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.28); font-size: .78rem;
    }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,.94); border: 1px solid #dce8ec; border-radius: 16px;
        padding: .95rem 1rem; box-shadow: 0 7px 24px rgba(15, 58, 70, .06);
    }
    [data-testid="stMetricValue"] { color: #0e6575; font-weight: 800; }
    .stTabs [data-baseweb="tab-list"] {
        gap: .35rem; background: white; border: 1px solid #deeaed; padding: .35rem;
        border-radius: 15px; box-shadow: 0 4px 16px rgba(15, 58, 70, .04);
    }
    .stTabs [data-baseweb="tab"] { border-radius: 11px; padding: .55rem .8rem; }
    .stTabs [aria-selected="true"] { background: #e5f6f4; color: #075d68; }
    .stButton > button { border-radius: 12px; font-weight: 650; }
    [data-testid="stDataFrame"] { border: 1px solid #deeaed; border-radius: 14px; overflow: hidden; }
    .demo-note {
        padding: .8rem .9rem; border-radius: 13px; background: rgba(255,255,255,.10);
        border: 1px solid rgba(255,255,255,.16); line-height: 1.9; font-size: .85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ◈ EKP")
    st.caption("Enterprise Knowledge Platform")
    if DEMO_MODE:
        st.markdown(
            "<div class='demo-note'><b>● نسخه نمایشی فعال است</b><br>داده‌ها ساختگی‌اند و هیچ تماس خارجی با مدل زبانی انجام نمی‌شود.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### مسیر پیشنهادی نمایش")
        st.markdown(
            "1. شاخص‌ها را در **داشبورد** ببینید.\n2. یک رکورد را در **بازبینی** تأیید کنید.\n3. روابط را در **نقشه دانش** بررسی کنید.\n4. سؤال نمونه را در **جست‌وجو و RAG** اجرا کنید."
        )
        st.divider()
        st.caption(f"Backend: {API}")
    else:
        st.info("برای اجرای نسخه نمایشی، `DEMO_MODE=true` را تنظیم کنید.")

KNOWLEDGE_TYPES = {
    "تجربه و درس‌آموخته": "lesson_learned",
    "روش، رویه یا فرایند": "procedure",
    "راهنمای فنی یا نرم‌افزاری": "technical_guide",
    "سیاست، ضابطه یا آیین‌نامه": "policy",
    "تصمیم و تحلیل مدیریتی": "decision_record",
    "گزارش و تحلیل": "report",
    "پرسش و پاسخ": "faq",
    "مرجع و استاندارد": "reference",
    "سایر": "other",
}
TYPE_LABELS = {value: label for label, value in KNOWLEDGE_TYPES.items()}
RELATION_LABELS = {
    "HAS_TYPE": "نوع دانش",
    "BELONGS_TO_UNIT": "متعلق به واحد",
    "COVERS_TOPIC": "پوشش موضوع",
    "CONSIDERS": "بررسی گزینه",
    "EXPLAINED_BY": "مبتنی بر",
    "DESCRIBES": "شرح می‌دهد",
    "PRODUCES": "منجر می‌شود به",
    "RELATED_TO": "مرتبط با",
    "RELATED_ASSET": "دارایی مرتبط",
}


def _error_message(response: requests.Response) -> str:
    try:
        detail = response.json().get("detail", response.text)
        return json.dumps(detail, ensure_ascii=False) if isinstance(detail, (dict, list)) else str(detail)
    except Exception:
        return response.text


def get(path: str) -> Any:
    response = requests.get(API + path, timeout=60)
    if not response.ok:
        raise RuntimeError(_error_message(response))
    return response.json()


def post(path: str, payload: dict[str, Any] | None = None, files=None, data=None) -> Any:
    response = requests.post(
        API + path,
        json=payload if files is None else None,
        files=files,
        data=data,
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(_error_message(response))
    return response.json()


def patch(path: str, payload: dict[str, Any]) -> Any:
    response = requests.patch(API + path, json=payload, timeout=120)
    if not response.ok:
        raise RuntimeError(_error_message(response))
    return response.json()


def fail(error: Exception) -> None:
    st.error(f"خطا: {error}")


def safe_index(options: list[Any], value: Any, default: int = 0) -> int:
    return options.index(value) if value in options else default


def select_demo_question(question: str) -> None:
    st.session_state["rag_question_input"] = question


def graphviz_from_map(data: dict[str, Any]) -> str:
    lines = ["digraph KnowledgeMap {", "rankdir=LR;", 'node [shape=box, style="rounded"];']
    seen: set[str] = set()
    for relation in data.get("relations", [])[:180]:
        source = str(relation.get("source_label", ""))[:90]
        target = str(relation.get("target_label", ""))[:90]
        if not source or not target:
            continue
        knowledge_id = relation.get("knowledge_id")
        source_id = f"n{abs(hash((source, knowledge_id)))}"
        target_id = f"n{abs(hash((target, knowledge_id, 'target')))}"
        if source_id not in seen:
            lines.append(f'{source_id} [label="{source.replace(chr(34), chr(39))}"];')
            seen.add(source_id)
        if target_id not in seen:
            lines.append(f'{target_id} [label="{target.replace(chr(34), chr(39))}"];')
            seen.add(target_id)
        relation_label = RELATION_LABELS.get(
            str(relation.get("relation_type", "")), str(relation.get("relation_type", ""))
        )
        lines.append(f'{source_id} -> {target_id} [label="{relation_label}"];')
    lines.append("}")
    return "\n".join(lines)


st.markdown(
    f"""
    <section class="demo-hero">
      <div class="demo-kicker">ENTERPRISE KNOWLEDGE PLATFORM · v0.9</div>
      <div class="demo-title">دانش سازمانی؛ از تجربه پراکنده تا تصمیم قابل اتکا</div>
      <div class="demo-subtitle">ثبت ساخت‌یافته، ارزیابی کیفیت و شواهد، بازبینی انسانی، نقشه دانش و بازیابی منبع‌محور در یک جریان یکپارچه و فارسی‌محور.</div>
      {"<span class='demo-badge'>DEMO MODE · داده ساختگی · اجرای کاملاً محلی</span>" if DEMO_MODE else ""}
    </section>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs(["داشبورد", "ثبت دانش", "بازبینی", "نقشه دانش", "جست‌وجو و RAG", "اسناد", "شکاف‌ها", "ممیزی"])


with tabs[0]:
    try:
        dashboard = get("/dashboard")
        metrics = [
            ("کل دانش", dashboard["knowledge_total"]),
            ("منتشرشده", dashboard["published"]),
            ("در انتظار بازبینی", dashboard["pending_review"]),
            ("شکاف باز", dashboard["open_gaps"]),
            ("سررسید بازبینی", dashboard["stale_or_due"]),
            ("بدون مالک", dashboard["without_owner"]),
            ("بازخورد", dashboard["feedback_total"]),
            ("اسناد", dashboard["documents"]),
        ]
        columns = st.columns(4)
        for index, (label, value) in enumerate(metrics):
            columns[index % 4].metric(label, value)
        items = get("/knowledge")
        if items:
            st.dataframe(items, use_container_width=True, hide_index=True)
        else:
            st.info("هنوز دانشی ثبت نشده است.")
    except Exception as error:
        fail(error)


with tabs[1]:
    try:
        users = get("/users")
        domains = get("/domains")
        user_by_name = {user["full_name"]: user["id"] for user in users}
        user_by_id = {user["id"]: user for user in users}
        domain_by_name = {domain["name"]: domain["id"] for domain in domains}

        st.info(
            "یک توضیح کوتاه وارد کنید، فقط سند را بارگذاری کنید، یا هر دو را انجام دهید. "
            "سامانه نوع دانش، عنوان، خلاصه، موضوع، محتوای اصلی، برچسب‌ها و اطلاعات قابل استخراج را خودکار تکمیل می‌کند."
        )

        if "capture_session_id" not in st.session_state:
            st.session_state.capture_session_id = None
        if "last_knowledge_id" not in st.session_state:
            st.session_state.last_knowledge_id = None

        if st.button("شروع ثبت دانش جدید", type="primary"):
            session = post("/knowledge-capture/sessions", {"user_id": 4, "mode": "fast"})
            st.session_state.capture_session_id = session["id"]
            st.session_state.last_knowledge_id = None
            st.rerun()

        session_id = st.session_state.capture_session_id
        if not session_id:
            st.warning("برای شروع روی «شروع ثبت دانش جدید» کلیک کنید.")
        else:
            session = get(f"/knowledge-capture/sessions/{session_id}")
            form_data = session.get("form_data", {})
            validation = post(f"/knowledge-capture/sessions/{session_id}/validate")

            metric_columns = st.columns(4)
            metric_columns[0].metric("تکمیل ضروری", f"{validation['essential_completion']}٪")
            metric_columns[1].metric("کیفیت محتوا", f"{validation['quality_score']}٪")
            metric_columns[2].metric("اعتبار مستندات", f"{validation['evidence_score']}٪")
            metric_columns[3].metric("اطمینان استخراج", f"{validation['confidence_score']}٪")

            source_col, upload_col = st.columns(2)
            with source_col:
                st.subheader("توضیح اختیاری")
                source_text = st.text_area(
                    "هر آنچه می‌دانید طبیعی و یک‌جا بنویسید",
                    height=210,
                    placeholder="مثلاً یک تجربه کاری، روش انجام کار، تصمیم، تحلیل، دستورالعمل، نکته مالی، فرایند منابع انسانی یا راهنمای فنی...",
                )
                if st.button("تحلیل توضیح و تکمیل خودکار فرم", disabled=not source_text.strip()):
                    post(f"/knowledge-capture/sessions/{session_id}/messages", {"message": source_text})
                    st.success("توضیح تحلیل و فرم به‌روزرسانی شد.")
                    st.rerun()

            with upload_col:
                st.subheader("بارگذاری سند")
                upload = st.file_uploader(
                    "PDF، تصویر، Word، Excel یا متن",
                    type=["pdf", "png", "jpg", "jpeg", "txt", "md", "docx", "xlsx"],
                    key=f"knowledge_source_{session_id}",
                )
                if upload and st.button("بارگذاری، تحلیل و اتصال سند", key=f"attach_{session_id}"):
                    files = {"file": (upload.name, upload.getvalue(), upload.type or "application/octet-stream")}
                    result_data = post(
                        "/attachments/upload",
                        files=files,
                        data={"session_id": session_id, "category": "source_document"},
                    )
                    if result_data.get("extraction_error"):
                        st.warning("فایل متصل شد، اما استخراج کامل متن ممکن نبود: " + result_data["extraction_error"])
                    elif result_data.get("extracted_fields"):
                        st.success("سند تحلیل شد و فرم از محتوای آن تکمیل شد.")
                    else:
                        st.success("سند به دانش متصل شد.")
                    st.rerun()

                attachments = session.get("attachments", [])
                if attachments:
                    st.markdown("**اسناد متصل‌شده**")
                    for attachment in attachments:
                        st.markdown(
                            f"- [{attachment['filename']}]({PUBLIC_API}/attachments/{attachment['id']}/download)"
                        )
                else:
                    st.caption("کاربر می‌تواند بدون هیچ توضیحی فقط یک سند بارگذاری کند.")

            st.divider()
            st.subheader("فرم عمومی دانش — تکمیل خودکار و قابل ویرایش")
            st.caption("فیلدهای تخصصی فقط وقتی از جنس دانش قابل استخراج باشند پر می‌شوند و هیچ‌کدام اجباری نیستند.")

            type_values = list(KNOWLEDGE_TYPES.values())
            selected_type_value = form_data.get("knowledge_type", "other")
            selected_type_label = TYPE_LABELS.get(selected_type_value, "سایر")

            identity_a, identity_b = st.columns([1, 2])
            knowledge_type_label = identity_a.selectbox(
                "نوع دانش",
                list(KNOWLEDGE_TYPES),
                index=safe_index(list(KNOWLEDGE_TYPES), selected_type_label, len(KNOWLEDGE_TYPES) - 1),
            )
            title = identity_b.text_input("عنوان خودکار", form_data.get("title", ""))
            summary = st.text_area("خلاصه خودکار", form_data.get("summary", ""), height=100)

            problem = st.text_area("موضوع، نیاز یا وضعیت *", form_data.get("problem", ""), height=100)
            action = st.text_area("شرح دانش، راهکار یا روش اصلی *", form_data.get("action_taken", ""), height=180)
            action_steps = st.text_area("مراحل اجرا یا استفاده", form_data.get("action_steps", ""), height=110)

            detail_a, detail_b = st.columns(2)
            occurrence = detail_a.text_area(
                "زمینه و شرایط کاربرد", form_data.get("occurrence_conditions", ""), height=90
            )
            symptoms = detail_b.text_area("داده‌ها، نشانه‌ها یا ورودی‌های مرتبط", form_data.get("symptoms", ""), height=90)
            investigation = detail_a.text_area(
                "بررسی‌ها، تحلیل‌ها یا منابع استفاده‌شده", form_data.get("investigation_steps", ""), height=100
            )
            root_cause = detail_b.text_area("علت، منطق یا مبنای تصمیم", form_data.get("root_cause", ""), height=100)
            verification = detail_a.text_area(
                "روش کنترل، ارزیابی یا تأیید", form_data.get("verification", ""), height=90
            )
            result = detail_b.text_area("نتیجه، خروجی یا اثر", form_data.get("result", ""), height=90)
            lesson = detail_a.text_area("نکات کلیدی و توصیه‌ها", form_data.get("lesson_learned", ""), height=100)
            limitations = detail_b.text_area(
                "محدودیت‌ها، استثناها و شرایط عدم کاربرد", form_data.get("limitations", ""), height=100
            )
            safety = st.text_area("ریسک‌ها، کنترل‌ها و ملاحظات مهم", form_data.get("safety_notes", ""), height=90)

            st.markdown("#### اطلاعات حاکمیتی")
            default_owner_id = form_data.get("owner_user_id") or 4
            default_owner_name = next(
                (name for name, user_id in user_by_name.items() if user_id == default_owner_id), list(user_by_name)[0]
            )
            owner_options = list(user_by_name)
            governance_a, governance_b, governance_c = st.columns(3)
            owner = governance_a.selectbox(
                "مالک دانش *", owner_options, index=safe_index(owner_options, default_owner_name, 0)
            )
            default_unit = form_data.get("unit") or user_by_id.get(user_by_name[owner], {}).get("unit", "")
            unit = governance_b.text_input("واحد سازمانی *", default_unit)
            sensitivity_options = ["internal", "restricted", "confidential"]
            sensitivity = governance_c.selectbox(
                "سطح دسترسی *",
                sensitivity_options,
                index=safe_index(sensitivity_options, form_data.get("sensitivity") or "internal", 0),
            )

            domain_options = ["انتخاب نشده"] + list(domain_by_name)
            current_domain = next(
                (name for name, domain_id in domain_by_name.items() if domain_id == form_data.get("domain_id")),
                "انتخاب نشده",
            )
            meta_a, meta_b, meta_c = st.columns(3)
            domain = meta_a.selectbox("حوزه دانش", domain_options, index=safe_index(domain_options, current_domain, 0))
            project = meta_b.text_input("پروژه، فرایند یا سامانه مرتبط", form_data.get("project", ""))
            asset = meta_c.text_input("شناسه تجهیز، سامانه یا دارایی", form_data.get("equipment_tag", ""))
            tags = st.text_input("برچسب‌های خودکار", form_data.get("tags", ""))

            form_payload: dict[str, Any] = {
                "knowledge_type": KNOWLEDGE_TYPES[knowledge_type_label],
                "title": title,
                "summary": summary,
                "problem": problem,
                "action_taken": action,
                "action_steps": action_steps,
                "occurrence_conditions": occurrence,
                "symptoms": symptoms,
                "investigation_steps": investigation,
                "root_cause": root_cause,
                "verification": verification,
                "result": result,
                "lesson_learned": lesson,
                "limitations": limitations,
                "safety_notes": safety,
                "unit": unit,
                "owner_user_id": user_by_name[owner],
                "owner_text": form_data.get("owner_text", ""),
                "sensitivity": sensitivity,
                "domain_id": None if domain == "انتخاب نشده" else domain_by_name[domain],
                "project": project,
                "equipment_tag": asset,
                "tags": tags,
                "evidence": form_data.get("evidence", ""),
                "source_filename": form_data.get("source_filename", ""),
                "initial_hypothesis": form_data.get("initial_hypothesis", ""),
                "root_cause_status": form_data.get("root_cause_status", ""),
                "transfer_message": form_data.get("transfer_message", ""),
            }

            existing_knowledge_id = st.session_state.get("last_knowledge_id") or session.get("knowledge_id")
            if existing_knowledge_id:
                st.info(f"این نشست قبلاً به پیش‌نویس دانش #{existing_knowledge_id} تبدیل شده است.")

            action_columns = st.columns([1, 1, 2])
            if action_columns[0].button(
                "ذخیره تغییرات فرم", key=f"save_form_{session_id}", disabled=bool(existing_knowledge_id)
            ):
                patch(f"/knowledge-capture/sessions/{session_id}/form", {"form_data": form_payload})
                st.success("فرم ذخیره شد.")
                st.rerun()

            core_ready = bool(problem.strip() and action.strip())
            if action_columns[1].button(
                "ذخیره و ساخت پیش‌نویس",
                type="primary",
                disabled=not core_ready or bool(existing_knowledge_id),
                key=f"confirm_{session_id}",
            ):
                patch(f"/knowledge-capture/sessions/{session_id}/form", {"form_data": form_payload})
                result_data = post(f"/knowledge-capture/sessions/{session_id}/confirm")
                st.session_state.last_knowledge_id = result_data["knowledge_id"]
                st.success(f"دانش #{result_data['knowledge_id']} در پایگاه داده ذخیره شد.")
                st.rerun()

            last_knowledge_id = existing_knowledge_id
            if last_knowledge_id:
                action_columns[2].link_button("دانلود PDF فرم", f"{PUBLIC_API}/knowledge/{last_knowledge_id}/pdf")
                if st.button("ارسال پیش‌نویس برای بازبینی", type="primary", key=f"submit_{last_knowledge_id}"):
                    post(f"/knowledge/{last_knowledge_id}/submit")
                    st.success("دانش برای بازبینی ارسال شد.")
                    st.session_state.capture_session_id = None
                    st.session_state.last_knowledge_id = None
                    st.rerun()
    except Exception as error:
        fail(error)


with tabs[2]:
    try:
        review_items = (
            get("/knowledge?status=pending_review")
            + get("/knowledge?status=needs_changes")
            + get("/knowledge?status=draft")
        )
        if not review_items:
            st.info("موردی برای بازبینی وجود ندارد.")
        else:
            item_map = {f"#{item['id']} - {item['title']} [{item['status']}]": item["id"] for item in review_items}
            knowledge_id = item_map[st.selectbox("انتخاب دانش", list(item_map))]
            knowledge = get(f"/knowledge/{knowledge_id}")
            structured = knowledge.get("structured_data", {})

            header_a, header_b, header_c, header_d = st.columns(4)
            header_a.metric("نسخه", knowledge["version"])
            header_b.metric("کیفیت", f"{knowledge.get('quality_score', 0)}٪")
            header_c.metric("تکمیل", f"{knowledge.get('completeness_score', 0)}٪")
            header_d.metric("مستندات", f"{knowledge.get('evidence_score', 0)}٪")
            st.link_button("دانلود PDF بازبینی", f"{PUBLIC_API}/knowledge/{knowledge_id}/pdf")

            left, right = st.columns([1.45, 1])
            with left:
                st.subheader(knowledge["title"])
                st.caption(
                    f"وضعیت: {knowledge['status']} | نوع: {TYPE_LABELS.get(knowledge.get('knowledge_type'), knowledge.get('knowledge_type'))} | "
                    f"مالک: {knowledge.get('owner_name') or knowledge.get('owner_text') or '-'}"
                )
                review_fields = {
                    "summary": "خلاصه",
                    "problem": "موضوع، نیاز یا وضعیت",
                    "action_taken": "شرح دانش، راهکار یا روش اصلی",
                    "action_steps": "مراحل اجرا یا استفاده",
                    "occurrence_conditions": "زمینه و شرایط کاربرد",
                    "symptoms": "داده‌ها، نشانه‌ها یا ورودی‌ها",
                    "investigation_steps": "بررسی‌ها، تحلیل‌ها یا منابع",
                    "root_cause": "علت، منطق یا مبنای تصمیم",
                    "verification": "روش کنترل یا تأیید",
                    "result": "نتیجه، خروجی یا اثر",
                    "lesson_learned": "نکات کلیدی و توصیه‌ها",
                    "limitations": "محدودیت‌ها و استثناها",
                    "safety_notes": "ریسک‌ها و ملاحظات",
                }
                edits: dict[str, str] = {}
                for field, label in review_fields.items():
                    edits[field] = st.text_area(
                        label,
                        structured.get(field, ""),
                        height=90 if field != "action_taken" else 150,
                        key=f"review_{knowledge_id}_{field}",
                    )
                change_reason = st.text_input("علت تغییر", "اصلاح در بازبینی")
                if st.button("ذخیره اصلاحات و ایجاد نسخه جدید", key=f"review_save_{knowledge_id}"):
                    patch(
                        f"/knowledge/{knowledge_id}",
                        {
                            "data": {
                                "structured_data": edits,
                                "title": knowledge["title"],
                                "summary": edits.get("summary", ""),
                            },
                            "change_reason": change_reason,
                        },
                    )
                    st.success("اصلاحات ذخیره و نسخه جدید ایجاد شد.")
                    st.rerun()

            with right:
                st.markdown("#### پیوست‌ها")
                if knowledge.get("attachments"):
                    for attachment in knowledge["attachments"]:
                        st.markdown(
                            f"- [{attachment['filename']}]({PUBLIC_API}/attachments/{attachment['id']}/download)"
                        )
                else:
                    st.caption("پیوستی ثبت نشده است.")

                st.markdown("#### نسخه‌ها")
                st.dataframe(knowledge.get("versions", []), use_container_width=True, hide_index=True)
                st.markdown("#### تصمیم بازبین")
                decision_labels = {"تأیید و انتشار": "approve", "نیازمند اصلاح": "changes", "رد": "reject"}
                decision_label = st.selectbox("تصمیم", list(decision_labels), key=f"decision_{knowledge_id}")
                comment = st.text_area("نظر کلی بازبین", key=f"comment_{knowledge_id}")
                if st.button("ثبت تصمیم", type="primary", key=f"decision_submit_{knowledge_id}"):
                    result_data = post(
                        f"/knowledge/{knowledge_id}/review",
                        {
                            "decision": decision_labels[decision_label],
                            "comment": comment,
                            "reviewer_user_id": 2,
                            "field_comments": {},
                        },
                    )
                    if result_data["status"] == "published":
                        st.success("دانش تأیید و منتشر شد؛ اکنون در اسناد و نقشه دانش قابل مشاهده است.")
                        if result_data.get("index", {}).get("error"):
                            st.warning("رکورد در اسناد و نقشه دانش ثبت شد، اما ایندکس RAG در این اجرا تکمیل نشد.")
                    else:
                        st.success(f"تصمیم ثبت شد. وضعیت جدید: {result_data['status']}")
                    st.rerun()
                if knowledge.get("reviews"):
                    st.dataframe(knowledge["reviews"], use_container_width=True, hide_index=True)
    except Exception as error:
        fail(error)


with tabs[3]:
    try:
        map_data = get("/knowledge-map")
        st.subheader("نقشه دانش سازمان")
        st.caption("فقط دانش‌های تأیید و منتشرشده در این نقشه نمایش داده می‌شوند.")
        risk = map_data.get("risk", [])
        if risk:
            risk_columns = st.columns(4)
            risk_columns[0].metric("حوزه‌ها", len(risk))
            risk_columns[1].metric("دانش بدون مالک", sum(item.get("without_owner", 0) or 0 for item in risk))
            risk_columns[2].metric("دانش منتشرشده", sum(item.get("published", 0) or 0 for item in risk))
            risk_columns[3].metric("بازبینی عقب‌افتاده", sum(item.get("overdue", 0) or 0 for item in risk))

        published = map_data.get("knowledge", [])
        if published:
            st.markdown("#### دانش‌های منتشرشده")
            st.dataframe(published, use_container_width=True, hide_index=True)

        hierarchy, graph = st.columns([1, 1.4])
        with hierarchy:
            st.markdown("#### درخت حوزه‌ها")
            domains = map_data.get("domains", [])
            roots = [domain for domain in domains if not domain.get("parent_id")]
            children: dict[int, list[dict[str, Any]]] = {}
            for domain in domains:
                if domain.get("parent_id"):
                    children.setdefault(domain["parent_id"], []).append(domain)
            for root in roots:
                st.markdown(f"**{root['name']}** — {root.get('item_count', 0)} دانش")
                for child in children.get(root["id"], []):
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;↳ {child['name']} — {child.get('item_count', 0)} دانش",
                        unsafe_allow_html=True,
                    )
        with graph:
            st.markdown("#### گراف ارتباط دانش")
            if map_data.get("relations"):
                st.graphviz_chart(graphviz_from_map(map_data), use_container_width=True)
            else:
                st.info(
                    "پس از تأیید اولین دانش، ارتباط موضوع، نوع، واحد، روش، نتیجه و زمینه در اینجا نمایش داده می‌شود."
                )

        st.markdown("#### موجودیت‌های استخراج‌شده")
        st.dataframe(map_data.get("entities", []), use_container_width=True, hide_index=True)

        users = get("/users")
        user_map = {user["full_name"]: user["id"] for user in users}
        domain_map = {"بدون والد": None, **{domain["name"]: domain["id"] for domain in map_data.get("domains", [])}}
        with st.expander("تعریف حوزه جدید"):
            with st.form("new_domain"):
                name = st.text_input("نام حوزه")
                parent = st.selectbox("حوزه والد", list(domain_map))
                owner = st.selectbox("مالک حوزه", list(user_map))
                review_days = st.number_input("دوره بازبینی (روز)", 30, 730, 180)
                if st.form_submit_button("ایجاد حوزه"):
                    post(
                        "/domains",
                        {
                            "name": name,
                            "parent_id": domain_map[parent],
                            "owner_user_id": user_map[owner],
                            "review_days": review_days,
                            "access_level": "internal",
                        },
                    )
                    st.success("حوزه ایجاد شد.")
                    st.rerun()
    except Exception as error:
        fail(error)


with tabs[4]:
    st.subheader("پرسش از حافظه سازمانی")
    st.caption("پاسخ فقط زمانی ساخته می‌شود که دانش منتشرشده و قابل استناد در دسترس باشد.")
    if DEMO_MODE:
        try:
            demo_status_data = get("/demo/status")
            questions = demo_status_data.get("sample_questions", [])
        except Exception:
            questions = []
        if questions:
            st.markdown("#### سؤال‌های پیشنهادی")
            question_columns = st.columns(2)
            for index, sample_question in enumerate(questions):
                question_columns[index % 2].button(
                    sample_question,
                    key=f"demo_question_{index}",
                    on_click=select_demo_question,
                    args=(sample_question,),
                    use_container_width=True,
                )
    question = st.text_area(
        "سؤال خود را وارد کنید",
        key="rag_question_input",
        placeholder="مثلاً: برای جلوگیری از افزایش دمای یاتاقان پمپ P-101 چه کاری باید انجام شود؟",
        height=110,
    )
    if st.button("پرسش", key="rag_question") and question:
        try:
            with st.spinner("در حال بازیابی دانش‌های مرتبط و ساخت پاسخ منبع‌محور..."):
                result_data = post("/chat", {"question": question})
            st.markdown("#### پاسخ")
            st.markdown(result_data["answer"])
            relevance = result_data.get("relevance", {})
            relevance_columns = st.columns(3)
            relevance_columns[0].metric("سطح ارتباط", relevance.get("level", "—"))
            relevance_columns[1].metric("بهترین امتیاز", f"{float(relevance.get('best_score', 0)):.0%}")
            relevance_columns[2].metric("منابع بازیابی‌شده", relevance.get("document_count", 0))
            if result_data.get("sources"):
                with st.expander("مشاهده منابع و امتیازهای بازیابی", expanded=True):
                    st.dataframe(result_data["sources"], use_container_width=True, hide_index=True)
        except Exception as error:
            fail(error)


with tabs[5]:
    try:
        documents = get("/documents")
        if documents:
            st.dataframe(documents, use_container_width=True, hide_index=True)
        else:
            st.info("پس از تأیید دانش، نسخه منتشرشده و فایل‌های پیوست‌شده به‌صورت خودکار اینجا ثبت می‌شوند.")
    except Exception as error:
        fail(error)


with tabs[6]:
    try:
        st.dataframe(get("/gaps"), use_container_width=True, hide_index=True)
    except Exception as error:
        fail(error)


with tabs[7]:
    try:
        st.dataframe(get("/audit"), use_container_width=True, hide_index=True)
    except Exception as error:
        fail(error)
