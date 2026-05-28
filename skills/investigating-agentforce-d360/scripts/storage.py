"""Shared per-session JSON writer.

Every Data Cloud artifact lands under the nested layout:

    DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/<session_id>/<source>.<name>.json

One save, one shape, one directory convention — imported by every caller.

**Security contract:**
All four path segments (``org_id_15``, ``agent_api_name``, ``agent_version``,
``session_id``) flow through ``paths.session_dir(...)``, which validates
each via fs_guard (regex) before the join. A ``..`` or ``/`` in any
segment raises ``paths.PathValidationError`` — direct
``DATA_ROOT / session_id`` composition is unreachable from this module.

Source-prefix convention:
    Flat directory, prefix filenames with provenance so an `ls` on the
    per-session dir tells you where each artifact came from:

        dc.sessions.json       — from Data Cloud
        dc.interactions.json

    Baking the prefix into the API (vs. leaving it to filename discipline)
    makes it impossible to forget — callers pass ``source`` + ``name``,
    never a raw filename.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import paths


def save(
    data: list[dict] | dict,
    org_id_15: str,
    agent_api_name: str,
    agent_version: str,
    session_id: str,
    source: str,
    name: str,
) -> Path:
    """Write JSON under the nested session dir. Returns the target path.

    Signature:
        save(data, org_id_15, agent_api_name, agent_version, session_id,
             source, name) -> Path

    ``source`` is the leading filename segment for provenance — callers
    pass ``"dc"``. ``name`` is the bare artifact name, no extension —
    ``.json`` is appended.

    Raises ``paths.PathValidationError`` if any of the four identity
    segments fails validation.
    """
    # paths.session_dir() validates org_id_15, agent_api_name, agent_version
    # (via fs_guard) and session_id (via SESSION_ID_RE.fullmatch). Any bad
    # input raises PathValidationError before we touch the filesystem.
    target = paths.session_dir(
        org_id_15, agent_api_name, agent_version, session_id
    )
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{source}.{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    _write_breadcrumb(org_id_15, agent_api_name, agent_version, session_id)
    return path


def _write_breadcrumb(
    org_id_15: str,
    agent_api_name: str,
    agent_version: str,
    session_id: str,
) -> None:
    """Write ``<org>/_sessions/<sid>.link`` pointing at the session dir.

    Plain text, no symlink (Windows-safe). Content is the relative path
    ``../<agent>__<ver>/<sid>\\n``. Idempotent — overwriting with the
    same content is a no-op semantically. Silent on failure; breadcrumbs
    are best-effort (a missing breadcrumb doesn't break the write,
    only handoff-session discovery).
    """
    try:
        link_dir = paths.DATA_ROOT / org_id_15 / "_sessions"
        link_dir.mkdir(parents=True, exist_ok=True)
        link_path = link_dir / f"{session_id}.link"
        link_path.write_text(
            f"../{agent_api_name}__{agent_version}/{session_id}\n"
        )
    except OSError:
        pass
