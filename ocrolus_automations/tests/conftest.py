"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path when running tests (e.g. from repo root)
src = Path(__file__).resolve().parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
