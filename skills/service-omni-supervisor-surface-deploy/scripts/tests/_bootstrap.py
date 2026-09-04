"""Shared paths + fake-`sf` harness for the supervisor-surface-deploy contract suite.

The fake serves the org guard query, config resolution, existing-surface reads, and record
inserts from env tunables. Org-free and network-free.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-supervisor-surface-deploy"
SCRIPT = f"{SKILL_DIR}/scripts/deploy-and-report.sh"

# Tunables (env):
#   FAKE_SANDBOX       = true|false           (safe_to_write guard; default true)
#   FAKE_CFG_COUNT     = 0|1|2                (OmniSupervisorConfig rows; default 1)
#   FAKE_EXIST_ACTIONS = JSON array of types  (existing OmniSupervisorConfigAction; default [])
#   FAKE_EXIST_TABS    = JSON array of types  (existing OmniSupervisorConfigTab;    default [])
#   FAKE_CREATE_OK     = true|false           (record insert result; default true)
_FAKE_SF = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SANDBOX="${FAKE_SANDBOX:-true}"
CFG_COUNT="${FAKE_CFG_COUNT:-1}"
EXIST_ACTIONS="${FAKE_EXIST_ACTIONS:-[]}"
EXIST_TABS="${FAKE_EXIST_TABS:-[]}"
CREATE_OK="${FAKE_CREATE_OK:-true}"

case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      if [ "$SANDBOX" = "true" ]; then OT="Developer Edition"; else OT="Enterprise Edition"; fi
      echo "{\"status\":0,\"result\":{\"records\":[{\"IsSandbox\":$SANDBOX,\"TrialExpirationDate\":null,\"OrganizationType\":\"$OT\"}]}}"
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfig\b"; then
      case "$CFG_COUNT" in
        0) echo '{"status":0,"result":{"records":[]}}';;
        2) echo '{"status":0,"result":{"records":[{"Id":"0Q2xx0000000001AAA","DeveloperName":"Omni_Supervisor"},{"Id":"0Q2xx0000000002AAA","DeveloperName":"Second_Config"}]}}';;
        *) echo '{"status":0,"result":{"records":[{"Id":"0Q2xx0000000001AAA","DeveloperName":"Omni_Supervisor"}]}}';;
      esac
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigAction"; then
      echo "{\"status\":0,\"result\":{\"records\":$(printf '%s' "$EXIST_ACTIONS" | jq -c 'to_entries | map({OmniSupervisorActionType:.value, DisplayOrder:(.key+1)})')}}"
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigTab"; then
      echo "{\"status\":0,\"result\":{\"records\":$(printf '%s' "$EXIST_TABS" | jq -c 'to_entries | map({OmniSupervisorTabType:.value, DisplayOrder:(.key+1)})')}}"
    else
      echo '{"status":0,"result":{"records":[]}}'
    fi
    exit 0;;
  "data create")
    if [ "$CREATE_OK" = "true" ]; then
      echo '{"status":0,"result":{"id":"0Q3xx0000000001AAA","success":true}}'
    else
      echo '{"status":1,"name":"FIELD_INTEGRITY_EXCEPTION","message":"bad value for restricted picklist field"}'
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
        self._tmp = tempfile.mkdtemp(prefix="supsurface-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
