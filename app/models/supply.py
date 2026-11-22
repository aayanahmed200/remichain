from datetime import datetime, timezone

from app import db


class SupplyDonation(db.Model):
    """Surplus medical supplies offered by a facility."""

    __tablename__ = "supply_donations"

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False)

    item_name = db.Column(db.String(150), nullable=False)  # e.g. "Insulin", "N95 Masks"
    category = db.Column(db.String(80), nullable=False)  # medication, PPE, equipment, consumable
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(30), default="units")

    expiry_date = db.Column(db.Date, nullable=True)  # null for durable equipment
    condition = db.Column(db.String(30), default="new")  # new, like_new, used_functional

    # available, reserved, delivered, expired
    status = db.Column(db.String(20), default="available")
    # Set by the scheduled sweep when the expiry date passes; shown to the
    # donor so stock is flagged rather than silently dropped from matching.
    expired_flagged_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "facility_id": self.facility_id,
            "item_name": self.item_name,
            "category": self.category,
            "quantity": self.quantity,
            "unit": self.unit,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "condition": self.condition,
            "status": self.status,
            "expired_flagged_at": (
                self.expired_flagged_at.isoformat() if self.expired_flagged_at else None
            ),
        }
