"""Shared paths + fake-`sf` harness for the escalation-configure contract suite (org-free, network-free; drives the bash+Node skill via subprocess, asserting exit codes + emitted JSON)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

# skills/ root is three levels up (.../<skill>/scripts/tests/_bootstrap.py).
SKILLS_ROOT = Path(__file__).resolve().parents[3]

SKILL_DIR = "service-agentforce-human-escalation-configure"
SCRIPT = f"{SKILL_DIR}/scripts/verify-and-configure.sh"
# The ITSM coordinator's advancement gate - exercised for the escalation verdict mapping.
VERDICT_SCRIPT = "service-itsm-agentic-setup-agentforce-coordinate/scripts/verify-child-verdict.mjs"

# A fake `sf` that reports a PRODUCTION customer org so the safe_to_write guard must refuse.
# A fake `project deploy` returns a sentinel so a guard bypass would surface loudly.
_FAKE_SF_PROD = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}]}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "project deploy")
    echo '{"status":1,"result":{"success":false},"message":"FAKE_SF_DEPLOY_SHOULD_NOT_BE_REACHED"}'; exit 1;;
  *) echo '{"status":0,"result":{}}'; exit 0;;
esac
"""

# A fake `sf` for a SANDBOX org where every deterministic surface already resolves (active agent,
# MessagingChannel, queue + QueueSobject + QRC, active RoutingFlow) and `project retrieve` writes
# canEscalate=true / an outboundRouteName so the doc-driven surfaces verify true. The FAKE_* env vars
# below toggle each surface off to exercise the block/create paths; a GroupMember POST flips membership
# via a marker file (stateful convergence); canonical QRC id 0RC000000000001AAA makes create+adopt converge.
_FAKE_SF_SANDBOX = r"""#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_ACTIVE="${FAKE_AGENT_ACTIVE:-1}"
MC_PRESENT="${FAKE_MC_PRESENT:-1}"
QS_PRESENT="${FAKE_QS_PRESENT:-1}"
QRC_PRESENT="${FAKE_QRC_PRESENT:-1}"
QUEUE_PRESENT="${FAKE_QUEUE_PRESENT:-1}"
QUEUE_BOUND="${FAKE_QUEUE_BOUND:-1}"
QUEUE_MEMBERS="${FAKE_QUEUE_MEMBERS:-1}"
ROUTE_TYPE="${FAKE_ROUTE_TYPE:-OmniChannelFlow}"
ROUTE_SURFACE="${FAKE_ROUTE_SURFACE:-Messaging}"
# FAKE_GENAI_MD=0 → org exposes no GenAiPlugin/GenAiPlannerBundle metadata types (the escalation
# preflight must then BLOCK before any write). Default 1 → the authoring metadata is exposed.
GENAI_MD="${FAKE_GENAI_MD:-1}"
# FAKE_MODEL pins the authoring model the org advertises: classic (GenAiPlugin+GenAiPlannerBundle),
# nga (AiAuthoringBundle, no GenAiPlannerBundle), or none. Empty => derive from GENAI_MD (1=classic,0=none).
MODEL="${FAKE_MODEL:-}"
if [ -z "$MODEL" ]; then [ "$GENAI_MD" = "1" ] && MODEL="classic" || MODEL="none"; fi
TARGET_MODEL="${FAKE_TARGET_MODEL:-$MODEL}"
# FAKE_NGA_SURFACE=1 => retrieved AiAuthoringBundle contains connection messaging: + @utils.escalate
# (Service escalation surface present). 0 => neither (surface missing => INCOMPLETE on nga).
NGA_SURFACE="${FAKE_NGA_SURFACE:-1}"
RC_ID="0RC000000000001AAA"
# Opt-in call log: when FAKE_SF_CALLLOG points at a file, append every invocation's args so a
# test can prove which mutations did (or did NOT) happen - e.g. idempotent re-runs create nothing.
if [ -n "${FAKE_SF_CALLLOG:-}" ]; then printf '%s\n' "$args" >> "$FAKE_SF_CALLLOG"; fi
_has_members() { [ "$QUEUE_MEMBERS" = "1" ] || [ -f "$SELF_DIR/.gm_added" ]; }
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}'; exit 0;;
  "org list")
    if printf '%s' "$args" | grep -q "metadata-types"; then
      case "$MODEL" in
        classic) echo '{"status":0,"result":{"metadataObjects":[{"xmlName":"Bot"},{"xmlName":"GenAiPlugin"},{"xmlName":"GenAiPlannerBundle"}]}}';;
        nga)     echo '{"status":0,"result":{"metadataObjects":[{"xmlName":"Bot"},{"xmlName":"AiAuthoringBundle"},{"xmlName":"GenAiPlugin"}]}}';;
        both)    echo '{"status":0,"result":{"metadataObjects":[{"xmlName":"Bot"},{"xmlName":"AiAuthoringBundle"},{"xmlName":"GenAiPlugin"},{"xmlName":"GenAiPlannerBundle"}]}}';;
        *)       echo '{"status":0,"result":{"metadataObjects":[{"xmlName":"Bot"},{"xmlName":"BotTemplate"},{"xmlName":"BotBlock"}]}}';;
      esac
    else
      echo '{"status":0,"result":{}}'
    fi
    exit 0;;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM BotDefinition"; then
      if [ "$AGENT_ACTIVE" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0Xx000000000001AAA","DeveloperName":"Support_Agent","MasterLabel":"Support Agent","BotVersions":{"records":[{"Id":"04V000000000001AAA","Status":"Active"}]}}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[{"Id":"0Xx000000000001AAA","DeveloperName":"Support_Agent","MasterLabel":"Support Agent","BotVersions":{"records":[{"Id":"04V000000000001AAA","Status":"Inactive"}]}}],"totalSize":1}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM MessagingChannel"; then
      if [ "$MC_PRESENT" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0M9000000000001AAA","DeveloperName":"Support_Chat"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM QueueSobject"; then
      if [ "$QS_PRESENT" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"0Q9000000000001AAA"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM QueueRoutingConfig"; then
      if [ "$QRC_PRESENT" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"'"$RC_ID"'","DeveloperName":"Human_Support_Queue_RC"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM FlowDefinitionView"; then
      echo '{"status":0,"result":{"records":[{"ApiName":"Human_Escalation_Outbound_Flow","ActiveVersionId":"301000000000001AAA"}],"totalSize":1}}'
    elif printf '%s' "$args" | grep -q "FROM GroupMember"; then
      if _has_members; then
        echo '{"status":0,"result":{"records":[{"UserOrGroupId":"005000000000001AAA"}],"totalSize":1}}'
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM User"; then
      if printf '%s' "$args" | grep -q "COUNT(Id)"; then
        if _has_members; then
          echo '{"status":0,"result":{"records":[{"c":1}],"totalSize":1}}'
        else
          echo '{"status":0,"result":{"records":[{"c":0}],"totalSize":1}}'
        fi
      else
        # Id-by-username (assignment path) → an active user row.
        echo '{"status":0,"result":{"records":[{"Id":"005000000000002AAA"}],"totalSize":1}}'
      fi
    elif printf '%s' "$args" | grep -q "FROM Group"; then
      if [ "$QUEUE_PRESENT" = "1" ]; then
        if [ "$QUEUE_BOUND" = "1" ]; then
          echo '{"status":0,"result":{"records":[{"Id":"00G000000000001AAA","QueueRoutingConfigId":"'"$RC_ID"'"}],"totalSize":1}}'
        else
          echo '{"status":0,"result":{"records":[{"Id":"00G000000000001AAA","QueueRoutingConfigId":null}],"totalSize":1}}'
        fi
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
    exit 0;;
  "api request")
    # Data API POST/PATCH (QueueSobject bind, QueueRoutingConfig create, Group.QueueRoutingConfigId bind).
    if printf '%s' "$args" | grep -q "sobjects/QueueRoutingConfig"; then
      echo '{"success":true,"id":"'"$RC_ID"'"}'
    elif printf '%s' "$args" | grep -q "sobjects/QueueSobject"; then
      echo '{"success":true,"id":"0Q9000000000009AAA"}'
    elif printf '%s' "$args" | grep -q "sobjects/GroupMember"; then
      touch "$SELF_DIR/.gm_added"
      echo '{"success":true,"id":"0GM00000000001AAA"}'
    else
      # Group PATCH → 204 empty body on success.
      echo ''
    fi
    exit 0;;
  "project retrieve")
    dir=$(printf '%s' "$args" | sed -n 's/.*--target-metadata-dir[ =]\([^ ]*\).*/\1/p'); dir="${dir:-.}"
    mkdir -p "$dir"
    if printf '%s' "$args" | grep -q "AiAuthoringBundle:"; then
      [ "$TARGET_MODEL" = "nga" ] || [ "$TARGET_MODEL" = "both" ] || exit 1
      if [ "$NGA_SURFACE" = "1" ]; then
        cat > "$dir/Support_Agent.agent" <<'AGENT'
start_agent support_agent:
    connection messaging:
        end_user_client: customer_web_client
    reasoning:
        actions:
            human_handoff: @utils.escalate
                description: "Transfer the user to a human agent."
AGENT
      else
        cat > "$dir/Support_Agent.agent" <<'AGENT'
start_agent support_agent:
    reasoning:
        actions:
            answer: @actions.AnswerQuestionWithKnowledge
AGENT
      fi
    elif printf '%s' "$args" | grep -q "GenAiPlugin:"; then
      echo '<canEscalate>true</canEscalate>' > "$dir/plugin.xml"
    elif printf '%s' "$args" | grep -q "GenAiPlannerBundle:"; then
      [ "$TARGET_MODEL" = "classic" ] || [ "$TARGET_MODEL" = "both" ] || exit 1
      cat > "$dir/bundle.xml" <<BXML
<GenAiPlannerBundle>
  <plannerSurfaces>
    <surfaceType>${ROUTE_SURFACE}</surfaceType>
    <outboundRouteConfigs>
      <escalationMessage>Transferring you to a live support agent.</escalationMessage>
      <outboundRouteName>Human_Escalation_Outbound_Flow</outboundRouteName>
      <outboundRouteType>${ROUTE_TYPE}</outboundRouteType>
    </outboundRouteConfigs>
  </plannerSurfaces>
</GenAiPlannerBundle>
BXML
    fi
    echo '{"status":0,"result":{"success":true}}'; exit 0;;
  "project deploy")
    echo '{"status":0,"result":{"success":true,"files":[{"fullName":"Human_Escalation_Outbound_Flow","type":"Flow","state":"Created"}]}}'; exit 0;;
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


def run_node(script_rel, args):
    """Run a bundled Node helper; return (returncode, stdout)."""
    proc = subprocess.run(
        ["node", str(SKILLS_ROOT / script_rel), *args],
        capture_output=True, text=True, cwd=str(SKILLS_ROOT),
    )
    return proc.returncode, (proc.stdout or "")


class FakeSf:
    """Context manager: a temp dir holding an executable fake `sf` first on PATH."""

    def __init__(self, body=_FAKE_SF_PROD):
        self._body = body
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="esc-fake-sf-")
        sf = Path(self._tmp) / "sf"
        sf.write_text(self._body)
        sf.chmod(0o755)
        return self._tmp

    def __exit__(self, *exc):
        import shutil
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
