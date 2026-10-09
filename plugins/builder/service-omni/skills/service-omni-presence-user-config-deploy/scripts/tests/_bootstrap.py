"""Shared paths + fake-`sf` harness for the presence-user-config contract suite.

Drives ``deploy-and-report.sh`` via ``subprocess`` and asserts on exit codes + emitted JSON.
Org-free and network-free. ``jq`` comes from the real PATH.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-presence-user-config-deploy"
SCRIPT = f"{SKILL_DIR}/scripts/deploy-and-report.sh"

# PRODUCTION org - safe_to_write must refuse before any deploy.
_FAKE_SF_PROD = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}]}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project deploy") echo '{"status":1,"result":{"success":false},"message":"FAKE_SF_DEPLOY_SHOULD_NOT_BE_REACHED"}'; exit 1;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""

# SANDBOX org. Tunables:
#   FAKE_STATE_DR / FAKE_STATE_PUC → Created|Changed|Unchanged (default Created).
#   FAKE_DEPLOY_FAIL=1 → deploy fails with an OmniChannel-shaped problem.
#   FAKE_CONFIG_DN / FAKE_DR_DN → fullNames echoed in the report (default the script defaults).
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
STATE_DR="${FAKE_STATE_DR:-Created}"
STATE_PUC="${FAKE_STATE_PUC:-Created}"
CONFIG_DN="${FAKE_CONFIG_DN:-Omni_Demo_Presence_Config}"
DR_DN="${FAKE_DR_DN:-Training}"
if [ -n "${FAKE_SF_CALLLOG:-}" ]; then printf '%s\n' "$args" >> "$FAKE_SF_CALLLOG"; fi
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM User"; then
      echo '{"status":0,"result":{"records":[{"Username":"resolved.byid@example.com"}],"totalSize":1}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project deploy")
    if printf '%s' "$args" | grep -q "report"; then
      if [ "${FAKE_DEPLOY_FAIL:-0}" = "1" ]; then
        PROB="${FAKE_DEPLOY_PROBLEM:-INVALID_TYPE: OmniChannel not enabled}"
        printf '{"status":0,"result":{"success":false,"id":"0AfXX0000000001","status":"Failed","details":{"componentFailures":[{"problem":"%s"}]}}}' "$PROB"
      else
        printf '{"status":0,"result":{"success":true,"id":"0AfXX0000000001","status":"Succeeded","files":[{"fullName":"%s","type":"PresenceDeclineReason","state":"%s"},{"fullName":"%s","type":"PresenceUserConfig","state":"%s"}]}}' "$DR_DN" "$STATE_DR" "$CONFIG_DN" "$STATE_PUC"
      fi
    else
      # async start → return a job id so the script polls report.
      echo '{"status":0,"result":{"id":"0AfXX0000000001","status":"Queued"}}'
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
    def __init__(self, body=_FAKE_SF_PROD):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="puc-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
