#!/usr/bin/env python3
"""Offline tests for the Help Agent authoring-capability preflight."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "helpagent_authoring_preflight.py"
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[5]
COORDINATOR_SKILL = PLUGIN_ROOT / "skills" / "service-helpagent-coordinate" / "SKILL.md"
OVERLAY_PATCH = COORDINATOR_SKILL.with_name("SKILL.overlay.patch")
FLAT_SKILL = REPO_ROOT / "skills" / "service-helpagent-coordinate" / "SKILL.md"
QUALIFIED_OWNER = "agentforce-adlc:agentforce-generate"
POST_GATE_RUNTIME_GUIDANCE = (
    COORDINATOR_SKILL.parent / "assets" / "help-agent-spec.md",
    COORDINATOR_SKILL.parent / "references" / "agent-script.md",
    COORDINATOR_SKILL.parent / "references" / "output-report-format.md",
)

FAKE_SF = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
log_path = Path(os.environ["FAKE_SF_LOG"])
with log_path.open("a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")

if args[:2] == ["org", "display"]:
    mode = os.environ.get("FAKE_SF_ORG", "ready")
    if mode == "ready":
        print(json.dumps({"status": 0, "result": {"username": "builder@example.test", "orgId": "00D000000000001"}}))
        raise SystemExit(0)
    if mode == "transient":
        print(json.dumps({"status": 1, "name": "NetworkError", "message": "ETIMEDOUT"}))
        raise SystemExit(1)
    if mode == "malformed":
        print("not-json")
        raise SystemExit(0)
    if mode == "cli_error":
        print(json.dumps({"status": 1, "name": "UnknownCommand", "message": "unsupported local CLI response"}))
        raise SystemExit(1)
    print(json.dumps({"status": 1, "name": "NamedOrgNotFound", "message": "No authorization information found"}))
    raise SystemExit(1)

if args[:3] == ["agent", "validate", "authoring-bundle"]:
    expected = Path.cwd() / "force-app" / "main" / "default" / "aiAuthoringBundles" / "HelpAgentAuthoringPreflight"
    required = [
        Path.cwd() / "sfdx-project.json",
        expected / "HelpAgentAuthoringPreflight.agent",
        expected / "HelpAgentAuthoringPreflight.bundle-meta.xml",
    ]
    if not all(path.is_file() for path in required):
        print(json.dumps({"status": 1, "name": "AABNotFound", "message": "probe fixture missing"}))
        raise SystemExit(1)

    mode = os.environ.get("FAKE_SF_VALIDATE", "ready")
    if mode == "ready":
        print(json.dumps({"status": 0, "result": {"success": True}}))
        raise SystemExit(0)
    if mode == "unavailable":
        print(json.dumps({"status": 2, "name": "AgentApiNotFound", "message": "Validation/compilation API returned HTTP 404. The API endpoint may not be available in your org or region."}))
        raise SystemExit(2)
    if mode == "unavailable_opaque":
        print(json.dumps({"status": 2, "name": "UnexpectedErrorShape", "message": "Request rejected"}))
        raise SystemExit(2)
    if mode == "auth":
        print(json.dumps({"status": 1, "name": "InvalidJwtToken", "message": "HTTP 401: JWT expired"}))
        raise SystemExit(1)
    if mode == "transient":
        print(json.dumps({"status": 3, "name": "ServerError", "message": "Validation/compilation API returned HTTP 500"}))
        raise SystemExit(3)
    if mode == "compile":
        print(json.dumps({"status": 1, "name": "CompileAgentScriptError", "message": "Unsupported probe syntax"}))
        raise SystemExit(1)
    print("unexpected non-json response")
    raise SystemExit(1)

print(json.dumps({"status": 1, "name": "UnexpectedCommand", "message": "unexpected command"}))
raise SystemExit(1)
'''


class HelpAgentAuthoringPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="helpagent-preflight-test-")
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.sf_path = self.bin_dir / "sf"
        self.sf_path.write_text(FAKE_SF, encoding="utf-8")
        self.sf_path.chmod(self.sf_path.stat().st_mode | stat.S_IXUSR)
        self.log_path = self.root / "sf-calls.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_preflight(self, *, org: str = "ready", validate: str = "ready") -> tuple[subprocess.CompletedProcess[str], dict]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}",
                "FAKE_SF_LOG": str(self.log_path),
                "FAKE_SF_ORG": org,
                "FAKE_SF_VALIDATE": validate,
            }
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target-org", "target-org"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        payload = json.loads(result.stdout)
        return result, payload

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines()]

    def test_ready_runs_only_org_display_then_non_mutating_validation_and_cleans_temp_project(self) -> None:
        result, payload = self.run_preflight()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["outcome"], "ready")
        self.assertTrue(payload["safeToProceed"])
        self.assertIn("does not prove Service Agent", payload["limitation"])

        calls = self.calls()
        self.assertEqual(calls[0]["args"], ["org", "display", "--target-org", "target-org", "--json"])
        self.assertEqual(
            calls[1]["args"],
            [
                "agent",
                "validate",
                "authoring-bundle",
                "--api-name",
                "HelpAgentAuthoringPreflight",
                "--target-org",
                "target-org",
                "--json",
            ],
        )
        all_args = " ".join(arg for call in calls for arg in call["args"])
        for forbidden in (" deploy ", " publish ", " activate ", " adl ", " create ", " update ", " delete "):
            self.assertNotIn(forbidden, f" {all_args} ")
        self.assertFalse(Path(calls[1]["cwd"]).exists(), "temporary probe project must be removed")

    def test_org_auth_failure_stops_before_compiler_probe(self) -> None:
        result, payload = self.run_preflight(org="auth")

        self.assertEqual(result.returncode, 20)
        self.assertEqual(payload["outcome"], "authentication_or_org_access_failure")
        self.assertFalse(payload["safeToProceed"])
        self.assertEqual(len(self.calls()), 1)

    def test_documented_compiler_404_is_authoring_unavailable(self) -> None:
        result, payload = self.run_preflight(validate="unavailable")

        self.assertEqual(result.returncode, 21)
        self.assertEqual(payload["outcome"], "agentforce_authoring_unavailable_or_not_entitled")
        self.assertIn("admin or Support", payload["remediation"])

    def test_documented_compiler_exit_code_2_is_authoritative_without_error_text(self) -> None:
        result, payload = self.run_preflight(validate="unavailable_opaque")

        self.assertEqual(result.returncode, 21)
        self.assertEqual(payload["outcome"], "agentforce_authoring_unavailable_or_not_entitled")

    def test_compiler_auth_failure_is_not_misclassified_as_entitlement(self) -> None:
        result, payload = self.run_preflight(validate="auth")

        self.assertEqual(result.returncode, 20)
        self.assertEqual(payload["outcome"], "authentication_or_org_access_failure")

    def test_transient_service_failure_is_resumable(self) -> None:
        result, payload = self.run_preflight(validate="transient")

        self.assertEqual(result.returncode, 22)
        self.assertEqual(payload["outcome"], "transient_cli_or_service_failure")
        self.assertIn("Retry this checkpoint", payload["remediation"])

    def test_probe_compile_failure_is_inconclusive_not_entitlement(self) -> None:
        result, payload = self.run_preflight(validate="compile")

        self.assertEqual(result.returncode, 23)
        self.assertEqual(payload["outcome"], "capability_cannot_be_conclusively_verified")
        self.assertIn("Do not proceed", payload["remediation"])

    def test_unexpected_success_response_is_inconclusive(self) -> None:
        result, payload = self.run_preflight(org="malformed")

        self.assertEqual(result.returncode, 23)
        self.assertEqual(payload["outcome"], "capability_cannot_be_conclusively_verified")
        self.assertEqual(len(self.calls()), 1)

    def test_unclassified_org_cli_failure_is_inconclusive_not_authentication(self) -> None:
        result, payload = self.run_preflight(org="cli_error")

        self.assertEqual(result.returncode, 23)
        self.assertEqual(payload["outcome"], "capability_cannot_be_conclusively_verified")
        self.assertEqual(len(self.calls()), 1)

    def test_coordinator_enforces_dependency_probe_org_probe_then_owner_delegation(self) -> None:
        skill = COORDINATOR_SKILL.read_text(encoding="utf-8")

        capability = skill.index("### Step 1 — Resolve the owning capability")
        org_probe = skill.index("### Step 2 — Probe the selected org without changing it")
        delegation = skill.index("### Step 3 — Delegate to the owner")
        readiness = skill.index("### Readiness check (silent, MANDATORY, do not reorder)")
        self.assertLess(capability, org_probe)
        self.assertLess(org_probe, delegation)
        self.assertLess(delegation, readiness)
        self.assertIn("Salesforce CLI availability does **not** prove", skill)
        self.assertIn("/salesforce-development:plugin-install agentforce-adlc", skill)
        self.assertIn("/reload-plugins", skill)
        self.assertIn("There is no coordinator fallback", skill)
        self.assertIn("do not hand-author or reconstruct `.agent` YAML", skill)
        self.assertIn("Skill-tool dispatch to `agentforce-adlc:agentforce-generate`", skill)
        self.assertIn("delegate Agentforce-specific readiness", skill)
        self.assertIn("to `agentforce-adlc:agentforce-generate`", skill)
        self.assertIn("scripts/helpagent_dependency_preflight.py", skill)
        self.assertIn("documented `claude plugin list --json`", skill)
        self.assertIn("agentforce-adlc@claude-plugins-official", skill)
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}/../agentforce-adlc", skill)

    def test_plugin_only_behavior_is_declared_as_an_overlay(self) -> None:
        self.assertTrue(OVERLAY_PATCH.is_file())
        self.assertNotEqual(
            FLAT_SKILL.read_text(encoding="utf-8"),
            COORDINATOR_SKILL.read_text(encoding="utf-8"),
        )

    def test_runtime_guidance_keeps_agentforce_delegation_plugin_qualified(self) -> None:
        skill = COORDINATOR_SKILL.read_text(encoding="utf-8")
        self.assertIn(f"(use {QUALIFIED_OWNER})", skill)
        self.assertIn(f"created by `{QUALIFIED_OWNER}`", skill)

        # relatedSkills is repository metadata and must remain the canonical
        # flat skill directory name rather than a runtime dispatch identity.
        self.assertIn('    - "agentforce-generate"', skill)
        self.assertNotIn(f'    - "{QUALIFIED_OWNER}"', skill)

        for path in POST_GATE_RUNTIME_GUIDANCE:
            with self.subTest(path=path.relative_to(COORDINATOR_SKILL.parent)):
                guidance = path.read_text(encoding="utf-8")
                self.assertIn(QUALIFIED_OWNER, guidance)
                self.assertNotIn("agentforce-generate", guidance.replace(QUALIFIED_OWNER, ""))


if __name__ == "__main__":
    unittest.main()
