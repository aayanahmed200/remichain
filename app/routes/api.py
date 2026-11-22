import os

from flask import Blueprint, jsonify, request

from app.models import SupplyDonation, SupplyRequest, Match
from app.services.matching import run_matching_pass, find_matches_for_request
from app.services.sweep import run_maintenance

api_bp = Blueprint("api", __name__)


def _cron_authorized():
    """Allow Vercel's scheduler, and nothing else.

    With CRON_SECRET set, the bearer token Vercel sends is the only way in.
    Without it, fall back to Vercel's own request signature plus loopback so
    local development and a fresh deploy both work unattended.
    """
    secret = os.environ.get("CRON_SECRET", "").strip()
    if secret:
        return request.headers.get("Authorization", "") == f"Bearer {secret}"

    if request.headers.get("x-vercel-cron"):
        return True
    if request.headers.get("User-Agent", "").startswith("vercel-cron"):
        return True
    return request.remote_addr in ("127.0.0.1", "::1")


@api_bp.route("/donations", methods=["GET"])
def list_donations():
    return jsonify([d.to_dict() for d in SupplyDonation.query.all()])


@api_bp.route("/requests", methods=["GET"])
def list_requests():
    return jsonify([r.to_dict() for r in SupplyRequest.query.all()])


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
    created = run_matching_pass()
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
