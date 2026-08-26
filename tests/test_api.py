from __future__ import annotations

from langchain_core.documents import Document

from app.main import ChatRequest, chat


def test_chat_uses_structured_relevance_result(monkeypatch):
    relevance = {
        "level": "strong",
        "best_score": 0.8,
        "average_score": 0.8,
        "document_count": 1,
    }
    document = Document(
        page_content="A grounded answer.",
        metadata={"source": "test", "page": 1, "relevance_score": 0.8},
    )

    monkeypatch.setattr("app.service.ask", lambda _question: ("answer", [document], relevance))

    response = chat(ChatRequest(question="question"))

    assert response["answer"] == "answer"
    assert response["relevance"]["best_score"] == 0.8
    assert response["sources"][0]["source"] == "test"
