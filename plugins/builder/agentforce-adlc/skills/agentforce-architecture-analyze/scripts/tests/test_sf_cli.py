"""Tests for sf_cli loads YAML with safe_load only.

Also covers redaction boundary for stderr content via the local
_redact_subprocess_stderr helper.
"""
from __future__ import annotations

import unittest

import yaml

from . import _bootstrap  # noqa: F401

import sf_cli  # type: ignore


class YamlSafeLoadTests(unittest.TestCase):
    """the bound loader must be identity-equal to yaml.safe_load."""

    def test_loader_is_yaml_safe_load(self):
        self.assertIs(
            sf_cli._SAFE_LOADER,
            yaml.safe_load,
            "sf_cli must use yaml.safe_load, not yaml.load ",
        )

    def test_module_docstring_mentions_safe_load(self):
        """The security contract lives in the docstring; reviewers who
        grep for `yaml.load` in this module should find only the banned
        reference plus the explanation."""
        self.assertIn("yaml.safe_load", sf_cli.__doc__ or "")
        self.assertIn("yaml.load is banned", sf_cli.__doc__ or "")

    def test_safe_load_rejects_python_object_construction(self):
        """Sanity check that safe_load actually differs from load —
        an attacker-controlled `!!python/object` tag must raise."""
        malicious = "!!python/object/apply:os.system ['echo pwned']"
        with self.assertRaises(yaml.YAMLError):
            sf_cli._SAFE_LOADER(malicious)


class StderrRedactionTests(unittest.TestCase):
    """subprocess stderr is redacted before reaching log/exception text."""

    def test_bearer_token_in_stderr_redacted(self):
        stderr = "Error: API call failed\nAuthorization: Bearer TESTONLY_STDERR_TOKEN\n"
        safe = sf_cli._redact_subprocess_stderr(stderr)
        self.assertNotIn("TESTONLY_STDERR_TOKEN", safe)
        self.assertIn("<redacted>", safe)

    def test_empty_stderr_returns_empty(self):
        self.assertEqual(sf_cli._redact_subprocess_stderr(""), "")
        self.assertEqual(sf_cli._redact_subprocess_stderr(None), "")


class ModuleTopImportTests(unittest.TestCase):
    """`redact_text` is imported at sf_cli module top. If anyone
    re-introduces a lazy `from rest_client import _redact_text` inside
    `_redact_subprocess_stderr`, these tests fail.
    """

    def test_redact_text_bound_at_module_top(self):
        self.assertTrue(hasattr(sf_cli, "redact_text"))
        # And it's the actual public function, not a stub.
        import rest_client as _rc
        self.assertIs(sf_cli.redact_text, _rc.redact_text)

    def test_subprocess_stderr_redaction_does_not_import_private(self):
        """Behavioral proof: redaction works without any lazy import. If
        rest_client.redact_text were renamed and nobody updated sf_cli's
        module-top import, the module would fail to load — an obvious,
        loud failure rather than a silent redaction skip at runtime.
        """
        stderr = "Authorization: Bearer TOKEN_MUST_NOT_SURVIVE"
        out = sf_cli._redact_subprocess_stderr(stderr)
        self.assertNotIn("TOKEN_MUST_NOT_SURVIVE", out)
        self.assertIn("<redacted>", out)


class StderrAuthLinePrefixTests(unittest.TestCase):
    """auth patterns only match on lines starting with Error:/Warning:.

    Tightens `_stderr_matches_auth` to line-anchored scanning so an
    embedded substring in prose (or a stray Node ESM warning that
    doesn't begin with Error:/Warning:) doesn't false-trigger
    AuthRequired.
    """

    PATTERNS = ("NoOrgAuthenticationError", "NamedOrgNotFoundError")

    def test_error_line_with_pattern_matches(self):
        stderr = "Error: NoOrgAuthenticationError — no org logged in\n"
        self.assertTrue(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))

    def test_warning_line_with_pattern_matches(self):
        """Warning-prefixed lines are ALSO in scope per the tightened rule.

        Some sf CLI plugins emit auth issues as Warning-level diagnostics
        before the hard Error; we don't want to miss those.
        """
        stderr = "Warning: NoOrgAuthenticationError — auth cache stale\n"
        self.assertTrue(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))

    def test_embedded_prose_does_not_match(self):
        """Pattern embedded mid-line without Error:/Warning: prefix → NO match.

        This is the behavior change: previous substring match would
        have false-positived here.
        """
        stderr = "see docs for NoOrgAuthenticationError troubleshooting\n"
        self.assertFalse(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))

    def test_empty_stderr_no_match(self):
        self.assertFalse(sf_cli._stderr_matches_auth("", self.PATTERNS))
        self.assertFalse(sf_cli._stderr_matches_auth(None, self.PATTERNS))

    def test_multiline_stderr_pattern_on_third_line_matches(self):
        stderr = (
            "Warning: @gthoppae/sf-cli-plugin-data360 is a linked ESM module\n"
            "debug: config loaded\n"
            "Error: NoOrgAuthenticationError — no default org\n"
        )
        self.assertTrue(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))

    def test_esm_warning_without_auth_pattern_no_match(self):
        """The exact warning shape we're trying NOT to false-positive on.

        If a future sf CLI plugin name happened to contain an auth pattern
        substring (unlikely but possible), the line-prefix rule alone
        wouldn't save us. For now, this canonical ESM warning contains no
        auth pattern, so it MUST NOT match.
        """
        stderr = (
            "Warning: @gthoppae/sf-cli-plugin-data360 is a linked ESM module\n"
            "and will not reload without CLI restart\n"
        )
        self.assertFalse(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))

    def test_other_prefix_with_pattern_does_not_match(self):
        """Lines that don't start with Error:/Warning: — even with a pattern
        substring — are filtered out."""
        stderr = "debug: NoOrgAuthenticationError transient\n"
        self.assertFalse(sf_cli._stderr_matches_auth(stderr, self.PATTERNS))


class RunSfTests(unittest.TestCase):
    """Cover ``run_sf`` end-to-end with subprocess mocked.

    Uses the real ``org_display`` recipe shipped under ``assets/cli/`` so
    the recipe load + arg substitution + auth-pattern config exercise
    real code paths.
    """

    from types import SimpleNamespace as _Namespace

    def _patch_subprocess(self, *, returncode: int = 0,
                          stdout: str = '{"status":0,"result":{}}',
                          stderr: str = "",
                          raise_exc: BaseException | None = None):
        from unittest import mock
        if raise_exc is not None:
            return mock.patch.object(sf_cli.subprocess, "run", side_effect=raise_exc)
        cp = self._Namespace(returncode=returncode, stdout=stdout, stderr=stderr)
        return mock.patch.object(sf_cli.subprocess, "run", return_value=cp)

    def test_returns_parsed_stdout_on_success(self):
        with self._patch_subprocess():
            data = sf_cli.run_sf("org_display", ORG_ALIAS="my-org")
        self.assertEqual(data, {"status": 0, "result": {}})

    def test_raises_when_required_param_missing(self):
        with self.assertRaises(sf_cli.SfCliError) as ctx:
            sf_cli.run_sf("org_display")  # missing ORG_ALIAS
        self.assertIn("missing required params", str(ctx.exception))
        self.assertIn("ORG_ALIAS", str(ctx.exception))

    def test_classifies_auth_failure_via_stderr_pattern(self):
        # org_display recipe has NoOrgAuthenticationError in its
        # auth_required_stderr_patterns list.
        with self._patch_subprocess(
            returncode=1,
            stdout='{"status":1}',
            stderr="Error: NoOrgAuthenticationError — no org\n",
        ):
            with self.assertRaises(sf_cli.AuthRequired):
                sf_cli.run_sf("org_display", ORG_ALIAS="my-org")

    def test_raises_sfcli_error_on_nonauth_failure(self):
        with self._patch_subprocess(
            returncode=1,
            stdout='{"status":1}',
            stderr="Error: SomethingElseBlewUp\n",
        ):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.run_sf("org_display", ORG_ALIAS="my-org")
        self.assertIn("exit=1", str(ctx.exception))

    def test_raises_sfcli_error_on_subprocess_timeout(self):
        import subprocess as _subprocess
        with self._patch_subprocess(
            raise_exc=_subprocess.TimeoutExpired(cmd=["sf"], timeout=1),
        ):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.run_sf("org_display", ORG_ALIAS="my-org")
        self.assertIn("timed out", str(ctx.exception))

    def test_raises_sfcli_error_when_binary_missing(self):
        # FileNotFoundError = sf binary not on PATH.
        with self._patch_subprocess(raise_exc=FileNotFoundError("sf not found")):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.run_sf("org_display", ORG_ALIAS="my-org")
        self.assertIn("invocation failed", str(ctx.exception))

    def test_does_not_inject_show_secrets_env(self):
        """Tripwire: run_sf must not rely on SF_TEMP_SHOW_SECRETS.

        sf CLI removes that env var (forcedotcom/cli#3560); tokens come
        only from ``sf org auth show-access-token``.
        """
        from unittest import mock
        captured = {}

        def fake_run(argv, **kwargs):
            captured["env"] = kwargs.get("env")
            captured["argv"] = argv
            return self._Namespace(
                returncode=0, stdout='{"status":0,"result":{}}', stderr="",
            )

        with mock.patch.object(sf_cli.subprocess, "run", side_effect=fake_run):
            sf_cli.run_sf("org_display", ORG_ALIAS="my-org")

        env = captured["env"] or {}
        self.assertNotIn("SF_TEMP_SHOW_SECRETS", env)

    def test_org_display_recipe_includes_verbose_flag(self):
        """Tripwire for the W-22582511 ``--verbose`` fix.

        Without ``--verbose``, some sf CLI builds omit fields that callers
        expect in ``--json`` output.
        """
        from unittest import mock
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return self._Namespace(
                returncode=0, stdout='{"status":0,"result":{}}', stderr="",
            )

        with mock.patch.object(sf_cli.subprocess, "run", side_effect=fake_run):
            sf_cli.run_sf("org_display", ORG_ALIAS="my-org")

        self.assertIn("--verbose", captured["argv"])


class ShowAccessTokenCapabilityTests(unittest.TestCase):
    """Preflight for the required ``sf org auth show-access-token`` command."""

    # Shape of real ``--help`` output (sf CLI 2.150.6): the command id is
    # printed in the USAGE line.
    REAL_HELP = (
        "Show an access token for an org.\n\nUSAGE\n"
        "  $ sf org auth show-access-token -o <value> [--json]\n"
    )

    def setUp(self):
        # The preflight caches success process-wide; isolate every test.
        sf_cli._show_access_token_capability_ok = False
        self.addCleanup(
            setattr, sf_cli, "_show_access_token_capability_ok", False,
        )

    def test_capability_check_passes_when_help_available(self):
        from types import SimpleNamespace
        from unittest import mock

        cp = SimpleNamespace(returncode=0, stdout=self.REAL_HELP, stderr="")
        with mock.patch.object(sf_cli.subprocess, "run", return_value=cp) as run:
            sf_cli.assert_show_access_token_capability()
        argv = run.call_args.args[0]
        self.assertEqual(argv, ["sf", "org", "auth", "show-access-token", "--help"])

    def test_capability_check_raises_clear_error_when_missing(self):
        import subprocess as _subprocess
        from unittest import mock

        err = _subprocess.CalledProcessError(
            returncode=1,
            cmd=["sf", "org", "auth", "show-access-token", "--help"],
            stderr="show-access-token is not a sf command",
        )
        with mock.patch.object(sf_cli.subprocess, "run", side_effect=err):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.assert_show_access_token_capability()
        self.assertIn("missing required command", str(ctx.exception))
        self.assertIn("sf org auth show-access-token", str(ctx.exception))

    def test_capability_check_raises_when_sf_not_on_path(self):
        from unittest import mock

        with mock.patch.object(
            sf_cli.subprocess, "run", side_effect=FileNotFoundError("sf"),
        ):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.assert_show_access_token_capability()
        self.assertIn("not found on PATH", str(ctx.exception))

    def test_successful_preflight_is_cached_for_process(self):
        from types import SimpleNamespace
        from unittest import mock

        cp = SimpleNamespace(returncode=0, stdout=self.REAL_HELP, stderr="")
        with mock.patch.object(sf_cli.subprocess, "run", return_value=cp) as run:
            sf_cli.assert_show_access_token_capability()
            sf_cli.assert_show_access_token_capability()
        self.assertEqual(run.call_count, 1)

    def test_failed_preflight_is_not_cached(self):
        import subprocess as _subprocess
        from types import SimpleNamespace
        from unittest import mock

        err = _subprocess.CalledProcessError(
            returncode=1,
            cmd=["sf", "org", "auth", "show-access-token", "--help"],
            stderr="show-access-token is not a sf command",
        )
        ok = SimpleNamespace(returncode=0, stdout=self.REAL_HELP, stderr="")
        with mock.patch.object(
            sf_cli.subprocess, "run", side_effect=[err, ok],
        ) as run:
            with self.assertRaises(sf_cli.SfCliError):
                sf_cli.assert_show_access_token_capability()
            # Retried (not cached) and now succeeds.
            sf_cli.assert_show_access_token_capability()
            # Success is cached — no third spawn.
            sf_cli.assert_show_access_token_capability()
        self.assertEqual(run.call_count, 2)

    def test_zero_exit_without_help_signature_fails_and_is_not_cached(self):
        """A CLI that answers an unknown command with exit 0 (e.g. printing
        top-level help) must NOT be treated as capable."""
        from types import SimpleNamespace
        from unittest import mock

        bogus = SimpleNamespace(
            returncode=0,
            stdout="\x1b[1mUSAGE\x1b[22m\n  $ sf [COMMAND]\n\nTOPICS\n  org\n",
            stderr="Authorization: Bearer SECRET_TOKEN_X",
        )
        ok = SimpleNamespace(returncode=0, stdout=self.REAL_HELP, stderr="")
        with mock.patch.object(
            sf_cli.subprocess, "run", side_effect=[bogus, ok],
        ) as run:
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.assert_show_access_token_capability()
            msg = str(ctx.exception)
            self.assertIn("missing required command", msg)
            self.assertNotIn("SECRET_TOKEN_X", msg)
            self.assertFalse(sf_cli._show_access_token_capability_ok)
            # Next call re-probes and now succeeds.
            sf_cli.assert_show_access_token_capability()
        self.assertEqual(run.call_count, 2)
        self.assertTrue(sf_cli._show_access_token_capability_ok)

    def test_zero_exit_with_empty_output_fails(self):
        from types import SimpleNamespace
        from unittest import mock

        cp = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(sf_cli.subprocess, "run", return_value=cp):
            with self.assertRaises(sf_cli.SfCliError) as ctx:
                sf_cli.assert_show_access_token_capability()
        self.assertIn("lacked the command signature", str(ctx.exception))
        self.assertFalse(sf_cli._show_access_token_capability_ok)

    def test_zero_exit_unknown_command_notice_echoing_name_fails(self):
        """Unknown-command notices contain the bare command name; only the
        USAGE form (`$ sf org auth show-access-token`) may pass."""
        from types import SimpleNamespace
        from unittest import mock

        for out in (
            "Error: Command org:auth:show-access-token not found.",
            "Warning: show-access-token is not a sf command.",
            "Did you mean org auth show-access-token? Run sf help for options.",
        ):
            with self.subTest(out=out):
                sf_cli._show_access_token_capability_ok = False
                cp = SimpleNamespace(returncode=0, stdout="", stderr=out)
                with mock.patch.object(sf_cli.subprocess, "run", return_value=cp):
                    with self.assertRaises(sf_cli.SfCliError) as ctx:
                        sf_cli.assert_show_access_token_capability()
                self.assertIn("missing required command", str(ctx.exception))
                self.assertFalse(sf_cli._show_access_token_capability_ok)

    def test_ansi_colored_real_help_passes(self):
        """Real help with ANSI styling still matches the signature."""
        from types import SimpleNamespace
        from unittest import mock

        cp = SimpleNamespace(
            returncode=0,
            stdout="\x1b[1mUSAGE\x1b[22m\n  $ sf org auth "
                   "show-access-token -o <value>\n",
            stderr="",
        )
        with mock.patch.object(sf_cli.subprocess, "run", return_value=cp):
            sf_cli.assert_show_access_token_capability()
        self.assertTrue(sf_cli._show_access_token_capability_ok)


if __name__ == "__main__":
    unittest.main()
