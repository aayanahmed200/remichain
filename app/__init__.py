import os
from datetime import datetime, timezone

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from config import BASE_DIR, Config

db = SQLAlchemy()

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
# Static files are served by Vercel's CDN from public/ in production and by
# Flask from the same directory during local development.
STATIC_DIR = os.path.join(BASE_DIR, "public", "static")


def _ensure_facility_credentials_column():
    """Add facilities.password_hash to a database created before accounts existed.

    `db.create_all()` only creates missing tables, so a database that already
    has `facilities` would never gain the new column. The check-then-ALTER runs
    on both SQLite (local) and Postgres (Vercel + Supabase).
    """
    inspector = inspect(db.engine)
    if "facilities" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("facilities")}
    if "password_hash" in columns:
        return
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE facilities ADD COLUMN password_hash VARCHAR(255)"))


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes.main import main_bp
    from app.routes.donations import donations_bp
    from app.routes.requests import requests_bp
    from app.routes.facilities import facilities_bp
    from app.routes.matches import matches_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(facilities_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_account():
        from app.auth import current_facility

        return {"account": current_facility()}

    @app.context_processor
    def inject_site_meta():
        site_url = app.config.get("SITE_URL", "https://remichain.vercel.app").rstrip("/")
        return {
            "site_url": site_url,
            "canonical": site_url + request.path,
            "year": datetime.now(timezone.utc).year,
        }

    with app.app_context():
        try:
            db.create_all()
            _ensure_facility_credentials_column()
            from app.services.seed import seed_facilities
            seed_facilities()
        except Exception:  # noqa: BLE001 - a cold start must not crash the site
            db.session.rollback()
            app.logger.exception("Could not initialise the database")

    return app
