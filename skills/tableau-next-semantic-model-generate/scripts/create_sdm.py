#!/usr/bin/env python3
"""Create a Semantic Data Model with a single anchor data object.

Builds an SDM on an existing DLO/DMO/CIO (the data object must already exist —
DMO/DLO creation is out of scope). Creates with ONE anchor object to dodge the
bulk-create timeout; add further objects with add_data_object.py and joins with
add_relationship.py.

Usage:
    # DMO-backed anchor (preferred when a DMO exists)
    python scripts/create_sdm.py \\
      --api-name Sales_Cloud_SDM \\
      --label "Sales Cloud SDM" \\
      --data-object qb_hw_employee__dlm \\
      --workspace HR_Workforce

    # DLO-direct anchor, explicit object apiName, no auto-bind
    python scripts/create_sdm.py \\
      --api-name Orders_SDM --label "Orders SDM" \\
      --data-object orders__dll --object-api-name Orders \\
      --no-include-all-fields --workspace Sales_Cloud

    # Dry-run (print payload, no POST)
    python scripts/create_sdm.py \\
      --api-name Demo_SDM --label "Demo SDM" \\
      --data-object accounts__dlm --dry-run

After a successful create the script resolves the server-stored (suffixed)
field apiNames — copy those into add_relationship.py join keys. On a bulk-create
timeout it does NOT blind-retry (that hits "Unique constraint violated"); it
waits then lists to confirm persistence.
"""

import argparse
import json
import sys
import time
from typing import Optional

from _shared.sdm_discovery import extract_object_field_apinames
from _shared.sdm_structure_templates import (
    build_create_sdm,
    build_data_object,
    infer_data_object_type,
    validate_data_object_name,
    validate_sdm_api_name,
)
from _shared.sf_api import (
    get_credentials,
    sdm_create_endpoint,
    sdm_detail_endpoint,
    sdm_list_endpoint,
    sf_get,
    sf_post,
    workspace_endpoint,
)

# How long to wait before confirming persistence on a bulk-create timeout.
TIMEOUT_RECOVERY_WAIT_SECONDS = 30


def confirm_persisted_after_timeout(
    token: str, instance: str, api_name: str,
    wait_seconds: int = TIMEOUT_RECOVERY_WAIT_SECONDS,
) -> bool:
    """Recovery path for the bulk-create timeout: wait, then LIST to confirm.

    A create with many objects can return a generic timeout even though the SDM
    persists ~10-30s later. A naive re-POST then hits "Unique constraint
    violated". So we wait and check the model list instead of re-POSTing.

    Returns True if the SDM is found persisted.
    """
    print(
        f"\n⚠ Create timed out. The SDM may still have persisted. Waiting "
        f"{wait_seconds}s then confirming via list (NOT re-POSTing — a retry "
        f"would hit 'Unique constraint violated')...",
        file=sys.stderr,
    )
    time.sleep(wait_seconds)
    data = sf_get(token, instance, sdm_list_endpoint())
    models = (data or {}).get("semantic_models") or (data or {}).get("items") or []
    for m in models:
        if m.get("apiName") == api_name:
            print(f"✓ Confirmed: SDM '{api_name}' persisted despite the timeout.", file=sys.stderr)
            return True
    print(
        f"✗ SDM '{api_name}' not found after waiting. It may need more time — "
        f"re-run `discover_sdm.py --list` shortly before retrying the create.",
        file=sys.stderr,
    )
    return False


def register_in_workspace(
    token: str, instance: str, workspace: str, sdm_id: str,
) -> Optional[str]:
    """Register the SDM as a Referenced SemanticModel asset in a workspace.

    The assets endpoint takes exactly {assetId, assetType, assetUsageType} —
    the assetId is the SDM's server id (NOT its apiName), and `name`/`label` are
    rejected ('Unrecognized field "name"'). Returns an error string on failure,
    None on success.
    """
    payload = {
        "assetId": sdm_id,
        "assetType": "SemanticModel",
        "assetUsageType": "Referenced",
    }
    path = f"{workspace_endpoint(workspace)}/assets"
    _, err = sf_post(token, instance, path, payload)
    return err


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Semantic Data Model with a single anchor data object.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-name", required=True, help="SDM apiName (letter-led, no spaces/__/trailing _)")
    parser.add_argument("--label", required=True, help="SDM display label")
    parser.add_argument(
        "--data-object", required=True,
        help="Source data object name with type suffix (__dll DLO / __dlm DMO / __dlc CIO)",
    )
    parser.add_argument(
        "--object-api-name",
        help="SDM-level apiName for the anchor object (default: source name without suffix)",
    )
    parser.add_argument("--object-label", help="Anchor object display label (default: object apiName)")
    parser.add_argument(
        "--object-type", choices=["Dlo", "Dmo", "Cio"],
        help="dataObjectType (default: inferred from the source-name suffix)",
    )
    parser.add_argument("--dataspace", default="default", help="Dataspace (default: default)")
    parser.add_argument("--description", default="", help="Optional SDM description")
    parser.add_argument(
        "--no-include-all-fields", action="store_true",
        help="Do NOT auto-bind every source column (shouldIncludeAllFields=false). "
             "Auto-bind suffixes every apiName; use base-field adds for controlled names.",
    )
    parser.add_argument(
        "--workspace",
        help="Workspace apiName to register the new SDM in (required unless --skip-workspace)",
    )
    parser.add_argument(
        "--skip-workspace", action="store_true",
        help="Skip workspace registration (the SDM still exists but isn't surfaced in a workspace)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the payload without POSTing")
    args = parser.parse_args()

    # 1. apiName regex (clear, client-side — names the apiName, not the misleading server msg).
    ok, err = validate_sdm_api_name(args.api_name)
    if not ok:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # 2. Source data-object suffix.
    ok, err = validate_data_object_name(args.data_object)
    if not ok:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # 3. Require an explicit workspace decision (don't infer one).
    if not args.dry_run and not args.workspace and not args.skip_workspace:
        print(
            "Error: provide --workspace <apiName> to register the SDM, or "
            "--skip-workspace to skip registration explicitly.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Default the object apiName to the source name without its suffix.
    object_api_name = args.object_api_name
    if not object_api_name:
        object_api_name = args.data_object
        for suffix in ("__dll", "__dlm", "__dlc"):
            if object_api_name.endswith(suffix):
                object_api_name = object_api_name[: -len(suffix)]
                break

    anchor = build_data_object(
        api_name=object_api_name,
        data_object_name=args.data_object,
        label=args.object_label or object_api_name,
        data_object_type=args.object_type or infer_data_object_type(args.data_object),
        should_include_all_fields=not args.no_include_all_fields,
    )
    payload = build_create_sdm(
        api_name=args.api_name,
        label=args.label,
        anchor=anchor,
        dataspace=args.dataspace,
        description=args.description,
    )

    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not POSTed]", file=sys.stderr)
        return

    # POST create.
    token, instance = get_credentials()
    resp, err = sf_post(token, instance, sdm_create_endpoint(), payload)

    if err:
        if "timed out" in err.lower() or "timeout" in err.lower():
            if confirm_persisted_after_timeout(token, instance, args.api_name):
                resp = sf_get(token, instance, sdm_detail_endpoint(args.api_name))
            else:
                sys.exit(1)
        else:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

    if not resp:
        print("✗ Create returned no body.", file=sys.stderr)
        sys.exit(1)

    actual_name = resp.get("apiName", args.api_name)
    sdm_id = resp.get("id", "")
    print(f"\n✓ Created SDM: {actual_name}", file=sys.stderr)

    # Resolve the server-stored (suffixed) field apiNames.
    field_map = extract_object_field_apinames(resp)
    if field_map:
        print("\nStored field apiNames (use these as join keys — never guess the suffix):", file=sys.stderr)
        for obj, fields in field_map.items():
            print(f"  {obj}:", file=sys.stderr)
            if fields["dimensions"]:
                print(f"    dimensions: {', '.join(fields['dimensions'])}", file=sys.stderr)
            if fields["measures"]:
                print(f"    measures:   {', '.join(fields['measures'])}", file=sys.stderr)

    # Register in a workspace (explicit; not inferred).
    if args.workspace:
        ws_err = register_in_workspace(token, instance, args.workspace, sdm_id)
        if ws_err:
            print(f"\n⚠ SDM created but workspace registration failed: {ws_err}", file=sys.stderr)
            print(f"  Register manually in workspace '{args.workspace}'.", file=sys.stderr)
        else:
            print(f"\n✓ Registered SDM in workspace '{args.workspace}'", file=sys.stderr)
    elif args.skip_workspace:
        print("\n(Skipped workspace registration per --skip-workspace.)", file=sys.stderr)


if __name__ == "__main__":
    main()
