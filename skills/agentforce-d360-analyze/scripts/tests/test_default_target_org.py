"""``--org`` is optional: entry points fall back to the sf CLI default org.

Covers ``dc.default_target_org`` (mocked at the subprocess boundary) and the
three user entry points that take ``--org`` — ``discover_sessions``,
``fetch_dc`` and ``resolve_session`` — with and without an explicit alias.

``default_target_org`` runs the show-access-token capability preflight
(``sf org auth show-access-token --help``) before ``sf config get``, so every
fake here routes by argv: the preflight gets real-shaped USAGE help (or a
"command missing" answer), and ``sf config get`` gets the canned payload.
"""
from __future__ import annotations

import io
import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import dc  # type: ignore
import discover_sessions  # type: ignore
import fetch_dc  # type: ignore
import resolve_session  # type: ignore
from .fixtures.synthetic_session import IDS  # type: ignore
from .test_fetch_dc_main import _MainHarness as _FetchHarness  # type: ignore

_CONFIG_ARGV = ["sf", "config", "get", "target-org", "--json"]
_PREFLIGHT_ARGV = ["sf", "org", "auth", "show-access-token", "--help"]
# Shape of real ``--help`` output (sf CLI 2.150.6).
_REAL_HELP = "USAGE\n  $ sf org auth show-access-token -o <value> [--json]\n"
_UPGRADE_MSG = "Upgrade/reinstall Salesforce CLI"
_NO_ORG_MSG = "no --org given and no default target org set"


def _config_payload(value: str | None) -> str:
    entry = {"name": "target-org", "location": "Local", "success": True}
    if value is not None:
        entry["value"] = value
    return json.dumps({"status": 0, "result": [entry], "warnings": []})


def _cp(stdout: str) -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _sf_run(value: str | None = None, *, config=None, preflight: str = "ok",
            calls: list | None = None):
    """subprocess.run stand-in routing by argv.

    ``preflight``: "ok" → real USAGE help; "nonzero" → the CLI rejects the
    unknown command (CalledProcessError); "no-usage" → exit 0 without the
    USAGE line (an old CLI echoing a not-found notice).
    ``config``: a callable/exception overriding the ``sf config get`` answer;
    default is the canned payload for ``value``. ``calls`` records argv.
    """
    def fake_run(argv, **kwargs):
        if calls is not None:
            calls.append((argv, kwargs))
        if argv == _PREFLIGHT_ARGV:
            if preflight == "ok":
                return _cp(_REAL_HELP)
            if preflight == "nonzero":
                raise subprocess.CalledProcessError(
                    returncode=127, cmd=argv,
                    stderr="Warning: show-access-token is not a sf command.",
                )
            if preflight == "no-usage":
                return _cp("Command org:auth:show-access-token not found.")
            raise AssertionError(f"bad preflight mode {preflight!r}")
        if argv == _CONFIG_ARGV:
            if isinstance(config, BaseException):
                raise config
            if callable(config):
                return config(argv, **kwargs)
            return _cp(_config_payload(value))
        raise AssertionError(f"unexpected argv: {argv}")
    return fake_run


def _sf_config_run(value: str | None):
    """A CLI with a working preflight whose default org is ``value``."""
    return _sf_run(value)


# A CLI lacking show-access-token, in both shapes the preflight rejects.
_MISSING_CMD_MODES = ("nonzero", "no-usage")


class _FreshPreflight(unittest.TestCase):
    """The preflight caches success process-wide; isolate every test."""

    def setUp(self):
        dc._show_access_token_capability_ok = False
        self.addCleanup(setattr, dc, "_show_access_token_capability_ok", False)


# -----------------------------------------------------------------------------
# dc.default_target_org
# -----------------------------------------------------------------------------


class DefaultTargetOrgTests(_FreshPreflight):

    def test_returns_configured_value_with_timeout(self):
        calls: list = []
        with mock.patch.object(
            dc.subprocess, "run", side_effect=_sf_run("my-default", calls=calls),
        ):
            self.assertEqual(dc.default_target_org(), "my-default")
        self.assertEqual([a for a, _ in calls], [_PREFLIGHT_ARGV, _CONFIG_ARGV])
        config_kwargs = calls[1][1]
        self.assertTrue(config_kwargs.get("timeout"))
        self.assertTrue(config_kwargs.get("check"))

    def test_missing_show_access_token_fails_before_config_get(self):
        for mode in _MISSING_CMD_MODES:
            with self.subTest(preflight=mode):
                dc._show_access_token_capability_ok = False
                calls: list = []
                with mock.patch.object(
                    dc.subprocess, "run",
                    side_effect=_sf_run(None, preflight=mode, calls=calls),
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        dc.default_target_org()
                msg = str(ctx.exception)
                self.assertIn("sf org auth show-access-token", msg)
                self.assertIn(_UPGRADE_MSG, msg)
                self.assertNotIn(_NO_ORG_MSG, msg)
                self.assertEqual([a for a, _ in calls], [_PREFLIGHT_ARGV])
                self.assertFalse(dc._show_access_token_capability_ok)

    def test_preflight_cached_across_default_org_and_resolve_org(self):
        calls: list = []
        base = _sf_run("my-default", calls=calls)

        def fake_run(argv, **kwargs):
            if argv[:3] == ["sf", "org", "display"]:
                calls.append((argv, kwargs))
                return _cp(json.dumps({"result": {"instanceUrl": "https://x"}}))
            if argv[:4] == ["sf", "org", "auth", "show-access-token"] and "--help" not in argv:
                calls.append((argv, kwargs))
                return _cp(json.dumps({"result": {"accessToken": "TOK"}}))
            return base(argv, **kwargs)

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            org = dc.default_target_org()
            self.assertEqual(dc.default_target_org(), org)
            self.assertEqual(dc.resolve_org(org), ("https://x", "TOK"))
        argvs = [a for a, _ in calls]
        self.assertEqual(argvs[0], _PREFLIGHT_ARGV)
        self.assertEqual(argvs.count(_PREFLIGHT_ARGV), 1, argvs)

    def test_empty_result_raises_clear_error(self):
        payloads = [
            _config_payload(None),                      # key unset
            _config_payload(""),                        # blank value
            json.dumps({"status": 0, "result": []}),    # no entries
            json.dumps({"status": 0}),                  # no result at all
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with mock.patch.object(
                    dc.subprocess, "run",
                    side_effect=_sf_run(config=lambda *a, _p=payload, **k: _cp(_p)),
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        dc.default_target_org()
                msg = str(ctx.exception)
                self.assertIn("no --org given and no default target org set", msg)
                self.assertIn("sf config set target-org <alias>", msg)

    def test_sf_failure_raises_redacted_error(self):
        err = subprocess.CalledProcessError(
            returncode=1, cmd=_CONFIG_ARGV,
            stderr='boom Authorization: Bearer 00DSECRET!tok "accessToken": "00DLEAK"',
        )
        with mock.patch.object(dc.subprocess, "run", side_effect=_sf_run(config=err)):
            with self.assertRaises(SystemExit) as ctx:
                dc.default_target_org()
        msg = str(ctx.exception)
        self.assertIn("no --org given and no default target org set", msg)
        self.assertIn("sf config get target-org", msg)
        self.assertIn("boom", msg)
        self.assertNotIn("00DSECRET", msg)
        self.assertNotIn("00DLEAK", msg)
        self.assertIn("<redacted>", msg)

    def test_sf_missing_raises_clear_error(self):
        # No sf at all: the preflight is the first call and reports it.
        calls: list = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            raise FileNotFoundError("sf")

        with mock.patch.object(dc.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(SystemExit) as ctx:
                dc.default_target_org()
        self.assertIn("sf CLI not found on PATH", str(ctx.exception))
        self.assertEqual(calls, [_PREFLIGHT_ARGV])

    def test_sf_vanishes_before_config_get_raises_clear_error(self):
        with mock.patch.object(
            dc.subprocess, "run", side_effect=_sf_run(config=FileNotFoundError("sf")),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.default_target_org()
        self.assertIn("sf CLI not found on PATH", str(ctx.exception))

    def test_timeout_raises_clear_error(self):
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=_sf_run(
                config=subprocess.TimeoutExpired(cmd=_CONFIG_ARGV, timeout=30),
            ),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.default_target_org()
        msg = str(ctx.exception)
        self.assertIn("`sf config get target-org` timed out", msg)
        self.assertIn(_NO_ORG_MSG, msg)

    def test_non_json_output_raises_clear_error(self):
        with mock.patch.object(
            dc.subprocess, "run",
            side_effect=_sf_run(config=lambda *a, **k: _cp("Warning: not json")),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dc.default_target_org()
        self.assertIn("non-JSON", str(ctx.exception))


# -----------------------------------------------------------------------------
# discover_sessions
# -----------------------------------------------------------------------------


class DiscoverSessionsOrgDefaultTests(_FreshPreflight):

    def _run(self, *argv: str, run_side_effect):
        with mock.patch.object(discover_sessions.sys, "argv",
                               ["discover_sessions.py", *argv]):
            with mock.patch.object(dc.subprocess, "run",
                                   side_effect=run_side_effect) as run:
                with mock.patch.object(
                    discover_sessions, "resolve_org",
                    return_value=("https://x", "T"),
                ) as resolve:
                    with mock.patch.object(discover_sessions, "post", return_value=[]):
                        with mock.patch("sys.stdout", io.StringIO()) as out:
                            rc = discover_sessions.main()
        return rc, run, resolve, out.getvalue()

    def test_no_org_uses_default_target_org(self):
        rc, run, resolve, out = self._run(
            "--grep", "refund", "--limit", "5",
            run_side_effect=_sf_config_run("def-org"),
        )
        self.assertEqual(rc, 2)  # zero rows
        self.assertEqual(
            [c.args[0] for c in run.call_args_list], [_PREFLIGHT_ARGV, _CONFIG_ARGV],
        )
        resolve.assert_called_once_with("def-org")
        self.assertIn("def-org", out)

    def test_explicit_org_wins_and_helper_not_called(self):
        with mock.patch.object(discover_sessions, "default_target_org") as helper:
            rc, run, resolve, _ = self._run(
                "--org", "explicit-org",
                run_side_effect=AssertionError("sf must not be called"),
            )
        self.assertEqual(rc, 2)
        helper.assert_not_called()
        run.assert_not_called()
        resolve.assert_called_once_with("explicit-org")

    def test_no_org_and_no_default_exits_with_clear_message(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run(run_side_effect=_sf_config_run(None))
        self.assertIn("no --org given and no default target org set", str(ctx.exception))

    def test_no_org_on_cli_lacking_show_access_token_reports_upgrade(self):
        # No default org AND no show-access-token: the upgrade message wins,
        # `sf config get` is never run, and no org resolution is attempted.
        for mode in _MISSING_CMD_MODES:
            with self.subTest(preflight=mode):
                dc._show_access_token_capability_ok = False
                calls: list = []
                with mock.patch.object(discover_sessions.sys, "argv",
                                       ["discover_sessions.py"]):
                    with mock.patch.object(
                        dc.subprocess, "run",
                        side_effect=_sf_run(None, preflight=mode, calls=calls),
                    ):
                        with mock.patch.object(discover_sessions, "resolve_org") as resolve:
                            with self.assertRaises(SystemExit) as ctx:
                                discover_sessions.main()
                msg = str(ctx.exception)
                self.assertIn(_UPGRADE_MSG, msg)
                self.assertNotIn(_NO_ORG_MSG, msg)
                self.assertNotIn(_CONFIG_ARGV, [a for a, _ in calls])
                self.assertEqual([a for a, _ in calls], [_PREFLIGHT_ARGV])
                resolve.assert_not_called()


# -----------------------------------------------------------------------------
# fetch_dc
# -----------------------------------------------------------------------------


class FetchDcOrgDefaultTests(_FreshPreflight):

    _BASE = ["fetch_dc.py", "--session", IDS.SID, "--no-assemble", "--no-render"]

    def test_no_org_uses_default_target_org(self):
        captured = {}

        def capture(ctx):
            captured.update(ctx)
            ctx["org_id_15"] = IDS.ORG_ID_15
            ctx["agent_api_name"] = IDS.AGENT_API
            ctx["agent_version"] = IDS.AGENT_VERSION

        with _FetchHarness():
            with mock.patch.object(fetch_dc, "_run_waterfall", side_effect=capture):
                with mock.patch.object(dc.subprocess, "run",
                                       side_effect=_sf_config_run("def-org")) as run:
                    with mock.patch.object(fetch_dc.sys, "argv", list(self._BASE)):
                        rc = fetch_dc.main()
                fetch_dc.preflight_dc_access.assert_called_once_with(IDS.SID, "def-org")
        self.assertEqual(rc, 0)
        self.assertEqual(
            [c.args[0] for c in run.call_args_list], [_PREFLIGHT_ARGV, _CONFIG_ARGV],
        )
        self.assertEqual(captured["org_alias"], "def-org")

    def test_explicit_org_wins_and_helper_not_called(self):
        with _FetchHarness():
            with mock.patch.object(fetch_dc, "default_target_org") as helper:
                with mock.patch.object(
                    fetch_dc.sys, "argv", [*self._BASE, "--org", "explicit-org"],
                ):
                    rc = fetch_dc.main()
                fetch_dc.preflight_dc_access.assert_called_once_with(
                    IDS.SID, "explicit-org",
                )
        self.assertEqual(rc, 0)
        helper.assert_not_called()

    def test_no_default_routes_through_dc_access_denied(self):
        with _FetchHarness(is_tty=False):
            with mock.patch.object(dc.subprocess, "run",
                                   side_effect=_sf_config_run(None)):
                with mock.patch.object(fetch_dc.sys, "argv", list(self._BASE)):
                    with mock.patch("sys.stdout", io.StringIO()) as out:
                        rc = fetch_dc.main()
            fetch_dc.preflight_dc_access.assert_not_called()
        self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)
        payload = json.loads(out.getvalue().strip().splitlines()[-1])
        self.assertEqual(payload["status"], "DC_ACCESS_DENIED")
        self.assertEqual(payload["reason"], "no_org")
        self.assertIn("no default target org set", payload["detail"])

    def test_no_org_on_cli_lacking_show_access_token_reports_upgrade(self):
        # Headless contract is unchanged (DC_ACCESS_DENIED, exit 10, same
        # reason code the explicit-org preflight failure already uses), but the
        # detail is the upgrade message and `sf config get` never runs.
        for mode in _MISSING_CMD_MODES:
            with self.subTest(preflight=mode):
                dc._show_access_token_capability_ok = False
                calls: list = []
                with _FetchHarness(is_tty=False):
                    with mock.patch.object(
                        dc.subprocess, "run",
                        side_effect=_sf_run(None, preflight=mode, calls=calls),
                    ):
                        with mock.patch.object(fetch_dc.sys, "argv", list(self._BASE)):
                            with mock.patch("sys.stdout", io.StringIO()) as out:
                                rc = fetch_dc.main()
                    fetch_dc.preflight_dc_access.assert_not_called()
                self.assertEqual(rc, fetch_dc.EXIT_DC_ACCESS_DENIED)
                payload = json.loads(out.getvalue().strip().splitlines()[-1])
                self.assertEqual(payload["status"], "DC_ACCESS_DENIED")
                self.assertIn(_UPGRADE_MSG, payload["detail"])
                self.assertNotIn(_NO_ORG_MSG, payload["detail"])
                self.assertEqual([a for a, _ in calls], [_PREFLIGHT_ARGV])


# -----------------------------------------------------------------------------
# resolve_session (live lookup only needs an org on a disk miss)
# -----------------------------------------------------------------------------


class ResolveSessionOrgDefaultTests(unittest.TestCase):

    _MSG = "0Mw000000000000"

    def _run(self, *argv: str):
        with mock.patch.object(resolve_session.sys, "argv",
                               ["resolve_session.py", "--id", self._MSG, *argv]):
            with mock.patch.object(resolve_session, "resolve_from_disk", return_value=None):
                with mock.patch.object(
                    resolve_session, "resolve", return_value="resolved-uuid",
                ) as resolve:
                    with mock.patch("sys.stdout", io.StringIO()) as out:
                        rc = resolve_session.main()
        return rc, resolve, out.getvalue()

    def test_disk_miss_without_org_uses_default(self):
        with mock.patch.object(
            resolve_session, "default_target_org", return_value="def-org",
        ) as helper:
            rc, resolve, out = self._run()
        self.assertEqual(rc, 0)
        helper.assert_called_once_with()
        resolve.assert_called_once_with(self._MSG, org="def-org")
        self.assertIn("resolved-uuid", out)

    def test_explicit_org_wins_and_helper_not_called(self):
        with mock.patch.object(resolve_session, "default_target_org") as helper:
            rc, resolve, _ = self._run("--org", "explicit-org")
        self.assertEqual(rc, 0)
        helper.assert_not_called()
        resolve.assert_called_once_with(self._MSG, org="explicit-org")


if __name__ == "__main__":
    unittest.main()
