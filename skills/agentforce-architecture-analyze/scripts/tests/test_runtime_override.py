"""Tests for the --data-dir / --cache-dir override mechanism.

Three things must be true after ``--data-dir <path>`` is parsed:

1. ``paths.DATA_ROOT`` points at the override.
2. ``config.DATA_ROOT`` points at the override (re-export).
3. ``main.DATA_ROOT`` points at the override (the local ``from config import
   DATA_ROOT`` snapshot at module top).

If any of the three is stale, callers reading ``DATA_ROOT`` from that module
see the default path. ``main.py:2221`` writes ``str(DATA_ROOT)`` into the
``.emit_ctx.json`` file consumed by ``emit_result.py`` — getting that wrong
means the RESULT block points users at the wrong directory.
"""
from __future__ import annotations

from pathlib import Path

from . import _bootstrap  # noqa: F401 — sys.path setup

import config  # type: ignore
import main  # type: ignore
from _shared import paths, runtime  # type: ignore


def _reset_overrides() -> None:
    """Clear runtime overrides so the test starts from a known state."""
    runtime.set_data_root_override(None)
    runtime.set_cache_root_override(None)
    # Re-resolve all three namespace levels back to defaults.
    default_data = runtime.resolve_data_root("investigating-agentforce-architecture")
    default_cache = runtime.resolve_cache_root("investigating-agentforce-architecture")
    paths.DATA_ROOT = default_data
    paths.CACHE_ROOT = default_cache
    config.DATA_ROOT = default_data
    config.CACHE_ROOT = default_cache
    config.PROBE_CACHE_ROOT = default_cache / "_channel_probe"
    main.DATA_ROOT = default_data


def test_default_paths_under_vibe() -> None:
    """No overrides → all 3 namespaces point at ~/.vibe/."""
    _reset_overrides()
    expected_data = Path.home() / ".vibe" / "data" / "investigating-agentforce-architecture"
    expected_cache = Path.home() / ".vibe" / "cache" / "investigating-agentforce-architecture"
    assert paths.DATA_ROOT == expected_data
    assert config.DATA_ROOT == expected_data
    assert main.DATA_ROOT == expected_data
    assert paths.CACHE_ROOT == expected_cache
    assert config.CACHE_ROOT == expected_cache


def test_data_dir_override_rebinds_three_namespaces(tmp_path: Path) -> None:
    """--data-dir /tmp/x → all 3 namespaces (paths, config, main) update."""
    _reset_overrides()
    override = tmp_path / "custom-data"
    args = main.parse_args([
        "--org-alias", "myorg",
        "--agent", "MyAgent",
        "--work-dir", str(tmp_path / "work"),
        "--data-dir", str(override),
    ])
    main._apply_path_overrides(args)
    # All three namespace levels must equal the override path.
    assert paths.DATA_ROOT == override, "paths.DATA_ROOT not rebound"
    assert config.DATA_ROOT == override, "config.DATA_ROOT not rebound"
    assert main.DATA_ROOT == override, "main.DATA_ROOT not rebound"
    _reset_overrides()


def test_cache_dir_override_rebinds_paths_and_config(tmp_path: Path) -> None:
    """--cache-dir /tmp/y → paths.CACHE_ROOT, config.CACHE_ROOT, and PROBE_CACHE_ROOT update."""
    _reset_overrides()
    override = tmp_path / "custom-cache"
    args = main.parse_args([
        "--org-alias", "myorg",
        "--agent", "MyAgent",
        "--work-dir", str(tmp_path / "work"),
        "--cache-dir", str(override),
    ])
    main._apply_path_overrides(args)
    assert paths.CACHE_ROOT == override
    assert config.CACHE_ROOT == override
    assert config.PROBE_CACHE_ROOT == override / "_channel_probe"
    _reset_overrides()


def test_no_override_leaves_defaults_intact(tmp_path: Path) -> None:
    """Running with no override flags must not mutate anything."""
    _reset_overrides()
    expected_data = Path.home() / ".vibe" / "data" / "investigating-agentforce-architecture"
    args = main.parse_args([
        "--org-alias", "myorg",
        "--agent", "MyAgent",
        "--work-dir", str(tmp_path / "work"),
    ])
    main._apply_path_overrides(args)
    assert paths.DATA_ROOT == expected_data
    assert config.DATA_ROOT == expected_data
    assert main.DATA_ROOT == expected_data
