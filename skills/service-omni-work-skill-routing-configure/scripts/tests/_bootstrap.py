"""Shared paths + fake-`sf` harness for the work-skill-routing contract suite.

Drives ``configure-and-report.sh`` via ``subprocess`` and asserts on exit codes + emitted JSON.
Org-free and network-free. ``jq`` comes from the real PATH.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-work-skill-routing-configure"
SCRIPT = f"{SKILL_DIR}/scripts/configure-and-report.sh"

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
#   FAKE_STATE_WSR   -> Created|Changed|Unchanged (default Created).
#   FAKE_SKILL_PRESENT -> 1|0 (default 1); 0 blocks on the missing-Skill prereq.
#   FAKE_DEPLOY_FAIL=1 -> deploy fails with a feature-unavailable (INVALID_TYPE) problem.
#   FAKE_RULE_DN     -> fullName echoed in the report (default Case).
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
STATE_WSR="${FAKE_STATE_WSR:-Created}"
RULE_DN="${FAKE_RULE_DN:-Case}"
if [ -n "${FAKE_SF_CALLLOG:-}" ]; then printf '%s\n' "$args" >> "$FAKE_SF_CALLLOG"; fi
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM WorkSkillRouting"; then
      if [ "${FAKE_WSR_INCONCLUSIVE:-0}" = "1" ]; then
        echo '{"status":1,"message":"Transient failure reading WorkSkillRouting metadata"}'
      elif [ "${FAKE_WSR_EXISTING:-0}" = "1" ]; then
        if [ "${FAKE_WSR_NULL_OPTIONALS:-0}" = "1" ]; then
          echo '{"status":0,"result":{"totalSize":1,"records":[{"Metadata":{"masterLabel":"Existing Label","isActive":true,"relatedEntity":"Case","workSkillRoutingAttributes":[{"field":"Case.Priority","skill":"Priority_Support","value":"High","skillLevel":null,"skillPriority":null}]}}]}}'
        else
          echo '{"status":0,"result":{"totalSize":1,"records":[{"Metadata":{"masterLabel":"Existing Label","isActive":true,"relatedEntity":"Case","workSkillRoutingAttributes":[{"field":"Case.Priority","skill":"Priority_Support","value":"High"}]}}]}}'
        fi
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM Skill"; then
      if [ "${FAKE_SKILL_PRESENT:-1}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0C9xx0000000001"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project deploy")
    if printf '%s' "$args" | grep -q "report"; then
      if grep -R -q '>null<' force-app/main/default/workSkillRoutings 2>/dev/null; then
        echo '{"status":0,"result":{"success":false,"id":"0AfXX0000000001","status":"Failed","details":{"componentFailures":[{"problem":"null is not a valid value for the type xsd:int"}]}}}'
      elif [ "${FAKE_DEPLOY_FAIL:-0}" = "1" ]; then
        echo '{"status":0,"result":{"success":false,"id":"0AfXX0000000001","status":"Failed","details":{"componentFailures":[{"problem":"INVALID_TYPE: WorkSkillRouting not available"}]}}}'
      else
        printf '{"status":0,"result":{"success":true,"id":"0AfXX0000000001","status":"Succeeded","files":[{"fullName":"%s","type":"WorkSkillRouting","state":"%s"}]}}' "$RULE_DN" "$STATE_WSR"
      fi
    else
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
        self._tmp = tempfile.mkdtemp(prefix="wsr-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
