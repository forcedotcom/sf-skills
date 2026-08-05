#!/usr/bin/env python3
"""Unit tests for the cross-platform executable resolver in sf_context.py
(WIN-026) and the deterministic setup/org reporting (WIN-027).

These are the evidence for the Windows fix: they simulate Windows resolution of a
`.cmd`/`.bat` shim (via a faked `shutil.which`) and assert that a COMSPEC-wrapped
ARGV ARRAY is built — never a shell string — while POSIX paths spawn directly.
They also assert that a genuinely-missing tool is reported FAILED (not silently
empty, not green) and that failure diagnostics never leak tokens/secrets.

Offline: no live org, no real subprocess spawn (subprocess.run / shutil.which are
mocked). Stdlib unittest only (no pytest/PyYAML) so it runs anywhere Python does,
including the 3.9 baseline.

Run: python3 plugins/builder/salesforce-development/scripts/test/test_sf_context.py
"""
from __future__ import annotations

import importlib.util
import json
import io
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

# sf_context.py is the sibling of this test's parent dir: scripts/test/ → scripts/.
# (The runtime lives under scripts/ rather than bin/ because this repo's
# .gitignore blocks bin/ — see the bin/README.md note.)
_MODULE_PATH = Path(__file__).resolve().parent.parent / "sf_context.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sf_context_under_test", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


sfx = _load_module()


def _completed(stdout="", returncode=0, stderr=""):
    """A stand-in for subprocess.CompletedProcess (only the fields run() reads)."""
    return types.SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


class ResolveExecutableTests(unittest.TestCase):
    def test_delegates_to_shutil_which(self):
        with mock.patch.object(sfx.shutil, "which", return_value="/usr/local/bin/sf") as which:
            self.assertEqual(sfx.resolve_executable("sf"), "/usr/local/bin/sf")
            which.assert_called_once_with("sf")

    def test_windows_shim_found_via_pathext(self):
        # shutil.which honors PATHEXT on Windows, so a bare "sf" resolves to sf.cmd.
        with mock.patch.object(sfx.shutil, "which", return_value=r"C:\tools\sf\bin\sf.cmd"):
            self.assertEqual(sfx.resolve_executable("sf"), r"C:\tools\sf\bin\sf.cmd")

    def test_missing_returns_none(self):
        with mock.patch.object(sfx.shutil, "which", return_value=None):
            self.assertIsNone(sfx.resolve_executable("definitely-not-a-tool"))

    def test_empty_name_returns_none(self):
        self.assertIsNone(sfx.resolve_executable(""))


class BuildCommandTests(unittest.TestCase):
    def test_posix_spawns_resolved_path_directly(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            argv = sfx.build_command("sf", ["config", "get", "target-org", "--json"])
        self.assertEqual(argv, ["/usr/local/bin/sf", "config", "get", "target-org", "--json"])
        # A plain argv array, first element the resolved binary (no cmd wrapper).
        self.assertIsInstance(argv, list)
        self.assertNotIn("/c", argv)

    def test_windows_cmd_shim_wrapped_with_comspec(self):
        resolved = r"C:\Program Files\sf\bin\sf.cmd"
        with mock.patch.object(sfx, "resolve_executable", return_value=resolved), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": r"C:\Windows\System32\cmd.exe"}, clear=False):
            argv = sfx.build_command("sf", ["config", "get", "target-org"])
        self.assertEqual(
            argv,
            [r"C:\Windows\System32\cmd.exe", "/c", resolved, "config", "get", "target-org"],
        )

    def test_windows_bat_shim_wrapped(self):
        resolved = r"C:\tools\npm.bat"
        with mock.patch.object(sfx, "resolve_executable", return_value=resolved), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": r"C:\Windows\System32\cmd.exe"}, clear=False):
            argv = sfx.build_command("npm", ["--version"])
        self.assertEqual(argv, [r"C:\Windows\System32\cmd.exe", "/c", resolved, "--version"])

    def test_comspec_falls_back_to_cmd_exe(self):
        resolved = r"C:\tools\sf.cmd"
        env_without_comspec = {k: v for k, v in sfx.os.environ.items() if k != "COMSPEC"}
        with mock.patch.object(sfx, "resolve_executable", return_value=resolved), \
                mock.patch.dict(sfx.os.environ, env_without_comspec, clear=True):
            argv = sfx.build_command("sf", ["version"])
        self.assertEqual(argv, ["cmd.exe", "/c", resolved, "version"])

    def test_missing_tool_returns_none(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            self.assertIsNone(sfx.build_command("sf", ["version"]))

    def test_never_builds_a_shell_string(self):
        # The crux of the .cmd case: "no shell" and "injection-safe" are reconciled
        # by keeping an ARGV ARRAY. Assert the result is always a list of tokens,
        # never a single concatenated command string.
        for resolved in (r"C:\tools\sf.cmd", "/usr/local/bin/sf"):
            with mock.patch.object(sfx, "resolve_executable", return_value=resolved):
                argv = sfx.build_command("sf", ["config", "get"])
            self.assertIsInstance(argv, list)
            for token in argv:
                self.assertIsInstance(token, str)

    def test_cmd_shim_refuses_metacharacter_args(self):
        # cmd.exe re-parses its command line, so an arg with a shell metacharacter
        # must NOT reach a batch shim. build_command fails closed (returns None).
        for bad in ("safe&whoami", "a|b", "x>y", "a<b", "p^q", "%PATH%", 'a"b',
                    "a!b", "a(b", "a)b", "a\nb", "a\rb"):
            with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                    mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False):
                argv = sfx.build_command("sf", ["config", "get", bad])
            self.assertIsNone(argv, f"metacharacter arg should be refused: {bad!r}")

    def test_cmd_shim_refuses_dangerous_path(self):
        # A reparse-dangerous char in the resolved shim PATH is also refused
        # (e.g. `%` env-expansion or unquoted `&`), fail closed.
        for bad_path in (r"C:\a&b\sf.cmd", r"C:\weird%dir\sf.cmd", r"C:\x!y\sf.cmd"):
            with mock.patch.object(sfx, "resolve_executable", return_value=bad_path), \
                    mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False):
                self.assertIsNone(sfx.build_command("sf", ["version"]),
                                  f"dangerous shim path should be refused: {bad_path!r}")

    def test_cmd_shim_allows_program_files_x86_path(self):
        # `(` `)` appear in legitimate install paths, so the PATH guard must NOT
        # reject them (they're only rejected in ARGS).
        resolved = r"C:\Program Files (x86)\sf\bin\sf.cmd"
        with mock.patch.object(sfx, "resolve_executable", return_value=resolved), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False):
            argv = sfx.build_command("sf", ["version"])
        self.assertEqual(argv, ["cmd.exe", "/c", resolved, "version"])

    def test_posix_path_allows_metacharacters(self):
        # The reparse hazard is cmd.exe-specific; a direct shell=False spawn of a
        # POSIX/.exe path is not subject to it, so args pass through unchanged.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            argv = sfx.build_command("sf", ["config", "get", "safe&whoami"])
        self.assertEqual(argv, ["/usr/local/bin/sf", "config", "get", "safe&whoami"])

    def test_cmd_shim_allows_ordinary_args(self):
        # A normal alias/flag arg (no metacharacters, spaces ok) still runs.
        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False):
            argv = sfx.build_command("sf", ["org", "display", "--target-org", "my-scratch"])
        self.assertEqual(argv, ["cmd.exe", "/c", r"C:\tools\sf.cmd", "org", "display", "--target-org", "my-scratch"])

    def test_run_refuses_metacharacter_arg_and_never_spawns(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run") as spawn:
            self.assertEqual(sfx.run(["sf", "config", "get", "a&b"]), "")
        spawn.assert_not_called()

    def test_preserves_argv_boundaries(self):
        # A SOQL query with spaces must remain ONE argv element (no concatenation),
        # both on POSIX and inside the cmd wrapper.
        query = "SELECT Id FROM Account WHERE Name = 'Acme Inc'"
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            argv = sfx.build_command("sf", ["data", "query", "--query", query])
        self.assertIn(query, argv)
        self.assertEqual(argv[-1], query)

        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False):
            argv = sfx.build_command("sf", ["data", "query", "--query", query])
        self.assertEqual(argv[-1], query)
        self.assertEqual(argv[:2], ["cmd.exe", "/c"])


class RunTests(unittest.TestCase):
    def test_run_spawns_comspec_argv_with_shell_false(self):
        resolved = r"C:\tools\sf.cmd"
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return _completed(stdout="ok-out", returncode=0)

        with mock.patch.object(sfx, "resolve_executable", return_value=resolved), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run", side_effect=fake_run):
            out = sfx.run(["sf", "config", "get", "target-org", "--json"])

        self.assertEqual(out, "ok-out")
        self.assertEqual(captured["argv"], ["cmd.exe", "/c", resolved, "config", "get", "target-org", "--json"])
        self.assertIsInstance(captured["argv"], list)
        self.assertIs(captured["kwargs"].get("shell"), False)

    def test_run_posix_spawns_resolved_path(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            return _completed(stdout="v1", returncode=0)

        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/git"), \
                mock.patch.object(sfx.subprocess, "run", side_effect=fake_run):
            out = sfx.run(["git", "--version"])

        self.assertEqual(out, "v1")
        self.assertEqual(captured["argv"], ["/usr/local/bin/git", "--version"])

    def test_run_missing_tool_returns_empty_and_never_spawns(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None), \
                mock.patch.object(sfx.subprocess, "run") as spawn:
            self.assertEqual(sfx.run(["sf", "version"]), "")
        spawn.assert_not_called()

    def test_run_nonzero_returncode_returns_empty(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run", return_value=_completed(stdout="x", returncode=1)):
            self.assertEqual(sfx.run(["sf", "version"]), "")

    def test_run_timeout_returns_empty(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  side_effect=sfx.subprocess.TimeoutExpired(cmd="sf", timeout=1)):
            self.assertEqual(sfx.run(["sf", "version"]), "")

    def test_run_applies_platform_default_timeout(self):
        # An unspecified timeout resolves to the platform-aware _cli_timeout()
        # (longer on Windows to survive slow cold `sf.cmd` startup under load).
        captured = {}

        def fake_run(argv, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _completed(stdout="x", returncode=0)

        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.object(sfx, "_is_windows", return_value=True), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run", side_effect=fake_run):
            sfx.run(["sf", "config", "get", "target-org"])
        self.assertEqual(captured["timeout"], 30)

        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx, "_is_windows", return_value=False), \
                mock.patch.object(sfx.subprocess, "run", side_effect=fake_run):
            sfx.run(["sf", "version"])
        self.assertEqual(captured["timeout"], 10)


class PlatformTuningTests(unittest.TestCase):
    def test_cli_timeout_scales_on_windows(self):
        with mock.patch.object(sfx, "_is_windows", return_value=True):
            self.assertEqual(sfx._cli_timeout(), 30)
        with mock.patch.object(sfx, "_is_windows", return_value=False):
            self.assertEqual(sfx._cli_timeout(), 10)

    def test_check_tools_workers_reduced_on_windows(self):
        with mock.patch.object(sfx, "_is_windows", return_value=True):
            self.assertEqual(sfx._check_tools_workers(), 3)
        with mock.patch.object(sfx, "_is_windows", return_value=False):
            self.assertEqual(sfx._check_tools_workers(), 7)


class ForceUtf8StdioTests(unittest.TestCase):
    def test_reconfigures_stdout_and_stderr_to_utf8(self):
        # Windows cp1252 consoles can't encode the box-drawing glyphs the status
        # commands print; startup reconfigures the streams to UTF-8.
        calls = []

        class FakeStream:
            def reconfigure(self, **kw):
                calls.append(kw)

        with mock.patch.object(sfx.sys, "stdout", FakeStream()), \
                mock.patch.object(sfx.sys, "stderr", FakeStream()):
            sfx._force_utf8_stdio()
        self.assertEqual(calls, [{"encoding": "utf-8"}, {"encoding": "utf-8"}])

    def test_stream_without_reconfigure_is_safe(self):
        class NoReconfigure:
            pass

        with mock.patch.object(sfx.sys, "stdout", NoReconfigure()), \
                mock.patch.object(sfx.sys, "stderr", NoReconfigure()):
            sfx._force_utf8_stdio()  # must not raise

    def test_reconfigure_error_is_swallowed(self):
        class BadStream:
            def reconfigure(self, **kw):
                raise ValueError("boom")

        with mock.patch.object(sfx.sys, "stdout", BadStream()), \
                mock.patch.object(sfx.sys, "stderr", BadStream()):
            sfx._force_utf8_stdio()  # must not raise


class GetTargetOrgTests(unittest.TestCase):
    _CONFIG_JSON = json.dumps(
        {"result": [{"name": "target-org", "value": "myScratch"}]}
    )
    _NO_ORG_JSON = json.dumps({"result": [{"name": "target-org"}]})

    def setUp(self):
        # get_target_org_detailed now honors SF_TARGET_ORG / SFDX_TARGET_ORG before
        # the CLI config (matching `sf` and the proxy). Scrub them so the CLI-mock
        # cases below observe the config path, not the runner's ambient env.
        patcher = mock.patch.dict(sfx.os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        sfx.os.environ.pop("SF_TARGET_ORG", None)
        sfx.os.environ.pop("SFDX_TARGET_ORG", None)

    def test_succeeds_when_sf_resolves_to_cmd_shim(self):
        # The Windows regression: get_target_org() returned "" because sf.cmd
        # could not be launched. With the resolver it must succeed.
        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=self._CONFIG_JSON, returncode=0)):
            self.assertEqual(sfx.get_target_org(), "myScratch")

    def test_missing_cli_reports_no_org_not_a_crash(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            self.assertEqual(sfx.get_target_org(), "")

    def test_detailed_distinguishes_no_org_from_cli_failure(self):
        # CLI ran, org set → (alias, "").
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=self._CONFIG_JSON, returncode=0)):
            self.assertEqual(sfx.get_target_org_detailed(), ("myScratch", ""))

        # CLI ran, no org set → ("", "") (empty reason = genuinely no org).
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=self._NO_ORG_JSON, returncode=0)):
            self.assertEqual(sfx.get_target_org_detailed(), ("", ""))

        # CLI present but query failed (nonzero) → ("", "nonzero"), NOT a false no-org.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout="", returncode=1)):
            alias, reason = sfx.get_target_org_detailed()
            self.assertEqual(alias, "")
            self.assertEqual(reason, "nonzero")

        # CLI query timed out → ("", "timeout").
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  side_effect=sfx.subprocess.TimeoutExpired(cmd="sf", timeout=1)):
            self.assertEqual(sfx.get_target_org_detailed(), ("", "timeout"))

    def test_detailed_flags_invalid_output_on_exit_zero(self):
        # sf exits 0 but the payload can't be trusted → "invalid-output", never a
        # false "no org configured" and never a crash on an unexpected shape.
        cases = {
            "malformed JSON": "{not valid json",
            "empty stdout": "",
            "non-object root (array)": "[1, 2, 3]",
            "non-object root (scalar)": "\"hi\"",
            "missing result field": json.dumps({"status": 0}),
            "result not a list (object)": json.dumps({"result": {}}),
            "result not a list (string)": json.dumps({"result": "x"}),
        }
        for label, payload in cases.items():
            with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                    mock.patch.object(sfx.subprocess, "run",
                                      return_value=_completed(stdout=payload, returncode=0)):
                alias, reason = sfx.get_target_org_detailed()
            self.assertEqual(alias, "", f"{label}: alias should be empty")
            self.assertEqual(reason, "invalid-output", f"{label}: reason should be invalid-output")

    def test_detailed_well_formed_no_entry_is_no_org(self):
        # A well-formed empty/other-key result is genuinely "no org" (not invalid),
        # and non-dict entries in the list don't crash.
        for payload in (json.dumps({"result": []}),
                        json.dumps({"result": [{"name": "other"}]}),
                        json.dumps({"result": ["stringy", 5, None]})):
            with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                    mock.patch.object(sfx.subprocess, "run",
                                      return_value=_completed(stdout=payload, returncode=0)):
                self.assertEqual(sfx.get_target_org_detailed(), ("", ""))

    def test_env_target_org_takes_precedence_over_config(self):
        # SF_TARGET_ORG / SFDX_TARGET_ORG must win over the CLI config, matching
        # how `sf` itself and the proxy's resolveTargetOrg() resolve the org. If
        # the consumer read config here while the proxy stamped sidecars with the
        # env org, the MCP-health filter would reject valid sidecars.
        for var in ("SF_TARGET_ORG", "SFDX_TARGET_ORG"):
            with self.subTest(var=var):
                # The CLI would say "myScratch"; the env override must win — and
                # subprocess.run must not even be consulted (short-circuit).
                run_spy = mock.MagicMock(
                    return_value=_completed(stdout=self._CONFIG_JSON, returncode=0))
                with mock.patch.dict(sfx.os.environ, {var: "envOrg"}, clear=False), \
                        mock.patch.object(sfx.subprocess, "run", run_spy):
                    self.assertEqual(sfx.get_target_org_detailed(), ("envOrg", ""))
                    run_spy.assert_not_called()

    def test_sf_target_org_wins_over_sfdx_target_org(self):
        # When both are set, SF_TARGET_ORG takes priority (same order as the proxy).
        with mock.patch.dict(sfx.os.environ,
                             {"SF_TARGET_ORG": "sfOrg", "SFDX_TARGET_ORG": "sfdxOrg"},
                             clear=False):
            self.assertEqual(sfx.get_target_org_detailed(), ("sfOrg", ""))


class RunResultTests(unittest.TestCase):
    def test_ok_result(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout="hi", returncode=0)):
            res = sfx.run_result(["sf", "version"])
        self.assertTrue(res.ok)
        self.assertEqual(res.stdout, "hi")
        self.assertEqual(res.reason, "")

    def test_unresolved_reason(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            res = sfx.run_result(["sf", "version"])
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "unresolved")

    def test_nonzero_reason(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout="", returncode=2)):
            res = sfx.run_result(["sf", "version"])
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "nonzero")
        self.assertEqual(res.returncode, 2)

    def test_timeout_reason(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  side_effect=sfx.subprocess.TimeoutExpired(cmd="sf", timeout=1)):
            self.assertEqual(sfx.run_result(["sf", "version"]).reason, "timeout")

    def test_run_wrapper_preserves_empty_on_failure(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout="junk", returncode=1)):
            self.assertEqual(sfx.run(["sf", "version"]), "")


class CheckToolsTests(unittest.TestCase):
    def test_sf_cli_ok_when_cmd_shim_resolves(self):
        version_out = "@salesforce/cli/2.100.0 win32-x64 node-v20.0.0"
        with mock.patch.object(sfx, "resolve_executable", return_value=r"C:\tools\sf.cmd"), \
                mock.patch.dict(sfx.os.environ, {"COMSPEC": "cmd.exe"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=version_out, returncode=0)):
            result = sfx._check_sf_cli()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["version"], "2.100.0")

    def test_sf_cli_warns_when_update_available(self):
        # Readiness = latest. The cached oclif notice (on `sf version` stderr)
        # reports a newer release, so an installed-but-outdated CLI is 🟡, not 🟢.
        version_out = "@salesforce/cli/2.130.9 darwin-arm64 node-v22.0.0"
        stderr_out = " ›   Warning: @salesforce/cli update available from 2.130.9 to 2.144.6."
        env = {k: v for k, v in sfx.os.environ.items() if k != sfx._UPDATE_CHECK_ENV}
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.dict(sfx.os.environ, env, clear=True), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=version_out, stderr=stderr_out, returncode=0)):
            result = sfx._check_sf_cli()
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["version"], "2.130.9")
        self.assertIn("2.144.6", result["message"])

    def test_sf_cli_ok_when_up_to_date(self):
        # No update notice on stderr → the CLI is current → 🟢.
        version_out = "@salesforce/cli/2.144.6 darwin-arm64 node-v22.0.0"
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=version_out, stderr="", returncode=0)):
            result = sfx._check_sf_cli()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["version"], "2.144.6")

    def test_sf_cli_update_check_opt_out_stays_ok(self):
        # SFDX_SKIP_CLI_UPDATE_CHECK=1 disables the readiness warn even when an
        # update notice is present — a user who opted out never sees the 🟡.
        version_out = "@salesforce/cli/2.130.9 darwin-arm64 node-v22.0.0"
        stderr_out = " ›   Warning: @salesforce/cli update available from 2.130.9 to 2.144.6."
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"), \
                mock.patch.dict(sfx.os.environ, {sfx._UPDATE_CHECK_ENV: "1"}, clear=False), \
                mock.patch.object(sfx.subprocess, "run",
                                  return_value=_completed(stdout=version_out, stderr=stderr_out, returncode=0)):
            result = sfx._check_sf_cli()
        self.assertEqual(result["status"], "ok")

    def test_missing_sf_cli_reported_critical_not_silently_empty(self):
        # A genuinely-missing tool: resolver finds nothing, run() returns "".
        # WIN-027: this must be reported FAILED, never silently empty or green.
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            result = sfx._check_sf_cli()
        self.assertEqual(result["status"], "critical")
        self.assertNotEqual(result["status"], "ok")
        self.assertIn("Not found", result["message"])

    def test_missing_npm_reported_critical(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            result = sfx._check_npm()
        self.assertEqual(result["status"], "critical")

    def test_mcp_check_keeps_three_concerns_distinct(self):
        # WIN-027: config presence, per-server platform-MCP health (WIN-033/040),
        # and process health are separate rows; process health is NEVER inferred
        # green from config.
        with mock.patch.object(sfx, "_probe_server",
                                side_effect=lambda slug, timeout=None: {
                                    "name": sfx._mcp_row_name(slug), "status": "warn",
                                    "version": None, "message": "stubbed"}):
            rows = sfx._check_mcp()
        names = [r["name"] for r in rows]
        self.assertIn("Salesforce MCP (config)", names)
        self.assertIn("Salesforce MCP (salesforce-api-context)", names)
        self.assertIn("Salesforce MCP (metadata-experts)", names)
        self.assertIn("Salesforce MCP (process)", names)
        process_row = next(r for r in rows if r["name"] == "Salesforce MCP (process)")
        # Process health is informational (not a warning), so a healthy setup can
        # read fully green — but it is never inferred "ok" from config/endpoint.
        self.assertEqual(process_row["status"], "info")
        self.assertNotEqual(process_row["status"], "ok")


    def test_code_analyzer_installed_reports_ok(self):
        # Physically installed → `sf plugins inspect` returns a real version.
        inspect_out = json.dumps([{"name": "@salesforce/plugin-code-analyzer", "version": "5.11.1"}])

        def fake_run(argv, **_):
            if "inspect" in argv:
                return inspect_out
            return ""

        with mock.patch.object(sfx, "run", side_effect=fake_run):
            result = sfx._check_code_analyzer()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["version"], "5.11.1")
        self.assertEqual(result["message"], "Installed")

    def test_code_analyzer_jit_registered_reports_ok_not_critical(self):
        # NOT physically installed → `inspect` fails (JIT plugins yield {"error": {}}
        # and exit 1, so run() returns ""). But the CLI registers it as a JIT plugin,
        # so it auto-installs on first use — this is AVAILABLE, never critical.
        plugins_out = json.dumps([
            {"name": "@salesforce/plugin-org", "version": "3.0.0"},
            {
                "name": "@salesforce/cli",
                "options": {"isRoot": True},
                "pjson": {"oclif": {"jitPlugins": {"@salesforce/plugin-code-analyzer": "5.11.1"}}},
            },
        ])

        def fake_run(argv, **_):
            if "inspect" in argv:
                return ""  # JIT plugin not yet installed
            if "--json" in argv:
                return plugins_out
            return ""

        with mock.patch.object(sfx, "run", side_effect=fake_run):
            result = sfx._check_code_analyzer()
        self.assertEqual(result["status"], "ok")
        self.assertNotEqual(result["status"], "critical")
        self.assertEqual(result["version"], "5.11.1")
        self.assertIn("JIT", result["message"])

    def test_code_analyzer_genuinely_absent_reports_critical(self):
        # inspect fails AND the plugin is not in the CLI's jitPlugins registry →
        # genuinely missing, so report critical with the install hint.
        plugins_out = json.dumps([
            {"name": "@salesforce/cli", "options": {"isRoot": True},
             "pjson": {"oclif": {"jitPlugins": {"@salesforce/plugin-signups": "2.0.0"}}}},
        ])

        def fake_run(argv, **_):
            if "inspect" in argv:
                return ""
            if "--json" in argv:
                return plugins_out
            return ""

        with mock.patch.object(sfx, "run", side_effect=fake_run):
            result = sfx._check_code_analyzer()
        self.assertEqual(result["status"], "critical")
        self.assertIsNone(result["version"])
        self.assertIn("plugins install", result["message"])

    def test_check_tools_attaches_diagnostic_on_failure(self):
        # All native tools missing → several critical rows → a diagnostic block is
        # attached so the failure is understandable (and not flipped green).
        with mock.patch.object(sfx, "resolve_executable", return_value=None), \
                mock.patch.object(sfx, "get_target_org", return_value=""):
            buf = io.StringIO()
            with redirect_stdout(buf):
                sfx.cmd_check_tools()
            report = json.loads(buf.getvalue())

        self.assertIn("tools", report)
        self.assertTrue(any(t["status"] == "critical" for t in report["tools"]))
        self.assertIn("diagnostic", report)
        diag = report["diagnostic"]
        for key in ("platform", "shell", "cwd", "pluginRoot", "resolvedExecutables"):
            self.assertIn(key, diag)


class McpHealthContractTests(unittest.TestCase):
    """WIN-033 (passive sidecar read) + WIN-040 (active --probe) — see
    CONTRACT-mcp-health.md. The consumer owns the server-key -> slug-arg
    mapping; sidecar filename AND --probe arg both use the SLUG ARG
    ("metadata-experts"), never the .mcp.json server key
    ("salesforce-metadata-experts")."""

    def test_slug_mapping_uses_slug_arg_not_server_key(self):
        self.assertEqual(sfx._MCP_SERVER_SLUGS["salesforce-api-context"], "salesforce-api-context")
        self.assertEqual(sfx._MCP_SERVER_SLUGS["salesforce-metadata-experts"], "metadata-experts")
        self.assertNotIn("salesforce-metadata-experts", sfx._MCP_SERVER_SLUGS.values())

    def test_state_table_matches_contract(self):
        self.assertEqual(sfx._render_mcp_state_row("s", "ok")["status"], "ok")
        self.assertEqual(sfx._render_mcp_state_row("s", "inactive")["status"], "critical")
        self.assertEqual(sfx._render_mcp_state_row("s", "auth")["status"], "warn")
        self.assertEqual(sfx._render_mcp_state_row("s", "env-not-ready")["status"], "warn")
        self.assertEqual(sfx._render_mcp_state_row("s", "unreachable")["status"], "warn")

    def test_unknown_state_renders_neutral_warn_not_crash(self):
        row = sfx._render_mcp_state_row("metadata-experts", "some-future-state")
        self.assertEqual(row["status"], "warn")
        self.assertIn("Unrecognized", row["message"])

    def test_missing_state_renders_neutral_warn_not_crash(self):
        row = sfx._render_mcp_state_row("metadata-experts", None)
        self.assertEqual(row["status"], "warn")

    def test_passive_row_absent_sidecar_is_neutral_not_invented(self):
        with mock.patch.object(sfx, "_read_health_sidecar", return_value=None):
            row = sfx._passive_mcp_row("metadata-experts")
        self.assertEqual(row["status"], "info")
        self.assertIn("not yet observed", row["message"].lower())

    def test_passive_row_present_sidecar_renders_from_state(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                return_value={"slug": "metadata-experts", "state": "inactive",
                                               "detail": "HTTP 404 Server definition not found"}):
            row = sfx._passive_mcp_row("metadata-experts")
        self.assertEqual(row["status"], "critical")
        self.assertIn("not activated", row["message"])

    def test_read_health_sidecar_reads_slug_named_file(self):
        # The sidecar path MUST be keyed by the slug arg, not the server key.
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(Path, "read_text", return_value=json.dumps({"state": "ok"})) as read_text:
            data = sfx._read_health_sidecar("metadata-experts")
        self.assertEqual(data, {"state": "ok"})
        # read_text was called on a Path ending in metadata-experts.json.
        self.assertTrue(read_text.call_count >= 1)

    def test_read_health_sidecar_bad_json_returns_none_not_crash(self):
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(Path, "read_text", return_value="{not valid json"):
            self.assertIsNone(sfx._read_health_sidecar("metadata-experts"))

    def test_read_health_sidecar_missing_file_returns_none(self):
        with mock.patch.object(Path, "exists", return_value=False):
            self.assertIsNone(sfx._read_health_sidecar("metadata-experts"))

    def test_probe_server_parses_json_line_from_stdout(self):
        probe_json = json.dumps({"slug": "metadata-experts", "state": "auth",
                                  "detail": "401", "httpStatus": 401, "org": "my-alias"})
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(sfx, "run_result",
                                  return_value=sfx.RunResult(True, probe_json, 0, "")):
            row = sfx._probe_server("metadata-experts")
        self.assertEqual(row["status"], "warn")
        self.assertEqual(row["name"], "Salesforce MCP (metadata-experts)")

    def test_probe_server_uses_slug_arg_in_shell_out(self):
        captured = {}

        def fake_run_result(cmd, timeout=None):
            captured["cmd"] = cmd
            return sfx.RunResult(True, json.dumps({"state": "ok"}), 0, "")

        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(sfx, "run_result", side_effect=fake_run_result):
            sfx._probe_server("metadata-experts")
        self.assertIn("--probe", captured["cmd"])
        self.assertEqual(captured["cmd"][-1], "metadata-experts")
        self.assertNotIn("salesforce-metadata-experts", captured["cmd"])

    def test_probe_server_nonzero_exit_renders_warn_not_crash(self):
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(sfx, "run_result",
                                  return_value=sfx.RunResult(False, "", 1, "nonzero")):
            row = sfx._probe_server("metadata-experts")
        self.assertEqual(row["status"], "warn")

    def test_probe_server_unparseable_stdout_renders_warn_not_crash(self):
        with mock.patch.object(Path, "exists", return_value=True), \
                mock.patch.object(sfx, "run_result",
                                  return_value=sfx.RunResult(True, "not json", 0, "")):
            row = sfx._probe_server("metadata-experts")
        self.assertEqual(row["status"], "warn")

    def test_probe_server_missing_proxy_bundle_renders_warn_not_crash(self):
        with mock.patch.object(Path, "exists", return_value=False):
            row = sfx._probe_server("metadata-experts")
        self.assertEqual(row["status"], "warn")

    # --- _passive_mcp_summary (WIN-033 /status banner) -------------------
    # The banner summary is network-free (reads only the sidecars) and MUST
    # surface the worst observed state so an inactive server is never hidden
    # behind a healthy one.

    def _fake_sidecars(self, by_slug, org=None):
        """Return a _read_health_sidecar stand-in keyed by slug arg. A value may
        be a bare state string, or a (state, org) tuple to model the sidecar's
        `org` field; `org=` sets a default org for bare-string entries."""
        def _reader(slug):
            entry = by_slug.get(slug)
            if entry is None:
                return None
            if isinstance(entry, tuple):
                state, entry_org = entry
            else:
                state, entry_org = entry, org
            return {"slug": slug, "state": state, "org": entry_org}
        return _reader

    def test_summary_all_ok_reports_both_active(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"})):
            summary = sfx._passive_mcp_summary()
        self.assertIn("active", summary.lower())
        self.assertNotIn("not activated", summary.lower())

    def test_summary_inactive_surfaces_not_activated_even_if_other_ok(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "inactive"})):
            summary = sfx._passive_mcp_summary()
        self.assertIn("NOT activated", summary)
        self.assertIn("metadata-experts", summary)

    def test_summary_no_sidecars_is_not_yet_observed_not_invented(self):
        with mock.patch.object(sfx, "_read_health_sidecar", return_value=None):
            summary = sfx._passive_mcp_summary()
        self.assertIn("not yet observed", summary.lower())

    def test_summary_mixed_degraded_points_at_check_tools(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "auth"})):
            summary = sfx._passive_mcp_summary()
        self.assertIn("degraded", summary.lower())
        self.assertIn("check-tools", summary.lower())

    # --- partial observation is PENDING, not an outage (review P1 #1) ---------
    # One server ok, the other not yet observed (no sidecar), none bad: this is
    # still connecting, so the summary must read as pending ("not yet observed"),
    # never "degraded" — otherwise _mcp_indicator paints a false ✗ unavailable.
    def test_summary_partial_ok_and_unobserved_is_pending_not_degraded(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok"})):  # metadata-experts absent
            summary = sfx._passive_mcp_summary()
        self.assertIn("not yet observed", summary.lower())
        self.assertNotIn("degraded", summary.lower())
        self.assertNotIn("active", summary.lower())  # not a full-green claim either
        # And the banner icon derives to connecting, not unavailable.
        icon, style = sfx._mcp_indicator(summary)
        self.assertIn("connecting", icon)
        self.assertNotIn("unavailable", icon)

    # --- org-scoped observations (review P1 #2) -------------------------------
    # A sidecar written against a DIFFERENT org must not be shown as healthy for
    # the org the user is currently on.
    def test_summary_ignores_sidecar_from_a_different_org(self):
        # Both servers ok, but recorded against "orgA"; active org is "orgB".
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"}, org="orgA")):
            summary = sfx._passive_mcp_summary(active_org="orgB")
        # No usable observation for orgB -> neutral not-yet-observed, NOT active.
        self.assertIn("not yet observed", summary.lower())
        self.assertNotIn("active", summary.lower())

    def test_summary_accepts_sidecar_matching_active_org(self):
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"}, org="orgA")):
            summary = sfx._passive_mcp_summary(active_org="orgA")
        self.assertIn("active", summary.lower())

    def test_summary_no_active_org_does_not_filter(self):
        # When the active org is unknown, fall back to state-only (no over-filter).
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"}, org="orgA")):
            summary = sfx._passive_mcp_summary()  # no active_org
        self.assertIn("active", summary.lower())

    def test_summary_accepts_sidecar_by_username_when_resolved_by_alias(self):
        # review P2 #2: the producer stamps the configured USERNAME while the
        # consumer resolves the SAME org by ALIAS. Passing both identifiers must
        # accept the username-stamped sidecar (not reject it as a foreign org).
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"},
                                    org="user@example.com")):
            summary = sfx._passive_mcp_summary(
                active_org=("myAlias", "user@example.com"))
        self.assertIn("active", summary.lower())
        self.assertNotIn("not yet observed", summary.lower())

    def test_summary_still_rejects_truly_foreign_org_with_both_ids(self):
        # The alias/username tolerance must not defeat the org filter: a sidecar
        # from a genuinely different org is still rejected when neither the alias
        # nor the username matches.
        with mock.patch.object(sfx, "_read_health_sidecar",
                                side_effect=self._fake_sidecars(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"}, org="otherOrg")):
            summary = sfx._passive_mcp_summary(
                active_org=("myAlias", "user@example.com"))
        self.assertIn("not yet observed", summary.lower())
        self.assertNotIn("active", summary.lower())

    # --- _live_mcp_summary (WIN-040 live-probe banner) ------------------------
    # The live summary actively probes each server so the banner reflects REAL
    # current reachability. A fresh probe is authoritative for this session's org
    # and OVERRIDES a stale sidecar (the activate-then-still-inactive demo gap);
    # a probe that cannot run falls back to that server's last-known sidecar.

    def _fake_probes(self, by_slug):
        """Return a _probe_server_raw stand-in keyed by slug arg. A value may be a
        bare state string (-> {slug, state, org}) or None (probe could not run)."""
        def _probe(slug, timeout=None):
            state = by_slug.get(slug)
            if state is None:
                return None
            return {"slug": slug, "state": state, "org": "liveOrg"}
        return _probe

    def test_live_summary_probe_overrides_stale_inactive_sidecar(self):
        # Sidecars say inactive (stale); live probe says ok -> summary is active.
        with mock.patch.object(sfx, "_probe_server_raw",
                                side_effect=self._fake_probes(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "ok"})), \
                mock.patch.object(sfx, "_read_health_sidecar",
                                  side_effect=self._fake_sidecars(
                                      {"salesforce-api-context": "inactive",
                                       "metadata-experts": "inactive"})):
            summary = sfx._live_mcp_summary(active_org="liveOrg")
        self.assertIn("active", summary.lower())
        self.assertNotIn("not activated", summary.lower())

    def test_live_summary_probe_surfaces_inactive_over_stale_ok(self):
        # The reverse: sidecar says ok (stale), live probe says inactive.
        with mock.patch.object(sfx, "_probe_server_raw",
                                side_effect=self._fake_probes(
                                    {"salesforce-api-context": "ok",
                                     "metadata-experts": "inactive"})), \
                mock.patch.object(sfx, "_read_health_sidecar",
                                  side_effect=self._fake_sidecars(
                                      {"salesforce-api-context": "ok",
                                       "metadata-experts": "ok"})):
            summary = sfx._live_mcp_summary(active_org="liveOrg")
        self.assertIn("NOT activated", summary)
        self.assertIn("metadata-experts", summary)

    def test_live_summary_falls_back_to_sidecar_when_probe_cannot_run(self):
        # Both probes fail to run (None); the last-known org-filtered sidecars are
        # used so a transient/offline failure degrades to the cached reading.
        with mock.patch.object(sfx, "_probe_server_raw",
                                side_effect=self._fake_probes({})), \
                mock.patch.object(sfx, "_read_health_sidecar",
                                  side_effect=self._fake_sidecars(
                                      {"salesforce-api-context": "ok",
                                       "metadata-experts": "ok"}, org="cachedOrg")):
            summary = sfx._live_mcp_summary(active_org="cachedOrg")
        self.assertIn("active", summary.lower())

    def test_live_summary_probe_failure_plus_foreign_sidecar_is_pending(self):
        # Probe can't run AND the only sidecar is from another org -> no usable
        # observation -> neutral not-yet-observed, never a false green.
        with mock.patch.object(sfx, "_probe_server_raw",
                                side_effect=self._fake_probes({})), \
                mock.patch.object(sfx, "_read_health_sidecar",
                                  side_effect=self._fake_sidecars(
                                      {"salesforce-api-context": "ok",
                                       "metadata-experts": "ok"}, org="otherOrg")):
            summary = sfx._live_mcp_summary(active_org="thisOrg")
        self.assertIn("not yet observed", summary.lower())
        self.assertNotIn("active", summary.lower())

    # --- partial: one tracked server healthy, one down (user-requested glyph) --
    # A half-working feature is neither a full outage nor healthy: the summary
    # reads "partial", names the down server, and the banner glyph is ⚠ partial —
    # distinct from both ✓ connected (all ok) and ✗ unavailable (all down).
    def test_summary_one_ok_one_inactive_is_partial(self):
        summary = sfx._summarize_mcp_states(
            {"salesforce-api-context": "ok", "metadata-experts": "inactive"})
        self.assertIn("partial", summary.lower())
        self.assertIn("metadata-experts", summary)  # names the down server
        icon, style = sfx._mcp_indicator(summary)
        self.assertIn("partial", icon)
        self.assertNotIn("connected", icon)      # not a false green
        self.assertNotIn("unavailable", icon)    # not a full outage either

    def test_summary_one_ok_one_auth_is_partial(self):
        summary = sfx._summarize_mcp_states(
            {"salesforce-api-context": "ok", "metadata-experts": "auth"})
        self.assertIn("partial", summary.lower())
        self.assertIn("partial", sfx._mcp_indicator(summary)[0])

    def test_summary_both_inactive_is_full_unavailable_not_partial(self):
        summary = sfx._summarize_mcp_states(
            {"salesforce-api-context": "inactive", "metadata-experts": "inactive"})
        self.assertNotIn("partial", summary.lower())
        self.assertIn("unavailable", sfx._mcp_indicator(summary)[0])

    def test_partial_summary_icon_precedence_over_active_substring(self):
        # The partial summary contains the word "active" ("others active"); the
        # indicator MUST test "partial" first so it never paints a false ✓.
        summary = ("sf-mcp-proxy: partial — metadata-experts NOT activated in this "
                   "org (others active) — enable in Setup (check-tools for detail)")
        icon, _ = sfx._mcp_indicator(summary)
        self.assertIn("partial", icon)
        self.assertNotIn("connected", icon)

    def test_live_summary_mixes_live_probe_with_sidecar_fallback(self):
        # One server probes live (ok); the other's probe fails but its sidecar is
        # a fresh inactive -> the inactive must still surface (worst-of).
        def _one_probe(slug, timeout=None):
            if slug == "salesforce-api-context":
                return {"slug": slug, "state": "ok", "org": "liveOrg"}
            return None  # metadata-experts probe could not run
        with mock.patch.object(sfx, "_probe_server_raw", side_effect=_one_probe), \
                mock.patch.object(sfx, "_read_health_sidecar",
                                  side_effect=self._fake_sidecars(
                                      {"metadata-experts": "inactive"}, org="liveOrg")):
            summary = sfx._live_mcp_summary(active_org="liveOrg")
        self.assertIn("NOT activated", summary)
        self.assertIn("metadata-experts", summary)

    # --- banner icon derivation (WIN-033 /status org-box "MCP" field) -----
    # render_banner_message() derives the compact ✓/⟳/✗ icon from the health
    # summary string. It MUST understand the _passive_mcp_summary() vocabulary,
    # not only the legacy "connected/connecting/bridged" strings — otherwise a
    # healthy "... active" summary falls through to "✗ unavailable" and the icon
    # contradicts the Note (regression caught in live dry-run against DEorgFRI).

    def _banner_for(self, summary):
        org = {"alias": "x", "edition": "e", "apiVersion": "62.0",
               "instanceUrl": "u", "username": "n"}
        proj = {"name": "P", "source_api": "62.0", "package_dirs": "force-app"}
        stats = {k: 0 for k in ("apex_src", "apex_test", "triggers", "lwc",
                                 "aura", "objects", "permsets", "flows")}
        return sfx.render_banner_message(org, proj, stats, "", summary)

    def test_banner_icon_active_summary_is_connected_no_note(self):
        out = self._banner_for("sf-mcp-proxy: api-context, metadata-experts active")
        self.assertIn("✓ connected", out)
        self.assertNotIn("✗ unavailable", out)
        self.assertNotIn("Note:", out)

    def test_banner_icon_inactive_summary_is_unavailable(self):
        summary = ("sf-mcp-proxy: metadata-experts NOT activated in this org — "
                   "enable in Setup (check-tools for detail)")
        out = self._banner_for(summary)
        # "active" is a substring of "NOT activated" — the icon must NOT be fooled.
        self.assertIn("✗ unavailable", out)
        self.assertNotIn("✓ connected", out)
        # The environment band shows only the tri-state icon; per-server detail
        # lives in check-tools (WIN-040), so there is no verbose Note line here.

    def test_banner_icon_not_yet_observed_is_connecting_no_note(self):
        out = self._banner_for("sf-mcp-proxy: not yet observed — run check-tools to probe")
        self.assertIn("⟳ connecting", out)
        self.assertNotIn("Note:", out)

    def test_banner_icon_degraded_summary_is_unavailable(self):
        out = self._banner_for("sf-mcp-proxy: degraded — run check-tools for per-server detail")
        self.assertIn("✗ unavailable", out)

    # --- MCP names line is scoped to the servers the glyph covers -------------
    # The names shown next to the single ✓/✗ glyph must be ONLY the health-tracked
    # platform servers. salesforce-lsp is a local stdio process the glyph never
    # reflects, so listing it beside the glyph misleads the viewer.
    def test_mcp_server_names_excludes_local_lsp(self):
        mcp_json = json.dumps({"mcpServers": {
            "salesforce-api-context": {},
            "salesforce-lsp": {},
            "salesforce-metadata-experts": {},
        }})
        with mock.patch.object(Path, "read_text", return_value=mcp_json):
            names = sfx._mcp_server_names(Path("/plugin"))
        self.assertIn("api-context", names)
        self.assertIn("metadata-experts", names)
        self.assertNotIn("lsp", names)

    def test_mcp_server_names_read_error_yields_empty(self):
        with mock.patch.object(Path, "read_text", side_effect=OSError("boom")):
            self.assertEqual(sfx._mcp_server_names(Path("/plugin")), [])

    # --- cmd_status must not probe an unreachable org -------------------------
    # The live probe runs on an executor thread that cannot be cancelled, so
    # cmd_status resolves the org FIRST and only probes when it is reachable.
    # Probing before the unreachable-org early return would leave a live thread
    # that concurrent.futures joins at interpreter exit, hanging /status until the
    # probe subprocesses time out (Prizm P2 on 94bab3b).
    def test_cmd_status_unreachable_org_does_not_probe(self):
        with mock.patch.object(sfx.Path, "exists", return_value=True), \
                mock.patch.object(sfx, "resolve_executable", return_value="/usr/bin/sf"), \
                mock.patch.object(sfx, "get_target_org_detailed",
                                  return_value=("deadOrg", "")), \
                mock.patch.object(sfx, "resolve_org_info", return_value=None), \
                mock.patch.object(sfx, "_live_mcp_summary",
                                  side_effect=AssertionError(
                                      "must not probe an unreachable org")) as probe, \
                mock.patch("builtins.print"):
            rc = sfx.cmd_status()
        self.assertEqual(rc, 0)
        probe.assert_not_called()


class DiagnosticTests(unittest.TestCase):
    def test_diagnostic_shape(self):
        ctx = sfx.diagnostic_context(["sf", "npm"])
        self.assertEqual(ctx["platform"], sfx.sys.platform)
        self.assertIn("sf", ctx["resolvedExecutables"])
        self.assertIn("npm", ctx["resolvedExecutables"])

    def test_diagnostic_is_secret_free(self):
        # The diagnostic must never carry tokens/secrets — only environment shape
        # and resolved executable paths.
        ctx = sfx.diagnostic_context()
        blob = json.dumps(ctx).lower()
        for forbidden in ("token", "jwt", "secret", "password", "authorization", "bearer"):
            self.assertNotIn(forbidden, blob)

    def test_render_diagnostic_lines_is_text(self):
        text = sfx.render_diagnostic_lines(sfx.diagnostic_context(["sf"]))
        self.assertIn("platform:", text)
        self.assertIn("resolved executables:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
