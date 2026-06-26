"""Shared CLI override helper for d360 entry scripts.

D360 has 5 independent entry scripts (``fetch_dc.py``, ``assemble_dc.py``,
``render_dc.py``, ``resolve_session.py``, ``discover_sessions.py``) — each
needs the same ``--data-dir`` / ``--cache-dir`` flags and the same
3-level namespace rebind. This module factors that duplication into one
helper.

Usage in each entry script::

    from _shared.cli_override import add_cli_flags, apply_overrides

    parser = argparse.ArgumentParser(...)
    parser.add_argument(...)
    add_cli_flags(parser)
    args = parser.parse_args()
    apply_overrides(args, caller_globals=globals())

The ``caller_globals=globals()`` parameter is the magic that lets us
rebind the entry script's own ``DATA_ROOT`` / ``CACHE_ROOT`` snapshot —
without it, only ``paths.X`` and ``config.X`` would update, and the
entry script's local ``DATA_ROOT`` would still point at the default.
"""
from __future__ import annotations

import argparse
from pathlib import Path

_SKILL_NAME = "investigating-agentforce-d360"


def add_cli_flags(parser: argparse.ArgumentParser) -> None:
    """Add --data-dir / --cache-dir flags to the given parser.

    Defaults are runtime-agnostic (``~/.vibe/...``); other
    runtimes (AFV OOTB, Codex, Cursor, OpenCode) override at invocation
    time.
    """
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "Override data root (default: "
            "~/.vibe/data/investigating-agentforce-d360)."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Override cache root (default: "
            "~/.vibe/cache/investigating-agentforce-d360)."
        ),
    )


def apply_overrides(args: argparse.Namespace, caller_globals: dict) -> None:
    """Apply --data-dir / --cache-dir overrides across all 3 namespace levels.

    Must be called BEFORE any pipeline code reads ``DATA_ROOT`` or
    ``CACHE_ROOT``.

    Levels rebound:
      1. ``paths.DATA_ROOT`` (the source of truth)
      2. ``config.DATA_ROOT`` (the re-export)
      3. The caller's own local ``DATA_ROOT`` (via ``caller_globals``)

    Why 3 levels? Python's ``from X import Y`` snapshots ``Y`` into the
    caller's local namespace at import time. Mutating ``X.Y`` later does
    NOT update the caller's local binding. Without the 3rd-level rebind,
    any function in the caller that references ``DATA_ROOT`` still sees
    the default path even after ``paths.DATA_ROOT`` was overridden.
    """
    if not (args.data_dir or args.cache_dir):
        return

    from _shared import runtime, paths
    import config

    if args.data_dir:
        runtime.set_data_root_override(args.data_dir)
        new_data = runtime.resolve_data_root(_SKILL_NAME)
        paths.DATA_ROOT = new_data
        config.DATA_ROOT = new_data
        # Rebind caller's local snapshot, if it captured DATA_ROOT.
        if "DATA_ROOT" in caller_globals:
            caller_globals["DATA_ROOT"] = new_data

    if args.cache_dir:
        runtime.set_cache_root_override(args.cache_dir)
        new_cache = runtime.resolve_cache_root(_SKILL_NAME)
        paths.CACHE_ROOT = new_cache
        if hasattr(config, "CACHE_ROOT"):
            config.CACHE_ROOT = new_cache
        if "CACHE_ROOT" in caller_globals:
            caller_globals["CACHE_ROOT"] = new_cache
