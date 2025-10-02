from models.db_utils import db
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.product import Product
from openai_utils import get_reply_json
from config import logger, serpapi_key, rapidapi_key, enable_twitter, enable_medium
import json
from clients.twitter_client import TwitterClient, TweetSummary
from clients.medium_client import MediumClient
from clients.serp_client import SerpApiClient
from clients.thinking_client import ThinkingClient


def _app_context():
    from app import create_app
    app = create_app()
    return app.app_context()


def generate_report(report_id: str):
    with _app_context():
        rep: Report | None = Report.query.get(report_id)
        if not rep:
            logger.error(f"Report {report_id} not found")
            return
        try:
            rep.mark_running()

            # Step 1: initial keyword groups via LLM
            s1 = ReportStep.start(rep.id, 'initial_keywords')
            product = rep.product
            thinker = ThinkingClient(user=getattr(product, 'user', None))
            resp = thinker.initial_keywords(product.name, product.description or "")
            s1.done(json.dumps(resp))

            # Step 2: Expand group2 with SerpAPI autocomplete
            expanded_group2 = list(resp.get('group2') or [])
            s2 = ReportStep.start(rep.id, 'serpapi_expand')
            try:
                if serpapi_key:
                    sa = SerpApiClient(api_key=serpapi_key)
                    expanded_group2 = sa.expand_keywords(expanded_group2, limit=100, per_kw_limit=10)
                    s2.done(json.dumps({"expanded_group2": expanded_group2}))
                else:
                    s2.done(json.dumps({"warning": "SERPAPI_KEY missing", "expanded_group2": expanded_group2}))
            except Exception as e:
                s2.fail(str(e))

            # Step 3-4: Twitter via RapidAPI (twttr)
            topics = []
            tweets_by_topic = {}
            tweets_by_kw_g1 = {}
            tweets_by_kw_g2 = {}
            s3 = ReportStep.start(rep.id, 'twitter_trends_and_tweets')
            try:
                if enable_twitter and rapidapi_key:
                    tw = TwitterClient(api_key=rapidapi_key)
                    trend_names = tw.get_trending_topics(limit=30)
                    # Filter topics with LLM for relevance
                    topics = thinker.filter_topics(product.name, product.description or "", trend_names, limit=10)
                    # Fetch tweets for each topic
                    for tp in topics:
                        res = tw.search(tp, count=5)
                        tweets_by_topic[tp] = res
                    # Fetch tweets for kw group1
                    for kw in (resp.get('group1') or [])[:15]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g1[kw] = res
                    # Fetch tweets for kw group2 (expanded)
                    for kw in expanded_group2[:20]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g2[kw] = res
                    s3.done(json.dumps({
                        "trends": topics,
                        "by_trend": tweets_by_topic,
                        "g1": tweets_by_kw_g1,
                        "g2": tweets_by_kw_g2,
                    }))
                else:
                    s3.done(json.dumps({"warning": "Twitter disabled or RAPIDAPI_KEY missing"}))
            except Exception as e:
                s3.fail(str(e))

            # Step 5: Medium tags and trending articles via RapidAPI
            medium_tags = []
            trending_by_tag = {}
            s5 = ReportStep.start(rep.id, 'medium_tags_and_articles')
            try:
                if enable_medium and rapidapi_key:
                    md = MediumClient(api_key=rapidapi_key)
                    all_tags = md.list_root_tags(limit=100)
                    # Select relevant tags via LLM using thinking client
                    medium_tags = thinker.filter_topics(product.name, product.description or "", all_tags, limit=10)
                    # Fetch trending articles per tag
                    for tg in medium_tags:
                        trending_by_tag[tg] = md.get_trending_articles(tg, limit=10)
                    s5.done(json.dumps({"tags": medium_tags, "counts": {k: len(v) for k, v in trending_by_tag.items()}}))
                else:
                    s5.done(json.dumps({"warning": "Medium disabled or RAPIDAPI_KEY missing"}))
            except Exception as e:
                s5.fail(str(e))

            # Steps 6-10: LLM-generated suggestions
            # Helper to add suggestion safely
            def add_headline(text, source_type, visibility='subscriber', rank=0.0, meta=None):
                try:
                    Suggestion.add(rep.id, source_type, 'article_headline', text, rank, json.dumps(meta or {}), visibility)
                except Exception as e:
                    logger.error(f"add_headline failed: {e}")

            def add_tweet(text, source_type, visibility='subscriber', rank=0.0, meta=None):
                try:
                    Suggestion.add(rep.id, source_type, 'tweet', text, rank, json.dumps(meta or {}), visibility)
                except Exception as e:
                    logger.error(f"add_tweet failed: {e}")

            def add_reply(text, source_type, visibility='subscriber', rank=0.0, meta=None):
                try:
                    Suggestion.add(rep.id, source_type, 'tweet_reply', text, rank, json.dumps(meta or {}), visibility)
                except Exception as e:
                    logger.error(f"add_reply failed: {e}")

            # 6. Headlines per trending topic
            for tp in topics[:10]:
                if tp not in tweets_by_topic:
                    continue
                tweets_ctx = tweets_by_topic.get(tp)
                tweets_text = "\n".join([
                    *(t.text for t in (tweets_ctx.top or [])[:5]),
                    *(t.text for t in (tweets_ctx.latest or [])[:5])
                ])
                try:
                    heads = thinker.headlines_for_topic(product.name, product.description or "", tp, tweets_text, n=5)
                    for i, h in enumerate(heads):
                        add_headline(h, 'trending_topic', 'guest' if i < (rep.visibility_cutoff or 5) else 'subscriber', rank=1.0 - i*0.1, meta={"topic": tp})
                except Exception as e:
                    logger.error(e)

            # 7. Potential tweets per trending topic
            for tp in topics[:10]:
                try:
                    tweets = thinker.tweets_for_topic(product.name, product.description or "", tp, n=5)
                    for i, t in enumerate(tweets):
                        add_tweet(t, 'trending_topic', 'guest' if i < 1 else 'subscriber', rank=1.0 - i*0.1, meta={"topic": tp})
                except Exception as e:
                    logger.error(e)

            # 8. Headlines per keyword in expanded group2, with tweets and without
            for kw in expanded_group2[:15]:
                kw_tweets = tweets_by_kw_g2.get(kw)
                tweets_text = "\n".join([
                    *(t.text for t in (kw_tweets.top or [])[:5]),
                    *(t.text for t in (kw_tweets.latest or [])[:5])
                ])
                try:
                    out = thinker.headlines_for_keyword(product.name, product.description or "", kw, tweets_text, n=3)
                    for h in out.get('with_tweets', [])[:3]:
                        add_headline(h, 'kw_g2', 'subscriber', 0.8, {"keyword": kw, "with_tweets": True})
                    for h in out.get('without_tweets', [])[:3]:
                        add_headline(h, 'kw_g2', 'subscriber', 0.7, {"keyword": kw, "with_tweets": False})
                except Exception as e:
                    logger.error(e)

            # 9. Headlines per Medium tag using trending articles
            for tg in medium_tags[:10]:
                arts = trending_by_tag.get(tg) or []
                titles = "\n".join([getattr(a, 'title') or '' for a in arts[:10]])
                try:
                    heads = thinker.headlines_for_medium_tag(product.name, product.description or "", tg, titles, n=3)
                    for h in heads:
                        add_headline(h, 'medium_tag', 'subscriber', 0.75, {"tag": tg})
                except Exception as e:
                    logger.error(e)

            # 10. Witty replies for every fetched tweet (rank and keep top 5 per source)
            def top_replies_for(items, source_key):
                candidates = []
                for tw in items:
                    text = tw.text
                    if not text:
                        continue
                    try:
                        rep_text = thinker.witty_reply(product.name, product.description or "", text)
                        if rep_text:
                            score = min(1.0, max(0.1, len(rep_text) / 280))
                            candidates.append((score, rep_text))
                    except Exception:
                        continue
                candidates.sort(key=lambda x: x[0], reverse=True)
                for i, (_, r) in enumerate(candidates[:5]):
                    add_reply(r, source_key, 'subscriber', 0.9 - i*0.1)

            # from topics
            for tp in topics[:10]:
                ctx = tweets_by_topic.get(tp)
                top_replies_for((ctx.top or []) + (ctx.latest or []), 'trending_topic')
            # from kw groups
            for kw in (resp.get('group1') or [])[:10]:
                ctx = tweets_by_kw_g1.get(kw)
                top_replies_for((ctx.top or []) + (ctx.latest or []), 'kw_g1')
            for kw in expanded_group2[:10]:
                ctx = tweets_by_kw_g2.get(kw)
                top_replies_for((ctx.top or []) + (ctx.latest or []), 'kw_g2')

            rep.mark_partial()  # as soon as some suggestions exist

            # On complete
            rep.mark_complete()
        except Exception as e:
            logger.exception(e)
            rep.mark_failed(str(e))


def generate_article(article_id: str):
    with _app_context():
        art = Article.query.get(article_id)
        if not art:
            logger.error(f"Article {article_id} not found")
            return
        try:
            # Minimal content placeholder until full prompt designed
            art.content_md = f"# {art.title}\n\n(Generated content will appear here.)"
            art.content_html = f"<h1>{art.title}</h1><p>(Generated content will appear here.)</p>"
            art.status = 'ready'
            db.session.add(art)
            db.session.commit()
        except Exception as e:
            logger.exception(e)
            art.status = 'failed'
            art.error_message = str(e)
            db.session.add(art)
            db.session.commit()
