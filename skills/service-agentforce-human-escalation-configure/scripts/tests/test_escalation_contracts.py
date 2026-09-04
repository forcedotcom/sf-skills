"""Org-free contract tests for service-agentforce-human-escalation-configure.

Run standalone:  python3 skills/service-agentforce-human-escalation-configure/scripts/tests/test_escalation_contracts.py
Or via pytest / unittest discovery.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

# Allow standalone execution (no package context) as well as discovery.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import (  # noqa: E402
    SKILLS_ROOT,
    SKILL_DIR,
    SCRIPT,
    VERDICT_SCRIPT,
    FakeSf,
    _FAKE_SF_PROD,
    _FAKE_SF_SANDBOX,
    run,
    run_node,
)


def _last_json(text):
    """Extract the last JSON object printed to stdout (the skill's verdict)."""
    depth = 0
    start = None
    obj = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    pass
                start = None
    return obj


class SyntaxTests(unittest.TestCase):
    def test_bash_syntax_valid(self):
        proc = subprocess.run(["bash", "-n", str(SKILLS_ROOT / SCRIPT)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_node_helpers_parse(self):
        for rel in (
            f"{SKILL_DIR}/scripts/classify-agent-active.mjs",
            f"{SKILL_DIR}/scripts/verify-escalation-config.mjs",
            f"{SKILL_DIR}/scripts/extract-outbound-route.mjs",
            f"{SKILL_DIR}/scripts/patch-escalation-surfaces.mjs",
            f"{SKILL_DIR}/scripts/classify-nga-escalation.mjs",
        ):
            proc = subprocess.run(["node", "--check", str(SKILLS_ROOT / rel)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{rel}: {proc.stderr}")

    def test_verify_only_retrieves_use_unzip(self):
        # Regression (blocker 1): every `sf project retrieve start --target-metadata-dir` - the
        # authoring AND the verify-only paths for GenAiPlugin / GenAiPlannerBundle / AiAuthoringBundle -
        # must pass --unzip. Without it --target-metadata-dir yields a ZIP and the grep/find/classifier
        # scans binary, so a correctly configured org is misreported as incomplete.
        src = (SKILLS_ROOT / SCRIPT).read_text()
        offending = [ln.strip() for ln in src.splitlines()
                     if "--target-metadata-dir" in ln and "--unzip" not in ln]
        self.assertEqual(offending, [], f"retrieve without --unzip: {offending}")


class InputContractTests(unittest.TestCase):
    """All must reject BEFORE the first sf call (PATH has no sf)."""

    def test_missing_org_rejected(self):
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_agent_name_rejected(self):
        rc, out = run(["myorg", "bad;name"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("agent_developer_name", out)

    def test_injection_queue_name_rejected(self):
        rc, out = run(["myorg", "Support_Agent", "bad queue"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("queue_developer_name", out)

    def test_injection_topic_name_rejected(self):
        rc, out = run(
            ["myorg", "Support_Agent", "Human_Support_Queue", "bad topic'"],
            scrub_sf=True,
        )
        self.assertEqual(rc, 1, out)
        self.assertIn("escalation_topic_api_name", out)

    def test_injection_bundle_name_rejected(self):
        rc, out = run(
            ["myorg", "Support_Agent", "Human_Support_Queue", "Escalate_Topic", "bad;bundle"],
            scrub_sf=True,
        )
        self.assertEqual(rc, 1, out)
        self.assertIn("planner_bundle_api_name", out)


class ProductionGuardTests(unittest.TestCase):
    def test_production_org_refused(self):
        with FakeSf(_FAKE_SF_PROD) as fake:
            rc, out = run(["prodorg"], path_prefix=fake)
        self.assertEqual(rc, 1, out)
        verdict = _last_json(out)
        self.assertIsNotNone(verdict, out)
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertNotIn("FAKE_SF_DEPLOY_SHOULD_NOT_BE_REACHED", out)


class PreconditionTests(unittest.TestCase):
    def test_inactive_agent_blocks(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(["sbx"], path_prefix=fake, extra_env={"FAKE_AGENT_ACTIVE": "0"})
        self.assertEqual(rc, 1, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertIn("precondition", verdict["blocking_issue"].lower())

    def test_missing_messaging_channel_blocks(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(["sbx"], path_prefix=fake, extra_env={"FAKE_MC_PRESENT": "0"})
        self.assertEqual(rc, 1, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertIn("MessagingChannel", verdict["blocking_issue"])


class VerdictTests(unittest.TestCase):
    def test_incomplete_without_topic_and_bundle(self):
        # Deterministic infra (queue/flow/agent) resolves, but canEscalate +
        # outboundRouteConfigs are unverified without the topic/bundle names.
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(["sbx"], path_prefix=fake)
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "INCOMPLETE")
        missing = verdict["config_verification"]["missing"]
        self.assertIn("canEscalate", missing)
        self.assertIn("outboundRouteConfigs", missing)
        # The surfaces the script owns must already pass.
        self.assertNotIn("outboundFlowActive", missing)
        self.assertNotIn("humanQueue", missing)
        self.assertNotIn("agentActive", missing)

    def test_configured_with_topic_bundle_and_threshold(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(
                ["sbx", "Support_Agent", "Human_Support_Queue",
                 "Escalate_To_Human", "Support_Agent"],
                path_prefix=fake,
                extra_env={"THRESHOLD_AUTHORED": "1"},
            )
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "CONFIGURED")
        self.assertTrue(verdict["config_verification"]["deterministicPass"])
        self.assertTrue(verdict["config_verification"]["directivePass"])

    def test_plan_only_stops_before_writes(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(["sbx"], path_prefix=fake, extra_env={"PLAN_ONLY": "1"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "PLAN")
        self.assertTrue(verdict["plan_mode"])


class ClassifierTests(unittest.TestCase):
    def _write(self, tmp, name, payload):
        p = Path(tmp) / name
        p.write_text(json.dumps(payload))
        return str(p.relative_to(SKILLS_ROOT)) if False else p

    def test_agent_active_classifier(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            active = Path(tmp) / "bot.json"
            active.write_text(json.dumps({"status": 0, "result": {"records": [
                {"DeveloperName": "Support_Agent", "Id": "0Xx",
                 "BotVersions": {"records": [{"Id": "1", "Status": "Active"}]}}]}}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/classify-agent-active.mjs",
                               [str(active), "Support_Agent"])
            self.assertEqual(rc, 0, out)
            self.assertTrue(json.loads(out)["ready"])

            inactive = Path(tmp) / "bot2.json"
            inactive.write_text(json.dumps({"status": 0, "result": {"records": [
                {"DeveloperName": "Support_Agent", "Id": "0Xx",
                 "BotVersions": {"records": [{"Id": "1", "Status": "Inactive"}]}}]}}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/classify-agent-active.mjs",
                               [str(inactive), "Support_Agent"])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertFalse(v["ready"])
            self.assertEqual(v["reason"], "agent-inactive")

    def test_config_verifier_pass_and_fail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base_full = {
                "canEscalate": True,
                "outboundRouteName": "Human_Escalation_Outbound_Flow",
                "outboundRouteType": "OmniChannelFlow",
                "outboundRouteSameBlock": True,
                "outboundRouteMessagingSurface": True,
                "expectedFlowName": "Human_Escalation_Outbound_Flow",
                "flowActiveVersionId": "301", "queueId": "00G",
                "queueSobjectPresent": True, "queueHasActiveDirectUserMember": True,
                "queueRoutingConfigPresent": True, "queueRoutingConfigBound": True,
                "agentActive": True, "thresholdAuthored": True,
            }
            full = Path(tmp) / "ev.json"
            full.write_text(json.dumps(base_full))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(full)])
            self.assertEqual(rc, 0, out)
            self.assertEqual(json.loads(out)["verdict"], "CONFIGURED")

            # Routing + surface complete but the failure-threshold directive is NOT authored: must
            # report ROUTING_CONFIGURED_POLICY_PENDING (never CONFIGURED) so a missing escalation
            # policy cannot hide behind a green verdict.
            policy_pending = Path(tmp) / "ev_policy.json"
            policy_pending.write_text(json.dumps({**base_full, "thresholdAuthored": False}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(policy_pending)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "ROUTING_CONFIGURED_POLICY_PENDING")
            self.assertTrue(v["deterministicPass"])
            self.assertFalse(v["directivePass"])
            self.assertIn("thresholdDirective", v["missing"])

            # An unbound QRC (Group.QueueRoutingConfigId not set) must NOT be CONFIGURED.
            unbound = Path(tmp) / "ev3.json"
            unbound.write_text(json.dumps({**base_full, "queueRoutingConfigBound": False}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(unbound)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "INCOMPLETE")
            self.assertIn("queueRoutingConfigBound", v["missing"])

            # A queue with zero active human members must NOT be CONFIGURED.
            nomembers = Path(tmp) / "ev4.json"
            nomembers.write_text(json.dumps({**base_full, "queueHasActiveDirectUserMember": False}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(nomembers)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "INCOMPLETE")
            self.assertIn("queueHasActiveDirectUserMember", v["missing"])

            # Route name matches but type is not OmniChannelFlow → outboundRouteConfigs fails.
            badtype = Path(tmp) / "ev5.json"
            badtype.write_text(json.dumps({**base_full, "outboundRouteType": "Copilot"}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(badtype)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "INCOMPLETE")
            self.assertIn("outboundRouteConfigs", v["missing"])

            # Route name + type present but not on a Messaging surface → outboundRouteConfigs fails.
            badsurface = Path(tmp) / "ev6.json"
            badsurface.write_text(json.dumps({**base_full, "outboundRouteMessagingSurface": False}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(badsurface)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "INCOMPLETE")
            self.assertIn("outboundRouteConfigs", v["missing"])

            partial = Path(tmp) / "ev2.json"
            partial.write_text(json.dumps({
                "canEscalate": False, "flowActiveVersionId": "301", "queueId": "00G",
                "queueSobjectPresent": True, "queueRoutingConfigPresent": True,
                "agentActive": True, "thresholdAuthored": False}))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(partial)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["verdict"], "INCOMPLETE")
            self.assertIn("canEscalate", v["missing"])


class QueueContractTests(unittest.TestCase):
    """The skill must actually ENSURE the queue/QueueSobject/QRC + bind, not just query them."""

    _FULL_ARGS = ["sbx", "Support_Agent", "Human_Support_Queue",
                  "Escalate_To_Human", "Support_Agent"]

    def test_creates_qrc_when_absent_and_reaches_configured(self):
        # QRC absent → script must POST-create it; Group already reports it bound (stateless fake).
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QRC_PRESENT": "0"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "CONFIGURED", out)
        self.assertNotIn("queueRoutingConfig", verdict["config_verification"]["missing"])
        self.assertNotIn("queueRoutingConfigBound", verdict["config_verification"]["missing"])

    def test_binds_messaging_session_queue_sobject_when_absent(self):
        # QueueSobject absent → script must POST-bind MessagingSession, then still reach CONFIGURED.
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QS_PRESENT": "0"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "CONFIGURED", out)
        self.assertNotIn("queueSobject", verdict["config_verification"]["missing"])

    def test_blocks_when_queue_binding_cannot_persist(self):
        # Group.QueueRoutingConfigId never persists → the skill must BLOCK, not falsely proceed.
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QUEUE_BOUND": "0"})
        self.assertEqual(rc, 1, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "BLOCKED", out)
        self.assertIn("bind", verdict["blocking_issue"].lower())

    def test_incomplete_when_queue_has_no_members(self):
        # A queue with zero active human members must NOT reach CONFIGURED (empty-queue guard).
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QUEUE_MEMBERS": "0"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "INCOMPLETE", out)
        self.assertIn("queueHasActiveDirectUserMember", verdict["config_verification"]["missing"])
        self.assertEqual(verdict["queue"]["active_direct_user_member_count"], 0)

    def test_assigns_members_from_explicit_usernames_reaches_configured(self):
        # Zero members + an explicit allowlist → the skill POSTs GroupMember, then reaches CONFIGURED.
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QUEUE_MEMBERS": "0",
                                     "QUEUE_MEMBER_USERNAMES": "agent1@example.com"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "CONFIGURED", out)
        self.assertNotIn("queueHasActiveDirectUserMember", verdict["config_verification"]["missing"])

    def test_blocks_on_injection_shaped_member_username(self):
        # An injection-shaped username must be rejected in the input-contract section, BEFORE any
        # sf call - so the org is never mutated. That path emits the plain {"error":...} shape and
        # exits 1 (same contract as the other input-validation guards), not a late BLOCKED verdict.
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_QUEUE_MEMBERS": "0",
                                     "QUEUE_MEMBER_USERNAMES": "bad'name"})
        self.assertEqual(rc, 1, out)
        self.assertIn("QUEUE_MEMBER_USERNAMES", out)

    def test_incomplete_when_route_type_not_omnichannelflow(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_ROUTE_TYPE": "Copilot"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "INCOMPLETE", out)
        self.assertIn("outboundRouteConfigs", verdict["config_verification"]["missing"])

    def test_incomplete_when_route_not_on_messaging_surface(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_ROUTE_SURFACE": "InternalCopilot"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "INCOMPLETE", out)
        self.assertIn("outboundRouteConfigs", verdict["config_verification"]["missing"])


class QueueMetadataShapeTests(unittest.TestCase):
    """The rendered Queue metadata must follow the canonical Metadata API element sequence."""

    def test_queue_xml_uses_canonical_element_order(self):
        src = (SKILLS_ROOT / SCRIPT).read_text()
        # doesSendEmailToMembers MUST precede name in the Queue heredoc (Metadata API sequence).
        i_dse = src.find("<doesSendEmailToMembers>")
        i_name = src.find("<name>${QUEUE_DN}</name>")
        self.assertGreater(i_dse, -1, "Queue heredoc missing <doesSendEmailToMembers>")
        self.assertGreater(i_name, -1, "Queue heredoc missing <name>${QUEUE_DN}</name>")
        self.assertLess(i_dse, i_name,
                        "Queue XML violates canonical order: <doesSendEmailToMembers> must precede <name>")


class IdempotencyTests(unittest.TestCase):
    """A re-run against an org where every surface already exists must ADOPT, never re-create:
    no duplicate QueueRoutingConfig, QueueSobject, or membership is written. Proven by asserting
    the fake `sf` call log contains none of the create POSTs while the verdict still reaches
    CONFIGURED."""

    _FULL_ARGS = ["sbx", "Support_Agent", "Human_Support_Queue",
                  "Escalate_To_Human", "Support_Agent"]

    def test_rerun_all_present_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            calllog = Path(tmp) / "calls.log"
            with FakeSf(_FAKE_SF_SANDBOX) as fake:
                rc, out = run(self._FULL_ARGS, path_prefix=fake,
                              extra_env={"THRESHOLD_AUTHORED": "1",
                                         "FAKE_SF_CALLLOG": str(calllog)})
            self.assertEqual(rc, 0, out)
            verdict = _last_json(out)
            self.assertEqual(verdict["status"], "CONFIGURED", out)
            log = calllog.read_text() if calllog.exists() else ""
            self.assertNotIn("sobjects/QueueRoutingConfig", log,
                             "QRC already present - a re-run must not POST a new one")
            self.assertNotIn("sobjects/QueueSobject", log,
                             "QueueSobject already present - a re-run must not POST a new bind")
            self.assertNotIn("sobjects/GroupMember", log,
                             "members already present - a re-run must not POST a new member")


class ContextPreservationTests(unittest.TestCase):
    """Context preservation (the human inherits the SAME MessagingSession + transcript) is a
    runtime fact, but its deterministic preconditions are verifiable: the routed context object
    must be MessagingSession (QueueSobject bound) AND the hand-off must stay inside Omni via an
    OmniChannelFlow outbound route on the Messaging surface. Missing either => not CONFIGURED."""

    _BASE = {
        "canEscalate": True,
        "outboundRouteName": "Human_Escalation_Outbound_Flow",
        "outboundRouteType": "OmniChannelFlow",
        "outboundRouteSameBlock": True,
        "outboundRouteMessagingSurface": True,
        "expectedFlowName": "Human_Escalation_Outbound_Flow",
        "flowActiveVersionId": "301", "queueId": "00G",
        "queueSobjectPresent": True, "queueHasActiveDirectUserMember": True,
        "queueRoutingConfigPresent": True, "queueRoutingConfigBound": True,
        "agentActive": True, "thresholdAuthored": True,
    }

    def _verdict(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ev.json"
            p.write_text(json.dumps(payload))
            rc, out = run_node(f"{SKILL_DIR}/scripts/verify-escalation-config.mjs", [str(p)])
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def test_configured_preserves_context(self):
        self.assertEqual(self._verdict(self._BASE)["verdict"], "CONFIGURED")

    def test_missing_messaging_session_sobject_breaks_preservation(self):
        v = self._verdict({**self._BASE, "queueSobjectPresent": False})
        self.assertEqual(v["verdict"], "INCOMPLETE")
        self.assertIn("queueSobject", v["missing"])

    def test_non_omnichannel_route_breaks_preservation(self):
        v = self._verdict({**self._BASE, "outboundRouteType": "Copilot"})
        self.assertEqual(v["verdict"], "INCOMPLETE")
        self.assertIn("outboundRouteConfigs", v["missing"])


class ThresholdInputTests(unittest.TestCase):
    """The failure threshold must be a REAL numeric input: validated, rendered into the directive,
    and echoed in the structured verdict (not just a boolean 'authored' flag)."""

    _FULL_ARGS = ["sbx", "Support_Agent", "Human_Support_Queue",
                  "Escalate_To_Human", "Support_Agent"]

    def test_default_threshold_is_two(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["threshold"]["default_failures"], 2, out)
        self.assertTrue(verdict["threshold"]["directive_rendered"], out)

    def test_three_attempt_value_is_rendered_and_reported(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1",
                                     "DEFAULT_FAILURE_THRESHOLD": "3"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["threshold"]["default_failures"], 3, out)
        self.assertEqual(verdict["threshold"]["authored"], True, out)
        self.assertEqual(verdict["config_verification"]["defaultFailureThreshold"], 3, out)

    def test_non_numeric_threshold_rejected_before_any_sf_call(self):
        rc, out = run(["myorg"], scrub_sf=True,
                      extra_env={"DEFAULT_FAILURE_THRESHOLD": "three"})
        self.assertEqual(rc, 1, out)
        self.assertIn("DEFAULT_FAILURE_THRESHOLD", out)

    def test_zero_threshold_rejected(self):
        rc, out = run(["myorg"], scrub_sf=True,
                      extra_env={"DEFAULT_FAILURE_THRESHOLD": "0"})
        self.assertEqual(rc, 1, out)
        self.assertIn("DEFAULT_FAILURE_THRESHOLD", out)


class GenAiPreflightTests(unittest.TestCase):
    """Escalation needs the Agentforce authoring metadata (GenAiPlugin/GenAiPlannerBundle). If the
    org exposes neither, the skill must BLOCK before any write instead of building routing infra
    that can only report INCOMPLETE."""

    _FULL_ARGS = ["sbx", "Support_Agent", "Human_Support_Queue",
                  "Escalate_To_Human", "Support_Agent"]

    def test_blocks_before_any_write_when_genai_metadata_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            calllog = Path(tmp) / "calls.log"
            with FakeSf(_FAKE_SF_SANDBOX) as fake:
                rc, out = run(self._FULL_ARGS, path_prefix=fake,
                              extra_env={"FAKE_GENAI_MD": "0",
                                         "FAKE_SF_CALLLOG": str(calllog)})
            self.assertEqual(rc, 1, out)
            verdict = _last_json(out)
            self.assertEqual(verdict["status"], "BLOCKED", out)
            self.assertIn("GenAiPlannerBundle", verdict["blocking_issue"])
            log = calllog.read_text() if calllog.exists() else ""
            self.assertNotIn("project deploy", log, "must block before any deploy")
            self.assertNotIn("sobjects/", log, "must block before any DML write")

    def test_proceeds_when_genai_metadata_present(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._FULL_ARGS, path_prefix=fake,
                          extra_env={"THRESHOLD_AUTHORED": "1", "FAKE_GENAI_MD": "1"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(_last_json(out)["status"], "CONFIGURED", out)


class NgaModelTests(unittest.TestCase):
    """On a next-gen (AiAuthoringBundle) org the skill must NOT block for a missing GenAiPlannerBundle.
    It builds the model-agnostic routing infra, then verifies the NGA escalation surface (a reachable
    @utils.escalate for a Service agent / a create-record action for an Employee agent) - reaching
    CONFIGURED when present, INCOMPLETE (surface delegated to agentforce-generate) when not."""

    _ARGS = ["sbx", "Support_Agent", "Human_Support_Queue"]

    def test_target_specific_nga_wins_when_both_metadata_models_exist(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._ARGS, path_prefix=fake,
                          extra_env={"FAKE_MODEL": "both", "FAKE_TARGET_MODEL": "nga",
                                     "THRESHOLD_AUTHORED": "1"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(_last_json(out)["authoring_model"], "nga", out)

    def test_nga_org_not_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            calllog = Path(tmp) / "calls.log"
            with FakeSf(_FAKE_SF_SANDBOX) as fake:
                rc, out = run(self._ARGS, path_prefix=fake,
                              extra_env={"FAKE_MODEL": "nga", "THRESHOLD_AUTHORED": "1",
                                         "FAKE_SF_CALLLOG": str(calllog)})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertNotEqual(verdict["status"], "BLOCKED", out)
        self.assertEqual(verdict["authoring_model"], "nga", out)

    def test_nga_configured_when_escalate_surface_present(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._ARGS, path_prefix=fake,
                          extra_env={"FAKE_MODEL": "nga", "FAKE_NGA_SURFACE": "1",
                                     "THRESHOLD_AUTHORED": "1"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "CONFIGURED", out)
        self.assertEqual(verdict["authoring_model"], "nga", out)
        self.assertEqual(verdict["agent"]["type"], "service", out)
        self.assertTrue(verdict["agent"]["escalation_surface_present"], out)
        # Classic-only checks must not appear on the NGA path.
        self.assertNotIn("canEscalate", verdict["config_verification"]["missing"])
        self.assertNotIn("outboundRouteConfigs", verdict["config_verification"]["missing"])

    def test_nga_incomplete_when_surface_missing(self):
        with FakeSf(_FAKE_SF_SANDBOX) as fake:
            rc, out = run(self._ARGS, path_prefix=fake,
                          extra_env={"FAKE_MODEL": "nga", "FAKE_NGA_SURFACE": "0",
                                     "THRESHOLD_AUTHORED": "1"})
        self.assertEqual(rc, 0, out)
        verdict = _last_json(out)
        self.assertEqual(verdict["status"], "INCOMPLETE", out)
        self.assertIn("ngaEscalationSurface", verdict["config_verification"]["missing"])
        # The routing infra half must still pass - only the agent surface is missing.
        self.assertNotIn("humanQueue", verdict["config_verification"]["missing"])
        self.assertNotIn("queueRoutingConfigBound", verdict["config_verification"]["missing"])

    def test_nga_classifier_service_vs_employee(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = Path(tmp) / "svc"
            svc.mkdir()
            (svc / "A.agent").write_text(
                "start_agent x:\n    connection messaging:\n    reasoning:\n"
                "        actions:\n            h: @utils.escalate\n")
            rc, out = run_node(f"{SKILL_DIR}/scripts/classify-nga-escalation.mjs", [str(svc)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["agentType"], "service")
            self.assertTrue(v["escalationSurfacePresent"])

            emp = Path(tmp) / "emp"
            emp.mkdir()
            (emp / "B.agent").write_text(
                "start_agent y:\n    reasoning:\n        actions:\n"
                "            t: @actions.createIncidentRecord\n")
            rc, out = run_node(f"{SKILL_DIR}/scripts/classify-nga-escalation.mjs", [str(emp)])
            self.assertEqual(rc, 0, out)
            v = json.loads(out)
            self.assertEqual(v["agentType"], "employee")
            self.assertTrue(v["escalationSurfacePresent"])


class NgaClassifierHardeningTests(unittest.TestCase):
    """The classifier must not report CONFIGURED off comments, prose, cross-block matches, or unrelated
    files, and must exit 3 (not 0) when the retrieve dir is unreadable/missing."""

    CLASSIFIER = f"{SKILL_DIR}/scripts/classify-nga-escalation.mjs"

    def _classify(self, files: dict):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, content in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            rc, out = run_node(self.CLASSIFIER, [str(root)])
            self.assertEqual(rc, 0, out)
            return json.loads(out)

    def test_commented_out_escalate_does_not_count(self):
        # A commented escalation block (the classic false-positive) must NOT satisfy the surface.
        v = self._classify({
            "A.agent": (
                "start_agent x:\n"
                "    connection messaging:\n"
                "    reasoning:\n"
                "        actions:\n"
                "            // human_handoff: @utils.escalate\n"
                "            # human_handoff: @utils.escalate\n"
                "            answer: @actions.AnswerQuestionWithKnowledge\n"
            ),
        })
        self.assertEqual(v["agentType"], "service")
        self.assertFalse(v["escalationSurfacePresent"], v)

    def test_escalate_outside_actions_section_does_not_count(self):
        # `@utils.escalate` in prose/description (not under a reasoning: actions: header) is unreachable.
        v = self._classify({
            "A.agent": (
                "start_agent x:\n"
                "    connection messaging:\n"
                '    description: "This agent could @utils.escalate someday."\n'
                "    reasoning:\n"
                "        actions:\n"
                "            answer: @actions.AnswerQuestionWithKnowledge\n"
            ),
        })
        self.assertFalse(v["escalationSurfacePresent"], v)

    def test_cross_block_messaging_and_escalate_do_not_combine(self):
        # messaging in one agent block + escalate in a DIFFERENT block must not prove a service surface.
        v = self._classify({
            "A.agent": (
                "start_agent has_messaging:\n"
                "    connection messaging:\n"
                "    reasoning:\n"
                "        actions:\n"
                "            answer: @actions.AnswerQuestionWithKnowledge\n"
                "start_agent has_escalate:\n"
                "    reasoning:\n"
                "        actions:\n"
                "            h: @utils.escalate\n"
            ),
        })
        # First block (messaging) sets agentType=service, but no single block has BOTH → not present.
        self.assertEqual(v["agentType"], "service")
        self.assertFalse(v["escalationSurfacePresent"], v)

    def test_tokens_in_unrelated_non_script_file_ignored(self):
        # A README/xml that merely mentions the tokens is not Agent Script → no bundle, no surface.
        v = self._classify({
            "notes.md": "connection messaging: and @utils.escalate are how NGA agents escalate.\n",
        })
        self.assertFalse(v["bundleFound"], v)
        self.assertEqual(v["agentType"], "unknown")
        self.assertFalse(v["escalationSurfacePresent"], v)

    def test_unreadable_or_missing_dir_exits_3(self):
        missing = str(Path(tempfile.gettempdir()) / "nga-does-not-exist-xyz123")
        rc, _ = run_node(self.CLASSIFIER, [missing])
        self.assertEqual(rc, 3)


class CoordinatorGateTests(unittest.TestCase):
    def test_escalation_verdict_mapping(self):
        rc, out = run_node(VERDICT_SCRIPT, ["escalation", "CONFIGURED"])
        self.assertEqual(rc, 0, out)
        rc, _ = run_node(VERDICT_SCRIPT, ["escalation", "ALREADY-CONFIGURED"])
        self.assertEqual(rc, 0)
        rc, _ = run_node(VERDICT_SCRIPT, ["escalation", "INCOMPLETE"])
        self.assertEqual(rc, 1)
        rc, _ = run_node(VERDICT_SCRIPT, ["escalation", "BLOCKED"])
        self.assertEqual(rc, 1)


class PackagedAssetTests(unittest.TestCase):
    def test_bundled_xml_is_wellformed(self):
        base = SKILLS_ROOT / SKILL_DIR / "assets"
        for rel in ("package.xml",
                    "force-app/main/default/flows/Human_Escalation_Outbound_Flow.flow-meta.xml"):
            xml.dom.minidom.parse(str(base / rel))

    def test_bundled_json_is_wellformed(self):
        base = SKILLS_ROOT / SKILL_DIR / "assets"
        json.loads((base / "sfdx-project.json").read_text())

    def test_outbound_flow_is_queuebased(self):
        flow = (SKILLS_ROOT / SKILL_DIR / "assets" / "force-app" / "main" / "default" /
                "flows" / "Human_Escalation_Outbound_Flow.flow-meta.xml").read_text()
        self.assertIn("<stringValue>QueueBased</stringValue>", flow)
        self.assertIn("__QUEUE_DEVELOPER_NAME__", flow)
        self.assertIn("<processType>RoutingFlow</processType>", flow)


PATCHER = f"{SKILL_DIR}/scripts/patch-escalation-surfaces.mjs"

_PLUGIN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<GenAiPlugin xmlns="http://soap.sforce.com/2006/04/metadata">
    <aiPluginUtterances>
        <developerName>U1</developerName>
        <language>en_US</language>
        <masterLabel>U1</masterLabel>
        <utterance>help</utterance>
    </aiPluginUtterances>
    <description>Escalation topic</description>
    <developerName>Escalate_To_Human</developerName>
    <language>en_US</language>
    <masterLabel>Escalate To Human</masterLabel>
    <pluginType>Topic</pluginType>
</GenAiPlugin>
"""

_BUNDLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<GenAiPlannerBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Support Agent</masterLabel>
    <plannerSurfaces>
        <adaptiveResponseAllowed>false</adaptiveResponseAllowed>
        <callRecordingAllowed>false</callRecordingAllowed>
        <surface>SurfaceAction__Messaging</surface>
        <surfaceType>Messaging</surfaceType>
    </plannerSurfaces>
    <plannerType>AiCopilot__ReAct</plannerType>
</GenAiPlannerBundle>
"""

_BUNDLE_NO_MESSAGING = _BUNDLE_XML.replace("Messaging", "Telephony")

_FLOW = "Human_Escalation_Outbound_Flow"


def _patch(mode, path, *extra):
    proc = subprocess.run(
        ["node", str(SKILLS_ROOT / PATCHER), mode, str(path), *extra],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class PatcherXsdOrderTests(unittest.TestCase):
    """The schema-aware patcher must honor the GenAiPlannerBundle/GenAiPlugin XSD element order."""

    def _tmp(self, tmp, name, content):
        p = Path(tmp) / name
        p.write_text(content)
        return p

    def test_can_escalate_inserted_after_utterances_before_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "t.genAiPlugin", _PLUGIN_XML)
            rc, out, err = _patch("canEscalate", p)
            self.assertEqual(rc, 0, err)
            text = p.read_text()
            xml.dom.minidom.parseString(text)  # well-formed
            i_utt = text.rindex("</aiPluginUtterances>")
            i_esc = text.index("<canEscalate>")
            i_desc = text.index("<description>")
            self.assertLess(i_utt, i_esc, "canEscalate must follow aiPluginUtterances")
            self.assertLess(i_esc, i_desc, "canEscalate must precede description")
            self.assertIn("<canEscalate>true</canEscalate>", text)

    def test_can_escalate_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "t.genAiPlugin", _PLUGIN_XML)
            _patch("canEscalate", p)
            rc, out, err = _patch("canEscalate", p)
            self.assertEqual(rc, 0, err)
            self.assertEqual(json.loads(out)["changed"], False)
            self.assertEqual(p.read_text().count("<canEscalate>"), 1)

    def test_can_escalate_refuses_without_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "t.genAiPlugin",
                          '<?xml version="1.0"?>\n<GenAiPlugin xmlns="x"></GenAiPlugin>\n')
            rc, out, err = _patch("canEscalate", p)
            self.assertEqual(rc, 4, out + err)

    def test_outbound_route_inserted_before_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "b.genAiPlannerBundle", _BUNDLE_XML)
            rc, out, err = _patch("outboundRoute", p, _FLOW)
            self.assertEqual(rc, 0, err)
            text = p.read_text()
            xml.dom.minidom.parseString(text)
            i_cfg = text.index("<outboundRouteConfigs>")
            i_surface = text.index("<surface>")
            self.assertLess(i_cfg, i_surface, "outboundRouteConfigs must precede <surface> per XSD")
            # Internal order: escalationMessage, outboundRouteName, outboundRouteType.
            i_msg = text.index("<escalationMessage>")
            i_name = text.index("<outboundRouteName>")
            i_type = text.index("<outboundRouteType>")
            self.assertLess(i_msg, i_name)
            self.assertLess(i_name, i_type)
            self.assertIn("<outboundRouteType>OmniChannelFlow</outboundRouteType>", text)

    def test_outbound_route_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "b.genAiPlannerBundle", _BUNDLE_XML)
            _patch("outboundRoute", p, _FLOW)
            rc, out, err = _patch("outboundRoute", p, _FLOW)
            self.assertEqual(rc, 0, err)
            self.assertEqual(json.loads(out)["changed"], False)
            self.assertEqual(p.read_text().count("<outboundRouteConfigs>"), 1)

    def test_outbound_route_refuses_without_messaging_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "b.genAiPlannerBundle", _BUNDLE_NO_MESSAGING)
            rc, out, err = _patch("outboundRoute", p, _FLOW)
            self.assertEqual(rc, 4, out + err)

    def test_outbound_route_requires_flow_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._tmp(tmp, "b.genAiPlannerBundle", _BUNDLE_XML)
            rc, out, err = _patch("outboundRoute", p)
            self.assertEqual(rc, 2, out + err)


class AuthorSurfacesContractTests(unittest.TestCase):
    """Guard the AUTHOR_SURFACES CLI format + agent lifecycle so a refactor cannot regress it."""

    def setUp(self):
        self.src = (SKILLS_ROOT / SCRIPT).read_text()
        start = self.src.index("Step 6b")
        end = self.src.index("Step 7 - Verify", start)
        self.block = self.src[start:end]

    def test_retrieve_uses_unzip_and_deploy_uses_metadata_dir(self):
        self.assertIn("--unzip", self.block)
        self.assertIn("--metadata-dir", self.block)

    def test_never_deploys_metadata_format_as_source_dir(self):
        code = "\n".join(ln for ln in self.block.splitlines() if not ln.strip().startswith("#"))
        self.assertNotIn("--source-dir", code,
                         "metadata-format retrieval must deploy with --metadata-dir, not --source-dir")

    def test_agent_lifecycle_order_publish_deactivate_deploy_activate(self):
        i_publish = self.block.index("agent publish authoring-bundle")
        i_deactivate = self.block.index("agent deactivate")
        i_deploy = self.block.index("deploy start --target-org \"$ORG\" --metadata-dir")
        i_activate = self.block.rindex("agent activate")
        self.assertLess(i_publish, i_deactivate, "publish must precede deactivate")
        self.assertLess(i_deactivate, i_deploy, "deactivate must precede deploy (deploy fails while active)")
        self.assertLess(i_deploy, i_activate, "activate must follow deploy")

    def test_final_activation_is_fail_closed(self):
        # The terminal reactivation must be guarded by emit_blocked, never swallowed with `|| true`.
        tail = self.block[self.block.rindex("# 5) Reactivate"):]
        self.assertIn("emit_blocked", tail)
        self.assertIn("agent activate", tail)
        activate_line = [ln for ln in tail.splitlines() if "sf agent activate" in ln and "if !" in ln]
        self.assertTrue(activate_line, "final activate must be checked with `if !`")

    def test_reverifies_latest_botversion(self):
        self.assertIn("bot-after.json", self.block)
        self.assertIn("classify-agent-active.mjs", self.block)
        self.assertIn("refusing to report CONFIGURED against a stale/inactive version", self.block)

    def test_refuses_when_no_authoring_identifiers(self):
        self.assertIn("AUTHOR_SURFACES=1 requires escalation_topic_api_name and/or planner_bundle_api_name",
                      self.block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
