"""Org-free security tests proving the TraceFlag fail-closed contract for both run-create.sh scripts: setPassword runs only when no active TraceFlag exists (else users stay reset_required; a failing TraceFlag query also fails closed), proven via a fake-sf marker file."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]  # the skills/ directory
AGENT_SCRIPT = SKILLS_ROOT / "service-omni-agent-users-create/scripts/run-create.sh"
SUPERVISOR_SCRIPT = SKILLS_ROOT / "service-omni-supervisor-users-create/scripts/run-create.sh"

FAKE_SF = r"""#!/usr/bin/env bash
# Minimal fake `sf` for TraceFlag fail-closed tests. Differentiates the create-users Apex from the
# System.setPassword Apex by reading the --file contents, and records setPassword submissions.
cmd="$1"; sub="$2"; shift 2 || true
all="$*"
file=""
prev=""
for a in "$@"; do
  if [ "$prev" = "--file" ]; then file="$a"; fi
  prev="$a"
done
case "$cmd $sub" in
  "apex run")
    # The setPassword Apex is EXACTLY `System.setPassword('id','pw');` on its first line; the
    # create-users template may merely mention setPassword in a comment, so match the first line only.
    if [ -n "$file" ] && head -1 "$file" 2>/dev/null | grep -q '^System.setPassword'; then
      : > "$FAKE_SETPW_MARKER"
      echo '{"status":0,"result":{"compiled":true,"success":true,"logs":""}}'
    else
      echo '{"status":0,"result":{"compiled":true,"success":true,"logs":"AGENT_USER_CREATED|005000000000001AAA|agent1.sfx@example.com|agent1.sfx@example.com SUPERVISOR_CREATED|005000000000002AAA|supervisor1.sfx@example.com|supervisor1.sfx@example.com"}}'
    fi
    ;;
  "org display")
    echo '{"status":0,"result":{"username":"admin@example.com"}}'
    ;;
  "data query")
    if printf '%s' "$all" | grep -q "TraceFlag"; then
      case "${FAKE_TF:-none}" in
        active) echo '{"status":0,"result":{"totalSize":1,"records":[{"Id":"7tf000000000001AAA","ExpirationDate":"2999-01-01T12:00:00.000+0000"}]}}' ;;
        fail)   exit 1 ;;
        *)      echo '{"status":0,"result":{"totalSize":0,"records":[]}}' ;;
      esac
    else
      echo '{"status":0,"result":{"records":[{"Id":"005000000000009AAA"}]}}'
    fi
    ;;
  *)
    echo '{"status":0,"result":{}}'
    ;;
esac
"""


def _run(script: Path, tf_mode: str):
    """Run a user-create script with the fake sf; return (rc, parsed_json, setpw_called)."""
    with tempfile.TemporaryDirectory() as tmp:
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        (bindir / "sf").write_text(FAKE_SF)
        (bindir / "sf").chmod(0o755)
        marker = Path(tmp) / "setpw_called"

        cred_file = Path(tmp) / "CREDENTIALS.json"
        env = dict(os.environ)
        env["PATH"] = f"{bindir}:{env['PATH']}"
        env["FAKE_TF"] = tf_mode
        env["FAKE_SETPW_MARKER"] = str(marker)
        # Isolate the credentials escrow file inside the temp dir so a run never writes to the repo.
        env["OMNI_CREDENTIALS_FILE"] = str(cred_file)

        proc = subprocess.run(
            ["bash", str(script), "myorg", "1", "00e000000000001AAA", "sfx"],
            capture_output=True, text=True, env=env, cwd=tmp,
        )
        out = None
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
        cred_text = cred_file.read_text() if cred_file.exists() else ""
        return proc.returncode, out, marker.exists(), proc.stdout + proc.stderr, cred_text


class TraceFlagFailClosedTests(unittest.TestCase):
    SCRIPTS = (("agent", AGENT_SCRIPT), ("supervisor", SUPERVISOR_SCRIPT))

    def test_no_traceflag_sets_password(self):
        for label, script in self.SCRIPTS:
            with self.subTest(script=label):
                rc, out, setpw_called, raw, cred_text = _run(script, "none")
                self.assertEqual(rc, 0, raw)
                self.assertIsNotNone(out, raw)
                self.assertTrue(setpw_called, "System.setPassword must run when no TraceFlag is active")
                self.assertIsNone(out.get("security_warning"), raw)
                self.assertEqual(out["created_users"][0]["password_status"], "generated", raw)
                # P0: plaintext must NEVER be in stdout - it is escrowed to the 0600 credentials file.
                self.assertIsNone(out["created_users"][0]["password"], raw)
                self.assertTrue(out.get("credentials_written"), raw)
                self.assertTrue(str(out.get("credentials_file", "")).endswith("CREDENTIALS.json"), raw)
                pw = json.loads(cred_text)
                pairs = next(iter(pw.values()))
                self.assertTrue(pairs and pairs[0].get("password"), "escrow file must hold the plaintext")
                self.assertNotIn(pairs[0]["password"], raw, "generated password leaked into stdout/stderr")

    def test_active_traceflag_never_calls_setpassword(self):
        for label, script in self.SCRIPTS:
            with self.subTest(script=label):
                rc, out, setpw_called, raw, cred_text = _run(script, "active")
                self.assertEqual(rc, 0, raw)
                self.assertIsNotNone(out, raw)
                self.assertFalse(setpw_called,
                                 "PROOF FAILED: System.setPassword was submitted while a TraceFlag was active")
                self.assertIsNotNone(out.get("security_warning"), raw)
                self.assertEqual(out["created_users"][0]["password_status"], "reset_required", raw)
                self.assertIsNone(out["created_users"][0]["password"], raw)

    def test_traceflag_query_failure_fails_closed(self):
        for label, script in self.SCRIPTS:
            with self.subTest(script=label):
                rc, out, setpw_called, raw, cred_text = _run(script, "fail")
                self.assertEqual(rc, 0, raw)
                self.assertIsNotNone(out, raw)
                self.assertFalse(setpw_called,
                                 "A failed TraceFlag query must fail closed (no setPassword)")
                self.assertIsNotNone(out.get("security_warning"), raw)
                self.assertEqual(out["created_users"][0]["password_status"], "reset_required", raw)


class SourceContractTests(unittest.TestCase):
    """Guard the exact fail-closed shape so a refactor cannot silently regress it."""

    def test_setpassword_is_gated_on_traceflag_safe(self):
        for script in (AGENT_SCRIPT, SUPERVISOR_SCRIPT):
            src = script.read_text()
            self.assertIn('if [ "$TRACEFLAG_SAFE" != "true" ]; then', src, str(script))
            # The active-TraceFlag path must `continue` before reaching set_password_via_apex.
            gate = src.index('if [ "$TRACEFLAG_SAFE" != "true" ]; then')
            setpw = src.index("SETPW_RESULT=$(set_password_via_apex")
            self.assertLess(gate, setpw, f"{script}: TRACEFLAG_SAFE gate must precede setPassword")

    def test_traceflag_query_uses_soql_expiration_filter(self):
        for script in (AGENT_SCRIPT, SUPERVISOR_SCRIPT):
            src = script.read_text()
            self.assertIn("ExpirationDate > $NOW_UTC", src, str(script))
            self.assertIn("TRACEFLAG_SAFE=false", src, str(script))

    def test_password_never_passed_via_jq_argv(self):
        # The generated password must not reach jq (or any command) through argv/env, which are visible
        # via process inspection. It is fed to jq over stdin and escrowed via --slurpfile (a file).
        for script in (AGENT_SCRIPT, SUPERVISOR_SCRIPT):
            src = script.read_text()
            self.assertNotIn('--arg p "$PW"', src, f"{script}: password must not be a jq --arg")
            self.assertNotIn('--argjson c "$pairs"', src, f"{script}: pairs (with secrets) must not be jq argv")
            self.assertIn('printf \'%s\' "$PW" | jq -Rsc', src, f"{script}: password must be fed via stdin")
            self.assertIn('--slurpfile c "$pairs_file"', src, f"{script}: escrow must read pairs from a file")

    def test_escrow_failure_marks_users_needing_reset(self):
        # When escrow fails the plaintext is unrecoverable, so the affected users must be listed in
        # users_needing_password_reset (not only flipped in per-user status).
        for script in (AGENT_SCRIPT, SUPERVISOR_SCRIPT):
            src = script.read_text()
            self.assertIn("ESCROW_FAILED_UNAMES=", src, str(script))
            self.assertIn("NEEDS_RESET=$(jq -c -n --argjson a \"$NEEDS_RESET\" --argjson b \"$ESCROW_FAILED_UNAMES\"", src, str(script))


if __name__ == "__main__":
    unittest.main(verbosity=2)
