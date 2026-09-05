#!/usr/bin/env python3
"""Run the Help Agent's non-mutating Agent Script authoring preflight.

The Salesforce CLI has no standalone entitlement-inspection command for the
Agent Script compiler.  The strongest documented check is
``sf agent validate authoring-bundle``.  This helper runs that command against
a fixed, minimal bundle in a temporary DX project, then removes the project.
It never deploys, publishes, activates, creates, updates, or deletes org state.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


CHECKPOINT = "Help Agent — Agentforce authoring capability preflight"
PROBE_API_NAME = "HelpAgentAuthoringPreflight"

# Keep the probe independent of service-agent-only features and org-specific
# users.  A successful compile proves that this org/session can reach and use
# the common Agent Script compiler.  It intentionally does not claim that
# downstream Service Agent, Data Cloud, Knowledge, or channel checks passed.
PROBE_AGENT = """system:
    instructions: "Return a short readiness acknowledgement."
    messages:
        welcome: "Hello."
        error: "Sorry, something went wrong."

config:
    developer_name: "HelpAgentAuthoringPreflight"
    agent_label: "Help Agent Authoring Preflight"
    description: "Non-deploying compiler reachability probe."
    agent_type: "AgentforceEmployeeAgent"

language:
    default_locale: "en_US"

start_agent readiness:
    label: "Readiness"
    description: "Confirms that the Agent Script compiler accepted the probe."
    reasoning:
        instructions: ->
            | Reply that the authoring preflight is ready.
"""

PROBE_METADATA = """<?xml version="1.0" encoding="UTF-8"?>
<AiAuthoringBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <bundleType>AGENT</bundleType>
</AiAuthoringBundle>
"""

LIMITATION = (
    "This probe verifies authentication and direct Agent Script compiler reachability only. "
    "It does not prove Service Agent, Data Cloud, Knowledge, channel, license-seat, or per-user permission readiness."
)

AUTH_PATTERNS = re.compile(
    r"No authorization information|NamedOrgNotFound|not authenticated|INVALID_SESSION_ID|"
    r"InvalidSessionId|expired (?:access|refresh) token|HTTP\s*(?:401|403)|ERROR_HTTP_(?:401|403)|"
    r"Jwt.*(?:invalid|expired|failed)|InvalidJwtToken|does not have access",
    re.IGNORECASE,
)
AUTHORING_UNAVAILABLE_PATTERNS = re.compile(
    r"AgentApiNotFound|ERROR_HTTP_404|Validation/compilation API returned HTTP 404|"
    r"API endpoint may not be available in your org or region",
    re.IGNORECASE,
)
TRANSIENT_PATTERNS = re.compile(
    r"ECONN|ENOTFOUND|ETIMEDOUT|ECONNRESET|socket hang up|timed out|timeout|"
    r"HTTP\s*(?:429|5\d\d)|ERROR_HTTP_(?:429|5\d\d)|ServerError|Service Unavailable|"
    r"Validation/compilation API returned HTTP 500",
    re.IGNORECASE,
)

EXIT_CODES = {
    "ready": 0,
    "authentication_or_org_access_failure": 20,
    "agentforce_authoring_unavailable_or_not_entitled": 21,
    "transient_cli_or_service_failure": 22,
    "capability_cannot_be_conclusively_verified": 23,
}


def _run(args: list[str], *, cwd: Path | None, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=os.environ.copy(),
    )


def _parse_json(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout or ''}\n{result.stderr or ''}".strip()


def _emit(
    outcome: str,
    target_org: str,
    summary: str,
    remediation: str,
) -> int:
    payload = {
        "checkpoint": CHECKPOINT,
        "outcome": outcome,
        "safeToProceed": outcome == "ready",
        "targetOrg": target_org,
        "probe": "sf agent validate authoring-bundle",
        "summary": summary,
        "remediation": remediation,
        "resumeCheckpoint": CHECKPOINT,
        "limitation": LIMITATION,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return EXIT_CODES[outcome]


def _write_probe_project(project_dir: Path) -> None:
    bundle_dir = (
        project_dir
        / "force-app"
        / "main"
        / "default"
        / "aiAuthoringBundles"
        / PROBE_API_NAME
    )
    bundle_dir.mkdir(parents=True)
    (project_dir / "sfdx-project.json").write_text(
        json.dumps({"packageDirectories": [{"path": "force-app", "default": True}]}),
        encoding="utf-8",
    )
    (bundle_dir / f"{PROBE_API_NAME}.agent").write_text(PROBE_AGENT, encoding="utf-8")
    (bundle_dir / f"{PROBE_API_NAME}.bundle-meta.xml").write_text(PROBE_METADATA, encoding="utf-8")


def run_preflight(target_org: str, timeout_seconds: int) -> int:
    if shutil.which("sf") is None:
        return _emit(
            "capability_cannot_be_conclusively_verified",
            target_org,
            "Salesforce CLI is not available, so the selected org could not be checked.",
            "Install or repair the supported Salesforce CLI, then rerun this checkpoint. Do not begin Agentforce authoring yet.",
        )

    try:
        org_result = _run(
            ["sf", "org", "display", "--target-org", target_org, "--json"],
            cwd=None,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _emit(
            "transient_cli_or_service_failure",
            target_org,
            "The Salesforce CLI timed out while checking the selected org.",
            "Retry this checkpoint after CLI or service connectivity recovers; no org state was changed.",
        )
    except OSError:
        return _emit(
            "capability_cannot_be_conclusively_verified",
            target_org,
            "The Salesforce CLI could not be executed, so org access was not verified.",
            "Repair the local Salesforce CLI, then rerun this checkpoint. Do not begin Agentforce authoring yet.",
        )

    if org_result.returncode != 0:
        org_output = _combined_output(org_result)
        if TRANSIENT_PATTERNS.search(org_output):
            return _emit(
                "transient_cli_or_service_failure",
                target_org,
                "The selected org could not be checked because of a transient CLI or service failure.",
                "Retry this checkpoint after connectivity or service health recovers; no org state was changed.",
            )
        if AUTH_PATTERNS.search(org_output):
            return _emit(
                "authentication_or_org_access_failure",
                target_org,
                "The Salesforce CLI could not authenticate to or access the selected org.",
                "Reauthenticate or select an org the current user can access, then rerun this checkpoint.",
            )
        return _emit(
            "capability_cannot_be_conclusively_verified",
            target_org,
            "The selected org check failed without an authoritative authentication or service classification.",
            "Repair or update the Salesforce CLI, confirm the target-org alias, and rerun this checkpoint. Do not infer entitlement from this response.",
        )

    org_json = _parse_json(org_result.stdout)
    if org_json is None or org_json.get("status") not in (0, None) or not isinstance(org_json.get("result"), dict):
        return _emit(
            "capability_cannot_be_conclusively_verified",
            target_org,
            "Org access returned an unexpected response, so authentication could not be verified conclusively.",
            "Repair or update the Salesforce CLI and rerun this checkpoint. Do not infer entitlement from this response.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="helpagent-authoring-preflight-") as temp_dir:
            project_dir = Path(temp_dir)
            _write_probe_project(project_dir)
            validate_result = _run(
                [
                    "sf",
                    "agent",
                    "validate",
                    "authoring-bundle",
                    "--api-name",
                    PROBE_API_NAME,
                    "--target-org",
                    target_org,
                    "--json",
                ],
                cwd=project_dir,
                timeout_seconds=timeout_seconds,
            )
    except subprocess.TimeoutExpired:
        return _emit(
            "transient_cli_or_service_failure",
            target_org,
            "The Agent Script compiler probe timed out.",
            "Retry this checkpoint after CLI or service health recovers; the temporary local probe was removed and no org state was changed.",
        )
    except OSError:
        return _emit(
            "capability_cannot_be_conclusively_verified",
            target_org,
            "The Agent Script compiler probe could not be executed.",
            "Repair or update the Salesforce CLI and rerun this checkpoint. Do not begin Agentforce authoring yet.",
        )

    validate_output = _combined_output(validate_result)
    validate_json = _parse_json(validate_result.stdout)
    result_payload = validate_json.get("result") if validate_json else None
    if (
        validate_result.returncode == 0
        and isinstance(result_payload, dict)
        and result_payload.get("success") is True
    ):
        return _emit(
            "ready",
            target_org,
            "The selected org accepted the fixed non-deploying Agent Script compiler probe.",
            "Continue by delegating Agentforce readiness and authoring to agentforce-adlc:agentforce-generate; still run its downstream feature and permission checks.",
        )

    if AUTH_PATTERNS.search(validate_output):
        return _emit(
            "authentication_or_org_access_failure",
            target_org,
            "Authentication or org access failed while contacting the Agent Script compiler.",
            "Reauthenticate the selected org and confirm the current user can use Agentforce DX, then rerun this checkpoint.",
        )

    if validate_result.returncode == 2 or AUTHORING_UNAVAILABLE_PATTERNS.search(validate_output):
        return _emit(
            "agentforce_authoring_unavailable_or_not_entitled",
            target_org,
            "The Agent Script authoring endpoint returned its documented unavailable response for this org or region.",
            "Ask the Salesforce admin or Support to enable/onboard Agent Script authoring for this org and region, then rerun this checkpoint. Do not treat this 404 as a local CLI or permission-set fix.",
        )

    if TRANSIENT_PATTERNS.search(validate_output) or validate_result.returncode == 3:
        return _emit(
            "transient_cli_or_service_failure",
            target_org,
            "The Agent Script compiler probe failed because of a transient CLI or service condition.",
            "Retry this checkpoint after service health recovers; the temporary local probe was removed and no org state was changed.",
        )

    return _emit(
        "capability_cannot_be_conclusively_verified",
        target_org,
        "The non-deploying compiler probe did not produce an authoritative readiness result.",
        "Update or repair the Salesforce CLI and agentforce-adlc environment, or obtain authoritative org-onboarding confirmation, then rerun this checkpoint. Do not proceed as though entitlement was verified.",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-org", required=True, help="Alias or username of the selected Salesforce org")
    parser.add_argument("--timeout-seconds", type=int, default=60, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")
    return run_preflight(args.target_org, args.timeout_seconds)


if __name__ == "__main__":
    sys.exit(main())
