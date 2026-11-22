import os
import tempfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Hosted Postgres providers hand out their connection string under different
# names. Neon, Supabase, and the Vercel storage integrations cover the ones
# below, so accept whichever the deployment provides.
DATABASE_ENV_VARS = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_PRISMA_URL",
    "POSTGRES_URL_NON_POOLING",
)


def database_uri():
    """Connection string for SQLAlchemy.

    Postgres when the deployment supplies one (required on Vercel, where the
    filesystem is read-only and ephemeral), otherwise a local SQLite file.
    """
    for name in DATABASE_ENV_VARS:
        url = os.environ.get(name, "").strip()
        if not url:
            continue
        # Providers still emit the legacy `postgres://` scheme, which
        # SQLAlchemy does not recognize, and SQLAlchemy 2 needs the driver
        # spelled out so it loads psycopg (v3) instead of guessing psycopg2.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    if os.environ.get("VERCEL"):
        # No database configured: keep the site usable, but remember that
        # writes here live only as long as this function instance.
        return "sqlite:///" + os.path.join(tempfile.gettempdir(), "remichain.db")

    return "sqlite:///" + os.path.join(BASE_DIR, "remichain.db")


class Config:
    # Canonical origin used for SEO tags, the sitemap and absolute links.
    SITE_URL = os.environ.get("SITE_URL", "https://remichain.vercel.app")

    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or "dev-secret-change-in-production"
    )
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Serverless functions are frozen between requests, so pooled connections
    # can go stale or be dropped by the provider while the instance sleeps.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 180}

    # Matching engine tuning
    URGENCY_WEIGHT = 3.0
    EXPIRY_WEIGHT = 2.0
    PROXIMITY_WEIGHT = 1.5
    QUANTITY_WEIGHT = 1.0
