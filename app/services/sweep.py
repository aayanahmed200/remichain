"""Scheduled maintenance.

Two jobs run on the same timer:

1. Sweep expired stock — anything still "available" past its expiry date is
   taken out of the matching pool and flagged on the donor's dashboard. The
   row is kept (with its quantity and expiry) so the donor can see what went
   bad and the history stays intact; nothing is deleted behind their back.
2. Run the matching pass — the network-wide one, not a single facility's.

Both are idempotent: a flag is only set on stock still "available", and the
matching pass only proposes pairings for still-open requests and still-available
donations. Running this twice a day, or twice by accident, changes nothing the
second time.
"""

from datetime import date, datetime, timezone

from app import db
from app.models import SupplyDonation
from app.services.matching import change_match_status, run_matching_pass


def sweep_expired_stock(today=None):
    """Flag available stock whose expiry date has passed.

    Returns the donations flagged by this call (empty when nothing expired).
    """
    cutoff = today or date.today()
    now = datetime.now(timezone.utc)

    # "reserved" is stock fully committed to a proposed match that has not been
    # accepted yet — it is still expired stock, and the match below is declined
    # so the quantity comes back before the row is flagged.
    expired = SupplyDonation.query.filter(
        SupplyDonation.status.in_(("available", "reserved")),
        SupplyDonation.expiry_date.isnot(None),
        SupplyDonation.expiry_date <= cutoff,
    ).all()

    for donation in expired:
        # A proposed match sitting on this stock would let the recipient accept
        # supplies that have already expired. Decline it through the normal
        # path, which puts the quantity back and reopens the request, before
        # the donation itself is flagged.
        for match in list(donation.matches):
            if match.status == "proposed":
                change_match_status(match, "decline")

        donation.status = "expired"
        donation.expired_flagged_at = now

    if expired:
        db.session.commit()

    return expired


def run_maintenance():
    """Sweep first, then match, so expired stock is never proposed."""
    expired = sweep_expired_stock()
    created = run_matching_pass()
    return expired, created
