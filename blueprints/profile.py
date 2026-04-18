from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, User

profile_bp = Blueprint('profile', __name__)

def _get_view_club():
    if current_user.role == 'admin':
        return request.args.get('club_filter', 'All')
    return current_user.club

def _query_param(view_club):
    if view_club and view_club != 'All' and current_user.role == 'admin':
        return f'?club_filter={view_club}'
    return ''

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    view_club = _get_view_club()
    if request.method == 'POST':
        current_user.email    = request.form.get('email', '')
        current_user.phone    = request.form.get('phone', '')
        current_user.bio      = request.form.get('bio', '')
        current_user.position = request.form.get('position', '')
        current_user.linkedin = request.form.get('linkedin', '')
        db.session.commit()
        return redirect(url_for('profile.profile') + _query_param(view_club))
    return render_template('profile.html',
        user=current_user,
        current_view=view_club,
        query_param=_query_param(view_club),
    )
