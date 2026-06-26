"""Runtime override hook for DATA_ROOT / CACHE_ROOT.

Default layout is ``~/.vibe/data/<skill>`` and
``~/.vibe/cache/<skill>`` — runtime-agnostic branding that
follows the repo's "tool-agnostic language" guideline.

Other runtimes (AFV OOTB, Codex, Cursor, OpenCode) can override via
``--data-dir`` / ``--cache-dir`` CLI flags on entry scripts. Those flags
call ``set_*_override()`` BEFORE any pipeline module imports ``paths.py``,
so the resolution helpers below pick up the override.

Three-level rebind contract
---------------------------
Python's ``from X import Y`` snapshots ``Y`` into the importer's local
namespace. Mutating ``X.Y`` later does NOT update the importer's local
binding. Entry scripts that capture ``DATA_ROOT`` / ``CACHE_ROOT`` at
module top must therefore rebind in THREE places after override:

1. ``paths.DATA_ROOT`` — the source of truth
2. ``config.DATA_ROOT`` — the re-export
3. The entry script's own local ``DATA_ROOT`` (via ``global``)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

_DATA_OVERRIDE: Optional[Path] = None
_CACHE_OVERRIDE: Optional[Path] = None


def set_data_root_override(p: Optional[Path]) -> None:
    """Set the data-root override. Pass ``None`` to clear."""
    global _DATA_OVERRIDE
    _DATA_OVERRIDE = p


def set_cache_root_override(p: Optional[Path]) -> None:
    """Set the cache-root override. Pass ``None`` to clear."""
    global _CACHE_OVERRIDE
    _CACHE_OVERRIDE = p


def resolve_data_root(skill_name: str) -> Path:
    """Resolve the data root for ``skill_name``.

    Returns the override if set, else the runtime-agnostic default
    ``~/.vibe/data/<skill_name>``.
    """
    return _DATA_OVERRIDE or (Path.home() / ".vibe" / "data" / skill_name)


def resolve_cache_root(skill_name: str) -> Path:
    """Resolve the cache root for ``skill_name``.

    Returns the override if set, else the runtime-agnostic default
    ``~/.vibe/cache/<skill_name>``.
    """
    return _CACHE_OVERRIDE or (Path.home() / ".vibe" / "cache" / skill_name)
