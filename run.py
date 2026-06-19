"""PyInstaller entry point.

A thin launcher so the frozen .exe runs the same dispatch as `python -m ductsort`:
arguments -> CLI, no arguments -> GUI file picker.
"""
from ductsort.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
