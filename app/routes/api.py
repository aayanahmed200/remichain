import hmac
import os

from flask import Blueprint, jsonify, request

from app.auth import current_facility
from app.models import CatalogItem, SupplyDonation, SupplyRequest, Match
from app.ratelimit import consume
from app.services.matching import run_matching_pass, find_matches_for_request
from app.services.sweep import run_maintenance

api_bp = Blueprint("api", __name__)


def _cron_authorized():
    """Only Vercel's scheduler, proved by the shared secret.

    Without CRON_SECRET the job is refused rather than trusting a user agent,
    which anyone can copy. Loopback stays open so local development works.
    """
    secret = os.environ.get("CRON_SECRET", "").strip()
    if secret:
        return hmac.compare_digest(
            request.headers.get("Authorization", ""), f"Bearer {secret}"
        )
    return request.remote_addr in ("127.0.0.1", "::1")


@api_bp.route("/donations", methods=["GET"])
def list_donations():
    return jsonify([d.to_dict() for d in SupplyDonation.query.all()])


@api_bp.route("/requests", methods=["GET"])
def list_requests():
    return jsonify([r.to_dict() for r in SupplyRequest.query.all()])


@api_bp.route("/catalogue", methods=["GET"])
def list_catalogue():
    """The normalised catalogue: canonical names, aliases and pack sizes."""
    return jsonify([item.to_dict() for item in CatalogItem.query.order_by(CatalogItem.name)])


@api_bp.route("/matches", methods=["GET"])
def list_matches():
    return jsonify([m.to_dict() for m in Match.query.all()])


@api_bp.route("/requests/<int:request_id>/candidates", methods=["GET"])
def candidates_for_request(request_id):
    req = SupplyRequest.query.get_or_404(request_id)
    matches = find_matches_for_request(req, limit=5)
    return jsonify([
        {"donation": d.to_dict(), "score": round(score, 2)} for d, score in matches
    ])


@api_bp.route("/run-matching", methods=["POST"])
def trigger_matching_pass():
    """Run matching for the signed-in facility's own stock.

    This used to be a public POST that ran the whole network's matching pass,
    which let anyone cause writes by hitting a URL. The site-wide pass now
    belongs to the scheduled job; this endpoint is scoped like the dashboard
    button.
    """
    facility = current_facility()
    if facility is None:
        return jsonify({"error": "sign in with a facility account to run matching"}), 401

    if not consume("api_match_run", 10, 60, identity=facility.id):
        return jsonify({"error": "too many matching passes, wait a minute"}), 429

    created = run_matching_pass(donor_facility_id=facility.id)
    return jsonify({"matches_created": len(created), "matches": [m.to_dict() for m in created]})


@api_bp.route("/cron/maintenance", methods=["GET", "POST"])
def cron_maintenance():
    """Scheduled job: flag expired stock, then run the network matching pass.

    Called by Vercel Cron (see vercel.json). Safe to call by hand or repeatedly.
    """
    if not _cron_authorized():
        return jsonify({"error": "unauthorized"}), 403

    expired, created = run_maintenance()
    return jsonify({
        "expired_flagged": [
            {
                "id": donation.id,
                "item_name": donation.item_name,
                "quantity": donation.quantity,
                "unit": donation.unit,
                "facility": donation.facility.name if donation.facility else None,
            }
            for donation in expired
        ],
        "matches_created": len(created),
        "matches": [match.to_dict() for match in created],
    })
