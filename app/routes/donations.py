from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.auth import current_facility, login_required
from app.models import SupplyDonation
from app.ratelimit import enforce
from app.services.catalog import catalog_item_for
from app.validation import (
    CATEGORIES,
    CONDITIONS,
    MAX_CATEGORY,
    MAX_ITEM_NAME,
    MAX_NOTES,
    MAX_QUANTITY,
    MAX_UNIT,
    trimmed,
    whole_number,
)

donations_bp = Blueprint("donations", __name__)


@donations_bp.route("/donate", methods=["GET", "POST"])
@login_required
def donate():
    facility = current_facility()

    if request.method == "POST":
        enforce("donate", 30, 60, identity=facility.id)

        errors = []

        expiry_raw = trimmed(request.form.get("expiry_date"), 10)[0]
        expiry_date = None
        if expiry_raw:
            try:
                expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Expiry date must be a valid date (YYYY-MM-DD).")

        item_name, item_long = trimmed(request.form.get("item_name"), MAX_ITEM_NAME)
        if not item_name:
            errors.append("Item name is required.")
        elif item_long:
            errors.append(f"Item name must be {MAX_ITEM_NAME} characters or fewer.")

        category = trimmed(request.form.get("category"), MAX_CATEGORY)[0]
        if category not in CATEGORIES:
            errors.append("Choose a category from the list.")

        quantity, quantity_error = whole_number(request.form.get("quantity"), 1, MAX_QUANTITY)
        if quantity_error:
            errors.append(quantity_error)

        unit, unit_long = trimmed(request.form.get("unit") or "units", MAX_UNIT)
        if unit_long:
            errors.append(f"Unit must be {MAX_UNIT} characters or fewer.")

        condition = trimmed(request.form.get("condition"), 30)[0]
        if condition not in CONDITIONS:
            condition = "new"

        notes, notes_long = trimmed(request.form.get("notes"), MAX_NOTES)
        if notes_long:
            errors.append(f"Notes must be {MAX_NOTES} characters or fewer.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("donate.html", facility=facility), 400

        donation = SupplyDonation(
            # Always the signed-in facility: stock is only ever listed under the
            # account that will answer for it.
            facility_id=facility.id,
            item_name=item_name,
            category=category,
            quantity=quantity,
            unit=unit or "units",
            expiry_date=expiry_date,
            condition=condition,
            notes=notes,
        )
        db.session.add(donation)
        db.session.commit()

        # Add the spelling to the catalogue if it is new, so the next listing
        # or request with the same wording resolves without guesswork.
        catalog_item_for(item_name, category, create=True)

        flash(f"Thank you — {donation.item_name} listed as surplus.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("donate.html", facility=facility)
