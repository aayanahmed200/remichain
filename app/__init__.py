import hashlib
import os
from datetime import datetime, timezone

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from config import BASE_DIR, Config

db = SQLAlchemy()

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
# Static files are served by Vercel's CDN from public/ in production and by
# Flask from the same directory during local development.
STATIC_DIR = os.path.join(BASE_DIR, "public", "static")


# Columns added after the tables first shipped. `db.create_all()` only creates
# missing tables, so an existing database has to be altered in place.
ADDED_COLUMNS = {
    "facilities": {"password_hash": "VARCHAR(255)"},
    "supply_donations": {"expired_flagged_at": "TIMESTAMP"},
}


def _ensure_schema_columns():
    """Add any columns a database predating them is missing.

The check-then-ALTER runs on both SQLite (local) and Postgres (Vercel +
    Supabase). Existing rows get NULL, which every reader treats as "not set".
    """
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    for table, columns in ADDED_COLUMNS.items():
        if table not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        missing = {name: ddl for name, ddl in columns.items() if name not in existing}
        if not missing:
            continue
        with db.engine.begin() as connection:
            for name, ddl in missing.items():
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


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

    from app.security import init_security

    init_security(app)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(429)
    def request_error(error):
        return (
            render_template(
                "error.html",
                code=error.code,
                title=error.name,
                message=error.description,
            ),
            error.code,
        )

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

    @app.context_processor
    def inject_asset_version():
        """Cache-bust style.css and app.js.

        Both files keep a stable name, so a browser that cached them during an
        earlier deployment keeps painting that stylesheet until it expires —
        which reads as the site forgetting a redesign. The query string is a
        hash of the files' contents rather than their mtime: Vercel normalises
        mtimes during a build, so every deploy would otherwise produce the
        same version and never invalidate anything.
        """
        version = app.extensions.get("asset_version")
        if version is None:
            digest = hashlib.sha1()
            # Icons are in here on purpose: browsers keep a favicon in a cache
            # of their own that outlives normal revalidation and is keyed by
            # URL, so replacing the file behind /favicon.ico is not enough —
            # the URL has to change for the new mark to appear.
            assets = [
                os.path.join(STATIC_DIR, "css/style.css"),
                os.path.join(STATIC_DIR, "js/app.js"),
                os.path.join(STATIC_DIR, "images/logo-mark.png"),
                os.path.join(STATIC_DIR, "images/icon-32.png"),
                os.path.join(STATIC_DIR, "images/icon-180.png"),
                os.path.join(STATIC_DIR, "images/icon-192.png"),
                os.path.join(STATIC_DIR, "images/icon-512.png"),
                os.path.join(STATIC_DIR, "images/og.png"),
                os.path.join(BASE_DIR, "public", "favicon.ico"),
            ]
            for path in assets:
                try:
                    with open(path, "rb") as asset:
                        digest.update(asset.read())
                except OSError:
                    continue
            version = digest.hexdigest()[:10]
            app.extensions["asset_version"] = version
        return {"asset_version": version}

    with app.app_context():
        try:
            # Imported here so the model is registered before create_all().
            from app.models import RateLimit  # noqa: F401

            db.create_all()
            _ensure_schema_columns()
            from app.services.catalog import seed_catalog
            from app.services.seed import seed_facilities

            seed_facilities()
            seed_catalog()
        except Exception:  # noqa: BLE001 - a cold start must not crash the site
            db.session.rollback()
            app.logger.exception("Could not initialise the database")

    return app
