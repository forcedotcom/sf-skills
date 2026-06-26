"""Shared constants for investigating-agentforce-d360.

Values that don't vary per environment or user live here. If a value
needs to be overridable at runtime in the future, swap this module for
a loader — callers won't notice.

Path layout::

    ~/.vibe/data/investigating-agentforce-d360/
    └── <org_id_15>/
        └── <agent_api_name>__<agent_version>/
            └── <session_id>/                          ← session artifacts

``DATA_ROOT`` is re-exported from the canonical helper in
``scripts/_shared/paths.py`` (sibling module, inlined at the skill
boundary). All session-dir composition MUST go through
``paths.session_dir(...)`` — never compose ``DATA_ROOT / <sid>``
directly, because that bypasses the 4-segment regex validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Data Cloud Query API — the instance_url prefix is resolved at runtime
# via `sf org display --target-org <alias> --json` (Claude does that,
# not python). Python only owns the path.
DC_API_PATH = "/services/data/v66.0/ssot/query"


# -----------------------------------------------------------------------------
# Shared path helpers — sibling _shared/ package
# -----------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _shared import paths  # type: ignore  # noqa: E402,F401 — re-export
from _shared import sql    # type: ignore  # noqa: E402,F401 — re-export

# One persistent tree per session. Writes land directly here — no
# ephemeral /tmp staging. Re-running the same session id finds prior
# results, which later enables per-artifact caching.
DATA_ROOT = paths.DATA_ROOT
