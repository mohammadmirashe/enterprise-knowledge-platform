from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
import re
from typing import Any

import fitz


STATUS_LABELS = {
    "preview": "پیش‌نمایش - ذخیره‌نشده",
    "draft": "پیش‌نویس",
    "pending_review": "در انتظار بازبینی",
    "needs_changes": "نیازمند اصلاح",
    "published": "منتشرشده",
    "rejected": "ردشده",
    "archived": "بایگانی‌شده",
}

SENSITIVITY_LABELS = {
    "internal": "داخلی",
    "restricted": "محدود",
    "confidential": "محرمانه",
    "public": "عمومی",
}

SECTION_LABELS = {
    "summary": "خلاصه",
    "problem": "موضوع، نیاز یا وضعیت",
    "occurrence_conditions": "زمینه و شرایط کاربرد",
    "symptoms": "داده‌ها، نشانه‌ها یا ورودی‌های مرتبط",
    "action_taken": "شرح دانش، راهکار یا روش اصلی",
    "action_steps": "مراحل اجرا یا استفاده",
    "investigation_steps": "بررسی‌ها، تحلیل‌ها یا منابع استفاده‌شده",
    "initial_hypothesis": "فرضیات یا گزینه‌های اولیه",
    "root_cause": "علت، منطق یا مبنای تصمیم",
    "root_cause_status": "وضعیت اعتبار تحلیل",
    "verification": "روش کنترل، ارزیابی یا تأیید",
    "result": "نتیجه، خروجی یا اثر",
    "lesson_learned": "درس‌آموخته، نکات کلیدی و توصیه‌ها",
    "limitations": "محدودیت‌ها، استثناها و شرایط عدم کاربرد",
    "safety_notes": "ریسک‌ها، کنترل‌ها و ملاحظات مهم",
    "evidence": "منابع و مستندات",
    "project": "پروژه، فرایند یا سامانه مرتبط",
    "transfer_message": "پیام انتقال دانش",
    "tags": "برچسب‌ها",
}


def _text(value: Any, missing: str = "ثبت نشده") -> str:
    value = "" if value is None else str(value).strip()
    return value or missing


def _html(value: Any, missing: str = "") -> str:
    value = "" if value is None else str(value).strip()
    if not value:
        value = missing
    return escape(value).replace("\n", "<br>")


def _find_font() -> tuple[Path | None, Path | None]:
    """Return a Persian-capable regular and bold font already installed on the host."""
    pairs = (
        ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        (
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        ),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    )
    for regular, bold in pairs:
        regular_path = Path(regular)
        if regular_path.exists():
            bold_path = Path(bold)
            return regular_path, bold_path if bold_path.exists() else None
    return None, None


def _font_resources() -> tuple[fitz.Archive | None, str]:
    regular, bold = _find_font()
    if regular is None:
        # MuPDF's generic sans-serif font fallback still supports most Unicode
        # environments. The explicit path is preferred whenever available.
        return None, "body { font-family: sans-serif; }"

    archive = fitz.Archive(str(regular.parent))
    css = f"@font-face {{font-family: KMSPersian; src: url('{regular.name}'); font-weight: 400;}}"
    if bold:
        css += f"@font-face {{font-family: KMSPersian; src: url('{bold.name}'); font-weight: 700;}}"
    css += "body {font-family: KMSPersian, sans-serif;}"
    return archive, css


def _normalise_data(knowledge: dict[str, Any]) -> dict[str, Any]:
    data = dict(knowledge.get("structured_data") or {})
    if knowledge.get("summary") and not data.get("summary"):
        data["summary"] = knowledge["summary"]
    if knowledge.get("title") and not data.get("title"):
        data["title"] = knowledge["title"]
    if knowledge.get("equipment_tag") and not data.get("equipment_tag"):
        data["equipment_tag"] = knowledge["equipment_tag"]
    if knowledge.get("unit") and not data.get("unit"):
        data["unit"] = knowledge["unit"]
    return data


def _status(value: Any) -> str:
    raw = str(value or "").strip()
    return STATUS_LABELS.get(raw, raw or "ثبت نشده")


def _sensitivity(value: Any) -> str:
    raw = str(value or "").strip()
    return SENSITIVITY_LABELS.get(raw, raw or "ثبت نشده")


def _score_card(label: str, value: Any) -> str:
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        numeric = 0
    numeric = max(0, min(100, numeric))
    return (
        '<td class="score-card" width="33%">'
        f'<div class="score-value">{numeric:.0f}٪</div>'
        f'<div class="score-label">{_html(label)}</div>'
        "</td>"
    )


def _make_html(knowledge: dict[str, Any]) -> str:
    data = _normalise_data(knowledge)
    title = _html(knowledge.get("title") or data.get("title") or "فرم ثبت دانش سازمانی")

    version_value = knowledge.get("version")
    version = "پیش‌نمایش" if str(knowledge.get("status")) == "preview" else _text(version_value)

    meta = [
        ("شناسه دانش", knowledge.get("id")),
        ("وضعیت", _status(knowledge.get("status"))),
        ("نسخه", version),
        ("حوزه دانشی", knowledge.get("domain_name") or data.get("domain_name")),
        ("واحد سازمانی", knowledge.get("unit") or data.get("unit")),
        ("دارایی / سامانه مرتبط", knowledge.get("equipment_tag") or data.get("equipment_tag")),
        ("مالک دانش", knowledge.get("owner_name") or knowledge.get("owner_text") or data.get("owner_text")),
        ("سطح دسترسی", _sensitivity(knowledge.get("sensitivity") or data.get("sensitivity"))),
    ]

    meta_rows = "".join(
        '<div class="meta-item">'
        f'<span class="meta-label">{_html(label)}:</span> '
        f'<span class="meta-value">{_html(value, "ثبت نشده")}</span>'
        "</div>"
        for label, value in meta
    )

    sections: list[str] = []
    for field, label in SECTION_LABELS.items():
        value = data.get(field)
        if not value:
            continue
        if field == "tags":
            if isinstance(value, (list, tuple, set)):
                value = "، ".join(str(item) for item in value if str(item).strip())
            tags = [tag.strip() for tag in str(value).replace(";", "،").split("،") if tag.strip()]
            body = _html("، ".join(tags))
            css_class = "section-body tags"
        else:
            body = _html(value)
            css_class = "section-body"
        sections.append(f'<div class="section-title">{_html(label)}</div><div class="{css_class}">{body}</div>')

    attachments = knowledge.get("attachments") or []
    attachment_html = ""
    if attachments:
        items = "".join(
            '<div class="attachment-item">'
            f"<strong>{_html(item.get('category'), 'سند')}:</strong> "
            f"{_html(item.get('filename'), 'بدون نام')}"
            "</div>"
            for item in attachments
        )
        attachment_html = (
            f'<div class="section-title">پیوست‌ها و اسناد بارگذاری‌شده</div><div class="section-body">{items}</div>'
        )

    reviews = knowledge.get("reviews") or []
    review_html = ""
    if reviews:
        rows = "".join(
            "<tr>"
            f"<td>{_html(item.get('comment'), '-')}</td>"
            f"<td>{_html(item.get('decision'), '-')}</td>"
            f"<td>{_html(item.get('reviewer_name'), '-')}</td>"
            f"<td>{_html(item.get('created_at'), '-')}</td>"
            "</tr>"
            for item in reviews
        )
        review_html = (
            '<div class="section-title">تاریخچه بازبینی</div>'
            '<table class="review-table" width="500"><thead><tr>'
            "<th>نظر</th><th>تصمیم</th><th>بازبین</th><th>تاریخ</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )

    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"></head>
<body>
  <div class="document-header">
    <div class="document-kicker">فرم ثبت و بازبینی دانش سازمانی</div>
    <h1>{title}</h1>
  </div>

  <div class="meta-panel">{meta_rows}</div>

  <div class="score-strip">
    <span>تکمیل اطلاعات: {_html(str(knowledge.get("completeness_score", 0)) + "٪")}</span>
    <span class="separator">|</span>
    <span>کیفیت محتوایی: {_html(str(knowledge.get("quality_score", 0)) + "٪")}</span>
    <span class="separator">|</span>
    <span>اعتبار شواهد: {_html(str(knowledge.get("evidence_score", 0)) + "٪")}</span>
  </div>

  {"".join(sections)}
  {attachment_html}
  {review_html}

  <div class="document-note">
    این سند از سامانه مدیریت دانش تولید شده است. اعتبار نهایی آن تابع وضعیت تأیید و نسخه ثبت‌شده در سامانه است.
  </div>
</body>
</html>"""


def _css(font_css: str) -> str:
    return (
        font_css
        + r"""
@page { size: A4; }
* { box-sizing: border-box; }
html, body {
  direction: rtl;
  text-align: right;
  hyphens: none;
  -webkit-hyphens: none;
  color: #24313a;
  font-size: 10.2pt;
  line-height: 1.75;
  margin: 0;
  padding: 0;
}
body { background: white; }
.document-header {
  border: 1px solid #b8cbd4;
  border-right: 7px solid #14566f;
  background: #edf5f7;
  padding: 12px 15px 10px;
  margin-bottom: 10px;
}
.document-kicker {
  color: #56717d;
  font-size: 8.7pt;
  margin-bottom: 4px;
}
h1 {
  color: #123f52;
  font-size: 17pt;
  font-weight: 700;
  line-height: 1.45;
  margin: 0;
}
table { border-collapse: collapse; width: 100%; }
.meta-panel {
  margin: 8px 0 10px;
  border: 1px solid #b9c4ca;
}
.meta-item {
  border-bottom: 1px solid #d3dadd;
  padding: 6px 9px;
  background: #fbfcfc;
}
.meta-item:last-child { border-bottom: 0; }
.meta-label { color: #284a59; font-weight: 700; }
.meta-value { color: #26343b; }
.score-strip {
  border: 1px solid #c5d1d6;
  background: #f4f8f9;
  color: #14566f;
  padding: 8px 10px;
  margin: 8px 0 11px;
  text-align: center;
  font-weight: 700;
}
.score-strip .separator { color: #95a7af; padding: 0 7px; }
.section-title {
  background: #eaf2f4;
  color: #164c62;
  border: 1px solid #ced8dc;
  border-right: 5px solid #1b708d;
  padding: 5px 8px;
  margin-top: 8px;
  font-weight: 700;
  font-size: 10.4pt;
  page-break-after: avoid;
}
.section-body {
  border-right: 1px solid #ced8dc;
  border-left: 1px solid #ced8dc;
  border-bottom: 1px solid #ced8dc;
  padding: 7px 9px 8px;
  margin-bottom: 3px;
  text-align: justify;
  white-space: normal;
}
.attachment-item { padding: 3px 0; }
.document-note {
  margin-top: 13px;
  border-top: 1px solid #cbd5da;
  padding-top: 7px;
  color: #718087;
  font-size: 8pt;
  text-align: center;
}
"""
    )


def _rect_fn(_rect_num: int, _filled: fitz.Rect) -> tuple[fitz.Rect, fitz.Rect, fitz.Matrix]:
    media = fitz.paper_rect("a4")
    # Reserve the bottom strip for page numbering.
    content = fitz.Rect(43, 42, media.width - 43, media.height - 46)
    return media, content, fitz.Identity


def _searchable_identifiers(value: Any) -> list[str]:
    """Collect technical identifiers that RTL layout may expose with soft hyphens."""
    if isinstance(value, dict):
        text = " ".join(str(item) for item in value.values() if not isinstance(item, (dict, list, tuple, set)))
        nested = [item for item in value.values() if isinstance(item, (dict, list, tuple, set))]
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value if not isinstance(item, (dict, list, tuple, set)))
        nested = [item for item in value if isinstance(item, (dict, list, tuple, set))]
    else:
        text = str(value or "")
        nested = []

    identifiers = re.findall(r"(?<![A-Za-z0-9])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+(?![A-Za-z0-9])", text)
    for item in nested:
        identifiers.extend(_searchable_identifiers(item))
    return list(dict.fromkeys(identifiers))


def _add_page_numbers(
    pdf_bytes: bytes,
    archive: fitz.Archive | None,
    font_css: str,
    searchable_identifiers: list[str],
) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # MuPDF Story may occasionally leave a final empty continuation page when
    # the last block fits exactly at the page boundary. Remove only genuinely
    # empty trailing pages before numbering; content pages are never touched.
    while doc.page_count > 1:
        last = doc[-1]
        has_text = bool(last.get_text().strip())
        has_images = bool(last.get_images(full=True))
        has_drawings = bool(last.get_drawings())
        if has_text or has_images or has_drawings:
            break
        doc.delete_page(doc.page_count - 1)

    total = doc.page_count
    for index, page in enumerate(doc, start=1):
        footer = (
            f'<div dir="rtl" style="font-size:8px; color:#65747b; text-align:center;">صفحه {index} از {total}</div>'
        )
        page.insert_htmlbox(
            fitz.Rect(43, page.rect.height - 35, page.rect.width - 43, page.rect.height - 17),
            footer,
            css=font_css,
            archive=archive,
        )

    # MuPDF's RTL shaping can map an ASCII hyphen to a soft hyphen in the
    # ToUnicode layer. Add an invisible ASCII metadata line so equipment tags
    # and other technical identifiers remain exactly searchable/copyable.
    if searchable_identifiers and doc.page_count:
        doc[0].insert_text(
            fitz.Point(1, 1),
            " ".join(searchable_identifiers),
            fontsize=1,
            render_mode=3,
        )
    output = BytesIO()
    doc.save(output, garbage=3, deflate=True)
    doc.close()
    return output.getvalue()


def make_pdf(knowledge: dict[str, Any]) -> bytes:
    """Generate a cross-platform Persian PDF with native RTL shaping.

    PyMuPDF's HTML story engine uses HarfBuzz for Persian/Arabic shaping and
    therefore avoids the disconnected/reversed glyph problem of ReportLab's
    plain Paragraph renderer. No external browser, GTK, or office suite is
    required.
    """
    archive, font_css = _font_resources()
    story = fitz.Story(
        _make_html(knowledge),
        user_css=_css(font_css),
        em=11,
        archive=archive,
    )
    stream = BytesIO()
    writer = fitz.DocumentWriter(stream)
    story.write(writer, _rect_fn)
    writer.close()
    pdf_bytes = stream.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("تولید PDF ناموفق بود")
    return _add_page_numbers(pdf_bytes, archive, font_css, _searchable_identifiers(knowledge))
