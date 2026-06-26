"""Shared sys.path bootstrap for the test suite.

The scripts/ scripts expect to be imported as top-level modules (config,
soql_loader, rest_client, sf_cli) — that's how they behave when main.py
does `from config import ...`. Tests mirror that by inserting scripts/
onto sys.path.

fs_guard is now sourced via ``from config import fs_guard`` (config.py
re-exports it from the plugin _shared/ package). No tools/ entry on
sys.path is required — config.py's dev-fallback walks up to the repo's
``plugins/investigating-agentforce-architecture/shared/`` when ``scripts/_shared/``
hasn't yet been mirrored by install.sh / the build script.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent

s = str(_SCRIPTS_DIR)
if s not in sys.path:
    sys.path.insert(0, s)
