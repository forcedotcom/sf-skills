"""Test bootstrap — loads the hyphenated skill scripts as importable modules.

The skill's scripts (``apply-casesettings.py``, ``validate-casesettings.py``)
have hyphens in their names, so they can't be imported with a normal
``import``. Every ``test_*.py`` in this directory does::

    from . import _bootstrap
    apply_mod = _bootstrap.load_apply()
    validate_mod = _bootstrap.load_validate()

to get the loaded modules. Loading is cached so repeated calls are cheap and
return the same module object.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# scripts/tests/_bootstrap.py → scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent

_CACHE: dict[str, object] = {}


def _load(module_name: str, filename: str):
    if module_name in _CACHE:
        return _CACHE[module_name]
    path = _SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {filename} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CACHE[module_name] = module
    return module


def load_apply():
    """Return the loaded ``apply-casesettings.py`` module."""
    return _load("apply_casesettings", "apply-casesettings.py")


def load_validate():
    """Return the loaded ``validate-casesettings.py`` module."""
    return _load("validate_casesettings", "validate-casesettings.py")
