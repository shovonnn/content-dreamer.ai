from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models.db_utils import db
from models.user import User
from models.product import Product
from models.report import Report
from models.report_step import ReportStep
from models.suggestion import Suggestion
from models.article import Article
from models.meme import Meme
from models.slop import Slop
from models.subscription import SubscriptionPlan, UserSubscription, UsageQuota
from plans import get_plans
from stripe_util import stripe
from datetime import datetime, timedelta
from datetime import date
from uuid import uuid4
from queue_util import q
import os
from stripe_util import webhook_secret
import json
from config import logger
import config as config
from markdown import markdown as md_to_html

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


@bp_reports.route('/api/billing/checkout', methods=['POST'])
@jwt_required()
def create_checkout_session():
    data = request.get_json(force=True, silent=True) or {}
    plan_id = (data.get('plan_id') or '').strip()
    if plan_id not in ('pro', 'advanced'):
        abort(400, 'Invalid plan_id')
    plans = get_plans()
    plan = next((p for p in plans if p['id'] == plan_id), None)
    if not plan or not plan.get('stripe_price_id'):
        abort(400, 'Plan not available')
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if not user:
        abort(404)
    sub = UserSubscription.query.filter_by(user_id=user.id).first()
    if sub and sub.stripe_subscription_id:
        sub.update_status()
        if sub.status in ('active', 'trialing') and sub.plan_id == plan_id:
            abort(400, 'You are already subscribed to this plan')
        elif sub.status in ('active', 'trialing') and sub.plan_id != plan_id:
            # lets update the subscription instead of creating a new one
            sub.switch_plan(plan)
            return jsonify({'url': None, 'success': 'Subscription updated successfully'}), 200

    # Ensure a customer
    customer = stripe.Customer.create(email=user.email or None, metadata={'user_id': user.id})
    # Derive return URLs
    origin = request.headers.get('Origin') or (getattr(config, 'app_url', None) or 'http://localhost:3000')
    # Create checkout session
    session = stripe.checkout.Session.create(
        mode='subscription',
        customer=customer.id,
        line_items=[{'price': plan['stripe_price_id'], 'quantity': 1}],
        success_url=origin + '/dashboard?upgrade=success',
        cancel_url=origin + '/pricing?canceled=1',
        allow_promotion_codes=True,
    )
    # Persist or update pending subscription record
    sub = UserSubscription.query.filter_by(user_id=user.id).first()
    if not sub:
        sub = UserSubscription.create(user_id=user.id, plan_id=plan_id, status='pending')
    else:
        sub.plan_id = plan_id
        sub.status = 'pending'
        db.session.add(sub)
        db.session.commit()
    # Record customer id for portal reuse
    sub.stripe_customer_id = customer.id
    db.session.add(sub)
    db.session.commit()
    return jsonify({'url': session.url}), 200


@bp_reports.route('/api/billing/portal', methods=['POST'])
@jwt_required()
def create_billing_portal():
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if not user:
        abort(404)
    # Try to find existing stripe customer via last subscription
    last = UserSubscription.query.filter_by(user_id=user.id).order_by(UserSubscription.current_period_end.desc()).first()
    customer_id = last.stripe_customer_id if last and last.stripe_customer_id else None
    if not customer_id:
        # Create if absent
        cust = stripe.Customer.create(email=user.email or None, metadata={'user_id': user.id})
        customer_id = cust.id
    portal = stripe.billing_portal.Session.create(customer=customer_id, return_url=(request.headers.get('Origin') or '*') + '/pricing')
    return jsonify({'url': portal.url}), 200


@bp_reports.route('/api/admin/sync_plans', methods=['POST'])
def admin_sync_plans():
    # Light admin guard: require header token if set
    admin_token = request.headers.get('X-Admin-Token')
    expected = os.getenv('ADMIN_SYNC_TOKEN')
    if expected and admin_token != expected:
        abort(403)
    plans = get_plans()
    for p in plans:
        rec = SubscriptionPlan.query.get(p['id'])
        limits_json = json.dumps(p['limits'])
        if not rec:
            rec = SubscriptionPlan(id=p['id'], price_usd=p['price_usd'], stripe_price_id=p.get('stripe_price_id'), limits_json=limits_json, active=True)
            db.session.add(rec)
        else:
            rec.price_usd = p['price_usd']
            rec.stripe_price_id = p.get('stripe_price_id')
            rec.limits_json = limits_json
            rec.active = True
            db.session.add(rec)
    db.session.commit()
    return jsonify({'synced': len(plans)}), 200


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
            return jsonify({'report_id': existing.id, 'prompt_login': True}), 200

    # Enforce daily quotas for authenticated users
    if user_id:
        enforce_ok, reason = _enforce_quota(user_id, kind='content')
        if not enforce_ok:
            return jsonify({'error': reason, 'upgrade_required': True}), 402

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
    ok, reason = _enforce_quota(current_user_id, kind='content')
    if not ok:
        return jsonify({'error': reason, 'upgrade_required': True}), 402
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
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    ok, reason = _enforce_quota(current_user_id, kind='article')
    if not ok:
        return jsonify({'error': reason, 'upgrade_required': True}), 402
    meta = json.loads(sug.meta_json) if sug.meta_json else {}
    art = Article.create(report_id=rep.id, title=sug.text, description=meta.get('description'), suggestion_id=sug.id)
    # persist article_id into suggestion meta for future quick access on the client
    try:
        meta = meta or {}
        meta['article_id'] = art.id
        sug.meta_json = json.dumps(meta)
        db.session.add(sug)
        db.session.commit()
    except Exception:
        logger.exception("Failed to persist article_id into suggestion meta")
    # enqueue article generation
    q.enqueue('workers.generate_article', art.id, job_timeout='15m')
    return jsonify({'article_id': art.id, 'status': art.status}), 200


@bp_reports.route('/api/slops', methods=['POST'])
@jwt_required()
def create_slop():
    data = request.get_json(force=True, silent=True) or {}
    suggestion_id = data.get('suggestion_id')
    if not suggestion_id:
        abort(400, 'suggestion_id required')
    sug = Suggestion.query.get(suggestion_id)
    if not sug:
        abort(404)
    rep = sug.report
    current_user_id = get_jwt_identity()
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    ok, reason = _enforce_quota(current_user_id, kind='video')
    if not ok:
        return jsonify({'error': reason, 'upgrade_required': True}), 402
    meta = json.loads(sug.meta_json) if sug.meta_json else {}
    concept = sug.text
    instructions_json = json.dumps(meta.get('instructions') or {})
    sl = Slop.create(report_id=rep.id, suggestion_id=sug.id, concept=concept, instructions_json=instructions_json)
    q.enqueue('workers.generate_slop', sl.id, job_timeout='30m')
    return jsonify({'slop_id': sl.id, 'status': sl.status}), 200


@bp_reports.route('/api/slops/<sid>', methods=['GET'])
@jwt_required()
def get_slop(sid):
    sl = Slop.query.get(sid)
    if not sl:
        abort(404)
    current_user_id = get_jwt_identity()
    rep = sl.report
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    return jsonify({'id': sl.id, 'status': sl.status, 'concept': sl.concept, 'error': sl.error_message}), 200


@bp_reports.route('/api/slops/<sid>/video', methods=['GET'])
def get_slop_video(sid):
    from flask import Response
    sl = Slop.query.get(sid)
    if not sl or sl.status != 'ready':
        abort(404)
    if not sl.video_path:
        abort(404)
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'static', sl.video_path) if not sl.video_path.startswith('static/') else os.path.join(base_dir, sl.video_path)
    if not os.path.exists(file_path):
        abort(404)
    with open(file_path, 'rb') as f:
        data = f.read()
    return Response(data, mimetype='video/mp4')


@bp_reports.route('/api/memes', methods=['POST'])
@jwt_required()
def create_meme():
    data = request.get_json(force=True, silent=True) or {}
    suggestion_id = data.get('suggestion_id')
    if not suggestion_id:
        abort(400, 'suggestion_id required')
    sug = Suggestion.query.get(suggestion_id)
    if not sug:
        abort(404)
    rep = sug.report
    current_user_id = get_jwt_identity()
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    # reuse article quota for meme generation to keep it simple
    ok, reason = _enforce_quota(current_user_id, kind='article')
    if not ok:
        return jsonify({'error': reason, 'upgrade_required': True}), 402
    meta = json.loads(sug.meta_json) if sug.meta_json else {}
    concept = sug.text
    instructions_json = json.dumps(meta.get('instructions') or {})
    mem = Meme.create(report_id=rep.id, suggestion_id=sug.id, concept=concept, instructions_json=instructions_json)
    # enqueue meme generation
    q.enqueue('workers.generate_meme', mem.id, job_timeout='10m')
    return jsonify({'meme_id': mem.id, 'status': mem.status}), 200


@bp_reports.route('/api/memes/<mid>', methods=['GET'])
@jwt_required()
def get_meme(mid):
    mem = Meme.query.get(mid)
    if not mem:
        abort(404)
    current_user_id = get_jwt_identity()
    rep = mem.report
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    return jsonify({
        'id': mem.id,
        'status': mem.status,
        'concept': mem.concept,
        'error': mem.error_message,
    }), 200


@bp_reports.route('/api/memes/<mid>/image', methods=['GET'])
def get_meme_image(mid):
    """Serve meme image as PNG for embedding or download.

    This endpoint is public; clients should use the meme id stored in suggestion meta. We do not expose user-identifying info.
    """
    from flask import Response
    mem = Meme.query.get(mid)
    if not mem or mem.status != 'ready':
        abort(404)
    # If we have a saved file path, serve it
    if getattr(mem, 'image_path', None):
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'static', mem.image_path) if not mem.image_path.startswith('static/') else os.path.join(base_dir, mem.image_path)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                data = f.read()
            return Response(data, mimetype='image/png')
    # Prefer bytes if present
    if mem.image_bytes:
        return Response(mem.image_bytes, mimetype='image/png')
    # Fallback to base64 if present
    if mem.image_b64:
        import base64
        try:
            data = base64.b64decode(mem.image_b64)
            return Response(data, mimetype='image/png')
        except Exception:
            pass
    return jsonify({'error': 'No image available'}), 404


@bp_reports.route('/api/articles/<aid>', methods=['GET'])
@jwt_required()
def get_article(aid):
    art = Article.query.get(aid)
    if not art:
        abort(404)
    current_user_id = get_jwt_identity()
    rep = art.report
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    return jsonify({
        'id': art.id,
        'title': art.title,
        'content_html': art.content_html,
        'content_md': art.content_md,
        'status': art.status,
        'error': art.error_message,
    }), 200


@bp_reports.route('/api/articles/<aid>', methods=['PUT'])
@jwt_required()
def update_article(aid):
    art = Article.query.get(aid)
    if not art:
        abort(404)
    current_user_id = get_jwt_identity()
    rep = art.report
    guest_id = _request_guest_id()
    if (not rep.user_id and not rep.guest_id) or (rep.user_id and rep.user_id != current_user_id) or  (not rep.user_id and rep.guest_id and rep.guest_id != guest_id):
        abort(403)
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get('title') or '').strip()
    content_md = data.get('content_md')
    if title:
        art.title = title
    if content_md is not None:
        # Normalize to string and compute HTML
        art.content_md = content_md
        try:
            art.content_html = md_to_html(content_md or '')
        except Exception:
            logger.exception('Failed to render markdown to HTML')
            art.content_html = None
    # Consider edited article as ready
    if art.status != 'ready':
        art.status = 'ready'
    db.session.add(art)
    db.session.commit()
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
    plan_id, limits = _get_user_plan_and_limits(uid)
    return jsonify({'plan_id': plan_id, 'limits': limits}), 200


# -------- Products and Feeds (reports) management --------

@bp_reports.route('/api/products', methods=['GET'])
def list_products():
    """List products for current user or guest, including latest feed summary.

    If both an authenticated user and a guest_id are present (client sends X-Guest-Id header or guest_id query param),
    first merge any guest-owned products and reports into the user so the response reflects
    a unified list after login.
    """
    current_user = _current_user_or_none()
    guest_id = _request_guest_id()
    # If user is logged in and a guest_id is provided, merge guest-owned items into the user
    if current_user and guest_id:
        uid = current_user.id
        # Move products
        guest_products = Product.query.filter_by(guest_id=guest_id).all()
        changed = False
        for p in guest_products:
            p.user_id = uid
            p.guest_id = None
            db.session.add(p)
            changed = True
        # Move reports
        guest_reports = Report.query.filter_by(guest_id=guest_id).all()
        for r in guest_reports:
            r.user_id = uid
            r.guest_id = None
            db.session.add(r)
            changed = True
        if changed:
            db.session.commit()

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
    if user_id:
        ok, reason = _enforce_quota(user_id, kind='content')
        if not ok:
            return jsonify({'error': reason, 'upgrade_required': True}), 402
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


# ---------- Helpers: subscription and quotas ----------

def _get_user_plan_and_limits(user_id: str):
    plans = get_plans()
    # default free
    default_plan = next((p for p in plans if p['id'] == 'free'), plans[0])
    sub = UserSubscription.query.filter_by(user_id=user_id).order_by(UserSubscription.current_period_end.desc()).first()
    plan_id = default_plan['id']
    limits = default_plan['limits']
    if sub:
        sub.update_status()
    if sub and sub.status in ('active', 'trialing', 'past_due') and sub.plan_id:
        p = next((pp for pp in plans if pp['id'] == sub.plan_id), None)
        if p:
            plan_id = p['id']
            limits = p['limits']
    return plan_id, limits


def _enforce_quota(user_id: str, kind: str):
    today = date.today()
    quota = UsageQuota.get_or_create(user_id, today)
    plan_id, limits = _get_user_plan_and_limits(user_id)
    if kind == 'content':
        allowed = limits.get('content_generations_per_day', 1)
        used = quota.content_gen_count or 0
        if allowed >= 0 and used >= allowed:
            return False, 'Daily content generation limit reached. Upgrade your plan.'
        quota.content_gen_count = used + 1
    elif kind == 'article':
        allowed = limits.get('articles_per_day', 1)
        used = quota.article_gen_count or 0
        if allowed >= 0 and used >= allowed:
            return False, 'Daily article generation limit reached. Upgrade your plan.'
        quota.article_gen_count = used + 1
    elif kind == 'video':
        allowed = limits.get('videos_per_day', 0)
        used = (getattr(quota, 'video_gen_count', 0) or 0)
        if allowed >= 0 and used >= allowed:
            return False, 'Daily video generation limit reached. Upgrade your plan.'
        quota.video_gen_count = used + 1
    else:
        return True, ''
    db.session.add(quota)
    db.session.commit()
    return True, ''


@bp_reports.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)  # type: ignore
        else:
            event = json.loads(payload)
    except Exception as e:
        logger.exception(e)
        return jsonify({'error': 'invalid payload'}), 400

    et = event.get('type') if isinstance(event, dict) else getattr(event, 'type', None)
    data = event.get('data', {}).get('object', {}) if isinstance(event, dict) else getattr(event, 'data', {}).get('object', {})

    def ensure_user_sub(customer_id: str, subscription_id: str | None, status: str | None, plan_id_hint: str | None = None):
        sub = UserSubscription.query.filter_by(stripe_customer_id=customer_id).first()
        if not sub:
            # fallback by subscription id
            if subscription_id:
                sub = UserSubscription.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not sub:
            return
        if subscription_id:
            sub.stripe_subscription_id = subscription_id
        
        sub.update_status()
        # map price -> plan id if provided
        if plan_id_hint:
            sub.plan_id = plan_id_hint
        db.session.add(sub)
        db.session.commit()

    if et in ('checkout.session.completed', 'customer.subscription.created', 'customer.subscription.updated'):
        # Extract fields
        customer_id = data.get('customer')
        sub_id = data.get('subscription') or data.get('id')
        status = data.get('status')
        plan_id_hint = None
        try:
            price_id = (data.get('plan') or {}).get('id') or (data.get('items', {}).get('data', [{}])[0].get('price', {}) or {}).get('id')
            if price_id:
                plans = get_plans()
                for p in plans:
                    if p.get('stripe_price_id') == price_id:
                        plan_id_hint = p['id']
                        break
        except Exception:
            pass
        if customer_id:
            ensure_user_sub(customer_id, sub_id, status, plan_id_hint)

    return jsonify({'received': True}), 200
