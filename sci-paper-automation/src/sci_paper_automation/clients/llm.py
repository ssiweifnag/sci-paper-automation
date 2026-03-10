from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    def generate(self, *, system: str, user: str, max_tokens: int = 2000) -> str: ...


@dataclass
class MockLLMClient:
    model: str = 'mock-sonnet'

    def generate(self, *, system: str, user: str, max_tokens: int = 2000) -> str:
        return (
            f'[MOCK LLM RESPONSE | model={self.model}]\n'
            f'SYSTEM:\n{system[:300]}\n\n'
            f'USER:\n{user[:1200]}\n\n'
            '這是 MVP mock 輸出，後續可替換成真實 Claude / OpenAI / Gemini 客戶端。'
        )


@dataclass
class ClaudeLLMClient:
    api_key: str
    model: str = 'claude-sonnet-4-20250514'

    def __post_init__(self) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise RuntimeError('anthropic 套件未安裝，請先 pip install anthropic') from exc
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, *, system: str, user: str, max_tokens: int = 2000) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{'role': 'user', 'content': user}],
        )
        return response.content[0].text
