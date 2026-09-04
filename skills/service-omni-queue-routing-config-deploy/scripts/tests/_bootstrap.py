from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = "service-omni-queue-routing-config-deploy/scripts/upsert-and-report.sh"

_FAKE_SF = r'''#!/usr/bin/env bash
sub="${1:-} ${2:-}"; args="$*"
SANDBOX="${FAKE_SANDBOX:-true}"; TRIAL="${FAKE_TRIAL:-null}"; ORG_TYPE="${FAKE_ORG_TYPE:-Developer Edition}"
B_RM="${FAKE_BEFORE_RM:-MostAvailable}"; B_CW="${FAKE_BEFORE_CW:-5}"; B_CP="${FAKE_BEFORE_CP:-null}"
B_PT="${FAKE_BEFORE_PT:-null}"; B_RP="${FAKE_BEFORE_RP:-1}"; B_ML="${FAKE_BEFORE_ML:-Case Routing Config}"
F_RM="${FAKE_FINAL_RM:-MostAvailable}"; F_CW="${FAKE_FINAL_CW:-5}"; F_CP="${FAKE_FINAL_CP:-null}"
F_PT="${FAKE_FINAL_PT:-null}"; F_RP="${FAKE_FINAL_RP:-1}"; F_ML="${FAKE_FINAL_ML:-Case Routing Config}"
case "$sub" in
  "org display") echo '{"status":0,"result":{"id":"00Dxx0000000000EAA"}}';;
  "data query")
    if printf '%s' "$args" | grep -q "FROM Organization"; then
      printf '{"status":0,"result":{"records":[{"IsSandbox":%s,"TrialExpirationDate":%s,"OrganizationType":"%s"}]}}' "$SANDBOX" "$TRIAL" "$ORG_TYPE"
    elif printf '%s' "$args" | grep -q "FROM User"; then
      echo '{"status":0,"result":{"records":[{"Id":"005000000000001AAA","IsActive":true}],"totalSize":1}}'
    elif printf '%s' "$args" | grep -q "FROM QueueRoutingConfig"; then
      if printf '%s' "$args" | grep -q "WHERE Id="; then
        printf '{"status":0,"result":{"totalSize":1,"records":[{"Id":"0Jrxx0000000001","DeveloperName":"Case_Routing_Config","MasterLabel":"%s","RoutingModel":"%s","RoutingPriority":%s,"IsAttributeBased":false,"CapacityWeight":%s,"CapacityPercentage":%s,"PushTimeout":%s,"OverflowAssigneeId":null}]}}' "$F_ML" "$F_RM" "$F_RP" "$F_CW" "$F_CP" "$F_PT"
      elif [ "${FAKE_EXISTING:-0}" = "1" ]; then
        printf '{"status":0,"result":{"totalSize":1,"records":[{"Id":"0Jrxx0000000001","DeveloperName":"Case_Routing_Config","MasterLabel":"%s","RoutingModel":"%s","RoutingPriority":%s,"IsAttributeBased":false,"CapacityWeight":%s,"CapacityPercentage":%s,"PushTimeout":%s,"OverflowAssigneeId":null}]}}' "$B_ML" "$B_RM" "$B_RP" "$B_CW" "$B_CP" "$B_PT"
      else
        echo '{"status":0,"result":{"records":[],"totalSize":0}}'
      fi
    else echo '{"status":0,"result":{"records":[],"totalSize":0}}'; fi;;
  "api request")
    if printf '%s' "$args" | grep -q "method POST"; then
      echo '{"id":"0Jrxx0000000001","success":true,"errors":[]}'
    else echo ''; fi;;
  *) echo '{"status":0,"result":{}}';;
esac
'''


def run(args, path_prefix=None, scrub_sf=False, extra_env=None):
    env = dict(os.environ)
    if scrub_sf:
        env["PATH"] = os.pathsep.join(d for d in env.get("PATH", "").split(os.pathsep)
                                      if d and not os.path.exists(os.path.join(d, "sf")))
    if path_prefix:
        env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
    if extra_env:
        env.update({key: str(value) for key, value in extra_env.items()})
    proc = subprocess.run(["bash", str(SKILLS_ROOT / SCRIPT), *args], capture_output=True,
                          text=True, env=env, cwd=str(SKILLS_ROOT))
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def last_json(out: str) -> dict:
    decoder = json.JSONDecoder()
    result, index = None, 0
    while index < len(out):
        if out[index] not in "{[":
            index += 1
            continue
        try:
            candidate, end = decoder.raw_decode(out, index)
            if isinstance(candidate, dict):
                result = candidate
            index = end
        except json.JSONDecodeError:
            index += 1
    assert result is not None, out
    return result


class FakeSf:
    def __init__(self, body=_FAKE_SF):
        self.body = body
        self.tmp = None

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="qrc-fake-sf-")
        executable = Path(self.tmp) / "sf"
        executable.write_text(self.body)
        executable.chmod(0o755)
        return self.tmp

    def __exit__(self, *_):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
