from models.db_utils import db
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.product import Product
from openai_utils import get_reply_json
from config import logger
import json


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
                # Dummy call structure; actual parsing handled in openai_utils
                resp = get_reply_json(product.user or None, system, user_msg)
            except Exception as e:
                logger.exception(e)
                resp = {"group1": [], "group2": []}
            s1.done(json.dumps(resp))

            # TODO: Step 2-5: SerpAPI, Twitter RapidAPI, Medium RapidAPI with ReportStep logs

            # TODO: Steps 6-10: Generate suggestions and store Suggestion rows

            # Insert a minimal example suggestion so partial UI has content
            Suggestion.add(
                report_id=rep.id,
                source_type='trending_topic',
                kind='article_headline',
                text=f"How {product.name} changes the game in 2025",
                rank=0.9,
                meta_json=json.dumps({'demo': True}),
                visibility='guest',
            )

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
