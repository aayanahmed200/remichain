import os

from flask import Blueprint, flash, redirect, render_template, send_from_directory, url_for
from sqlalchemy import or_

from app.auth import current_facility, login_required
from app.models import Facility, Match, SupplyDonation, SupplyRequest
from app.services.matching import run_matching_pass
from config import BASE_DIR

main_bp = Blueprint("main", __name__)

# Vercel serves these from public/ at the CDN; the routes keep local
# development (and any other host) behaving the same way.
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


def network_stats():
    """Headline numbers shown on the landing page."""
    return {
        "facilities": Facility.query.count(),
        "available_donations": SupplyDonation.query.filter_by(status="available").count(),
        "open_requests": SupplyRequest.query.filter(
            SupplyRequest.status.in_(["open", "partially_fulfilled"])
        ).count(),
        "matches_made": Match.query.count(),
    }


def facility_stats(facility):
    """The same four numbers, but for one facility's own records."""
    return {
        "facilities": Facility.query.count(),
        "available_donations": SupplyDonation.query.filter_by(
            facility_id=facility.id, status="available"
        ).count(),
        "open_requests": SupplyRequest.query.filter(
            SupplyRequest.facility_id == facility.id,
            SupplyRequest.status.in_(["open", "partially_fulfilled"]),
        ).count(),
        "matches_made": own_matches_query(facility).count(),
    }


def own_matches_query(facility):
    """Matches where this facility is the donor or the recipient."""
    return Match.query.filter(
        or_(
            Match.donation.has(SupplyDonation.facility_id == facility.id),
            Match.request.has(SupplyRequest.facility_id == facility.id),
        )
    )


@main_bp.route("/")
def index():
    recent_matches = Match.query.order_by(Match.created_at.desc()).limit(4).all()
    return render_template(
        "index.html",
        stats=network_stats(),
        recent_matches=recent_matches,
        facilities=Facility.query.order_by(Facility.name).all(),
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    facility = current_facility()
    donations = (
        SupplyDonation.query.filter_by(facility_id=facility.id)
        .order_by(SupplyDonation.created_at.desc())
        .limit(20)
        .all()
    )
    requests_ = (
        SupplyRequest.query.filter_by(facility_id=facility.id)
        .order_by(SupplyRequest.created_at.desc())
        .limit(20)
        .all()
    )
    matches = own_matches_query(facility).order_by(Match.created_at.desc()).limit(20).all()
    return render_template(
        "dashboard.html",
        facility=facility,
        stats=facility_stats(facility),
        donations=donations,
        requests=requests_,
        matches=matches,
    )


@main_bp.route("/dashboard/run-matching", methods=["POST"])
@login_required
def run_matching():
    facility = current_facility()
    created = run_matching_pass(donor_facility_id=facility.id)
    if created:
        noun = "match" if len(created) == 1 else "matches"
        flash(f"Matching pass complete — {len(created)} new {noun} proposed from your stock.", "success")
    else:
        flash("Matching pass complete — none of your available stock fits an open request right now.", "info")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(PUBLIC_DIR, "favicon.ico", mimetype="image/vnd.microsoft.icon")


@main_bp.route("/robots.txt")
def robots():
    return send_from_directory(PUBLIC_DIR, "robots.txt", mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap():
    return send_from_directory(PUBLIC_DIR, "sitemap.xml", mimetype="application/xml")


@main_bp.route("/site.webmanifest")
def manifest():
    return send_from_directory(
        PUBLIC_DIR, "site.webmanifest", mimetype="application/manifest+json"
    )
