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
    """Tests for fail-fast access-token retrieval per forcedotcom/cli#3560.

    The token comes ONLY from ``sf org auth show-access-token --json
    --no-prompt``; ``sf org display`` supplies instanceUrl only. The
    display stub deliberately carries a non-empty ``TOKEN_FROM_DISPLAY``
    so any regression to a display-token fallback is caught.

    Tests mock ``subprocess.run`` with a side-effect callable that routes
    by argv shape (preflight ``--help`` / display / show-access-token)
    without spawning real processes.
    """

    REDACTED_TOKEN = "[REDACTED] Use 'sf org auth show-access-token' to view"
    PREFLIGHT_ARGV = ["sf", "org", "auth", "show-access-token", "--help"]
    # Shape of real ``--help`` output (sf CLI 2.150.6).
    REAL_HELP = "USAGE\n  $ sf org auth show-access-token -o <value> [--json]\n"

    def setUp(self):
        # The preflight caches success process-wide; isolate every test.
        dc._show_access_token_capability_ok = False
        self.addCleanup(setattr, dc, "_show_access_token_capability_ok", False)

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

    def _route(self, *, preflight_missing=False, primary_fails=False,
               primary_token="TOKEN_FROM_SHOW", captured=None):
        """Build a fake_run that routes by argv shape.

        - preflight_missing → ``show-access-token --help`` raises
                              CalledProcessError (sf CLI lacks the command)
        - primary_fails     → token call raises CalledProcessError
                              (e.g. org not authenticated)
        - primary_token     → accessToken returned by the token call
        - captured          → optional list; each (argv, kwargs) is appended
        """
        def fake_run(argv, **kwargs):
            if captured is not None:
                captured.append((argv, kwargs))
            if "show-access-token" in argv and "--help" in argv:
                if preflight_missing:
                    raise subprocess.CalledProcessError(
                        returncode=1, cmd=argv,
                        stderr="show-access-token is not a sf command",
                    )
                return self._cp(self.REAL_HELP)
            if "display" in argv:
                return self._cp(self._display_payload())
            if "show-access-token" in argv:
                if primary_fails:
                    raise subprocess.CalledProcessError(
                        returncode=1, cmd=argv,
                        stderr="NoOrgAuthenticationError",
                    )
                return self._cp(
                    self._show_token_payload(access_token=primary_token),
                )
            raise AssertionError(f"unexpected argv: {argv}")
        return fake_run

    def test_primary_path_returns_show_token(self):
        """Happy path — dedicated command returns a clean token."""
        with mock.patch.object(dc.subprocess, "run", side_effect=self._route()):
            url, token = dc.resolve_org("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_SHOW")

    def test_primary_failure_raises_without_display_fallback(self):
        """Token command failing is terminal — the display payload's
        accessToken must NOT be used as a fallback."""
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(primary_fails=True),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        msg = str(ctx.exception)
        self.assertIn("sf org auth show-access-token", msg)
        self.assertNotIn("TOKEN_FROM_DISPLAY", msg)

    def test_primary_non_json_output_raises(self):
        def fake_run(argv, **kwargs):
            if "--help" in argv:
                return self._cp(self.REAL_HELP)
            if "display" in argv:
                return self._cp(self._display_payload())
            return self._cp("Warning: something not json")

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("sf org auth show-access-token", str(ctx.exception))

    def test_primary_redacted_raises(self):
        """Dedicated command returns the placeholder — fail fast rather than
        handing the redaction string to downstream callers (which would
        cause INVALID_AUTH_HEADER 401 on every call)."""
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(primary_token=self.REDACTED_TOKEN),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("could not retrieve a usable access token", str(ctx.exception))

    def test_primary_empty_token_raises(self):
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(primary_token=""),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("could not retrieve a usable access token", str(ctx.exception))

    def test_capability_preflight_failure_raises_clear_error(self):
        """sf CLI without `sf org auth show-access-token` → actionable
        upgrade message, and the token call is never attempted."""
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(preflight_missing=True, captured=captured),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        msg = str(ctx.exception)
        self.assertIn("missing required command", msg)
        self.assertIn("sf org auth show-access-token", msg)
        self.assertIn("Upgrade/reinstall Salesforce CLI", msg)
        token_calls = [a for a, _ in captured
                       if "show-access-token" in a and "--no-prompt" in a]
        self.assertEqual(token_calls, [])

    def test_zero_exit_without_help_signature_fails_and_is_not_cached(self):
        """A CLI that answers an unknown command with exit 0 must NOT be
        treated as capable; the failure is not cached, so the next call
        re-probes."""
        bogus = self._cp(
            "\x1b[1mUSAGE\x1b[22m\n  $ sf [COMMAND]\n",
            stderr='{"accessToken":"SECRET_Z"}',
        )
        with mock.patch.object(
            dc.subprocess, "run", side_effect=[bogus, self._cp(self.REAL_HELP)],
        ) as run:
            with self.assertRaises(SystemExit) as ctx:
                dc._assert_show_access_token_capability()
            msg = str(ctx.exception)
            self.assertIn("missing required command", msg)
            self.assertNotIn("SECRET_Z", msg)
            self.assertFalse(dc._show_access_token_capability_ok)
            dc._assert_show_access_token_capability()
        self.assertEqual(run.call_count, 2)
        self.assertTrue(dc._show_access_token_capability_ok)

    def test_zero_exit_without_help_signature_blocks_resolve_org(self):
        captured: list = []
        route = self._route(captured=captured)

        def fake_run(argv, **kwargs):
            if "--help" in argv:
                captured.append((argv, kwargs))
                return self._cp("")
            return route(argv, **kwargs)

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("lacked the command signature", str(ctx.exception))
        self.assertEqual([a for a, _ in captured], [self.PREFLIGHT_ARGV])

    def test_zero_exit_unknown_command_notice_echoing_name_fails(self):
        """Unknown-command notices contain the bare command name; only the
        USAGE form (`$ sf org auth show-access-token`) may pass."""
        for out in (
            "Error: Command org:auth:show-access-token not found.",
            "Warning: show-access-token is not a sf command.",
            "Did you mean org auth show-access-token? Run sf help for options.",
        ):
            with self.subTest(out=out):
                dc._show_access_token_capability_ok = False
                with mock.patch.object(
                    dc.subprocess, "run", return_value=self._cp("", stderr=out),
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        dc._assert_show_access_token_capability()
                self.assertIn("missing required command", str(ctx.exception))
                self.assertFalse(dc._show_access_token_capability_ok)

    def test_real_help_signature_passes_preflight(self):
        with mock.patch.object(
            dc.subprocess, "run", return_value=self._cp(self.REAL_HELP),
        ):
            dc._assert_show_access_token_capability()
        self.assertTrue(dc._show_access_token_capability_ok)

    def test_raises_systemexit_when_sf_cli_missing(self):
        """sf binary not on PATH — bail with the install hint."""
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
        """Tripwire — token call MUST be `sf org auth show-access-token`
        with `--no-prompt`. Without `--no-prompt` the command blocks on a
        confirmation banner that --json doesn't suppress on its own."""
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            dc.resolve_org("my-org")

        argvs = [a for a, _ in captured]
        # display call is still required for non-secret metadata.
        self.assertTrue(any("display" in a for a in argvs))
        primary = next(
            a for a in argvs if "show-access-token" in a and "--no-prompt" in a
        )
        self.assertIn("--json", primary)
        self.assertIn("--target-org", primary)

    def test_does_not_inject_show_secrets_env(self):
        """Tripwire: no sf subprocess may rely on SF_TEMP_SHOW_SECRETS
        (removed from sf CLI per forcedotcom/cli#3560)."""
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            dc.resolve_org("my-org")

        self.assertTrue(captured)
        for argv, kwargs in captured:
            env = kwargs.get("env") or {}
            self.assertNotIn("SF_TEMP_SHOW_SECRETS", env, msg=argv)

    def test_preflight_is_first_sf_call(self):
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            dc.resolve_org("my-org")
        argvs = [a for a, _ in captured]
        self.assertEqual(argvs[0], self.PREFLIGHT_ARGV)
        self.assertIn("display", argvs[1])

    def test_preflight_failure_never_invokes_display(self):
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(preflight_missing=True, captured=captured),
        ):
            with self.assertRaises(SystemExit):
                dc.resolve_org("my-org")
        self.assertEqual([a for a, _ in captured], [self.PREFLIGHT_ARGV])

    def test_missing_sf_reports_preflight_error_not_display(self):
        captured: list = []

        def fake_run(argv, **kwargs):
            captured.append(argv)
            raise FileNotFoundError("sf")

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(SystemExit) as ctx:
                dc.resolve_org("my-org")
        self.assertIn("sf CLI not found", str(ctx.exception))
        self.assertEqual(captured, [self.PREFLIGHT_ARGV])

    def test_preflight_runs_once_across_two_resolves(self):
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            dc.resolve_org("my-org")
            dc.resolve_org("my-org")
        argvs = [a for a, _ in captured]
        self.assertEqual(argvs.count(self.PREFLIGHT_ARGV), 1)
        self.assertEqual(sum(1 for a in argvs if "display" in a), 2)

    def test_failed_preflight_is_retried_on_next_resolve(self):
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=self._route(preflight_missing=True, captured=captured),
        ):
            with self.assertRaises(SystemExit):
                dc.resolve_org("my-org")
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            _url, token = dc.resolve_org("my-org")
        self.assertEqual(token, "TOKEN_FROM_SHOW")
        argvs = [a for a, _ in captured]
        self.assertEqual(argvs.count(self.PREFLIGHT_ARGV), 2)

    def _token_call_fails_with(self, *, stdout: str, stderr: str):
        def fake_run(argv, **kwargs):
            if "--help" in argv:
                return self._cp(self.REAL_HELP)
            if "display" in argv:
                return self._cp(self._display_payload())
            raise subprocess.CalledProcessError(
                returncode=1, cmd=argv, output=stdout, stderr=stderr,
            )
        return fake_run

    def test_token_call_failure_output_is_redacted(self):
        """A failing `show-access-token --json` can echo the token on
        stdout (or a bearer header on stderr); neither may reach the exit
        message."""
        cases = {
            "stdout_only": ('{"accessToken":"SECRET_X"}', ""),
            "stderr_and_stdout": (
                '{"accessToken":"SECRET_X"}',
                "Error: request failed\nBearer SECRET_Y\n",
            ),
            "auth_header_and_qs": (
                "", "Authorization: Bearer SECRET_Y accessToken=SECRET_X",
            ),
        }
        for label, (stdout, stderr) in cases.items():
            with self.subTest(label):
                with mock.patch.object(
                    dc.subprocess, "run",
                    side_effect=self._token_call_fails_with(
                        stdout=stdout, stderr=stderr,
                    ),
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        dc.resolve_org("my-org")
                msg = str(ctx.exception)
                self.assertNotIn("SECRET_X", msg)
                self.assertNotIn("SECRET_Y", msg)
                self.assertIn("<redacted>", msg)

    def test_preflight_failure_output_is_redacted(self):
        for label, (stdout, stderr) in {
            "stdout_only": ('{"accessToken":"SECRET_X"}', ""),
            "stderr": ("", "Bearer SECRET_Y"),
        }.items():
            with self.subTest(label):
                dc._show_access_token_capability_ok = False
                err = subprocess.CalledProcessError(
                    returncode=1, cmd=self.PREFLIGHT_ARGV,
                    output=stdout, stderr=stderr,
                )
                with mock.patch.object(dc.subprocess, "run", side_effect=err):
                    with self.assertRaises(SystemExit) as ctx:
                        dc.resolve_org("my-org")
                msg = str(ctx.exception)
                self.assertIn("missing required command", msg)
                self.assertNotIn("SECRET_X", msg)
                self.assertNotIn("SECRET_Y", msg)

    def test_display_call_still_passes_verbose(self):
        """org_display still includes --verbose for metadata shape stability."""
        captured: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=self._route(captured=captured),
        ):
            dc.resolve_org("my-org")

        display_argv = next(a for a, _ in captured if "display" in a)
        self.assertIn("--verbose", display_argv)


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
