from pathlib import Path


def load_prompt(path: str | Path, **kwargs) -> str:
    text = Path(path).read_text(encoding='utf-8')
    return text.format(**kwargs)
