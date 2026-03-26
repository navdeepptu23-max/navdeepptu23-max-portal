from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Database configuration - handle Render ephemeral storage
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Using external database (PostgreSQL, etc)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Use SQLite with persistent path
    import tempfile
    # On Render, use /tmp but it persists during service lifetime
    # For local development, use portal.db
    db_path = os.path.join(os.path.dirname(__file__), 'portal.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    bio = db.Column(db.Text, default='')
    avatar_url = db.Column(db.String(255), default='https://ui-avatars.com/api/?name=User')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_avatar(self):
        if self.full_name:
            return f"https://ui-avatars.com/api/?name={self.full_name}&background=random"
        return f"https://ui-avatars.com/api/?name={self.username}&background=random"
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'bio': self.bio,
            'created_at': self.created_at.isoformat(),
            'post_count': len(self.posts)
        }


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author.username,
            'created_at': self.created_at.isoformat(),
            'likes': self.likes,
            'views': self.views
        }


class HospitalReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hospital_name = db.Column(db.String(255), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)
    
    # Outpatients
    outpatients_new_male = db.Column(db.Integer, default=0)
    outpatients_new_female = db.Column(db.Integer, default=0)
    outpatients_new_male_child = db.Column(db.Integer, default=0)
    outpatients_new_female_child = db.Column(db.Integer, default=0)
    
    outpatients_old_male = db.Column(db.Integer, default=0)
    outpatients_old_female = db.Column(db.Integer, default=0)
    outpatients_old_male_child = db.Column(db.Integer, default=0)
    outpatients_old_female_child = db.Column(db.Integer, default=0)
    
    outpatients_emergency_male = db.Column(db.Integer, default=0)
    outpatients_emergency_female = db.Column(db.Integer, default=0)
    outpatients_emergency_male_child = db.Column(db.Integer, default=0)
    outpatients_emergency_female_child = db.Column(db.Integer, default=0)
    
    # Admissions
    admissions_male = db.Column(db.Integer, default=0)
    admissions_female = db.Column(db.Integer, default=0)
    admissions_male_child = db.Column(db.Integer, default=0)
    admissions_female_child = db.Column(db.Integer, default=0)
    
    admissions_emergency = db.Column(db.Integer, default=0)
    medical_legal_cases = db.Column(db.Integer, default=0)
    same_day_admission_discharge = db.Column(db.Integer, default=0)
    
    # Surgeries
    tubectomies = db.Column(db.Integer, default=0)
    vasectomies = db.Column(db.Integer, default=0)
    minor_surgeries = db.Column(db.Integer, default=0)
    major_surgeries = db.Column(db.Integer, default=0)
    
    # Deaths & Deliveries
    deaths_total = db.Column(db.Integer, default=0)
    normal_deliveries = db.Column(db.Integer, default=0)
    caesarean_deliveries = db.Column(db.Integer, default=0)
    male_children_births = db.Column(db.Integer, default=0)
    female_children_births = db.Column(db.Integer, default=0)
    
    # Lab & Misc
    lab_tests = db.Column(db.Integer, default=0)
    cumulative_inpatient_days = db.Column(db.Integer, default=0)
    user_charges_collection = db.Column(db.Float, default=0)
    rsby_cases = db.Column(db.Integer, default=0)
    remarks = db.Column(db.Text, default='')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hospital_name': self.hospital_name,
            'district': self.district,
            'month_year': self.month_year,
            'created_at': self.created_at.isoformat()
        }


# ==================== DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin login required', 'danger')
            return redirect(url_for('admin_login'))
        admin = User.query.get(session['admin_id'])
        if not admin or not admin.is_admin:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' in session:
        try:
            return User.query.get(session['user_id'])
        except Exception as e:
            print(f"[USER LOOKUP ERROR] {e}")
            return None
    return None


def get_current_admin():
    if 'admin_id' in session:
        try:
            admin = User.query.get(session['admin_id'])
            if admin and admin.is_admin:
                return admin
        except Exception as e:
            print(f"[ADMIN LOOKUP ERROR] {e}")
            return None
    return None


def find_user_by_credential(credential):
    """Find user by username, email, or numeric user ID."""
    credential = (credential or '').strip()
    if not credential:
        return None

    user = User.query.filter(func.lower(User.username) == credential.lower()).first()
    if not user and '@' in credential:
        user = User.query.filter(func.lower(User.email) == credential.lower()).first()
    if not user and credential.isdigit():
        user = User.query.get(int(credential))
    return user


# ==================== ROUTES: PUBLIC ====================

@app.route('/')
def index():
    user = get_current_user()
    try:
        posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        stats = {
            'total_users': User.query.count(),
            'total_posts': Post.query.count(),
            'total_likes': sum(p.likes for p in Post.query.all())
        }
    except Exception as e:
        print(f"Database query error: {e}")
        posts = []
        stats = {'total_users': 0, 'total_posts': 0, 'total_likes': 0}
    
    return render_template('index.html', user=user, posts=posts, stats=stats)


@app.route('/about')
def about():
    user = get_current_user()
    return render_template('about.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        if not all([username, email, password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter(func.lower(User.email) == email.lower()).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        try:
            # Create user
            user = User(username=username, email=email, full_name=full_name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            print(f"[REGISTER] [OK] User created: {username}")
            print(f"[REGISTER] Total users now: {User.query.count()}")
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"[REGISTER ERROR] {str(e)}")
            db.session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html', user=get_current_user())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        credential = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        print(f"[LOGIN] Attempting login for credential: {credential}")
        
        try:
            user = find_user_by_credential(credential)
            
            if user:
                print(f"[LOGIN] User found: {user.username}")
                if not user.is_active:
                    flash('Your account is inactive. Contact admin.', 'danger')
                    return redirect(url_for('login'))
                if user.check_password(password):
                    print(f"[LOGIN] Password correct for {user.username}")
                    session['user_id'] = user.id
                    session.permanent = True
                    flash(f'Welcome back, {user.username}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    print(f"[LOGIN] Password INCORRECT for {user.username}")
            else:
                print(f"[LOGIN] User NOT found for credential: {credential}")
                try:
                    print(f"[LOGIN] Total users in database: {User.query.count()}")
                except Exception as count_err:
                    print(f"[LOGIN] Could not count users: {count_err}")
            
            flash('Invalid username/email/user ID or password', 'danger')
        except Exception as e:
            print(f"[LOGIN ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Login error. Please try again.', 'danger')
    
    return render_template('login.html', user=get_current_user())


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# ==================== ROUTES: ADMIN ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        credential = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        admin = find_user_by_credential(credential)
        
        if admin and admin.is_admin and admin.is_active and admin.check_password(password):
            session['admin_id'] = admin.id
            session.permanent = True
            flash(f'Welcome Admin, {admin.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
    
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    admin = get_current_admin()
    total_users = User.query.count()
    total_reports = HospitalReport.query.count()
    total_posts = Post.query.count()
    recent_reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).limit(10).all()
    
    stats = {
        'total_users': total_users,
        'total_reports': total_reports,
        'total_posts': total_posts
    }
    
    return render_template('admin_dashboard.html', admin=admin, stats=stats, reports=recent_reports)


@app.route('/admin/users')
@admin_required
def admin_users():
    admin = get_current_admin()
    users = User.query.all()
    return render_template('admin_users.html', admin=admin, users=users)


@app.route('/admin/reports')
@admin_required
def admin_reports():
    admin = get_current_admin()
    reports = HospitalReport.query.order_by(HospitalReport.created_at.desc()).all()
    return render_template('admin_reports.html', admin=admin, reports=reports)


@app.route('/admin/report/<int:report_id>')
@admin_required
def admin_view_report(report_id):
    admin = get_current_admin()
    report = HospitalReport.query.get_or_404(report_id)
    return render_template('admin_report_view.html', admin=admin, report=report)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Admin logged out', 'info')
    return redirect(url_for('admin_login'))


# ==================== ROUTES: USER DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    user_posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    stats = {
        'post_count': len(user_posts),
        'total_views': sum(p.views for p in user_posts),
        'total_likes': sum(p.likes for p in user_posts)
    }
    return render_template('dashboard.html', user=user, posts=user_posts, stats=stats)


@app.route('/profile/<username>')
def profile(username):
    profile_user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=profile_user.id).order_by(Post.created_at.desc()).all()
    current_user = get_current_user()
    stats = {
        'post_count': len(posts),
        'total_views': sum(p.views for p in posts),
        'total_likes': sum(p.likes for p in posts)
    }
    return render_template('profile.html', profile_user=profile_user, posts=posts, current_user=current_user, stats=stats)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = get_current_user()
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '').strip()
        user.bio = request.form.get('bio', '').strip()
        user.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', user=user)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = get_current_user()
    
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not user.check_password(old_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('change_password'))
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('change_password'))
        
        user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', user=user)


# ==================== ROUTES: POSTS ====================

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    user = get_current_user()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title or not content:
            flash('Title and content are required', 'danger')
            return redirect(url_for('new_post'))
        
        post = Post(title=title, content=content, user_id=user.id)
        db.session.add(post)
        db.session.commit()
        
        flash('Post created successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('new_post.html', user=user)


@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    current_user = get_current_user()
    return render_template('view_post.html', post=post, current_user=current_user)


@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = get_current_user()
    
    if post.user_id != user.id:
        flash('You can only edit your own posts', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        post.title = request.form.get('title', '').strip()
        post.content = request.form.get('content', '').strip()
        post.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Post updated successfully', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    
    return render_template('edit_post.html', post=post, user=user)


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = get_current_user()
    
    if post.user_id != user.id:
        flash('You can only delete your own posts', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post deleted successfully', 'success')
    return redirect(url_for('dashboard'))


@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({'likes': post.likes, 'success': True})


# ==================== HELPERS: HOSPITAL META ====================

def parse_hospital_meta(report):
    """Parse JSON metadata stored in the remarks column."""
    default = {"sanctioned_beds": "", "functional_beds": "", "doctors_incharge": "", "remarks": ""}
    raw = report.remarks or ""
    if not raw:
        return default
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        default["remarks"] = raw
        return default
    if not isinstance(payload, dict) or payload.get("_format") != "hospital_meta_v1":
        default["remarks"] = raw
        return default
    return {
        "sanctioned_beds": (payload.get("sanctioned_beds") or "").strip(),
        "functional_beds": (payload.get("functional_beds") or "").strip(),
        "doctors_incharge": (payload.get("doctors_incharge") or "").strip(),
        "remarks": (payload.get("remarks") or "").strip(),
    }


# ==================== ROUTES: HOSPITAL REPORTS ====================

def _apply_hospital_form(report, form):
    """Apply form values to a HospitalReport instance and store JSON metadata."""
    report.hospital_name = form.get('hospital_name', '').strip()
    report.district = form.get('district', '').strip()
    report.month_year = form.get('month_year', '').strip()
    # Outpatients
    for f in ['outpatients_new_male','outpatients_new_female','outpatients_new_male_child','outpatients_new_female_child',
              'outpatients_old_male','outpatients_old_female','outpatients_old_male_child','outpatients_old_female_child',
              'outpatients_emergency_male','outpatients_emergency_female','outpatients_emergency_male_child','outpatients_emergency_female_child',
              'admissions_male','admissions_female','admissions_male_child','admissions_female_child',
              'admissions_emergency','medical_legal_cases','same_day_admission_discharge',
              'tubectomies','vasectomies','minor_surgeries','major_surgeries',
              'deaths_total','normal_deliveries','caesarean_deliveries','male_children_births','female_children_births',
              'lab_tests','cumulative_inpatient_days','rsby_cases']:
        setattr(report, f, form.get(f, 0, type=int))
    report.user_charges_collection = form.get('user_charges_collection', 0, type=float)
    report.remarks = json.dumps({
        "_format": "hospital_meta_v1",
        "sanctioned_beds": form.get('sanctioned_beds', '').strip(),
        "functional_beds": form.get('functional_beds', '').strip(),
        "doctors_incharge": form.get('doctors_incharge', '').strip(),
        "remarks": form.get('remarks_text', '').strip(),
    })


@app.route('/hospital/report/new', methods=['GET', 'POST'])
@login_required
def new_hospital_report():
    user = get_current_user()

    if request.method == 'POST':
        if not all([request.form.get('hospital_name','').strip(),
                    request.form.get('district','').strip(),
                    request.form.get('month_year','').strip()]):
            flash('Hospital name, district, and month/year are required.', 'danger')
            return redirect(url_for('new_hospital_report'))

        report = HospitalReport(user_id=user.id)
        _apply_hospital_form(report, request.form)
        db.session.add(report)
        db.session.commit()
        flash('Hospital report submitted successfully.', 'success')
        return redirect(url_for('hospital_reports_list'))

    return render_template('hospital_report_form.html', user=user, report=None, hospital_meta={}, form_action=url_for('new_hospital_report'))


@app.route('/hospital/reports')
@login_required
def hospital_reports_list():
    user = get_current_user()
    reports = HospitalReport.query.filter_by(user_id=user.id).order_by(HospitalReport.created_at.desc()).all()
    return render_template('hospital_reports_list.html', user=user, reports=reports)


@app.route('/hospital/report/<int:report_id>')
@login_required
def view_hospital_report(report_id):
    report = HospitalReport.query.get_or_404(report_id)
    user = get_current_user()
    if report.user_id != user.id:
        flash('You do not have permission to view this report.', 'danger')
        return redirect(url_for('hospital_reports_list'))
    return render_template('hospital_report_view.html', report=report, user=user, hospital_meta=parse_hospital_meta(report))


@app.route('/hospital/report/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_hospital_report(report_id):
    report = HospitalReport.query.get_or_404(report_id)
    user = get_current_user()
    if report.user_id != user.id:
        flash('You do not have permission to edit this report.', 'danger')
        return redirect(url_for('hospital_reports_list'))

    if request.method == 'POST':
        if not all([request.form.get('hospital_name','').strip(),
                    request.form.get('district','').strip(),
                    request.form.get('month_year','').strip()]):
            flash('Hospital name, district, and month/year are required.', 'danger')
            return redirect(url_for('edit_hospital_report', report_id=report_id))
        _apply_hospital_form(report, request.form)
        db.session.commit()
        flash('Report updated successfully.', 'success')
        return redirect(url_for('view_hospital_report', report_id=report.id))

    return render_template('hospital_report_form.html', user=user, report=report,
                           hospital_meta=parse_hospital_meta(report),
                           form_action=url_for('edit_hospital_report', report_id=report.id))


@app.route('/hospital/report/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_hospital_report(report_id):
    report = HospitalReport.query.get_or_404(report_id)
    user = get_current_user()
    if report.user_id != user.id:
        flash('You do not have permission to delete this report.', 'danger')
        return redirect(url_for('hospital_reports_list'))
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted.', 'info')
    return redirect(url_for('hospital_reports_list'))


# ==================== ROUTES: API ====================

@app.route('/api/users')
def api_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@app.route('/api/posts')
def api_posts():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=20)
    return jsonify({
        'posts': [p.to_dict() for p in posts.items],
        'total': posts.total,
        'pages': posts.pages,
        'current_page': page
    })


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    user = get_current_user()
    return render_template('404.html', user=user), 404


@app.errorhandler(500)
def server_error(error):
    try:
        user = get_current_user()
        return render_template('500.html', user=user), 500
    except Exception:
        return "500 Server Error: Something went wrong on our end.", 500


# ==================== ROUTES: FORGOT PASSWORD ====================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        credential = request.form.get('credential', '').strip()
        if not credential:
            flash('Please enter your username or email.', 'warning')
            return redirect(url_for('forgot_password'))

        user = find_user_by_credential(credential)
        if user:
            # In a production system you would send a reset email here.
            # For now, display account info so the user can contact admin.
            flash(
                f'Account found: <strong>{user.username}</strong> '
                f'(ID: {user.id}). Please contact your administrator to reset your password.',
                'info'
            )
        else:
            flash('No account found with that username or email.', 'danger')
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html', user=get_current_user())


# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_user():
    try:
        return {'current_user': get_current_user()}
    except Exception:
        return {'current_user': None}


# ==================== INITIALIZATION ====================

def create_database():
    """Create all database tables"""
    with app.app_context():
        try:
            db.create_all()
            print("[OK] Database tables created successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Database creation error: {e}")
            return False


# Initialize database immediately when module loads
print("[INIT] Initializing database on app startup...")
create_database()


# Fallback: Also initialize on first request
_db_ready = False

@app.before_request
def ensure_db_ready():
    global _db_ready
    if not _db_ready:
        try:
            db.create_all()
            _db_ready = True
        except Exception as e:
            print(f"First request DB init: {e}")


if __name__ == '__main__':
    app.run(debug=False)
