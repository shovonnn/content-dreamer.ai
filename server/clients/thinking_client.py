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
            "return keywords prospective clients write about on Twitter. Be specific and think critically and creatively. Return distinct keywords that are relevant for target clients but unique from each other that means not variations of the same concept. "
            'Think critically, twitter is a place where people share their problems, frustrations, aspirations, achievements, and milestones. What would your target clients tweet about that indicates they have the problem our product solves or are looking for a solution. '
            'For example, if a product is about "helping people find remote jobs", keywords could be "where to find remote jobs", "tired of office work", "struggle of long commute", "hiring", "looking for job", "learned new skill", "graduated". '
            'if the product is about "learning new languages", keywords could be "travel the world", "moving abroad", "expat struggle", "learn new language", "duolingo issues"(or other competitor app), "looking to learn something new". '
            'if the product is about "fitness", keywords could be "how can i lose weight", "need to get in shape", "workout routine", "gym motivation", "healthy eating", "fitness goals", "new year resolution". '
            'if the product is about "personal finance", keywords could be "how to save money", "empty bank account", "struggling pay rent", "investing tips", "debt free journey", "budgeting help", "financial freedom", "side hustle ideas". '
            'if the product is about "mental health", keywords could be "feeling anxious", "overwhelmed with work", "need a break", "stress management", "self care tips", "mindfulness practice", "therapy experience". '
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
        
    def filter_keywords(self, product_name: str, description: str, keywords: List[str], limit: int = 5) -> List[str]:
        system = 'Select the most relevant keywords to the product from this list. Prioritize distinct keywords and long-tail keywords. Return JSON {"keywords":["..."]}'
        user_msg = f"Product: {product_name}. Description: {description}. Keywords: {keywords}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            res = out.get('keywords') or []
            if not isinstance(res, list):
                return keywords[:min(limit, 5)]
            return res[:limit]
        except Exception:
            # Fallback to first few
            return keywords[:min(limit, 5)]

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

    def articles_for_topic(self, product_name: str, description: str, topic: str, more_context: str = None, n: int = 5) -> List[dict]:
        system = (f'Generate {n} compelling article concepts for the topic and context provided. Think critically and creatively and avoid generic ideas. Not necessarily need to focus on our product. Try to come up with novel ideas. Focus on something that hasn\'t been covered extensively and can be helpful. '
        'Return as JSON {"article_concepts":[{'
        '"title":"...", "description":"..."}]}'
        )
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}."
        if more_context:
            user_msg += f" Helpful Context: {more_context[:10000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            heads = out.get('article_concepts') or []
            return heads[:n] if isinstance(heads, list) else []
        except Exception as e:
            logger.error(e)
            return []

    def tweets_for_topic(self, product_name: str, description: str, topic: str, more_context: str = None, n: int = 5) -> List[str]:
        system = (f'Write {n} potential tweets about the topic aligned with the product positioning. Avoid emojis. Don\'t overdo the promotion. '
            'Try to sound more casual. Return JSON {"tweets":["..."]}'
        )
        user_msg = f"Product: {product_name}. Description: {description}. Topic: {topic}."
        if more_context:
            user_msg += f" Helpful Context: {more_context[:10000]}"
        try:
            out = get_reply_json(self.user, system, user_msg)
            tweets = out.get('tweets') or []
            return tweets[:n] if isinstance(tweets, list) else []
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
