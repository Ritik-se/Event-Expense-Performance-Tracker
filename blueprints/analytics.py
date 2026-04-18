from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Event, TicketSale, Club
import numpy as np
from sqlalchemy import func, case

analytics_bp = Blueprint('analytics', __name__)

def _get_view_club():
    if current_user.role == 'admin':
        return request.args.get('club_filter', 'All')
    return current_user.club

def _query_param(view_club):
    if view_club and view_club != 'All' and current_user.role == 'admin':
        return f'?club_filter={view_club}'
    return ''

def _linear_forecast(view_club):
    """Numpy linear regression for predictive AI engine."""
    q = db.session.query(
        func.strftime('%Y-%m', Event.date).label('month'),
        func.sum(Event.amount).label('total')
    ).filter(Event.type == 'Income')
    if view_club != 'All':
        q = q.filter(Event.club == view_club)
    rows = q.group_by('month').order_by('month').all()
    if len(rows) < 2:
        return 0, []
    values = [float(r.total) for r in rows]
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values, 1)
    forecast = float(coeffs[0] * len(values) + coeffs[1])
    return max(0, int(forecast)), [int(np.polyval(coeffs, xi)) for xi in x]


@analytics_bp.route('/reports')
@login_required
def reports():
    view_club = _get_view_club()
    qp = _query_param(view_club)

    # ── Cashflow (MoM) ────────────────────────────────────────────────────
   # 1. Build the base query (Notice we use 'case' here, NOT 'func.case')
    cf_q = db.session.query(
        func.strftime('%Y-%m', Event.date).label('month'),
        func.sum(case((Event.type == 'Income', Event.amount), else_=0)).label('inc'),
        func.sum(case((Event.type == 'Expense', Event.amount), else_=0)).label('exp')
    )
    
    # 2. Apply the dynamic club filter if the user isn't an Admin looking at "All"
    if view_club != 'All':
        cf_q = cf_q.filter(Event.club == view_club)
        
    # 3. Group, sort, and execute!
    cashflow = cf_q.group_by('month').order_by('month').limit(6).all()

    # ── Top Events ────────────────────────────────────────────────────────
    te_q = db.session.query(Event.name, Event.participation)
    if view_club != 'All':
        te_q = te_q.filter(Event.club == view_club)
    top_events = te_q.order_by(Event.participation.desc()).limit(5).all()

    # ── Payment Distribution ──────────────────────────────────────────────
    pd_q = db.session.query(TicketSale.payment_method, func.count().label('cnt'))
    if view_club != 'All':
        pd_q = pd_q.filter(TicketSale.club == view_club)
    pay_dist = pd_q.group_by(TicketSale.payment_method).all()

    # ── Club Performance Radar ────────────────────────────────────────────
    radar = db.session.query(
        Event.club,
        func.sum(Event.participation).label('total_p'),
        func.count().label('event_count')
    ).group_by(Event.club).all()

    # ── Totals ────────────────────────────────────────────────────────────
    base_q = db.session.query(func.sum(Event.tickets_sold), func.sum(Event.participation))
    if view_club != 'All':
        base_q = base_q.filter(Event.club == view_club)
    total_tickets, total_participation = base_q.one()

    # ── AI Forecast ───────────────────────────────────────────────────────
    ai_next, trend_line = _linear_forecast(view_club)

    return render_template('reports.html',
        user=current_user,
        current_view=view_club,
        query_param=qp,
        cf_labels=[r.month for r in cashflow],
        cf_income=[float(r.inc) for r in cashflow],
        cf_expense=[float(r.exp) for r in cashflow],
        trend_line=trend_line,
        te_labels=[r.name[:25] for r in top_events],
        te_data=[r.participation for r in top_events],
        pay_labels=[r.payment_method for r in pay_dist],
        pay_data=[r.cnt for r in pay_dist],
        radar_labels=[r.club for r in radar],
        radar_data=[r.total_p for r in radar],
        total_tickets=total_tickets or 0,
        total_participation=total_participation or 0,
        ai_forecast=ai_next,
    )


@analytics_bp.route('/api/chart_data')
@login_required
def chart_data():
    """AJAX endpoint for chart data refresh."""
    view_club = _get_view_club()
    ai_next, trend_line = _linear_forecast(view_club)

    cf_q = db.session.query(
        func.strftime('%Y-%m', Event.date).label('month'),
        func.sum(func.case((Event.type == 'Income', Event.amount), else_=0)).label('inc'),
        func.sum(func.case((Event.type == 'Expense', Event.amount), else_=0)).label('exp'),
    )
    if view_club != 'All':
        cf_q = cf_q.filter(Event.club == view_club)
    cashflow = cf_q.group_by('month').order_by('month').limit(6).all()

    pay_q = db.session.query(TicketSale.payment_method, func.count())
    if view_club != 'All':
        pay_q = pay_q.filter(TicketSale.club == view_club)
    pay_dist = pay_q.group_by(TicketSale.payment_method).all()

    radar = db.session.query(
        Event.club, func.sum(Event.participation)
    ).group_by(Event.club).all()

    return jsonify({
        'cashflow': {
            'labels': [r.month for r in cashflow],
            'income': [float(r.inc) for r in cashflow],
            'expense': [float(r.exp) for r in cashflow],
            'trendLine': trend_line,
        },
        'payment': {
            'labels': [r[0] for r in pay_dist],
            'data':   [r[1] for r in pay_dist],
        },
        'radar': {
            'labels': [r[0] for r in radar],
            'data':   [int(r[1] or 0) for r in radar],
        },
        'ai_forecast': ai_next,
    })
