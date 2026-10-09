"""Fake Salesforce CLI harness for the Omni-Channel inventory analyzer."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = SKILLS_ROOT / "service-omni-channel-inventory-analyze/scripts/analyze.sh"

_FAKE_SF = r'''#!/usr/bin/env bash
command_name="${1:-} ${2:-}"
case "$command_name" in
  "org display")
    if [ "${FAKE_AUTH:-ok}" = "fail" ]; then
      echo '{"status":1,"message":"not authenticated"}' >&2
      exit 1
    fi
    echo '{"status":0,"result":{}}'
    ;;
  "api request")
    printf '%s\n' "$*" >> "${FAKE_SF_LOG:?}"
    if [ "${FAKE_API_STATUS:-ok}" = "fail" ]; then
      echo "${FAKE_API_ERROR:-request failed}" >&2
      exit 1
    fi
    printf '%s\n' "${FAKE_API_BODY:-[]}"
    ;;
  *)
    echo '{"status":1,"message":"unexpected command"}' >&2
    exit 1
    ;;
esac
'''


class FakeSf:
    def __enter__(self):
        self._directory = tempfile.mkdtemp(prefix="omni-inventory-fake-sf-")
        self.log_path = Path(self._directory) / "commands.log"
        sf_path = Path(self._directory) / "sf"
        sf_path.write_text(_FAKE_SF)
        sf_path.chmod(0o755)
        return self

    def run(self, args: list[str], **values):
        env = dict(os.environ)
        env["PATH"] = self._directory + os.pathsep + env.get("PATH", "")
        env["FAKE_SF_LOG"] = str(self.log_path)
        for key, value in values.items():
            env[key] = json.dumps(value) if key == "FAKE_API_BODY" and not isinstance(value, str) else str(value)
        process = subprocess.run(
            ["bash", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(SKILLS_ROOT),
        )
        commands = self.log_path.read_text() if self.log_path.exists() else ""
        return process.returncode, process.stdout + process.stderr, commands

    def __exit__(self, *_):
        shutil.rmtree(self._directory, ignore_errors=True)


def last_json(output: str) -> dict:
    decoder = json.JSONDecoder()
    parsed = None
    position = 0
    while position < len(output):
        if output[position] == "{":
            try:
                candidate, end = decoder.raw_decode(output, position)
                parsed = candidate
                position = end
                continue
            except json.JSONDecodeError:
                pass
        position += 1
    assert parsed is not None, f"No JSON object found in output:\n{output}"
    return parsed
