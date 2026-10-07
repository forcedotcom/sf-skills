"""Run SKILL.md's "## Resolving the script prefix" bash block under bash and zsh.

The block is the contract the agent executes verbatim, so these tests extract
it from SKILL.md (no copy to drift) and run it under ``env -i`` against fake
install layouts, then call ``python3 "$prefix/fetch_dc.py"`` the way every
later SKILL.md invocation does. The stub fetch_dc.py records its own path so
the test can assert which copy actually ran.

Scenarios: scripts at the candidate root (shipped layout), scripts only under
``<candidate>/artifacts/scripts/`` (ADK eval staging layout) via an exported
SKILL_ROOT and via the install-root probe, root preferred over its own
artifacts/, candidate order preserved, and nothing found (guard message).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SKILL_NAME = "agentforce-d360-analyze"


def _find_skill_md() -> Path:
    # contributed-skills: <skill>/scripts/tests/ -> <skill>/SKILL.md
    # outputs/unified-sors: <skill>/artifacts/scripts/tests/ -> <skill>/SKILL.md
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "SKILL.md"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("SKILL.md not found above " + __file__)


def _extract_prefix_block(skill_md: str) -> str:
    section = skill_md.split("## Resolving the script prefix", 1)[1]
    match = re.search(r"```bash\n(.*?)\n```", section, re.S)
    if match is None:
        raise ValueError("no ```bash block under '## Resolving the script prefix'")
    return match.group(1) + "\n"


_FETCH_STUB = """\
import json, os, sys
with open({record!r}, "a") as fh:
    fh.write(json.dumps({{"path": os.path.realpath(__file__),
                         "argv": sys.argv[1:]}}) + "\\n")
"""

# Appended after the extracted block: report what it resolved, then invoke the
# entry script exactly as the rest of SKILL.md does.
_EPILOGUE = """
printf 'SKILL_ROOT=%s\\nprefix=%s\\n' "$SKILL_ROOT" "$prefix"
python3 "$prefix/fetch_dc.py" --session probe-test
"""


class PrefixBlockTest(unittest.TestCase):
    SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]

    @classmethod
    def setUpClass(cls) -> None:
        cls.block = _extract_prefix_block(_find_skill_md().read_text())

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="d360-prefix-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.record = self.tmp / "calls.jsonl"
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "python3").symlink_to(sys.executable)
        self.script = self.tmp / "block.sh"
        self.script.write_text(self.block + _EPILOGUE)

    # -- helpers ---------------------------------------------------------

    def _make_scripts(self, root: Path) -> Path:
        scripts = root / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "fetch_dc.py").write_text(_FETCH_STUB.format(record=str(self.record)))
        return scripts

    def _run(self, shell: str, skill_root: str | None):
        if self.record.exists():
            self.record.unlink()
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home)}
        if skill_root is not None:
            env["SKILL_ROOT"] = skill_root
        cmd = ["env", "-i", *(f"{k}={v}" for k, v in env.items()),
               shell, str(self.script)]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=self.tmp,
        )
        calls = []
        if self.record.exists():
            calls = [json.loads(l) for l in self.record.read_text().splitlines()]
        return proc, calls

    def _assert_resolved(self, proc, calls, root: Path) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"SKILL_ROOT={root}\n", proc.stdout)
        self.assertIn(f"prefix={root}/scripts\n", proc.stdout)
        self.assertEqual(len(calls), 1, calls)
        self.assertEqual(
            calls[0]["path"], str((root / "scripts" / "fetch_dc.py").resolve())
        )
        self.assertEqual(calls[0]["argv"], ["--session", "probe-test"])

    # -- scenarios -------------------------------------------------------

    def test_shells_available(self) -> None:
        self.assertIn("bash", self.SHELLS)

    def test_a_shipped_layout_exported_root(self) -> None:
        root = self.tmp / "skill"
        self._make_scripts(root)
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                self._assert_resolved(*self._run(shell, str(root)), root)

    def test_b_scripts_only_under_artifacts_of_exported_root(self) -> None:
        staged = self.tmp / "staged" / _SKILL_NAME
        self._make_scripts(staged / "artifacts")
        (staged / "SKILL.md").write_text("# staged\n")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                self._assert_resolved(
                    *self._run(shell, str(staged)), staged / "artifacts"
                )

    def test_c_artifacts_found_via_install_root_probe(self) -> None:
        staged = self.home / ".claude" / "skills" / _SKILL_NAME
        self._make_scripts(staged / "artifacts")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                self._assert_resolved(
                    *self._run(shell, None), staged / "artifacts"
                )

    def test_d_candidate_root_preferred_over_its_artifacts(self) -> None:
        root = self.tmp / "skill"
        self._make_scripts(root)
        self._make_scripts(root / "artifacts")
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                self._assert_resolved(*self._run(shell, str(root)), root)

    def test_e_earlier_candidate_artifacts_beats_later_candidate_root(self) -> None:
        staged = self.tmp / "staged" / _SKILL_NAME
        self._make_scripts(staged / "artifacts")
        self._make_scripts(self.home / ".claude" / "skills" / _SKILL_NAME)
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                self._assert_resolved(
                    *self._run(shell, str(staged)), staged / "artifacts"
                )

    def test_f_no_scripts_anywhere_reports_guard_message(self) -> None:
        empty = self.tmp / "empty" / _SKILL_NAME
        (empty / "artifacts").mkdir(parents=True)
        for shell in self.SHELLS:
            with self.subTest(shell=shell):
                proc, calls = self._run(shell, str(empty))
                self.assertEqual(proc.returncode, 1)
                self.assertIn(f"{_SKILL_NAME}: scripts not found", proc.stderr)
                self.assertNotIn("prefix=", proc.stdout)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
