from datetime import datetime, timezone

from app import db


class CatalogItem(db.Model):
    """One real-world supply, whatever people happen to call it.

    The catalogue is what turns "N95 masks", "N95 respirator" and "surgical
    masks N95" into the same thing, so matching compares items rather than
    strings.
    """

    __tablename__ = "catalog_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)  # canonical display name
    # Normalised, sorted tokens. Unique so one item owns one spelling family.
    key = db.Column(db.String(200), nullable=False, unique=True, index=True)
    category = db.Column(db.String(80), nullable=False)
    # What quantities are counted in once units are converted, e.g. "mask",
    # "tablet", "bag". Conversions in UnitConversion translate packs into this.
    base_unit = db.Column(db.String(30), nullable=False, default="unit")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    aliases = db.relationship(
        "ItemAlias", backref="catalog_item", lazy=True, cascade="all, delete-orphan"
    )
    conversions = db.relationship(
        "UnitConversion", backref="catalog_item", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CatalogItem {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "base_unit": self.base_unit,
            "aliases": [alias.alias for alias in self.aliases],
            "packs": {c.unit: c.per_base for c in self.conversions},
        }


class ItemAlias(db.Model):
    """A spelling someone actually types, mapped to a catalogue item."""

    __tablename__ = "item_aliases"

    id = db.Column(db.Integer, primary_key=True)
    catalog_item_id = db.Column(
        db.Integer, db.ForeignKey("catalog_items.id"), nullable=False, index=True
    )
    alias = db.Column(db.String(150), nullable=False)
    normalized = db.Column(db.String(200), nullable=False, unique=True, index=True)


class UnitConversion(db.Model):
    """How many base units one pack unit holds, for a given item.

    Per item rather than global, because a box of masks and a box of
    amoxicillin hold very different numbers of things.
    """

    __tablename__ = "unit_conversions"

    id = db.Column(db.Integer, primary_key=True)
    catalog_item_id = db.Column(
        db.Integer, db.ForeignKey("catalog_items.id"), nullable=False, index=True
    )
    unit = db.Column(db.String(30), nullable=False)  # normalised: "box", "strip"
    per_base = db.Column(db.Float, nullable=False)  # base units in one `unit`

    __table_args__ = (
        db.UniqueConstraint("catalog_item_id", "unit", name="uq_unit_conversion_item_unit"),
    )
