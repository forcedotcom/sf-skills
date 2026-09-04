"""Shared paths + fake-`sf` harness for the skills-based-routing contract suite.

Drives ``configure-and-report.sh`` through ``subprocess`` and asserts on exit codes + emitted JSON.
Org-free and network-free. ``jq`` comes from the real PATH.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-skills-based-routing-configure"
SCRIPT = f"{SKILL_DIR}/scripts/configure-and-report.sh"

# PRODUCTION org - safe_to_write must refuse before any write.
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
  "api request") echo '{"success":false,"errorCode":"FAKE_POST_SHOULD_NOT_BE_REACHED"}'; exit 0;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""

# SANDBOX org. Tunables (all default to the "everything must be created" path):
#   FAKE_SKILL_PRESENT=1 → the Skill already exists (reused); else absent → deploy then re-query.
#   FAKE_BIND_PRESENT=1   → a SkillUser binding already exists for each user (reused); else create.
#   FAKE_BIND_POST_FAIL=1 → the SkillUser POST fails for the second agent.
#   FAKE_BIND_DUPLICATE=1 → the SkillUser POST returns DUPLICATE_VALUE and is reconciled as reused.
# Two active users (005...0001 / 005...0002) are always resolved from the User query.
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_PRESENT="${FAKE_SKILL_PRESENT:-0}"
BIND_PRESENT="${FAKE_BIND_PRESENT:-0}"
BIND_POST_FAIL="${FAKE_BIND_POST_FAIL:-0}"
BIND_DUPLICATE="${FAKE_BIND_DUPLICATE:-0}"
if [ -n "${FAKE_SF_CALLLOG:-}" ]; then printf '%s\n' "$args" >> "$FAKE_SF_CALLLOG"; fi
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM User"; then
      echo '{"status":0,"result":{"records":[{"Id":"0050000000000001AAA","Username":"agent1@example.com","Name":"Agent One"},{"Id":"0050000000000002AAA","Username":"agent2@example.com","Name":"Agent Two"}],"totalSize":2}}'
    elif printf '%s' "$args" | grep -q "FROM SkillUser"; then
      if [ "$BIND_PRESENT" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0C90000000000001AAA","UserId":"0050000000000001AAA"},{"Id":"0C90000000000002AAA","UserId":"0050000000000002AAA"}],"totalSize":2}}'
      else echo '{"status":0,"result":{"records":[],"totalSize":0}}'; fi
    elif printf '%s' "$args" | grep -q "FROM Skill"; then
      if [ "$SKILL_PRESENT" = "1" ] || [ -f "$SELF_DIR/.skill_deployed" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0PS0000000000001AAA"}],"totalSize":1}}'
      else echo '{"status":0,"result":{"records":[],"totalSize":0}}'; fi
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project deploy")
    touch "$SELF_DIR/.skill_deployed"
    echo '{"status":0,"result":{"success":true,"files":[{"fullName":"'"$(printf '%s' "$args" | sed -n 's/.*Skill:\([A-Za-z0-9_]*\).*/\1/p')"'","type":"Skill","state":"Created"}]}}'
    exit 0;;
  "api request")
    if printf '%s' "$args" | grep -q "sobjects/SkillUser"; then
      if [ "$BIND_DUPLICATE" = "1" ]; then
        echo '[{"errorCode":"DUPLICATE_VALUE","message":"duplicate value found: unique constraint (SkillId, UserId)"}]';
      elif [ "$BIND_POST_FAIL" = "1" ] && printf '%s' "$args" | grep -q "0050000000000002AAA"; then
        echo '[{"errorCode":"FIELD_CUSTOM_VALIDATION_EXCEPTION","message":"forced binding failure"}]';
      else echo '{"success":true,"id":"0C90000000000009AAA"}'; fi
    else
      echo '{"success":true,"id":"000000000000000AAA"}'
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
        self._tmp = tempfile.mkdtemp(prefix="sbr-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
