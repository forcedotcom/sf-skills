"""Tests for ``main._resolve_creds`` fail-fast token retrieval
(forcedotcom/cli#3560).

The access token must come ONLY from
``sf org auth show-access-token --json --no-prompt`` via the
``show_access_token`` recipe. ``sf org display`` supplies instanceUrl
only; any ``accessToken`` it carries is never used.

We mock ``run_sf`` (not subprocess) since these tests target the
orchestration logic in ``main.py``, not the recipe loader. The recipe
loader, subprocess env, and capability preflight have their own
coverage in ``test_sf_cli.py``.
"""
from __future__ import annotations

import unittest
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import main  # type: ignore
from sf_cli import AuthRequired, SfCliError  # type: ignore


REDACTED_TOKEN = "[REDACTED] Use 'sf org auth show-access-token' to view"


def _display_payload(*, instance_url="https://example.salesforce.com",
                     access_token="TOKEN_FROM_DISPLAY"):
    return {"result": {
        "instanceUrl": instance_url,
        "accessToken": access_token,
    }}


def _show_token_payload(*, access_token="TOKEN_FROM_SHOW"):
    return {"result": {"accessToken": access_token}}


class ResolveCredsTests(unittest.TestCase):
    """Cover every branch of fail-fast token retrieval."""

    def setUp(self):
        patcher = mock.patch.object(
            main, "assert_show_access_token_capability", return_value=None,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _route(self, *, primary_payload=None, primary_exc=None,
               display_payload=None):
        """Build a ``run_sf`` side-effect that dispatches by recipe name."""
        display = display_payload or _display_payload()
        primary = primary_payload or _show_token_payload()

        def fake_run_sf(name, **params):
            if name == "org_display":
                return display
            if name == "show_access_token":
                if primary_exc is not None:
                    raise primary_exc
                return primary
            raise AssertionError(f"unexpected recipe: {name}")

        return fake_run_sf

    def test_primary_path_returns_show_token(self):
        """Happy path — dedicated command returns a clean token."""
        with mock.patch.object(main, "run_sf", side_effect=self._route()):
            url, token = main._resolve_creds("my-org")
        self.assertEqual(url, "https://example.salesforce.com")
        self.assertEqual(token, "TOKEN_FROM_SHOW")

    def test_primary_unknown_raises_authrequired(self):
        """show-access-token failing is terminal — the display payload's
        accessToken (non-empty here) must NOT be used as a fallback."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_exc=SfCliError("sf CLI 'show_access_token' failed"),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("show-access-token", str(ctx.exception))
        self.assertNotIn("TOKEN_FROM_DISPLAY", str(ctx.exception))

    def test_primary_auth_required_propagates_as_authrequired(self):
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_exc=AuthRequired("NoOrgAuthenticationError"),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("show-access-token", str(ctx.exception))

    def test_primary_returns_redacted_token_raises(self):
        """Dedicated command runs cleanly but returns the placeholder
        string — fail fast rather than handing it to Tooling/REST callers
        (which would 401 with INVALID_AUTH_HEADER)."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_payload=_show_token_payload(access_token=REDACTED_TOKEN),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("usable access token", str(ctx.exception))

    def test_primary_returns_empty_token_raises(self):
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                primary_payload=_show_token_payload(access_token=""),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("usable access token", str(ctx.exception))

    def test_missing_instance_url_raises_authrequired(self):
        """display returning empty instanceUrl is a hard failure — no
        amount of token-juggling helps if we can't talk to the org."""
        with mock.patch.object(
            main, "run_sf",
            side_effect=self._route(
                display_payload=_display_payload(instance_url=""),
            ),
        ):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("instanceUrl", str(ctx.exception))

    def test_primary_path_recipe_name_is_show_access_token(self):
        """Tripwire — the primary call MUST go through the
        ``show_access_token`` recipe. Without it the patch silently
        regresses to reading a (redacted) token from ``sf org display``."""
        recipes_called: list[str] = []

        def fake_run_sf(name, **params):
            recipes_called.append(name)
            if name == "org_display":
                return _display_payload()
            if name == "show_access_token":
                return _show_token_payload()
            raise AssertionError(f"unexpected recipe: {name}")

        with mock.patch.object(main, "run_sf", side_effect=fake_run_sf):
            main._resolve_creds("my-org")

        self.assertIn("show_access_token", recipes_called)
        # And the alias was passed through:
        # (We don't capture params here, but the recipe loader enforces
        # required_params at run_sf time — see test_sf_cli.py.)

    def test_capability_preflight_failure_raises_authrequired(self):
        """Missing ``sf org auth show-access-token`` fails fast with the
        preflight's upgrade message, before any token call is made."""
        recipes_called: list[str] = []

        def fake_run_sf(name, **params):
            recipes_called.append(name)
            return self._route()(name, **params)

        with mock.patch.object(
            main, "assert_show_access_token_capability",
            side_effect=SfCliError(
                "sf CLI is missing required command "
                "'sf org auth show-access-token'"
            ),
        ), mock.patch.object(main, "run_sf", side_effect=fake_run_sf):
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("missing required command", str(ctx.exception))
        # Preflight runs first: neither `sf org display` nor the token
        # command may be invoked when it fails.
        self.assertEqual(recipes_called, [])

    def test_preflight_runs_before_org_display(self):
        calls: list[str] = []

        def fake_run_sf(name, **params):
            calls.append(name)
            return self._route()(name, **params)

        with mock.patch.object(
            main, "assert_show_access_token_capability",
            side_effect=lambda: calls.append("preflight"),
        ), mock.patch.object(main, "run_sf", side_effect=fake_run_sf):
            main._resolve_creds("my-org")
        self.assertEqual(calls, ["preflight", "org_display", "show_access_token"])


class ResolveCredsPreflightCacheTests(unittest.TestCase):
    """Exercise the REAL preflight (subprocess mocked) through
    ``_resolve_creds``: argv order, once-per-process success caching, and
    no caching of failures."""

    PREFLIGHT_ARGV = ["sf", "org", "auth", "show-access-token", "--help"]
    REAL_HELP = "USAGE\n  $ sf org auth show-access-token -o <value>\n"

    def setUp(self):
        import sf_cli  # type: ignore
        self.sf_cli = sf_cli
        sf_cli._show_access_token_capability_ok = False
        self.addCleanup(
            setattr, sf_cli, "_show_access_token_capability_ok", False,
        )

    def _patches(self, calls, preflight_effects):
        """Patch subprocess (preflight) + run_sf (recipes) into one ordered
        ``calls`` log. ``preflight_effects`` is consumed per preflight spawn."""
        from types import SimpleNamespace
        effects = list(preflight_effects)

        def fake_subprocess_run(argv, **kwargs):
            calls.append(list(argv))
            effect = effects.pop(0)
            if isinstance(effect, BaseException):
                raise effect
            if effect == "no-signature":
                # Zero exit but not the command's help (unknown command).
                return SimpleNamespace(
                    returncode=0, stdout="USAGE\n  $ sf [COMMAND]\n", stderr="",
                )
            return SimpleNamespace(
                returncode=0, stdout=self.REAL_HELP, stderr="",
            )

        def fake_run_sf(name, **params):
            calls.append(name)
            if name == "org_display":
                return _display_payload()
            if name == "show_access_token":
                return _show_token_payload()
            raise AssertionError(f"unexpected recipe: {name}")

        return (
            mock.patch.object(
                self.sf_cli.subprocess, "run", side_effect=fake_subprocess_run,
            ),
            mock.patch.object(main, "run_sf", side_effect=fake_run_sf),
        )

    def test_preflight_argv_is_first_sf_call(self):
        calls: list = []
        p1, p2 = self._patches(calls, ["ok"])
        with p1, p2:
            main._resolve_creds("my-org")
        self.assertEqual(calls[0], self.PREFLIGHT_ARGV)
        self.assertEqual(calls[1:], ["org_display", "show_access_token"])

    def test_preflight_runs_once_across_two_resolves(self):
        calls: list = []
        p1, p2 = self._patches(calls, ["ok"])
        with p1, p2:
            main._resolve_creds("my-org")
            main._resolve_creds("my-org")
        self.assertEqual(calls.count(self.PREFLIGHT_ARGV), 1)
        self.assertEqual(calls.count("org_display"), 2)

    def test_missing_sf_fails_preflight_and_skips_display(self):
        calls: list = []
        p1, p2 = self._patches(calls, [FileNotFoundError("sf")])
        with p1, p2:
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
        self.assertIn("not found on PATH", str(ctx.exception))
        self.assertNotIn("org_display", calls)

    def test_failed_preflight_is_retried_on_next_resolve(self):
        import subprocess as _subprocess
        err = _subprocess.CalledProcessError(
            returncode=1, cmd=self.PREFLIGHT_ARGV,
            stderr="show-access-token is not a sf command",
        )
        calls: list = []
        p1, p2 = self._patches(calls, [err, "ok"])
        with p1, p2:
            with self.assertRaises(AuthRequired):
                main._resolve_creds("my-org")
            self.assertNotIn("org_display", calls)
            url, token = main._resolve_creds("my-org")
        self.assertEqual(token, "TOKEN_FROM_SHOW")
        self.assertEqual(calls.count(self.PREFLIGHT_ARGV), 2)

    def test_zero_exit_without_help_signature_fails_and_is_retried(self):
        calls: list = []
        p1, p2 = self._patches(calls, ["no-signature", "ok"])
        with p1, p2:
            with self.assertRaises(AuthRequired) as ctx:
                main._resolve_creds("my-org")
            self.assertIn("missing required command", str(ctx.exception))
            self.assertNotIn("org_display", calls)
            self.assertFalse(self.sf_cli._show_access_token_capability_ok)
            url, token = main._resolve_creds("my-org")
        self.assertEqual(token, "TOKEN_FROM_SHOW")
        self.assertEqual(calls.count(self.PREFLIGHT_ARGV), 2)


if __name__ == "__main__":
    unittest.main()
