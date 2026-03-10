from __future__ import annotations

import argparse
import json
from pathlib import Path

from sci_paper_automation.agents.format_checker import FormatChecker
from sci_paper_automation.agents.integrity import AcademicRiskScreening
from sci_paper_automation.agents.journal import JournalMatcher
from sci_paper_automation.agents.literature import LiteratureFetcher
from sci_paper_automation.agents.revision import PaperRevisionAgent
from sci_paper_automation.clients.llm import ClaudeLLMClient, MockLLMClient
from sci_paper_automation.models.state import PaperState


def build_llm(config: dict):
    llm_cfg = config.get('llm', {})
    provider = llm_cfg.get('provider', 'mock')
    if provider == 'claude':
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise RuntimeError('使用 claude provider 時需設定 ANTHROPIC_API_KEY')
        return ClaudeLLMClient(api_key=api_key, model=llm_cfg.get('model', 'claude-sonnet-4-20250514'))
    return MockLLMClient(model=llm_cfg.get('model', 'mock-sonnet'))


def load_text_if_exists(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8', errors='ignore')


def load_config(cfg_path: Path) -> dict:
    suffix = cfg_path.suffix.lower()
    text = cfg_path.read_text(encoding='utf-8')
    if suffix == '.json':
        return json.loads(text)
    if suffix in {'.yaml', '.yml'}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError('讀取 YAML 設定需要先安裝 PyYAML，或改用 JSON 設定檔。') from exc
        return yaml.safe_load(text)
    raise ValueError(f'不支援的設定檔格式: {suffix}')


def run_pipeline(config_path: str) -> dict:
    cfg_path = Path(config_path)
    config = load_config(cfg_path)
    project_root = cfg_path.parent.parent
    prompt_dir = project_root / 'prompts'
    output_root = (cfg_path.parent.parent / config['outputs']['root_dir']).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    state = PaperState(
        project_id=config['project_id'],
        topic=config['topic'],
        paper_path=config['paper_path'],
        target_journal=config.get('target_journal'),
        keywords=config.get('keywords', []),
    )

    llm = build_llm(config)
    literature = LiteratureFetcher()
    revision = PaperRevisionAgent(llm, prompt_dir)
    checker = FormatChecker()
    journal = JournalMatcher(llm, prompt_dir)
    integrity = AcademicRiskScreening(llm, prompt_dir)

    state.status = 'fetching_literature'
    state.literature_results = literature.fetch_semantic_scholar(state.topic, limit=5)

    paper_text = load_text_if_exists(state.paper_path)
    state.abstract = paper_text[:1200] if paper_text else f'Topic summary placeholder: {state.topic}'

    state.status = 'revising_abstract'
    revised_abstract = revision.enhance_abstract(state.abstract, state.keywords)
    state.revision_history.append({'step': 'enhance_abstract', 'output': revised_abstract})

    state.status = 'matching_journal'
    state.journal_matches = journal.match(state.abstract or '', state.keywords)

    state.status = 'integrity_screening'
    state.integrity_report = integrity.review(paper_text or state.abstract or '')

    paper_docx = Path(state.paper_path)
    if paper_docx.exists() and paper_docx.suffix.lower() == '.docx':
        state.status = 'format_checking'
        state.format_report = checker.check_docx(str(paper_docx))
    else:
        state.format_report = {'skipped': True, 'reason': 'paper_path 不存在或不是 .docx'}

    state.status = 'completed'
    result = state.to_dict()
    (output_root / 'pipeline_result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    result = run_pipeline(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
