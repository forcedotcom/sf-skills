#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = SKILLS_ROOT / "service-omni-command-center-configure/scripts/configure-and-report.sh"
DOCUMENT_TOOL = SKILLS_ROOT / "service-omni-command-center-configure/scripts/settings_document.py"


FAKE_SF = r"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
[ -z "${FAKE_CALL_LOG:-}" ] || printf '%s\n' "$args" >> "$FAKE_CALL_LOG"

if [ "${1:-} ${2:-}" = "org display" ]; then
  echo '{"status":0,"result":{"username":"fake@example.invalid"}}'
  exit 0
fi

if [ "${1:-} ${2:-}" = "project retrieve" ]; then
  mkdir -p force-app/main/default/settings
  target=force-app/main/default/settings/OmniChannel.settings-meta.xml
  if [ -f "$FAKE_STATE_DIR/deployed.xml" ]; then
    cp "$FAKE_STATE_DIR/deployed.xml" "$target"
  else
    {
      echo '<?xml version="1.0" encoding="UTF-8"?>'
      echo '<OmniChannelSettings xmlns="http://soap.sforce.com/2006/04/metadata">'
      echo '  <enableOmniChannel>true</enableOmniChannel>'
      echo '  <unrelatedSetting>true</unrelatedSetting>'
      if [ "${FAKE_API_PRESENT:-1}" = "1" ]; then
        echo "  <enableCommandCenterForServiceV2>${FAKE_V2:-false}</enableCommandCenterForServiceV2>"
        echo "  <enableConversationMonitoring>${FAKE_CONVERSATION:-false}</enableConversationMonitoring>"
        echo "  <enableAgentSneakPeek>${FAKE_AGENT_PEEK:-false}</enableAgentSneakPeek>"
        echo "  <enableClientSneakPeek>${FAKE_CLIENT_PEEK:-false}</enableClientSneakPeek>"
        echo "  <enableWhisperMessaging>${FAKE_WHISPER:-false}</enableWhisperMessaging>"
        echo "  <enableSkillsAndQueueActions>${FAKE_QUEUE_ACTIONS:-false}</enableSkillsAndQueueActions>"
      fi
      echo '</OmniChannelSettings>'
    } > "$target"
  fi
  echo '{"status":0,"result":{"success":true}}'
  exit 0
fi

if [ "${1:-} ${2:-}" = "project deploy" ]; then
  if [ "${FAKE_DEPLOY_FAIL:-0}" = "1" ]; then
    echo '{"status":1,"message":"simulated failure","result":{"success":false,"status":"Failed"}}'
    exit 1
  fi
  source_path=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "--source-dir" ]; then source_path="$2"; break; fi
    shift
  done
  cp "$source_path" "$FAKE_STATE_DIR/deployed.xml"
  touch "$FAKE_STATE_DIR/deployed"
  echo '{"status":0,"result":{"success":true,"status":"Succeeded","id":"0AfFakeDeploy"}}'
  exit 0
fi

if [ "${1:-} ${2:-}" = "data query" ]; then
  if printf '%s' "$args" | grep -q 'FROM Organization'; then
    if [ "${FAKE_PRODUCTION:-0}" = "1" ]; then
      echo '{"status":0,"result":{"records":[{"IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}]}}'
    else
      echo '{"status":0,"result":{"records":[{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    fi
  elif printf '%s' "$args" | grep -q 'FROM FlexiPage'; then
    if { [ -f "$FAKE_STATE_DIR/deployed" ] && [ "${FAKE_SEED_AFTER_DEPLOY:-1}" = "1" ]; } || [ "${FAKE_SEED_PRESENT:-0}" = "1" ]; then
      echo '{"status":0,"result":{"records":[{"Id":"0M0Fake"}],"totalSize":1}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
  elif printf '%s' "$args" | grep -q 'FROM TabDefinition'; then
    if { [ -f "$FAKE_STATE_DIR/deployed" ] && [ "${FAKE_TAB_AFTER_DEPLOY:-1}" = "1" ]; } || [ "${FAKE_TAB_PRESENT:-0}" = "1" ]; then
      echo '{"status":0,"result":{"records":[{"Name":"standard-commandcenterforservicev2"}],"totalSize":1}}'
    else
      echo '{"status":0,"result":{"records":[],"totalSize":0}}'
    fi
  else
    echo '{"status":0,"result":{"records":[],"totalSize":0}}'
  fi
  exit 0
fi

echo '{"status":1,"message":"unexpected fake sf invocation"}'
exit 1
"""


def run_script(*args: str, **environment: str):
    with tempfile.TemporaryDirectory(prefix="command-center-configure-") as directory:
        root = Path(directory)
        sf = root / "sf"
        sf.write_text(FAKE_SF)
        sf.chmod(0o755)
        state = root / "state"
        state.mkdir()
        call_log = root / "calls.log"
        env = dict(os.environ)
        env.update(environment)
        env["FAKE_STATE_DIR"] = str(state)
        env["FAKE_CALL_LOG"] = str(call_log)
        env["PATH"] = str(root) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            ["bash", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(SKILLS_ROOT),
        )
        calls = call_log.read_text() if call_log.exists() else ""
        deployed = (state / "deployed.xml").read_text() if (state / "deployed.xml").exists() else ""
        return result, calls, deployed


class CommandCenterConfigureContracts(unittest.TestCase):
    def test_script_and_python_syntax(self):
        shell = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        compile_result = subprocess.run(
            ["python3", "-c", f"import ast, pathlib; ast.parse(pathlib.Path({str(DOCUMENT_TOOL)!r}).read_text())"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

    def test_run_requires_apply_before_any_sf_call(self):
        result, calls, _ = run_script("run", "test-org")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reason_code"], "apply_required")
        self.assertEqual(calls, "")

    def test_plan_reports_changes_without_deploying(self):
        result, calls, _ = run_script("plan", "test-org")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "action_needed")
        self.assertNotIn("project deploy", calls)

    def test_missing_platform_field_fails_before_deploy(self):
        result, calls, _ = run_script("run", "test-org", "--apply", FAKE_API_PRESENT="0")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reason_code"], "platform_api_unavailable")
        self.assertNotIn("project deploy", calls)

    def test_production_org_is_refused(self):
        result, calls, _ = run_script("run", "test-org", "--apply", FAKE_PRODUCTION="1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reason_code"], "unsafe_target")
        self.assertNotIn("project deploy", calls)

    def test_run_preserves_unrelated_and_unspecified_settings(self):
        result, calls, deployed = run_script(
            "run",
            "test-org",
            "--apply",
            "--agent-sneak-peek",
            "true",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["status"], "configured")
        self.assertIn("project deploy", calls)
        self.assertIn("<unrelatedSetting>true</unrelatedSetting>", deployed)
        self.assertIn("<enableConversationMonitoring>false</enableConversationMonitoring>", deployed)
        self.assertIn("<enableAgentSneakPeek>true</enableAgentSneakPeek>", deployed)
        self.assertIn("<enableCommandCenterForServiceV2>true</enableCommandCenterForServiceV2>", deployed)

    def test_already_ready_is_reused_without_deploy(self):
        result, calls, _ = run_script(
            "run",
            "test-org",
            "--apply",
            FAKE_V2="true",
            FAKE_SEED_PRESENT="1",
            FAKE_TAB_PRESENT="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "reused")
        self.assertNotIn("project deploy", calls)

    def test_persisted_settings_without_seed_are_blocked(self):
        result, _, _ = run_script(
            "run",
            "test-org",
            "--apply",
            FAKE_SEED_AFTER_DEPLOY="0",
            FAKE_TAB_AFTER_DEPLOY="0",
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["reason_code"], "seed_incomplete")
        self.assertEqual(payload["after"]["settings"]["enableCommandCenterForServiceV2"]["value"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
