from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = "service-omni-agent-work-sharing-configure/scripts/configure-and-report.sh"

_FAKE_SF = r'''#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
state_dir="${FAKE_STATE_DIR:?}"
trace="$state_dir/trace"
deployed="$state_dir/deployed"
printf '%s\n' "$args" >> "$trace"

arg_after() {
  local wanted="$1" previous=""
  shift
  for value in "$@"; do
    if [ "$previous" = "$wanted" ]; then printf '%s' "$value"; return; fi
    previous="$value"
  done
}

case "$sub" in
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      if [ "${FAKE_PRODUCTION:-0}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}]}}'
      elif [ "${FAKE_DEVELOPER_EDITION:-0}" = "1" ]; then
        echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":false,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
      else
        echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
      fi
    fi;;
  "project retrieve")
    target_dir=$(arg_after --target-metadata-dir "$@")
    mkdir -p "$target_dir/unpackaged/unpackaged/objects"
    model="${FAKE_CURRENT_MODEL:-Private}"
    if [ -f "$deployed" ]; then model="${FAKE_READBACK_MODEL:-Read}"; fi
    cat > "$target_dir/unpackaged/unpackaged/objects/AgentWork.object" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <externalSharingModel>${FAKE_EXTERNAL_MODEL:-Private}</externalSharingModel>
    <sharingModel>${model}</sharingModel>
</CustomObject>
XML
    echo '{"status":0,"result":{"status":"Succeeded","success":true}}';;
  "project deploy")
    : > "$deployed"
    echo '{"status":0,"result":{"id":"0Afxx0000000001AAA","status":"Succeeded","success":true,"details":{"componentFailures":[]}}}';;
  *) echo '{"status":0,"result":{}}';;
esac
'''


def last_json(output: str) -> dict:
    decoder = json.JSONDecoder()
    result, index = None, 0
    while index < len(output):
        if output[index] not in "{[":
            index += 1
            continue
        try:
            candidate, end = decoder.raw_decode(output, index)
            if isinstance(candidate, dict):
                result = candidate
            index = end
        except json.JSONDecodeError:
            index += 1
    assert result is not None, output
    return result


class FakeSf:
    def __init__(self):
        self.root: Path | None = None
        self.bin_dir: Path | None = None
        self.state_dir: Path | None = None

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="agentwork-sharing-fake-sf-"))
        self.bin_dir = self.root / "bin"
        self.state_dir = self.root / "state"
        self.bin_dir.mkdir()
        self.state_dir.mkdir()
        executable = self.bin_dir / "sf"
        executable.write_text(_FAKE_SF)
        executable.chmod(0o755)
        return self

    def run(self, args, extra_env=None):
        assert self.bin_dir is not None and self.state_dir is not None
        env = dict(os.environ)
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        env["FAKE_STATE_DIR"] = str(self.state_dir)
        if extra_env:
            env.update({key: str(value) for key, value in extra_env.items()})
        proc = subprocess.run(
            ["bash", str(SKILLS_ROOT / SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(SKILLS_ROOT),
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def read_state(self, name: str) -> str:
        assert self.state_dir is not None
        path = self.state_dir / name
        return path.read_text() if path.exists() else ""

    def __exit__(self, *_):
        import shutil
        if self.root:
            shutil.rmtree(self.root, ignore_errors=True)
