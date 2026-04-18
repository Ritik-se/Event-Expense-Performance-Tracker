import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from models import db, User

def create_app():
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────
    app.config['SECRET_KEY']                  = os.environ.get('SECRET_KEY', 'EVENTIQ_MEDICAPS_2026_SUPERSECRET')
    app.config['SQLALCHEMY_DATABASE_URI']     = 'sqlite:///event_data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Extensions ─────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access EventIQ.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Blueprints ─────────────────────────────────────────────────────────
    from blueprints.auth      import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.analytics import analytics_bp
    from blueprints.comms     import comms_bp
    from blueprints.profile   import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(comms_bp)
    app.register_blueprint(profile_bp)

    # ── Error Handlers ─────────────────────────────────────────────────────
    from flask import render_template as rt
    @app.errorhandler(403)
    def forbidden(e):
        return rt('403.html'), 403

    # ── DB Init & Seed ─────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        from seed import seed_database
        seed_database()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
