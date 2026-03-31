import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Account, Order, MovingAddOn
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'mykost_secret_key_123')

# Konfigurasi Database MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:@localhost/mykost_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Inisialisasi Tabel
with app.app_context():
    db.create_all()

# --- HELPER: Ambil data user dari session ---
def get_logged_in_user():
    if 'user_id' in session:
        return Account.query.get(session['user_id'])
    return None

# --- CONTEXT PROCESSOR: Membuat current_user tersedia di semua file HTML ---
@app.context_processor
def inject_user():
    return dict(current_user=get_logged_in_user())

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'user')
        terms = request.form.get('terms')

        if password != confirm_password:
            flash("Password tidak cocok!", "danger")
            return redirect(url_for('register'))
        
        if not terms:
            flash("Anda harus menyetujui ketentuan layanan.", "warning")
            return redirect(url_for('register'))

        user_exists = Account.query.filter((Account.username == username) | (Account.email == email)).first()
        if user_exists:
            flash("Username atau Email sudah terdaftar.", "danger")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = Account(
            full_name=full_name,
            email=email,
            phone=phone,
            username=username,
            password=hashed_pw,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registrasi Berhasil! Silakan Login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Account.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'agent':
                return redirect(url_for('agent_dashboard'))
            elif user.role == 'mover':
                return redirect(url_for('mover_jobs'))
            return redirect(url_for('user_home'))
        
        flash("Username atau Password salah.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for('login'))

# ==========================================
# CORE ROUTES
# ==========================================

@app.route('/')
def index():
    user = get_logged_in_user()
    if not user:
        return render_template('preferences.html') # Landing page
    
    if user.role == 'admin': return redirect(url_for('admin_dashboard'))
    if user.role == 'agent': return redirect(url_for('agent_dashboard'))
    if user.role == 'mover': return redirect(url_for('mover_jobs'))
    return redirect(url_for('user_home'))

@app.route('/user/home', methods=['GET', 'POST'])
def user_home():
    user = get_logged_in_user()
    if not user or user.role != 'user': return redirect(url_for('login'))
    agents = Account.query.filter_by(role='agent').all()
    return render_template('preferences.html', agents=agents)

@app.route('/agent/dashboard')
def agent_dashboard():
    user = get_logged_in_user()
    if not user or user.role != 'agent': return redirect(url_for('login'))
    active_order = Order.query.filter_by(agent_id=user.id).filter(Order.status != 'COMPLETED', Order.status != 'CANCELLED').first()
    available_orders = Order.query.filter_by(status='PENDING').all()
    return render_template('dashboard.html', active_order=active_order, available_orders=available_orders)

@app.route('/admin/dashboard')
def admin_dashboard():
    user = get_logged_in_user()
    if not user or user.role != 'admin': return redirect(url_for('login'))
    return render_template('admin_dashboard.html', orders=Order.query.all(), users=Account.query.all())

if __name__ == '__main__':
    is_dev = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=is_dev)