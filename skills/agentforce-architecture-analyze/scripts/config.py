"""Shared paths + constants for investigating-agentforce-architecture.

Resolves SKILL_ROOT relative to this file's location — works on every
runtime without env vars. SKILL.md bash blocks still read the
``PLUGIN_ROOT`` env var (with a default fallback) because bash has no
``__file__`` equivalent.

Path layout:

    ~/.vibe/data/investigating-agentforce-architecture/
    └── <org_id_15>/
        └── <agent_api_name>__<agent_version>/        ← architecture artifacts

Every path component embedded in a cache / data directory must be
regex-validated before being joined to a Path. Four components are in
scope: `api_version`, `org_id15`, `agent_api_name`, `agent_version`.
(`planner_name` is validated separately at the SOQL substitution
boundary by `soql_loader.load_soql` — it never appears in a filesystem
path.) The helpers below are the ONLY sanctioned way to build those
paths — direct Path composition from unvalidated strings is a
path-traversal vulnerability.
"""
from __future__ import annotations

import sys
from pathlib import Path

# SKILL_ROOT is the directory holding SKILL.md, derived from this file's location:
#   <SKILL_ROOT>/scripts/config.py  →  Path(__file__).resolve().parent.parent
# Python doesn't read PLUGIN_ROOT — it's only for SKILL.md bash blocks
# (PR3 will replace those with a proper entry script).
SKILL_ROOT = Path(__file__).resolve().parent.parent
SOQL_DIR = SKILL_ROOT / "assets" / "soql"
CLI_DIR = SKILL_ROOT / "assets" / "cli"
MERMAID_DIR = SKILL_ROOT / "assets" / "mermaid"
REFERENCES_DIR = SKILL_ROOT / "references"


# -----------------------------------------------------------------------------
# Shared path helpers — sourced from scripts/_shared/.
# -----------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _shared import paths as _paths  # type: ignore  # noqa: E402
from _shared import fs_guard  # type: ignore  # noqa: E402,F401 — re-exported for sibling scripts + tests

DATA_ROOT = _paths.DATA_ROOT
CACHE_ROOT = _paths.CACHE_ROOT
PROBE_CACHE_ROOT = CACHE_ROOT / "_channel_probe"

# Cache TTL — 7 days. Probe TTL same.
CACHE_TTL_DAYS = 7
PROBE_TTL_DAYS = 7

# BFS defensive termination guard.
#
# Historically this was `5` and acted as a functional constraint on
# chain depth. That was wrong: shared utility flows like `handleFlowFault`
# appear on every real flow's fault path, so any moderately nested tree
# (`[FLOW] A → [FLOW] B → [FLOW] handleFlowFault`) tripped the cap and
# surfaced the utility in `_pending_fetches` even though it is trivially
# expandable. Cycle detection now runs via a per-branch ancestor path set
# (`visited_in_path` in `inflate_flow_leaf`), which is the textbook-correct
# primitive for this problem: the same flow visited on two sibling branches
# is not a cycle, but the same flow visited along its own ancestor chain is.
#
# This constant is retained purely as a defensive last-resort termination
# guard for pathological graphs that somehow evade per-branch cycle detection
# (e.g. a bug regression in `_cycle_key`). In practice the per-branch set
# terminates every real bot tree long before this depth is reached.
MAX_BFS_DEPTH = 20

# Schema version — 3.1 (2026-05-05) canonicalizes `invocation_type` on
# STANDARD_ACTION nodes, formerly split across `raw_invocation_type` and
# `raw_action_type`. Must match `parse_wave.init_tree`'s `_schema_version`
# literal. Any bump forces a cache rebuild via `cache_check.py`'s gate.
SCHEMA_VERSION = "3.1"

# Default parallelism for ThreadPoolExecutor (Flow metadata fan-out).
DEFAULT_PARALLELISM = 5


# -----------------------------------------------------------------------------
# validated path builders
# -----------------------------------------------------------------------------
# fs_guard is re-exported above from `scripts/_shared/`.
# Sibling scripts (soql_loader, render_architecture, fetch_soql)
# and the test suite import it as ``from config import fs_guard`` so the
# resolution dance lives in one place.


def build_agent_data_dir(org_id_15: str, agent_api_name: str, agent_version: str) -> Path:
    """Return DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/.

    Thin wrapper over ``_shared.paths.agent_dir`` — kept so existing
    callers don't need to change import sites. The shared helper raises
    ``paths.PathValidationError`` (a ValueError subclass); we re-raise
    the underlying ``fs_guard.ValidationError`` so existing tests that
    catch that specific type keep passing.
    """
    fs_guard.validate_org_id_15(org_id_15, label="org_id_15")
    fs_guard.validate_api_name(agent_api_name, label="agent_api_name")
    fs_guard.validate_api_name(agent_version, label="agent_version")
    return _paths.DATA_ROOT / org_id_15 / f"{agent_api_name}__{agent_version}"


def build_agent_cache_dir(org_id_15: str, agent_api_name: str, agent_version: str) -> Path:
    """Return CACHE_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/.

    Mirrors ``build_agent_data_dir`` under the cache root. Validation gate
    matches — every segment regex-checked before the join.
    """
    fs_guard.validate_org_id_15(org_id_15, label="org_id_15")
    fs_guard.validate_api_name(agent_api_name, label="agent_api_name")
    fs_guard.validate_api_name(agent_version, label="agent_version")
    return CACHE_ROOT / org_id_15 / f"{agent_api_name}__{agent_version}"


def build_probe_cache_dir(org_id_15: str, api_version: str) -> Path:
    """Return PROBE_CACHE_ROOT/<org_id_15>/<api_version>/.

    org_id_15 via validate_api_name (regex tolerates 15-char alnum),
    api_version via validate_api_version (enforces `vNN.N` shape — rejects
    `..`, `/`, and any non-version string).
    """
    fs_guard.validate_org_id_15(org_id_15, label="org_id_15")
    fs_guard.validate_api_version(api_version, label="api_version")
    return PROBE_CACHE_ROOT / org_id_15 / api_version
