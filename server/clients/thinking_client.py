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
        group1 = self.get_keywords_for_prospective_clients(product_name, description)
        group2 = self.get_keywords_for_seo(product_name, description)
        return { 'group1': group1, 'group2': group2 }

    def get_keywords_for_prospective_clients(self, product_name: str, description: str) -> List[str]:
        system = (
            "We are looking to find clients from twitter by searching for tweets. Given the product name and description, "
            "return keywords prospective clients write about on Twitter. Be specific and think critically and creatively and avoid generic terms. "
            'Respond as JSON {"keywords": ["keyword1", "keyword2", ...]}'
        )
        user_msg = f"Product: {product_name}\nDescription: {description}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            return out.get('keywords') or []
        except Exception as e:
            logger.exception(e)
            return []
        
    def get_keywords_for_seo(self, product_name: str, description: str) -> List[str]:
        system = (
            "We are looking to find keywords people search on Google. Given the product name and description, "
            "return keywords people search on Google. Be specific and think critically and creatively and avoid generic terms but include long-tail keywords with less competition even if it is bit outside the box. "
            'Respond as JSON {"keywords": ["keyword1", "keyword2", ...]}'
        )
        user_msg = f"Product: {product_name}\nDescription: {description}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            return out.get('keywords') or []
        except Exception as e:
            logger.exception(e)
            return []

    def filter_topics(self, product_name: str, description: str, topics: List[str], limit: int = 10) -> List[str]:
        system = 'Select the most relevant topics to the product from this list. Return JSON {"topics":["..."]}'
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
        system = 'Generate 5 compelling article ideas(as Headline) for the topic using the tweet context. Think critically and creatively and avoid generic phrases, emojis, generic ideas. Try to come up with novel ideas. Focus on something that hasn\'t been covered extensively and can be helpful. Return as JSON {"headlines":["..."]}'
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}. Tweets: {tweets_text[:3000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            heads = out.get('headlines') or []
            return heads[:n] if isinstance(heads, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def tweets_for_topic(self, product_name: str, description: str, topic: str, n: int = 5) -> List[str]:
        system = 'Write 5 potential tweets about the topic aligned with the product positioning. Avoid emojis. Don\'t overdo the promotion. Try to sound more casual. Return JSON {"tweets":["..."]}'
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}."
        try:
            out = get_reply_json(self.user, system, user_msg)
            tweets = out.get('tweets') or []
            return tweets[:n] if isinstance(tweets, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def headlines_for_keyword(self, product_name: str, description: str, keyword: str, tweets_text: str, n: int = 3) -> Dict[str, List[str]]:
        system = 'Generate 3 SEO-friendly article ideas(as Headline) around the keyword using the tweet context if provided. Think critically and creatively and avoid generic phrases, emojis, generic ideas. Return JSON {"with_tweets":["..."],"without_tweets":["..."]}'
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
        system = 'Generate 3 article ideas(as Headline) inspired by these trending Medium articles for the given tag. Think critically and creatively and avoid generic phrases, emojis, generic ideas. Try to come up with ideas that are not only catchy but also provide real value to the reader. Return JSON {"headlines":["..."]}'
        user_msg = f"Product: {product_name}. Description: {description}. Tag: {tag}. Articles: {titles_text[:3000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            heads = out.get('headlines') or []
            return heads[:n] if isinstance(heads, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def witty_reply(self, product_name: str, description: str, tweet_text: str) -> Optional[str]:
        system = 'Write a witty but helpful single-tweet reply. Avoid emojis. DO NOT Promote our product. Just say something useful and keep it short and concise. Return JSON {"reply":"..."}'
        user_msg = f"Tweet: {tweet_text[:500]}\nProduct: {product_name}. Description: {description}."
        try:
            out = get_reply_json(self.user, system, user_msg)
            reply = out.get('reply')
            return reply if isinstance(reply, str) and reply.strip() else None
        except Exception as e:
            logger.error(e)
            return None
