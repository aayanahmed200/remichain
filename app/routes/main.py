from flask import Blueprint, flash, redirect, render_template, url_for

from app.models import Facility, Match, SupplyDonation, SupplyRequest
from app.services.matching import run_matching_pass

main_bp = Blueprint("main", __name__)


def network_stats():
    """Headline numbers shown on the landing page and the dashboard."""
    return {
        "facilities": Facility.query.count(),
        "available_donations": SupplyDonation.query.filter_by(status="available").count(),
        "open_requests": SupplyRequest.query.filter(
            SupplyRequest.status.in_(["open", "partially_fulfilled"])
        ).count(),
        "matches_made": Match.query.count(),
    }


@main_bp.route("/")
def index():
    return render_template(
        "index.html",
        stats=network_stats(),
        facilities=Facility.query.order_by(Facility.name).all(),
    )


@main_bp.route("/dashboard")
def dashboard():
    donations = SupplyDonation.query.order_by(SupplyDonation.created_at.desc()).limit(20).all()
    requests_ = SupplyRequest.query.order_by(SupplyRequest.created_at.desc()).limit(20).all()
    matches = Match.query.order_by(Match.created_at.desc()).limit(20).all()
    return render_template(
        "dashboard.html",
        stats=network_stats(),
        donations=donations,
        requests=requests_,
        matches=matches,
    )


@main_bp.route("/dashboard/run-matching", methods=["POST"])
def run_matching():
    created = run_matching_pass()
    if created:
        noun = "match" if len(created) == 1 else "matches"
        flash(f"Matching pass complete — {len(created)} new {noun} proposed.", "success")
    else:
        flash("Matching pass complete — no new matches to propose right now.", "info")
    return redirect(url_for("main.dashboard"))
