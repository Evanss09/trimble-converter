"""Prepare every report view from the raw records, driven by the trade profile.

The Excel and PDF renderers consume the structures built here, so the two
deliverables always agree and every breakdown reconciles to one grand total.
"""
from __future__ import annotations

from . import aggregate, model


def has_floor(records) -> bool:
    """True if any record carries a real floor (not blank / "(no floor)")."""
    return any(str(r.get("floor", "")).strip() not in ("", "(no floor)") for r in records)


def has_source(records) -> bool:
    return len({r.get("source") for r in records if r.get("source")}) > 1


def _system_rank(records) -> dict:
    by_sys = aggregate.rollup(records, ["system"])   # sorted material desc
    return {n["key"]: i for i, n in enumerate(by_sys)}


def _sorter_for(dim, sys_rank):
    if dim == "floor":
        return lambda n: model.floor_sort_key(n["key"])
    if dim == "system":
        return lambda n: sys_rank.get(n["key"], 10_000)
    if dim == "size_norm":
        return lambda n: min((str(r.get("sorted_size") or "") for r in n["records"]), default="")
    return None   # default: Material $ desc


def build(records: list[dict], profile, unit_labels: dict) -> dict:
    """Return prepared views (hierarchy + flat breakdowns) and KPIs for a trade."""
    grand = aggregate.total(records)
    sys_rank = _system_rank(records)
    floored = has_floor(records)

    hierarchy_dims = list(profile.hierarchy)
    if profile.floor_aware and floored and "floor" not in hierarchy_dims:
        hierarchy_dims = ["floor"] + hierarchy_dims

    sorters = [_sorter_for(d, sys_rank) for d in hierarchy_dims]
    hierarchy = aggregate.rollup(records, hierarchy_dims, sorters)

    flats = []
    if floored:
        flats.append({"title": "By Floor", "tab": "By Floor", "dim": "floor",
                      "kind": "floor", "nodes": aggregate.rollup(
                          records, ["floor"], [_sorter_for("floor", sys_rank)])})
    for f in profile.flats:
        flats.append({"title": f["title"], "tab": f["tab"], "dim": f["dim"],
                      "kind": f["kind"], "nodes": aggregate.rollup(
                          records, [f["dim"]], [_sorter_for(f["dim"], sys_rank)])})
    if has_source(records):
        flats.append({"title": "By Source / Area", "tab": "By Source", "dim": "source",
                      "kind": "source", "nodes": aggregate.rollup(records, ["source"])})

    area = grand["area"] or 0.0
    hrs = grand["labour_hrs"] or 0.0
    kpis = {
        "material_cost": grand["material_cost"], "labour_hrs": grand["labour_hrs"],
        "weight": grand["weight"], "area": grand["area"], "qty": grand["qty"],
        "labour_cost": grand["labour_cost"],
        "dollar_per_area": (grand["material_cost"] / area) if area else 0.0,
        "hrs_per_area": (grand["labour_hrs"] / area) if area else 0.0,
        "dollar_per_hour": (grand["material_cost"] / hrs) if hrs else 0.0,
        "line_count": len(records),
    }

    return {
        "grand": grand, "kpis": kpis,
        "hierarchy": hierarchy, "hierarchy_dims": hierarchy_dims,
        "flats": flats,
    }


_BLANK_LABELS = {
    "size": "(no size)", "floor": "(no floor)", "system": "(no system)",
    "spec": "(no spec)", "drawing": "(no drawing)", "trade": "(no trade)",
    "item_type": "(no item type)", "source": "(no source)",
}


def label(value, kind: str = "") -> str:
    """Display label for a group key, substituting friendly text for blanks."""
    s = "" if value is None else str(value).strip()
    return s if s else _BLANK_LABELS.get(kind, "(blank)")
