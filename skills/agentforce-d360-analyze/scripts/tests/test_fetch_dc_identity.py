"""Tests for ``fetch_dc._resolve_identity`` + ``sf org display`` fallback.

Closes a real-world failure mode: ``sessions[0].ssot__InternalOrganizationId__c``
is occasionally null in SSOT materialization despite every other field
being populated (e.g. session ``019dface-0000-7000-8000-000000000001`` in
``my-org-alias``). The authenticated ``sf`` alias knows the org id
regardless, so we fall back to ``sf org display --target-org <alias> --json``
and parse ``.result.id``. If that also fails, a unified diagnostic
surfaces both failure modes.

Every test patches ``subprocess.run`` at the ``fetch_dc`` module level so
no real CLI is ever invoked.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import fetch_dc  # type: ignore


_ORG_ALIAS = "my-org-alias"
_FULL_ORG_ID_18 = "00D0000000000000EA"
_EXPECTED_ORG_ID_15 = "00D000000000000"
_AGENT_API = "DemoAgent"
_AGENT_VER = "v5"


def _agent_participant() -> dict:
    return {
        "ssot__AiAgentSessionParticipantRole__c": "AGENT",
        "ssot__AiAgentApiName__c": _AGENT_API,
        "ssot__AiAgentVersionApiName__c": _AGENT_VER,
    }


def _sf_cli_success_stdout(org_id: str = _FULL_ORG_ID_18) -> str:
    """Shape mirrors the real ``sf org display --json`` payload."""
    return json.dumps({
        "status": 0,
        "result": {
            "id": org_id,
            "instanceUrl": "https://example.my.salesforce.com",
            "accessToken": "REDACTED",
        },
    })


class ResolveIdentityDmoPopulatedTests(unittest.TestCase):
    """Happy path — DMO field carries a valid 18-char id, no subprocess spawn."""

    def test_resolve_identity_uses_dmo_when_populated(self):
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [_agent_participant()]

        with mock.patch.object(fetch_dc.subprocess, "run") as m_run:
            org_id_15, agent, ver = fetch_dc._resolve_identity(
                sessions, participants, _ORG_ALIAS,
            )

        self.assertEqual(org_id_15, _EXPECTED_ORG_ID_15)
        self.assertEqual(agent, _AGENT_API)
        self.assertEqual(ver, _AGENT_VER)
        m_run.assert_not_called()


class ResolveIdentityDmoFallbackTests(unittest.TestCase):
    """DMO field null/empty/short — fall back to ``sf org display``."""

    def _patch_sf_cli_ok(self, org_id: str = _FULL_ORG_ID_18):
        return mock.patch.object(
            fetch_dc.subprocess, "run",
            return_value=SimpleNamespace(
                stdout=_sf_cli_success_stdout(org_id),
                stderr="",
                returncode=0,
            ),
        )

    def test_resolve_identity_falls_back_to_sf_cli_when_dmo_null(self):
        sessions = [{"ssot__InternalOrganizationId__c": None}]
        participants = [_agent_participant()]

        with self._patch_sf_cli_ok() as m_run:
            org_id_15, agent, ver = fetch_dc._resolve_identity(
                sessions, participants, _ORG_ALIAS,
            )

        self.assertEqual(org_id_15, _EXPECTED_ORG_ID_15)
        self.assertEqual(agent, _AGENT_API)
        self.assertEqual(ver, _AGENT_VER)
        # Exact argv shape matters — it's the public contract with the sf CLI.
        args, kwargs = m_run.call_args
        self.assertEqual(
            args[0],
            ["sf", "org", "display", "--target-org", _ORG_ALIAS, "--json"],
        )
        self.assertTrue(kwargs.get("check"))
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))

    def test_resolve_identity_falls_back_when_dmo_empty_string(self):
        sessions = [{"ssot__InternalOrganizationId__c": ""}]
        participants = [_agent_participant()]

        with self._patch_sf_cli_ok():
            org_id_15, _, _ = fetch_dc._resolve_identity(
                sessions, participants, _ORG_ALIAS,
            )
        self.assertEqual(org_id_15, _EXPECTED_ORG_ID_15)

    def test_resolve_identity_falls_back_when_dmo_shorter_than_15(self):
        sessions = [{"ssot__InternalOrganizationId__c": "shortid"}]
        participants = [_agent_participant()]

        with self._patch_sf_cli_ok():
            org_id_15, _, _ = fetch_dc._resolve_identity(
                sessions, participants, _ORG_ALIAS,
            )
        self.assertEqual(org_id_15, _EXPECTED_ORG_ID_15)


class ResolveIdentityBothSourcesFailTests(unittest.TestCase):
    """When both the DMO field AND the CLI fallback fail, surface both."""

    def test_resolve_identity_raises_when_both_sources_fail(self):
        sessions = [{"ssot__InternalOrganizationId__c": None}]
        participants = [_agent_participant()]

        err = subprocess.CalledProcessError(
            returncode=1,
            cmd=["sf", "org", "display", "--target-org", _ORG_ALIAS, "--json"],
            stderr="No AuthInfo found for name " + _ORG_ALIAS,
        )
        with mock.patch.object(fetch_dc.subprocess, "run", side_effect=err):
            with self.assertRaises(SystemExit) as ctx:
                fetch_dc._resolve_identity(
                    sessions, participants, _ORG_ALIAS,
                )

        msg = str(ctx.exception)
        # Must mention both failure modes so users know which to fix.
        self.assertIn("both DMO field and sf org display failed", msg)
        self.assertIn(_ORG_ALIAS, msg)
        self.assertIn("CalledProcessError", msg)


class ResolveIdentityNoAgentParticipantsTests(unittest.TestCase):
    """Recently-created sessions can land here while STDM is still
    materializing — the AGENT participant rows haven't been written yet.
    The error must hint at retry rather than implying a malformed session.
    """

    def test_resolve_identity_raises_with_retry_hint_when_no_agent_participants(self):
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        # No AGENT-role participants; only a USER row.
        participants = [{
            "ssot__AiAgentSessionParticipantRole__c": "USER",
            "ssot__AiAgentApiName__c": "",
            "ssot__AiAgentVersionApiName__c": "",
        }]

        with self.assertRaises(SystemExit) as ctx:
            fetch_dc._resolve_identity(sessions, participants, _ORG_ALIAS)

        msg = str(ctx.exception)
        # Identifying string for the error class.
        self.assertIn("no AGENT participants", msg)
        # New (Fix #6) wording — leads with retry, then falls back to malformed.
        self.assertIn("retry in a few minutes", msg)
        self.assertIn("STDM materialization", msg)

    def test_resolve_identity_raises_when_only_empty_field_participants(self):
        # AGENT-role row exists but agent_api_name + agent_version are blank.
        # Same outcome — no usable identity, same retry-hint error.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [{
            "ssot__AiAgentSessionParticipantRole__c": "AGENT",
            "ssot__AiAgentApiName__c": "",
            "ssot__AiAgentVersionApiName__c": "",
        }]

        with self.assertRaises(SystemExit) as ctx:
            fetch_dc._resolve_identity(sessions, participants, _ORG_ALIAS)

        self.assertIn("no AGENT participants", str(ctx.exception))


class ResolveIdentityUserRowFallbackTests(unittest.TestCase):
    """Some agent shapes (e.g. the OOTB ``MyAgent`` template) leave
    AGENT-row ``ssot__AiAgentApiName__c`` / ``ssot__AiAgentVersionApiName__c``
    as ``NOT_SET`` indefinitely, while USER-role rows correctly carry the
    api_name. The downstream session is otherwise complete (interactions,
    steps, generations all materialize), so refusing to run wastes signal.

    The fallback promotes the api_name from any participant row, stamps
    version=``v0`` (placeholder satisfying ``^v[0-9]+$`` per fs_guard), and
    proceeds. Tests guard against regression — a future "tighten this back
    up" refactor would re-break the MyAgent case silently.
    """

    def test_falls_back_to_user_row_api_name_when_agent_rows_not_set(self):
        # Mirrors a real session shape observed in production:
        # USER rows carry the api_name, AGENT rows are 'NOT_SET'.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "NOT_SET",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]

        org_id_15, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )

        self.assertEqual(org_id_15, _EXPECTED_ORG_ID_15)
        self.assertEqual(agent, "MyAgent")
        # Placeholder must satisfy the AGENT_VERSION_RE used by paths.session_dir.
        self.assertEqual(ver, "v0")

    def test_fallback_handles_blank_api_name_on_agent_row(self):
        # AGENT row api_name is empty string (rather than the literal
        # 'NOT_SET'). Both shapes mean the same thing per _NOT_SET.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",
                "ssot__AiAgentVersionApiName__c": "",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "",
                "ssot__AiAgentVersionApiName__c": "",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "MyAgent")
        self.assertEqual(ver, "v0")

    def test_fallback_picks_lexicographic_first_when_multiple_user_names(self):
        # Multi-agent handoff session where USER rows mention both agents.
        # The fallback uses sorted({...})[0] to match the dominant-agent
        # policy used elsewhere in the pipeline.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "ZAgent",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "AAgent",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "NOT_SET",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "AAgent")
        self.assertEqual(ver, "v0")

    def test_agent_row_with_only_version_not_set_still_uses_strict_path(self):
        # Defensive: AGENT row has a real api_name but version=NOT_SET. The
        # strict candidate filter rejects it, but the fallback should still
        # promote the api_name (avoiding a needless raise just because version
        # was missing on the AGENT row).
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [{
            "ssot__AiAgentSessionParticipantRole__c": "AGENT",
            "ssot__AiAgentApiName__c": "RealAgent",
            "ssot__AiAgentVersionApiName__c": "NOT_SET",
        }]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "RealAgent")
        self.assertEqual(ver, "v0")

    def test_fallback_rejects_api_name_with_invalid_shape(self):
        # Even though a non-empty api_name is present on a USER row, if it
        # doesn't satisfy ^[A-Za-z0-9_]+$ (fs_guard.API_NAME_RE) the fallback
        # MUST fall through to the original SystemExit. Without this guard,
        # paths.session_dir would later reject the dir with an opaque
        # ValidationError far from where the bad value originated.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        for bad_name in ("Service Agent", "agent-v1", "agent.v1", "héllo"):
            with self.subTest(bad_name=bad_name):
                participants = [{
                    "ssot__AiAgentSessionParticipantRole__c": "USER",
                    "ssot__AiAgentApiName__c": bad_name,
                    "ssot__AiAgentVersionApiName__c": "NOT_SET",
                }]
                with self.assertRaises(SystemExit) as ctx:
                    fetch_dc._resolve_identity(
                        sessions, participants, _ORG_ALIAS,
                    )
                # Falls through to the strict-path SystemExit, NOT a path-
                # validation traceback from fs_guard.
                self.assertIn("no AGENT participants", str(ctx.exception))

    def test_fallback_skips_invalid_picks_valid_when_both_present(self):
        # If multiple api_names are seen, the regex filter should drop the
        # invalid ones and the fallback should still succeed with a valid one.
        # Defense against a real session that mixes a malformed display-name
        # row (e.g. legacy data) with a clean USER row.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "Service Agent",  # invalid
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",  # valid
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]
        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "MyAgent")
        self.assertEqual(ver, "v0")

    def test_fallback_returned_version_matches_agent_version_regex(self):
        # Belt-and-braces: the placeholder version we return MUST match
        # the ^v[0-9]+$ shape enforced by paths.session_dir / fs_guard
        # (see scripts/_shared/paths.py:_validate_agent_triple). If a
        # future change picks a different placeholder ('NOT_SET',
        # 'unknown', 'v0.0', etc.) directory creation downstream will
        # blow up. Test the exact contract here without taking a
        # cross-skill import dependency.
        import re

        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [{
            "ssot__AiAgentSessionParticipantRole__c": "USER",
            "ssot__AiAgentApiName__c": "MyAgent",
            "ssot__AiAgentVersionApiName__c": "NOT_SET",
        }]
        _, _, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertRegex(ver, r"^v[0-9]+$")


class ResolveIdentityCrossRoleVersionHarvestTests(unittest.TestCase):
    """Real-data shape: AGENT participant rows had api_name + version both
    NOT_SET, but the USER rows carried the real (api_name, version) pair.
    The prior fallback only harvested api_name from non-AGENT rows and
    stamped version=``v0``, so the dir landed at ``<agent>__v0/`` while
    ``assemble_dc`` reconciled the real version into the tree from
    ``session.identity`` — dir + tree out of sync.

    The cross-role harvest closes that gap: when the strict AGENT-only
    candidate list is empty, scan ALL participant rows for a valid
    (api_name, version) pair before falling back to the v0 placeholder.
    Real version wins; placeholder is genuinely a last resort.
    """

    def test_user_row_carries_real_version_dir_lands_correctly(self):
        # The exact shape found on a live session. AGENT rows: NOT_SET on
        # both fields. USER rows: real pair.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",
                "ssot__AiAgentVersionApiName__c": "v24",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",
                "ssot__AiAgentVersionApiName__c": "v24",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "NOT_SET",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "MyAgent")
        # MUST be the real version, NOT the v0 placeholder — that's the
        # whole point of the cross-role harvest.
        self.assertEqual(ver, "v24")

    def test_falls_through_to_v0_placeholder_when_no_role_carries_version(self):
        # Builder Previewer shape: api_name lands on a USER row but no
        # participant row carries a real version. Must drop through to
        # the v0 placeholder branch (which keeps the pipeline runnable
        # for that legitimate session shape).
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "MyAgent",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "NOT_SET",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "MyAgent")
        self.assertEqual(ver, "v0")

    def test_cross_role_rejects_malformed_version(self):
        # Someone wrote a malformed version into a USER row (e.g.
        # 'v1.0', '1', '24'). Must NOT adopt it — fs_guard will reject
        # the dir later. Fall through to v0 placeholder so the pipeline
        # still runs and the assemble_dc reconcile can promote later
        # if a real version shows up elsewhere in the tree.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        for bad_version in ("v1.0", "1", "24", "version-24", ""):
            with self.subTest(bad_version=bad_version):
                participants = [
                    {
                        "ssot__AiAgentSessionParticipantRole__c": "USER",
                        "ssot__AiAgentApiName__c": "MyAgent",
                        "ssot__AiAgentVersionApiName__c": bad_version,
                    },
                    {
                        "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                        "ssot__AiAgentApiName__c": "NOT_SET",
                        "ssot__AiAgentVersionApiName__c": "NOT_SET",
                    },
                ]
                _, agent, ver = fetch_dc._resolve_identity(
                    sessions, participants, _ORG_ALIAS,
                )
                self.assertEqual(agent, "MyAgent")
                # Bad version rejected; placeholder kicks in.
                self.assertEqual(ver, "v0")

    def test_strict_agent_row_precedence_beats_user_row(self):
        # When BOTH AGENT and USER rows carry valid (api_name, version)
        # pairs, the strict-AGENT path runs first and the cross-role
        # branch is unreachable. Pin this precedence so a future
        # refactor can't accidentally reorder the resolution. If the
        # AGENT row's pair were ever shadowed by a USER row's pair, the
        # dominant-agent invariant on handoff sessions breaks.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "AAgent",  # lex-first across both rows
                "ssot__AiAgentVersionApiName__c": "v1",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "ZAgent",  # lex-LAST overall
                "ssot__AiAgentVersionApiName__c": "v9",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        # AGENT-row precedence: ZAgent/v9 wins, NOT AAgent/v1.
        self.assertEqual(agent, "ZAgent")
        self.assertEqual(ver, "v9")

    def test_cross_role_picks_lex_first_when_multiple_valid_pairs(self):
        # Handoff with two valid (api_name, version) pairs across USER
        # rows. The strict-path dominant-agent rule applies: lex-first
        # wins. This keeps the cross-role harvest aligned with the
        # AGENT-only path's selection policy.
        sessions = [{"ssot__InternalOrganizationId__c": _FULL_ORG_ID_18}]
        participants = [
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "ZAgent",
                "ssot__AiAgentVersionApiName__c": "v9",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "USER",
                "ssot__AiAgentApiName__c": "AAgent",
                "ssot__AiAgentVersionApiName__c": "v3",
            },
            {
                "ssot__AiAgentSessionParticipantRole__c": "AGENT",
                "ssot__AiAgentApiName__c": "NOT_SET",
                "ssot__AiAgentVersionApiName__c": "NOT_SET",
            },
        ]

        _, agent, ver = fetch_dc._resolve_identity(
            sessions, participants, _ORG_ALIAS,
        )
        self.assertEqual(agent, "AAgent")
        self.assertEqual(ver, "v3")


if __name__ == "__main__":
    unittest.main()
