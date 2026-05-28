"""Top-level vs nested identity coherence under manifest-placeholder shapes.

Regression coverage for the bug where ``fetch_dc._resolve_identity`` falls
through its strict AGENT-participant pick (fetch_dc.py:570-597) on agent
shapes like MyAgent — leaving the manifest with
``agent_version="v0"`` (placeholder) — while wave 5 then materializes
``gateway_request_tags`` rows that carry the real ``v24``. The harvester
``_build_session_identity`` correctly reads ``v24`` into
``session.identity.agent_version``, but the top-level ``identity`` block
was previously copied straight off the manifest and silently disagreed
with the same JSON file's nested copy.

These tests pin the promotion policy implemented by
``_promote_identity`` / ``_reconcile_top_identity``:

  - manifest "v0" + session "v24"     -> top promotes to v24
  - manifest "v3" + session None      -> top stays v3 (manifest wins)
  - manifest api None + session real  -> top promotes
  - manifest "v3" + session "v5"      -> top stays v3 (manifest wins;
                                          strict AGENT pick is intentional)
  - manifest "v0" + session "v0"      -> top stays v0 (no real value
                                          available; placeholder leak
                                          remains visible to investigator)

Plus a full round-trip through ``assemble_dc.assemble`` to confirm the
top-level and nested identity records agree on a real MyAgent-shape
session.
"""
from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import (  # type: ignore
    IDS, make_manifest, make_rows, write_to_disk,
)


# -----------------------------------------------------------------------------
# Unit tests for _promote_identity (single-field policy)
# -----------------------------------------------------------------------------


class PromoteVersionTests(unittest.TestCase):
    """`_promote_identity(..., kind="version")` — placeholder-only promotion."""

    def test_v0_placeholder_promoted_when_session_has_real_version(self):
        out = assemble_dc._promote_identity("v0", "v24", kind="version")
        self.assertEqual(out, "v24")

    def test_keeps_manifest_value_when_session_identity_is_none(self):
        # Manifest already real; no reason to look elsewhere.
        out = assemble_dc._promote_identity("v3", None, kind="version")
        self.assertEqual(out, "v3")

    def test_keeps_v0_when_session_also_returns_v0(self):
        # No real value harvestable. Placeholder remains visible so
        # the investigator can still see the resolution failed.
        out = assemble_dc._promote_identity("v0", "v0", kind="version")
        self.assertEqual(out, "v0")

    def test_keeps_v0_when_session_value_is_garbage(self):
        # Session shouldn't be able to "promote" a non-version-shaped string.
        out = assemble_dc._promote_identity("v0", "garbage", kind="version")
        self.assertEqual(out, "v0")

    def test_keeps_v0_when_session_value_is_none(self):
        out = assemble_dc._promote_identity("v0", None, kind="version")
        self.assertEqual(out, "v0")

    def test_no_promotion_when_both_real_but_disagree(self):
        # Strict AGENT-row pick is intentional — manifest wins.
        out = assemble_dc._promote_identity("v3", "v5", kind="version")
        self.assertEqual(out, "v3")


class PromoteApiNameTests(unittest.TestCase):
    """`_promote_identity(..., kind="api_name")` — NOT_SET-ish promotion."""

    def test_none_manifest_promoted_when_session_has_value(self):
        out = assemble_dc._promote_identity(
            None, "MyAgent", kind="api_name",
        )
        self.assertEqual(out, "MyAgent")

    def test_not_set_string_promoted_when_session_has_value(self):
        out = assemble_dc._promote_identity(
            "NOT_SET", "MyAgent", kind="api_name",
        )
        self.assertEqual(out, "MyAgent")

    def test_empty_manifest_promoted_when_session_has_value(self):
        out = assemble_dc._promote_identity("", "MyAgent", kind="api_name")
        self.assertEqual(out, "MyAgent")

    def test_keeps_manifest_value_when_session_is_none(self):
        # Symmetric of the version case — manifest wins when session
        # has nothing to offer.
        out = assemble_dc._promote_identity(
            "MyAgent", None, kind="api_name",
        )
        self.assertEqual(out, "MyAgent")

    def test_keeps_manifest_when_both_real(self):
        out = assemble_dc._promote_identity(
            "ManifestAgent", "SessionAgent", kind="api_name",
        )
        self.assertEqual(out, "ManifestAgent")


# -----------------------------------------------------------------------------
# Reconcile helper — composed policy across both fields + stderr note
# -----------------------------------------------------------------------------


class ReconcileTopIdentityTests(unittest.TestCase):

    def test_reconcile_emits_stderr_note_when_version_promoted(self):
        manifest = {"agent_api_name": "MyAgent", "agent_version": "v0"}
        session_identity = {
            "agent_api_name": None,
            "agent_version": "v24",
        }
        with mock.patch("sys.stderr") as fake_stderr:
            top = assemble_dc._reconcile_top_identity(
                manifest, session_identity, "00DXX0000000ABC",
            )
        self.assertEqual(top["agent_version"], "v24")
        self.assertEqual(top["agent_api_name"], "MyAgent")
        self.assertEqual(top["org_id_15"], "00DXX0000000ABC")
        # The stderr note format is part of the contract — at least
        # one print call mentioning "promoted" must fire.
        emitted = [
            call.args[0] for call in fake_stderr.write.call_args_list
            if call.args
        ]
        self.assertTrue(
            any("promoted" in str(s) for s in emitted),
            f"expected promotion note on stderr; got writes: {emitted}",
        )

    def test_reconcile_silent_when_no_promotion_needed(self):
        manifest = {"agent_api_name": "DemoAgent", "agent_version": "v5"}
        session_identity = {
            "agent_api_name": "DemoAgent",
            "agent_version": "v5",
        }
        with mock.patch("sys.stderr") as fake_stderr:
            top = assemble_dc._reconcile_top_identity(
                manifest, session_identity, "00DXX0000000ABC",
            )
        self.assertEqual(top["agent_version"], "v5")
        emitted = [
            call.args[0] for call in fake_stderr.write.call_args_list
            if call.args
        ]
        self.assertFalse(
            any("promoted" in str(s) for s in emitted),
            f"unexpected promotion note: {emitted}",
        )


# -----------------------------------------------------------------------------
# Full-fixture round-trip — MyAgent-shape session through assemble()
# -----------------------------------------------------------------------------


def _serviceagent2_shape_disk_writer(tmp_root: Path) -> Path:
    """Materialize a MyAgent-shape session under tmp_root.

    Mutates the synthetic fixture so that:

      - manifest carries the placeholder ``agent_version="v0"`` (mirrors
        what ``fetch_dc._resolve_identity``'s fallback stamps).
      - the AGENT participant row has its ``ssot__AiAgentVersionApiName__c``
        cleared to NOT_SET (so ``_build_session_identity`` doesn't pick up
        a version from there).
      - ``gateway_request_tags`` carries an ``agent_version_api_name=v24``
        tag against the declared GW request, so the harvester finds the
        real value.

    The session dir lives under ``<org>/<api_name>__v0/<sid>/`` to match the
    placeholder-stamped layout fetch_dc actually writes on this path.
    """
    rows = make_rows()

    # AGENT row: clear version so _build_session_identity has no hint
    # via that path; the harvest must come from gateway_request_tags.
    for p in rows["participants"]:
        if p.get("ssot__AiAgentSessionParticipantRole__c") == "AGENT":
            p["ssot__AiAgentVersionApiName__c"] = "NOT_SET"

    # Add the agent_version_api_name tag against the declared GW request.
    rows["gateway_request_tags"].append({
        "id__c": "tag-agent-version",
        "parent__c": IDS.GW_REQ_DECLARED,
        "tag__c": "agent_version_api_name",
        "tagValue__c": '"v24"',  # quoted form mirrors live shape
    })
    # Plus agent_developer_name so session.identity.agent_api_name
    # also gets a real value to test the api_name path.
    rows["gateway_request_tags"].append({
        "id__c": "tag-agent-dev",
        "parent__c": IDS.GW_REQ_DECLARED,
        "tag__c": "agent_developer_name",
        "tagValue__c": '"MyAgent"',
    })

    # Manifest: placeholder version, real api_name (matches the
    # MyAgent fallback's actual output — it stamps api_name from
    # any participant row but version is forced to "v0").
    manifest = make_manifest()
    manifest["agent_api_name"] = "MyAgent"
    manifest["agent_version"] = "v0"
    manifest["org_id_15"] = IDS.ORG_ID_15

    # Layout: <org>/<api_name>__v0/<sid>/ — the placeholder-shaped dir.
    sdir = tmp_root / IDS.ORG_ID_15 / "MyAgent__v0" / IDS.SID
    sdir.mkdir(parents=True, exist_ok=True)

    (sdir / "dc._session_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    for name, rs in rows.items():
        if rs:
            (sdir / f"dc.{name}.json").write_text(
                json.dumps(rs, indent=2) + "\n"
            )

    # Breadcrumb for _find_session_dir's primary path.
    link_dir = tmp_root / IDS.ORG_ID_15 / "_sessions"
    link_dir.mkdir(parents=True, exist_ok=True)
    (link_dir / f"{IDS.SID}.link").write_text(
        f"../MyAgent__v0/{IDS.SID}\n"
    )
    return sdir


class AssembleEndToEndIdentityCoherenceTests(unittest.TestCase):
    """The bug repro — top-level vs nested identity must agree after fix."""

    def test_top_identity_promoted_when_manifest_has_v0_and_tags_have_v24(self):
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            _serviceagent2_shape_disk_writer(tmp_root)
            with mock.patch.object(paths, "DATA_ROOT", tmp_root):
                tree, _ = assemble_dc.assemble(IDS.SID)
        # The harvester (_build_session_identity) reads v24 from tags.
        self.assertEqual(tree["session"]["identity"]["agent_version"], "v24")
        # The top-level — previously v0 — must now agree.
        self.assertEqual(tree["identity"]["agent_version"], "v24")

    def test_top_and_session_identity_agree_on_agent_version(self):
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            _serviceagent2_shape_disk_writer(tmp_root)
            with mock.patch.object(paths, "DATA_ROOT", tmp_root):
                tree, _ = assemble_dc.assemble(IDS.SID)
        # The whole point of the fix.
        self.assertEqual(
            tree["identity"]["agent_version"],
            tree["session"]["identity"]["agent_version"],
        )

    def test_api_name_top_level_keeps_manifest_when_session_returns_null(self):
        # Mirror the live live-verification observation: top-level
        # api_name is "MyAgent" (from manifest), session.identity
        # api_name is None because no agent_developer_name tag fired.
        # Strip the agent_developer_name tag we added in the helper.
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            _serviceagent2_shape_disk_writer(tmp_root)
            sdir = tmp_root / IDS.ORG_ID_15 / "MyAgent__v0" / IDS.SID
            tags_path = sdir / "dc.gateway_request_tags.json"
            tags = json.loads(tags_path.read_text())
            tags = [t for t in tags if t.get("tag__c") != "agent_developer_name"]
            tags_path.write_text(json.dumps(tags, indent=2) + "\n")

            with mock.patch.object(paths, "DATA_ROOT", tmp_root):
                tree, _ = assemble_dc.assemble(IDS.SID)
        # session.identity.agent_api_name None — no harvestable value.
        self.assertIsNone(tree["session"]["identity"]["agent_api_name"])
        # Top-level keeps manifest's "MyAgent" — promotion does NOT
        # erase a real manifest value when session has nothing to offer.
        self.assertEqual(tree["identity"]["agent_api_name"], "MyAgent")


# -----------------------------------------------------------------------------
# Sanity: the existing happy-path fixture still produces matching identity
# (regression guard against the fix mutating the simple case).
# -----------------------------------------------------------------------------


class HappyPathStillCoherentTests(unittest.TestCase):

    def test_happy_path_unchanged(self):
        # The synthetic fixture's gateway_request_tags don't include
        # `agent_version_api_name`, so session.identity.agent_version is
        # None on this path. The fix's policy preserves the manifest
        # value ("v5") in that case — verifying the no-promote branch
        # doesn't accidentally null out the top-level when the harvest
        # layer has nothing to offer.
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            write_to_disk(tmp_root)
            with mock.patch.object(paths, "DATA_ROOT", tmp_root):
                tree, _ = assemble_dc.assemble(IDS.SID)
        self.assertEqual(tree["identity"]["agent_version"], IDS.AGENT_VERSION)
        self.assertEqual(tree["identity"]["agent_api_name"], IDS.AGENT_API)
        # session.identity may be None here (no agent_version_api_name tag);
        # the top-level keeps the manifest's real value, which is the point.
        self.assertIn(
            tree["session"]["identity"]["agent_version"],
            (None, IDS.AGENT_VERSION),
        )


if __name__ == "__main__":
    unittest.main()
