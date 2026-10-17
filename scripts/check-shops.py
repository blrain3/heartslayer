#!/usr/bin/env python3
"""Compatibility wrapper for the installed check-shops command."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heartslayer_kit.check_shops import main


if __name__ == '__main__':
    raise SystemExit(main())
