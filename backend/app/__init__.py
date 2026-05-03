"""app/__init__.py — Flask app factory."""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate

from app.models import db
from config import get_config


def create_app(config_class=None) -> Flask:
    app = Flask(__name__)

    # Load config
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # Extensions
    CORS(app)
    db.init_app(app)
    Migrate(app, db)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.extract import extract_bp
    from app.routes.admin import admin_bp
    from app.routes.billing import billing_bp
    from app.routes.leads import leads_bp
    from app.routes.export import export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(extract_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(export_bp)

    # Health check
    @app.route('/health')
    def health():
        return jsonify({"status": "ok", "service": "SpyLeads API"}), 200

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method_not_allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "internal_server_error"}), 500

    # Seed system config on startup
    with app.app_context():
        db.create_all()
        from app.services.quota_service import seed_default_config
        seed_default_config()

    return app
