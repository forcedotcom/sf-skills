"""Shared paths + fake-`sf` harness for the command-center-analyze contract suite.

Read-only skill: the fake serves SOQL/Tooling query responses only. Org-free and network-free.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-command-center-analyze"
SCRIPT = f"{SKILL_DIR}/scripts/analyze.sh"

# Tunables (env):
#   FAKE_CAP   = true|false|unknown  (V2 capability probe on PermissionSet)
#   FAKE_SEED  = true|false|unknown  (seeded FlexiPage, tooling)
#   FAKE_TAB   = true|false|unknown  (V2 TabDefinition)
#   FAKE_LEG   = integer             (OmniSupervisorConfig count; default 0)
#   FAKE_SUP_LOOKUP = true|missing|unknown  (supervisor User lookup)
#   FAKE_SUP_PERM = true|false|unknown      (supervisor permission query)
_FAKE_SF = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
CAP="${FAKE_CAP:-true}"
SEED="${FAKE_SEED:-false}"
TAB="${FAKE_TAB:-false}"
LEG="${FAKE_LEG:-0}"
SUP_PERM="${FAKE_SUP_PERM:-false}"
SUP_LOOKUP="${FAKE_SUP_LOOKUP:-true}"
emit_ok() { echo "{\"status\":0,\"result\":{\"records\":$1,\"totalSize\":$2}}"; }
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q -- "--use-tooling-api"; then
      if printf '%s' "$args" | grep -q "FROM FlexiPage"; then
        case "$SEED" in
          true)  emit_ok '[{"Id":"0M0xx0000000001AAA"}]' 1;;
          false) emit_ok '[]' 0;;
          *)     echo '{"status":1,"name":"UNEXPECTED","message":"tooling read failed"}';;
        esac
      elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfig"; then
        if [ "$LEG" -gt 0 ] 2>/dev/null; then emit_ok '[{"Id":"0L0xx0000000001AAA"}]' "$LEG"; else emit_ok '[]' 0; fi
      else
        emit_ok '[]' 0
      fi
      exit 0
    fi
    # non-tooling SOQL
    if printf '%s' "$args" | grep -q "FROM PermissionSetAssignment"; then
      case "$SUP_PERM" in
        true)    emit_ok '[{"Id":"0Paxx0000000001AAA"}]' 1;;
        false)   emit_ok '[]' 0;;
        *)       echo '{"status":1,"name":"UNEXPECTED","message":"permission read failed"}';;
      esac
    elif printf '%s' "$args" | grep -q "FROM PermissionSet"; then
      case "$CAP" in
        true)    emit_ok '[{"Id":"0PSxx0000000001AAA"}]' 1;;
        false)   echo '{"status":1,"name":"INVALID_FIELD","message":"No such column '"'"'PermissionsCommandCenterForServiceUser'"'"' on entity PermissionSet"}';;
        *)       echo '{"status":1,"name":"UNEXPECTED","message":"connection reset"}';;
      esac
    elif printf '%s' "$args" | grep -q "FROM TabDefinition"; then
      case "$TAB" in
        true)  emit_ok '[{"Name":"standard-commandcenterforservicev2"}]' 1;;
        false) emit_ok '[]' 0;;
        *)     echo '{"status":1,"name":"UNEXPECTED","message":"tab read failed"}';;
      esac
    elif printf '%s' "$args" | grep -q "FROM User"; then
      case "$SUP_LOOKUP" in
        true)    emit_ok '[{"Id":"0050000000000009AAA"}]' 1;;
        missing) emit_ok '[]' 0;;
        *)       echo '{"status":1,"name":"UNEXPECTED","message":"user read failed"}';;
      esac
    else
      emit_ok '[]' 0
    fi
    exit 0;;
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
    def __init__(self, body=_FAKE_SF):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="ccdetect-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
