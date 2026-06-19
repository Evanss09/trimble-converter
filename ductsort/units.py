"""Detect a project's unit system and supply the right measure labels.

Trimble exports values already in the project's display units, but the export
carries no units flag. Metric and imperial projects are told apart by the
magnitude of the duct dimensions: metric duct is sized in millimetres (typically
100-2000+), imperial duct in inches (typically 4-60). So the median duct
dimension separates them cleanly. We relabel only; we never convert the numbers.
"""
from __future__ import annotations

import re
import statistics

# Label sets. `per_area` is appended to the $/area and hrs/area KPIs.
UNIT_SETS = {
    "imperial": {
        "system": "imperial",
        "weight": "lb", "length": "ft", "area": "ft²",
        "per_area": "/ft²", "size": "in",
        "display": "Imperial (in, lb, ft²)",
    },
    "metric": {
        "system": "metric",
        "weight": "kg", "length": "m", "area": "m²",
        "per_area": "/m²", "size": "mm",
        "display": "Metric (mm, kg, m²)",
    },
}

_DUCT_SHAPES = {"Rectangular", "Round", "Round-Rect", "Rect-Round"}
_METRIC_MEDIAN_THRESHOLD = 50.0   # mm sizes sit far above this; inch sizes below
_METRIC_WEIGHT_AREA_RATIO = 2.5   # kg/m2 (~4-12) vs lb/ft2 (~0.4-1.5) fallback


def _duct_dimensions(records) -> list[float]:
    """Leading dimension numbers from duct-shaped lines.

    Skips angle/CFM style sizes (tokens that carry a 'ga' gauge or a 'CFM'
    label) so they do not pollute the magnitude signal.
    """
    dims: list[float] = []
    for r in records:
        if r.get("shape") not in _DUCT_SHAPES:
            continue
        size = r.get("size")
        if not isinstance(size, str):
            continue
        primary = size.split(",")[0]
        if re.search(r"ga\b|CFM", primary, re.IGNORECASE):
            continue
        for tok in re.findall(r"\d+(?:\.\d+)?", primary):
            v = float(tok)
            if 0 < v < 100000:
                dims.append(v)
    return dims


def detect(records) -> str:
    """Return 'metric' or 'imperial' for a set of records."""
    dims = _duct_dimensions(records)
    if len(dims) >= 10:
        return "metric" if statistics.median(dims) >= _METRIC_MEDIAN_THRESHOLD else "imperial"

    # Fallback: weight-per-area ratio when there are too few sized duct lines.
    weight = sum((r.get("weight") or 0.0) for r in records)
    area = sum((r.get("area") or 0.0) for r in records)
    if area > 0:
        return "metric" if (weight / area) > _METRIC_WEIGHT_AREA_RATIO else "imperial"
    return "imperial"


def labels(system: str) -> dict:
    """Return the label set for a system name, defaulting to imperial."""
    return UNIT_SETS.get(system, UNIT_SETS["imperial"])


def resolve(records, units: str = "auto", has_area: bool = True) -> dict:
    """Resolve a units choice to a label set, trade-aware.

    `has_area=False` (plumbing) has no area/length, so the display string names
    only the weight unit. Detection still works: plumbing has no duct shapes so
    `detect` falls through to imperial unless the weight/area signal says metric.
    """
    system = detect(records) if units == "auto" else units
    out = dict(labels(system))
    if not has_area:
        out["display"] = "Metric (kg)" if system == "metric" else "Imperial (lb)"
    return out
