"""CSRF protection.

Every unsafe request (POST/PUT/PATCH/DELETE) must carry the token bound to the
current session in a `csrf_token` form field or an `X-CSRF-Token` header.
Without it, a page on another site could submit a form to RemiChain using the
visitor's signed-in cookie, which is exactly how a stranger could accept or
decline someone else's match by URL.

The Vercel cron endpoint is exempt: it is authenticated by CRON_SECRET instead,
and never carries a browser session.
"""

import secrets

from flask import abort, request, session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_ENDPOINTS = {"api.cron_maintenance"}
TOKEN_KEY = "csrf_token"


def csrf_token():
    """The token for this session, minted on first use."""
    token = session.get(TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[TOKEN_KEY] = token
    return token


def init_security(app):
    @app.before_request
    def check_csrf():
        if request.method in SAFE_METHODS or request.endpoint in EXEMPT_ENDPOINTS:
            return None

        expected = session.get(TOKEN_KEY, "")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")

        if not expected or not sent or not secrets.compare_digest(str(sent), str(expected)):
            abort(
                400,
                description="That form is missing a valid security token. Reload the page and try again.",
            )
        return None

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token}
