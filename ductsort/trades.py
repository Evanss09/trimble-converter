"""Trade profiles: how to read and present each Trimble export type.

A TradeProfile captures everything trade-specific in one place — the raw column
map, the measures, the report columns, the drill hierarchy, the flat breakdowns
and the KPI cards — so the reader, views and renderers stay generic. Two trades
ship today: sheet metal and plumbing. Add another by adding a profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .model import num


# --------------------------------------------------------------- column specs
# Each column: key (record/measure key), header, kind (text/PDF formatting),
# excel (number format), optional unit (label key appended to the header).

# Sheet metal — one column set drives both summary and the size-aggregated drill.
SM_COLUMNS = [
    {"key": "qty",           "header": "Qty",        "kind": "int",   "excel": "#,##0"},
    {"key": "length",        "header": "Length",     "kind": "int",   "excel": "#,##0", "unit": "length"},
    {"key": "weight",        "header": "Weight",     "kind": "int",   "excel": "#,##0", "unit": "weight"},
    {"key": "area",          "header": "Area",       "kind": "int",   "excel": "#,##0", "unit": "area"},
    {"key": "material_cost", "header": "Material $",  "kind": "money", "excel": "$#,##0"},
    {"key": "labour_hrs",    "header": "Labour Hrs",  "kind": "hrs",   "excel": "#,##0.0"},
    {"key": "mat_pct",       "header": "Mat %",       "kind": "pct",   "excel": "0.0%"},
    {"key": "lab_pct",       "header": "Lab %",       "kind": "pct",   "excel": "0.0%"},
]

# Plumbing — aggregated summary tables (By System / Trade / Drawing, group rows).
PL_SUMMARY_COLUMNS = [
    {"key": "material_cost", "header": "Material $",  "kind": "money", "excel": "$#,##0"},
    {"key": "mat_pct",       "header": "Mat %",       "kind": "pct",   "excel": "0.0%"},
    {"key": "labour_hrs",    "header": "Labour Hrs",  "kind": "hrs",   "excel": "#,##0.0"},
    {"key": "lab_pct",       "header": "Lab %",       "kind": "pct",   "excel": "0.0%"},
    {"key": "weight",        "header": "Weight",      "kind": "int",   "excel": "#,##0", "unit": "weight"},
]

# Plumbing — the drill sheet, where group rows show the overview measures and
# leaf rows show per-line pricing detail (boss's "dig into the system" view).
PL_DETAIL_COLUMNS = [
    {"key": "qty",           "header": "Qty",        "kind": "qty",    "excel": "#,##0.#", "line_only": True},
    {"key": "list_price",    "header": "Price/ea",   "kind": "money2", "excel": "$#,##0.00", "line_only": True},
    {"key": "discount",      "header": "Mult %",     "kind": "pct",    "excel": "0%",       "line_only": True},
    {"key": "net_price",     "header": "Net/ea",     "kind": "money2", "excel": "$#,##0.00", "line_only": True},
    {"key": "lab_per_unit",  "header": "Hrs/ea",     "kind": "rate",   "excel": "#,##0.00", "line_only": True},
    {"key": "material_cost", "header": "Material $",  "kind": "money", "excel": "$#,##0"},
    {"key": "labour_hrs",    "header": "Hours",       "kind": "hrs",   "excel": "#,##0.0"},
    {"key": "mat_pct",       "header": "Mat %",       "kind": "pct",   "excel": "0.0%", "group_only": True},
    {"key": "lab_pct",       "header": "Lab %",       "kind": "pct",   "excel": "0.0%", "group_only": True},
]


# ---------------------------------------------------------------- derive funcs
def _derive_sheet_metal(rec: dict) -> None:
    rec["material_cost"] = (num(rec.get("fab_cost")) + num(rec.get("purchase_cost"))
                            + num(rec.get("quote_cost")))
    # Field/install hours only. Shop (fabrication) hours are excluded: VR does
    # not make the material, and some exports carry shop hours while others do
    # not, so they must never count toward reported labour.
    rec["labour_hrs"] = num(rec.get("field_hrs")) + num(rec.get("field_hand_hrs"))
    rec["labour_cost"] = 0.0
    for k in ("qty", "length", "weight", "area"):
        rec[k] = num(rec.get(k))


def _derive_plumbing(rec: dict) -> None:
    rec["material_cost"] = num(rec.get("material_dollars"))
    rec["labour_hrs"] = num(rec.get("hours"))
    rec["labour_cost"] = num(rec.get("labor_dollars"))
    rec["weight"] = num(rec.get("weight"))
    rec["qty"] = num(rec.get("qty"))
    rec["length"] = 0.0
    rec["area"] = 0.0
    rec["list_price"] = num(rec.get("list_price"))
    rec["discount"] = num(rec.get("multiplier"))
    q = rec["qty"]
    rec["net_price"] = (rec["material_cost"] / q) if q else (rec["list_price"] * rec["discount"])
    rec["lab_per_unit"] = (rec["labour_hrs"] / q) if q else 0.0


# ----------------------------------------------------------------- KPI cards
# label may contain {weight}/{area}/{per_area} placeholders filled at render.
SM_KPIS = [
    {"key": "material_cost", "label": "Material",       "fmt": "money"},
    {"key": "labour_hrs",    "label": "Labour hrs",     "fmt": "hrs0"},
    {"key": "weight",        "label": "Weight ({weight})", "fmt": "int"},
    {"key": "area",          "label": "Area ({area})",  "fmt": "int"},
    {"key": "dollar_per_area", "label": "Material {per_area}", "fmt": "money2"},
]
PL_KPIS = [
    {"key": "material_cost", "label": "Material",        "fmt": "money"},
    {"key": "labour_hrs",    "label": "Labour hrs",      "fmt": "hrs0"},
    {"key": "weight",        "label": "Weight ({weight})", "fmt": "int"},
    {"key": "dollar_per_hour", "label": "Material $/hr", "fmt": "money2"},
]


@dataclass(frozen=True)
class TradeProfile:
    name: str                       # 'sheet_metal' | 'plumbing'
    label: str                      # 'Sheet Metal' | 'Plumbing'
    abbr: str                       # 'SM' | 'PL'  (Excel tab prefix)
    sheet_hints: tuple              # raw-sheet name substrings to prefer
    column_map: dict                # raw header -> record key
    distinguishing: tuple           # columns that mark this trade
    derive: Callable[[dict], None]
    has_area: bool
    detail_mode: str                # 'size_agg' | 'line_items'
    hierarchy: tuple                # base drill dims (floor prepended if present)
    floor_aware: bool               # prepend 'floor' to hierarchy when populated
    flats: tuple                    # ({title, dim, kind}, ...) extra flat tabs
    summary_columns: list           # cols for flat tabs + group rows
    detail_columns: list            # cols for the drill sheet
    kpis: list                      # KPI card specs


# --------------------------------------------------------------- sheet metal
_SM_COLUMN_MAP = {
    "Drawing": "drawing", "System": "system", "Specs": "specs", "Floor": "floor",
    "Zone": "zone", "SysSymbol": "sys_symbol", "Material": "material", "F/P/Q": "fpq",
    "Shape": "shape", "Report Section": "report_section", "SubSection": "subsection",
    "Item Type": "item_type", "Item Name": "item_name", "Size": "size",
    "Metal Thickness": "metal_thickness", "Quantity": "qty", "Length": "length",
    "Weight": "weight", "Weight w/waste": "weight_waste", "Area": "area",
    "Area w/waste": "area_waste", "Liner Type": "liner_type", "Unit Cost": "unit_cost",
    "Fab Cost": "fab_cost", "Purchase Cost": "purchase_cost", "Quote Cost": "quote_cost",
    "Adj Shop Hrs": "shop_hrs", "Adj Field Hrs": "field_hrs",
    "Adj Shop Hand Hrs": "shop_hand_hrs", "Adj Field Hand Hrs": "field_hand_hrs",
    "SortedSize": "sorted_size",
}

SHEET_METAL = TradeProfile(
    name="sheet_metal", label="Sheet Metal", abbr="SM",
    sheet_hints=("rawdatasm", "raw data"),
    column_map=_SM_COLUMN_MAP,
    distinguishing=("Area", "Shape", "Fab Cost"),
    derive=_derive_sheet_metal,
    has_area=True,
    detail_mode="size_agg",
    hierarchy=("floor", "system", "size_norm"),
    floor_aware=True,
    flats=(
        {"title": "By Spec / Gauge", "tab": "By Spec-Gauge", "dim": "specs", "kind": "spec"},
        {"title": "By Duct Size (all systems)", "tab": "By Size", "dim": "size_norm", "kind": "size"},
        {"title": "By Drawing", "tab": "By Drawing", "dim": "drawing", "kind": "drawing"},
    ),
    summary_columns=SM_COLUMNS,
    detail_columns=SM_COLUMNS,
    kpis=SM_KPIS,
)


# ------------------------------------------------------------------ plumbing
_PL_COLUMN_MAP = {
    "Drawing": "drawing", "System": "system", "Floor": "floor", "Zone": "zone",
    "Symbol": "symbol", "Phase": "phase", "Line": "line",
    "Material Spec": "material_spec", "Item Type": "item_type", "Report Cat": "report_cat",
    "Trade": "trade", "Material Description": "material_desc", "Item Name": "item_name",
    "Size": "size", "Quantity": "qty", "List Price": "list_price",
    "Multiplier ID": "mult_id", "Multipler Desc": "mult_desc", "Multiplier": "multiplier",
    "Material Dollars": "material_dollars", "Weight": "weight", "Hours": "hours",
    "Labor Dollars": "labor_dollars", "PriceCode": "price_code", "SortedSize": "sorted_size",
}

PLUMBING = TradeProfile(
    name="plumbing", label="Plumbing", abbr="PL",
    sheet_hints=("raw data", "rawdata"),
    column_map=_PL_COLUMN_MAP,
    distinguishing=("Material Dollars", "Hours", "Material Spec"),
    derive=_derive_plumbing,
    has_area=False,
    detail_mode="line_items",
    hierarchy=("system", "material_spec", "size_norm"),
    floor_aware=True,
    flats=(
        {"title": "By Trade", "tab": "By Trade", "dim": "trade", "kind": "trade"},
        {"title": "By Drawing", "tab": "By Drawing", "dim": "drawing", "kind": "drawing"},
    ),
    summary_columns=PL_SUMMARY_COLUMNS,
    detail_columns=PL_DETAIL_COLUMNS,
    kpis=PL_KPIS,
)

PROFILES = (SHEET_METAL, PLUMBING)

# Common header columns that identify a raw-data sheet of either trade.
COMMON_SIGNATURE = ("Drawing", "System", "Size", "Quantity")


def detect_trade(headers) -> TradeProfile | None:
    """Pick the trade profile for a set of header names, or None if neither."""
    names = {str(h).strip() for h in headers if h is not None}
    if "Area" in names or "Shape" in names or "Fab Cost" in names:
        return SHEET_METAL
    if "Material Dollars" in names and "Hours" in names:
        return PLUMBING
    return None


def text_dims(profile: TradeProfile) -> tuple:
    """Record keys that should be coerced to clean strings for grouping."""
    keys = ("drawing", "system", "floor", "specs", "material_spec", "shape",
            "report_section", "report_cat", "subsection", "item_type", "material",
            "trade")
    return tuple(k for k in keys if k in profile.column_map.values())
