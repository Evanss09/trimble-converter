"""Entry dispatch: arguments -> CLI; no arguments -> GUI file picker.

So the same build serves `ductsort raw.xlsx` on the command line and a
double-click of the .exe (which launches with no args).
"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        return cli_main()
    from .gui import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
