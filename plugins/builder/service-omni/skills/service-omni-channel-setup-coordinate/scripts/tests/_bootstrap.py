"""Shared paths + fake-`sf` harness for the Omni contract suite (org-free, network-free): drives the bash skills via subprocess asserting exit codes + emitted JSON, with scrubbed-PATH (no sf) and production-org fake-sf fixtures for input-contract and safe_to_write checks."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

# skills/ root is three levels up from this file (.../<skill>/scripts/tests/_bootstrap.py).
SKILLS_ROOT = Path(__file__).resolve().parents[3]

# The 18 scripts under test, relative to skills/.
SCRIPTS = [
    "service-omni-base-settings-configure/scripts/configure-and-report.sh",
    "service-omni-base-settings-configure/scripts/detect-existing.sh",
    "service-omni-channel-setup-coordinate/scripts/integration-driver.sh",
    "service-omni-agent-users-create/scripts/detect-and-create.sh",
    "service-omni-agent-users-create/scripts/detect-existing.sh",
    "service-omni-agent-users-create/scripts/run-create.sh",
    "service-omni-permission-set-assign/scripts/verify-and-assign.sh",
    "service-omni-presence-status-deploy/scripts/deploy-and-report.sh",
    "service-omni-queue-deploy/scripts/verify-and-align.sh",
    "service-omni-queue-members-assign/scripts/verify-and-bind.sh",
    "service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh",
    "service-omni-routing-flow-deploy/scripts/deploy-and-report.sh",
    "service-omni-service-channel-configure/scripts/deploy-and-report.sh",
    "service-omni-supervisor-config-deploy/scripts/deploy-and-report.sh",
    "service-omni-supervisor-permset-assign/scripts/verify-and-assign.sh",
    "service-omni-supervisor-users-create/scripts/detect-and-create.sh",
    "service-omni-supervisor-users-create/scripts/detect-existing.sh",
    "service-omni-supervisor-users-create/scripts/run-create.sh",
]

# A fake `sf` that reports a PRODUCTION customer org, so safe_to_write guards must refuse.
# Also fabricates the OmniChannel settings XML on `project retrieve start` (all toggles
# false) so base-settings' detector returns all_enabled=false and reaches its run guard.
_FAKE_SF = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"
args="$*"
case "$sub" in
  "org display")
    echo '{"status":0,"result":{"username":"fake@prod.org","id":"00Dxx0000000000EAA"}}'; exit 0 ;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM Profile"; then
      echo '{"status":0,"result":{"records":[{"Id":"00exx0000000000AAA","Name":"Standard User"}]}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0 ;;
  "project retrieve")
    mkdir -p force-app/main/default/settings
    cat > force-app/main/default/settings/OmniChannel.settings-meta.xml <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<OmniChannelSettings xmlns="http://soap.sforce.com/2006/04/metadata">
  <enableOmniChannel>false</enableOmniChannel>
  <enableOmniSkillsRouting>false</enableOmniSkillsRouting>
  <enableOmniSecondaryRoutingPriority>false</enableOmniSecondaryRoutingPriority>
  <enableOmniStatusCapModel>false</enableOmniStatusCapModel>
  <enableOmniAutoLoginPrompt>false</enableOmniAutoLoginPrompt>
</OmniChannelSettings>
XML
    echo '{"status":0,"result":{"success":true}}'; exit 0 ;;
  "project deploy")
    echo '{"status":1,"result":{"success":false,"status":"Failed"},"message":"FAKE_SF_DEPLOY_SHOULD_NOT_BE_REACHED"}'; exit 1 ;;
  *)
    echo '{"status":0,"result":{}}'; exit 0 ;;
esac
"""

# A fake `sf` that reports a SANDBOX org - used only by the negative-control test to prove
# the safe_to_write assertions are discriminating (a safe org must NOT trip the refusal).
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    else echo '{"status":0,"result":{"records":[],"totalSize":0}}'; fi; exit 0;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""

# A parameterized fake `sf` for the Voice routing-flow steel-thread tests. It emulates a SANDBOX
# org where the VoiceCall queue + QueueRoutingConfig already resolve, and is tunable via env:
#   FAKE_SC_PRESENT=1   → the ServiceChannel query returns a row (id 0N9...); 0 → empty (fail-closed path)
#   FAKE_FLOW_ACTIVE=1  → an ACTIVE Flow version already exists (drives the reuse/stale-binding path)
#   FAKE_ACTIVE_IDS="..." → the IDs embedded in the retrieved active flow XML (space-separated). When it
#                         contains the current queue+QRC+SC ids the binding "matches" (→ reused);
#                         otherwise it has drifted (→ redeploy).
# Canonical current ids: queue=00G000000000001AAA, qrc=0RC00000000001AAA, sc=0N9000000000001AAA.
_FAKE_SF_VOICE = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SC_PRESENT="${FAKE_SC_PRESENT:-1}"
FLOW_ACTIVE="${FAKE_FLOW_ACTIVE:-0}"
ACTIVE_IDS="${FAKE_ACTIVE_IDS:-00G000000000001AAA 0RC00000000001AAA 0N9000000000001AAA}"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA","apiVersion":"66.0"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM ServiceChannel"; then
      if [ "$SC_PRESENT" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0N9000000000001AAA","MasterLabel":"Phone"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM QueueSobject"; then
      echo '{"status":0,"result":{"records":[{"QueueId":"00G000000000001AAA","Queue":{"DeveloperName":"VoiceQueue"}}],"totalSize":1}}'
    elif printf '%s' "$args" | grep -q "FROM Group"; then
      echo '{"status":0,"result":{"records":[{"Id":"00G000000000001AAA","QueueRoutingConfigId":"0RC00000000001AAA"}],"totalSize":1}}'
    elif printf '%s' "$args" | grep -q "FROM QueueRoutingConfig"; then
      echo '{"status":0,"result":{"records":[{"Id":"0RC00000000001AAA","DeveloperName":"Voice_Routing_Config"}],"totalSize":1}}'
    elif printf '%s' "$args" | grep -q "FROM PendingServiceRouting"; then
      if [ "${FAKE_PROOF:-0}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0RQ00000000001AAA","IsReadyForRouting":true,"RoutingModel":"QueueBased"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM AgentWork"; then
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    elif printf '%s' "$args" | grep -q "FROM SkillRequirement"; then
      # SkillsBased acceptance signal: the rows the platform attached to the PSR (RelatedRecordId=PSR).
      # FAKE_SKILLREQ=1 emulates a WorkSkillRouting rule that matched (RunSBRRules attached a SkillRequirement).
      if [ "${FAKE_SKILLREQ:-0}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0RS00000000001AAA","SkillId":"0PS00000000001AAA","SkillLevel":5}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM User"; then
      echo '{"status":0,"result":{"records":[{"Id":"005000000000001AAA","Username":"agent1@example.com"},{"Id":"005000000000002AAA","Username":"agent2@example.com"}],"totalSize":2}}'
    elif printf '%s' "$args" | grep -q "FROM FlowDefinitionView"; then
      # Post-deploy round-trip active-version proof. Distinct tunable from FLOW_ACTIVE (which drives
      # the PRE-deploy reuse detection): after a deploy the flow becomes active, so default active.
      if [ "${FAKE_FLOW_VIEW_ERROR:-0}" = "1" ]; then
        echo '{"status":1,"name":"EXTERNAL_OBJECT_EXCEPTION","message":"unrelated managed-package flow prevents FlowDefinitionView reads"}'
      elif [ "${FAKE_FLOW_ACTIVE_RT:-1}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"ApiName":"F","ActiveVersionId":"301000000000009AAA"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[{"ApiName":"F","ActiveVersionId":null}],"totalSize":1}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM Flow"; then
      if [ "$FLOW_ACTIVE" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"301000000000001AAA"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project retrieve")
    # Called inside a temp DX project (cwd). Write the "active" flow with the tunable embedded ids
    # so the stale-binding comparator can grep for them.
    flow=$(printf '%s' "$args" | sed -n 's/.*Flow:\([A-Za-z0-9_]*\).*/\1/p'); flow="${flow:-Omni_Route_VoiceCall_Trigger}"
    mkdir -p force-app/main/default/flows
    { echo '<?xml version="1.0" encoding="UTF-8"?>'; echo '<Flow xmlns="http://soap.sforce.com/2006/04/metadata">'
      for id in $ACTIVE_IDS; do echo "  <elementReference>$id</elementReference>"; done
      echo "  <stringValue>${ACTIVE_ROUTING_TYPE:-QueueBased}</stringValue>"
      [ "${ACTIVE_ROUTING_TYPE:-QueueBased}" != "SkillsBased" ] || echo "  <stringValue>${ACTIVE_SKILL_OPTION:-RunSBRRules}</stringValue>"
      echo '</Flow>'; } > "force-app/main/default/flows/${flow}.flow-meta.xml"
    echo '{"status":0,"result":{"success":true}}'; exit 0;;
  "project deploy")
    fn=$(printf '%s' "$args" | sed -n 's/.*Flow:\([A-Za-z0-9_]*\).*/\1/p'); fn="${fn:-Omni_Route_VoiceCall_Trigger}"
    echo "{\"status\":0,\"result\":{\"success\":true,\"files\":[{\"fullName\":\"$fn\",\"type\":\"Flow\",\"state\":\"Created\"}]}}"; exit 0;;
  "data create")
    echo '{"status":0,"result":{"id":"500000000000001AAA","success":true}}'; exit 0;;
  "data delete")
    # Log the deleted record-id so tests can prove runtime-proof cleanup happened.
    [ -n "${FAKE_DELETE_LOG:-}" ] && printf '%s\n' "$args" >> "$FAKE_DELETE_LOG"
    echo '{"status":0,"result":{"id":"500000000000001AAA","success":true}}'; exit 0;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""


def _run(script_rel, args, path_prefix=None, extra_path_scrub=False, extra_env=None):
    """Run a skill script, return (returncode, merged stdout+stderr).

    path_prefix: a dir to prepend to PATH (where a fake `sf` lives).
    extra_path_scrub: when True, build a PATH that excludes any real `sf` so the
      input-contract category can prove rejection happens before the first sf call.
    extra_env: optional dict of env vars overlaid onto the child environment (fake-`sf`
      tunables like FAKE_SC_PRESENT, and cross-skill handoff vars like
      SERVICE_CHANNEL_DEVELOPER_NAME / QUEUE_DEVELOPER_NAME / ROUTING_CONFIG_DEVELOPER_NAME).
    """
    env = dict(os.environ)
    if extra_path_scrub:
        # Keep only dirs that do NOT contain an `sf` executable, so `sf` is absent.
        kept = [d for d in env.get("PATH", "").split(os.pathsep)
                if d and not os.path.exists(os.path.join(d, "sf"))]
        env["PATH"] = os.pathsep.join(kept)
    if path_prefix:
        env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})
    proc = subprocess.run(
        ["bash", str(SKILLS_ROOT / script_rel), *args],
        capture_output=True, text=True, env=env, cwd=str(SKILLS_ROOT),
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class _FakeSfDir:
    """Context manager: a temp dir holding an executable fake `sf` on PATH."""

    def __init__(self, body=_FAKE_SF):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="omni-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
