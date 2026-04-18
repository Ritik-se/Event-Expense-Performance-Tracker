from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, Message, User
import datetime

comms_bp = Blueprint('comms', __name__)

def _get_view_club():
    if current_user.role == 'admin':
        return request.args.get('club_filter', 'All')
    return current_user.club

def _query_param(view_club):
    if view_club and view_club != 'All' and current_user.role == 'admin':
        return f'?club_filter={view_club}'
    return ''


@comms_bp.route('/comms')
@login_required
def comms():
    view_club = _get_view_club()
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    users_list = User.query.all()
    return render_template('comms.html',
        user=current_user,
        messages=messages,
        users_list=users_list,
        current_view=view_club,
        query_param=_query_param(view_club),
    )


@comms_bp.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    """AJAX endpoint — returns messages newer than ?after=<id>"""
    after_id = int(request.args.get('after', 0))
    msgs = Message.query.filter(Message.id > after_id).order_by(Message.timestamp.asc()).all()
    return jsonify([{
        'id':        m.id,
        'sender':    m.sender,
        'role':      m.role,
        'text':      m.text,
        'timestamp': m.timestamp.strftime('%H:%M'),
        'is_me':     m.sender == current_user.username,
    } for m in msgs])


@comms_bp.route('/api/messages', methods=['POST'])
@login_required
def post_message():
    """AJAX endpoint — post a new message."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'empty message'}), 400
    m = Message(
        sender_id=current_user.id,
        sender=current_user.username,
        role=current_user.role,
        text=text,
        timestamp=datetime.datetime.utcnow(),
    )
    db.session.add(m)
    db.session.commit()
    return jsonify({'id': m.id, 'status': 'ok'})
