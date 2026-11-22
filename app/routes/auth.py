from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.auth import current_facility, login_facility, logout_facility
from app.models import Facility

auth_bp = Blueprint("auth", __name__)

MIN_PASSWORD = 8
MAX_PASSWORD = 200


def _clean_email(raw):
    return (raw or "").strip().lower()


def _valid_email(email):
    return "@" in email and "." in email.rsplit("@", 1)[-1]


def _password_problem(password, confirm):
    if len(password) < MIN_PASSWORD:
        return f"Choose a password of at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return "That password is too long."
    if password != confirm:
        return "The two passwords do not match."
    return None


def _safe_next(target):
    """Only follow same-site relative paths after sign-in."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("main.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and current_facility() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = _clean_email(request.form.get("email"))
        password = request.form.get("password", "")
        facility = (
            Facility.query.filter(db.func.lower(Facility.contact_email) == email).first()
            if email
            else None
        )
        if facility is None or not facility.check_password(password):
            flash("That email and password do not match a facility account.", "error")
            return render_template("login.html", form=request.form, next=request.form.get("next", "")), 401

        login_facility(facility)
        flash(f"Signed in as {facility.name}.", "success")
        return redirect(_safe_next(request.form.get("next")))

    return render_template("login.html", form={}, next=request.args.get("next", ""))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    facility = current_facility()
    if facility is None:
        return redirect(url_for("main.index"))

    logout_facility()
    flash(f"Signed out of {facility.name}.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/claim", methods=["GET", "POST"])
def claim():
    """Give a facility that predates accounts an email and password.

    Only rows with no password can be claimed, so a claim can never take over
    an account that is already in use.
    """
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        email = _clean_email(request.form.get("email"))
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")

        errors = []
        if not name:
            errors.append("Enter the facility name exactly as it appears on the network list.")
        if not city:
            errors.append("Enter the facility's city.")
        if not _valid_email(email):
            errors.append("Enter a valid email — it becomes your sign-in address.")
        problem = _password_problem(password, confirm)
        if problem:
            errors.append(problem)

        if not errors and Facility.query.filter(db.func.lower(Facility.contact_email) == email).first():
            errors.append("That email already signs in to a facility — sign in instead.")

        facility = None
        if not errors:
            facility = (
                Facility.query.filter(
                    Facility.password_hash.is_(None),
                    db.func.lower(Facility.name) == name.lower(),
                    db.func.lower(Facility.city) == city.lower(),
                )
                .order_by(Facility.id)
                .first()
            )
            if facility is None:
                errors.append(
                    f"No unclaimed facility called \u201c{name}\u201d in {city}. "
                    "Check the spelling, or register it as a new facility."
                )

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("claim.html", form=request.form), 400

        facility.contact_email = email
        facility.set_password(password)
        db.session.commit()

        login_facility(facility)
        flash(f"{facility.name} is now yours to manage.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("claim.html", form={})
