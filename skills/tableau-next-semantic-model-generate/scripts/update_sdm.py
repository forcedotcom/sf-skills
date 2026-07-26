#!/usr/bin/env python3
"""Make an existing Semantic Data Model AI-ready (model-level update).

Flips an existing SDM to agent-queryable: set ``agentEnabled``, a structured
``businessPreferences`` context block (from a file), a ``description``, and
``categories``. This is a PATCH (partial body) — only the flags you pass are
sent; the server merges them onto the existing model (see
references/sdm-ai-readiness-api.md §1). Idempotent: re-running with the same
inputs sends the same payload.

This script only UPDATES an existing SDM. Creating SDMs / data objects /
relationships is out of scope (use create_sdm.py / add_*.py).

Usage:
    # Flip a model AI-ready with a businessPreferences block from a file
    python scripts/update_sdm.py Workforce_SDM \\
      --agent-enabled \\
      --description "Workforce model: headcount, hires, leavers by org." \\
      --business-preferences-file ./workforce_bp.txt \\
      --categories "HR,People"

    # Dry-run (print the PATCH payload, no network call)
    python scripts/update_sdm.py Workforce_SDM --agent-enabled --dry-run

The ``description`` is capped at 255 characters (raw input length). The server
HTML-encodes the value for storage but measures the limit against what you send,
so this guard rejects ``len(description) > 255`` BEFORE the API does — put the
depth in ``businessPreferences`` (no length limit observed) instead.
"""

import argparse
import json
import sys
from typing import Optional

from _shared.sdm_ai_templates import build_model_ai_payload
from _shared.sf_api import (
    get_credentials,
    parse_too_large_error,
    sdm_update_endpoint,
    sf_patch,
)

# The server caps `description` at 255 chars, measured on the RAW input (it
# HTML-encodes for storage but checks what you send — see
# references/sdm-ai-readiness-api.md §2).
DESCRIPTION_MAX_LEN = 255

# Where to put depth that doesn't fit the 255-char description.
_BP_HINT = (
    " Shorten it and move depth into --business-preferences-file (no observed "
    "length limit) — that is the right home for the model's PURPOSE / GRAIN & "
    "JOINS / KEY DEFINITIONS / SYNONYMS / DATA CAVEATS / PREFERRED MEASURES context."
)


def explain_too_large_error(err: str) -> Optional[str]:
    """Translate the server's 'data value too large' 400 into actionable guidance.

    Returns a friendly message (naming the offending field + the max length, and
    pointing depth at businessPreferences) when ``err`` is a length-cap
    rejection, else None so the caller falls back to the raw error.
    """
    parsed = parse_too_large_error(err)
    if parsed is None:
        return None
    field, max_len = parsed
    if field is None:
        # Generic phrase without a parsed field/length.
        return (
            "The server rejected the update: a field value is too long (the "
            "model `description` caps at 255 characters, measured on the raw "
            "input)." + _BP_HINT
        )
    suffix = _BP_HINT if field.lower() == "description" else ""
    return (
        f"The server rejected the update: '{field}' exceeds its maximum length "
        f"of {max_len} characters (measured on the raw input).{suffix}"
    )


def check_description_length(description: str) -> Optional[str]:
    """Return an actionable error if a description exceeds the raw 255-char cap.

    Measures the RAW input length (NOT the HTML-encoded length): the server
    HTML-encodes for storage but enforces the 255 limit against the input. So we
    must not encode before measuring — that would over-reject legitimate
    ``&``-containing descriptions the server accepts. Returns None if OK.
    """
    n = len(description)
    if n > DESCRIPTION_MAX_LEN:
        return (
            f"description is {n} characters; the server caps it at "
            f"{DESCRIPTION_MAX_LEN} (measured on the raw input). Shorten it and "
            f"move the depth into --business-preferences-file, which has no "
            f"observed length limit and is the right home for the model's "
            f"PURPOSE / GRAIN & JOINS / KEY DEFINITIONS / SYNONYMS / DATA "
            f"CAVEATS / PREFERRED MEASURES context."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Make an existing SDM AI-ready (agentEnabled + businessPreferences + description + categories).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("sdm", help="SDM apiName to update (must already exist)")
    parser.add_argument(
        "--agent-enabled", dest="agent_enabled", action="store_true", default=None,
        help="Set agentEnabled=true (expose the model to the AI agent).",
    )
    parser.add_argument(
        "--no-agent-enabled", dest="agent_enabled", action="store_false",
        help="Set agentEnabled=false (hide the model from the agent).",
    )
    parser.add_argument("--description", help="Model description (<=255 raw chars).")
    parser.add_argument(
        "--business-preferences-file",
        help="Path to a file whose contents become businessPreferences (the AI "
             "context block: PURPOSE/GRAIN & JOINS/KEY DEFINITIONS/SYNONYMS/DATA "
             "CAVEATS/PREFERRED MEASURES).",
    )
    parser.add_argument(
        "--categories",
        help="Comma-separated category labels (stored as a JSON array). NOTE: "
             "these are controlled 'Semantic Category' values, not free-form "
             "text — the server rejects unknown values (Invalid Semantic "
             "Category). Pass an empty string to clear (sets []).",
    )
    parser.add_argument("--label", help="Update the model display label.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the PATCH payload and exit without calling the org.")
    args = parser.parse_args()

    # Resolve businessPreferences from file (read up front so a bad path fails fast).
    business_preferences = None
    if args.business_preferences_file:
        try:
            with open(args.business_preferences_file, "r", encoding="utf-8") as fh:
                business_preferences = fh.read()
        except OSError as exc:
            print(f"Error: cannot read --business-preferences-file: {exc}", file=sys.stderr)
            return 1

    # Client-side description guard (reject before the API does).
    if args.description is not None:
        err = check_description_length(args.description)
        if err:
            print(f"Error: {err}", file=sys.stderr)
            return 1

    # Categories: comma string -> list. "" -> [] (explicit clear).
    categories = None
    if args.categories is not None:
        categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    # Assemble the partial PATCH body (only the fields the user set).
    from _shared.sdm_ai_templates import _UNSET  # sentinel for "not provided"
    try:
        payload = build_model_ai_payload(
            agent_enabled=args.agent_enabled if args.agent_enabled is not None else _UNSET,
            description=args.description if args.description is not None else _UNSET,
            business_preferences=business_preferences if business_preferences is not None else _UNSET,
            categories=categories if categories is not None else _UNSET,
            label=args.label if args.label is not None else _UNSET,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Provide at least one of --agent-enabled/--no-agent-enabled, "
            "--description, --business-preferences-file, --categories, --label.",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not PATCHed]", file=sys.stderr)
        return 0

    # PATCH the model.
    token, instance = get_credentials()
    resp, err = sf_patch(token, instance, sdm_update_endpoint(args.sdm), payload)
    if err:
        # Catch the server's length-cap rejection and re-surface it as actionable
        # guidance (the client-side guard pre-checks --description, but this
        # backstops any field the server caps).
        friendly = explain_too_large_error(err)
        if friendly:
            print(f"Error: {friendly}", file=sys.stderr)
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"\n✓ Updated SDM: {args.sdm}", file=sys.stderr)
    if isinstance(resp, dict):
        if "agentEnabled" in resp:
            print(f"  agentEnabled: {resp['agentEnabled']}", file=sys.stderr)
        if resp.get("businessPreferences"):
            print("  businessPreferences: set", file=sys.stderr)
    # Confirm actual state, not just the success code — discovery is the proof.
    print(
        f"  Verify with: python scripts/discover_sdm.py {args.sdm} "
        f"(check agentEnabled + businessPreferences).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
