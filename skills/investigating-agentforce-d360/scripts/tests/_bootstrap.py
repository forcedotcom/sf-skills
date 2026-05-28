"""Test bootstrap — adds sibling ``scripts/`` to sys.path.

Every ``test_*.py`` in this directory imports this module first
(as ``from . import _bootstrap``) so the sibling modules
(`config`, `storage`, `paths`, etc.) resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

# scripts/tests/_bootstrap.py → scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
