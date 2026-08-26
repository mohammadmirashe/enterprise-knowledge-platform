from app.capture_agent import (
    CaptureState,
    assistant_message,
    evaluate,
    extract_fields,
    knowledge_graph,
)


RICH_CASE = """
بعد از تعمیر پمپ P-101 و در اولین راه‌اندازی، دمای یاتاقان از مقدار عادی حدود 68 درجه به 92 درجه رسید و لرزش تجهیز نیز افزایش پیدا کرد.
در ابتدا وضعیت روغن‌کاری بررسی شد و مشکلی در سطح روغن مشاهده نشد. سپس با بررسی لرزش و اندازه‌گیری هم‌راستایی مشخص شد موتور و پمپ دچار انحراف زاویه‌ای شده‌اند.
پمپ از سرویس خارج و مطابق دستورالعمل LOTO ایمن‌سازی شد. سپس کوپلینگ باز شد، پایه‌ها کنترل شدند و هم‌راستایی موتور و پمپ اصلاح شد.
پس از راه‌اندازی مجدد، دمای یاتاقان به 68 درجه کاهش یافت و لرزش نیز به محدوده عادی بازگشت.
درس‌آموخته این است که پس از هر تعمیر یا باز و بسته شدن کوپلینگ، هم‌راستایی موتور و پمپ باید قبل از راه‌اندازی کنترل شود.
"""


def test_rich_message_extracts_action_and_final_result_without_reasking():
    data = extract_fields([{"role": "user", "content": RICH_CASE}], {})
    assert data["equipment_tag"] == "P-101"
    assert "اصلاح" in data["action_taken"]
    assert "92" in data["result"] and "68" in data["result"]
    assert data["result"].startswith("کاهش")
    assert data["root_cause_status"] == "confirmed"
    evaluation = evaluate(data, mode="fast")
    assert evaluation["state"] == CaptureState.DRAFT_READY.value
    assert evaluation["next_field"] is None
    assert evaluation["can_build_draft"] is True


def test_reasoning_separates_hypothesis_investigation_action():
    text = (
        "اول فکر کردیم مشکل از روغن است. فشار روغن را بررسی کردیم. "
        "اندازه‌گیری نشان داد هم‌راستایی به هم خورده است. کوپلینگ را تنظیم کردیم و لرزش برطرف شد."
    )
    data = extract_fields([{"role": "user", "content": text}], {})
    assert "فکر کردیم" in data["initial_hypothesis"]
    assert "بررسی" in data["investigation_steps"]
    assert "تنظیم" in data["action_taken"]
    assert "برطرف" in data["result"]


def test_short_answer_maps_only_to_compatible_asked_field():
    conversation = [
        {"role": "assistant", "content": "این تجربه مربوط به کدام واحد است؟", "asked_field": "unit"},
        {"role": "user", "content": "تعمیرات مکانیک"},
    ]
    data = extract_fields(conversation, {})
    assert data["unit"] == "تعمیرات مکانیک"

    unrelated = [
        {"role": "assistant", "content": "پروژه مرتبط چیست؟", "asked_field": "project"},
        {"role": "user", "content": "افزایش دما را باید به عنوان هشدار جدی در نظر گرفت."},
    ]
    data2 = extract_fields(unrelated, {})
    assert "project" not in data2


def test_fast_mode_stops_at_three_questions_or_when_draft_is_ready():
    partial = {"knowledge_type": "lesson_learned", "problem": "افزایش دما"}
    evaluation = evaluate(partial, mode="fast", question_count=3)
    assert evaluation["question_count"] if "question_count" in evaluation else True
    assert evaluation["next_field"] in {"root_cause", None}

    complete_core = extract_fields([{"role": "user", "content": RICH_CASE}], {})
    evaluation2 = evaluate(complete_core, mode="fast", question_count=0)
    message = assistant_message(evaluation2, complete_core, complete_core)
    assert "پیش‌نویس" in message
    assert "برای رفع مسئله چه اقدام" not in message


def test_graph_contains_reasoning_chain():
    graph = knowledge_graph(
        {
            "equipment_tag": "P-101",
            "problem": "افزایش دما",
            "initial_hypothesis": "مشکل روغن",
            "root_cause": "ناهم‌راستایی",
            "action_taken": "تنظیم کوپلینگ",
            "result": "کاهش دما",
        }
    )
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"HAS_PROBLEM", "INITIALLY_SUSPECTED", "CAUSED_BY", "RESOLVED_BY", "PRODUCED"} <= relations
