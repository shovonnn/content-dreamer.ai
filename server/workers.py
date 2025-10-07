from models.db_utils import db
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.product import Product
from openai_utils import get_reply_json, generate_image_base64
from config import logger, serpapi_key, rapidapi_key, enable_twitter, enable_medium
import json
from clients.twitter_client import TwitterClient, TweetSummary
from clients.medium_client import MediumClient
from clients.serp_client import SerpApiClient
from clients.thinking_client import ThinkingClient
import random
from typing import List, Dict, Any, Optional
from models.meme import Meme


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
            prospect_keywords = random.sample(resp.get('group1') or [], min(2, len(resp.get('group1') or [])))

            # Step 2: Expand group2 with SerpAPI autocomplete
            expanded_group2 = list(resp.get('group2') or [])
            s2 = ReportStep.start(rep.id, 'serpapi_expand')
            try:
                if serpapi_key:
                    sa = SerpApiClient(api_key=serpapi_key)
                    expanded_group2 = sa.expand_keywords(expanded_group2, limit=100, per_kw_limit=10)
                    expanded_group2 = thinker.filter_keywords(product.name, product.description or "", expanded_group2, limit=5)
                    # take random 2
                    if len(expanded_group2) >= 2:
                        expanded_group2 = random.sample(expanded_group2, 2)
                    s2.done(json.dumps({"expanded_group2": expanded_group2}))
                else:
                    s2.done(json.dumps({"warning": "SERPAPI_KEY missing", "expanded_group2": expanded_group2}))
            except Exception as e:
                # Ensure we clear failed state before attempting to persist failure
                try:
                    db.session.rollback()
                except Exception:
                    pass
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
                    # expanded_trends = sa.expand_keywords(trend_names, limit=100, per_kw_limit=5) if serpapi_key else trend_names
                    expanded_trends = trend_names
                    
                    # Filter topics with LLM for relevance
                    topics = thinker.filter_topics(product.name, product.description or "", expanded_trends, limit=10)
                    if len(topics) == 0:
                        # take 2 random trends if expansion fails
                        topics = random.sample(trend_names, min(2, len(trend_names)))
                    if len(topics) >= 3:
                        # take random 3 if too many
                        topics = random.sample(topics, 2)
                    # Fetch tweets for each topic
                    for tp in topics:
                        res = tw.search(tp, count=5)
                        tweets_by_topic[tp] = res
                    # Fetch tweets for kw group1
                    for kw in (prospect_keywords or [])[:15]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g1[kw] = res
                    # Fetch tweets for kw group2 (expanded)
                    for kw in expanded_group2[:20]:
                        res = tw.search(kw, count=5)
                        tweets_by_kw_g2[kw] = res
                    # Keep payload compact to avoid exceeding DB TEXT limits
                    def pack_res(r):
                        try:
                            topc = len(r.top or [])
                            latc = len(r.latest or [])
                            sample = (r.top[0].text if (r.top or []) else ((r.latest or [None])[0].text if (r.latest or []) else None))
                            if sample:
                                sample = sample[:200]
                            return {"top_count": topc, "latest_count": latc, "sample": sample}
                        except Exception:
                            return {"top_count": 0, "latest_count": 0, "sample": None}
                    payload = {
                        "trends": topics,
                        "by_trend": {k: pack_res(v) for k, v in tweets_by_topic.items()},
                        "g1": {k: pack_res(v) for k, v in tweets_by_kw_g1.items()},
                        "g2": {k: pack_res(v) for k, v in tweets_by_kw_g2.items()},
                    }
                    s3.done(json.dumps(payload))
                else:
                    s3.done(json.dumps({"warning": "Twitter disabled or RAPIDAPI_KEY missing"}))
            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                s3.fail(str(e))

            # Step 5: Medium tags and trending articles via RapidAPI
            medium_tags = []
            trending_by_tag = {}
            s5 = ReportStep.start(rep.id, 'medium_tags_and_articles')
            try:
                if enable_medium and rapidapi_key:
                    md = MediumClient(api_key=rapidapi_key)
                    # Select relevant tags via LLM using thinking client
                    medium_tags = md.get_all_available_tags(limit=200)
                    medium_tags = thinker.filter_keywords(product.name, product.description or "", medium_tags, limit=20)
                    if len(medium_tags) >= 2:
                        medium_tags = random.sample(medium_tags, 2)
                    # Fetch trending articles per tag
                    for tg in medium_tags:
                        trending_by_tag[tg] = md.get_trending_articles(tg, limit=2)
                    s5.done(json.dumps({"tags": medium_tags, "counts": {k: len(v) for k, v in trending_by_tag.items()}}))
                else:
                    s5.done(json.dumps({"warning": "Medium disabled or RAPIDAPI_KEY missing"}))
            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
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

            def add_meme_concept(concept: str, source_type: str, visibility='subscriber', rank: float = 0.5, meta: Optional[dict] = None):
                try:
                    m = meta or {}
                    # kind: 'meme_concept' to distinguish in UI
                    Suggestion.add(rep.id, source_type, 'meme_concept', concept, rank, json.dumps(m), visibility)
                except Exception as e:
                    logger.error(f"add_meme_concept failed: {e}")

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
                    articles = thinker.articles_for_topic(product.name, product.description or "", tp, tweets_text, n=2)
                    for i, h in enumerate(articles):
                        add_headline(
                            h.get('title'),
                            'trending_topic',
                            'guest' if i < (rep.visibility_cutoff or 5) else 'subscriber',
                            rank=1.0 - i*0.1,
                            meta={
                                "title": h.get('title'),
                                "description": h.get('description'),
                                "topic": tp,
                                "reason": f"From trending topic '{tp}' likely relevant to your audience",
                            },
                        )
                except Exception as e:
                    logger.error(e)

            # 7. Potential tweets per trending topic
            for tp in topics[:10]:
                try:
                    twts = tweets_by_topic.get(tp)
                    if twts:
                        context = "\n".join([
                            *(t.text for t in (twts.top or [])[:5]),
                            *(t.text for t in (twts.latest or [])[:5])
                        ])
                    else:
                        context = None
                    tweets = thinker.tweets_for_topic(product.name, product.description or "", tp, context, n=2)
                    for i, t in enumerate(tweets):
                        add_tweet(
                            t,
                            'trending_topic',
                            'guest' if i < 1 else 'subscriber',
                            rank=1.0 - i*0.1,
                            meta={
                                "topic": tp,
                                "reason": f"Tweet idea based on trending topic '{tp}'",
                            },
                        )
                except Exception as e:
                    logger.error(e)

            # 7b. Meme concepts per trending topic
            for tp in topics[:10]:
                try:
                    twts = tweets_by_topic.get(tp)
                    context = None
                    if twts:
                        context = "\n".join([
                            *(t.text for t in (twts.top or [])[:5]),
                            *(t.text for t in (twts.latest or [])[:5])
                        ])
                    memes = thinker.meme_ideas_from_twitter(product.name, product.description or "", tp, context, n=2)
                    for i, m in enumerate(memes):
                        add_meme_concept(
                            m.get('concept') or 'Meme idea',
                            'trending_topic',
                            'guest' if i < 1 else 'subscriber',
                            rank=0.55 - i*0.05,
                            meta={
                                "topic": tp,
                                "instructions": m.get('instructions'),
                                "reason": f"Meme idea based on trending topic '{tp}'",
                            }
                        )
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
                    articles = thinker.articles_for_topic(product.name, product.description or "", kw, tweets_text, n=2)
                    for h in articles:
                        add_headline(
                            h.get('title'),
                            'kw_g2',
                            'subscriber',
                            0.8,
                            {
                                "title": h.get('title'),
                                "description": h.get('description'),
                                "keyword": kw, "with_tweets": True, "reason": f"From keyword '{kw}'"}
                        )
                    
                    articles = thinker.articles_for_topic(product.name, product.description or "", kw, None, n=2)
                    for h in articles:
                        add_headline(
                            h.get('title'),
                            'kw_g2',
                            'subscriber',
                            0.7,
                            {
                                "title": h.get('title'),
                                "description": h.get('description'),
                                 "keyword": kw, "with_tweets": False, "reason": f"From keyword '{kw}'"}
                        )
                except Exception as e:
                    logger.error(e)

            # 9. Headlines per Medium tag using trending articles
            for tg in medium_tags[:10]:
                arts = trending_by_tag.get(tg) or []
                titles = "\n".join([getattr(a, 'title')+'\n'+getattr(a, 'subtitle') or '' for a in arts[:10]])
                try:
                    heads = thinker.articles_for_topic(product.name, product.description or "", tg, titles, n=2)
                    for h in heads:
                        add_headline(
                            h.get('title'),
                            'medium_tag',
                            'subscriber',
                            0.75,
                            {
                                "title": h.get('title'),
                                "description": h.get('description'),
                                "tag": tg, "reason": f"Inspired by trending articles under Medium tag '{tg}'"
                            }
                        )
                except Exception as e:
                    logger.error(e)

            # generate tweets from trending articles too
            for tg in medium_tags[:10]:
                arts = trending_by_tag.get(tg) or []
                titles = "\n".join([getattr(a, 'title')+'\n'+getattr(a, 'subtitle') or '' for a in arts[:10]])
                try:
                    tweets = thinker.tweets_for_topic(product.name, product.description or "", tg, titles, n=2)
                    for i, t in enumerate(tweets):
                        add_tweet(
                            t,
                            'medium_tag',
                            'subscriber' if i >= 1 else 'guest',
                            rank=0.6 - i*0.1,
                            meta={
                                "tag": tg,
                                "reason": f"Tweet idea based on trending articles under Medium tag '{tg}'",
                            },
                        )
                except Exception as e:
                    logger.error(e)

            # 9b. Meme concepts based on Medium tags/titles
            for tg in medium_tags[:10]:
                arts = trending_by_tag.get(tg) or []
                for a in arts[:3]:
                    title = getattr(a, 'title', '')
                    subtitle = getattr(a, 'subtitle', '')
                    try:
                        memes = thinker.meme_ideas_from_medium(product.name, product.description or "", title, subtitle, n=1)
                        for m in memes:
                            add_meme_concept(
                                m.get('concept') or 'Meme idea',
                                'medium_tag',
                                'subscriber',
                                rank=0.5,
                                meta={
                                    "tag": tg,
                                    "title": title,
                                    "subtitle": subtitle,
                                    "instructions": m.get('instructions'),
                                    "reason": f"Meme idea inspired by Medium article '{title}'",
                                }
                            )
                    except Exception as e:
                        logger.error(e)

            # 10. Witty replies for every fetched tweet (rank and keep top 5 per source)
            def top_replies_for(items, source_key, source_label=None):
                candidates = []
                for tw in items or []:
                    try:
                        base_text = getattr(tw, 'text', None) or (tw.get('text') if isinstance(tw, dict) else None)
                        if not base_text:
                            continue
                        rep_text = thinker.witty_reply(product.name, product.description or "", base_text)
                        if rep_text:
                            score = min(1.0, max(0.1, len(rep_text) / 280))
                            candidates.append((score, rep_text, tw))
                    except Exception:
                        continue
                candidates.sort(key=lambda x: x[0], reverse=True)
                for i, (_, r, tw) in enumerate(candidates[:10]):
                    # Build meta with original tweet details
                    try:
                        if hasattr(tw, 'to_dict'):
                            st = tw.to_dict()
                        elif isinstance(tw, TweetSummary):
                            st = {
                                "text": tw.text,
                                "user_name": tw.user_name,
                                "like_count": tw.like_count,
                                "retweet_count": tw.retweet_count,
                                "reply_count": tw.reply_count,
                            }
                        elif isinstance(tw, dict):
                            st = tw
                        else:
                            st = {"text": getattr(tw, 'text', None)}
                    except Exception:
                        st = {"text": getattr(tw, 'text', None)}
                    add_reply(
                        r,
                        source_key,
                        'subscriber',
                        0.9 - i*0.1,
                        {
                            "reason": f"Reply crafted for a tweet under '{source_label}'" if source_label else f"Reply crafted for a tweet",
                            "source_label": source_label,
                            "source_tweet": st,
                        },
                    )

            # from topics
            for tp in topics[:10]:
                ctx = tweets_by_topic.get(tp)
                #pick random 2 tweets from top+latest
                if ctx:
                    random_tweets = random.sample(((ctx.top or []) + (ctx.latest or [])), 2)
                    top_replies_for(random_tweets, 'trending_topic', tp)
            # from kw groups
            for kw in (prospect_keywords or [])[:10]:
                ctx = tweets_by_kw_g1.get(kw)
                if ctx:
                    random_tweets = random.sample(((ctx.top or []) + (ctx.latest or [])), 2)
                    top_replies_for(random_tweets, 'kw_g1', kw)
            for kw in expanded_group2[:10]:
                ctx = tweets_by_kw_g2.get(kw)
                if ctx:
                    random_tweets = random.sample(((ctx.top or []) + (ctx.latest or [])), 2)
                    top_replies_for(random_tweets, 'kw_g2', kw)

            rep.mark_partial()  # as soon as some suggestions exist

            # On complete
            rep.mark_complete()
        except Exception as e:
            logger.exception(e)
            rep.mark_failed(str(e))


def generate_article(article_id: str):
    with _app_context():
        from markdown import markdown
        art = Article.query.get(article_id)
        thinker = ThinkingClient(user=getattr(art.report.product, 'user', None)) if art else None
        if not art:
            logger.error(f"Article {article_id} not found")
            return
        try:
            # Minimal content placeholder until full prompt designed
            content = thinker.article_content(art.title, art.description or "")
            art.content_md = content.get('content_md')
            art.content_html = markdown(content.get('content_md', ''))
            art.status = 'ready'
            db.session.add(art)
            db.session.commit()
            # fetch suggestion and add article details to its meta
            if art.suggestion_id:
                sug = Suggestion.query.get(art.suggestion_id)
                if sug:
                    try:
                        meta = json.loads(sug.meta_json or '{}')
                    except Exception:
                        meta = {}
                    meta.update({
                        "article_id": art.id,
                        "article_title": art.title,
                        "article_description": art.description,
                    })
                    sug.meta_json = json.dumps(meta)
                    db.session.add(sug)
                    db.session.commit()
        except Exception as e:
            logger.exception(e)
            art.status = 'failed'
            art.error_message = str(e)
            db.session.add(art)
            db.session.commit()


def generate_meme(meme_id: str):
    with _app_context():
        mem = Meme.query.get(meme_id)
        if not mem:
            logger.error(f"Meme {meme_id} not found")
            return
        try:
            # Build a text prompt from instructions_json
            prompt_parts = []
            if mem.concept:
                prompt_parts.append(f"Concept: {mem.concept}")
            try:
                instr = json.loads(mem.instructions_json or '{}')
            except Exception:
                instr = {}
            template = instr.get('template')
            scene_description = instr.get('scene_description')
            style = instr.get('style')
            overlays = instr.get('text_overlays') or []
            if template:
                prompt_parts.append(f"Template: {template}")
            if scene_description:
                prompt_parts.append(f"Scene: {scene_description}")
            if style:
                prompt_parts.append(f"Style: {style}")
            if overlays:
                texts = "; ".join([f"{(o.get('position') or 'center')}: {o.get('text')}" for o in overlays if isinstance(o, dict)])
                prompt_parts.append(f"Text: {texts}")
            prompt = "\n".join(prompt_parts) or (mem.concept or 'Create a witty internet meme image')
            img_b64 = generate_image_base64(prompt, size='1024x1024')
            # Save to local static and store path
            import base64 as _b64, os
            from uuid import uuid4 as _uuid4
            data = _b64.b64decode(img_b64)
            # Determine directory and ensure it exists
            rel_dir = f"uploads/memes/{mem.report_id}"
            base_dir = os.path.dirname(os.path.abspath(__file__))
            root = os.path.join(base_dir, 'static', rel_dir)
            os.makedirs(root, exist_ok=True)
            fname = f"{_uuid4().hex}.png"
            dest = os.path.join(root, fname)
            with open(dest, 'wb') as f:
                f.write(data)
            # Store relative path (under static)
            mem.image_path = f"{rel_dir}/{fname}"
            # Clear heavy columns if previously used
            mem.image_bytes = None
            mem.image_b64 = None
            mem.status = 'ready'
            mem.model_used = 'gpt-image-1'
            db.session.add(mem)
            db.session.commit()
            # backfill suggestion meta with meme_id
            if mem.suggestion_id:
                sug = Suggestion.query.get(mem.suggestion_id)
                if sug:
                    try:
                        meta = json.loads(sug.meta_json or '{}')
                    except Exception:
                        meta = {}
                    meta.update({"meme_id": mem.id})
                    sug.meta_json = json.dumps(meta)
                    db.session.add(sug)
                    db.session.commit()
        except Exception as e:
            logger.exception(e)
            mem.status = 'failed'
            mem.error_message = str(e)
            db.session.add(mem)
            db.session.commit()
