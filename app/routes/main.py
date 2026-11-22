import os

from flask import Blueprint, flash, redirect, render_template, send_from_directory, url_for

from app.models import Facility, Match, SupplyDonation, SupplyRequest
from app.services.matching import run_matching_pass
from config import BASE_DIR

main_bp = Blueprint("main", __name__)

# Vercel serves these from public/ at the CDN; the routes keep local
# development (and any other host) behaving the same way.
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


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
    recent_matches = Match.query.order_by(Match.created_at.desc()).limit(4).all()
    return render_template(
        "index.html",
        stats=network_stats(),
        recent_matches=recent_matches,
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


@main_bp.route("/dashboard/run-matching", methods=["POST"])
def run_matching():
    created = run_matching_pass()
    if created:
        noun = "match" if len(created) == 1 else "matches"
        flash(f"Matching pass complete — {len(created)} new {noun} proposed.", "success")
    else:
        flash("Matching pass complete — no new matches to propose right now.", "info")
    return redirect(url_for("main.dashboard"))
