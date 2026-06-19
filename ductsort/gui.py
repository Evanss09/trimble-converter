"""Double-click entry: the Trimble Converter dashboard (pywebview, frameless).

Multi-file: pick one or several raw exports; same-trade files merge and trades
become separate sections in one combined Excel + PDF. Falls back to the bundled
Tkinter home screen if WebView2/pywebview is unavailable.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from . import __version__, trades
from .convert import peek, run_files
from .reader import RawDataError


def _web_index() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ductsort"
    else:
        base = Path(__file__).resolve().parent
    return base / "web" / "index.html"


def _human_size(path) -> str:
    try:
        n = float(os.path.getsize(path))
    except OSError:
        return ""
    if n < 1024:
        return f"{int(n)} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _profile(trade):
    return next((p for p in trades.PROFILES if p.name == trade), trades.PROFILES[0])


def _cards(seg):
    """KPI tiles for one segment of a render result."""
    ul, k = seg["unit_labels"], seg["kpis"]
    out = []
    for spec in _profile(seg["trade"]).kpis:
        from .model import fmt_value
        label = spec["label"].format(weight=ul.get("weight", ""), area=ul.get("area", ""),
                                     per_area=ul.get("per_area", ""))
        out.append({"value": fmt_value(spec["fmt"], k.get(spec["key"], 0.0)), "label": label})
    return out


class Api:
    def __init__(self):
        self._window = None

    def info(self) -> dict:
        return {"version": __version__}

    def choose_files(self):
        import webview
        win = self._window or (webview.windows[0] if webview.windows else None)
        if win is None:
            return []
        sel = win.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True,
            file_types=("Trimble export (*.xlsx;*.xlsm)", "All files (*.*)"))
        if not sel:
            return []
        return list(sel) if isinstance(sel, (list, tuple)) else [sel]

    def peek_files(self, paths) -> dict:
        """Per-file trade + line count for the idle file list."""
        files = []
        for p in paths:
            try:
                files.append(peek(p))
            except RawDataError as e:
                files.append({"file": Path(p).name, "error": str(e)})
            except Exception as e:  # pragma: no cover
                files.append({"file": Path(p).name, "error": str(e)})
        return {"files": files}

    def generate(self, paths, want_excel=True, want_pdf=True, units="auto") -> dict:
        t0 = time.time()
        try:
            res = run_files(list(paths), want_excel=bool(want_excel),
                            want_pdf=bool(want_pdf), units_choice=units, combined=True)[0]
        except RawDataError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # pragma: no cover
            return {"ok": False, "error": str(e)}

        files = []
        if res.get("excel"):
            files.append({"name": Path(res["excel"]).name, "path": str(res["excel"]),
                          "size": _human_size(res["excel"]), "desc": "Excel workbook"})
        if res.get("pdf"):
            pages = res.get("pdf_pages", 0)
            files.append({"name": Path(res["pdf"]).name, "path": str(res["pdf"]),
                          "size": _human_size(res["pdf"]),
                          "desc": f"PDF report · {pages} pages" if pages else "PDF report"})
        segments = [{"label": s["label"], "trade": s["trade"], "cards": _cards(s),
                     "sources": sorted(set(s["sources"]))} for s in res["segments"]]
        folder = str(Path(res.get("excel") or res.get("pdf")).parent)
        return {"ok": True, "seconds": round(time.time() - t0, 1),
                "title": res.get("title") or "Take-off", "multi": res.get("multi", False),
                "segments": segments, "files": files, "folder": folder}

    def open_path(self, p):
        self._open(p)

    def open_folder(self, p):
        self._open(p)

    @staticmethod
    def _open(target):
        if not target:
            return
        try:
            os.startfile(str(target))  # noqa: S606
        except Exception:
            pass

    def win_minimize(self):
        if self._window:
            try: self._window.minimize()
            except Exception: pass

    def win_maximize(self):
        if not self._window:
            return
        for m in ("toggle_fullscreen", "maximize", "restore"):
            fn = getattr(self._window, m, None)
            if callable(fn):
                try: fn(); return
                except Exception: continue

    def win_close(self):
        if self._window:
            try: self._window.destroy()
            except Exception: pass


def run() -> int:
    try:
        import webview
    except Exception:
        return _fallback()
    try:
        api = Api()
        window = webview.create_window(
            "Trimble Converter", url=str(_web_index()), js_api=api,
            width=900, height=804, min_size=(820, 640),
            frameless=True, easy_drag=False, background_color="#0e1116")
        api._window = window
        webview.start()
        return 0
    except Exception:
        return _fallback()


def _fallback() -> int:
    from . import gui_tk
    return gui_tk.run()


if __name__ == "__main__":
    raise SystemExit(run())
