"""Branded PDF for a ReportModel of trade segments.

A cover, then a condensed section per trade segment (segment band + KPI line +
summary tables). Full line-item / size detail lives in the Excel. Clean look:
black header bar with a red corner triangle, black footer bar, Manrope/Poppins
embedded.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from . import aggregate, brand, views
from .model import column_header, fmt_value

TOP_SIZES = 40


def _kpi_line(seg, S):
    ul, k = seg["unit_labels"], seg["data"]["kpis"]
    parts = []
    for spec in seg["profile"].kpis:
        lbl = spec["label"].format(weight=ul.get("weight", ""), area=ul.get("area", ""),
                                   per_area=ul.get("per_area", ""))
        parts.append(f"<b>{fmt_value(spec['fmt'], k.get(spec['key'], 0.0))}</b> {lbl}")
    return Paragraph("  &nbsp;&nbsp;•&nbsp;&nbsp;  ".join(parts), S["KPI"])


def _table(heading, nodes, kind, total_totals, columns, ul, S,
           total_label="Total", top=None, note=None):
    head = [Paragraph(heading_label(heading), S["TH"])] + [
        Paragraph(column_header(c, ul), S["THR"]) for c in columns]
    rows = [head]
    shown = nodes[:top] if top else nodes
    for n in shown:
        rows.append(_row(views.label(n["key"], kind), n["totals"], total_totals, columns, S))
    rows.append(_row(total_label, total_totals, total_totals, columns, S, bold=True))

    label_w = 5.4 * cm
    num_w = (S["usable"] - label_w) / len(columns)
    widths = [label_w] + [num_w] * len(columns)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(brand.TABLE_HDR)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(brand.ROW_LINE)),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor(brand.INK)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(brand.ROW_ALT)),
    ]
    for ri in range(1, len(rows) - 1):
        if ri % 2 == 0:
            cmds.append(("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#fafafa")))
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    block = [Paragraph(heading, S["H2"]), t]
    if note:
        block.append(Paragraph(note, S["NOTE"]))
    block.append(Spacer(1, 9))
    return KeepTogether(block)


def heading_label(heading):
    return heading.replace("Summary by ", "").replace("By ", "")


def _row(label, totals, grand, columns, S, bold=False):
    t = aggregate.add_percentages(totals, grand)
    style = S["TDB"] if bold else S["TD"]
    style_r = S["TDBR"] if bold else S["TDR"]
    cells = [Paragraph(_esc(label), style)]
    for col in columns:
        v = t.get(col["key"])
        cells.append(Paragraph("" if v is None else fmt_value(col["kind"], v), style_r))
    return cells


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _segment_section(seg, S):
    out = []
    ul = seg["unit_labels"]
    cols = seg["profile"].summary_columns
    grand = seg["data"]["grand"]
    dims = seg["data"]["hierarchy_dims"]

    out.append(Paragraph(f"{_esc(seg['label'])}", S["SEG"]))
    out.append(HRFlowable(width="100%", thickness=1.4, color=colors.HexColor(brand.ACCENT),
                          spaceBefore=2, spaceAfter=6))
    out.append(_kpi_line(seg, S))
    out.append(Spacer(1, 6))

    # Overview by the top hierarchy dim, then the second dim.
    d0 = dims[0]
    out.append(_table(f"Summary by {_dim_label(d0)}", seg["data"]["hierarchy"],
                      _kind(d0), grand, cols, ul, S))
    if len(dims) > 1:
        d1 = dims[1]
        nodes = aggregate.rollup(seg["records"], [d1])
        out.append(_table(f"Summary by {_dim_label(d1)}", nodes, _kind(d1), grand, cols, ul, S))

    for flat in seg["data"]["flats"]:
        if flat["dim"] in dims[:2]:
            continue
        top = TOP_SIZES if flat["dim"] == "size_norm" else None
        note = None
        if top and len(flat["nodes"]) > top:
            note = f"Top {top} of {len(flat['nodes']):,} shown; full list in the Excel."
        out.append(_table(flat["title"], flat["nodes"], flat["kind"], grand, cols, ul, S,
                          total_label="Total", top=top, note=note))
    return out


def _dim_label(dim):
    return {"floor": "Floor", "system": "System", "material_spec": "Material Spec",
            "size_norm": "Size", "drawing": "Drawing", "trade": "Trade",
            "specs": "Spec / Gauge"}.get(dim, dim.replace("_", " ").title())


def _kind(dim):
    return {"size_norm": "size", "material_spec": "spec", "specs": "spec"}.get(dim, dim)


def _styles(body, bold, head, head_bold, usable):
    def sty(name, size, font, color, align="left", leading=None):
        return ParagraphStyle(name, fontName=font, fontSize=size,
                              textColor=colors.HexColor(color),
                              alignment={"left": 0, "right": 2}[align],
                              leading=leading or size * 1.2)
    return {
        "usable": usable,
        "H1": sty("H1", 16, head_bold, brand.INK),
        "SEG": sty("SEG", 13, head_bold, brand.INK, leading=16),
        "H2": sty("H2", 10.5, head_bold, brand.INK, leading=13),
        "SUB": sty("SUB", 8.5, body, brand.MID_GRAY),
        "KPI": sty("KPI", 10, body, brand.DARK_GRAY, leading=15),
        "NOTE": sty("NOTE", 7.5, body, brand.MID_GRAY, leading=10),
        "TH": sty("TH", 8, head_bold, brand.WHITE),
        "THR": sty("THR", 8, head_bold, brand.WHITE, align="right"),
        "TD": sty("TD", 8, body, brand.DARK_GRAY),
        "TDR": sty("TDR", 8, body, brand.DARK_GRAY, align="right"),
        "TDB": sty("TDB", 8, bold, brand.INK),
        "TDBR": sty("TDBR", 8, bold, brand.INK, align="right"),
    }


def write(model: dict, out_path) -> tuple:
    out_path = Path(out_path)
    generated = date.today().strftime("%b %d, %Y")
    body, bold, head, head_bold = brand.register_reportlab_fonts()

    PAGE_W, PAGE_H = landscape(letter)
    HDR_H, FTR_H, LR = 1.55 * cm, 0.9 * cm, 1.6 * cm
    usable = PAGE_W - 2 * LR
    S = _styles(body, bold, head, head_bold, usable)
    title = model["title"] or "Trimble Take-off"
    doc_title = title + (" — Combined Takeoff Summary" if model["multi"] else " — Takeoff Summary")
    page_count = [0]

    def draw_page(canvas, d):
        page_count[0] = d.page
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(brand.INK))
        canvas.rect(0, PAGE_H - HDR_H, PAGE_W, HDR_H, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(brand.ACCENT))
        p = canvas.beginPath()
        p.moveTo(PAGE_W - 4.5 * cm, PAGE_H)
        p.lineTo(PAGE_W, PAGE_H)
        p.lineTo(PAGE_W, PAGE_H - HDR_H)
        p.close()
        canvas.drawPath(p, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(head_bold, 9)
        canvas.drawString(LR, PAGE_H - HDR_H + 0.5 * cm, doc_title)
        canvas.setFillColor(colors.HexColor(brand.INK))
        canvas.rect(0, 0, PAGE_W, FTR_H, fill=1, stroke=0)
        mid = FTR_H / 2 - 0.12 * cm
        canvas.setFillColor(colors.white)
        canvas.setFont(body, 7)
        canvas.drawCentredString(PAGE_W / 2, mid, brand.COMPANY_FOOTER)
        canvas.drawRightString(PAGE_W - 0.4 * cm, mid, f"Page {d.page}")
        canvas.restoreState()

    story = [Paragraph(_esc(doc_title), S["H1"]),
             HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(brand.ACCENT),
                        spaceBefore=2, spaceAfter=6)]
    sub = "   |   ".join(x for x in [title, f"Generated {generated}", brand.COMPANY_NAME] if x)
    story.append(Paragraph(_esc(sub), S["SUB"]))
    story.append(Spacer(1, 10))
    for seg in model["segments"]:
        story.extend(_segment_section(seg, S))
        story.append(Spacer(1, 6))

    tmp = out_path.with_name(f"{out_path.stem}.tmp_{os.getpid()}.pdf")
    docu = SimpleDocTemplate(str(tmp), pagesize=landscape(letter), leftMargin=LR, rightMargin=LR,
                             topMargin=HDR_H + 0.5 * cm, bottomMargin=FTR_H + 0.45 * cm)
    try:
        docu.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        try:
            os.replace(tmp, out_path)
            return out_path, page_count[0]
        except PermissionError:
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            alt = out_path.with_name(f"{out_path.stem} (locked-{stamp}).pdf")
            os.replace(tmp, alt)
            print(f"WARNING: '{out_path.name}' is open. Wrote '{alt.name}' instead.")
            return alt, page_count[0]
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
