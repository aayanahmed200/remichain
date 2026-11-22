from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.auth import current_facility, login_required
from app.models import SupplyRequest
from app.ratelimit import enforce
from app.services.catalog import catalog_item_for
from app.services.matching import find_matches_for_request, create_match
from app.validation import (
    CATEGORIES,
    MAX_CATEGORY,
    MAX_ITEM_NAME,
    MAX_NOTES,
    MAX_QUANTITY,
    MAX_UNIT,
    URGENCIES,
    trimmed,
    whole_number,
)

requests_bp = Blueprint("requests", __name__)


@requests_bp.route("/request", methods=["GET", "POST"])
@login_required
def request_supply():
    facility = current_facility()

    if request.method == "POST":
        enforce("request", 30, 60, identity=facility.id)

        errors = []

        item_name, item_long = trimmed(request.form.get("item_name"), MAX_ITEM_NAME)
        if not item_name:
            errors.append("Item needed is required.")
        elif item_long:
            errors.append(f"Item needed must be {MAX_ITEM_NAME} characters or fewer.")

        category = trimmed(request.form.get("category"), MAX_CATEGORY)[0]
        if category not in CATEGORIES:
            errors.append("Choose a category from the list.")

        quantity_needed, quantity_error = whole_number(
            request.form.get("quantity_needed"), 1, MAX_QUANTITY
        )
        if quantity_error:
            errors.append(quantity_error)

        unit, unit_long = trimmed(request.form.get("unit") or "units", MAX_UNIT)
        if unit_long:
            errors.append(f"Unit must be {MAX_UNIT} characters or fewer.")

        urgency = trimmed(request.form.get("urgency"), 20)[0]
        if urgency not in URGENCIES:
            urgency = "medium"

        notes, notes_long = trimmed(request.form.get("notes"), MAX_NOTES)
        if notes_long:
            errors.append(f"Notes must be {MAX_NOTES} characters or fewer.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("request.html", facility=facility), 400

        need = SupplyRequest(
            # Always the signed-in facility: the request belongs to the account
            # that will accept or decline whatever gets matched to it.
            facility_id=facility.id,
            item_name=item_name,
            category=category,
            quantity_needed=quantity_needed,
            unit=unit or "units",
            urgency=urgency,
            notes=notes,
        )
        db.session.add(need)
        db.session.commit()

        # Add the spelling to the catalogue if it is new, so the next listing
        # or request with the same wording resolves without guesswork.
        catalog_item_for(item_name, category, create=True)

        # Immediately try to propose a match so the requester sees value right away
        best = find_matches_for_request(need, limit=1)
        if best:
            donation, score = best[0]
            create_match(donation, need, score)
            flash(f"Request posted — a possible match was found for {need.item_name}!", "success")
        else:
            flash(f"Request posted for {need.item_name}. We'll match it as donations come in.", "info")

        return redirect(url_for("main.dashboard"))

    return render_template("request.html", facility=facility)
