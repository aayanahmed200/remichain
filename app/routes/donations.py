from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.auth import current_facility, login_required
from app.models import SupplyDonation

donations_bp = Blueprint("donations", __name__)


@donations_bp.route("/donate", methods=["GET", "POST"])
@login_required
def donate():
    facility = current_facility()

    if request.method == "POST":
        expiry_raw = request.form.get("expiry_date", "").strip()
        try:
            expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d").date() if expiry_raw else None
        except ValueError:
            flash("Expiry date must be a valid date (YYYY-MM-DD).", "error")
            return render_template("donate.html", facility=facility), 400

        try:
            quantity = int(request.form["quantity"])
            item_name = request.form["item_name"].strip()
            category = request.form["category"].strip()
            if not item_name or not category or quantity < 1:
                raise ValueError("missing or invalid field")
        except (KeyError, ValueError):
            flash(
                "Please enter an item name and category, and enter quantity as a whole number of at least 1.",
                "error",
            )
            return render_template("donate.html", facility=facility), 400

        donation = SupplyDonation(
            # Always the signed-in facility: stock is only ever listed under the
            # account that will answer for it.
            facility_id=facility.id,
            item_name=item_name,
            category=category,
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

    return render_template("donate.html", facility=facility)
