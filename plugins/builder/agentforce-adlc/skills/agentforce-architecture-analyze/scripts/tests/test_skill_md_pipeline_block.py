"""Run SKILL.md's "## Pipeline invocation" bash block under bash and zsh.

The block is the contract the agent executes verbatim, so these tests extract
it from SKILL.md (no copy to drift) and run it under ``env -i`` against:

* a stub SKILL_ROOT whose scripts/main.py records its argv, emit_result.py
  prints a RESULT marker, and _shared/fs_guard.py always passes;
* a stub ``sf`` on PATH that answers ``config get target-org --json`` with a
  canned payload (or fails).

Scenarios: ARGUMENTS unset with ARG_AGENT preset (default org used), flags in
ARGUMENTS, flags overriding preset ARG_*, nothing resolvable (usage, no
pipeline run), and SKILL_ROOT discovery when the scripts are staged under
``<candidate>/artifacts/`` (the ADK eval staging layout).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_NAME = "agentforce-architecture-analyze"


def _find_skill_md() -> Path:
    # contributed-skills: <skill>/scripts/tests/ -> <skill>/SKILL.md
    # outputs/unified-sors: <skill>/artifacts/scripts/tests/ -> <skill>/SKILL.md
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "SKILL.md"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("SKILL.md not found above " + __file__)


def _extract_pipeline_block(skill_md: str) -> str:
    section = skill_md.split("## Pipeline invocation", 1)[1]
    match = re.search(r"```bash\n(.*?)\n```", section, re.S)
    if match is None:
        raise ValueError("no ```bash block under '## Pipeline invocation'")
    return match.group(1) + "\n"


def _write_exec(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


_RECORDER = """\
import json, os, sys
with open({record!r}, "a") as fh:
    fh.write(json.dumps({{"script": {name!r}, "path": os.path.realpath(__file__),
                         "argv": sys.argv[1:]}}) + "\\n")
{tail}
"""

_SF_STUB = """#!/bin/sh
# Canned `sf config get target-org --json`; behaviour chosen by SF_STUB_MODE.
if [ "$1 $2 $3" != "config get target-org" ]; then
  echo "unexpected sf call: $*" >&2; exit 3
fi
case "${SF_STUB_MODE:-set}" in
  set) cat <<'JSON'
{
  "status": 0,
  "result": [
    {
      "name": "target-org",
      "location": "Local",
      "value": "default-org",
      "success": true
    }
  ],
  "warnings": []
}
JSON
  ;;
  unset) printf '%s\\n' '{"status":0,"result":[{"name":"target-org","success":true}],"warnings":[]}' ;;
  fail) echo '{"status":1,"name":"Error"}'; exit 1 ;;
esac
"""


class PipelineBlockTest(unittest.TestCase):
    SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]

    @classmethod
    def setUpClass(cls) -> None:
        cls.block = _extract_pipeline_block(_find_skill_md().read_text())

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="arch-block-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.record = self.tmp / "calls.jsonl"
        self.root = self.tmp / "skill"
        self._make_stub_scripts(self.root)
        self.bin = self.tmp / "bin"
        _write_exec(self.bin / "sf", _SF_STUB)
        (self.bin / "python3").symlink_to(sys.executable)
        self.script = self.tmp / "block.sh"
        self.script.write_text(self.block)
        self.home = self.tmp / "home"
        self.home.mkdir()

    # -- helpers ---------------------------------------------------------

    def _make_stub_scripts(self, root: Path) -> Path:
        """Recorder stubs for main.py / emit_result.py / _shared/fs_guard.py
        under ``root/scripts``; returns that scripts dir."""
        scripts = root / "scripts"
        (scripts / "_shared").mkdir(parents=True)
        (scripts / "main.py").write_text(
            _RECORDER.format(record=str(self.record), name="main", tail="")
        )
        (scripts / "emit_result.py").write_text(
            _RECORDER.format(
                record=str(self.record), name="emit",
                tail='print("=== RESULT ===")',
            )
        )
        (scripts / "_shared" / "fs_guard.py").write_text(
            _RECORDER.format(record=str(self.record), name="fs_guard", tail="")
        )
        return scripts

    def _run(self, shell: str, extra_env: dict[str, str], with_sf: bool = True,
             skill_root: str | None = None):
        if self.record.exists():
            self.record.unlink()
        bin_dir = self.bin
        if not with_sf:
            bin_dir = self.tmp / "bin-nosf"
            bin_dir.mkdir(exist_ok=True)
            if not (bin_dir / "python3").exists():
                (bin_dir / "python3").symlink_to(sys.executable)
        env = {
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "HOME": str(self.home),
            **extra_env,
        }
        if skill_root is None:
            env["SKILL_ROOT"] = str(self.root)
        elif skill_root:
            env["SKILL_ROOT"] = skill_root
        # skill_root="" → SKILL_ROOT unset, so the install-root probe runs.
        cmd = ["env", "-i", *(f"{k}={v}" for k, v in env.items()),
               shell, str(self.script)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        calls = []
        if self.record.exists():
            calls = [json.loads(l) for l in self.record.read_text().splitlines()]
        for call in calls:
            if call["script"] == "main" and "--work-dir" in call["argv"]:
                wd = call["argv"][call["argv"].index("--work-dir") + 1]
                shutil.rmtree(wd, ignore_errors=True)
        return proc, calls

    def _main_argv(self, calls):
        mains = [c["argv"] for c in calls if c["script"] == "main"]
        self.assertEqual(len(mains), 1, calls)
        return mains[0]

    def _opt(self, argv, flag):
        self.assertIn(flag, argv)
        return argv[argv.index(flag) + 1]

    # -- scenarios -------------------------------------------------------

    def test_shells_available(self) -> None:
        self.assertIn("bash", self.SHELLS)

    def test_a_arguments_unset_preset_agent_uses_default_org(self) -> None:
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(shell, {"ARG_AGENT": "Support_Agent"})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._main_argv(calls)
                self.assertEqual(self._opt(argv, "--org-alias"), "default-org")
                self.assertEqual(self._opt(argv, "--agent"), "Support_Agent")
                self.assertTrue(proc.stdout.rstrip().endswith("=== RESULT ==="))

    def test_b_flags_in_arguments(self) -> None:
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(
                    shell, {"ARGUMENTS": "--org o1 --agent a1 --version=v3 --force"}
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._main_argv(calls)
                self.assertEqual(self._opt(argv, "--org-alias"), "o1")
                self.assertEqual(self._opt(argv, "--agent"), "a1")
                self.assertEqual(self._opt(argv, "--version"), "v3")
                self.assertIn("--force", argv)

    def test_c_flags_override_preset_env(self) -> None:
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(shell, {
                    "ARGUMENTS": "document * the agent --org=o2 --agent a2",
                    "ARG_ORG": "env-org",
                    "ARG_AGENT": "EnvAgent",
                })
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._main_argv(calls)
                self.assertEqual(self._opt(argv, "--org-alias"), "o2")
                self.assertEqual(self._opt(argv, "--agent"), "a2")

    def test_preset_org_skips_default_lookup(self) -> None:
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(shell, {
                    "ARG_ORG": "env-org", "ARG_AGENT": "EnvAgent",
                    "SF_STUB_MODE": "fail",
                })
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._main_argv(calls)
                self.assertEqual(self._opt(argv, "--org-alias"), "env-org")

    def test_d_nothing_resolvable_prints_usage(self) -> None:
        cases = [
            ("unset", {"SF_STUB_MODE": "unset"}, True),
            ("sf-fails", {"SF_STUB_MODE": "fail"}, True),
            ("no-sf", {}, False),
            ("agent-only-no-default", {"SF_STUB_MODE": "unset", "ARG_AGENT": "A"}, True),
        ]
        for shell in self.SHELLS:
            for label, env, with_sf in cases:
                with self.subTest(shell=shell, case=label):
                    proc, calls = self._run(shell, env, with_sf=with_sf)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn("Which agent should I document", proc.stderr)
                    self.assertEqual(
                        [c for c in calls if c["script"] == "main"], []
                    )

    # -- SKILL_ROOT discovery: ADK eval artifacts/ staging layout ----------

    def _assert_all_from(self, calls, scripts_dir: Path) -> None:
        """main, emit_result and fs_guard all ran from ``scripts_dir``."""
        real = scripts_dir.resolve()
        self.assertEqual({c["script"] for c in calls}, {"main", "emit", "fs_guard"})
        for call in calls:
            self.assertTrue(
                Path(call["path"]).is_relative_to(real), (call["path"], real)
            )

    def test_e_scripts_only_under_artifacts_of_exported_root(self) -> None:
        staged = self.tmp / "staged" / _SKILL_NAME
        scripts = self._make_stub_scripts(staged / "artifacts")
        (staged / "SKILL.md").write_text("# staged\n")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(
                    shell, {"ARG_AGENT": "A", "ARG_ORG": "o"},
                    skill_root=str(staged),
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self._assert_all_from(calls, scripts)
                self._main_argv(calls)

    def test_f_artifacts_found_via_install_root_probe(self) -> None:
        # SKILL_ROOT unset: the candidate comes from the $HOME/.claude/skills probe.
        staged = self.home / ".claude" / "skills" / _SKILL_NAME
        scripts = self._make_stub_scripts(staged / "artifacts")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(
                    shell, {"ARG_AGENT": "A", "ARG_ORG": "o"}, skill_root="",
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self._assert_all_from(calls, scripts)

    def test_g_candidate_root_preferred_over_its_artifacts(self) -> None:
        root_scripts = self.root / "scripts"
        self._make_stub_scripts(self.root / "artifacts")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(shell, {"ARG_AGENT": "A", "ARG_ORG": "o"})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self._assert_all_from(calls, root_scripts)

    def test_h_earlier_candidate_artifacts_beats_later_candidate_root(self) -> None:
        # Candidate order is unchanged: exported SKILL_ROOT (artifacts layout)
        # wins over a later install root that has scripts/ at its top level.
        staged = self.tmp / "staged" / _SKILL_NAME
        scripts = self._make_stub_scripts(staged / "artifacts")
        self._make_stub_scripts(self.home / ".claude" / "skills" / _SKILL_NAME)
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(
                    shell, {"ARG_AGENT": "A", "ARG_ORG": "o"},
                    skill_root=str(staged),
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self._assert_all_from(calls, scripts)

    def test_i_no_scripts_anywhere_reports_guard_message(self) -> None:
        empty = self.tmp / "empty" / _SKILL_NAME
        (empty / "artifacts").mkdir(parents=True)
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(
                    shell, {"ARG_AGENT": "A", "ARG_ORG": "o"},
                    skill_root=str(empty),
                )
                self.assertEqual(proc.returncode, 1)
                self.assertIn(f"{_SKILL_NAME}: scripts not found", proc.stderr)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
