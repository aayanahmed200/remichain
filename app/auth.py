"""Facility accounts.

A signed-in facility is stored in the Flask session as its row id, so every
request re-reads the facility from the database rather than trusting anything
the browser sends. Ownership checks compare against that id, never against a
hidden form field.
"""

from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from app.models import Facility

SESSION_KEY = "facility_id"


def login_facility(facility):
    """Start a signed-in session for this facility."""
    session.clear()
    session[SESSION_KEY] = facility.id
    session.permanent = True
    g.facility = facility


def logout_facility():
    """Drop the session and any cached facility for this request."""
    session.pop(SESSION_KEY, None)
    g.pop("facility", None)


def current_facility():
    """The signed-in facility, or None. Cached on `g` for the request."""
    if "facility" in g:
        return g.facility

    facility_id = session.get(SESSION_KEY)
    facility = Facility.query.get(facility_id) if facility_id else None
    g.facility = facility
    return facility


def login_required(view):
    """Send signed-out visitors to the sign-in page, remembering where to go."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_facility() is None:
            flash("Sign in with your facility account to continue.", "info")
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def owns_match(facility, match):
    """True when this facility is either the donor or the recipient."""
    if facility is None or match is None:
        return False
    return facility.id in (match.donation.facility_id, match.request.facility_id)
