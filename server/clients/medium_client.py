from __future__ import annotations
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass


@dataclass
class MediumArticle:
    id: str
    title: str
    subtitle: str
    author: str
    publication_id: str
    published_at: str
    last_modified_at: str
    boosted_at: str

class MediumClient:
    """Thin client around RapidAPI Medium endpoints."""

    def __init__(self, api_key: str = None, host: str = "medium2.p.rapidapi.com", session: Optional[requests.Session] = None):
        if not api_key:
            from config import rapidapi_key
            api_key = rapidapi_key
        if not api_key:
            raise ValueError("MediumClient requires an API key")
        self.api_key = api_key
        self.host = host
        self.session = session or requests.Session()
        self.base_url = f"https://{host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
        }

    def list_root_tags(self, limit: int = 100) -> List[str]:
        r = self.session.get(f"{self.base_url}/root_tags", headers=self.headers, timeout=60)
        r.raise_for_status()
        tags = r.json().get("root_tags", [])
        return tags[:limit]

    def search_for_tags(self, query: str, limit: int = 100) -> List[str]:
        r = self.session.get(f"{self.base_url}/search/tags", headers=self.headers, params={"query": query}, timeout=60)
        r.raise_for_status()
        tags = r.json().get("tags", [])
        return tags[:limit]
    
    def get_article_by_id(self, article_id: str) -> Optional[MediumArticle]:
        r = self.session.get(f"{self.base_url}/article/{article_id}", headers=self.headers, timeout=60)
        if not r.ok:
            return None
        data = r.json()
        return MediumArticle(
            id=data.get("id", ""),
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            author=data.get("author", ""),
            publication_id=data.get("publication_id", ""),
            published_at=data.get("published_at", ""),
            last_modified_at=data.get("last_modified_at", ""),
            boosted_at=data.get("boosted_at", ""),
        )

    def trending_ids_for_tag(self, tag: str, limit: int = 10) -> List[Dict]:
        r = self.session.get(f"{self.base_url}/recommended_feed/{tag}", headers=self.headers, timeout=60)
        if not r.ok:
            return []
        return (r.json().get("recommended_feed") or [])[:limit]
    
    def get_trending_articles(self, keyword: str, limit: int = 10) -> List[MediumArticle]:
        tag = keyword.lower().replace(" ", "-")
        ids = self.trending_ids_for_tag(tag, limit=limit*2)
        articles: List[MediumArticle] = []
        for id in ids:
            article = self.get_article_by_id(id)
            if article is not None:
                articles.append(article)
            if len(articles) >= limit:
                break
        return articles[:limit]
    
    def search_for_articles(self, query: str, limit: int = 10) -> List[MediumArticle]:
        r = self.session.get(f"{self.base_url}/search/articles", headers=self.headers, params={"query": query}, timeout=60)
        if not r.ok:
            return []
        ids = (r.json().get("articles") or [])[:limit]
        articles: List[MediumArticle] = []
        for article_id in ids:
            article = self.get_article_by_id(article_id)
            if article is not None:
                articles.append(article)
        return articles

