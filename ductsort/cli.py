"""Command line: trimble-converter <raw1> [raw2 ...] [options].

One file -> one report. Several files -> one combined report (same-trade merged,
trades as separate sections) unless --separate is given.
"""
from __future__ import annotations

import argparse
import sys

from .convert import run_files
from .reader import RawDataError


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="trimble-converter",
        description="Convert Trimble AutoBid raw exports (sheet metal or plumbing) "
                    "into branded Excel + PDF take-off summaries.")
    p.add_argument("inputs", nargs="+", help="raw export .xlsx/.xlsm file(s)")
    p.add_argument("-o", "--out-dir", default=None,
                   help="Output folder (default: alongside the first input)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--excel-only", action="store_true", help="Write only the Excel workbook")
    g.add_argument("--pdf-only", action="store_true", help="Write only the PDF")
    p.add_argument("--units", choices=["auto", "imperial", "metric"], default="auto",
                   help="Unit labels: auto-detect (default), or force imperial/metric")
    p.add_argument("--separate", action="store_true",
                   help="One report per file instead of one combined report")
    args = p.parse_args(argv)

    try:
        results = run_files(
            args.inputs, args.out_dir,
            want_excel=not args.pdf_only, want_pdf=not args.excel_only,
            units_choice=args.units, combined=not args.separate,
        )
    except RawDataError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # pragma: no cover
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    for res in results:
        for s in res["segments"]:
            k = s["kpis"]
            print(f"  {s['label']:<12} ${k['material_cost']:>12,.0f}  "
                  f"{k['labour_hrs']:>9,.0f} hrs  {k['line_count']:>6,} lines")
        for kind in ("excel", "pdf"):
            if res.get(kind):
                print(f"{kind.upper():5s} -> {res[kind]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
