"""Put scripts/ on sys.path so tests can import the modules under test.

The scripts import each other as top-level modules (e.g. `import semver`), so the
scripts directory itself — not the repo root — must be importable.
"""
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
