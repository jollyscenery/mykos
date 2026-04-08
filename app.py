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

# Konfigurasi Database (Gunakan SQLite untuk pengembangan sesuai file .env)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///mykost.db')
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
# USER ROUTES (ALUR PENCARIAN KOS)
# ==========================================

@app.route('/')
def index():
    user = get_logged_in_user()
    if not user:
        return render_template('preferences.html')
    
    if user.role == 'admin': return redirect(url_for('admin_dashboard'))
    if user.role == 'agent': return redirect(url_for('agent_dashboard'))
    if user.role == 'mover': return redirect(url_for('mover_jobs'))
    return redirect(url_for('user_home'))

@app.route('/user/home', methods=['GET', 'POST'])
def user_home():
    user = get_logged_in_user()
    if not user or user.role != 'user': return redirect(url_for('login'))
    return render_template('preferences.html')

@app.route('/user/preferences_detail', methods=['POST'])
def preferences_detail():
    user = get_logged_in_user()
    if not user: return redirect(url_for('login'))
    
    # Simpan lokasi ke session untuk tahap berikutnya
    session['temp_location'] = request.form.get('location')
    return render_template('preferences_detail.html')

@app.route('/user/select_agent', methods=['POST'])
def select_agent():
    user = get_logged_in_user()
    if not user: return redirect(url_for('login'))
    
    # Simpan preferensi detail (AC, luas kamar, dll) ke session
    session['temp_details'] = request.form.get('detailed_prefs')
    agents = Account.query.filter_by(role='agent').all()
    return render_template('select_agent.html', agents=agents)

@app.route('/user/create_order', methods=['POST'])
def create_order():
    user = get_logged_in_user()
    if not user: return redirect(url_for('login'))
    
    agent_id = request.form.get('agent_id')
    
    # Membuat order baru dengan status menunggu pembayaran
    new_order = Order(
        user_id=user.id,
        agent_id=agent_id,
        location_pref=session.get('temp_location', 'Tidak diketahui'),
        detailed_preferences=session.get('temp_details', ''),
        status='WAITING_PAYMENT'
    )
    db.session.add(new_order)
    db.session.commit()
    
    # Bersihkan session temporary
    session.pop('temp_location', None)
    session.pop('temp_details', None)
    
    return redirect(url_for('payment', order_id=new_order.id))

@app.route('/user/order/<int:order_id>/payment', methods=['GET', 'POST'])
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        # Simpan metode pembayaran (BCA atau Virtual Account)
        order.payment_method = request.form.get('payment_method')
        order.status = 'ACCEPTED' 
        db.session.commit()
        flash(f"Pembayaran via {order.payment_method} Berhasil! Agen segera bekerja.", "success")
        return redirect(url_for('tracking_hub', order_id=order.id))
        
    return render_template('payment.html', order=order)

@app.route('/user/order/<int:order_id>/tracking')
def tracking_hub(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('tracking_hub.html', order=order)

@app.route('/user/order/<int:order_id>/report')
def final_report(order_id):
    order = Order.query.get_or_404(order_id)
    # Laporan hanya bisa dilihat jika status sudah REPORT_READY atau COMPLETED
    if order.status not in ['REPORT_READY', 'COMPLETED']:
        flash("Laporan belum tersedia. Tunggu agen menyelesaikan survei.", "warning")
        return redirect(url_for('tracking_hub', order_id=order.id))
    return render_template('final_report.html', order=order)

# Jasa Pindahan (Mover Add-on)
@app.route('/user/order/<int:order_id>/add-moving', methods=['POST'])
def add_moving(order_id):
    user = get_logged_in_user()
    if not user: return redirect(url_for('login'))
    
    moving_date_str = request.form.get('moving_date')
    moving_date = datetime.strptime(moving_date_str, '%Y-%m-%d').date()
    
    new_moving = MovingAddOn(
        order_id=order_id,
        moving_date=moving_date,
        items_desc=request.form.get('items_desc')
    )
    db.session.add(new_moving)
    db.session.commit()
    flash("Jasa Mover berhasil dipesan!", "success")
    return redirect(url_for('tracking_hub', order_id=order_id))

# ==========================================
# AGENT ROUTES
# ==========================================

@app.route('/agent/dashboard')
def agent_dashboard():
    user = get_logged_in_user()
    if not user or user.role != 'agent': return redirect(url_for('login'))
    
    # Pesanan yang sudah dibayar dan perlu disurvei
    active_orders = Order.query.filter_by(agent_id=user.id).filter(Order.status == 'ACCEPTED').all()
    # Pesanan yang sedang dalam proses survei
    surveying_orders = Order.query.filter_by(agent_id=user.id).filter(Order.status == 'SURVEYING').all()
    
    return render_template('dashboard.html', active_orders=active_orders, surveying_orders=surveying_orders)

@app.route('/agent/order/<int:order_id>/submit_report', methods=['POST'])
def submit_report(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Agen mengisi detail laporan kos
    order.kost_name = request.form.get('kost_name')
    order.kost_address = request.form.get('kost_address')
    order.kost_condition = request.form.get('kost_condition')
    order.pros = request.form.get('pros') # Keunggulan
    order.cons = request.form.get('cons') # Kekurangan
    order.status = 'REPORT_READY'
    
    db.session.commit()
    flash("Laporan survei berhasil dikirim ke pengguna.", "success")
    return redirect(url_for('agent_dashboard'))

# ==========================================
# ADMIN & MOVER ROUTES
# ==========================================

@app.route('/admin/dashboard')
def admin_dashboard():
    user = get_logged_in_user()
    if not user or user.role != 'admin': return redirect(url_for('login'))
    return render_template('admin_dashboard.html', orders=Order.query.all(), users=Account.query.all())

@app.route('/mover/jobs')
def mover_jobs():
    user = get_logged_in_user()
    if not user or user.role != 'mover': return redirect(url_for('login'))
    jobs = MovingAddOn.query.filter_by(status='PENDING').all()
    return render_template('jobs.html', moving_jobs=jobs)

if __name__ == '__main__':
    is_dev = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=is_dev)