from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PaperRecord:
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    source: str = "unknown"
    url: Optional[str] = None
    citations: Optional[int] = None


@dataclass
class PaperState:
    project_id: str
    topic: str
    paper_path: str
    target_journal: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    literature_results: List[PaperRecord] = field(default_factory=list)
    charts: List[str] = field(default_factory=list)
    revision_history: List[Dict[str, Any]] = field(default_factory=list)
    format_report: Dict[str, Any] = field(default_factory=dict)
    journal_matches: List[Dict[str, Any]] = field(default_factory=list)
    integrity_report: Dict[str, Any] = field(default_factory=dict)
    status: str = "initialized"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['literature_results'] = [asdict(x) for x in self.literature_results]
        return data
