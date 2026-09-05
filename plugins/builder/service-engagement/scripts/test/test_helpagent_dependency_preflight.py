#!/usr/bin/env python3
"""Offline tests for the Help Agent dependency registry classifier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "helpagent_dependency_preflight.py"

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
log_path = os.environ.get("FAKE_CLAUDE_LOG")
if log_path:
    Path(log_path).write_text(json.dumps(args), encoding="utf-8")

if args != ["plugin", "list", "--json"]:
    print("unexpected command", file=sys.stderr)
    raise SystemExit(2)

mode = os.environ.get("FAKE_CLAUDE_MODE", "enabled")
secret_entry = {
    "id": "unrelated@marketplace",
    "enabled": True,
    "mcpServers": {"private": {"headers": {"Authorization": "SECRET_MUST_NOT_LEAK"}}},
}
if mode == "enabled":
    payload = [secret_entry, {"id": "agentforce-adlc@claude-plugins-official", "enabled": True, "installPath": "/private/cache/path"}]
elif mode == "disabled":
    payload = [secret_entry, {"id": "agentforce-adlc@claude-plugins-official", "enabled": False}]
elif mode == "missing":
    payload = [secret_entry, {"id": "agentforce-adlc-evil@marketplace", "enabled": True}]
elif mode == "multiple":
    payload = [
        {"id": "agentforce-adlc@claude-plugins-official", "enabled": True},
        {"id": "agentforce-adlc@custom", "enabled": False},
    ]
elif mode == "unsafe":
    payload = [{"id": "agentforce-adlc@bad/marketplace", "enabled": True}]
elif mode == "malformed":
    print("not json SECRET_MUST_NOT_LEAK")
    raise SystemExit(0)
elif mode == "failure":
    print("SECRET_MUST_NOT_LEAK", file=sys.stderr)
    raise SystemExit(1)
else:
    payload = []

print(json.dumps(payload))
raise SystemExit(0)
'''


class HelpAgentDependencyPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="helpagent-dependency-test-")
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.claude_path = self.bin_dir / "claude"
        self.claude_path.write_text(FAKE_CLAUDE, encoding="utf-8")
        self.claude_path.chmod(self.claude_path.stat().st_mode | stat.S_IXUSR)
        self.log_path = self.root / "claude-call.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_preflight(self, mode: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}",
                "FAKE_CLAUDE_LOG": str(self.log_path),
                "FAKE_CLAUDE_MODE": mode,
            }
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        return result, json.loads(result.stdout)

    def test_installed_enabled_returns_only_sanitized_matching_state(self) -> None:
        result, payload = self.run_preflight("enabled")

        self.assertEqual(result.returncode, 10)
        self.assertEqual(payload["registryState"], "installed_enabled")
        self.assertEqual(payload["pluginId"], "agentforce-adlc@claude-plugins-official")
        self.assertFalse(payload["liveCapabilityVerified"])
        self.assertNotIn("SECRET_MUST_NOT_LEAK", result.stdout)
        self.assertNotIn("/private/cache/path", result.stdout)
        self.assertEqual(json.loads(self.log_path.read_text(encoding="utf-8")), ["plugin", "list", "--json"])

    def test_installed_disabled_preserves_exact_safe_plugin_id(self) -> None:
        result, payload = self.run_preflight("disabled")

        self.assertEqual(result.returncode, 11)
        self.assertEqual(payload["registryState"], "installed_disabled")
        self.assertEqual(payload["pluginId"], "agentforce-adlc@claude-plugins-official")

    def test_similar_plugin_name_does_not_satisfy_dependency(self) -> None:
        result, payload = self.run_preflight("missing")

        self.assertEqual(result.returncode, 12)
        self.assertEqual(payload["registryState"], "missing")
        self.assertIsNone(payload["pluginId"])

    def test_multiple_matching_entries_are_inconclusive(self) -> None:
        result, payload = self.run_preflight("multiple")

        self.assertEqual(result.returncode, 13)
        self.assertEqual(payload["registryState"], "inconclusive")
        self.assertIsNone(payload["pluginId"])

    def test_unsafe_matching_id_is_inconclusive_and_not_reflected(self) -> None:
        result, payload = self.run_preflight("unsafe")

        self.assertEqual(result.returncode, 13)
        self.assertEqual(payload["registryState"], "inconclusive")
        self.assertNotIn("bad/marketplace", result.stdout)

    def test_malformed_or_failed_registry_never_leaks_raw_output(self) -> None:
        for mode in ("malformed", "failure"):
            with self.subTest(mode=mode):
                result, payload = self.run_preflight(mode)
                self.assertEqual(result.returncode, 13)
                self.assertEqual(payload["registryState"], "inconclusive")
                self.assertNotIn("SECRET_MUST_NOT_LEAK", result.stdout)
                self.assertNotIn("SECRET_MUST_NOT_LEAK", result.stderr)


if __name__ == "__main__":
    unittest.main()
