from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db
from app.models import SupplyRequest, Facility
from app.services.matching import find_matches_for_request, create_match

requests_bp = Blueprint("requests", __name__)


@requests_bp.route("/request", methods=["GET", "POST"])
def request_supply():
    facilities = Facility.query.order_by(Facility.name).all()

    if request.method == "POST":
        try:
            facility_id = int(request.form["facility_id"])
            quantity_needed = int(request.form["quantity_needed"])
        except (KeyError, ValueError):
            flash("Please choose a facility and enter quantity needed as a whole number.", "error")
            return render_template("request.html", facilities=facilities), 400

        need = SupplyRequest(
            facility_id=facility_id,
            item_name=request.form["item_name"].strip(),
            category=request.form["category"],
            quantity_needed=quantity_needed,
            unit=request.form.get("unit", "units"),
            urgency=request.form.get("urgency", "medium"),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(need)
        db.session.commit()

        # Immediately try to propose a match so the requester sees value right away
        best = find_matches_for_request(need, limit=1)
        if best:
            donation, score = best[0]
            create_match(donation, need, score)
            flash(f"Request posted — a possible match was found for {need.item_name}!", "success")
        else:
            flash(f"Request posted for {need.item_name}. We'll match it as donations come in.", "info")

        return redirect(url_for("main.dashboard"))

    return render_template("request.html", facilities=facilities)
