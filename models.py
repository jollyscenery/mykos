from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # Role mencakup user, agent, mover, dan admin
    role = db.Column(db.Enum('user', 'agent', 'mover', 'admin', name='role_types'), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi untuk melacak pesanan sebagai user atau agen
    orders_as_user = db.relationship('Order', foreign_keys='Order.user_id', backref='user_acc', lazy=True)
    orders_as_agent = db.relationship('Order', foreign_keys='Order.agent_id', backref='agent_acc', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    
    # Input awal dari User
    location_pref = db.Column(db.String(255), nullable=False)
    detailed_preferences = db.Column(db.Text, nullable=True) # Kamar mandi, AC, luas, dll.
    
    # Fitur Pembayaran
    status = db.Column(db.Enum('PENDING', 'WAITING_PAYMENT', 'ACCEPTED', 'SURVEYING', 'REPORT_READY', 'COMPLETED', 'CANCELLED', name='order_status'), default='PENDING')
    payment_method = db.Column(db.String(50), nullable=True) # BCA, Virtual Account, dll.
    
    # Fitur Tracking Lokasi Agen (Koordinat)
    agent_lat = db.Column(db.Float, nullable=True)
    agent_lng = db.Column(db.Float, nullable=True)

    # Laporan Final (Dapat diakses setelah pembayaran selesai)
    kost_name = db.Column(db.String(255), nullable=True)
    kost_address = db.Column(db.Text, nullable=True)
    kost_condition = db.Column(db.Text, nullable=True)
    kost_image = db.Column(db.String(255), nullable=True) # Nama file foto kos
    pros = db.Column(db.Text, nullable=True) # Keunggulan (berdasarkan preferensi/umum)
    cons = db.Column(db.Text, nullable=True) # Kekurangan
    report_notes = db.Column(db.Text, nullable=True) # Catatan tambahan agen
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi ke Moving Add-on (Mover)
    moving_addon = db.relationship('MovingAddOn', backref='parent_order', uselist=False, lazy=True)

class MovingAddOn(db.Model):
    __tablename__ = 'moving_addons'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    mover_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True) 
    
    moving_date = db.Column(db.Date, nullable=False)
    items_desc = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('PENDING', 'IN_PROGRESS', 'DELIVERED', name='moving_status'), default='PENDING')