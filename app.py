from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///portal.db')
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
        return User.query.get(session['user_id'])
    return None


def get_current_admin():
    if 'admin_id' in session:
        admin = User.query.get(session['admin_id'])
        if admin and admin.is_admin:
            return admin
    return None


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
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        if not all([username, email, password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create user
        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', user=get_current_user())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session.permanent = True
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
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
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        admin = User.query.filter_by(username=username).first()
        
        if admin and admin.is_admin and admin.check_password(password):
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


# ==================== ROUTES: HOSPITAL REPORTS ====================

@app.route('/hospital/report/new', methods=['GET', 'POST'])
@login_required
def new_hospital_report():
    user = get_current_user()
    
    if request.method == 'POST':
        hospital_name = request.form.get('hospital_name', '').strip()
        district = request.form.get('district', '').strip()
        month_year = request.form.get('month_year', '').strip()
        
        if not all([hospital_name, district, month_year]):
            flash('Hospital name, district, and month/year are required', 'danger')
            return redirect(url_for('new_hospital_report'))
        
        report = HospitalReport(
            user_id=user.id,
            hospital_name=hospital_name,
            district=district,
            month_year=month_year,
            # Outpatients - New
            outpatients_new_male=request.form.get('outpatients_new_male', 0, type=int),
            outpatients_new_female=request.form.get('outpatients_new_female', 0, type=int),
            outpatients_new_male_child=request.form.get('outpatients_new_male_child', 0, type=int),
            outpatients_new_female_child=request.form.get('outpatients_new_female_child', 0, type=int),
            # Outpatients - Old
            outpatients_old_male=request.form.get('outpatients_old_male', 0, type=int),
            outpatients_old_female=request.form.get('outpatients_old_female', 0, type=int),
            outpatients_old_male_child=request.form.get('outpatients_old_male_child', 0, type=int),
            outpatients_old_female_child=request.form.get('outpatients_old_female_child', 0, type=int),
            # Outpatients - Emergency
            outpatients_emergency_male=request.form.get('outpatients_emergency_male', 0, type=int),
            outpatients_emergency_female=request.form.get('outpatients_emergency_female', 0, type=int),
            outpatients_emergency_male_child=request.form.get('outpatients_emergency_male_child', 0, type=int),
            outpatients_emergency_female_child=request.form.get('outpatients_emergency_female_child', 0, type=int),
            # Admissions
            admissions_male=request.form.get('admissions_male', 0, type=int),
            admissions_female=request.form.get('admissions_female', 0, type=int),
            admissions_male_child=request.form.get('admissions_male_child', 0, type=int),
            admissions_female_child=request.form.get('admissions_female_child', 0, type=int),
            admissions_emergency=request.form.get('admissions_emergency', 0, type=int),
            medical_legal_cases=request.form.get('medical_legal_cases', 0, type=int),
            same_day_admission_discharge=request.form.get('same_day_admission_discharge', 0, type=int),
            # Surgeries
            tubectomies=request.form.get('tubectomies', 0, type=int),
            vasectomies=request.form.get('vasectomies', 0, type=int),
            minor_surgeries=request.form.get('minor_surgeries', 0, type=int),
            major_surgeries=request.form.get('major_surgeries', 0, type=int),
            # Deaths & Deliveries
            deaths_total=request.form.get('deaths_total', 0, type=int),
            normal_deliveries=request.form.get('normal_deliveries', 0, type=int),
            caesarean_deliveries=request.form.get('caesarean_deliveries', 0, type=int),
            male_children_births=request.form.get('male_children_births', 0, type=int),
            female_children_births=request.form.get('female_children_births', 0, type=int),
            # Lab & Misc
            lab_tests=request.form.get('lab_tests', 0, type=int),
            cumulative_inpatient_days=request.form.get('cumulative_inpatient_days', 0, type=int),
            user_charges_collection=request.form.get('user_charges_collection', 0, type=float),
            rsby_cases=request.form.get('rsby_cases', 0, type=int)
        )
        db.session.add(report)
        db.session.commit()
        
        flash('Hospital report submitted successfully', 'success')
        return redirect(url_for('hospital_reports_list'))
    
    return render_template('hospital_report_form.html', user=user)


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
        flash('You do not have permission to view this report', 'danger')
        return redirect(url_for('hospital_reports_list'))
    
    return render_template('hospital_report_view.html', report=report, user=user)


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
    user = get_current_user()
    return render_template('500.html', user=user), 500


# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}


# ==================== INITIALIZATION ====================

def create_database():
    """Create all database tables"""
    with app.app_context():
        try:
            db.create_all()
            print("✓ Database tables created successfully")
            return True
        except Exception as e:
            print(f"✗ Database creation error: {e}")
            return False


# Initialize database immediately when module loads
print("🔄 Initializing database on app startup...")
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
