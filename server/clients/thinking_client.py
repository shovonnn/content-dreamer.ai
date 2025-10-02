from __future__ import annotations
from typing import Dict, List, Optional
from openai_utils import get_reply_json
from config import logger


class ThinkingClient:
    """Encapsulates all LLM prompting used in the report pipeline.

    This isolates prompts, shapes, and parsing so worker logic stays clean and testable.
    """

    def __init__(self, user=None):
        # Optional authenticated user for credit logging; guests may be None
        self.user = user

    def initial_keywords(self, product_name: str, description: str) -> Dict:
        system = (
            "You are an expert content strategist. Given a product name and description, "
            "return two groups of keywords: group1 (keywords prospective clients write about on Twitter) "
            "and group2 (keywords people search on Google). Respond as JSON {'group1':[], 'group2':[]}"
        )
        user_msg = f"Product: {product_name}\nDescription: {description}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            g1 = out.get('group1') or []
            g2 = out.get('group2') or []
            if not isinstance(g1, list) or not isinstance(g2, list):
                return {"group1": [], "group2": []}
            return {"group1": g1, "group2": g2}
        except Exception as e:
            logger.exception(e)
            return {"group1": [], "group2": []}

    def filter_topics(self, product_name: str, description: str, topics: List[str], limit: int = 10) -> List[str]:
        system = "Select the most relevant topics to the product from this list. Return JSON {'topics':['...']}"
        user_msg = f"Product: {product_name}. Description: {description}. Topics: {topics}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            res = out.get('topics') or []
            if not isinstance(res, list):
                return topics[:min(limit, 5)]
            return res[:limit]
        except Exception:
            # Fallback to first few
            return topics[:min(limit, 5)]

    def headlines_for_topic(self, product_name: str, description: str, topic: str, tweets_text: str, n: int = 5) -> List[str]:
        system = "Generate 5 compelling article headlines for the topic using the tweet context. Return as JSON {'headlines':['...']}"
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}. Tweets: {tweets_text[:3000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            heads = out.get('headlines') or []
            return heads[:n] if isinstance(heads, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def tweets_for_topic(self, product_name: str, description: str, topic: str, n: int = 5) -> List[str]:
        system = "Write 5 potential tweets about the topic aligned with the product positioning. Return JSON {'tweets':['...']}"
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}."
        try:
            out = get_reply_json(self.user, system, user_msg)
            tweets = out.get('tweets') or []
            return tweets[:n] if isinstance(tweets, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def headlines_for_keyword(self, product_name: str, description: str, keyword: str, tweets_text: str, n: int = 3) -> Dict[str, List[str]]:
        system = "Generate 3 SEO-friendly article headlines around the keyword using the tweet context if provided. Return JSON {'with_tweets':['...'],'without_tweets':['...']}"
        user_msg = f"Product: {product_name}. Description: {description}. Keyword: {keyword}. Tweets: {tweets_text[:3000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            wt = out.get('with_tweets') or []
            wot = out.get('without_tweets') or []
            return {
                "with_tweets": wt[:n] if isinstance(wt, list) else [],
                "without_tweets": wot[:n] if isinstance(wot, list) else [],
            }
        except Exception as e:
            logger.error(e)
            return {"with_tweets": [], "without_tweets": []}

    def headlines_for_medium_tag(self, product_name: str, description: str, tag: str, titles_text: str, n: int = 3) -> List[str]:
        system = "Generate 3 article headlines inspired by these trending Medium articles for the given tag. Return JSON {'headlines':['...']}"
        user_msg = f"Product: {product_name}. Description: {description}. Tag: {tag}. Articles: {titles_text[:3000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            heads = out.get('headlines') or []
            return heads[:n] if isinstance(heads, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def witty_reply(self, product_name: str, description: str, tweet_text: str) -> Optional[str]:
        system = "Write a witty but helpful single-tweet reply. Return JSON {'reply':'...'}"
        user_msg = f"Tweet: {tweet_text[:500]}\nProduct: {product_name}. Description: {description}."
        try:
            out = get_reply_json(self.user, system, user_msg)
            reply = out.get('reply')
            return reply if isinstance(reply, str) and reply.strip() else None
        except Exception as e:
            logger.error(e)
            return None
