"""Tkinter fallback home screen (dark "mint-pro" theme), multi-file aware.

Used when WebView2/pywebview is unavailable. Plainer than the web dashboard but
the same conversion and combined output, so the tool works on any Windows box.
"""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import __version__, trades
from .convert import run_files
from .model import fmt_value
from .reader import RawDataError

BG, BG2, PANEL, BORDER = "#0e1116", "#0b0e12", "#12161c", "#2f3a45"
MINT, MINT_INK, TXT, MUTED, MUTED2 = "#1bd198", "#06251c", "#e6edf3", "#8b96a3", "#5f6b78"


def _profile(trade):
    return next((p for p in trades.PROFILES if p.name == trade), trades.PROFILES[0])


def run() -> int:
    root = tk.Tk()
    root.title("Trimble Converter")
    root.configure(bg=BG)
    root.geometry("620x640")
    root.minsize(560, 600)
    state = {"paths": [], "result": None}

    header = tk.Frame(root, bg=BG2, height=58); header.pack(fill="x"); header.pack_propagate(False)
    tk.Label(header, text="T", bg=MINT, fg=MINT_INK, font=("Consolas", 13, "bold"),
             width=2, height=1).pack(side="left", padx=(18, 11), pady=14)
    tk.Label(header, text="Trimble Converter", bg=BG2, fg=TXT,
             font=("Segoe UI", 13, "bold")).pack(side="left", pady=14)
    tk.Frame(root, bg="#1c232c", height=1).pack(fill="x")

    body = tk.Frame(root, bg=BG); body.pack(fill="both", expand=True, padx=26, pady=18)

    footer = tk.Frame(root, bg=BG2, height=30); footer.pack(fill="x", side="bottom"); footer.pack_propagate(False)
    tk.Label(footer, text="Trimble Converter", bg=BG2, fg=MUTED2, font=("Segoe UI", 8)).pack(side="left", padx=18)
    tk.Label(footer, text=f"v{__version__}", bg=BG2, fg=MINT, font=("Consolas", 8, "bold")).pack(side="right", padx=18)

    units_var = tk.StringVar(value="auto")
    excel_var = tk.BooleanVar(value=True)
    pdf_var = tk.BooleanVar(value=True)

    def clear_body():
        for w in body.winfo_children():
            w.destroy()

    def show_home():
        clear_body()
        tk.Label(body, text="SHEET METAL & PLUMBING TAKE-OFF", bg=BG, fg=MINT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(body, text="Drop raw take-offs, get the report.", bg=BG, fg=TXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(3, 14))

        zone = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        zone.pack(fill="x")
        chosen = tk.StringVar(value="No files chosen")

        def choose():
            paths = filedialog.askopenfilenames(
                title="Select Trimble raw export(s)",
                filetypes=[("Trimble export", "*.xlsx *.xlsm"), ("All files", "*.*")])
            if paths:
                state["paths"] = list(paths)
                chosen.set(f"{len(paths)} file(s) selected" if len(paths) > 1 else Path(paths[0]).name)
                gen_btn.config(state="normal", bg=MINT, fg=MINT_INK)

        tk.Label(zone, text="One or many .xlsx / .xlsm exports", bg=PANEL, fg=TXT,
                 font=("Segoe UI", 11)).pack(pady=(16, 8))
        tk.Button(zone, text="Choose files", command=choose, bg="#1a1f26", fg=TXT,
                  activebackground="#1a1f26", activeforeground=MINT, relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=16, pady=6, cursor="hand2").pack()
        tk.Label(zone, textvariable=chosen, bg=PANEL, fg=MUTED, font=("Consolas", 9)).pack(pady=(10, 16))

        opts = tk.Frame(body, bg=BG); opts.pack(fill="x", pady=18)
        ucol = tk.Frame(opts, bg=BG); ucol.pack(side="left", expand=True, anchor="w")
        tk.Label(ucol, text="UNITS", bg=BG, fg=MUTED2, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        for val, lbl in [("auto", "Auto-detect"), ("imperial", "Imperial"), ("metric", "Metric")]:
            tk.Radiobutton(ucol, text=lbl, value=val, variable=units_var, bg=BG, fg=TXT,
                           selectcolor=BG2, activebackground=BG, activeforeground=MINT,
                           font=("Segoe UI", 10)).pack(anchor="w")
        ocol = tk.Frame(opts, bg=BG); ocol.pack(side="left", expand=True, anchor="w")
        tk.Label(ocol, text="OUTPUT", bg=BG, fg=MUTED2, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Checkbutton(ocol, text="Excel workbook", variable=excel_var, bg=BG, fg=TXT,
                       selectcolor=BG2, activebackground=BG, activeforeground=MINT,
                       font=("Segoe UI", 10)).pack(anchor="w")
        tk.Checkbutton(ocol, text="PDF report", variable=pdf_var, bg=BG, fg=TXT,
                       selectcolor=BG2, activebackground=BG, activeforeground=MINT,
                       font=("Segoe UI", 10)).pack(anchor="w")

        gen_btn = tk.Button(body, text="Generate report", command=do_convert,
                            bg="#222a33", fg=MUTED2, activebackground=MINT, activeforeground=MINT_INK,
                            relief="flat", font=("Segoe UI", 12, "bold"), pady=11, cursor="hand2",
                            state="disabled")
        gen_btn.pack(fill="x", pady=(8, 0))
        if state["paths"]:
            chosen.set(f"{len(state['paths'])} file(s) selected" if len(state['paths']) > 1
                       else Path(state['paths'][0]).name)
            gen_btn.config(state="normal", bg=MINT, fg=MINT_INK)

    def do_convert():
        if not state["paths"]:
            return
        if not (excel_var.get() or pdf_var.get()):
            messagebox.showwarning("Pick an output", "Choose Excel, PDF, or both.")
            return
        try:
            res = run_files(state["paths"], want_excel=excel_var.get(), want_pdf=pdf_var.get(),
                            units_choice=units_var.get(), combined=True)[0]
        except RawDataError as e:
            messagebox.showerror("Not a raw export", str(e)); return
        except Exception as e:
            messagebox.showerror("Could not generate report", str(e)); return
        state["result"] = res
        show_result(res)

    def show_result(res):
        clear_body()
        tk.Label(body, text="REPORT READY", bg=BG, fg=MINT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(body, text=(res["title"] or "Take-off") + ("  (combined)" if res["multi"] else ""),
                 bg=BG, fg=TXT, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(2, 12))

        for seg in res["segments"]:
            prof = _profile(seg["trade"]); ul = seg["unit_labels"]; k = seg["kpis"]
            tk.Label(body, text=seg["label"], bg=BG, fg=MINT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 4))
            grid = tk.Frame(body, bg=BG); grid.pack(fill="x")
            cards = []
            for spec in prof.kpis:
                lbl = spec["label"].format(weight=ul.get("weight", ""), area=ul.get("area", ""),
                                           per_area=ul.get("per_area", ""))
                cards.append((fmt_value(spec["fmt"], k.get(spec["key"], 0.0)), lbl))
            for i, (val, lbl) in enumerate(cards):
                cell = tk.Frame(grid, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
                cell.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="nsew")
                tk.Frame(cell, bg=MINT, width=3).pack(side="left", fill="y")
                inner = tk.Frame(cell, bg=PANEL); inner.pack(side="left", fill="both", expand=True, padx=9, pady=7)
                tk.Label(inner, text=val, bg=PANEL, fg=TXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
                tk.Label(inner, text=lbl, bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            for c in range(4):
                grid.columnconfigure(c, weight=1)

        actions = tk.Frame(body, bg=BG); actions.pack(fill="x", pady=18)

        def opener(p):
            return lambda: (p and os.startfile(str(p)))

        if res.get("excel"):
            tk.Button(actions, text="Open Excel", command=opener(res["excel"]), bg="#1a1f26", fg=TXT,
                      activeforeground=MINT, relief="flat", font=("Segoe UI", 10, "bold"),
                      padx=10, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        if res.get("pdf"):
            tk.Button(actions, text="Open PDF", command=opener(res["pdf"]), bg="#1a1f26", fg=TXT,
                      activeforeground=MINT, relief="flat", font=("Segoe UI", 10, "bold"),
                      padx=10, pady=6, cursor="hand2").pack(side="left", padx=(0, 8))
        folder = Path(res.get("excel") or res.get("pdf")).parent
        tk.Button(actions, text="Open folder", command=opener(folder), bg=MINT, fg=MINT_INK,
                  relief="flat", font=("Segoe UI", 10, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Convert another", command=show_home, bg="#1a1f26", fg=TXT,
                  activeforeground=MINT, relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=6, cursor="hand2").pack(side="left")

    show_home()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
