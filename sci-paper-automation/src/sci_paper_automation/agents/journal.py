from __future__ import annotations

from pathlib import Path

from sci_paper_automation.clients.llm import LLMClient
from sci_paper_automation.utils.prompts import load_prompt


class JournalMatcher:
    def __init__(self, llm: LLMClient, prompt_dir: Path):
        self.llm = llm
        self.prompt_dir = prompt_dir

    def match(self, abstract: str, keywords: list[str]) -> list[dict]:
        user = load_prompt(
            self.prompt_dir / 'journal_match.txt',
            abstract=abstract,
            keywords=', '.join(keywords),
        )
        result = self.llm.generate(
            system='你負責提供投稿方向建議，若缺少外部資料，不可虛構期刊指標。',
            user=user,
            max_tokens=1200,
        )
        return [{'source': 'llm_stub', 'recommendation': result}]
