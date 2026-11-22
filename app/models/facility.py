from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class Facility(db.Model):
    """A hospital, clinic, pharmacy, or NGO that can donate or request medical supplies."""

    __tablename__ = "facilities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    facility_type = db.Column(db.String(50), nullable=False)  # hospital, clinic, ngo, pharmacy
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    contact_email = db.Column(db.String(150), nullable=True)
    # Null until the facility claims its row or registers an account; rows
    # without one can be claimed once, and never again after that.
    password_hash = db.Column(db.String(255), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    donations = db.relationship("SupplyDonation", backref="facility", lazy=True)
    requests = db.relationship("SupplyRequest", backref="facility", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    @property
    def has_account(self):
        return bool(self.password_hash)

    def __repr__(self):
        return f"<Facility {self.name} ({self.city}, {self.country})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "facility_type": self.facility_type,
            "city": self.city,
            "country": self.country,
            "verified": self.verified,
        }
