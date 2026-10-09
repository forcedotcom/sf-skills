"""Shared paths + fake-`sf` harness for the queue-members-assign contract suite.

Drives ``verify-and-bind.sh`` via ``subprocess`` and asserts on exit codes + emitted JSON.
Org-free and network-free. ``jq`` comes from the real PATH.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-queue-members-assign"
SCRIPT = f"{SKILL_DIR}/scripts/verify-and-bind.sh"

# org display succeeds, but the Organization safe_to_write query FAILS (non-zero, stderr-only).
# Reproduces an auth/network/API failure: the script must emit structured blocked JSON on stdout
# instead of a silent `set -e` exit.
_FAKE_SF_ORG_QUERY_FAILS = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo "ERROR running data query: INVALID_SESSION_ID" >&2
      exit 1
    fi
    echo '{"status":0,"result":{"records":[],"totalSize":0}}'; exit 0;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""


def run(args, path_prefix=None, scrub_sf=False, extra_env=None):
    env = dict(os.environ)
    if scrub_sf:
        kept = [d for d in env.get("PATH", "").split(os.pathsep)
                if d and not os.path.exists(os.path.join(d, "sf"))]
        env["PATH"] = os.pathsep.join(kept)
    if path_prefix:
        env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})
    proc = subprocess.run(
        ["bash", str(SKILLS_ROOT / SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(SKILLS_ROOT),
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class FakeSf:
    def __init__(self, body=_FAKE_SF_ORG_QUERY_FAILS):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="qm-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
