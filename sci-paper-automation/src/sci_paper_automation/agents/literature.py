from __future__ import annotations

from typing import List
import requests

from sci_paper_automation.models.state import PaperRecord


class LiteratureFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'sci-paper-automation/1.0'})

    def fetch_semantic_scholar(self, query: str, limit: int = 10) -> List[PaperRecord]:
        url = 'https://api.semanticscholar.org/graph/v1/paper/search'
        params = {
            'query': query,
            'limit': limit,
            'fields': 'title,abstract,year,authors,citationCount,url',
        }
        try:
            response = self.session.get(url, params=params, timeout=20)
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

    def fetch_pubmed(self, query: str, limit: int = 10) -> List[PaperRecord]:
        # PubMed E-utilities
        try:
            # Search
            search_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': limit,
                'retmode': 'json',
                'sort': 'relevance',
            }
            search_resp = self.session.get(search_url, params=search_params, timeout=20)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            idlist = search_data.get('esearchresult', {}).get('IdList', [])
            if not idlist:
                return []
            
            # Fetch details
            fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(idlist[:limit]),
                'retmode': 'json',
            }
            fetch_resp = self.session.get(fetch_url, params=fetch_params, timeout=20)
            fetch_resp.raise_for_status()
            fetch_data = fetch_resp.json()
        except Exception as e:
            print(f"PubMed fetch error: {e}")
            return []

        records: List[PaperRecord] = []
        for uid, info in fetch_data.get('result', {}).items():
            if uid == 'uids':
                continue
            records.append(
                PaperRecord(
                    title=info.get('title', ''),
                    abstract='',  # PubMed summary doesn't include abstract
                    authors=[a.get('name', '') for a in info.get('authors', [])],
                    year=int(info.get('pubdate', '0')[:4]) if info.get('pubdate') else None,
                    doi=info.get('doi'),
                    source='pubmed',
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                    citations=info.get('pmc') and 1 or 0,
                )
            )
        return records

    def fetch_openalex(self, query: str, limit: int = 10) -> List[PaperRecord]:
        url = 'https://api.openalex.org/works'
        params = {
            'search': query,
            'per-page': limit,
            'select': 'id,title,abstract,publication_year,authorships,doi,cited_by_count',
        }
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        records: List[PaperRecord] = []
        for item in payload.get('results', []):
            authors = [a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])]
            records.append(
                PaperRecord(
                    title=item.get('title', ''),
                    abstract=item.get('abstract', '') or '',
                    authors=authors,
                    year=item.get('publication_year'),
                    doi=item.get('doi'),
                    source='openalex',
                    url=item.get('id', '').replace('https://openalex.org/', 'https://doi.org/'),
                    citations=item.get('cited_by_count'),
                )
            )
        return records

    def fetch_arxiv(self, query: str, limit: int = 10) -> List[PaperRecord]:
        url = 'https://export.arxiv.org/api/query'
        params = {
            'search_query': f'all:{query}',
            'max_results': limit,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
        }
        try:
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            # Parse XML manually to avoid extra dependencies
            text = response.text
        except Exception:
            return []

        records: List[PaperRecord] = []
        import re
        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
        for entry in entries:
            title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            id_match = re.search(r'<id>(.*?)</id>', entry)
            date_match = re.search(r'<published>(.*?)</published>', entry)
            author_matches = re.findall(r'<name>(.*?)</name>', entry)
            
            title = title_match.group(1).strip() if title_match else ''
            summary = summary_match.group(1).strip()[:500] if summary_match else ''
            arxiv_id = id_match.group(1).strip() if id_match else ''
            year = int(date_match.group(1)[:4]) if date_match else None
            
            records.append(PaperRecord(
                title=title,
                abstract=summary,
                authors=author_matches,
                year=year,
                source='arxiv',
                url=arxiv_id,
                citations=0,
            ))
        return records
