from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.auth import current_facility, login_facility
from app.models import Facility
from app.ratelimit import enforce
from app.routes.auth import _password_problem, _valid_email
from app.validation import (
    FACILITY_TYPES,
    MAX_CITY,
    MAX_COUNTRY,
    MAX_EMAIL,
    MAX_NAME,
    trimmed,
)

facilities_bp = Blueprint("facilities", __name__)


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
        # Registration writes a row and hashes a password, so it is worth
        # slowing down: five attempts per IP per ten minutes.
        enforce("register", 5, 600)

        name, name_long = trimmed(request.form.get("name"), MAX_NAME)
        city, city_long = trimmed(request.form.get("city"), MAX_CITY)
        country, country_long = trimmed(request.form.get("country"), MAX_COUNTRY)
        facility_type = trimmed(request.form.get("facility_type"), 20)[0].lower()
        email = trimmed(request.form.get("contact_email"), MAX_EMAIL)[0].lower()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")

        errors = []
        if not name:
            errors.append("Facility name is required.")
        elif name_long:
            errors.append(f"Facility name must be {MAX_NAME} characters or fewer.")
        if not city:
            errors.append("City is required.")
        elif city_long:
            errors.append(f"City must be {MAX_CITY} characters or fewer.")
        if not country:
            errors.append("Country is required.")
        elif country_long:
            errors.append(f"Country must be {MAX_COUNTRY} characters or fewer.")
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
