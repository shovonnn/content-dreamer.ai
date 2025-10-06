from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models.db_utils import db
from models.user import User
from models.product import Product
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.subscription import SubscriptionPlan, UserSubscription, UsageQuota
from plans import get_plans
from datetime import date
from uuid import uuid4
from queue_util import q
import json
from config import logger

bp_reports = Blueprint('bp_reports', __name__)


def _current_user_or_none():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if not uid:
            return None
        return User.query.get(uid)
    except Exception:
        return None


def _request_guest_id():
    # Prefer header, fallback to query param
    return (request.headers.get('X-Guest-Id') or request.args.get('guest_id') or '').strip() or None


@bp_reports.route('/api/plans', methods=['GET'])
def list_plans():
    plans = get_plans()
    return jsonify(plans), 200


@bp_reports.route('/api/reports/initiate', methods=['POST'])
@bp_reports.route('/api/feeds/initiate', methods=['POST'])  # alias path using feed terminology
def initiate_report():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('product_name') or '').strip()
    desc = (data.get('product_description') or '').strip()
    guest_id = (data.get('guest_id') or '').strip() or None
    if not name or not desc:
        abort(400, 'product_name and product_description required')
    current_user = _current_user_or_none()
    user_id = current_user.id if current_user else None

    # Enforce guest rule: only one report per guest until login
    if not user_id and guest_id:
        existing = Report.query.filter_by(guest_id=guest_id).first()
        if existing:
            return jsonify({'report_id': existing.id}), 200

    prod = Product.create(name=name, description=desc, user_id=user_id, guest_id=guest_id)
    # Visibility cutoff from plan config (basic default for guests)
    visibility_cutoff = 5
    rep = Report.create(product_id=prod.id, user_id=user_id, guest_id=guest_id, visibility_cutoff=visibility_cutoff)

    # Enqueue background job
    q.enqueue('workers.generate_report', rep.id, job_timeout='30m')

    return jsonify({'report_id': rep.id}), 200


@bp_reports.route('/api/reports/<rid>', methods=['GET'])
@bp_reports.route('/api/feeds/<rid>', methods=['GET'])  # alias path using feed terminology
def get_report(rid):
    rep = Report.query.get(rid)
    if not rep:
        abort(404)
    current_user = _current_user_or_none()
    is_owner = True
    if current_user and rep.user_id == current_user.id:
        is_owner = True
    # Guest cookie flow: allow if guest_id provided and matches
    req_guest_id = request.args.get('guest_id') or (request.headers.get('X-Guest-Id'))
    is_guest_owner = (rep.guest_id and req_guest_id and rep.guest_id == req_guest_id and not rep.user_id)

    # suggestions selection
    if is_owner:
        suggestions = [
            {
                'id': s.id,
                'kind': s.kind,
                'source_type': s.source_type,
                'text': s.text,
                'rank': s.rank,
                'meta': (json.loads(s.meta_json) if s.meta_json else None),
            } for s in rep.suggestions
        ]
        partial = False
    elif is_guest_owner:
        # Return partial set for guests
        all_guest = [s for s in rep.suggestions if s.visibility in ('guest', 'subscriber')]
        all_guest.sort(key=lambda x: x.rank or 0, reverse=True)
        suggestions = [
            {
                'id': s.id,
                'kind': s.kind,
                'source_type': s.source_type,
                'text': s.text,
                'rank': s.rank,
                'meta': (json.loads(s.meta_json) if s.meta_json else None),
            } for s in all_guest[: (rep.visibility_cutoff or 5)]
        ]
        partial = True
    else:
        # Not allowed to see details, return status only
        return jsonify({
            'id': rep.id,
            'status': rep.status,
            'partial': True,
            'suggestions': [],
            'steps': [{'step_name': st.step_name, 'status': st.status} for st in rep.steps],
        }), 200

    return jsonify({
        'id': rep.id,
        'product': {
            'id': rep.product.id,
            'name': rep.product.name,
            'description': rep.product.description,
        },
        'status': rep.status,
        'partial': partial,
        'suggestions': suggestions,
        'steps': [{'step_name': st.step_name, 'status': st.status} for st in rep.steps],
    }), 200


@bp_reports.route('/api/reports/<rid>/regenerate', methods=['POST'])
@jwt_required()
def regenerate_report(rid):
    current_user_id = get_jwt_identity()
    rep = Report.query.get(rid)
    if not rep or (rep.user_id != current_user_id):
        abort(404)
    # TODO: enforce quota here
    new_rep = Report.create(product_id=rep.product_id, user_id=current_user_id, visibility_cutoff=rep.visibility_cutoff)
    q.enqueue('workers.generate_report', new_rep.id, job_timeout='30m')
    return jsonify({'report_id': new_rep.id}), 200


@bp_reports.route('/api/articles', methods=['POST'])
@jwt_required()
def create_article():
    data = request.get_json(force=True, silent=True) or {}
    suggestion_id = data.get('suggestion_id')
    if not suggestion_id:
        abort(400, 'suggestion_id required')
    sug = Suggestion.query.get(suggestion_id)
    if not sug:
        abort(404)
    rep = sug.report
    current_user_id = get_jwt_identity()
    if rep.user_id != current_user_id:
        abort(403)
    # TODO: enforce article quota
    art = Article.create(report_id=rep.id, title=sug.text[:140], suggestion_id=sug.id)
    # enqueue article generation
    q.enqueue('workers.generate_article', art.id, job_timeout='15m')
    return jsonify({'article_id': art.id, 'status': art.status}), 200


@bp_reports.route('/api/articles/<aid>', methods=['GET'])
@jwt_required()
def get_article(aid):
    art = Article.query.get(aid)
    if not art:
        abort(404)
    current_user_id = get_jwt_identity()
    if art.report.user_id != current_user_id:
        abort(403)
    return jsonify({
        'id': art.id,
        'title': art.title,
        'content_html': art.content_html,
        'content_md': art.content_md,
        'status': art.status,
        'error': art.error_message,
    }), 200


@bp_reports.route('/api/merge-guest-reports', methods=['POST'])
@jwt_required()
def merge_guest_reports():
    data = request.get_json(force=True, silent=True) or {}
    guest_id = (data.get('guest_id') or '').strip()
    if not guest_id:
        abort(400, 'guest_id required')
    uid = get_jwt_identity()
    # move products
    from models.product import Product
    from models.report import Report
    products = Product.query.filter_by(guest_id=guest_id).all()
    for p in products:
        p.user_id = uid
        p.guest_id = None
        db.session.add(p)
    reports = Report.query.filter_by(guest_id=guest_id).all()
    for r in reports:
        r.user_id = uid
        r.guest_id = None
        db.session.add(r)
    db.session.commit()
    return jsonify({'merged': True}), 200


@bp_reports.route('/api/me/limits', methods=['GET'])
@jwt_required()
def my_limits():
    uid = get_jwt_identity()
    # Simplified: return basic defaults for now
    plans = get_plans()
    # TODO: fetch actual user subscription
    plan = next((p for p in plans if p['id'] == 'basic'), plans[0])
    return jsonify({'plan_id': plan['id'], 'limits': plan['limits']}), 200


# -------- Products and Feeds (reports) management --------

@bp_reports.route('/api/products', methods=['GET'])
def list_products():
    """List products for current user or guest, including latest feed summary."""
    current_user = _current_user_or_none()
    guest_id = _request_guest_id()
    q = None
    if current_user:
        q = Product.query.filter_by(user_id=current_user.id)
    elif guest_id:
        q = Product.query.filter_by(guest_id=guest_id)
    else:
        return jsonify({'products': []}), 200

    products = q.order_by(Product.created_on.desc()).all()
    # Collect latest report per product
    out = []
    for p in products:
        latest = Report.query.filter_by(product_id=p.id).order_by(Report.created_on.desc()).first()
        out.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'created_on': p.created_on.isoformat() if p.created_on else None,
            'updated_on': p.updated_on.isoformat() if p.updated_on else None,
            'latest_feed': ({
                'id': latest.id,
                'status': latest.status,
                'created_on': latest.created_on.isoformat() if latest and latest.created_on else None,
                'completed_at': latest.completed_at.isoformat() if latest and latest.completed_at else None,
            } if latest else None)
        })
    return jsonify({'products': out}), 200


@bp_reports.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    desc = (data.get('description') or '').strip()
    if not name or not desc:
        abort(400, 'name and description required')
    current_user = _current_user_or_none()
    guest_id = _request_guest_id()
    user_id = current_user.id if current_user else None
    prod = Product.create(name=name, description=desc, user_id=user_id, guest_id=(None if user_id else guest_id))
    return jsonify({
        'id': prod.id,
        'name': prod.name,
        'description': prod.description,
        'created_on': prod.created_on.isoformat() if prod.created_on else None,
    }), 200


def _ensure_product_access(pid: str):
    p = Product.query.get(pid)
    if not p:
        abort(404)
    current_user = _current_user_or_none()
    guest_id = _request_guest_id()
    if current_user and p.user_id == current_user.id:
        return p, current_user.id, None
    if (not current_user) and guest_id and p.guest_id == guest_id and not p.user_id:
        return p, None, guest_id
    abort(403)


@bp_reports.route('/api/products/<pid>/feeds/initiate', methods=['POST'])
def initiate_feed_for_product(pid):
    """Create a new feed (report) for an existing product."""
    p, user_id, guest_id = _ensure_product_access(pid)
    # Visibility cutoff: default 5 for guests, else from plan (simplified)
    visibility_cutoff = 5
    rep = Report.create(product_id=p.id, user_id=user_id, guest_id=guest_id, visibility_cutoff=visibility_cutoff)
    q.enqueue('workers.generate_report', rep.id, job_timeout='30m')
    return jsonify({'report_id': rep.id}), 200


@bp_reports.route('/api/products/<pid>/feeds', methods=['GET'])
def list_product_feeds(pid):
    p, user_id, guest_id = _ensure_product_access(pid)
    reports = Report.query.filter_by(product_id=p.id).order_by(Report.created_on.desc()).all()
    return jsonify({'feeds': [
        {
            'id': r.id,
            'status': r.status,
            'created_on': r.created_on.isoformat() if r.created_on else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
        } for r in reports
    ]}), 200
