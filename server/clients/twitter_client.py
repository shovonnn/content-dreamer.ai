from __future__ import annotations
import json
from typing import List, Dict, Optional, Any
import requests
from dataclasses import dataclass
from config import logger


@dataclass
class TweetSummary:
    text: str
    user_name: str
    like_count: int
    retweet_count: int
    reply_count: int
    # New: include identifiers to allow UI deep linking
    id: Optional[str] = None  # tweet id (id_str/rest_id)
    username: Optional[str] = None  # user handle (screen_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "user_name": self.user_name,
            "like_count": self.like_count,
            "retweet_count": self.retweet_count,
            "reply_count": self.reply_count,
            "id": self.id,
            "username": self.username,
        }


@dataclass
class TwitterSearchResult:
    top: List[TweetSummary]
    latest: List[TweetSummary]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top": [t.to_dict() for t in self.top],
            "latest": [t.to_dict() for t in self.latest],
        }


class TwitterClient:
    """Thin client around RapidAPI 'twttr' endpoints.

    Abstracts HTTP and host headers so callers only pass inputs/receive Python objects.
    """

    def __init__(self, api_key: str = None, host: str = "twitter241.p.rapidapi.com", session: Optional[requests.Session] = None):
        if not api_key:
            from config import rapidapi_key
            api_key = rapidapi_key
        
        if not api_key:
            raise ValueError("TwitterClient requires an API key")
        self.api_key = api_key
        self.host = host
        self.session = session or requests.Session()
        self.base_url = f"https://{host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
        }

    def get_trending_topics(self, limit: int = 30) -> List[str]:
        url = f"{self.base_url}/trends-by-location?woeid=2424766"
        r = self.session.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()
        data = r.json().get('result', [{}])[0]
        names = [t.get("name") for t in (data.get("trends") or []) if t.get("name")]
        return names[:limit]

    def search(self, query: str, count: int = 5) -> TwitterSearchResult:
        params = {"query": query, "count": count}
        # Top (popular)
        res_top = self.session.get(f"{self.base_url}/search-v2", headers=self.headers, params={**params, "type": "Top"}, timeout=60)
        # Latest (recent)
        res_latest = self.session.get(f"{self.base_url}/search-v2", headers=self.headers, params={**params, "type": "Latest"}, timeout=60)

        def extract_tweets(resp):
            if not resp.ok:
                logger.warning(f"Twitter search response not OK: {getattr(resp, 'status_code', 'NA')}")
                return []
            try:
                data = resp.json()
                instructions = (
                    data.get("result", {})
                        .get("timeline", {})
                        .get("instructions", [])
                )
                tweets: List[TweetSummary] = []

                for instr in instructions:
                    entries = instr.get("entries", [])
                    for entry in entries:
                        content = entry.get("content", {})
                        # Only care about timeline items (skip user carousels/modules)
                        content_typename = content.get("__typename") or content.get("entryType")
                        if content_typename != "TimelineTimelineItem":
                            continue

                        # Different payloads may use `itemContent` or `content`
                        item = content.get("itemContent", {}) or content.get("content", {})
                        item_typename = item.get("__typename") or item.get("itemType")
                        if item_typename != "TimelineTweet":
                            continue

                        # Newer schema: `tweet_results.result` (sometimes `TweetWithVisibilityResults`)
                        # Legacy schema: `tweetResult.result` (direct `Tweet`)
                        tr = item.get("tweet_results") or item.get("tweetResult") or {}
                        res = tr.get("result", {})
                        if not res:
                            continue

                        tweet_obj: Dict = {}
                        res_typename = res.get("__typename")
                        if res_typename == "TweetWithVisibilityResults":
                            tweet_obj = res.get("tweet", {})
                        elif res_typename == "Tweet":
                            tweet_obj = res
                        else:
                            # Fallback: some variants may still be usable as-is
                            tweet_obj = res

                        if not tweet_obj:
                            continue

                        # Extract text (most reliable in legacy.full_text)
                        legacy = tweet_obj.get("legacy", {})
                        text = legacy.get("full_text") or tweet_obj.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {}).get("text")
                        if not text or not text.strip():
                            continue  # skip if there is no textual content

                        # Extract user name
                        user_name = (
                            ((tweet_obj.get("core", {})
                               .get("user_results", {})
                               .get("result", {})
                               .get("core", {})
                               .get("name"))
                             )
                            or ((tweet_obj.get("core", {})
                                  .get("user_results", {})
                                  .get("result", {})
                                  .get("legacy", {})
                                  .get("name")))
                            or ""
                        )

                        # Counts
                        like_count = int(legacy.get("favorite_count") or 0)
                        retweet_count = int(legacy.get("retweet_count") or 0)
                        reply_count = int(legacy.get("reply_count") or 0)

                        # Identifiers for linking
                        tweet_id = legacy.get("id_str") or tweet_obj.get("rest_id")
                        user_result = (
                            tweet_obj.get("core", {})
                                     .get("user_results", {})
                                     .get("result", {})
                        )
                        username = (
                            user_result.get("legacy", {}).get("screen_name")
                            or user_result.get("core", {}).get("screen_name")
                        )

                        tweets.append(
                            TweetSummary(
                                text=text.strip(),
                                user_name=user_name or "",
                                like_count=like_count,
                                retweet_count=retweet_count,
                                reply_count=reply_count,
                                id=tweet_id,
                                username=username,
                            )
                        )

                return tweets
            except Exception as e:
                logger.exception(f"Failed to parse tweets: {e}")
                return []

        top = extract_tweets(res_top)
        latest = extract_tweets(res_latest)
        return TwitterSearchResult(top=top, latest=latest)
