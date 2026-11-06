"""Discover customer orgs and ECAs through CLI auth, keeping tokens out of output."""

import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .client import load_credentials, my_domain_origin
from .evaluation import write_json


APP_LABEL = "agentforce-hyperclassifier-optimize"
APP_NAME = "agentforce_hyperclassifier_optimize"


def deployment_details(result):
    """Keep only a validated job handle and known status, never raw CLI output."""
    if not isinstance(result, dict):
        return {}
    details = {}
    job = result.get("id")
    if isinstance(job, str) and re.fullmatch(r"0Af[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?", job):
        details["deployment_id"] = job
    status = result.get("status")
    if status in ("Pending", "InProgress", "Succeeded", "SucceededPartial", "Failed", "Canceled", "Canceling"):
        details["status"] = status
    return details


class CLIError(ValueError):
    """A sanitized CLI failure with optional deployment recovery metadata."""

    def __init__(self, message, deployment=None):
        super().__init__(message)
        self.deployment = deployment or {}


def sf(arguments, cwd=None, timeout=300):
    """Capture CLI JSON privately; never echo raw CLI output containing credentials."""
    executable = shutil.which("sf")
    if not executable:
        raise ValueError("Salesforce CLI is required for onboarding; install sf and log in to the customer org")
    environment = dict(os.environ, SF_DISABLE_LOG_FILE="true", SF_DISABLE_TELEMETRY="true",
                       SFDX_DISABLE_TELEMETRY="true")
    try:
        process = subprocess.run([executable, *arguments, "--json"], cwd=cwd, env=environment,
                                 capture_output=True, text=True, timeout=timeout)
        data = json.loads(process.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise ValueError("Salesforce CLI failed, timed out or returned invalid JSON; no CLI output was logged") from None
    if not isinstance(data, dict) or process.returncode or data.get("status", 0):
        code = data.get("name", "CLI_ERROR") if isinstance(data, dict) else "CLI_ERROR"
        code = code if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_]+", code) else "CLI_ERROR"
        deployment = deployment_details(data.get("result")) if (
            isinstance(data, dict) and arguments[:3] == ["project", "deploy", "start"]) else {}
        raise CLIError(f"Salesforce CLI failed ({code}); check login, permissions and command availability", deployment)
    return data.get("result")


def discover_orgs():
    """List locally authenticated org identities without exposing stored tokens."""
    records = sf(["org", "list", "auth"])
    if not isinstance(records, list):
        raise ValueError("Unexpected org list response")
    keys = ("alias", "username", "orgId", "instanceUrl", "isSandbox", "isExpired")
    return [{key: row.get(key) for key in keys} for row in records]


def resolve_org(target=None):
    """Resolve an explicit alias or the CLI default and discard credential fields."""
    arguments = ["org", "display"] + (["--target-org", target] if target else [])
    result = sf(arguments)
    if not isinstance(result, dict):
        raise ValueError("Unexpected org display response")
    org = {"org_id": result.get("id"), "username": result.get("username"),
           "alias": result.get("alias") or target or result.get("username"),
           "instance_url": result.get("instanceUrl", "").rstrip("/"),
           "api_version": result.get("apiVersion", "68.0")}
    if not re.fullmatch(r"00D[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?", org.get("org_id") or ""):
        raise ValueError("CLI did not resolve a valid customer org identity")
    my_domain_origin(org["instance_url"])
    if not re.fullmatch(r"[0-9]{2,3}\.0", str(org["api_version"])):
        raise ValueError("Unexpected org API version")
    return org


def read_org_session(target):
    """Retrieve a CLI session token for org administration only, never inference."""
    result = sf(["org", "display", "--target-org", target])
    token = result.get("accessToken") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token.strip() or token.lstrip().upper().startswith("[REDACTED]"):
        # Newer CLIs separate secret output from the ordinary org display command.
        result = sf(["org", "auth", "show-access-token", "--target-org", target])
        token = result.get("accessToken") if isinstance(result, dict) else None
    if (not isinstance(token, str) or not token.strip()
            or token.lstrip().upper().startswith("[REDACTED]")):
        raise ValueError("No CLI session token available; log in to the customer org again")
    return token


def discover_eca(org, app_name=APP_NAME):
    """Use the CLI's customer-org session to query ECA identities through Tooling API."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", app_name):
        raise ValueError("Invalid ECA API name")
    # sf performs the authenticated Tooling API call with its org session token.
    # The session token never enters Client, which mints a separate ECA OrgJWT.
    query = ("SELECT Id, DeveloperName, MasterLabel FROM ExternalClientApplication "
             f"WHERE DeveloperName = '{app_name}' OR MasterLabel = '{APP_LABEL}'")
    result = sf(["data", "query", "--target-org", org["alias"], "--use-tooling-api", "--query", query])
    records = result.get("records") if isinstance(result, dict) else None
    if not isinstance(records, list):
        raise ValueError("Unexpected ECA discovery response; do not assume the app is absent")
    return [{key: record.get(key) for key in ("Id", "DeveloperName", "MasterLabel")} for record in records]


def workspace_path(org, override=None):
    """Keep reusable org configuration outside the skill and customer source trees."""
    return Path(override).expanduser().resolve() if override else (
        Path.home() / ".config" / "agentforce-hyperclassifier-optimize" / org["org_id"])


def initialize_workspace(org, path):
    """Bind a private workspace to one org and reject accidental cross-org reuse."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Workspace must not be a symlink")
    if path.exists() and not (path / "profile.json").exists() and any(path.iterdir()):
        raise ValueError("Choose an empty private workspace, not an existing project directory")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)
    profile_path = path / "profile.json"
    if profile_path.exists():
        old = json.loads(profile_path.read_text(encoding="utf-8"))
        if old.get("org_id") != org["org_id"]:
            raise ValueError("Workspace belongs to a different org")
    write_json(profile_path, org)
    return path


def save_credentials(org, workspace, source=None):
    """Import a private file or securely prompt for ECA credentials without echoing them."""
    destination = Path(workspace) / "credentials.env"
    if destination.exists():
        raise ValueError("Credentials already saved; reuse them or explicitly back up and rotate them")
    if source:
        values = load_credentials(source)
    else:
        if not sys.stdin.isatty():
            raise ValueError("No interactive terminal; save ECA details in a private file and use --env-file")
        values = {"SF_INSTANCE_URL": org["instance_url"],
                  "SF_CLIENT_ID": getpass.getpass("ECA Consumer Key (hidden): "),
                  "SF_CLIENT_SECRET": getpass.getpass("ECA Consumer Secret (hidden): ")}
    if values["SF_INSTANCE_URL"] != org["instance_url"]:
        raise ValueError("ECA credentials belong to a different org origin")
    if any(not value or "\n" in value or "\r" in value for value in values.values()):
        raise ValueError("Credential values must be nonempty single-line values")
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("\n".join(key + "=" + value for key, value in values.items()) + "\n")
    return destination


def credentials_for_run(args):
    """Load credentials explicitly or find the org-bound onboarding workspace."""
    org = resolve_org(args.target_org) if args.target_org else None
    if args.env_file:
        values = load_credentials(args.env_file)
    elif args.workspace:
        workspace = workspace_path(org, args.workspace)
        profile = json.loads((workspace / "profile.json").read_text(encoding="utf-8"))
        if org and profile.get("org_id") != org["org_id"]:
            raise ValueError("Selected org and workspace do not match")
        values = load_credentials(workspace / "credentials.env")
        if values["SF_INSTANCE_URL"] != profile.get("instance_url"):
            raise ValueError("Saved credentials and workspace org do not match")
    elif all(os.environ.get(key) for key in ("SF_INSTANCE_URL", "SF_CLIENT_ID", "SF_CLIENT_SECRET")):
        values = load_credentials()
    else:
        org = org or resolve_org()
        path = workspace_path(org)
        if not (path / "credentials.env").is_file():
            raise ValueError("ECA onboarding required: run setup_hyperclassifier.py inspect for this org")
        values = load_credentials(path / "credentials.env")
    if org and values["SF_INSTANCE_URL"] != org["instance_url"]:
        raise ValueError("Selected org and ECA credentials do not match")
    return values
