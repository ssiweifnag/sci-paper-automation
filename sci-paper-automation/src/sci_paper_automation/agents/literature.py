from __future__ import annotations

from typing import List
import requests

from sci_paper_automation.models.state import PaperRecord


class LiteratureFetcher:
    def fetch_semantic_scholar(self, query: str, limit: int = 10) -> List[PaperRecord]:
        url = 'https://api.semanticscholar.org/graph/v1/paper/search'
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,abstract,year,authors,citationCount,url',
        }
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        records: List[PaperRecord] = []
        for item in payload.get('data', []):
            records.append(
                PaperRecord(
                    title=item.get('title', ''),
                    abstract=item.get('abstract', '') or '',
                    authors=[a.get('name', '') for a in item.get('authors', [])],
                    year=item.get('year'),
                    source='semantic_scholar',
                    url=item.get('url'),
                    citations=item.get('citationCount'),
                )
            )
        return records
