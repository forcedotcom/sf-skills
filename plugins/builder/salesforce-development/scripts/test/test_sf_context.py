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
import os
import stat
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
    def setUp(self):
        # cmd_check_tools now writes a readiness verdict to ./.sf/ as a side effect,
        # so isolate the cwd in a temp dir — otherwise the run litters the invoker's
        # directory. The direct `_check_*` unit tests don't touch cwd, so this is
        # harmless for them.
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    def _mock_all_checks(self, git=None, cli=None):
        """Patch every _check_* to a green row (info for the MCP process row) so a
        cmd_check_tools run is deterministic and offline. `git`/`cli` override those
        rows for the not-ready cases."""
        ok = lambda name: {"name": name, "status": "ok", "version": "x", "message": "Installed"}
        return [
            mock.patch.object(sfx, "_check_sf_cli", return_value=cli or ok("Salesforce CLI")),
            mock.patch.object(sfx, "_check_code_analyzer", return_value=ok("Code Analyzer plugin")),
            mock.patch.object(sfx, "_check_node", return_value=ok("Node.js")),
            mock.patch.object(sfx, "_check_npm", return_value=ok("NPM")),
            mock.patch.object(sfx, "_check_git", return_value=git or ok("Git")),
            mock.patch.object(sfx, "_check_source_tracking", return_value=ok("Source Tracking")),
            mock.patch.object(sfx, "_check_mcp", return_value=[
                {"name": "Salesforce MCP (config)", "status": "ok"},
                {"name": "Salesforce MCP (process)", "status": "info"},
            ]),
            mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/tool"),
        ]

    def _run_check_tools(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            sfx.cmd_check_tools()
        return json.loads(buf.getvalue())

    def _read_verdict(self):
        return json.loads((Path(".sf") / "environment-readiness.json").read_text())

    def _read_report(self):
        return json.loads((Path(".sf") / "environment-readiness-report.json").read_text())

    def _run_readiness_banner(self):
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            code = sfx.cmd_readiness_banner()
        return code, buf.getvalue(), err.getvalue()

    def test_readiness_banner_prints_the_deterministic_render_from_the_persisted_report(self):
        # The platform-environment-validate paint fallback: after a check-tools scan
        # persists the report, `readiness-banner` prints exactly render_readiness_text
        # from that same report — so the skill never hand-renders the banner from JSON.
        patches = self._mock_all_checks()
        for p in patches:
            p.start()
        try:
            self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        code, out, err = self._run_readiness_banner()
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(out, sfx.render_readiness_text(self._read_report(), color=False) + "\n")
        self.assertIn("Ready to build on Salesforce?", out)

    def test_readiness_banner_fails_open_with_a_pointer_when_no_report_exists(self):
        # No check-tools run in this cwd → no persisted report. The command stays
        # fail-open: nothing on stdout, a one-line pointer to check-tools on stderr,
        # exit 2. The check-tools JSON, not this banner, is the authoritative result.
        code, out, err = self._run_readiness_banner()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("check-tools", err)

    def test_check_tools_writes_ready_verdict_when_all_green(self):
        # No critical and no warn rows (the MCP process row is info, which does NOT
        # count) → readiness is a pass, with a toolchain signature and timestamp.
        patches = self._mock_all_checks()
        for p in patches:
            p.start()
        try:
            report = self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        self.assertNotIn("diagnostic", report)  # nothing critical
        verdict = self._read_verdict()
        self.assertTrue(verdict["ready"])
        self.assertEqual(verdict["needsAttention"], [])
        self.assertIn("signature", verdict)
        self.assertIn("checkedAt", verdict)

    def test_check_tools_writes_not_ready_when_a_tool_is_critical(self):
        git_missing = {"name": "Git", "status": "critical", "version": None, "message": "Not found"}
        patches = self._mock_all_checks(git=git_missing)
        for p in patches:
            p.start()
        try:
            self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        verdict = self._read_verdict()
        self.assertFalse(verdict["ready"])
        self.assertIn("Git", verdict["needsAttention"])

    def test_check_tools_warn_row_is_ready_but_flagged(self):
        # A 🟡 warn (a non-LTS Node, an outdated-but-working CLI) is ADVISORY, not a
        # blocker: it is surfaced in needsAttention for the banner, but readiness
        # stays True and blockers is empty, so the scaffold gate never blocks on it.
        cli_outdated = {"name": "Salesforce CLI", "status": "warn", "version": "2.1",
                        "message": "Version 2.1 is outdated"}
        patches = self._mock_all_checks(cli=cli_outdated)
        for p in patches:
            p.start()
        try:
            self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        verdict = self._read_verdict()
        self.assertTrue(verdict["ready"])                          # warn alone never blocks
        self.assertEqual(verdict["blockers"], [])                  # nothing critical
        self.assertIn("Salesforce CLI", verdict["needsAttention"])  # still surfaced

    def test_check_tools_blockers_are_critical_only_not_warnings(self):
        # When a critical AND a warn coexist, ready is False (the critical blocks)
        # but `blockers` names ONLY the critical — the warn stays advisory in
        # needsAttention so the scaffold-gate block never misattributes it.
        git_missing = {"name": "Git", "status": "critical", "version": None, "message": "Not found"}
        cli_warn = {"name": "Salesforce CLI", "status": "warn", "version": "2.1",
                    "message": "Version 2.1 is outdated"}
        patches = self._mock_all_checks(git=git_missing, cli=cli_warn)
        for p in patches:
            p.start()
        try:
            self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        verdict = self._read_verdict()
        self.assertFalse(verdict["ready"])
        self.assertEqual(verdict["blockers"], ["Git"])              # critical only
        self.assertIn("Git", verdict["needsAttention"])
        self.assertIn("Salesforce CLI", verdict["needsAttention"])  # warn surfaced, not a blocker

    def test_check_tools_persists_the_full_report_for_the_paint_hook(self):
        # The readiness-paint PostToolUse hook renders the banner from this file — a
        # PostToolUse payload carries only the executed command, never the scan's
        # stdout, so the report must be persisted for the hook to read back. It is
        # the same object the scan prints to stdout.
        patches = self._mock_all_checks()
        for p in patches:
            p.start()
        try:
            report = self._run_check_tools()
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(self._read_report(), report)
        self.assertIn("tools", self._read_report())

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


class ReadinessStateTests(unittest.TestCase):
    """The cached readiness verdict mirrors the CLI-update state: cwd-relative
    .sf/ JSON, fail-open read, signature-gated freshness. The load-bearing rule is
    the honesty invariant — an absent or corrupt verdict, or a not-ready one, is
    NEVER treated as a pass."""

    def setUp(self):
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    def _readiness_files(self):
        directory = Path(".sf")
        return sorted(path.name for path in directory.iterdir()) if directory.exists() else []

    def test_record_and_load_roundtrip(self):
        self.assertTrue(sfx._record_readiness_verdict(True, [], "sig-1"))
        state = sfx._load_readiness_state()
        self.assertTrue(state["ready"])
        self.assertEqual(state["signature"], "sig-1")
        self.assertEqual(state["needsAttention"], [])
        self.assertIn("checkedAt", state)
        self.assertEqual(self._readiness_files(), ["environment-readiness.json"])

    def test_blockers_default_to_needs_attention_when_omitted(self):
        # Back-compat: a caller that doesn't distinguish severities (no blockers arg)
        # gets blockers == needsAttention, so the gate still names those.
        sfx._record_readiness_verdict(False, ["Git"], "sig-1")
        self.assertEqual(sfx._load_readiness_state()["blockers"], ["Git"])

    def test_blockers_recorded_distinct_from_needs_attention(self):
        # A warn-only verdict: not-green (needsAttention) yet no blockers, so ready
        # can honestly be True — this is the shape a warn-only scan writes.
        sfx._record_readiness_verdict(True, ["Node.js"], "sig-1", blockers=[])
        state = sfx._load_readiness_state()
        self.assertTrue(state["ready"])
        self.assertEqual(state["needsAttention"], ["Node.js"])
        self.assertEqual(state["blockers"], [])

    def test_is_fresh_requires_a_pass_and_matching_signature(self):
        sfx._record_readiness_verdict(True, [], "sig-1")
        self.assertTrue(sfx._readiness_is_fresh("sig-1"))
        # Toolchain changed since the scan → the cached green no longer applies.
        self.assertFalse(sfx._readiness_is_fresh("sig-2"))

    def test_not_ready_verdict_is_never_fresh(self):
        sfx._record_readiness_verdict(False, ["Git"], "sig-1")
        self.assertFalse(sfx._readiness_is_fresh("sig-1"))

    def test_absent_verdict_reads_empty_and_is_never_a_pass(self):
        # No file written yet → unchecked → honest {} → never fresh (never green).
        self.assertEqual(sfx._load_readiness_state(), {})
        self.assertFalse(sfx._readiness_is_fresh("anything"))

    def test_corrupt_verdict_reads_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        (Path(".sf") / "environment-readiness.json").write_text("{ not json")
        self.assertEqual(sfx._load_readiness_state(), {})
        self.assertFalse(sfx._readiness_is_fresh("anything"))

    def test_oversized_verdict_reads_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        padding = "x" * sfx._READINESS_JSON_MAX_BYTES
        (Path(".sf") / "environment-readiness.json").write_text(
            json.dumps({"ready": True, "signature": "sig-1", "padding": padding})
        )
        self.assertEqual(sfx._load_readiness_state(), {})
        self.assertFalse(sfx._readiness_is_fresh("sig-1"))

    def test_unreadable_verdict_reads_empty(self):
        with mock.patch.object(sfx.os, "open", side_effect=OSError("unreadable")) as opened:
            self.assertEqual(sfx._load_readiness_state(), {})
        opened.assert_called_once()

    def test_reader_rejects_fifo_mode_without_reading_and_uses_safe_flags(self):
        binary_flag = 1 << 29
        fifo_stat = type("FifoStat", (), {"st_mode": stat.S_IFIFO, "st_size": 0})()
        with mock.patch.object(sfx.os, "O_BINARY", binary_flag, create=True), \
                mock.patch.object(sfx.os, "open", return_value=71) as opened, \
                mock.patch.object(sfx.os, "fstat", return_value=fifo_stat), \
                mock.patch.object(sfx.os, "read") as read, \
                mock.patch.object(sfx.os, "close") as close:
            self.assertEqual(sfx._load_bounded_small_json(Path("readiness-fifo")), {})
            flags = opened.call_args.args[1]
            for name in ("O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "O_BINARY"):
                flag = getattr(sfx.os, name, 0)
                if flag:
                    self.assertTrue(flags & flag, name)
            read.assert_not_called()
            close.assert_called_once_with(71)

    def test_reader_does_not_follow_symlink_when_no_follow_is_supported(self):
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "symlink"):
            self.skipTest("no-follow symlink opens are not supported")
        target = Path("readiness-target.json")
        target.write_text(json.dumps({"ready": True}))
        link = Path("readiness-link.json")
        try:
            link.symlink_to(target.name)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        self.assertEqual(sfx._load_bounded_small_json(link), {})
        self.assertEqual(json.loads(target.read_text()), {"ready": True})

    def test_symlinked_readiness_parent_fails_open_and_writes_fail_silent(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are not supported")
        outside = Path(self._tmp.name).parent / f"{Path(self._tmp.name).name}-outside-sf"
        outside.mkdir()
        target = outside / "environment-readiness-report.json"
        original = json.dumps({"tools": [{"name": "outside"}]}).encode()
        target.write_bytes(original)
        try:
            Path(".sf").symlink_to(outside, target_is_directory=True)
        except OSError as error:
            target.unlink()
            outside.rmdir()
            self.skipTest(f"directory symlink creation is unavailable: {error}")
        try:
            self.assertEqual(sfx._load_readiness_report(), {})
            self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "inside"}]}))
            # Simulate Python's native-Windows no-dir-fd path: identity and reparse
            # checks must reject the same hostile parent without touching its target.
            with mock.patch.object(sfx, "_PHASE_DIR_FD_SUPPORTED", False):
                self.assertEqual(sfx._load_readiness_report(), {})
                self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "fallback"}]}))
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(sorted(path.name for path in outside.iterdir()), [target.name])
        finally:
            Path(".sf").unlink()
            target.unlink()
            outside.rmdir()

    def test_valid_non_object_json_roots_read_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        path = Path(".sf") / "environment-readiness.json"
        for value in ([{"ready": True}], "ready", 1, True, None):
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                self.assertEqual(sfx._load_readiness_state(), {})

    def test_deeply_nested_json_recursion_reads_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        path = Path(".sf") / "environment-readiness.json"
        path.write_text("[" * 10000 + "{}" + "]" * 10000)
        self.assertEqual(sfx._load_readiness_state(), {})

    def test_report_record_and_load_roundtrip(self):
        # The FULL report is persisted next to the coarse verdict so the readiness-
        # paint hook can render the banner from it (the hook payload carries only the
        # command, never the scan's stdout). Same cwd-relative .sf/, fail-open read.
        report = {"tools": [{"name": "Git", "status": "ok", "version": "git version 2.50.1"}]}
        self.assertTrue(sfx._record_readiness_report(report))
        self.assertEqual(sfx._load_readiness_report(), report)
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_atomic_replace_exposes_only_complete_old_or_new_report(self):
        old = {"tools": [{"name": "Git", "status": "warn", "message": "old"}]}
        new = {"tools": [{"name": "Git", "status": "ok", "message": "new"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        path = Path(".sf") / "environment-readiness-report.json"
        prior = path.read_bytes()
        real_replace = os.replace
        observations = []

        def observe_replace(source, destination, **kwargs):
            source_path = path.parent / source if kwargs.get("src_dir_fd") is not None else Path(source)
            observations.append((path.read_bytes(), source_path.read_bytes()))
            real_replace(source, destination, **kwargs)

        with mock.patch.object(sfx.os, "replace", side_effect=observe_replace):
            self.assertTrue(sfx._record_readiness_report(new))

        self.assertEqual(observations[0][0], prior)
        self.assertEqual(json.loads(observations[0][1]), new)
        self.assertEqual(sfx._load_readiness_report(), new)
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_readiness_temp_is_exclusive_owner_only_and_cleaned_after_success(self):
        report = {"tools": [{"name": "Git", "status": "ok"}]}
        real_open = os.open
        real_replace = os.replace
        temp_modes = []

        def observe_replace(source, destination, **kwargs):
            stat_kwargs = ({"dir_fd": kwargs["src_dir_fd"]}
                           if kwargs.get("src_dir_fd") is not None else {})
            temp_modes.append(os.stat(source, **stat_kwargs).st_mode & 0o777)
            real_replace(source, destination, **kwargs)

        with mock.patch.object(sfx.os, "open", wraps=real_open) as opened, \
                mock.patch.object(sfx.os, "replace", side_effect=observe_replace):
            self.assertTrue(sfx._record_readiness_report(report))

        temp_open = next(
            call for call in opened.call_args_list
            if Path(call.args[0]).name.startswith(".environment-readiness-report.json.")
        )
        self.assertTrue(temp_open.args[1] & os.O_EXCL)
        self.assertEqual(temp_open.args[2], 0o600)
        self.assertEqual(temp_modes, [0o600])
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_writer_uses_binary_flag_when_available(self):
        binary_flag = 1 << 29
        directory = types.SimpleNamespace(fd=None)
        with mock.patch.object(sfx.os, "O_BINARY", binary_flag, create=True), \
                mock.patch.object(sfx, "_open_phase_directory", return_value=directory), \
                mock.patch.object(
                    sfx, "_open_phase_child", side_effect=OSError("stop")
                ) as opened:
            self.assertFalse(sfx._record_readiness_report({"tools": []}))

        self.assertTrue(opened.call_args.args[2] & binary_flag)

    def test_temp_file_collision_is_preserved_and_destination_unchanged(self):
        old = {"tools": [{"name": "Git", "status": "warn", "message": "old"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        destination = Path(".sf") / "environment-readiness-report.json"
        prior = destination.read_bytes()
        collision = destination.with_name(f".{destination.name}.collision.tmp")
        collision_bytes = b"owned by another writer"
        collision.write_bytes(collision_bytes)

        with mock.patch.object(sfx.secrets, "token_hex", return_value="collision"), \
                mock.patch.object(sfx.os, "replace") as replace:
            self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "Node.js"}]}))

        replace.assert_not_called()
        self.assertEqual(destination.read_bytes(), prior)
        self.assertEqual(collision.read_bytes(), collision_bytes)

    def test_temp_directory_collision_is_not_removed(self):
        destination = Path(".sf") / "environment-readiness-report.json"
        destination.parent.mkdir(parents=True)
        collision = destination.with_name(f".{destination.name}.collision.tmp")
        collision.mkdir()

        with mock.patch.object(sfx.secrets, "token_hex", return_value="collision"):
            self.assertFalse(sfx._record_readiness_report({"tools": []}))

        self.assertTrue(collision.is_dir())
        self.assertFalse(destination.exists())

    def test_temp_symlink_collision_is_not_removed_or_followed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are not supported")
        destination = Path(".sf") / "environment-readiness-report.json"
        destination.parent.mkdir(parents=True)
        target = destination.parent / "collision-target"
        target_bytes = b"must remain untouched"
        target.write_bytes(target_bytes)
        collision = destination.with_name(f".{destination.name}.collision.tmp")
        try:
            collision.symlink_to(target.name)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        with mock.patch.object(sfx.secrets, "token_hex", return_value="collision"):
            self.assertFalse(sfx._record_readiness_report({"tools": []}))

        self.assertTrue(collision.is_symlink())
        self.assertEqual(target.read_bytes(), target_bytes)
        self.assertFalse(destination.exists())

    def test_partial_writes_are_completed_before_replace(self):
        report = {"tools": [{"name": "Git", "status": "ok", "message": "complete"}]}
        real_write = os.write
        writes = []

        def write_small_chunk(fd, value):
            chunk = bytes(value[:min(7, len(value))])
            writes.append(chunk)
            return real_write(fd, chunk)

        with mock.patch.object(sfx.os, "write", side_effect=write_small_chunk):
            self.assertTrue(sfx._record_readiness_report(report))

        self.assertGreater(len(writes), 1)
        self.assertEqual(sfx._load_readiness_report(), report)

    def test_failed_short_write_preserves_prior_report_and_cleans_temp(self):
        old = {"tools": [{"name": "Git", "status": "warn", "message": "old"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        path = Path(".sf") / "environment-readiness-report.json"
        prior = path.read_bytes()
        real_write = os.write
        first_write = True

        def short_then_stop(fd, value):
            nonlocal first_write
            if first_write:
                first_write = False
                chunk = bytes(value[:max(1, len(value) // 2)])
                return real_write(fd, chunk)
            return 0

        with mock.patch.object(sfx.os, "write", side_effect=short_then_stop):
            self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "Node.js"}]}))

        self.assertEqual(path.read_bytes(), prior)
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_failed_fsync_preserves_prior_report_and_cleans_temp(self):
        old = {"tools": [{"name": "Git", "status": "warn", "message": "old"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        path = Path(".sf") / "environment-readiness-report.json"
        prior = path.read_bytes()

        with mock.patch.object(sfx.os, "fsync", side_effect=OSError("fsync failed")):
            self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "Node.js"}]}))

        self.assertEqual(path.read_bytes(), prior)
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_failed_replace_preserves_prior_report_and_cleans_temp(self):
        old = {"tools": [{"name": "Git", "status": "warn", "message": "old"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        path = Path(".sf") / "environment-readiness-report.json"
        prior = path.read_bytes()

        with mock.patch.object(sfx.os, "replace", side_effect=OSError("replace failed")):
            self.assertFalse(sfx._record_readiness_report({"tools": [{"name": "Node.js"}]}))

        self.assertEqual(path.read_bytes(), prior)
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_directory_sync_failure_is_reported_and_temp_is_cleaned(self):
        with mock.patch.object(sfx, "_sync_phase_directory", return_value=False) as sync:
            self.assertFalse(sfx._record_readiness_report({"tools": []}))
        sync.assert_called_once()
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_recursive_report_is_rejected_before_filesystem_mutation(self):
        recursive = {"tools": []}
        cursor = recursive
        for _ in range(10000):
            child = {}
            cursor["child"] = child
            cursor = child
        with mock.patch.object(sfx.os, "open", wraps=os.open) as opened:
            self.assertFalse(sfx._record_readiness_report(recursive))
        opened.assert_not_called()
        self.assertFalse(Path(".sf").exists())

    def test_oversized_report_write_is_rejected_before_mutation(self):
        old = {"tools": [{"name": "Git", "status": "ok"}]}
        self.assertTrue(sfx._record_readiness_report(old))
        path = Path(".sf") / "environment-readiness-report.json"
        prior = path.read_bytes()
        oversized = {"tools": [], "padding": "x" * sfx._READINESS_JSON_MAX_BYTES}

        with mock.patch.object(sfx.os, "open", wraps=os.open) as opened:
            self.assertFalse(sfx._record_readiness_report(oversized))

        self.assertEqual(path.read_bytes(), prior)
        opened.assert_not_called()
        self.assertEqual(self._readiness_files(), ["environment-readiness-report.json"])

    def test_absent_report_reads_empty(self):
        # No scan has run yet → honest {} (the paint hook then stays silent).
        self.assertEqual(sfx._load_readiness_report(), {})

    def test_corrupt_report_reads_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        (Path(".sf") / "environment-readiness-report.json").write_text("{ not json")
        self.assertEqual(sfx._load_readiness_report(), {})

    def test_oversized_report_reads_empty(self):
        Path(".sf").mkdir(parents=True, exist_ok=True)
        padding = "x" * sfx._READINESS_JSON_MAX_BYTES
        (Path(".sf") / "environment-readiness-report.json").write_text(
            json.dumps({"tools": [], "padding": padding})
        )
        self.assertEqual(sfx._load_readiness_report(), {})

    def test_unreadable_report_reads_empty(self):
        with mock.patch.object(sfx.os, "open", side_effect=OSError("unreadable")) as opened:
            self.assertEqual(sfx._load_readiness_report(), {})
        opened.assert_called_once()


class WelcomeReadinessTests(unittest.TestCase):
    """`_welcome_readiness` is the cheap 3-way signal the front-of-journey surfaces
    read: it resolves `sf` on PATH and consults a SESSION-SCOPED env-verified marker,
    with NO subprocess. "ready" is earned only by a check-tools pass THIS session
    (recorded by the readiness-paint hook), so a new session re-verifies — readiness
    is a current property, never trusted from a durable cross-session cache."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_marker_dir = sfx._WELCOME_MARKER_DIR
        self._orig_sid = sfx._CURRENT_SESSION_ID
        sfx._WELCOME_MARKER_DIR = Path(self._tmp.name)
        sfx._CURRENT_SESSION_ID = "sess-1"

    def tearDown(self):
        sfx._WELCOME_MARKER_DIR = self._orig_marker_dir
        sfx._CURRENT_SESSION_ID = self._orig_sid
        self._tmp.cleanup()

    def test_absent_when_sf_not_on_path(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            self.assertEqual(sfx._welcome_readiness(), "absent")

    def test_unverified_when_present_but_not_checked_this_session(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            # No env-verified marker recorded for this session yet.
            self.assertEqual(sfx._welcome_readiness(), "unverified")

    def test_ready_when_checked_this_session(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_env_verified("sess-1")
            self.assertEqual(sfx._welcome_readiness(), "ready")

    def test_marker_from_another_session_does_not_carry_over(self):
        # Readiness is session-scoped: a pass recorded under a DIFFERENT session id
        # never counts for this one, so a fresh session honestly re-verifies.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_env_verified("sess-OTHER")
            self.assertEqual(sfx._welcome_readiness(), "unverified")

    def test_absent_wins_even_with_a_marker(self):
        # `sf` off PATH is definitively not-ready, whatever any marker says.
        sfx._record_env_verified("sess-1")
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            self.assertEqual(sfx._welcome_readiness(), "absent")

    def test_no_session_id_reads_unverified(self):
        # The non-hook Bash-subcommand path carries no session id; with nothing to
        # key a marker on, readiness reads conservatively as unverified (never ready).
        sfx._CURRENT_SESSION_ID = ""
        sfx._record_env_verified("sess-1")   # a marker exists, but not for ""
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            self.assertEqual(sfx._welcome_readiness(), "unverified")


class HasAuthedOrgTests(unittest.TestCase):
    """`_has_authed_org` is the cheap, subprocess-free "has the user ever authed an
    org" signal. It is auth HISTORY — deliberately DISTINCT from `_has_target_org`
    (the current-target signal that lights the Connect stage); this one only tunes
    the Connect CTA copy (a returning developer with orgs authed is invited to pick
    one as the target; a first-timer to authenticate one). It lists the global auth
    store (~/.sfdx) — a per-USER, cwd-independent fact — and counts a *.json off the
    non-auth denylist ONLY when its content carries a stored credential. A tokenless
    cache the CLI co-locates there (notably the org-id-keyed *.sandbox.json sandbox-
    process record, which survives `sf org logout --all`) must NOT read as an org, or
    the returning-developer CTA would show falsely. Home is patched to a temp dir so
    the real store is never read (determinism on any machine / CI)."""

    # A credential-bearing auth file (the OAuth shape); any of _AUTH_CREDENTIAL_KEYS
    # would do — this mirrors what `sf org login web` persists.
    AUTH_CONTENT = {"accessToken": "00Dxx!redacted", "refreshToken": "5Aep!redacted",
                    "orgId": "00Dxx0000001gPFEAY", "instanceUrl": "https://x.my.salesforce.com"}
    # The exact key set sf writes into the tokenless *.sandbox.json process cache —
    # note `username` is present (so a "has a username" heuristic would false-positive)
    # but NONE of _AUTH_CREDENTIAL_KEYS is.
    SANDBOX_CACHE = {"prodOrgUsername": "admin@acme.com", "sandboxInfoId": "0GRxx",
                     "sandboxName": "mySandbox", "sandboxOrgId": "00Dxx", "sandboxProcessId": "0GQxx",
                     "sandboxUsername": "admin@acme.com.mysandbox", "timestamp": "2026-07-27T00:00:00Z",
                     "username": "admin@acme.com.mysandbox"}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.sfdx = self.home / ".sfdx"
        self._home_patch = mock.patch.object(sfx.Path, "home", return_value=self.home)
        self._home_patch.start()

    def tearDown(self):
        self._home_patch.stop()
        self._tmp.cleanup()

    def _write(self, name, *, as_dir=False, content=None):
        """Create ~/.sfdx/<name>. Files default to a credential-bearing auth body so a
        plain _write() is a real authentication; pass content={...} for a tokenless
        cache or content='...' for raw (non-JSON) bytes."""
        target = self.sfdx / name
        self.sfdx.mkdir(parents=True, exist_ok=True)
        if as_dir:
            target.mkdir()
            return
        if content is None:
            content = self.AUTH_CONTENT
        body = json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        target.write_text(body, encoding="utf-8")

    def test_true_when_a_username_keyed_auth_file_present(self):
        self._write("jdoe@acme.example.com.json")
        self.assertTrue(sfx._has_authed_org())

    def test_true_for_org_id_and_scratch_keyed_auth(self):
        # Auth files are keyed by username, org-id, or scratch-org id — the KEY shape is
        # irrelevant; a credential in the body is what counts, so a new key shape is
        # still a connection. Presence is monotonic, so each shape in turn stays True.
        for key in ("00Dxx0000001gPFEAY.json", "test-abc123@example.com.json"):
            with self.subTest(key=key):
                self._write(key)
                self.assertTrue(sfx._has_authed_org())

    def test_true_for_jwt_and_password_only_credentials(self):
        # JWT persists a private key (no refresh token); username-password / scratch
        # orgs persist a password. Either alone is a real, durable authentication.
        for content in ({"privateKey": "-----BEGIN-redacted", "username": "svc@acme.com"},
                        {"password": "!redacted", "username": "test@scratch.com"}):
            with self.subTest(cred=sorted(content)[0]):
                self.sfdx.mkdir(parents=True, exist_ok=True)
                for stale in self.sfdx.glob("*.json"):
                    stale.unlink()
                self._write("cred.json", content=content)
                self.assertTrue(sfx._has_authed_org())

    def test_false_for_tokenless_sandbox_process_cache(self):
        # THE N4 regression: an org-id-keyed *.sandbox.json is off the denylist and
        # is_file()==True, but it carries no credential, so it must not light Connect.
        # This is the state left behind by `sf org create sandbox` + `sf org logout`.
        self._write("00DXK0000011cVh2AI.sandbox.json", content=self.SANDBOX_CACHE)
        self.assertFalse(sfx._has_authed_org())

    def test_false_for_credential_less_json(self):
        # A *.json off the denylist that carries no credential (e.g. a stray metadata
        # blob) is not an authentication — content, not filename, is the gate.
        self._write("orphan.json", content={"orgId": "00Dxx", "username": "a@b.c"})
        self.assertFalse(sfx._has_authed_org())

    def test_sandbox_cache_alongside_a_real_auth_returns_true(self):
        # The real auth file still wins — the tokenless cache neither adds nor masks.
        self._write("00DXK0000011cVh2AI.sandbox.json", content=self.SANDBOX_CACHE)
        self._write("jdoe@acme.example.com.json")
        self.assertTrue(sfx._has_authed_org())

    def test_false_when_only_non_auth_files_present(self):
        # The bookkeeping files sf drops next to auth entries must NOT read as an org.
        for name in sfx._NON_AUTH_SFDX_FILES:
            self._write(name)
        self.assertFalse(sfx._has_authed_org())

    def test_mixed_auth_and_non_auth_returns_true(self):
        for name in sfx._NON_AUTH_SFDX_FILES:
            self._write(name)
        self._write("jdoe@acme.example.com.json")
        self.assertTrue(sfx._has_authed_org())

    def test_false_when_sfdx_dir_absent(self):
        # No ~/.sfdx at all → iterdir raises → fails soft to False, never raises.
        self.assertFalse(self.sfdx.exists())
        self.assertFalse(sfx._has_authed_org())

    def test_false_when_sfdx_dir_empty(self):
        self.sfdx.mkdir(parents=True)
        self.assertFalse(sfx._has_authed_org())

    def test_corrupt_or_oversized_json_fails_soft_to_false(self):
        # An unreadable / non-JSON *.json off the denylist must be skipped, never raise.
        self._write("broken.json", content="{not: valid json")
        self.assertFalse(sfx._has_authed_org())

    def test_non_json_files_and_json_subdirectories_do_not_count(self):
        # A .json-suffixed *directory* (is_file() False) and a non-json file must both
        # be ignored — only regular *.json auth entries light Connect.
        self._write("notes.txt")
        self._write("scratch-orgs.json", as_dir=True)
        self.assertFalse(sfx._has_authed_org())


class HasTargetOrgTests(unittest.TestCase):
    """`_has_target_org` is the CURRENT-target signal that lights the Connect stage —
    "is an org set as the default/target right now", distinct from `_has_authed_org`'s
    auth history. Subprocess-free: it reads the local project config first, then the
    global user config, honoring the modern `sf` `target-org` key and the legacy sfdx
    `defaultusername`. A configured-but-offline target still counts as set; a missing /
    empty / corrupt config fails soft to False. Home AND the project root are temp
    dirs so the real config is never read (determinism on any machine / CI)."""

    def setUp(self):
        self._home_tmp = tempfile.TemporaryDirectory()
        self._root_tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._home_tmp.name)
        self.root = Path(self._root_tmp.name)
        self._home_patch = mock.patch.object(sfx.Path, "home", return_value=self.home)
        self._home_patch.start()

    def tearDown(self):
        self._home_patch.stop()
        self._home_tmp.cleanup()
        self._root_tmp.cleanup()

    def _write(self, base, rel, content):
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content) if isinstance(content, dict) else str(content),
                        encoding="utf-8")

    def test_false_when_no_config_anywhere(self):
        self.assertFalse(sfx._has_target_org(self.root))

    def test_true_from_local_sf_config(self):
        self._write(self.root, ".sf/config.json", {"target-org": "acme-dev"})
        self.assertTrue(sfx._has_target_org(self.root))

    def test_true_from_global_sf_config(self):
        self._write(self.home, ".sf/config.json", {"target-org": "acme-dev"})
        self.assertTrue(sfx._has_target_org(self.root))

    def test_true_from_legacy_sfdx_defaultusername(self):
        # A project configured by older sfdx tooling still counts as having a target.
        self._write(self.root, ".sfdx/sfdx-config.json", {"defaultusername": "a@b.c"})
        self.assertTrue(sfx._has_target_org(self.root))

    def test_false_when_config_present_but_no_target_key(self):
        # An empty config, or one carrying only unrelated keys, is not a target.
        self._write(self.root, ".sf/config.json", {})
        self._write(self.home, ".sf/config.json", {"org-api-version": "60.0"})
        self.assertFalse(sfx._has_target_org(self.root))

    def test_false_when_target_value_is_empty(self):
        # A present-but-empty target-org must not read as set.
        self._write(self.root, ".sf/config.json", {"target-org": ""})
        self.assertFalse(sfx._has_target_org(self.root))

    def test_corrupt_config_fails_soft_to_false(self):
        self._write(self.root, ".sf/config.json", "{ not json")
        self.assertFalse(sfx._has_target_org(self.root))

    def test_local_target_counts_even_when_global_is_empty(self):
        # A configured-but-offline target is still "set" — reachability isn't tested
        # here; the org band annotates that separately.
        self._write(self.home, ".sf/config.json", {})
        self._write(self.root, ".sf/config.json", {"target-org": "offline-org"})
        self.assertTrue(sfx._has_target_org(self.root))

    def test_configured_alias_returns_the_target_name(self):
        # _has_target_org is a thin boolean over _configured_target_alias, which returns
        # the NAME so the org band can show *which* org is targeted (not just that one is).
        self._write(self.root, ".sf/config.json", {"target-org": "acme-dev"})
        self.assertEqual(sfx._configured_target_alias(self.root), "acme-dev")

    def test_configured_alias_is_none_when_nothing_is_set(self):
        self.assertIsNone(sfx._configured_target_alias(self.root))

    def test_configured_alias_prefers_local_over_global(self):
        self._write(self.home, ".sf/config.json", {"target-org": "global-org"})
        self._write(self.root, ".sf/config.json", {"target-org": "local-org"})
        self.assertEqual(sfx._configured_target_alias(self.root), "local-org")

    def test_configured_alias_ignores_empty_and_whitespace_values(self):
        self._write(self.root, ".sf/config.json", {"target-org": "   "})
        self.assertIsNone(sfx._configured_target_alias(self.root))


class ToolchainSignatureTests(unittest.TestCase):
    """The freshness signature must be STABLE across shells: per-shell version-manager
    shims (fnm, nvm, pyenv) resolve to different symlink paths per invocation but point
    at the same real executable. Canonicalizing with realpath collapses them, so a
    cached 'ready' verdict isn't spuriously invalidated between the scan and a later
    welcome — while a genuine version change (a new realpath target) still invalidates."""

    def test_signature_canonicalizes_symlinks_to_the_real_binary(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "sf-real"
            real.write_text("#!/bin/sh\n")
            # Two distinct shim paths that both point at the same real binary — the
            # shape of per-shell version-manager churn.
            shim_a = Path(d) / "shim-a"
            shim_b = Path(d) / "shim-b"
            os.symlink(real, shim_a)
            os.symlink(real, shim_b)
            with mock.patch.object(
                sfx, "resolve_executable",
                side_effect=lambda t: str(shim_a) if t == "sf" else None,
            ):
                sig_a = sfx._toolchain_signature()
            with mock.patch.object(
                sfx, "resolve_executable",
                side_effect=lambda t: str(shim_b) if t == "sf" else None,
            ):
                sig_b = sfx._toolchain_signature()
            # Different shims, same real binary → identical signature (the stability).
            self.assertEqual(sig_a, sig_b)
            self.assertIn(os.path.realpath(str(real)), sig_a)   # keyed on the target
            self.assertNotIn("shim-a", sig_a)                    # not on the volatile shim

    def test_missing_tool_contributes_empty_segment_not_a_crash(self):
        # resolve_executable → None for every tool must yield a stable all-empty
        # signature (no realpath call on a falsy path), never an exception.
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            self.assertEqual(sfx._toolchain_signature(), "|||")


class ScaffoldGateTests(unittest.TestCase):
    """The PreToolUse backstop on `sf project generate` — the scaffold chokepoint of
    the front-of-journey readiness floor. It NEVER runs the scan (PATH lookup + one
    small verdict read only), self-gates on the command, and grades block/warn/allow
    by how cheaply it can prove the environment broken. Fails OPEN on any error."""

    def setUp(self):
        self._prev_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    def run_gate(self, command):
        payload = io.StringIO(json.dumps({"tool_input": {"command": command}}))
        out = io.StringIO()
        with mock.patch.object(sfx.sys, "stdin", payload), redirect_stdout(out):
            code = sfx.cmd_scaffold_gate()
        return code, json.loads(out.getvalue())

    def _decision(self, result):
        return result.get("hookSpecificOutput", {}).get("permissionDecision")

    def test_non_scaffold_command_stays_silent_without_touching_path_or_verdict(self):
        # Some Claude Code builds fire every Bash PreToolUse hook — the self-gate
        # must let unrelated commands through without even resolving the CLI.
        for cmd in ("cd /tmp && ls", "sf org list", "sf project deploy start -o x", ""):
            with self.subTest(cmd=cmd):
                with mock.patch.object(sfx, "resolve_executable") as rex, \
                        mock.patch.object(sfx, "_load_readiness_state") as lrs:
                    code, result = self.run_gate(cmd)
                self.assertEqual((code, result), (0, {"continue": True}))
                rex.assert_not_called()
                lrs.assert_not_called()

    def test_absent_cli_denies_with_remediation(self):
        with mock.patch.object(sfx, "resolve_executable", return_value=None):
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(self._decision(result), "deny")
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("platform-environment-validate", reason)
        self.assertRegex(reason, r"(?i)isn't on your path")

    def test_ran_and_failed_verdict_for_this_toolchain_denies(self):
        # A scan that RAN and FAILED under the CURRENT signature is known-broken →
        # block, naming what needs attention.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_readiness_verdict(False, ["Git", "Node.js"], sfx._toolchain_signature())
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(self._decision(result), "deny")
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("Git", reason)
        self.assertIn("Node.js", reason)

    def test_fresh_pass_allows_silently(self):
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_readiness_verdict(True, [], sfx._toolchain_signature())
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(result, {"continue": True})

    def test_warn_only_verdict_allows_silently(self):
        # THE field regression: a scan that recorded warnings but no blockers is
        # ready=True, so scaffolding passes through untouched. This is the non-LTS
        # Node / indeterminate source-tracking case — advisory warns must never gate.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_readiness_verdict(True, ["Node.js", "Source Tracking"],
                                          sfx._toolchain_signature(), blockers=[])
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(result, {"continue": True})
        self.assertIsNone(self._decision(result))

    def test_block_names_only_blockers_not_advisory_warnings(self):
        # When a real blocker and an advisory warn coexist, the deny reason names the
        # blocker (Git) and NOT the warn (Node.js) — a block never reads as though a
        # warning were the thing standing in the way.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_readiness_verdict(False, ["Git", "Node.js"],
                                          sfx._toolchain_signature(), blockers=["Git"])
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(self._decision(result), "deny")
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("Git", reason)
        self.assertNotIn("Node.js", reason)

    def test_unverified_allows_but_nudges_the_check(self):
        # `sf` present, no verdict → can't prove broken → ALLOW, but the model note
        # steers toward verifying first. Never a deny.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            _, result = self.run_gate("sf project generate --name acme")
        self.assertTrue(result.get("continue"))
        self.assertIsNone(self._decision(result))
        note = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("platform-environment-validate", note)

    def test_stale_failed_verdict_does_not_block(self):
        # A failure recorded under a DIFFERENT (since-changed) toolchain no longer
        # describes this machine — we can't prove it's broken now, so warn, not block.
        with mock.patch.object(sfx, "resolve_executable", return_value="/usr/local/bin/sf"):
            sfx._record_readiness_verdict(False, ["Git"], "some-other-signature")
            _, result = self.run_gate("sf project generate --name acme")
        self.assertTrue(result.get("continue"))
        self.assertIsNone(self._decision(result))

    def test_crash_fails_open(self):
        with mock.patch.object(sfx, "_read_hook_payload", side_effect=RuntimeError("boom")):
            _, result = self.run_gate("sf project generate --name acme")
        self.assertEqual(result, {"continue": True})


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

    def test_render_diagnostic_lines_wraps_wide_paths_by_terminal_cells(self):
        wide = "界" * 80
        text = sfx.render_diagnostic_lines({
            "platform": "darwin", "shell": wide, "cwd": wide,
            "pluginRoot": wide, "resolvedExecutables": {"sf": wide},
        })
        self.assertTrue(all(
            sfx._terminal_cell_width(line) <= 80 for line in text.splitlines()
        ), text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
