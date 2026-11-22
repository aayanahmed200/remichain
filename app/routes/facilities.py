from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.auth import current_facility, login_facility
from app.models import Facility
from app.routes.auth import _password_problem, _valid_email

facilities_bp = Blueprint("facilities", __name__)

FACILITY_TYPES = ["hospital", "clinic", "pharmacy", "ngo"]


def _coordinate(raw, label, low, high, errors):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        errors.append(f"{label} must be a number, for example 31.5497.")
        return None
    if not low <= value <= high:
        errors.append(f"{label} must be between {low} and {high}.")
        return None
    return value


@facilities_bp.route("/facilities/new", methods=["GET", "POST"])
def new_facility():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        country = request.form.get("country", "").strip()
        facility_type = request.form.get("facility_type", "hospital").strip().lower()
        email = request.form.get("contact_email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")

        errors = []
        if not name:
            errors.append("Facility name is required.")
        if not city:
            errors.append("City is required.")
        if not country:
            errors.append("Country is required.")
        if facility_type not in FACILITY_TYPES:
            facility_type = "hospital"
        if not _valid_email(email):
            errors.append("Enter the email that will sign in to this facility, for example supplies@facility.org.")
        problem = _password_problem(password, confirm)
        if problem:
            errors.append(problem)

        if not errors and Facility.query.filter(db.func.lower(Facility.contact_email) == email).first():
            errors.append("A facility already signs in with that email. Sign in instead, or use another address.")

        latitude = _coordinate(request.form.get("latitude"), "Latitude", -90, 90, errors)
        longitude = _coordinate(request.form.get("longitude"), "Longitude", -180, 180, errors)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("facility_new.html", types=FACILITY_TYPES, form=request.form), 400

        facility = Facility(
            name=name,
            facility_type=facility_type,
            city=city,
            country=country,
            latitude=latitude,
            longitude=longitude,
            contact_email=email,
            verified=False,
        )
        facility.set_password(password)
        db.session.add(facility)
        db.session.commit()

        # Registering is signing up: the facility lands straight in its own
        # dashboard rather than having to sign in again.
        login_facility(facility)
        flash(f"{facility.name} is now on the network — list your surplus stock.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("facility_new.html", types=FACILITY_TYPES, form={})
