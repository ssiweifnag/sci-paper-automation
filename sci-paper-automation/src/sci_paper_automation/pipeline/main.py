from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pathlib import Path as PathLib

from sci_paper_automation.agents.format_checker import FormatChecker
from sci_paper_automation.agents.integrity import AcademicRiskScreening
from sci_paper_automation.agents.journal import JournalMatcher
from sci_paper_automation.agents.literature import LiteratureFetcher
from sci_paper_automation.agents.revision import PaperRevisionAgent
from sci_paper_automation.agents.video_knowledge import VideoKnowledgeExtractor
from sci_paper_automation.clients.llm import ClaudeLLMClient, MiniMaxLLMClient, MockLLMClient
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
    if provider == 'minimax':
        import os
        api_key = os.getenv('MINIMAX_API_KEY')
        if not api_key:
            raise RuntimeError('使用 minimax provider 時需設定 MINIMAX_API_KEY')
        return MiniMaxLLMClient(
            api_key=api_key,
            model=llm_cfg.get('model', 'MiniMax-M2.5'),
            base_url=llm_cfg.get('base_url', 'https://api.minimax.chat/v1'),
        )
    return MockLLMClient(model=llm_cfg.get('model', 'mock-sonnet'))


def load_text_if_exists(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ''
    
    suffix = p.suffix.lower()
    if suffix == '.docx':
        # Try python-docx first
        try:
            from docx import Document
            doc = Document(path)
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text.strip())
            return '\n\n'.join(text_parts)
        except ImportError:
            pass
        except Exception as e:
            pass
        
        # Fallback: extract via zipfile (docx is just XML inside)
        try:
            import zipfile
            text_parts = []
            with zipfile.ZipFile(path, 'r') as z:
                # Read document.xml which contains the main content
                with z.open('word/document.xml') as f:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(f)
                    root = tree.getroot()
                    # Word uses namespaces, strip them for simpler parsing
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    for elem in root.iter():
                        if elem.tag.endswith('}t'):  # Text element
                            if elem.text:
                                text_parts.append(elem.text)
            return ''.join(text_parts)
        except Exception as e:
            return f"[DOCX: {p.name} - extract error: {e}]"
    
    # Plain text files
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

    # Fetch from multiple sources
    state.status = 'fetching_literature'
    all_results = []
    sources = config.get('sources', {})
    limit = config.get('max_results', 10)
    topic = state.topic
    
    # Fetch from enabled sources
    if sources.get('semantic_scholar', False):
        print("Fetching from Semantic Scholar...")
        all_results.extend(literature.fetch_semantic_scholar(topic, limit=limit))
    
    if sources.get('pubmed', False):
        print("Fetching from PubMed...")
        all_results.extend(literature.fetch_pubmed(topic, limit=limit))
    
    if sources.get('openalex', False):
        print("Fetching from OpenAlex...")
        all_results.extend(literature.fetch_openalex(topic, limit=limit))
    
    if sources.get('arxiv', False):
        print("Fetching from arXiv...")
        all_results.extend(literature.fetch_arxiv(topic, limit=limit))
    
    state.literature_results = all_results[:limit * 2]  # Allow some duplicates
    
    # Video knowledge extraction
    video_sources = config.get('video_sources', {})
    video_results = []
    if video_sources.get('youtube') or video_sources.get('bilibili'):
        video_urls = video_sources.get('urls', [])
        video_style = video_sources.get('style', 'academic')
        video_api_key = config.get('llm', {}).get('api_key') or os.getenv('MINIMAX_API_KEY')
        
        if video_urls:
            print("Extracting video knowledge...")
            video_extractor = VideoKnowledgeExtractor(
                api_key=video_api_key,
                provider=config.get('llm', {}).get('provider', 'minimax')
            )
            
            for video_url in video_urls:
                print(f"  Processing: {video_url}")
                try:
                    result = video_extractor.process_video(
                        video_url, 
                        style=video_style,
                        summary=True
                    )
                    video_results.append({
                        'url': video_url,
                        'result': result
                    })
                except Exception as e:
                    print(f"  Error processing {video_url}: {e}")
    
    state.charts = video_results  # Store video results in charts field for now
    
    # Try to read paper from Box path
    paper_text = ''
    paper_path = config.get('paper_path', '')
    
    if paper_path:
        # Try relative to config, or absolute
        p = Path(paper_path)
        if not p.exists():
            # Try as absolute path
            p = Path(cfg_path.parent.parent / paper_path)
        if p.exists():
            if p.suffix.lower() == '.docx':
                # For docx, just note that it's available
                paper_text = f"[論文檔案: {p.name}]"
            else:
                paper_text = p.read_text(encoding='utf-8', errors='ignore')[:5000]
    
    # Also check for papers in configured folder
    paper_folder = config.get('paper_folder', '')
    if paper_folder:
        folder = Path(cfg_path.parent.parent / paper_folder)
        if folder.exists():
            # Look for markdown or text files
            for ext in ['*.md', '*.txt']:
                for f in sorted(folder.glob(ext))[:3]:
                    paper_text += f"\n\n--- {f.name} ---\n"
                    paper_text += f.read_text(encoding='utf-8', errors='ignore')[:2000]
    
    state.abstract = paper_text[:2000] if paper_text else f'Topic: {state.topic}'

    state.status = 'revising_abstract'
    revised_abstract = revision.enhance_abstract(state.abstract, state.keywords)
    state.revision_history.append({'step': 'enhance_abstract', 'output': revised_abstract})

    state.status = 'matching_journal'
    state.journal_matches = journal.match(state.abstract or '', state.keywords)

    state.status = 'integrity_screening'
    state.integrity_report = integrity.review(paper_text or state.abstract or '')

    paper_docx = Path(paper_path)
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
