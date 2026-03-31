from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False) # Nama Asli
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False) # Nomor Telepon
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # Role ditambahkan 'admin'
    role = db.Column(db.Enum('user', 'agent', 'mover', 'admin', name='role_types'), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi
    # backref diubah sedikit agar lebih deskriptif (user_acc & agent_acc)
    orders_as_user = db.relationship('Order', foreign_keys='Order.user_id', backref='user_acc', lazy=True)
    orders_as_agent = db.relationship('Order', foreign_keys='Order.agent_id', backref='agent_acc', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    # agent_id dibuat nullable=True karena saat PENDING belum ada agen yang mengambil
    agent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    
    location_pref = db.Column(db.String(255), nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    # Status ditambahkan 'ACCEPTED' dan 'CANCELLED' sesuai alur baru
    status = db.Column(db.Enum('PENDING', 'ACCEPTED', 'SURVEYING', 'REPORT_READY', 'COMPLETED', 'CANCELLED', name='order_status'), default='PENDING')
    report_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi ke Moving Add-on
    moving_addon = db.relationship('MovingAddOn', backref='parent_order', uselist=False, lazy=True)

class MovingAddOn(db.Model):
    __tablename__ = 'moving_addons'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    mover_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True) 
    
    moving_date = db.Column(db.Date, nullable=False)
    items_desc = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('PENDING', 'IN_PROGRESS', 'DELIVERED', name='moving_status'), default='PENDING')