from flask import Blueprint, flash, redirect, url_for

from app.models import Match
from app.services.matching import change_match_status

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/matches/<int:match_id>/<action>", methods=["POST"])
def set_status(match_id, action):
    """Accept, decline or complete a proposed match."""
    match = Match.query.get_or_404(match_id)
    ok, message = change_match_status(match, action)
    flash(message, "success" if ok else "error")
    return redirect(url_for("main.dashboard"))
