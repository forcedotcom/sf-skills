"""Tests for ``dc`` (Data Cloud transport) + ``resolve_session``
(messaging-id → UUID resolver).

Both modules sit at the bottom of the dependency tree and have small,
well-defined public APIs that are mostly mockable at the subprocess /
urllib boundary.
"""
from __future__ import annotations

import io
import json
import subprocess
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import dc  # type: ignore
import resolve_session  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import IDS, write_to_disk  # type: ignore


# -----------------------------------------------------------------------------
# dc.load_sql / dc.parse
# -----------------------------------------------------------------------------


class LoadSqlTests(unittest.TestCase):

    def test_substitutes_placeholders_and_strips(self):
        # discover_sessions has SELECT_LIST/JOINS/WHERE_CLAUSE/LIMIT placeholders.
        sql = dc.load_sql(
            "discover_sessions",
            SELECT_LIST="*",
            JOINS="",
            WHERE_CLAUSE="1=1",
            LIMIT="10",
        )
        self.assertIn("SELECT *", sql)
        self.assertIn("LIMIT 10", sql)


class ParseTests(unittest.TestCase):

    def test_returns_data_array(self):
        self.assertEqual(dc.parse({"data": [{"a": 1}]}), [{"a": 1}])

    def test_returns_empty_list_when_data_missing(self):
        self.assertEqual(dc.parse({}), [])

    def test_returns_empty_list_for_falsy_input(self):
        self.assertEqual(dc.parse(None), [])
        self.assertEqual(dc.parse({}), [])


# -----------------------------------------------------------------------------
# dc.resolve_org — sf CLI shell-out
# -----------------------------------------------------------------------------


class ResolveOrgTests(unittest.TestCase):
    """Tests for the two-path access-token retrieval per forcedotcom/cli#3560.

    Path 1 (primary): ``sf org auth show-access-token --json --no-prompt``
    Path 2 (fallback): ``sf org display`` + ``SF_TEMP_SHOW_SECRETS=true``

    Most tests mock ``subprocess.run`` with a side-effect callable that
    returns a different stub depending on which sf subcommand was invoked,
    so we can exercise primary success, primary failure → fallback, and
    full-failure paths without spawning real processes.
    """

    REDACTED_TOKEN = "[REDACTED] Use 'sf org auth show-access-token' to view"

    def _cp(self, stdout: str, *, returncode: int = 0, stderr: str = ""):
        return SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr,
        )

    def _display_payload(self, *, access_token: str = "TOKEN_FROM_DISPLAY") -> str:
        return json.dumps({"result": {
            "instanceUrl": "https://example.salesforce.com",
            "accessToken": access_token,
        }})

    def _show_token_payload(self, *, access_token: str = "TOKEN_FROM_SHOW") -> str:
        return json.dumps({"result": {"accessToken": access_token}})

    def _route(self, primary_ok=True, primary_unknown=False,
               primary_redacted=False, display_redacted=False):
        """Build a fake_run that routes by argv shape.

        - primary_ok=True   → show-access-token returns clean token
        - primary_unknown   → show-access-token raises CalledProcessError
                              (older sf CLI without the subcommand)
        - primary_redacted  → show-access-token returns the placeholder
        - display_redacted  → org_display token field is the placeholder
                              (so fallback also fails — test full-failure)
        """
        def fake_run(argv, **kwargs):
            # display call
            if "display" in argv:
                return self._cp(
                    self._display_payload(
                        access_token=(self.REDACTED_TOKEN if display_redacted
                                      else "TOKEN_FROM_DISPLAY"),
                    ),
                )
            # show-access-token call
            if "show-access-token" in argv:
                if primary_unknown:
                    raise subprocess.CalledProcessError(
                        returncode=1, cmd=argv,
                        stderr="show-access-token is not a sf command",
                    )
                token = (self.REDACTED_TOKEN if primary_redacted
                         else "TOKEN_FROM_SHOW")
                return self._cp(self._show_token_payload(access_token=token))
            raise AssertionError(f"unexpected argv: {argv}")
        return fake_run

    def test_primary_path_returns_show_token(self):
        """Happy path — dedicated command returns a clean token."""
        with mock.patch.object(dc.subprocess, "run", side_effect=self._route()):
            url, token = dc.resolve_org("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_SHOW")

    def test_primary_unknown_falls_back_to_display_token(self):
        """Older sf CLI: show-access-token unknown → use display payload."""
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(primary_unknown=True),
        ):
            url, token = dc.resolve_org("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_DISPLAY")

    def test_primary_redacted_falls_back_to_display_token(self):
        """Edge case: dedicated command returns the placeholder string —
        treat as failure and try the display fallback."""
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(primary_redacted=True),
        ):
            url, token = dc.resolve_org("my-org")
        self.assertEqual(token, "TOKEN_FROM_DISPLAY")

    def test_both_paths_redacted_raises(self):
        """If both paths return the placeholder, surface a clean SystemExit
        rather than handing back the redaction string to downstream callers
        (which would cause INVALID_AUTH_HEADER 401 on every Tooling/REST call)."""
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(primary_redacted=True, display_redacted=True),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("could not retrieve a usable access token", str(ctx.exception))

    def test_raises_systemexit_when_sf_cli_missing(self):
        """sf binary not on PATH — bail with the upgrade hint."""
        with mock.patch.object(
            dc.subprocess, "run", side_effect=FileNotFoundError("sf"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("sf CLI not found", str(ctx.exception))

    def test_raises_systemexit_on_display_failure(self):
        """org_display itself failing is fatal — no instanceUrl, no recovery."""
        err = subprocess.CalledProcessError(
            returncode=1, cmd=["sf", "org", "display"], stderr="No AuthInfo found",
        )
        with mock.patch.object(dc.subprocess, "run", side_effect=err):
            with self.assertRaises(SystemExit):
                dc.resolve_org("my-org")

    def test_primary_path_argv_contains_show_access_token(self):
        """Tripwire — primary call MUST be `sf org auth show-access-token`
        with `--no-prompt`. Without `--no-prompt` the command blocks on a
        confirmation banner that --json doesn't suppress on its own."""
        captured_argvs: list[list[str]] = []

        def fake_run(argv, **kwargs):
            captured_argvs.append(argv)
            if "display" in argv:
                return self._cp(self._display_payload())
            return self._cp(self._show_token_payload())

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            dc.resolve_org("my-org")

        # display call should still pass --verbose + SF_TEMP_SHOW_SECRETS
        # (so the fallback path stays viable on this same invocation).
        self.assertTrue(any("display" in a for a in captured_argvs))
        # primary call shape:
        primary = next(a for a in captured_argvs if "show-access-token" in a)
        self.assertIn("--no-prompt", primary)
        self.assertIn("--json", primary)
        self.assertIn("--target-org", primary)

    def test_display_call_still_passes_verbose_and_show_secrets_env(self):
        """The legacy fallback path stays armed: org_display still runs
        with `--verbose` (so accessToken is emitted) and
        `SF_TEMP_SHOW_SECRETS=true` (so the token isn't redacted on sf
        CLI versions that still honour the workaround)."""
        captured = {}

        def fake_run(argv, **kwargs):
            if "display" in argv:
                captured["argv"] = argv
                captured["env"] = kwargs.get("env")
                return self._cp(self._display_payload())
            return self._cp(self._show_token_payload())

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            dc.resolve_org("my-org")

        self.assertIn("--verbose", captured["argv"])
        self.assertIsNotNone(captured["env"])
        self.assertEqual(captured["env"].get("SF_TEMP_SHOW_SECRETS"), "true")


# -----------------------------------------------------------------------------
# dc.post — HTTP path (urllib mock)
# -----------------------------------------------------------------------------


class PostTests(unittest.TestCase):

    def _fake_response(self, body: bytes):
        # Context-manager mock for urllib.request.urlopen
        cm = mock.MagicMock()
        cm.__enter__.return_value.read.return_value = body
        cm.__exit__.return_value = False
        return cm

    def test_returns_rows_on_2xx(self):
        body = json.dumps({"data": [{"a": 1}, {"a": 2}]}).encode()
        with mock.patch.object(
            dc.urllib.request, "urlopen", return_value=self._fake_response(body),
        ):
            out = dc.post(
                "SELECT 1", "https://x.salesforce.com", "TOKEN", "sessions",
            )
        self.assertEqual(out, [{"a": 1}, {"a": 2}])

    def test_raises_dcqueryerror_with_query_name_on_http_error(self):
        # HTTPError carries (url, code, msg, hdrs, fp). We need fp.read() to
        # work — the impl calls e.read() to grab the body.
        err = urllib.error.HTTPError(
            url="https://x.salesforce.com",
            code=400, msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b"sql parse error: missing FROM"),
        )
        with mock.patch.object(
            dc.urllib.request, "urlopen", side_effect=err,
        ):
            with self.assertRaises(dc.DCQueryError) as ctx:
                dc.post("SELECT bad", "https://x", "TOKEN", "sessions")
        msg = str(ctx.exception)
        self.assertIn("sessions", msg)
        self.assertIn("http=400", msg)
        self.assertIn("sql parse error", msg)


# -----------------------------------------------------------------------------
# resolve_session.is_messaging_id — pure shape check
# -----------------------------------------------------------------------------


class IsMessagingIdTests(unittest.TestCase):

    def test_15_char_0Mw_prefix_matches(self):
        self.assertTrue(resolve_session.is_messaging_id("0MwTESTMSG12345"))

    def test_18_char_0Mw_prefix_matches(self):
        self.assertTrue(resolve_session.is_messaging_id("0MwTESTMSG12345AAA"))

    def test_uuid_does_not_match(self):
        # 36 chars, dashes — UUIDs never accidentally pass.
        self.assertFalse(resolve_session.is_messaging_id(IDS.SID))

    def test_empty_does_not_match(self):
        self.assertFalse(resolve_session.is_messaging_id(""))

    def test_wrong_prefix_does_not_match(self):
        self.assertFalse(resolve_session.is_messaging_id("FOOVF00000AtTbV"))


# -----------------------------------------------------------------------------
# resolve_session.resolve_from_disk — scans DATA_ROOT
# -----------------------------------------------------------------------------


class ResolveFromDiskTests(unittest.TestCase):

    def test_uuid_input_passes_through_unchanged(self):
        self.assertEqual(
            resolve_session.resolve_from_disk(IDS.SID), IDS.SID,
        )

    def test_finds_uuid_when_messaging_id_in_dc_sessions(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            write_to_disk(tmp)  # synthetic fixture has the messaging id wired
            with mock.patch.object(
                resolve_session, "DATA_ROOT", tmp,
            ):
                out = resolve_session.resolve_from_disk("0MwTESTMSG12345AAA")
        self.assertEqual(out, IDS.SID)

    def test_returns_none_when_messaging_id_not_present_on_disk(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            write_to_disk(tmp)
            with mock.patch.object(
                resolve_session, "DATA_ROOT", tmp,
            ):
                out = resolve_session.resolve_from_disk("0Mw000000000000")
        self.assertIsNone(out)

    def test_returns_none_when_data_root_missing(self):
        with TemporaryDirectory() as t:
            ghost = Path(t) / "no-such"
            with mock.patch.object(
                resolve_session, "DATA_ROOT", ghost,
            ):
                out = resolve_session.resolve_from_disk("0MwTESTMSG12345AAA")
        self.assertIsNone(out)

    def test_skips_archive_dirs(self):
        # Plant a duplicate inside an "<uuid> - archive 1" dir; the resolver
        # should ignore it. Without the skip, the extra row could trigger
        # spurious multi-match.
        with TemporaryDirectory() as t:
            tmp = Path(t)
            write_to_disk(tmp)
            archive = tmp / IDS.ORG_ID_15 / f"{IDS.AGENT_API}__{IDS.AGENT_VERSION}" / f"{IDS.SID} - archive 1"
            archive.mkdir(parents=True)
            (archive / "dc.sessions.json").write_text(json.dumps([{
                "ssot__Id__c": "different-uuid-but-same-msg",
                "ssot__RelatedMessagingSessionId__c": "0MwTESTMSG12345AAA",
            }]))
            with mock.patch.object(resolve_session, "DATA_ROOT", tmp):
                out = resolve_session.resolve_from_disk("0MwTESTMSG12345AAA")
        # Resolver should return the canonical UUID, ignoring the archive
        # row. (If the archive weren't skipped, this would multi-match
        # raise.)
        self.assertEqual(out, IDS.SID)


# -----------------------------------------------------------------------------
# resolve_session.resolve_disk_or_live — combined path
# -----------------------------------------------------------------------------


class ResolveDiskOrLiveTests(unittest.TestCase):

    def test_uuid_input_passes_through(self):
        self.assertEqual(
            resolve_session.resolve_disk_or_live(IDS.SID), IDS.SID,
        )

    def test_disk_hit_returns_uuid_without_dc_call(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            write_to_disk(tmp)
            with mock.patch.object(resolve_session, "DATA_ROOT", tmp):
                with mock.patch.object(resolve_session, "_live_lookup") as live:
                    out = resolve_session.resolve_disk_or_live(
                        "0MwTESTMSG12345AAA", org="my-org",
                    )
            live.assert_not_called()
        self.assertEqual(out, IDS.SID)

    def test_disk_miss_no_org_raises_with_hint(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            with mock.patch.object(resolve_session, "DATA_ROOT", tmp):
                with self.assertRaises(SystemExit) as ctx:
                    resolve_session.resolve_disk_or_live(
                        "0MwTESTMSG12345AAA",
                    )
        self.assertIn("cannot resolve messaging id", str(ctx.exception))


# -----------------------------------------------------------------------------
# resolve_session.resolve — live DC-backed path
# -----------------------------------------------------------------------------


class ResolveLiveTests(unittest.TestCase):

    def test_single_row_returns_uuid(self):
        with mock.patch.object(
            resolve_session, "_live_lookup",
            return_value=[{"ssot__Id__c": "uuid-1"}],
        ):
            out = resolve_session.resolve("0MwTESTMSG12345AAA", org="my-org")
        self.assertEqual(out, "uuid-1")

    def test_zero_rows_raises(self):
        with mock.patch.object(
            resolve_session, "_live_lookup", return_value=[],
        ):
            with self.assertRaises(SystemExit) as ctx:
                resolve_session.resolve("0MwTESTMSG12345AAA", org="my-org")
        self.assertIn("no ssot__AIAgentSession", str(ctx.exception))

    def test_multi_row_raises_with_candidate_list(self):
        rows = [
            {"ssot__Id__c": "uuid-A", "ssot__StartTimestamp__c": "t"},
            {"ssot__Id__c": "uuid-B", "ssot__StartTimestamp__c": "t"},
        ]
        with mock.patch.object(
            resolve_session, "_live_lookup", return_value=rows,
        ):
            with self.assertRaises(SystemExit) as ctx:
                resolve_session.resolve("0MwTESTMSG12345AAA", org="my-org")
        self.assertIn("uuid-A", str(ctx.exception))
        self.assertIn("uuid-B", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
