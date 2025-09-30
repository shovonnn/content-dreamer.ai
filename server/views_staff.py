from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from models.admin_staff import AdminStaff
from models.user import User
from models.db_utils import db
from uuid import uuid4
from functools import wraps
import os
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp'}
DOCTOR_UPLOAD_DIR = os.path.join('static', 'uploads', 'doctors')

def _ensure_dir(path: str):  # small local helper
    os.makedirs(path, exist_ok=True)

def _save_doctor_photo(fs):
    if not fs or not getattr(fs, 'filename', None):
        return None
    filename = secure_filename(fs.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValueError('Unsupported image type')
    _ensure_dir(DOCTOR_UPLOAD_DIR)
    new_name = f"{uuid4().hex}{ext}"
    dest_path = os.path.join(DOCTOR_UPLOAD_DIR, new_name)
    fs.save(dest_path)
    # return path relative to static for existing CDN usage pattern
    return os.path.relpath(dest_path, 'static')

staff_views = Blueprint('staff_views', __name__, url_prefix='/staff')

# default list page size for staff listings
LIST_PAGE_SIZE = 20


def staff_required(level: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            staff_id = session.get('staff_id')
            if not staff_id:
                return redirect(url_for('staff_views.login', next=request.path))
            staff = AdminStaff.query.filter_by(id=staff_id, active=True).first()
            if not staff:
                session.pop('staff_id', None)
                return redirect(url_for('staff_views.login', next=request.path))
            # access level ordering
            if level:
                allowed_order = ['viewer', 'editor', 'admin', 'superadmin']
                if allowed_order.index(staff.access_level) < allowed_order.index(level):
                    abort(403)
            return fn(*args, staff=staff, **kwargs)
        return wrapper
    return decorator


@staff_views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').lower().strip()
        password = request.form.get('password','')
        staff = AdminStaff.query.filter_by(email=email, active=True).first()
        if staff and staff.check_password(password):
            session['staff_id'] = staff.id
            return redirect(request.args.get('next') or url_for('staff_views.dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('staff/login.html')


@staff_views.route('/logout')
def logout():
    session.pop('staff_id', None)
    return redirect(url_for('staff_views.login'))


@staff_views.route('/')
@staff_required('viewer')
def dashboard(staff: AdminStaff):
    # Keep the dashboard as a light landing page linking to the dedicated lists
    return render_template('staff/dashboard.html', staff=staff)

