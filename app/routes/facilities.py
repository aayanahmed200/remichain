from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Facility

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
        email = request.form.get("contact_email", "").strip()

        errors = []
        if not name:
            errors.append("Facility name is required.")
        if not city:
            errors.append("City is required.")
        if not country:
            errors.append("Country is required.")
        if facility_type not in FACILITY_TYPES:
            facility_type = "hospital"
        if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
            errors.append("Enter a valid contact email, for example supplies@facility.org.")

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
            contact_email=email or None,
            verified=False,
        )
        db.session.add(facility)
        db.session.commit()

        flash(f"{facility.name} is now on the network — you can list stock under it.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("facility_new.html", types=FACILITY_TYPES, form={})
