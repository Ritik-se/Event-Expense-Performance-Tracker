import time
import os
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, abort, Response
from flask_login import login_required, current_user
from models import db, Event, TicketSale, Message, AuditLog, User, Club
from decorators import admin_required
from sqlalchemy import func
import datetime

dashboard_bp = Blueprint('dashboard', __name__)

def _get_view_club():
    """Returns the club filter for the current request."""
    if current_user.role == 'admin':
        return request.args.get('club_filter', 'All')
    return current_user.club

def _query_param(view_club):
    if view_club and view_club != 'All' and current_user.role == 'admin':
        return f'?club_filter={view_club}'
    return ''

def _log(action, category='info'):
    entry = AuditLog(user_id=current_user.id, action=action, category=category)
    db.session.add(entry)
    db.session.commit()

def _ai_forecast(view_club):
    """Numpy linear regression on last-12-months income."""
    import numpy as np
    q = db.session.query(Event.amount).filter(Event.type == 'Income')
    if view_club != 'All':
        q = q.filter(Event.club == view_club)
    values = [r[0] for r in q.order_by(Event.date.desc()).limit(12).all()]
    if len(values) < 2:
        return int(sum(values) / len(values) * 1.1) if values else 0
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values[::-1], 1)
    forecast = coeffs[0] * len(values) + coeffs[1]
    return max(0, int(forecast))


@dashboard_bp.route('/')
def root():
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def index():
    view_club = _get_view_club()
    qp = _query_param(view_club)

    # ── POST: Launch Event (admin only) ──────────────────────────────────
    if request.method == 'POST' and 'launch_event' in request.form:
        if current_user.role != 'admin':
            abort(403)
        target_club = request.form['target_club']
        t_id = f"EVT-{int(time.time())}"
        ev = Event(
            name=request.form['name'],
            type=request.form['type'],
            amount=float(request.form['amount']),
            tickets_sold=int(request.form.get('tickets', 0)),
            participation=int(request.form.get('students', 0)),
            club=target_club,
            added_by_id=current_user.id,
            ticket_id=t_id,
        )
        db.session.add(ev)
        db.session.flush()
        _log(f"Launched new event '{ev.name}' for {target_club}", 'success')
        return redirect(url_for('dashboard.index') + qp)

    # ── POST: Buy Ticket ─────────────────────────────────────────────────
    if request.method == 'POST' and 'buy_ticket' in request.form:
        ev_id  = int(request.form['event_id'])
        ev     = Event.query.get_or_404(ev_id)
        t_code = f"TKT-{int(time.time())}-{ev_id}"
        qr_dir = os.path.join('static', 'qrcodes')
        os.makedirs(qr_dir, exist_ok=True)
        qr_file = f"{t_code}.png"
        verify_url = request.host_url.rstrip('/') + url_for('dashboard.verify_ticket', ticket_code=t_code)
        qrcode.make(verify_url).save(os.path.join(qr_dir, qr_file))

        ts = TicketSale(
            event_id=ev.id,
            event_name=ev.name,
            buyer_name=request.form['buyer_name'],
            payment_method=request.form['payment_method'],
            amount=ev.amount,
            ticket_code=t_code,
            status='Active',
            club=ev.club,
        )
        db.session.add(ts)
        ev.tickets_sold = (ev.tickets_sold or 0) + 1
        _log(f"Ticket sold for '{ev.name}' → {request.form['buyer_name']}", 'success')
        return redirect(url_for('dashboard.index') + qp)

    # ── Data queries ─────────────────────────────────────────────────────
    ev_q = Event.query
    ts_q = TicketSale.query
    if view_club != 'All':
        ev_q = ev_q.filter(Event.club == view_club)
        ts_q = ts_q.filter(TicketSale.club == view_club)

    events   = ev_q.order_by(Event.date.desc()).limit(20).all()
    income   = db.session.query(func.sum(Event.amount)).filter(Event.type == 'Income',
               *([Event.club == view_club] if view_club != 'All' else [])).scalar() or 0
    expense  = db.session.query(func.sum(Event.amount)).filter(Event.type == 'Expense',
               *([Event.club == view_club] if view_club != 'All' else [])).scalar() or 0

    tickets         = ts_q.order_by(TicketSale.purchase_date.desc()).limit(10).all()
    refund_requests = ts_q.filter(TicketSale.status == 'Refund Requested').all()
    active_events   = ev_q.filter(Event.type == 'Income').order_by(Event.date.desc()).limit(10).all()

    total_tix  = sum(e.tickets_sold or 0 for e in events)
    total_part = sum(e.participation or 0 for e in events)
    success_rate = round(total_part / total_tix * 100, 1) if total_tix > 0 else 0

    messages   = Message.query.order_by(Message.timestamp.desc()).limit(5).all()
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    all_clubs  = [c.name for c in Club.query.all()]

    # Payment distribution for doughnut
    pay_counts = db.session.query(TicketSale.payment_method, func.count()).group_by(TicketSale.payment_method)
    if view_club != 'All':
        pay_counts = pay_counts.filter(TicketSale.club == view_club)
    pay_counts = pay_counts.all()
    pay_labels = [r[0] for r in pay_counts]
    pay_data   = [r[1] for r in pay_counts]

    # Revenue trend (last 6 months)
    trend = db.session.query(
        func.strftime('%Y-%m', Event.date).label('month'),
        func.sum(Event.amount)
    ).filter(Event.type == 'Income',
             *([Event.club == view_club] if view_club != 'All' else [])
    ).group_by('month').order_by('month').limit(6).all()
    chart_labels = [r[0] for r in trend]
    chart_values = [r[1] for r in trend]

    return render_template('dashboard.html',
        user=current_user, events=events,
        income=round(income, 2), expense=round(expense, 2),
        tickets=tickets, refunds=refund_requests,
        active_events=active_events,
        success_rate=success_rate,
        ai_forecast=_ai_forecast(view_club),
        all_clubs=all_clubs,
        current_view=view_club,
        query_param=qp,
        messages=messages[::-1],
        audit_logs=audit_logs,
        chart_labels=chart_labels,
        chart_values=chart_values,
        pay_labels=pay_labels,
        pay_data=pay_data,
    )


@dashboard_bp.route('/add_club', methods=['POST'])
@login_required
@admin_required
def add_club():
    club_name = request.form['club_name'].strip()
    username  = request.form['username'].strip().lower()
    password  = request.form['password']

    # Create club record if not exists
    if not Club.query.filter_by(name=club_name).first():
        db.session.add(Club(name=club_name))

    if not User.query.filter_by(username=username).first():
        u = User(username=username, role='head', club=club_name,
                 email=f"{username}@medicaps.ac.in", position='President')
        u.set_password(password)
        db.session.add(u)
        _log(f"Admin created new club head: {username} → {club_name}", 'info')

    db.session.commit()
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/request_refund/<ticket_code>')
@login_required
def request_refund(ticket_code):
    ts = TicketSale.query.filter_by(ticket_code=ticket_code).first_or_404()
    ts.status = 'Refund Requested'
    _log(f"Refund requested for ticket {ticket_code} — {ts.buyer_name}", 'refund')
    return redirect(request.referrer or url_for('dashboard.index'))


@dashboard_bp.route('/process_refund/<ticket_code>/<action>')
@login_required
def process_refund(ticket_code, action):
    if current_user.role not in ['head', 'admin']:
        abort(403)
    ts = TicketSale.query.filter_by(ticket_code=ticket_code).first_or_404()
    # Club heads can only process their own club's tickets
    if current_user.role == 'head' and ts.club != current_user.club:
        abort(403)
    ts.status = 'Refunded' if action == 'approve' else 'Active'
    _log(f"Refund {'approved' if action=='approve' else 'rejected'} for ticket {ticket_code}", 'success' if action == 'approve' else 'alert')
    return redirect(request.referrer or url_for('dashboard.index'))


@dashboard_bp.route('/verify/<ticket_code>')
def verify_ticket(ticket_code):
    ticket = TicketSale.query.filter_by(ticket_code=ticket_code).first()
    return render_template('verify.html', ticket=ticket)


@dashboard_bp.route('/download_ticket/<filename>')
@login_required
def download_ticket(filename):
    from flask import send_file
    file_path = os.path.join('static', 'qrcodes', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=f"Ticket_{filename}")
    return "Ticket not found", 404


@dashboard_bp.route('/export_data')
@login_required
def export_data():
    view_club = _get_view_club()
    q = TicketSale.query
    if view_club != 'All':
        q = q.filter(TicketSale.club == view_club)
    sales = q.all()

    def generate():
        yield 'Date,Event Name,Buyer,Payment Method,Amount (INR),Status,Club\n'
        for r in sales:
            yield f"{r.purchase_date},{r.event_name},{r.buyer_name},{r.payment_method},{r.amount},{r.status},{r.club}\n"

    fname = view_club.replace(' ', '_') + '_Sales_Report.csv'
    return Response(generate(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={fname}'})
