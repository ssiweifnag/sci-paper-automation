from __future__ import annotations

from pathlib import Path

from sci_paper_automation.clients.llm import LLMClient
from sci_paper_automation.utils.prompts import load_prompt


class PaperRevisionAgent:
    def __init__(self, llm: LLMClient, prompt_dir: Path):
        self.llm = llm
        self.prompt_dir = prompt_dir

    def revise_section(self, section: str, content: str, target_journal: str | None = None) -> str:
        user = load_prompt(
            self.prompt_dir / 'revise_section.txt',
            target_journal=target_journal or '未指定',
            section=section,
            content=content,
        )
        return self.llm.generate(
            system='你負責協助改進學術寫作，但不得虛構結果或文獻。',
            user=user,
            max_tokens=2000,
        )

    def enhance_abstract(self, abstract: str, keywords: list[str]) -> str:
        user = load_prompt(
            self.prompt_dir / 'enhance_abstract.txt',
            abstract=abstract,
            keywords=', '.join(keywords),
        )
        return self.llm.generate(
            system='你負責優化摘要結構與清晰度，不得新增原文未支持的結論。',
            user=user,
            max_tokens=1200,
        )
