"""Generic group-by / rollup engine.

One code path computes every view (the Floor -> System -> Size hierarchy and
the flat By Spec/Gauge, By Size, By Drawing tables), so totals are derived a
single way and always reconcile to the same grand total.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Sequence

from .model import MEASURE_KEYS


def blank() -> dict:
    return {k: 0.0 for k in MEASURE_KEYS}


def total(records: Sequence[dict]) -> dict:
    """Sum every measure across a set of records."""
    acc = blank()
    for r in records:
        for k in MEASURE_KEYS:
            acc[k] += r.get(k, 0.0) or 0.0
    return acc


def add_percentages(measures: dict, grand: dict) -> dict:
    """Return a copy of `measures` with mat_pct / lab_pct vs the grand total."""
    out = dict(measures)
    gm = grand.get("material_cost", 0.0) or 0.0
    gl = grand.get("labour_hrs", 0.0) or 0.0
    out["mat_pct"] = (measures["material_cost"] / gm) if gm else 0.0
    out["lab_pct"] = (measures["labour_hrs"] / gl) if gl else 0.0
    return out


def rollup(records: Sequence[dict], dims: Sequence[str],
           sorters: Sequence[Callable[[dict], object] | None] | None = None) -> list[dict]:
    """Group records by `dims` into an ordered tree.

    Each node is ``{"key", "totals", "records", "children"}``. `children` is a
    list of child nodes (next dim) or ``None`` at the leaf level.

    `sorters` is an optional list parallel to `dims`; entry i is a key function
    applied to each node at that level. ``None`` (the default at every level)
    sorts by Material $ descending, which puts the biggest scope first.
    """
    return _rollup(list(records), list(dims), list(sorters or []), 0)


def _rollup(records, dims, sorters, depth):
    if not dims:
        return None
    key = dims[0]
    buckets: "OrderedDict[object, list]" = OrderedDict()
    for r in records:
        buckets.setdefault(r.get(key, ""), []).append(r)

    nodes = []
    for kval, recs in buckets.items():
        nodes.append({
            "key": kval,
            "totals": total(recs),
            "records": recs,
            "children": _rollup(recs, dims[1:], sorters, depth + 1),
        })

    sorter = sorters[depth] if depth < len(sorters) else None
    if sorter is None:
        nodes.sort(key=lambda n: n["totals"]["material_cost"], reverse=True)
    else:
        nodes.sort(key=sorter)
    return nodes
