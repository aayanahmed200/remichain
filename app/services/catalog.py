"""Item catalogue: names, aliases and unit conversion.

Free-text item names are resolved to a catalogue item before matching, so
"N95 masks" and "Surgical masks N95" pair while "Amoxicillin 500mg" and
"Amoxicillin 250mg" still do not.

Resolution order for a name:
  1. exact hit on a normalised alias (case, punctuation and word order ignored)
  2. token match against aliases: one name's words contained in the other's,
     or 60%+ word overlap, with numeric tokens required to agree exactly
  3. nothing — callers then fall back to direct name comparison

Quantities are compared in catalogue base units ("mask", "tablet", "bag"):
a quantity in "boxes" is multiplied by that item's pack size first.
"""

import re
import unicodedata

from flask import g

from app import db
from app.models import CatalogItem, ItemAlias, UnitConversion

STOPWORDS = {"a", "an", "the", "of", "and", "for", "with", "x"}

# Plurals we care about for units; name tokens go through the same helper.
DEFAULT_PACK_SIZES = {"dozen": 12.0, "unit": 1.0, "piece": 1.0, "pair": 2.0}


def _singular(token):
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith(("ses", "xes", "zes", "ches", "shes")) and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def tokens(text):
    """Normalised word list for a free-text name, in the order written."""
    text = unicodedata.normalize("NFKD", text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [_singular(part) for part in text.split() if part not in STOPWORDS]


def normalize_key(text):
    """Order-insensitive identity for a name: "N95 masks" and "masks n95"."""
    return " ".join(sorted(tokens(text)))


def normalize_unit(unit):
    return _singular((unit or "").strip().lower())


def _numeric(parts):
    return {part for part in parts if any(char.isdigit() for char in part)}


def names_align(left, right):
    """Do two free-text names look like the same item?"""
    left_tokens, right_tokens = tokens(left), tokens(right)
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True

    # Strengths and sizes are meaningful: 500mg must not pair with 250mg, and
    # a bare "amoxicillin" must not silently stand in for a specific dose.
    if _numeric(left_tokens) != _numeric(right_tokens):
        return False

    left_set, right_set = set(left_tokens), set(right_tokens)
    smaller, larger = sorted((left_set, right_set), key=len)
    if smaller <= larger:
        return True

    return len(left_set & right_set) / len(left_set | right_set) >= 0.6


def _cache():
    """Per-request memo; a matching pass resolves the same names repeatedly."""
    if not hasattr(g, "_catalog_cache"):
        g._catalog_cache = {"names": {}, "aliases": None, "packs": {}}
    return g._catalog_cache


def catalog_item_for(name, category=None, create=False):
    """The catalogue item a free-text name refers to, or None."""
    key = normalize_key(name)
    if not key:
        return None

    cache = _cache()
    if key in cache["names"]:
        return cache["names"][key]

    item = (
        CatalogItem.query.join(ItemAlias, ItemAlias.catalog_item_id == CatalogItem.id)
        .filter(ItemAlias.normalized == key)
        .first()
    )

    if item is None:
        if cache["aliases"] is None:
            cache["aliases"] = (
                CatalogItem.query.join(
                    ItemAlias, ItemAlias.catalog_item_id == CatalogItem.id
                )
                .order_by(CatalogItem.id)
                .all()
            )
        for candidate in cache["aliases"]:
            if any(names_align(name, alias.alias) for alias in candidate.aliases):
                item = candidate
                break

    if item is None and create:
        item = CatalogItem(
            name=" ".join(name.split())[:150],
            key=key,
            category=(category or "other")[:80],
            base_unit="unit",
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(ItemAlias(catalog_item_id=item.id, alias=item.name, normalized=key))
        db.session.commit()
        if cache["aliases"] is not None:
            cache["aliases"].append(item)

    cache["names"][key] = item
    return item


def items_pair(donation_item, request_item, donation_name, request_name):
    """True when a donation and a request refer to the same catalogue item."""
    if donation_item is not None and request_item is not None:
        return donation_item.id == request_item.id
    # Unknown to the catalogue: fall back to name comparison so a brand-new
    # pair still matches when the words really are the same.
    return normalize_key(donation_name) == normalize_key(request_name)


def base_quantity(catalog_item, unit):
    """How many base units one `unit` of this item holds (1.0 when unknown)."""
    if catalog_item is None:
        return 1.0

    key = normalize_unit(unit)
    if not key:
        return 1.0

    cache = _cache()["packs"]
    cache_key = (catalog_item.id, key)
    if cache_key in cache:
        return cache[cache_key]

    conversion = UnitConversion.query.filter_by(
        catalog_item_id=catalog_item.id, unit=key
    ).first()
    factor = conversion.per_base if conversion else DEFAULT_PACK_SIZES.get(key, 1.0)
    cache[cache_key] = factor
    return factor


SEED_ITEMS = [
    {
        "name": "N95 respirator mask",
        "category": "ppe",
        "base_unit": "mask",
        "aliases": [
            "N95 masks",
            "N95 mask",
            "N95 respirator",
            "N95 respirators",
            "Surgical masks N95",
            "Surgical mask N95",
            "respirator mask",
        ],
        "packs": {"box": 20, "pack": 10, "carton": 200},
    },
    {
        "name": "Surgical mask",
        "category": "ppe",
        "base_unit": "mask",
        "aliases": ["Surgical masks", "Face mask", "Medical mask", "3-ply mask"],
        "packs": {"box": 50, "pack": 10, "carton": 500},
    },
    {
        "name": "Nitrile examination gloves",
        "category": "ppe",
        "base_unit": "glove",
        "aliases": ["Nitrile gloves", "Exam gloves", "Examination gloves", "Gloves"],
        "packs": {"box": 100, "pack": 20, "carton": 1000},
    },
    {
        "name": "Disposable syringe 5ml",
        "category": "consumable",
        "base_unit": "syringe",
        "aliases": ["Syringe", "Syringes", "5ml syringe", "Disposable syringe"],
        "packs": {"box": 100, "pack": 20},
    },
    {
        "name": "Amoxicillin 500mg",
        "category": "medication",
        "base_unit": "capsule",
        "aliases": ["Amoxicillin", "Amoxicillin 500 mg", "Amox 500"],
        "packs": {"strip": 10, "box": 100, "blister": 10},
    },
    {
        "name": "Paracetamol 500mg",
        "category": "medication",
        "base_unit": "tablet",
        "aliases": ["Paracetamol", "Acetaminophen", "Paracetamol 500 mg"],
        "packs": {"strip": 10, "box": 100, "blister": 10},
    },
    {
        "name": "Normal saline 500ml",
        "category": "consumable",
        "base_unit": "bag",
        "aliases": ["Saline", "Normal saline", "Saline 500 ml", "IV saline"],
        "packs": {"box": 20, "carton": 100},
    },
    {
        "name": "Insulin vial",
        "category": "medication",
        "base_unit": "vial",
        "aliases": ["Insulin", "Insulin vials", "Human insulin"],
        "packs": {"box": 10, "pack": 5},
    },
    {
        "name": "Sterile gauze pad",
        "category": "consumable",
        "base_unit": "piece",
        "aliases": ["Gauze", "Gauze pads", "Sterile gauze"],
        "packs": {"pack": 10, "box": 100},
    },
    {
        "name": "Oxygen cylinder",
        "category": "equipment",
        "base_unit": "cylinder",
        "aliases": ["Oxygen cylinders", "O2 cylinder", "Oxygen tank"],
        "packs": {},
    },
]


def seed_catalog():
    """Create the starter catalogue once; later names join it on posting."""
    if CatalogItem.query.first() is not None:
        return

    for entry in SEED_ITEMS:
        item = CatalogItem(
            name=entry["name"],
            key=normalize_key(entry["name"]),
            category=entry["category"],
            base_unit=entry["base_unit"],
        )
        db.session.add(item)
        db.session.flush()

        for alias in [entry["name"], *entry["aliases"]]:
            key = normalize_key(alias)
            if not key:
                continue
            exists = ItemAlias.query.filter_by(normalized=key).first()
            if exists:
                continue
            db.session.add(ItemAlias(catalog_item_id=item.id, alias=alias, normalized=key))

        for unit, per_base in entry["packs"].items():
            db.session.add(
                UnitConversion(
                    catalog_item_id=item.id,
                    unit=normalize_unit(unit),
                    per_base=float(per_base),
                )
            )

    db.session.commit()
