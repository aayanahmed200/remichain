from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.models import SupplyDonation, Facility

donations_bp = Blueprint("donations", __name__)


@donations_bp.route("/donate", methods=["GET", "POST"])
def donate():
    facilities = Facility.query.order_by(Facility.name).all()

    if request.method == "POST":
        expiry_raw = request.form.get("expiry_date", "").strip()
        try:
            expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d").date() if expiry_raw else None
        except ValueError:
            flash("Expiry date must be a valid date (YYYY-MM-DD).", "error")
            return render_template("donate.html", facilities=facilities), 400

        try:
            facility_id = int(request.form["facility_id"])
            quantity = int(request.form["quantity"])
        except (KeyError, ValueError):
            flash("Please choose a facility and enter quantity as a whole number.", "error")
            return render_template("donate.html", facilities=facilities), 400

        donation = SupplyDonation(
            facility_id=facility_id,
            item_name=request.form["item_name"].strip(),
            category=request.form["category"],
            quantity=quantity,
            unit=request.form.get("unit", "units"),
            expiry_date=expiry_date,
            condition=request.form.get("condition", "new"),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(donation)
        db.session.commit()
        flash(f"Thank you — {donation.item_name} listed as surplus.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("donate.html", facilities=facilities)
