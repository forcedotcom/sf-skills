"""Shared paths + fake-`sf` harness for the sidebar-configure contract suite (org-free, network-free): drives enable-and-report.sh via subprocess with scrubbed-PATH and production/sandbox fake-sf fixtures (un-pinned/pinned app, console-app auto-detect cardinality)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = "service-omni-sidebar-configure"
SCRIPT = f"{SKILL_DIR}/scripts/enable-and-report.sh"

# PRODUCTION org - the safe_to_write guard must refuse before any write.
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
#   FAKE_APP_PINNED=1   → the retrieved CustomApplication already has isOmniPinnedViewEnabled=true
#                         (reused path). Default 0 → the element is absent (insert-before-label path).
#   FAKE_CONSOLE_APPS=N → number of deployable custom Lightning console apps returned by metadata
#                         discovery (0 → blocked, 1 → adopt, >1 → blocked). Default 1.
# A successful deploy touches a marker next to the fake sf; the subsequent re-retrieve then reports
# the flag as true, so the enable → deploy → post-verify path converges statefully.
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PINNED="${FAKE_APP_PINNED:-0}"
CONSOLE_APPS="${FAKE_CONSOLE_APPS:-1}"
if [ -n "${FAKE_SF_CALLLOG:-}" ]; then printf '%s\n' "$args" >> "$FAKE_SF_CALLLOG"; fi
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "org list")
    case "$CONSOLE_APPS" in
      0) echo '{"status":0,"result":[{"fullName":"standard__LightningService"}]}' ;;
      1) echo '{"status":0,"result":[{"fullName":"standard__LightningService"},{"fullName":"Demo_Console"}]}' ;;
      *) echo '{"status":0,"result":[{"fullName":"standard__LightningService"},{"fullName":"Demo_Console"},{"fullName":"Other_Console"}]}' ;;
    esac
    exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM AppDefinition"; then
      if printf '%s' "$args" | grep -q -- "--use-tooling-api"; then
        echo '{"status":1,"name":"INVALID_TYPE","message":"AppDefinition is not supported by Tooling API"}'
        exit 1
      fi
      case "$CONSOLE_APPS" in
        0) echo '{"status":0,"result":{"records":[],"totalSize":0}}';;
        1) echo '{"status":0,"result":{"records":[{"DeveloperName":"Demo_Console","Label":"Demo Console"}],"totalSize":1}}';;
        *) echo '{"status":0,"result":{"records":[{"DeveloperName":"Demo_Console","Label":"Demo Console"},{"DeveloperName":"Other_Console","Label":"Other Console"}],"totalSize":2}}';;
      esac
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project retrieve")
    appname=$(printf '%s' "$args" | sed -n 's/.*CustomApplication:\([A-Za-z0-9_]*\).*/\1/p'); appname="${appname:-Demo_Console}"
    pinned=false
    if [ "$APP_PINNED" = "1" ] || [ -f "$SELF_DIR/.deployed" ]; then pinned=true; fi
    if [ "$pinned" = "true" ]; then
      cat > "./${appname}.app-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <isOmniPinnedViewEnabled>true</isOmniPinnedViewEnabled>
    <label>${appname}</label>
    <navType>Console</navType>
    <uiType>Lightning</uiType>
</CustomApplication>
XML
    else
      cat > "./${appname}.app-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>${appname}</label>
    <navType>Console</navType>
    <uiType>Lightning</uiType>
</CustomApplication>
XML
    fi
    echo '{"status":0,"result":{"success":true}}'; exit 0;;
  "project deploy")
    if printf '%s' "$args" | grep -q "report"; then
      echo '{"status":0,"result":{"success":true,"status":"Succeeded","id":"0AfXX0000000001"}}'
    else
      touch "$SELF_DIR/.deployed"
      echo '{"status":0,"result":{"success":true,"status":"Succeeded","id":"0AfXX0000000001"}}'
    fi
    exit 0;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""


def run(args, path_prefix=None, scrub_sf=False, extra_env=None):
    """Run the orchestrator; return (returncode, merged stdout+stderr)."""
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
    """Context manager: a temp dir holding an executable fake `sf` first on PATH."""

    def __init__(self, body=_FAKE_SF_PROD):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="sidebar-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
