"""Tests for the --data-dir / --cache-dir override mechanism in d360.

D360 has 5 entry scripts (``fetch_dc.py``, ``assemble_dc.py``, ``render_dc.py``,
``resolve_session.py``, ``discover_sessions.py``) — each invokes the shared
``_shared.cli_override.apply_overrides()`` helper. Three things must be true
after ``--data-dir <path>`` is parsed:

1. ``paths.DATA_ROOT`` points at the override.
2. ``config.DATA_ROOT`` points at the override (re-export).
3. The entry script's local ``DATA_ROOT`` (captured via
   ``from config import DATA_ROOT``) points at the override.

Without all three, callers reading ``DATA_ROOT`` from the entry script see
stale defaults.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import _bootstrap  # noqa: F401 — sys.path setup

import config  # type: ignore
from _shared import paths, runtime  # type: ignore
from _shared.cli_override import add_cli_flags, apply_overrides  # type: ignore


def _reset_overrides() -> None:
    """Clear runtime overrides so the test starts from a known state."""
    runtime.set_data_root_override(None)
    runtime.set_cache_root_override(None)
    default_data = runtime.resolve_data_root("investigating-agentforce-d360")
    default_cache = runtime.resolve_cache_root("investigating-agentforce-d360")
    paths.DATA_ROOT = default_data
    paths.CACHE_ROOT = default_cache
    config.DATA_ROOT = default_data


def test_default_paths_under_vibe() -> None:
    """No overrides → DATA_ROOT points at ~/.vibe/data/investigating-agentforce-d360."""
    _reset_overrides()
    expected = Path.home() / ".vibe" / "data" / "investigating-agentforce-d360"
    assert paths.DATA_ROOT == expected
    assert config.DATA_ROOT == expected


def test_data_dir_override_rebinds_paths_and_config(tmp_path: Path) -> None:
    """--data-dir /tmp/x → paths.DATA_ROOT and config.DATA_ROOT update."""
    _reset_overrides()
    override = tmp_path / "custom-data"
    ap = argparse.ArgumentParser()
    add_cli_flags(ap)
    args = ap.parse_args(["--data-dir", str(override)])
    # Simulate what an entry script does — pass its own globals().
    fake_caller_globals: dict = {"DATA_ROOT": paths.DATA_ROOT}
    apply_overrides(args, caller_globals=fake_caller_globals)

    assert paths.DATA_ROOT == override, "paths.DATA_ROOT not rebound"
    assert config.DATA_ROOT == override, "config.DATA_ROOT not rebound"
    assert fake_caller_globals["DATA_ROOT"] == override, "caller's local DATA_ROOT not rebound"
    _reset_overrides()


def test_cache_dir_override_rebinds_paths(tmp_path: Path) -> None:
    """--cache-dir /tmp/y → paths.CACHE_ROOT updates."""
    _reset_overrides()
    override = tmp_path / "custom-cache"
    ap = argparse.ArgumentParser()
    add_cli_flags(ap)
    args = ap.parse_args(["--cache-dir", str(override)])
    fake_caller_globals: dict = {}
    apply_overrides(args, caller_globals=fake_caller_globals)
    assert paths.CACHE_ROOT == override
    _reset_overrides()


def test_no_override_leaves_defaults_intact() -> None:
    """No flags → no mutation."""
    _reset_overrides()
    expected = Path.home() / ".vibe" / "data" / "investigating-agentforce-d360"
    ap = argparse.ArgumentParser()
    add_cli_flags(ap)
    args = ap.parse_args([])
    fake_caller_globals: dict = {"DATA_ROOT": paths.DATA_ROOT}
    apply_overrides(args, caller_globals=fake_caller_globals)
    assert paths.DATA_ROOT == expected
    assert config.DATA_ROOT == expected
    assert fake_caller_globals["DATA_ROOT"] == expected


def test_caller_globals_without_data_root_key_is_safe(tmp_path: Path) -> None:
    """Entry scripts that don't capture DATA_ROOT (e.g. discover_sessions.py)
    must not crash when apply_overrides is called with their globals."""
    _reset_overrides()
    override = tmp_path / "custom-data"
    ap = argparse.ArgumentParser()
    add_cli_flags(ap)
    args = ap.parse_args(["--data-dir", str(override)])
    # Empty dict — simulates discover_sessions which doesn't bind DATA_ROOT.
    fake_caller_globals: dict = {}
    apply_overrides(args, caller_globals=fake_caller_globals)  # must not raise
    assert paths.DATA_ROOT == override
    assert "DATA_ROOT" not in fake_caller_globals  # didn't add it
    _reset_overrides()
