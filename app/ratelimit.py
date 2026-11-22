"""Per-identity request limits for the write endpoints.

Fixed windows: a bucket allows `limit` requests per `window_seconds`, then
returns 429 until the window rolls over. Counters live in the database (see
models/ratelimit.py) so they survive serverless instance churn.
"""

from datetime import datetime, timezone

from flask import abort, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import RateLimit


def _window(window_seconds):
    return int(datetime.now(timezone.utc).timestamp() // window_seconds)


def _increment(bucket, window):
    """Add one hit to the bucket and return the running total."""
    updated = (
        db.session.query(RateLimit)
        .filter(RateLimit.bucket == bucket, RateLimit.window_start == window)
        .update({RateLimit.hits: RateLimit.hits + 1}, synchronize_session=False)
    )
    if updated:
        db.session.commit()
        row = RateLimit.query.filter_by(bucket=bucket, window_start=window).first()
        return row.hits if row else 1

    # First hit of this window. A concurrent request can insert the same row
    # first, which the unique constraint catches; then just bump its counter.
    db.session.add(RateLimit(bucket=bucket, window_start=window, hits=1))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        db.session.query(RateLimit).filter(
            RateLimit.bucket == bucket, RateLimit.window_start == window
        ).update({RateLimit.hits: RateLimit.hits + 1}, synchronize_session=False)
        db.session.commit()
        row = RateLimit.query.filter_by(bucket=bucket, window_start=window).first()
        return row.hits if row else 2

    # Cheap housekeeping: windows older than an hour are never read again.
    db.session.query(RateLimit).filter(RateLimit.window_start < window - 60).delete()
    db.session.commit()
    return 1


def consume(scope, limit, window_seconds=60, identity=None):
    """Record one request. True while the caller is still under the limit."""
    who = str(identity) if identity is not None else (request.remote_addr or "unknown")
    return _increment(f"{scope}:{who}", _window(window_seconds)) <= limit


def enforce(scope, limit, window_seconds=60, identity=None):
    """consume(), but abort the request with 429 when the limit is spent."""
    if not consume(scope, limit, window_seconds, identity=identity):
        abort(
            429,
            description="Too many attempts in a short time. Wait a minute and try again.",
        )
