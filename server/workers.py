from models.db_utils import db
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.product import Product
from openai_utils import get_reply_json
from config import logger, serpapi_key, rapidapi_key, enable_twitter, enable_medium
import json
import requests
from clients.twitter_client import TwitterClient
from clients.medium_client import MediumClient
from clients.serp_client import SerpApiClient


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
            system = (
                "You are an expert content strategist. Given a product name and description, "
                "return two groups of keywords: group1 (keywords prospective clients write about on Twitter) "
                "and group2 (keywords people search on Google). Respond as JSON {\"group1\":[],\"group2\":[]}"
            )
            user_msg = f"Product: {product.name}\nDescription: {product.description}"
            try:
                resp = get_reply_json(getattr(product, 'user', None), system, user_msg)
            except Exception as e:
                logger.exception(e)
                resp = {"group1": [], "group2": []}
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
                    filter_system = "Select the most relevant topics to the product from this list. Return JSON {\"topics\":[\"...\"]}."
                    filter_user = f"Product: {product.name}. Description: {product.description}. Topics: {json.dumps(trend_names)}"
                    try:
                        filt = get_reply_json(getattr(product, 'user', None), filter_system, filter_user)
                        topics = (filt.get('topics') or [])[:10]
                    except Exception:
                        topics = trend_names[:5]
                    # Fetch tweets for each topic
                    for tp in topics:
                        res = tw.search(tp, count=5)
                        tweets_by_topic[tp] = {"top": res.top, "latest": res.latest}
                    # Fetch tweets for kw group1
                    for kw in (resp.get('group1') or [])[:15]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g1[kw] = {"top": res.top, "latest": res.latest}
                    # Fetch tweets for kw group2 (expanded)
                    for kw in expanded_group2[:20]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g2[kw] = {"top": res.top, "latest": res.latest}
                    s3.done(json.dumps({
                        "topics": topics,
                        "by_topic": {k: {"top": len(v.get('top', [])), "latest": len(v.get('latest', []))} for k, v in tweets_by_topic.items()},
                        "g1": {k: {"top": len(v.get('top', [])), "latest": len(v.get('latest', []))} for k, v in tweets_by_kw_g1.items()},
                        "g2": {k: {"top": len(v.get('top', [])), "latest": len(v.get('latest', []))} for k, v in tweets_by_kw_g2.items()},
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
                    # Select relevant tags via LLM
                    tag_system = "From the provided Medium root tags, pick the ones related to the product. Return JSON {\"tags\":[\"...\"]}."
                    tag_user = f"Product: {product.name}. Description: {product.description}. Tags: {json.dumps(all_tags)}"
                    try:
                        sel = get_reply_json(getattr(product, 'user', None), tag_system, tag_user)
                        medium_tags = (sel.get('tags') or [])[:10]
                    except Exception:
                        medium_tags = all_tags[:5]
                    # Fetch trending articles per tag
                    for tg in medium_tags:
                        trending_by_tag[tg] = md.trending_for_tag(tg, limit=10)
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
                tweets_ctx = tweets_by_topic.get(tp) or {}
                tweets_text = "\n".join([
                    *(t.get('text') or t.get('full_text') or '' for t in (tweets_ctx.get('top') or [])[:5]),
                    *(t.get('text') or t.get('full_text') or '' for t in (tweets_ctx.get('latest') or [])[:5])
                ])
                sys = "Generate 5 compelling article headlines for the topic using the tweet context. Return as JSON {\"headlines\":[\"...\"]}."
                usr = f"Product: {product.name}. Description: {product.description}. Topic: {tp}. Tweets: {tweets_text[:3000]}"
                try:
                    out = get_reply_json(getattr(product, 'user', None), sys, usr)
                    for i, h in enumerate((out.get('headlines') or [])[:5]):
                        add_headline(h, 'trending_topic', 'guest' if i < (rep.visibility_cutoff or 5) else 'subscriber', rank=1.0 - i*0.1, meta={"topic": tp})
                except Exception as e:
                    logger.error(e)

            # 7. Potential tweets per trending topic
            for tp in topics[:10]:
                sys = "Write 5 potential tweets about the topic aligned with the product positioning. Return JSON {\"tweets\":[\"...\"]}."
                usr = f"Product: {product.name}. Description: {product.description}. Topic: {tp}."
                try:
                    out = get_reply_json(getattr(product, 'user', None), sys, usr)
                    for i, t in enumerate((out.get('tweets') or [])[:5]):
                        add_tweet(t, 'trending_topic', 'guest' if i < 1 else 'subscriber', rank=1.0 - i*0.1, meta={"topic": tp})
                except Exception as e:
                    logger.error(e)

            # 8. Headlines per keyword in expanded group2, with tweets and without
            for kw in expanded_group2[:15]:
                kw_tweets = tweets_by_kw_g2.get(kw) or {}
                tweets_text = "\n".join([
                    *(t.get('text') or t.get('full_text') or '' for t in (kw_tweets.get('top') or [])[:5]),
                    *(t.get('text') or t.get('full_text') or '' for t in (kw_tweets.get('latest') or [])[:5])
                ])
                sys = "Generate 3 SEO-friendly article headlines around the keyword using the tweet context if provided. Return JSON {\"with_tweets\":[\"...\"],\"without_tweets\":[\"...\"]}."
                usr = f"Product: {product.name}. Description: {product.description}. Keyword: {kw}. Tweets: {tweets_text[:3000]}"
                try:
                    out = get_reply_json(getattr(product, 'user', None), sys, usr)
                    for h in (out.get('with_tweets') or [])[:3]:
                        add_headline(h, 'kw_g2', 'subscriber', 0.8, {"keyword": kw, "with_tweets": True})
                    for h in (out.get('without_tweets') or [])[:3]:
                        add_headline(h, 'kw_g2', 'subscriber', 0.7, {"keyword": kw, "with_tweets": False})
                except Exception as e:
                    logger.error(e)

            # 9. Headlines per Medium tag using trending articles
            for tg in medium_tags[:10]:
                arts = trending_by_tag.get(tg) or []
                titles = "\n".join([a.get('title') or '' for a in arts[:10]])
                sys = "Generate 3 article headlines inspired by these trending Medium articles for the given tag. Return JSON {\"headlines\":[\"...\"]}."
                usr = f"Product: {product.name}. Description: {product.description}. Tag: {tg}. Articles: {titles[:3000]}"
                try:
                    out = get_reply_json(getattr(product, 'user', None), sys, usr)
                    for h in (out.get('headlines') or [])[:3]:
                        add_headline(h, 'medium_tag', 'subscriber', 0.75, {"tag": tg})
                except Exception as e:
                    logger.error(e)

            # 10. Witty replies for every fetched tweet (rank and keep top 5 per source)
            def top_replies_for(items, source_key):
                candidates = []
                for tw in items:
                    text = tw.get('text') or tw.get('full_text') or ''
                    if not text:
                        continue
                    sys = "Write a witty but helpful single-tweet reply. Return JSON {\"reply\":\"...\"}."
                    usr = f"Tweet: {text[:500]}\nProduct: {product.name}. Description: {product.description}."
                    try:
                        out = get_reply_json(getattr(product, 'user', None), sys, usr)
                        rep_text = out.get('reply')
                        if rep_text:
                            # naive score based on length/keywords; replace with proper model ranking later
                            score = min(1.0, max(0.1, len(rep_text) / 280))
                            candidates.append((score, rep_text))
                    except Exception:
                        continue
                candidates.sort(key=lambda x: x[0], reverse=True)
                for i, (_, r) in enumerate(candidates[:5]):
                    add_reply(r, source_key, 'subscriber', 0.9 - i*0.1)

            # from topics
            for tp in topics[:10]:
                ctx = tweets_by_topic.get(tp) or {}
                top_replies_for((ctx.get('top') or []) + (ctx.get('latest') or []), 'trending_topic')
            # from kw groups
            for kw in (resp.get('group1') or [])[:10]:
                ctx = tweets_by_kw_g1.get(kw) or {}
                top_replies_for((ctx.get('top') or []) + (ctx.get('latest') or []), 'kw_g1')
            for kw in expanded_group2[:10]:
                ctx = tweets_by_kw_g2.get(kw) or {}
                top_replies_for((ctx.get('top') or []) + (ctx.get('latest') or []), 'kw_g2')

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
