"""Org-independent contract tests for the service-omni-* skills: bash -n syntax, input-contract rejection before the first sf call, safe_to_write refusal, Apex-template token fidelity, and packaged asset well-formedness - all org-free and network-free (CI-safe)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
import xml.dom.minidom
from pathlib import Path

# Hyphenated dir name blocks relative imports; add our dir to sys.path so this file runs standalone.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import _bootstrap  # noqa: E402
from _bootstrap import SKILLS_ROOT, SCRIPTS, _FakeSfDir, _FAKE_SF_SANDBOX, _FAKE_SF_VOICE, _run  # noqa: E402

_FLOW_SCRIPT = "service-omni-routing-flow-deploy/scripts/deploy-and-report.sh"


class SyntaxTests(unittest.TestCase):
    """(1) Every script must parse under `bash -n`."""

    def test_all_scripts_parse(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                proc = subprocess.run(
                    ["bash", "-n", str(SKILLS_ROOT / script)],
                    capture_output=True, text=True,
                )
                self.assertEqual(
                    proc.returncode, 0,
                    f"{script} failed bash -n: {proc.stderr.strip()}",
                )


class InputContractTests(unittest.TestCase):
    """(2) Deterministic rejection BEFORE the first sf call.

    Every case runs with `sf` scrubbed off PATH - if a script reached an sf call it
    would fail differently (command-not-found), so a clean expected-exit + expected
    error substring proves the guard fires first.
    """

    def assert_reject(self, script, args, want_exit, needle):
        rc, out = _run(script, args, extra_path_scrub=True)
        self.assertEqual(rc, want_exit, f"{script} {args} → exit {rc} (want {want_exit}); out={out[:200]}")
        self.assertRegex(out, re.compile(re.escape(needle), re.IGNORECASE),
                         f"{script} {args} output missing '{needle}'; out={out[:200]}")

    # --- missing required org-alias / too few args ---
    def test_missing_org_rejected(self):
        cases = [
            ("service-omni-base-settings-configure/scripts/detect-existing.sh", [], 1, "error"),
            ("service-omni-agent-users-create/scripts/detect-existing.sh", [], 1, "error"),
            ("service-omni-agent-users-create/scripts/run-create.sh", [], 1, "Usage"),
            ("service-omni-supervisor-users-create/scripts/run-create.sh", [], 1, "Usage"),
            ("service-omni-permission-set-assign/scripts/verify-and-assign.sh", [], 1, "Usage"),
            ("service-omni-supervisor-permset-assign/scripts/verify-and-assign.sh", [], 1, "Usage"),
            ("service-omni-queue-members-assign/scripts/verify-and-bind.sh", [], 1, "Usage"),
            ("service-omni-queue-deploy/scripts/verify-and-align.sh", [], 1, "Missing"),
            ("service-omni-service-channel-configure/scripts/deploy-and-report.sh", [], 1, "Missing"),
            ("service-omni-presence-status-deploy/scripts/deploy-and-report.sh", [], 1, "Missing"),
            ("service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh", [], 1, "Missing"),
            ("service-omni-supervisor-config-deploy/scripts/deploy-and-report.sh", [], 1, "Missing"),
            ("service-omni-base-settings-configure/scripts/configure-and-report.sh", [], 1, "Missing"),
            ("service-omni-agent-users-create/scripts/detect-and-create.sh", [], 1, "Missing"),
            ("service-omni-supervisor-users-create/scripts/detect-and-create.sh", [], 1, "Missing"),
            (_FLOW_SCRIPT, [], 1, "Missing"),
        ]
        for script, args, want, needle in cases:
            with self.subTest(script=script):
                self.assert_reject(script, args, want, needle)

    # --- invalid mode (plan|run) ---
    def test_invalid_mode_rejected(self):
        for script in [
            "service-omni-base-settings-configure/scripts/configure-and-report.sh",
            "service-omni-agent-users-create/scripts/detect-and-create.sh",
        ]:
            with self.subTest(script=script):
                self.assert_reject(script, ["bogus", "myorg"], 1, "Invalid mode")

    # --- coordinator flag / mode / arg validation (exit 2) ---
    def test_coordinator_arg_validation(self):
        drv = "service-omni-channel-setup-coordinate/scripts/integration-driver.sh"
        self.assert_reject(drv, [], 2, "plan or --run")
        self.assert_reject(drv, ["--frobnicate", "myorg"], 2, "Unknown flag")
        self.assert_reject(drv, ["--run"], 2, "Missing required")
        self.assert_reject(drv, ["--run", "org;rm -rf /"], 2, "Invalid org-alias")
        self.assert_reject(drv, ["--run", "myorg", "0"], 2, "Invalid count")
        self.assert_reject(drv, ["--run", "myorg", "3", "Widget"], 2, "Unsupported")

    # --- out-of-range count ---
    def test_out_of_range_count_rejected(self):
        cases = [
            ("service-omni-agent-users-create/scripts/detect-existing.sh", ["myorg", "0"], "range"),
            ("service-omni-agent-users-create/scripts/detect-existing.sh", ["myorg", "11"], "range"),
            ("service-omni-permission-set-assign/scripts/verify-and-assign.sh", ["myorg", "11"], "Invalid count"),
            ("service-omni-queue-members-assign/scripts/verify-and-bind.sh", ["myorg", "CaseQueue", "11"], "Invalid count"),
            ("service-omni-supervisor-permset-assign/scripts/verify-and-assign.sh", ["myorg", "6"], "Invalid count"),
            ("service-omni-supervisor-config-deploy/scripts/deploy-and-report.sh", ["myorg", "6"], "Invalid supervisor_count"),
        ]
        for script, args, needle in cases:
            with self.subTest(script=script, args=args):
                self.assert_reject(script, args, 1, needle)

    # --- injection-shaped DeveloperName rejected before any sf call ---
    def test_injection_queue_name_rejected(self):
        self.assert_reject(
            "service-omni-queue-deploy/scripts/verify-and-align.sh",
            ["myorg", "Case", "Case_Routing_Config", "bad name;DROP"],
            1, "Invalid queue_developer_name",
        )

    # --- F10: injection-shaped routing_config_dn (3rd positional) rejected before any sf call ---
    def test_injection_routing_config_dn_rejected(self):
        # A non-empty 3rd arg that is not a well-formed DeveloperName must reject up front.
        self.assert_reject(
            "service-omni-queue-deploy/scripts/verify-and-align.sh",
            ["myorg", "Case", "Case_Routing'; DROP", "CaseQueue"],
            1, "Invalid routing_config_developer_name",
        )
        # Leading digit is also invalid (DeveloperName must start with a letter).
        self.assert_reject(
            "service-omni-queue-deploy/scripts/verify-and-align.sh",
            ["myorg", "Case", "9bad", "CaseQueue"],
            1, "Invalid routing_config_developer_name",
        )

    # --- injection-shaped overflow-assignee (fallback user) rejected before any sf call ---
    def test_injection_overflow_assignee_rejected(self):
        # 7th positional is the overflow/fallback assignee; a non-Username/Id token must reject
        # up front (it is interpolated into a User SOQL WHERE), before the auth/org query.
        self.assert_reject(
            "service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh",
            ["myorg", "MostAvailable", "Case_Routing_Config", "Case Routing Config", "5", "1", "bad;DROP TABLE"],
            1, "Invalid overflow-assignee",
        )

    # --- F10: injection-shaped queue_developer_name in queue-members rejected before any sf call ---
    def test_injection_queue_member_queue_dn_rejected(self):
        self.assert_reject(
            "service-omni-queue-members-assign/scripts/verify-and-bind.sh",
            ["myorg", "bad name;DROP", "3"],
            1, "Invalid queue_developer_name",
        )

    # --- F10: injection-shaped permission-set name rejected before the org-mutating query ---
    # The PS-name guard sits AFTER the `sf org display` auth check, so a fake sf must be present
    # for auth to pass; the guard then rejects an injection-shaped name before any data query.
    def test_injection_permission_set_name_rejected(self):
        cases = [
            "service-omni-permission-set-assign/scripts/verify-and-assign.sh",
            "service-omni-supervisor-permset-assign/scripts/verify-and-assign.sh",
        ]
        with _FakeSfDir(body=_FAKE_SF_SANDBOX) as fake_dir:
            for script in cases:
                with self.subTest(script=script):
                    rc, out = _run(script, ["myorg", "1", "Bad Name; DROP"], path_prefix=fake_dir)
                    self.assertEqual(rc, 1, f"{script} → exit {rc} (want 1); out={out[:200]}")
                    self.assertRegex(
                        out, re.compile("Invalid permission-set name", re.IGNORECASE),
                        f"{script} output missing injection rejection; out={out[:200]}",
                    )

    # --- unsupported sObject type (exit 2) ---
    def test_unsupported_sobject_rejected(self):
        cases = [
            "service-omni-service-channel-configure/scripts/deploy-and-report.sh",
            "service-omni-presence-status-deploy/scripts/deploy-and-report.sh",
            "service-omni-queue-deploy/scripts/verify-and-align.sh",
        ]
        for script in cases:
            with self.subTest(script=script):
                self.assert_reject(script, ["myorg", "Widget"], 2, "Unsupported")

    # --- routing-flow: invalid --target (exit 2) + injection-shaped flow name (exit 1) ---
    def test_routing_flow_invalid_target_rejected(self):
        self.assert_reject(_FLOW_SCRIPT, ["myorg", "--target", "Widget", "--trigger"], 2, "Invalid --target")

    def test_routing_flow_injection_flow_name_rejected(self):
        self.assert_reject(_FLOW_SCRIPT, ["myorg", "bad;name", "--trigger"], 1, "Invalid flow_developer_name")


class SafeToWriteTests(unittest.TestCase):
    """(3) A production customer org is hard-refused before any mutation."""

    #: (label, script, args) - every mutating skill + the coordinator.
    REFUSERS = [
        ("base-settings (run)", "service-omni-base-settings-configure/scripts/configure-and-report.sh", ["run", "myorg"]),
        ("agent-users (run)", "service-omni-agent-users-create/scripts/detect-and-create.sh", ["run", "myorg", "3"]),
        ("supervisor-users (run)", "service-omni-supervisor-users-create/scripts/detect-and-create.sh", ["run", "myorg", "1"]),
        ("service-channel", "service-omni-service-channel-configure/scripts/deploy-and-report.sh", ["myorg", "Case"]),
        ("qrc", "service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh", ["myorg"]),
        ("queue-deploy", "service-omni-queue-deploy/scripts/verify-and-align.sh", ["myorg", "Case"]),
        ("queue-members", "service-omni-queue-members-assign/scripts/verify-and-bind.sh", ["myorg", "CaseQueue", "3"]),
        ("presence", "service-omni-presence-status-deploy/scripts/deploy-and-report.sh", ["myorg", "Case"]),
        ("permset-assign", "service-omni-permission-set-assign/scripts/verify-and-assign.sh", ["myorg", "3"]),
        ("supervisor-permset", "service-omni-supervisor-permset-assign/scripts/verify-and-assign.sh", ["myorg", "1"]),
        ("supervisor-config", "service-omni-supervisor-config-deploy/scripts/deploy-and-report.sh", ["myorg", "1"]),
        ("routing-flow (trigger)", "service-omni-routing-flow-deploy/scripts/deploy-and-report.sh", ["myorg", "--target", "VoiceCall", "--trigger"]),
        ("coordinator (run)", "service-omni-channel-setup-coordinate/scripts/integration-driver.sh", ["--run", "myorg", "3", "Case"]),
    ]

    _REFUSAL_RE = re.compile(r'refus|production|"?safe_to_write"?[:= ]*false', re.IGNORECASE)

    def test_production_org_refused(self):
        with _FakeSfDir() as fake_dir:
            for label, script, args in self.REFUSERS:
                with self.subTest(skill=label):
                    rc, out = _run(script, args, path_prefix=fake_dir)
                    self.assertNotEqual(rc, 0, f"{label}: expected non-zero (refusal), got 0; out={out[:200]}")
                    self.assertRegex(out, self._REFUSAL_RE,
                                     f"{label}: non-zero exit but no refusal signal; out={out[:220]}")
                    self.assertNotIn("FAKE_SF_DEPLOY_SHOULD_NOT_BE_REACHED", out,
                                     f"{label}: reached a deploy despite production guard")

    def test_sandbox_org_not_refused_negative_control(self):
        """Discriminating check: a SANDBOX org must NOT trip the production refusal.
        Proves the assertion above isn't trivially green. We pick a skill whose guard
        is query-only (qrc) so on a sandbox it proceeds past the guard (and fails
        later on missing fake data) rather than refusing."""
        with _FakeSfDir(body=_FAKE_SF_SANDBOX) as fake_dir:
            rc, out = _run(
                "service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh",
                ["myorg"], path_prefix=fake_dir,
            )
            self.assertNotRegex(
                out, re.compile(r'refus|"?safe_to_write"?[:= ]*false', re.IGNORECASE),
                f"sandbox org unexpectedly triggered a production refusal; out={out[:220]}",
            )


class ApexTemplateTests(unittest.TestCase):
    """(4) User-create Apex templates: token coverage + clean resolution."""

    TEMPLATES = [
        "service-omni-agent-users-create/assets/create-users.apex.template",
        "service-omni-supervisor-users-create/assets/create-supervisors.apex.template",
    ]
    EXPECTED_TOKENS = {"__COUNT__", "__PROFILE_ID__", "__SUFFIX__"}

    def test_token_set_matches_substitutions(self):
        for tpl in self.TEMPLATES:
            with self.subTest(template=tpl):
                text = (SKILLS_ROOT / tpl).read_text()
                tokens = set(re.findall(r"__[A-Z_]+__", text))
                self.assertEqual(
                    tokens, self.EXPECTED_TOKENS,
                    f"{tpl} tokens {tokens} != run-create.sh substitutions {self.EXPECTED_TOKENS}",
                )

    def test_resolves_to_token_free_apex(self):
        for tpl in self.TEMPLATES:
            with self.subTest(template=tpl):
                text = (SKILLS_ROOT / tpl).read_text()
                resolved = (text.replace("__COUNT__", "3")
                                .replace("__PROFILE_ID__", "00exx0000000000AAA")
                                .replace("__SUFFIX__", "abc12345"))
                leftover = re.findall(r"__[A-Z_]+__", resolved)
                self.assertEqual(leftover, [], f"{tpl} left residual tokens: {set(leftover)}")


class DeployAssetTests(unittest.TestCase):
    """(5) Packaged deploy assets are well-formed."""

    def test_all_xml_well_formed(self):
        xmls = sorted(SKILLS_ROOT.glob("service-omni-*/assets/**/*.xml"))
        self.assertTrue(xmls, "expected at least one packaged .xml asset")
        for asset in xmls:
            with self.subTest(asset=str(asset.relative_to(SKILLS_ROOT))):
                try:
                    xml.dom.minidom.parse(str(asset))
                except Exception as e:  # noqa: BLE001 - surface any parse failure as a test failure
                    self.fail(f"{asset} is not well-formed XML: {e}")

    def test_all_json_parses(self):
        jsons = sorted(SKILLS_ROOT.glob("service-omni-*/assets/**/*.json"))
        self.assertTrue(jsons, "expected at least one packaged .json asset")
        for j in jsons:
            with self.subTest(asset=str(j.relative_to(SKILLS_ROOT))):
                try:
                    json.loads(j.read_text())
                except Exception as e:  # noqa: BLE001
                    self.fail(f"{j} is not valid JSON: {e}")


class VoiceRoutingFlowTests(unittest.TestCase):
    """(6) Voice steel-thread behaviors for service-omni-routing-flow-deploy, driven by the
    parameterized _FAKE_SF_VOICE sandbox org (org-free, network-free, deterministic).

    Covers:
      - fail closed when the ServiceChannel does not resolve.
      - reuse only when the active flow's embedded bindings still match; redeploy on drift.
      - runtime proof is blocking under --require-proof, and the throwaway record is cleaned up.
    """

    #: Cross-skill handoff the coordinator supplies - the SAME channel/queue/QRC discovered upstream.
    HANDOFF = {
        "SERVICE_CHANNEL_DEVELOPER_NAME": "sfdc_phone",
        "QUEUE_DEVELOPER_NAME": "VoiceQueue",
        "ROUTING_CONFIG_DEVELOPER_NAME": "Voice_Routing_Config",
        # Drive the async poll with zero real waiting.
        "OMNI_PROOF_POLL_TRIES": "1",
        "OMNI_PROOF_POLL_SLEEP": "0",
    }

    def _run_flow(self, args, env):
        merged = dict(self.HANDOFF)
        merged.update(env)
        with _FakeSfDir(body=_FAKE_SF_VOICE) as fake_dir:
            return _run(_FLOW_SCRIPT, args, path_prefix=fake_dir, extra_env=merged)

    # --- unresolved ServiceChannel must block, never deploy a flow with an empty channel id ---
    def test_p0_fail_closed_when_service_channel_missing(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "0"},
        )
        self.assertEqual(rc, 1, f"expected block on missing ServiceChannel; out={out[:300]}")
        self.assertRegex(out, re.compile(r'ServiceChannel .*not found', re.IGNORECASE), out[:300])
        self.assertIn('"status": "blocked"', out)

    # --- happy deploy: channel present, no active flow yet → Created ---
    def test_deploys_when_channel_present(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0"},
        )
        self.assertEqual(rc, 0, f"expected clean deploy; out={out[:300]}")
        self.assertRegex(out, re.compile(r'"status":\s*"created"'), out[:300])
        # The resolved ServiceChannel id (0N9...) from the handoff channel must be embedded, not empty.
        self.assertIn("0N9000000000001AAA", out)
        # P1 round-trip proof: the reported active version id must come from FlowDefinitionView.
        self.assertIn("301000000000009AAA", out)
        self.assertRegex(out, re.compile(r'"flow_active_version_id":\s*"301000000000009AAA"'), out[:600])

    # --- P1 round-trip proof: deploy ok but NO active flow version → block (never claim active) ---
    def test_blocks_when_no_active_flow_version_after_deploy(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0", "FAKE_FLOW_ACTIVE_RT": "0"},
        )
        self.assertEqual(rc, 1, f"expected block when no active version; out={out[:300]}")
        self.assertRegex(out, re.compile(r'"status":\s*"blocked"'), out[:300])
        self.assertRegex(out, re.compile(r'active version', re.IGNORECASE), out[:500])

    def test_uses_tooling_flow_when_flow_definition_view_fails(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "1", "FAKE_FLOW_VIEW_ERROR": "1"},
        )
        self.assertEqual(rc, 0, f"expected Tooling Flow fallback; out={out[:500]}")
        self.assertRegex(out, re.compile(r'"status":\s*"reused"'), out[:500])
        self.assertRegex(out, re.compile(r'"flow_active_version_id":\s*"301000000000001AAA"'), out[:700])

    # --- P1 idempotency: active flow whose bindings still match → reused (no redeploy) ---
    def test_reuse_when_active_bindings_match(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "1"},  # default FAKE_ACTIVE_IDS = current ids
        )
        self.assertEqual(rc, 0, f"expected reuse; out={out[:300]}")
        self.assertRegex(out, re.compile(r'"status":\s*"reused"'), out[:300])

    # --- P1 stale repair: active flow bound to DIFFERENT ids → must redeploy, not reuse ---
    def test_redeploy_when_active_bindings_stale(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "1",
             "FAKE_ACTIVE_IDS": "00GSTALE0000001AAA 0RCSTALE000001AAA 0N9STALE0000001AAA"},
        )
        self.assertEqual(rc, 0, f"expected redeploy on drift; out={out[:300]}")
        self.assertNotRegex(out, re.compile(r'"status":\s*"reused"'),
                            f"stale bindings must NOT be reused; out={out[:300]}")
        self.assertRegex(out, re.compile(r'"status":\s*"created"'), out[:300])

    # --- P1 runtime proof BLOCKING: --require-proof with no PSR/AW must block ---
    def test_require_proof_blocks_without_routing_evidence(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--require-proof"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0", "FAKE_PROOF": "0"},
        )
        self.assertEqual(rc, 1, f"expected block when proof required but absent; out={out[:300]}")
        self.assertRegex(out, re.compile(r'REQUIRED but not observed', re.IGNORECASE), out[:300])

    # --- P1 runtime proof SUCCESS: --require-proof with PSR present → success + record cleaned up ---
    def test_require_proof_succeeds_and_cleans_up_record(self):
        import tempfile, os as _os
        log = tempfile.NamedTemporaryFile(prefix="omni-del-", delete=False)
        log.close()
        try:
            rc, out = self._run_flow(
                ["myorg", "--target", "VoiceCall", "--require-proof"],
                {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0", "FAKE_PROOF": "1",
                 "FAKE_DELETE_LOG": log.name},
            )
            self.assertEqual(rc, 0, f"expected success with proof present; out={out[:300]}")
            self.assertRegex(out, re.compile(r'"success":\s*true'), out[:300])
            # The throwaway VoiceCall (id 500...) must have been deleted by the cleanup trap.
            with open(log.name) as fh:
                deleted = fh.read()
            self.assertIn("500000000000001AAA", deleted,
                          "runtime-proof record was not cleaned up (no delete logged)")
        finally:
            _os.unlink(log.name)


class SkillsBasedRoutingFlowTests(unittest.TestCase):
    """(6b) Skills-based routing variant for service-omni-routing-flow-deploy (W-24069467).

    The base trigger flows hardcode routingType=QueueBased, so a skills-based-routing org
    config never takes effect at runtime. This variant emits routingType=SkillsBased with a
    non-null skillOption (RunSBRRules default → platform evaluates WorkSkillRouting rules and
    attaches SkillRequirement rows to the PSR). A null skillOption is exactly what NPEs the
    platform routeWork action and rolls back the triggering insert (W-24069761), so the deploy
    script refuses to emit one and the asset always carries it.

    Org-free/network-free: template well-formedness + input-contract rejection + the SkillsBased
    deploy path driven through the parameterized _FAKE_SF_VOICE sandbox.
    """

    FLOWS_DIR = (SKILLS_ROOT / "service-omni-routing-flow-deploy"
                 / "assets/force-app/main/default/flows")
    SKILLSBASED_TEMPLATES = [
        "Omni_Route_Case_Trigger.SkillsBased.flow-meta.xml",
        "Omni_Route_VoiceCall_Trigger.SkillsBased.flow-meta.xml",
    ]
    QUEUEBASED_TEMPLATES = [
        "Omni_Route_Case_Trigger.flow-meta.xml",
        "Omni_Route_VoiceCall_Trigger.flow-meta.xml",
    ]
    #: The tokens deploy-and-report.sh substitutes for the record-triggered variants.
    SED_SUBSTITUTIONS = {
        "__SERVICE_CHANNEL_ID__", "__SERVICE_CHANNEL_DEVNAME__", "__SERVICE_CHANNEL_LABEL__",
        "__ROUTING_CONFIG_ID__", "__QUEUE_ID__", "__SKILL_OPTION__",
    }
    DRIVER = (SKILLS_ROOT / "service-omni-channel-setup-coordinate"
              / "scripts/integration-driver.sh")
    COORDINATOR_DOC = SKILLS_ROOT / "service-omni-channel-setup-coordinate/SKILL.md"

    # --- template well-formedness: SkillsBased routingType + a NON-NULL skillOption token ---
    def test_skillsbased_templates_are_skillsbased_with_nonnull_skilloption(self):
        for name in self.SKILLSBASED_TEMPLATES:
            with self.subTest(template=name):
                path = self.FLOWS_DIR / name
                self.assertTrue(path.exists(), f"missing SkillsBased template {name}")
                text = path.read_text()
                self.assertRegex(
                    text, re.compile(r"<name>routingType</name>\s*<value>\s*<stringValue>SkillsBased</stringValue>"),
                    f"{name} must emit routingType=SkillsBased",
                )
                # skillOption must be present and carry the resolvable token (never a null/empty value).
                self.assertRegex(
                    text, re.compile(r"<name>skillOption</name>\s*<value>\s*<stringValue>__SKILL_OPTION__</stringValue>"),
                    f"{name} must carry a tokenized non-null skillOption (W-24069761)",
                )

    # --- regression guard: the QueueBased base flows stay QueueBased and never grow a skillOption ---
    def test_queuebased_templates_unchanged(self):
        for name in self.QUEUEBASED_TEMPLATES:
            with self.subTest(template=name):
                text = (self.FLOWS_DIR / name).read_text()
                self.assertIn("<stringValue>QueueBased</stringValue>", text,
                              f"{name} must stay routingType=QueueBased")
                self.assertNotIn("SkillsBased", text, f"{name} must not become SkillsBased")
                self.assertNotIn("skillOption", text,
                                 f"{name} (QueueBased) must not carry skillOption - QueueBased ignores it")

    # --- every token in the SkillsBased template is one the deploy script substitutes (no residue) ---
    def test_skillsbased_tokens_resolve_cleanly(self):
        for name in self.SKILLSBASED_TEMPLATES:
            with self.subTest(template=name):
                text = (self.FLOWS_DIR / name).read_text()
                tokens = set(re.findall(r"__[A-Z_]+__", text))
                self.assertIn("__SKILL_OPTION__", tokens, f"{name} must tokenize skillOption")
                unknown = tokens - self.SED_SUBSTITUTIONS
                self.assertEqual(unknown, set(),
                                 f"{name} has tokens deploy-and-report.sh does not substitute: {unknown}")

    # --- input contract (sf scrubbed): invalid routing-type is rejected before any sf call ---
    def test_invalid_routing_type_rejected(self):
        rc, out = _run(_FLOW_SCRIPT, ["myorg", "--trigger", "--routing-type", "Widget"],
                       extra_path_scrub=True)
        self.assertEqual(rc, 2, f"expected exit 2 on bad routing-type; out={out[:300]}")
        self.assertRegex(out, re.compile(r"Invalid --routing-type", re.IGNORECASE), out[:300])

    # --- 761 guard: SkillsBased with an explicitly empty skillOption is refused (never emit null) ---
    def test_skillsbased_empty_skill_option_rejected(self):
        rc, out = _run(_FLOW_SCRIPT, ["myorg", "--trigger", "--routing-type=SkillsBased", "--skill-option="],
                       extra_path_scrub=True)
        self.assertEqual(rc, 2, f"expected exit 2 on empty skill-option; out={out[:300]}")
        self.assertIn("W-24069761", out)

    # --- 761 guard: SkillsBased with an out-of-enum skillOption is refused ---
    def test_skillsbased_invalid_skill_option_rejected(self):
        rc, out = _run(_FLOW_SCRIPT, ["myorg", "--trigger", "--routing-type", "SkillsBased",
                                      "--skill-option", "Bogus"], extra_path_scrub=True)
        self.assertEqual(rc, 2, f"expected exit 2 on bad skill-option; out={out[:300]}")
        self.assertRegex(out, re.compile(r"Invalid --skill-option", re.IGNORECASE), out[:300])

    # --- SkillsBased with no --skill-option defaults to a safe non-null value (RunSBRRules) ---
    def test_skillsbased_defaults_to_runsbrrules(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger", "--routing-type", "SkillsBased"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0"},
        )
        self.assertEqual(rc, 0, f"expected clean SkillsBased deploy; out={out[:400]}")
        self.assertRegex(out, re.compile(r'"routing_type":\s*"SkillsBased"'), out[:600])
        self.assertRegex(out, re.compile(r'"skill_option":\s*"RunSBRRules"'), out[:600])

    # --- SkillsBased runtime proof: the PSR's SkillRequirement rows are queried and reported ---
    def test_skillsbased_require_proof_reports_skill_requirements(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--require-proof", "--routing-type", "SkillsBased"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0", "FAKE_PROOF": "1", "FAKE_SKILLREQ": "1"},
        )
        self.assertEqual(rc, 0, f"expected success with proof + skill requirement; out={out[:400]}")
        self.assertRegex(out, re.compile(r'"skill_requirement_count":\s*1'), out[:800])
        self.assertIn("0PS00000000001AAA", out)  # the SkillId the platform attached to the PSR

    def test_skillsbased_request_redeploys_active_queuebased_flow(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger",
             "--routing-type", "SkillsBased"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "1",
             "ACTIVE_ROUTING_TYPE": "QueueBased"},
        )
        self.assertEqual(rc, 0, out[:600])
        self.assertRegex(out, re.compile(r'"status":\s*"created"'), out[:600])

    def test_skillsbased_request_reuses_matching_active_flow(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--trigger",
             "--routing-type", "SkillsBased"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "1",
             "ACTIVE_ROUTING_TYPE": "SkillsBased",
             "ACTIVE_SKILL_OPTION": "RunSBRRules"},
        )
        self.assertEqual(rc, 0, out[:600])
        self.assertRegex(out, re.compile(r'"status":\s*"reused"'), out[:600])

    def test_required_skillsbased_proof_rejects_zero_skill_requirements(self):
        rc, out = self._run_flow(
            ["myorg", "--target", "VoiceCall", "--require-proof",
             "--routing-type", "SkillsBased"],
            {"FAKE_SC_PRESENT": "1", "FAKE_FLOW_ACTIVE": "0", "FAKE_PROOF": "1"},
        )
        self.assertEqual(rc, 1, out[:600])
        self.assertIn("SkillRequirement", out)

    def test_coordinator_infers_and_forwards_skillsbased_routing(self):
        source = self.DRIVER.read_text()
        self.assertIn('ROUTING_TYPE="${OMNI_ROUTING_TYPE:-}"', source)
        self.assertIn('ROUTING_TYPE="SkillsBased"', source)
        self.assertIn('--routing-type "$ROUTING_TYPE"', source)
        self.assertIn('--skill-option "$SKILL_OPTION"', source)

    def test_coordinator_sequences_wsr_before_routing_flow(self):
        source = self.DRIVER.read_text()
        wsr_index = source.index('run_skill "service-omni-work-skill-routing-configure"')
        flow_index = source.index('# ---- Routing flow')
        self.assertLess(wsr_index, flow_index)

    def test_coordinator_documents_sbr_routing_inputs(self):
        text = self.COORDINATOR_DOC.read_text()
        self.assertIn("OMNI_ROUTING_TYPE", text)
        self.assertIn("OMNI_SKILL_OPTION", text)
        self.assertIn("RunSBRRules", text)

    def _run_flow(self, args, env):
        # Cross-skill handoff the coordinator supplies; the VOICE fake ignores the devname values
        # and returns canonical channel/queue/QRC ids regardless, so these just satisfy resolution.
        merged = {
            "SERVICE_CHANNEL_DEVELOPER_NAME": "sfdc_phone",
            "QUEUE_DEVELOPER_NAME": "VoiceQueue",
            "ROUTING_CONFIG_DEVELOPER_NAME": "Voice_Routing_Config",
            "OMNI_PROOF_POLL_TRIES": "1",
            "OMNI_PROOF_POLL_SLEEP": "0",
        }
        merged.update(env)
        with _FakeSfDir(body=_FAKE_SF_VOICE) as fake_dir:
            return _run(_FLOW_SCRIPT, args, path_prefix=fake_dir, extra_env=merged)


class VoiceMembershipContractTests(unittest.TestCase):
    """(7) Explicit real-agent membership contract for service-omni-queue-members-assign."""

    SCRIPT = "service-omni-queue-members-assign/scripts/verify-and-bind.sh"

    # A malformed explicit token (neither Username nor 005-Id) must block after resolving the queue.
    def test_explicit_bad_token_blocked(self):
        with _FakeSfDir(body=_FAKE_SF_VOICE) as fake_dir:
            rc, out = _run(self.SCRIPT, ["myorg", "VoiceQueue", "", "not-an-email,also_bad"],
                           path_prefix=fake_dir)
        self.assertEqual(rc, 1, f"expected block on bad explicit token; out={out[:300]}")
        self.assertRegex(out, re.compile(r'neither a Username', re.IGNORECASE), out[:300])

    # A well-formed explicit username list drives the explicit source (member_source=explicit).
    def test_explicit_username_list_uses_explicit_source(self):
        with _FakeSfDir(body=_FAKE_SF_VOICE) as fake_dir:
            rc, out = _run(self.SCRIPT, ["myorg", "VoiceQueue", "", "agent1@example.com,agent2@example.com"],
                           path_prefix=fake_dir)
        # Whatever the final bind/re-query tally, the run must NOT block on parsing and must record
        # the explicit source (never silently fall back to the demo agent pattern).
        self.assertIn('"member_source": "explicit"', out, f"out={out[:400]}")


class CoordinatorSupervisorPermsetTests(unittest.TestCase):
    """(8) The coordinator must invoke the supervisor-permset leaf with the STANDARD
    ContactCenterSupervisor permission set - never the incompatible custom Omni_Supervisor
    (which re-declares license-gated perms and fails assignment on standard licenses)."""

    DRIVER = SKILLS_ROOT / "service-omni-channel-setup-coordinate" / "scripts" / "integration-driver.sh"

    def _driver_src(self) -> str:
        return self.DRIVER.read_text()

    def test_supervisor_permset_invocations_use_contact_center_supervisor(self):
        src = self._driver_src()
        # Every verify-and-assign invocation that supplies $SUPERVISOR_COUNT (the supervisor leaf)
        # must pass ContactCenterSupervisor as the permission-set argument.
        sup_invocations = re.findall(
            r'verify-and-assign\.sh\s+"\$ORG"\s+"\$SUPERVISOR_COUNT"\s+"([^"]+)"', src)
        self.assertTrue(sup_invocations, "no supervisor-permset invocation found in coordinator")
        for permset in sup_invocations:
            self.assertEqual(
                permset, "ContactCenterSupervisor",
                f"coordinator invokes supervisor-permset leaf with '{permset}', "
                f"expected 'ContactCenterSupervisor'")

    def test_coordinator_never_passes_custom_omni_supervisor_permset(self):
        src = self._driver_src()
        self.assertNotIn(
            'verify-and-assign.sh "$ORG" "$SUPERVISOR_COUNT" "Omni_Supervisor"', src,
            "coordinator must not assign the custom Omni_Supervisor permission set "
            "(license-gated perms fail on standard licenses)")


class CoordinatorRepExperienceTests(unittest.TestCase):
    """(9) Assert the optional rep-experience wiring and the independent SBR gate."""

    DRIVER = SKILLS_ROOT / "service-omni-channel-setup-coordinate" / "scripts" / "integration-driver.sh"

    def setUp(self):
        self.src = self.DRIVER.read_text()

    def test_rep_stage_gated_on_flag(self):
        self.assertRegex(
            self.src, r'\[\s*"\$\{OMNI_REP_EXPERIENCE:-0\}"\s*=\s*"1"\s*\]',
            "rep-experience stage must be gated behind OMNI_REP_EXPERIENCE=1")

    def test_rep_stage_invokes_all_three_leaves(self):
        for leaf, script in (
            ("service-omni-presence-user-config-deploy", "deploy-and-report.sh"),
            ("service-omni-skills-based-routing-configure", "configure-and-report.sh"),
            ("service-omni-sidebar-configure", "enable-and-report.sh"),
        ):
            self.assertIn(leaf, self.src, f"coordinator never invokes {leaf}")
            self.assertIn(script, self.src, f"coordinator never calls {leaf} via {script}")

    def test_sbr_gated_on_routing_type(self):
        self.assertRegex(
            self.src, r'\[\s*"\$ROUTING_TYPE"\s*=\s*"SkillsBased"\s*\]',
            "skills-based prerequisites must run only for SkillsBased routing")


class CoordinatorOverflowAssigneeTests(unittest.TestCase):
    """(10) Optional fallback routing threads end-to-end: the coordinator input
    OMNI_OVERFLOW_ASSIGNEE is exported as QRC_OVERFLOW_ASSIGNEE, and the QRC leaf reads
    that same env var onto QueueRoutingConfig.OverflowAssigneeId. Neither side's suite
    can prove the handoff alone."""

    DRIVER = SKILLS_ROOT / "service-omni-channel-setup-coordinate" / "scripts" / "integration-driver.sh"
    QRC_LEAF = SKILLS_ROOT / "service-omni-queue-routing-config-deploy" / "scripts" / "upsert-and-report.sh"

    def test_coordinator_exports_overflow_to_qrc_env(self):
        self.assertRegex(
            self.DRIVER.read_text(),
            r'export\s+QRC_OVERFLOW_ASSIGNEE="\$OMNI_OVERFLOW_ASSIGNEE"',
            "coordinator must export OMNI_OVERFLOW_ASSIGNEE as QRC_OVERFLOW_ASSIGNEE")

    def test_qrc_leaf_consumes_overflow_env(self):
        self.assertIn(
            "QRC_OVERFLOW_ASSIGNEE", self.QRC_LEAF.read_text(),
            "QRC leaf must read QRC_OVERFLOW_ASSIGNEE so the coordinator handoff lands")


class ConfirmedGapRegressionTests(unittest.TestCase):
    """Cross-skill contracts confirmed by live-org validation."""

    DRIVER = SKILLS_ROOT / "service-omni-channel-setup-coordinate" / "scripts" / "integration-driver.sh"
    AGENTS = SKILLS_ROOT / "service-omni-agent-users-create" / "scripts" / "detect-and-create.sh"
    QRC = SKILLS_ROOT / "service-omni-queue-routing-config-deploy" / "scripts" / "upsert-and-report.sh"
    BASE = SKILLS_ROOT / "service-omni-base-settings-configure" / "scripts" / "configure-and-report.sh"

    def test_mixed_runs_propagate_reused_agent_usernames(self):
        self.assertIn("reused_users", self.AGENTS.read_text())
        self.assertIn(".detect.existing_users", self.DRIVER.read_text())

    def test_coordinator_exposes_per_target_queue_overrides(self):
        source = self.DRIVER.read_text()
        for var in (
            "OMNI_CASE_QUEUE_DEVELOPER_NAME",
            "OMNI_VOICE_QUEUE_DEVELOPER_NAME",
            "OMNI_INCIDENT_QUEUE_DEVELOPER_NAME",
            "OMNI_MESSAGING_QUEUE_DEVELOPER_NAME",
        ):
            self.assertIn(var, source)
        self.assertIn("queue_override_for_target", source)

    def test_coordinator_adopts_existing_or_explicit_qrc(self):
        source = self.DRIVER.read_text()
        for var in (
            "OMNI_CASE_ROUTING_CONFIG_DEVELOPER_NAME",
            "OMNI_VOICE_ROUTING_CONFIG_DEVELOPER_NAME",
        ):
            self.assertIn(var, source)
        self.assertNotIn(
            "SELECT QueueRoutingConfig.DeveloperName FROM Group",
            source,
            "Group.QueueRoutingConfig is not a queryable relationship on supported orgs",
        )
        self.assertIn("SELECT QueueRoutingConfigId FROM Group", source)
        self.assertIn("SELECT DeveloperName FROM QueueRoutingConfig WHERE Id=", source)
        self.assertIn('QRC_DEVELOPER_NAME="$qrc_dn"', source)

    def test_qrc_push_timeout_is_written_and_verified(self):
        source = self.QRC.read_text()
        self.assertIn("QRC_PUSH_TIMEOUT", source)
        self.assertIn("{PushTimeout: $pt}", source)
        self.assertIn("PushTimeout(got=", source)

    def test_status_capacity_setting_uses_explicit_source_deploy(self):
        source = self.BASE.read_text()
        self.assertIn("--source-dir", source)
        self.assertIn("OmniChannel.settings-meta.xml", source)


class CoordinatorSupervisorSurfaceTests(unittest.TestCase):
    """(11) The supervisor surface + Command Center advisory + field-based routing are
    coordinator-only wiring the per-leaf suites cannot see. Assert: the read-only analysis
    always runs (never gated on the opt-in flag), the surface leaf runs after the config and
    is gated on the config disposition, and field-based WorkSkillRouting is gated on the
    four OMNI_WSR_* inputs."""

    DRIVER = SKILLS_ROOT / "service-omni-channel-setup-coordinate" / "scripts" / "integration-driver.sh"

    def setUp(self):
        self.src = self.DRIVER.read_text()

    def test_command_center_analyze_invoked(self):
        self.assertIn("service-omni-command-center-analyze", self.src,
                      "coordinator never invokes command-center-analyze")
        self.assertIn("analyze.sh", self.src,
                      "coordinator never calls command-center-analyze via analyze.sh")

    def test_command_center_analyze_not_gated_on_rep_flag(self):
        # The advisory read-only step must run regardless of the opt-in rep-experience flag: its
        # run_skill call is top-level (column 0), not indented inside the rep-experience `if` block.
        self.assertRegex(
            self.src, r'(?m)^run_skill "service-omni-command-center-analyze"',
            "command-center-analyze must be invoked top-level, outside the OMNI_REP_EXPERIENCE gate")

    def test_supervisor_surface_invoked_after_config(self):
        self.assertIn("service-omni-supervisor-surface-deploy", self.src,
                      "coordinator never invokes supervisor-surface-deploy")
        cfg_at = self.src.index("service-omni-supervisor-config-deploy")
        surface_at = self.src.index("service-omni-supervisor-surface-deploy")
        self.assertLess(cfg_at, surface_at,
                        "supervisor-surface-deploy must be sequenced after supervisor-config-deploy")

    def test_supervisor_surface_gated_on_config_disposition(self):
        self.assertIn("SUPERVISOR_CONFIG_OK", self.src,
                      "surface stage must gate on the run-mode supervisor-config disposition")
        self.assertIn("SUPERVISOR_CONFIG_PRESENT", self.src,
                      "surface stage must gate on the plan-mode supervisor-config presence")

    def test_selected_supervisor_config_is_forwarded_to_both_leaves(self):
        self.assertIn("OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME", self.src)
        self.assertIn(
            'deploy-and-report.sh "$ORG" "$SUPERVISOR_COUNT" "$DISCOVERED_QUEUES_CSV" "" "" "$SUPERVISOR_CONFIG_DN"',
            self.src,
            "coordinator must pass the selected DeveloperName to supervisor-config-deploy",
        )
        self.assertIn(
            'deploy-and-report.sh "$ORG" "$SUPERVISOR_CONFIG_RESOLVED_DN"',
            self.src,
            "coordinator must pass the resolved DeveloperName to supervisor-surface-deploy",
        )

    def test_work_skill_routing_gated_on_wsr_inputs(self):
        self.assertIn("service-omni-work-skill-routing-configure", self.src,
                      "coordinator never invokes work-skill-routing-configure")
        for var in ("OMNI_WSR_ENTITY", "OMNI_WSR_FIELD", "OMNI_WSR_SKILL", "OMNI_WSR_VALUE"):
            self.assertIn(var, self.src,
                          f"field-based routing must be gated on {var}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
