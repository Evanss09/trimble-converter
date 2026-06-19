"""VR Mechanical brand kit, baked in so the shipped tool has no external deps.

Palette and type mirror the approved VR look (vrmechanical.ca audit 2026-06-18):
black header bars, the logo red, Manrope headings + Poppins body for the PDF,
Arial for Excel (xlsx cannot embed fonts). Values are copied from the shared
`vr_brand.py` rather than imported so the standalone .exe carries everything.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ----------------------------------------------------------------- palette
VR_BLACK = "#0d0d0d"
VR_RED = "#d41d11"        # logo / registered-mark red
DARK_GRAY = "#1a1a1a"
MID_GRAY = "#555555"
TABLE_HDR = "#111111"     # near-black PDF table header
ROW_ALT = "#f5f5f5"       # alternating row tint
ROW_LINE = "#d8d8d8"      # row separator
SUBTOTAL_FILL = "#e9e9e9"  # grey subtotal band (Excel)
FLOOR_FILL = "#d41d11"    # floor band uses the brand red (Excel)
WHITE = "#ffffff"

EXCEL_FONT = "Arial"      # Excel stays Arial (cannot embed brand fonts)

COMPANY_NAME = "VR Mechanical Solutions Inc."
COMPANY_FOOTER = (
    "VR Mechanical Solutions Inc.  •  283 Station Street  "
    "•  Ajax ON  •  L1S 1S3  •  905-426-7551"
)


# --------------------------------------------------------------- font paths
def _fonts_dir() -> Path:
    """Locate the bundled fonts both from source and from a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ductsort" / "fonts"
    return Path(__file__).resolve().parent / "fonts"


FONTS_DIR = _fonts_dir()

# ReportLab registered font names used by the PDF renderer.
RL_BODY = "VR-Regular"
RL_BODY_BOLD = "VR-Bold"
RL_BODY_ITALIC = "VR-Italic"
RL_BODY_BOLDITALIC = "VR-BoldItalic"
RL_HEAD = "VR-Heading"
RL_HEAD_BOLD = "VR-Heading-Bold"


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
            "VR", normal=RL_BODY, bold=RL_BODY_BOLD,
            italic=RL_BODY_ITALIC, boldItalic=RL_BODY_BOLDITALIC,
        )
        return RL_BODY, RL_BODY_BOLD, RL_HEAD, RL_HEAD_BOLD
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Helvetica-Bold"
