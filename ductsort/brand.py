"""Built-in report style kit, baked in so the shipped tool has no external deps.

A clean, self-contained look: black header bars, a red accent, Manrope headings
+ Poppins body for the PDF, Arial for Excel (xlsx cannot embed fonts). Everything
is defined here so the standalone .exe carries its own styling with no external
files or imports.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ----------------------------------------------------------------- palette
INK = "#0d0d0d"
ACCENT = "#d41d11"        # red accent
DARK_GRAY = "#1a1a1a"
MID_GRAY = "#555555"
TABLE_HDR = "#111111"     # near-black PDF table header
ROW_ALT = "#f5f5f5"       # alternating row tint
ROW_LINE = "#d8d8d8"      # row separator
SUBTOTAL_FILL = "#e9e9e9"  # grey subtotal band (Excel)
FLOOR_FILL = "#d41d11"    # floor band uses the red accent (Excel)
WHITE = "#ffffff"

EXCEL_FONT = "Arial"      # Excel stays Arial (cannot embed fonts)

# Optional footer / subtitle text on the PDF. Empty by default so the tool is
# standalone; set these if you want your own name on the generated reports.
COMPANY_NAME = ""
COMPANY_FOOTER = ""


# --------------------------------------------------------------- font paths
def _fonts_dir() -> Path:
    """Locate the bundled fonts both from source and from a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ductsort" / "fonts"
    return Path(__file__).resolve().parent / "fonts"


FONTS_DIR = _fonts_dir()

# ReportLab registered font names used by the PDF renderer.
RL_BODY = "Report-Regular"
RL_BODY_BOLD = "Report-Bold"
RL_BODY_ITALIC = "Report-Italic"
RL_BODY_BOLDITALIC = "Report-BoldItalic"
RL_HEAD = "Report-Heading"
RL_HEAD_BOLD = "Report-Heading-Bold"


def register_reportlab_fonts() -> tuple[str, str, str, str]:
    """Register Manrope/Poppins with ReportLab. Returns (body, bold, head, head_bold).

    Falls back to Helvetica if the TTFs are missing so the PDF still renders.
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        pairs = [
            (RL_BODY, "Poppins-Regular.ttf"),
            (RL_BODY_BOLD, "Poppins-Bold.ttf"),
            (RL_BODY_ITALIC, "Poppins-Italic.ttf"),
            (RL_BODY_BOLDITALIC, "Poppins-BoldItalic.ttf"),
            (RL_HEAD, "Manrope-SemiBold.ttf"),
            (RL_HEAD_BOLD, "Manrope-Bold.ttf"),
        ]
        registered = set(pdfmetrics.getRegisteredFontNames())
        for name, fname in pairs:
            if name not in registered:
                pdfmetrics.registerFont(TTFont(name, str(FONTS_DIR / fname)))
        pdfmetrics.registerFontFamily(
            "Report", normal=RL_BODY, bold=RL_BODY_BOLD,
            italic=RL_BODY_ITALIC, boldItalic=RL_BODY_BOLDITALIC,
        )
        return RL_BODY, RL_BODY_BOLD, RL_HEAD, RL_HEAD_BOLD
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Helvetica-Bold"
