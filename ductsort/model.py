"""Shared, trade-agnostic helpers: number coercion, size normalization, floor
ordering, the aggregatable measure keys, and value/column formatting.

Trade-specific vocabulary (column maps, report columns, KPIs) lives in
``trades.py``. Everything here is deterministic.
"""
from __future__ import annotations

import re


# The aggregatable measures every rollup sums. Per-line attributes used only on
# plumbing detail rows (list_price, discount, net_price, lab_per_unit) are NOT
# here because they do not sum meaningfully.
MEASURE_KEYS = ("material_cost", "labour_hrs", "weight", "area", "length",
                "qty", "labour_cost")


def num(v) -> float:
    """Coerce a cell to a number; blanks / text become 0."""
    return float(v) if isinstance(v, (int, float)) else 0.0


# ----------------------------------------------------------------- size tidy-up
_CALCLEN = re.compile(r",\s*CalcLen", re.IGNORECASE)
_X = re.compile(r"\s*[xX]\s*")


def normalize_size(raw) -> str:
    """Clean a raw Size label for grouping in the By Size view.

    Strips a trailing ", CalcLen", collapses a transition label
    ("1000 x 1050, 750 x 400") to its primary size, and normalises spacing
    around the x. Round duct sizes ("300") and pipe sizes ("1/2", "2") pass
    through apart from whitespace.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    s = _CALCLEN.sub("", s)
    s = s.split(",")[0].strip()       # primary size of a transition
    s = _X.sub(" x ", s)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------- sort keys
_FLOOR_ORDER = [
    "footing", "foundation", "sub-basement", "subbasement", "cellar",
    "basement", "lower level", "ground", "main",
]
_FLOOR_TAIL = ["roof", "penthouse", "mezzanine"]


def floor_sort_key(name) -> tuple:
    """Order floors: known lows first, then numbered levels, then roof/PH."""
    s = (str(name) if name is not None else "").strip()
    low = s.lower()
    for i, token in enumerate(_FLOOR_ORDER):
        if token in low:
            return (0, i, low)
    m = re.search(r"(\d+)", s)
    if m and ("level" in low or "floor" in low or "fl" in low or "lvl" in low
              or re.fullmatch(r"\D*\d+\D*", s)):
        return (1, int(m.group(1)), low)
    for i, token in enumerate(_FLOOR_TAIL):
        if token in low:
            return (3, i, low)
    return (2, 0, low)


# ------------------------------------------------------------- formatting
def column_header(col: dict, unit_labels: dict | None = None) -> str:
    """Header text for a column, appending its unit label when applicable
    (e.g. Weight -> "Weight (kg)")."""
    header = col["header"]
    unit = col.get("unit")
    if unit and unit_labels and unit_labels.get(unit):
        return f"{header} ({unit_labels[unit]})"
    return header


def fmt_value(kind: str, value) -> str:
    """Format a measure for plain-text / PDF / KPI output."""
    if value is None:
        return ""
    if kind == "money":
        return f"${value:,.0f}"
    if kind == "money2":
        return f"${value:,.2f}"
    if kind == "hrs":
        return f"{value:,.1f}"
    if kind == "hrs0":
        return f"{value:,.0f}"
    if kind == "rate":
        return f"{value:,.2f}"
    if kind == "qty":
        return f"{value:,.1f}" if value % 1 else f"{value:,.0f}"
    if kind == "pct":
        return f"{value * 100:,.1f}%"
    return f"{value:,.0f}"
