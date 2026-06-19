"""DuctSort — VR Mechanical sheet metal takeoff summarizer.

Turns a Trimble AutoBid SheetMetal raw export into a tight, VR-branded Excel
workbook and PDF, sorted by floor, system, size, spec/gauge and drawing.
Deterministic and offline: no AI / network connection required.
"""
from .convert import convert

__all__ = ["convert"]
__version__ = "2.0.0"
