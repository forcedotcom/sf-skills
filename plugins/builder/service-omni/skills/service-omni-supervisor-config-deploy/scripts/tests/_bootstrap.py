from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = "service-omni-supervisor-config-deploy/scripts/deploy-and-report.sh"

_FAKE_SF = r'''#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
state_dir="${FAKE_STATE_DIR:?}"
deployed="$state_dir/deployed"
actions="$state_dir/actions"
tabs="$state_dir/tabs"
trace="$state_dir/trace"
capture_xml="$state_dir/deployed.xml"
capture_package="$state_dir/package.xml"
config_dn="${FAKE_CONFIG_DN:-Omni_Supervisor}"

emit_surface() {
  local kind="$1" source_file="$2" initial_json="$3" field="$4"
  if [ ! -f "$deployed" ]; then
    printf '%s' "$initial_json" | jq -c --arg field "$field" '
      to_entries | {status:0,result:{records:map({($field):.value,DisplayOrder:(.key+1)})}}'
    return
  fi
  if [ ! -s "$source_file" ]; then
    echo '{"status":0,"result":{"records":[]}}'
    return
  fi
  jq -R -s -c --arg field "$field" '
    split("\n") | map(select(length>0)) | to_entries |
    {status:0,result:{records:map({($field):.value,DisplayOrder:(.key+1)})}}' "$source_file"
}

case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}';;
  "org list") echo '{"status":0,"result":[]}' ;;
  "data query")
    printf '%s\n' "$args" >> "$trace"
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Dxx0000000000EAA","IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Developer Edition"}]}}'
    elif printf '%s' "$args" | grep -q "FROM User"; then
      echo '{"status":0,"result":{"records":[{"Id":"005xx0000000001AAA","Username":"supervisor1.0000000e@example.com","Profile":{"Name":"Standard User"}}]}}'
    elif printf '%s' "$args" | grep -q "FROM Group"; then
      echo '{"status":0,"result":{"records":[{"Id":"00Gxx0000000001AAA"}]}}'
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigAction"; then
      emit_surface action "$actions" "${FAKE_EXIST_ACTIONS:-[]}" OmniSupervisorActionType
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigTab"; then
      emit_surface tab "$tabs" "${FAKE_EXIST_TABS:-[]}" OmniSupervisorTabType
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigUser"; then
      echo '{"status":0,"result":{"records":[{"Id":"0Q4xx0000000001AAA"}]}}'
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfigQueue"; then
      echo '{"status":0,"result":{"records":[{"Id":"0Q5xx0000000001AAA"}]}}'
    elif printf '%s' "$args" | grep -q "FROM OmniSupervisorConfig"; then
      printf '{"status":0,"result":{"records":[{"Id":"0Q2xx0000000001AAA","DeveloperName":"%s","MasterLabel":"%s","SkillVisibility":"%s"}]}}' "$config_dn" "${FAKE_MASTER_LABEL:-Existing Supervisor Label}" "${FAKE_SKILL_VISIBILITY:-AnySkill}"
    else
      echo '{"status":0,"result":{"records":[]}}'
    fi;;
  "project deploy")
    if printf '%s' "$args" | grep -q " start "; then
      cp "force-app/main/default/omniSupervisorConfigs/$config_dn.omniSupervisorConfig-meta.xml" "$capture_xml"
      cp package.xml "$capture_package"
      echo '{"status":0,"result":{"id":"0Afxx0000000001AAA"}}'
    else
      : > "$deployed"
      if [ "${FAKE_DEPLOY_PRESERVES_SURFACE:-0}" = "1" ]; then
        printf '%s' "${FAKE_EXIST_ACTIONS:-[]}" | jq -r '.[]' > "$actions"
        printf '%s' "${FAKE_EXIST_TABS:-[]}" | jq -r '.[]' > "$tabs"
      else
        : > "$actions"; : > "$tabs"
      fi
      printf '{"status":0,"result":{"id":"0Afxx0000000001AAA","status":"Succeeded","files":[{"fullName":"%s","type":"OmniSupervisorConfig","state":"Changed"}]}}' "$config_dn"
    fi;;
  "data create")
    printf '%s\n' "$args" >> "$trace"
    if printf '%s' "$args" | grep -q "OmniSupervisorConfigAction"; then
      value=$(printf '%s' "$args" | sed -n 's/.*OmniSupervisorActionType=\([^ ]*\).*/\1/p')
      printf '%s\n' "$value" >> "$actions"
    elif printf '%s' "$args" | grep -q "OmniSupervisorConfigTab"; then
      value=$(printf '%s' "$args" | sed -n 's/.*OmniSupervisorTabType=\([^ ]*\).*/\1/p')
      printf '%s\n' "$value" >> "$tabs"
    fi
    echo '{"status":0,"result":{"id":"0Q3xx0000000001AAA","success":true}}';;
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
        self.root = Path(tempfile.mkdtemp(prefix="supconfig-fake-sf-"))
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
