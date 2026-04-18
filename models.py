from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  nullable=False, default='head')  # admin | head
    club          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), default='')
    phone         = db.Column(db.String(20),  default='')
    bio           = db.Column(db.Text,        default='No bio added yet.')
    position      = db.Column(db.String(80),  default='Member')
    linkedin      = db.Column(db.String(200), default='')
    profile_pic   = db.Column(db.String(300), default='https://cdn-icons-png.flaticon.com/512/3135/3135715.png')

    # Relationships
    events    = db.relationship('Event',    backref='creator', lazy=True, foreign_keys='Event.added_by_id')
    messages  = db.relationship('Message', backref='author',  lazy=True)
    audit_logs = db.relationship('AuditLog', backref='actor', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def pic(self):
        return self.profile_pic


class Club(db.Model):
    __tablename__ = 'clubs'
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    events = db.relationship('Event', backref='club_rel', lazy=True, foreign_keys='Event.club')


class Event(db.Model):
    __tablename__ = 'events'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    type           = db.Column(db.String(20),  nullable=False)   # Income | Expense
    amount         = db.Column(db.Float,       nullable=False)
    tickets_sold   = db.Column(db.Integer,     default=0)
    participation  = db.Column(db.Integer,     default=0)
    club           = db.Column(db.String(100), db.ForeignKey('clubs.name'), nullable=False)
    added_by_id    = db.Column(db.Integer,     db.ForeignKey('users.id'),   nullable=True)
    date           = db.Column(db.Date,        default=datetime.utcnow)
    payment_method = db.Column(db.String(20),  default='Cash')
    ticket_id      = db.Column(db.String(50),  unique=True)

    ticket_sales   = db.relationship('TicketSale', backref='event', lazy=True)


class TicketSale(db.Model):
    __tablename__ = 'ticket_sales'
    id             = db.Column(db.Integer, primary_key=True)
    event_id       = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    event_name     = db.Column(db.String(200))
    buyer_name     = db.Column(db.String(100), nullable=False)
    payment_method = db.Column(db.String(20),  nullable=False)
    amount         = db.Column(db.Float,       nullable=False)
    ticket_code    = db.Column(db.String(50),  unique=True, nullable=False)
    status         = db.Column(db.String(30),  default='Active')  # Active | Refund Requested | Refunded
    club           = db.Column(db.String(100), db.ForeignKey('clubs.name'), nullable=False)
    purchase_date  = db.Column(db.DateTime,    default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    id        = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender    = db.Column(db.String(80))   # cached username for easy display
    role      = db.Column(db.String(20))
    text      = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(300), nullable=False)
    category   = db.Column(db.String(30),  default='info')   # info | success | refund | alert
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
