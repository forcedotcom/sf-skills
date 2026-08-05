"""Shared helpers for the offline salesforce-development script tests."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def load_module(path: Path, name: str):
    """Load a script module from an exact path under a test-specific name."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_ansi(text: str) -> str:
    """Remove SGR sequences so visual goldens assert on visible text."""
    return _ANSI.sub("", text)
