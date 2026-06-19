"""Orchestration: one or more raw exports in, branded Excel + PDF out.

A run produces a ReportModel of trade segments. Multiple files of the same
trade merge into one segment (tagged by source file for big multi-person jobs);
different trades become separate segments in the same workbook / PDF.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import excel_report, pdf_report, reader, units, views


def _clean_source(path: Path) -> str:
    """A short area/source label from a filename."""
    s = path.stem
    s = re.sub(r"(?i)\b(raw\s*data|rawdata|raw|export|pivot|takeoff|take-off)\b", " ", s)
    s = re.sub(r"[-_]+", " ", s)
    return re.sub(r"\s+", " ", s).strip(" -") or path.stem


def analyze(input_path, units_choice: str = "auto") -> dict:
    """Read + detect trade for one file (records tagged with their source)."""
    input_path = Path(input_path)
    records, meta, profile = reader.load(input_path)
    src = _clean_source(input_path)
    for r in records:
        r["source"] = src
    return {"input_path": input_path, "records": records, "meta": meta,
            "profile": profile, "units_choice": units_choice, "source": src}


def peek(input_path, units_choice: str = "auto") -> dict:
    """Lightweight per-file summary for the dashboard file list."""
    a = analyze(input_path, units_choice)
    return {"file": a["input_path"].name, "trade": a["profile"].name,
            "label": a["profile"].label, "line_count": len(a["records"]),
            "bid_name": a["meta"].get("bid_name", "")}


def _segment(profile, analyses, units_choice) -> dict:
    """Merge same-trade analyses into one segment with its own views."""
    records = [r for a in analyses for r in a["records"]]
    metas = [a["meta"] for a in analyses]
    bid = next((m.get("bid_name") for m in metas if m.get("bid_name")), "")
    meta = {"bid_name": bid,
            "bid_number": next((m.get("bid_number") for m in metas if m.get("bid_number")), ""),
            "filter": metas[0].get("filter", "") if metas else ""}
    unit_labels = units.resolve(records, units_choice, profile.has_area)
    data = views.build(records, profile, unit_labels)
    sources = [a["source"] for a in analyses]
    return {"profile": profile, "label": profile.label, "abbr": profile.abbr,
            "sources": sources, "meta": meta, "unit_labels": unit_labels,
            "data": data, "records": records, "multi_source": len(set(sources)) > 1}


def build_model(analyses: list[dict], units_choice: str = "auto") -> dict:
    """Group analyses by trade into one ReportModel."""
    order, groups = [], {}
    for a in analyses:
        t = a["profile"].name
        if t not in groups:
            groups[t] = []
            order.append(t)
        groups[t].append(a)
    segments = [_segment(groups[t][0]["profile"], groups[t], units_choice) for t in order]

    bids = {s["meta"].get("bid_name") for s in segments if s["meta"].get("bid_name")}
    title = next(iter(bids)) if len(bids) == 1 else ""
    multi = len(segments) > 1 or any(s["multi_source"] for s in segments)
    return {"title": title, "segments": segments, "multi": multi}


def _safe_name(model: dict, fallback: str) -> str:
    # The bid name comes from the workbook and can be arbitrarily long; cap it so
    # the output path stays clear of the Windows MAX_PATH (260 char) limit, and
    # strip characters that are illegal in a filename / path separators.
    base = re.sub(r'[<>:"/\\|?*]', "", model["title"] or fallback).strip(" .")[:90].strip(" .")
    kind = "Combined Takeoff Summary" if model["multi"] else "Takeoff Summary"
    if model["title"]:
        return f"{base} - {kind}" if base else kind
    if model["multi"]:
        return "Combined Takeoff Summary"
    return f"{base} - Takeoff Summary" if base else "Takeoff Summary"


def render_model(model: dict, out_dir, want_excel=True, want_pdf=True,
                 fallback_name="Takeoff Summary") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(model, fallback_name)

    result = {"excel": None, "pdf": None, "pdf_pages": 0, "title": model["title"],
              "multi": model["multi"]}
    if want_excel:
        result["excel"] = excel_report.write(model, out_dir / f"{stem}.xlsx")
    if want_pdf:
        path, pages = pdf_report.write(model, out_dir / f"{stem}.pdf")
        result["pdf"] = path
        result["pdf_pages"] = pages
    # Per-segment summary for the UI / CLI.
    result["segments"] = [{"trade": s["profile"].name, "label": s["label"],
                            "sources": s["sources"], "kpis": s["data"]["kpis"],
                            "unit_labels": s["unit_labels"],
                            "bid_name": s["meta"].get("bid_name", "")}
                           for s in model["segments"]]
    return result


def run_files(paths, out_dir=None, want_excel=True, want_pdf=True,
              units_choice="auto", combined=True) -> list[dict]:
    """Convert one or more files. Returns a list of result dicts (one when
    combined, else one per file)."""
    paths = [Path(p) for p in paths]
    out_dir = Path(out_dir) if out_dir else paths[0].parent
    analyses = [analyze(p, units_choice) for p in paths]

    if combined or len(analyses) == 1:
        model = build_model(analyses, units_choice)
        return [render_model(model, out_dir, want_excel, want_pdf, paths[0].stem)]
    results = []
    for a in analyses:
        model = build_model([a], units_choice)
        results.append(render_model(model, out_dir, want_excel, want_pdf, a["input_path"].stem))
    return results


def convert(input_path, out_dir=None, want_excel=True, want_pdf=True,
            units_choice="auto") -> dict:
    """Single-file convenience (CLI / fallback). Exposes the one segment's
    meta/kpis/unit_labels at the top level for older callers."""
    res = run_files([input_path], out_dir, want_excel, want_pdf, units_choice)[0]
    seg = res["segments"][0]
    res["meta"] = {"bid_name": seg["bid_name"]}
    res["kpis"] = seg["kpis"]
    res["unit_labels"] = seg["unit_labels"]
    res["units"] = seg["unit_labels"]["system"]
    return res
