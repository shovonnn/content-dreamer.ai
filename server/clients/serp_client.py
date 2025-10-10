from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from xml.parsers.expat import model
import requests

@dataclass
class TechNewsArticle:
    title: str
    link: str
    date: Optional[str] = None
    summary: Optional[str] = None

class SerpApiClient:
    """Thin client for SerpAPI Google Autocomplete.

    Usage:
        sa = SerpApiClient(api_key)
        suggestions = sa.autocomplete("your query")
        expanded = sa.expand_keywords(["kw1", "kw2"])  # returns unique list
    """

    def __init__(self, api_key: str = None, session: Optional[requests.Session] = None):
        if not api_key:
            from config import serpapi_key
            api_key = serpapi_key
        if not api_key:
            raise ValueError("SerpApiClient requires an API key")
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"
        self.session = session or requests.Session()

    def get_top_tech_news(self, limit: int = 10) -> List[TechNewsArticle]:
        params = {
            "engine": "google_news",
            "gl": "us",
            "hl": "en",
            "topic_token": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
            "api_key": self.api_key,
            "num": limit,
        }
        r = self.session.get(self.base_url, params=params, timeout=20)
        if not r.ok:
            return []
        data = r.json() or {}
        out: List[TechNewsArticle] = []
        for result_item in data.get("news_results", []) or []:

            highlight = result_item.get("highlight")
            if not highlight and result_item.get('stories'):
                highlight = result_item['stories'][0]
            if not highlight:
                continue
            item = TechNewsArticle(
                title=highlight.get("title"),
                link=highlight.get("link"),
                date=highlight.get("date"),
                summary=None,
            )
            if item.title and item.link:
                item.summary = self.fetch_news_summary(item.title, item.link)
            out.append(item)
            if len(out) >= limit:
                break
        return out
    
    def fetch_news_summary(self, title: str, url: str) -> Optional[str]:
        from openai_utils import openai_client
        response = openai_client.responses.create(
            model="gpt-5",
            tools=[{"type": "web_search"}],
            input=f"Summarize the this news story '{title}' at {url}"
        )
        return response.output_text

    def autocomplete(self, query: str) -> List[str]:
        params = {
            "engine": "google_autocomplete",
            "q": query,
            "api_key": self.api_key,
        }
        r = self.session.get(self.base_url, params=params, timeout=20)
        if not r.ok:
            return []
        data = r.json() or {}
        out: List[str] = []
        for s in data.get("suggestions", []) or []:
            if isinstance(s, dict):
                val = s.get("value") or s.get("suggestion") or ""
            else:
                val = str(s)
            if val:
                out.append(val)
        return out

    def expand_keywords(self, keywords: List[str], limit: int = 100, per_kw_limit: int = 10) -> List[str]:
        """Expand given keywords with autocomplete suggestions.

        Returns a unique list including the original keywords plus new suggestions,
        truncated to the provided limit.
        """
        seen = []
        def add_unique(items: List[str]):
            for it in items:
                if it and it not in seen:
                    seen.append(it)
        add_unique(list(keywords or []))
        for kw in (keywords or [])[:per_kw_limit]:
            sugs = self.autocomplete(kw)
            add_unique(sugs)
            if len(seen) >= limit:
                break
        return seen[:limit]
