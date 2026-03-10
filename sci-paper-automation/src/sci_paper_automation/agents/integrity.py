from __future__ import annotations

from pathlib import Path

from sci_paper_automation.clients.llm import LLMClient
from sci_paper_automation.utils.prompts import load_prompt


class AcademicRiskScreening:
    def __init__(self, llm: LLMClient, prompt_dir: Path):
        self.llm = llm
        self.prompt_dir = prompt_dir

    def review(self, text: str) -> dict:
        user = load_prompt(self.prompt_dir / 'integrity_review.txt', text=text[:6000])
        result = self.llm.generate(
            system='你是投稿前風險審查助手，不可聲稱已完成正式查重。',
            user=user,
            max_tokens=1500,
        )
        return {
            'type': 'pre_submission_risk_screening',
            'summary': result,
            'warning': '此結果不能替代 iThenticate / Turnitin 等正式查重工具。',
        }
