from flask import Blueprint, flash, redirect, url_for

from app.auth import current_facility, login_required, owns_match
from app.models import Match
from app.services.matching import change_match_status

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/matches/<int:match_id>/<action>", methods=["POST"])
@login_required
def set_status(match_id, action):
    """Accept, decline or complete a match that involves this facility."""
    facility = current_facility()
    match = Match.query.get_or_404(match_id)

    # A match belongs to its donor and its recipient, nobody else. Without this
    # check any signed-in facility could move another pair's stock.
    if not owns_match(facility, match):
        flash(f"Match #{match.id} is not yours to action.", "error")
        return redirect(url_for("main.dashboard"))

    ok, message = change_match_status(match, action)
    flash(message, "success" if ok else "error")
    return redirect(url_for("main.dashboard"))
