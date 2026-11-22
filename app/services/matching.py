"""
Matching engine for RemiChain.

Pairs surplus medical supply donations with open requests using a weighted
score built from:
  - urgency of the requesting facility
  - how soon the donated item expires (use-it-or-lose-it priority)
  - geographic proximity between donor and recipient
  - how well the offered quantity covers the need

This is intentionally readable over clever: hackathon judges and future
contributors should be able to follow the scoring logic without a math degree.
"""

from datetime import date
from math import ceil, radians, sin, cos, sqrt, atan2

from flask import current_app

from app import db
from app.models import SupplyDonation, SupplyRequest, Match
from app.services.catalog import base_quantity, catalog_item_for, items_pair


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometers."""
    if None in (lat1, lon1, lat2, lon2):
        return None

    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def _expiry_urgency(donation):
    """Higher score = the donated item needs to move soon (or never expires)."""
    if donation.expiry_date is None:
        return 0.5  # durable equipment: mild priority, no rush
    days_left = (donation.expiry_date - date.today()).days
    if days_left <= 0:
        return 0.0  # already expired, should not be matched
    if days_left <= 14:
        return 1.0
    if days_left <= 60:
        return 0.6
    return 0.3


def _proximity_score(donation, req):
    donor = donation.facility
    recipient = req.facility
    dist = haversine_km(donor.latitude, donor.longitude, recipient.latitude, recipient.longitude)
    if dist is None:
        return 0.3  # unknown location: neutral-low score
    if dist <= 25:
        return 1.0
    if dist <= 100:
        return 0.7
    if dist <= 500:
        return 0.4
    return 0.15


def score_pair(donation: SupplyDonation, req: SupplyRequest, cfg) -> float:
    """Weighted score for how good a donation-to-request match is. Higher is better."""
    donation_item = catalog_item_for(donation.item_name, donation.category)
    request_item = catalog_item_for(req.item_name, req.category)
    if not items_pair(
        donation_item, request_item, donation.item_name, req.item_name
    ):
        return -1.0  # not the same item
    if (donation.expiry_date and donation.expiry_date <= date.today()) or req.quantity_needed <= 0 or donation.quantity <= 0:
        return -1.0  # never match expired, non-positive, or malformed stock/request (avoid ZeroDivisionError below)

    urgency = req.urgency_score / 4.0  # normalize 0-1
    expiry = _expiry_urgency(donation)
    proximity = _proximity_score(donation, req)
    # Coverage is compared in catalogue base units, so "2 boxes" of 100 masks
    # covers a need for "50 masks". Weights themselves are unchanged.
    donation_units = donation.quantity * base_quantity(donation_item, donation.unit)
    needed_units = req.quantity_needed * base_quantity(request_item, req.unit)
    coverage = min(donation_units / needed_units, 1.0)

    return (
        cfg.get("URGENCY_WEIGHT", 3.0) * urgency
        + cfg.get("EXPIRY_WEIGHT", 2.0) * expiry
        + cfg.get("PROXIMITY_WEIGHT", 1.5) * proximity
        + cfg.get("QUANTITY_WEIGHT", 1.0) * coverage
    )


def find_matches_for_request(req: SupplyRequest, limit=5, donation_facility_id=None):
    """Return the best-scoring available donations for a given request.

    `donation_facility_id` narrows the donor pool to one facility's stock, which
    is what a signed-in facility's "run matching" button does: it only ever
    proposes pairings from its own surplus.
    """
    query = SupplyDonation.query.filter_by(status="available")
    if donation_facility_id is not None:
        query = query.filter(SupplyDonation.facility_id == donation_facility_id)
    candidates = query.all()
    cfg = current_app.config
    scored = [(d, score_pair(d, req, cfg)) for d in candidates]
    scored = [(d, s) for d, s in scored if s > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def create_match(donation: SupplyDonation, req: SupplyRequest, score: float):
    """Create a Match, then take the donation/request out of the matching pool.

    Without this, `donation.status` and `req.status` would stay "available"
    and "open"/"partially_fulfilled" forever, so a repeated matching pass
    (re-triggered, or run on a schedule) would keep proposing the very same
    pairing and pile up duplicate Match rows. Updating the statuses here —
    the single place every match is created, whether from run_matching_pass()
    or the immediate on-submit match in routes/requests.py — is what makes
    matching idempotent.

    Returns the created Match, or None if a concurrent call already claimed
    this donation first (see the atomic update below) — callers should treat
    a None return as "no match created this time" rather than an error.
    """
    # Work out how much of the donation to take, in the donation's own unit.
    donation_item = catalog_item_for(donation.item_name, donation.category)
    request_item = catalog_item_for(req.item_name, req.category)
    donor_factor = base_quantity(donation_item, donation.unit)
    need_factor = base_quantity(request_item, req.unit)

    needed_base = req.quantity_needed * need_factor
    available_base = donation.quantity * donor_factor
    take_base = min(available_base, needed_base)

    if take_base >= available_base:
        matched_qty = donation.quantity
    else:
        # Packs are indivisible: covering 50 tablets from a box of 100 takes
        # the whole box, never half of one.
        matched_qty = min(donation.quantity, max(1, ceil(take_base / donor_factor)))

    # Atomic check-and-decrement, not a plain `donation.quantity -= matched_qty`
    # in Python: this makes the claim race-safe. Two concurrent matching
    # attempts against the same donation can both read the same pre-update
    # quantity, but only one of these UPDATEs will find the row still
    # `status="available"` with enough quantity left and actually apply —
    # the loser gets 0 affected rows back and bails out below instead of
    # silently over-committing stock that's already spoken for.
    updated_rows = (
        db.session.query(SupplyDonation)
        .filter(
            SupplyDonation.id == donation.id,
            SupplyDonation.status == "available",
            SupplyDonation.quantity >= matched_qty,
        )
        .update(
            {SupplyDonation.quantity: SupplyDonation.quantity - matched_qty},
            synchronize_session=False,
        )
    )
    if not updated_rows:
        db.session.rollback()
        return None  # someone else already matched this donation first

    db.session.refresh(donation)

    # Only the remainder matters now: a partially-claimed donation stays
    # "available" (with its reduced quantity) so the rest of it can still be
    # matched against other requests; it's only pulled out of the pool once
    # nothing is left.
    if donation.quantity <= 0:
        donation.status = "reserved"

    match = Match(
        donation_id=donation.id,
        request_id=req.id,
        score=score,
        matched_quantity=matched_qty,
        status="proposed",
    )
    db.session.add(match)

    # A request is only done once a match covers its whole need. Otherwise it
    # stays "partially_fulfilled", which run_matching_pass (and the dashboard
    # stats) already treat as still open for matching, so a later pass can
    # top it up from a different donation without re-touching this one.
    req.status = (
        "fulfilled" if matched_qty * donor_factor >= needed_base else "partially_fulfilled"
    )

    db.session.commit()
    return match


def run_matching_pass(donor_facility_id=None):
    """Batch job: scan every open request and propose the best match, if any.

    Pass `donor_facility_id` to match only one facility's surplus (the scoped
    dashboard pass); leave it None for the network-wide pass.


    Safe to call repeatedly (re-triggered by a user, retried, or run on a
    schedule): requests are only selected here while still "open" or
    "partially_fulfilled", donations are only offered by find_matches_for_request
    while still "available", and create_match() moves both out of those pools
    as soon as they're matched — so a second pass with no new donations or
    requests in between creates zero additional matches instead of duplicates.
    """
    created = []
    open_requests = SupplyRequest.query.filter(
        SupplyRequest.status.in_(["open", "partially_fulfilled"])
    ).all()

    for req in open_requests:
        best = find_matches_for_request(req, limit=1, donation_facility_id=donor_facility_id)
        if best:
            donation, score = best[0]
            match = create_match(donation, req, score)
            if match:
                created.append(match)

    return created


MATCH_ACTIONS = {"accept": "accepted", "decline": "rejected", "complete": "completed"}


def change_match_status(match, action):
    """Accept, decline or complete a proposed match.

    Declining releases the reserved quantity back to the donation and reopens
    the request, so a match never permanently removes stock from the pool.
    Returns (ok, message) for the caller to flash.
    """
    new_status = MATCH_ACTIONS.get(action)
    if new_status is None:
        return False, "Unknown match action."

    if action == "accept":
        if match.status != "proposed":
            return False, "Only proposed matches can be accepted."
        match.status = "accepted"
        db.session.commit()
        donor = match.donation.facility.name if match.donation.facility else "the donor"
        return True, f"Match #{match.id} accepted — arrange pickup with {donor}."

    if action == "complete":
        if match.status not in ("proposed", "accepted"):
            return False, "Only open matches can be completed."
        match.status = "completed"
        match.donation.status = "delivered"
        db.session.commit()
        return True, f"Match #{match.id} marked complete."

    if action == "decline":
        if match.status not in ("proposed", "accepted"):
            return False, "Only open matches can be declined."
        donation, req = match.donation, match.request
        donation.quantity += match.matched_quantity
        donation.status = "available"
        match.status = "rejected"
        still_open = any(
            other.status in ("proposed", "accepted")
            for other in req.matches
            if other.id != match.id
        )
        req.status = "partially_fulfilled" if still_open else "open"
        db.session.commit()
        return True, (
            f"Match #{match.id} declined — {match.matched_quantity} {donation.unit} "
            "returned to available stock."
        )

    return False, "Nothing changed."
