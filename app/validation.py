"""Input limits shared by the form routes.

Column widths live here as well, so a value that passes validation is always
short enough for the database instead of failing at commit time.
"""

MAX_ITEM_NAME = 150
MAX_CATEGORY = 80
MAX_UNIT = 30
MAX_NOTES = 2000
MAX_NAME = 150
MAX_CITY = 100
MAX_COUNTRY = 100
MAX_EMAIL = 150
MAX_PASSWORD = 200
MAX_QUANTITY = 1_000_000

FACILITY_TYPES = ("hospital", "clinic", "pharmacy", "ngo")
CATEGORIES = ("medication", "ppe", "equipment", "consumable")
CONDITIONS = ("new", "like_new", "used_functional")
URGENCIES = ("low", "medium", "high", "critical")


def trimmed(raw, limit):
    """Strip a submitted value and report whether it exceeded the limit.

    Returns (value, too_long). The value is cut at the limit so nothing that
    overflows a column ever reaches the database.
    """
    value = (raw or "").strip()
    return value[:limit], len(value) > limit


def whole_number(raw, low, high):
    """Parse a positive whole number within range. Returns (value, error)."""
    text = (raw or "").strip()
    if not text.isdigit():
        return None, f"Enter a whole number between {low:,} and {high:,}."
    value = int(text)
    if not low <= value <= high:
        return None, f"Enter a whole number between {low:,} and {high:,}."
    return value, None
