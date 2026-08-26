from __future__ import annotations

from collections.abc import Iterator
from openai import OpenAI


class AvalAILLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.avalai.ir/v1",
        temperature: float = 0.2,
        timeout: float = 120.0,
    ) -> None:
        if not api_key:
            raise ValueError("AvalAI API key is missing.")
        if not model:
            raise ValueError("Model name is missing.")
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model
        self.temperature = temperature

    def _messages(self, prompt: str) -> list[dict[str, str]]:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        return [
            {"role": "system", "content": "You are a reliable industrial RAG assistant."},
            {"role": "user", "content": prompt},
        ]

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=self._messages(prompt),
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The language model returned an empty response.")
        return content.strip()

    def stream(self, prompt: str) -> Iterator[str]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=self._messages(prompt),
            stream=True,
        )
        for event in response:
            if not event.choices:
                continue
            delta = event.choices[0].delta.content
            if delta:
                yield delta


OpenAILLM = AvalAILLM
