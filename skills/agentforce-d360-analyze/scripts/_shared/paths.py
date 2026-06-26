"""Canonical path helpers for investigating-agentforce-d360.

Layout:

    ~/.vibe/data/investigating-agentforce-d360/
    └── <org_id_15>/
        └── <agent_api_name>__<agent_version>/
            └── <session_id>/                          ← per-session DC artifacts
                ├── dc.*.json
                ├── dc._session_manifest.json
                ├── dc._session_tree.json
                └── dc._session_summary.md

Validation strategy
-------------------
The three "agent-identity" segments (org_id_15, agent_api_name, agent_version)
are validated by the regex helpers in the sibling ``fs_guard`` module. Any
segment containing ``..``, ``/``, or characters outside its regex charclass
raises ``PathValidationError`` — direct ``Path`` composition from unvalidated
input would be a path-traversal vulnerability and is prohibited.

``session_id`` is validated locally via ``SESSION_ID_RE.fullmatch`` because
fs_guard's ``api_name`` rule is too permissive for it (session IDs can contain
hyphens, which API names cannot). The regex is fully anchored (``\\A...\\Z``)
and call sites MUST use ``fullmatch`` — ``match`` would silently accept a
traversal suffix like ``abc\\n../etc``.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import fs_guard
from . import runtime


# -----------------------------------------------------------------------------
# Roots
# -----------------------------------------------------------------------------
# Runtime-agnostic defaults, overridable via --data-dir / --cache-dir
# CLI flags on every entry script (fetch_dc, assemble_dc, render_dc,
# resolve_session, discover_sessions). See runtime.py for details.

DATA_ROOT: Path = runtime.resolve_data_root("investigating-agentforce-d360")
CACHE_ROOT: Path = runtime.resolve_cache_root("investigating-agentforce-d360")


# -----------------------------------------------------------------------------
# Session-ID validation
# -----------------------------------------------------------------------------

# Fully anchored — call sites MUST use fullmatch (tested). Characters allowed:
# alphanumeric + underscore + hyphen, matching both UUIDs and MessagingSession
# IDs.
SESSION_ID_RE = re.compile(r"\A[A-Za-z0-9_\-]+\Z")  # @rule-suppress starter-sec-002 — re.compile, not eval/exec


class PathValidationError(ValueError):
    """Raised when a path segment fails validation.

    Wraps fs_guard's ``ValidationError`` as well as local ``session_id``
    rejections so callers have a single exception type to catch.
    """

    def __init__(self, label: str, reason: str) -> None:
        self.label = label
        self.reason = reason
        super().__init__(f"{label}: {reason}")


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------


def _validate_agent_triple(
    org_id_15: str, agent_api_name: str, agent_version: str
) -> None:
    """Validate the three identity segments. Raises PathValidationError on
    failure, wrapping fs_guard's ValidationError so callers don't need to
    know about fs_guard internals."""
    try:
        fs_guard.validate_org_id_15(org_id_15, label="org_id_15")
        fs_guard.validate_api_name(agent_api_name, label="agent_api_name")
        fs_guard.validate_agent_version(agent_version, label="agent_version")
    except fs_guard.ValidationError as e:
        raise PathValidationError(e.label, e.reason) from e


def validate_session_id(session_id: str) -> None:
    """Validate session_id via SESSION_ID_RE.fullmatch.

    Raises :class:`PathValidationError` on any of: None, non-string, empty,
    regex miss. This is the public validator every caller that composes a
    Path segment from a session-id MUST go through — direct
    ``Path / session_id`` composition bypasses the anchored-regex check.
    """
    if session_id is None:
        raise PathValidationError("session_id", "is None")
    if not isinstance(session_id, str):
        raise PathValidationError(
            "session_id", f"must be str, got {type(session_id).__name__}"
        )
    if not session_id:
        raise PathValidationError("session_id", "must not be empty")
    if not SESSION_ID_RE.fullmatch(session_id):
        preview = session_id[:40]
        raise PathValidationError(
            "session_id",
            f"does not match {SESSION_ID_RE.pattern} (preview={preview!r})",
        )


_validate_session_id = validate_session_id  # backward-compat alias


# -----------------------------------------------------------------------------
# Path builders
# -----------------------------------------------------------------------------


def agent_dir(
    org_id_15: str, agent_api_name: str, agent_version: str
) -> Path:
    """Return ``DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/``.

    All three segments are regex-validated before being joined. Any segment
    containing ``..``, ``/``, or characters outside its regex charclass
    raises ``PathValidationError``.
    """
    _validate_agent_triple(org_id_15, agent_api_name, agent_version)
    return DATA_ROOT / org_id_15 / f"{agent_api_name}__{agent_version}"


def session_dir(
    org_id_15: str,
    agent_api_name: str,
    agent_version: str,
    session_id: str,
) -> Path:
    """Return
    ``DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/<session_id>/``.

    All four segments are validated. The first three go through fs_guard;
    ``session_id`` goes through ``SESSION_ID_RE.fullmatch``. Any rejection
    raises ``PathValidationError``.
    """
    _validate_agent_triple(org_id_15, agent_api_name, agent_version)
    validate_session_id(session_id)
    return (
        DATA_ROOT
        / org_id_15
        / f"{agent_api_name}__{agent_version}"
        / session_id
    )
