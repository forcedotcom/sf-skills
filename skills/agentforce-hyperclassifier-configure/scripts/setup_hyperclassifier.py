#!/usr/bin/env python3
"""Onboard a customer org using its CLI alias and a dedicated or supplied ECA."""

import argparse
import json
from pathlib import Path
import sys

from hcopt.eca import deploy_eca, prepare_eca
from hcopt.onboarding import (APP_NAME, discover_eca, discover_orgs, initialize_workspace,
                             read_org_session, resolve_org, save_credentials, workspace_path)


def main(argv=None):
    """Inspect org access, prepare/review an ECA, and store private credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("orgs", "inspect", "configure", "prepare-eca", "deploy-eca"))
    parser.add_argument("--target-org", help="CLI alias or username; omission uses the configured default org")
    parser.add_argument("--workspace", type=Path, help="Private state directory; default is per-org under ~/.config")
    parser.add_argument("--env-file", type=Path, help="Existing private ECA credentials to import, never print")
    parser.add_argument("--contact-email")
    parser.add_argument("--run-as", help="Exact active username; omission uses the resolved CLI user with a warning")
    parser.add_argument("--app-name", default=APP_NAME)
    parser.add_argument("--check-session-token", action="store_true", help="Check availability without printing the token")
    parser.add_argument("--apply", action="store_true", help="Apply the prepared ECA plan after user authorization")
    args = parser.parse_args(argv)
    try:
        if args.command == "orgs":
            print(json.dumps(discover_orgs(), indent=2))
            return 0
        org = resolve_org(args.target_org)
        path = workspace_path(org, args.workspace)
        if args.command == "inspect":
            apps = discover_eca(org, args.app_name)
            result = {"org": org, "ecas": apps, "workspace": str(path),
                      "credentials_saved": (path / "credentials.env").is_file(),
                      "next_step": "reuse_or_supply_eca_credentials" if apps else "ask_for_existing_eca_credentials_or_create_eca",
                      "cli_session_is_gateway_auth": False}
            if args.check_session_token:
                result["session_token_available"] = bool(read_org_session(org["alias"]))
            print(json.dumps(result, indent=2))
            return 0
        initialize_workspace(org, path)
        if args.command == "configure":
            apps = discover_eca(org, args.app_name)
            destination = save_credentials(org, path, args.env_file)
            print(json.dumps({"credentials_saved": str(destination), "ecas_found": len(apps),
                              "next_step": "run_preflight_to_verify_OrgJWT_and_model_access"}))
        elif args.command == "prepare-eca":
            run_as = args.run_as or org["username"]
            warnings = []
            if not args.run_as:
                warning = (f"--run-as was omitted or empty; using CLI user {run_as!r} as the Run As user. "
                           "Client-credentials requests will use this user's permissions. Prefer a dedicated "
                           "integration user with least privileges; pass --run-as <username> to select it explicitly.")
                warnings.append(warning)
                print(f"Warning: {warning}", file=sys.stderr)
            plan = prepare_eca(org, path, args.contact_email, run_as, args.app_name)
            print(json.dumps({"plan": plan, "project": str(path / "eca"), "deployed": False,
                              "warnings": warnings}, indent=2))
        elif not args.apply:
            print((path / "eca/plan.json").read_text(encoding="utf-8"))
            print("Review this plan. Use --apply only when ECA creation in this org is authorized.")
        else:
            print(json.dumps(deploy_eca(org, path), indent=2))
            print("Retrieve Consumer Key and Secret privately in Setup, then run configure.")
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
