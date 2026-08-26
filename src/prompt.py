from __future__ import annotations

from langchain_core.documents import Document


class PromptBuilder:
    @staticmethod
    def build(
        question: str,
        documents: list[Document],
        relevance: dict[str, object],
        conversation_history: str = "",
    ) -> str:
        sources: list[str] = []
        for document in documents:
            meta = document.metadata
            sources.append(
                "\n".join(
                    [
                        "[SOURCE]",
                        f"Source: {meta.get('source', 'Unknown')}",
                        f"Page: {meta.get('page', 'Unknown')}",
                        f"Chunk: {meta.get('chunk_id', 'Unknown')}",
                        f"Similarity: {meta.get('relevance_score', 0)}",
                        "Content:",
                        document.page_content,
                        "[/SOURCE]",
                    ]
                )
            )
        context = "\n\n".join(sources) if sources else "No relevant source was retrieved."

        return f"""
You are an accurate Persian-first industrial knowledge-management assistant.
Answer in the same language as the user's question.

Rules:
- Prefer the retrieved context whenever it directly answers the question.
- Never invent a source, page, number, quote, or technical specification.
- When using retrieved information, cite the source and page naturally in the answer.
- When the context is insufficient, clearly state that the documents do not contain a complete answer.
- You may provide general knowledge only after clearly separating it from document-grounded information.
- Keep the answer practical, structured, and concise.

Conversation history:
{conversation_history or "No previous conversation."}

Retrieval analysis:
{relevance}

Retrieved context:
{context}

User question:
{question}

Final answer:
""".strip()
