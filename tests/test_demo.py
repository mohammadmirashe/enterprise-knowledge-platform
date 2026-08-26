from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import dashboard, init_db
from app.demo import demo_chat, seed_demo_data
from app.main import app
from config import settings


def test_demo_seed_is_idempotent_and_chat_is_grounded(tmp_path):
    original = settings.sqlite_path
    object.__setattr__(settings, "sqlite_path", tmp_path / "demo.db")
    try:
        init_db()
        first = seed_demo_data()
        second = seed_demo_data()

        assert first == {"created": 5, "published": 4}
        assert second == {"created": 0, "published": 0}

        metrics = dashboard()
        assert metrics["knowledge_total"] == 5
        assert metrics["published"] == 4
        assert metrics["pending_review"] == 1
        assert metrics["documents"] == 4
        assert metrics["open_gaps"] == 1

        response = demo_chat("برای افزایش دمای یاتاقان پمپ P-101 چه اقدامی لازم است؟")
        assert response["demo"] is True
        assert response["sources"]
        assert "P-101" in response["answer"]
        assert response["relevance"]["best_score"] > 0
    finally:
        object.__setattr__(settings, "sqlite_path", original)


def test_demo_mode_runs_through_real_api_lifespan(tmp_path):
    original_db = settings.sqlite_path
    original_demo_mode = settings.demo_mode
    object.__setattr__(settings, "sqlite_path", tmp_path / "demo_api.db")
    object.__setattr__(settings, "demo_mode", True)
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["demo_mode"] is True

            dashboard_response = client.get("/dashboard")
            assert dashboard_response.status_code == 200
            assert dashboard_response.json()["published"] == 4

            knowledge_map = client.get("/knowledge-map").json()
            assert len(knowledge_map["knowledge"]) == 4
            assert knowledge_map["relations"]

            review_queue = client.get("/knowledge", params={"status": "pending_review"}).json()
            assert len(review_queue) == 1

            review_response = client.post(
                f"/knowledge/{review_queue[0]['id']}/review",
                json={"decision": "approve", "comment": "تأیید در سناریوی دمو", "reviewer_user_id": 2},
            )
            assert review_response.status_code == 200
            assert review_response.json()["status"] == "published"
            assert review_response.json()["index"]["demo"] is True

            chat_response = client.post(
                "/chat",
                json={"question": "در رخداد حساب کاربری مشکوک چه اقدامی لازم است؟"},
            )
            assert chat_response.status_code == 200
            assert chat_response.json()["demo"] is True
            assert chat_response.json()["sources"]
    finally:
        object.__setattr__(settings, "sqlite_path", original_db)
        object.__setattr__(settings, "demo_mode", original_demo_mode)
