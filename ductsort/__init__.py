"""DuctSort — Trimble AutoBid takeoff summarizer (sheet metal and plumbing).

Turns a Trimble AutoBid raw export into a tight, branded Excel workbook and PDF,
sorted by floor, system, size, spec/gauge and drawing. Deterministic and offline:
no AI / network connection required.
"""
from .convert import convert

__all__ = ["convert"]
__version__ = "2.0.0"
