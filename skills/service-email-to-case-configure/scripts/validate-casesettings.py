#!/usr/bin/env python3
"""Validate a CaseSettings source file for headless Email-to-Case configuration.

This file is the input to apply-casesettings.py, which supplies the routing
emails (via --routing-email) and resolves the default case owner at apply time.
So the source file must NOT carry emailAddress, and the owner fields are optional.

Checks structural rules that must hold before applying:
  - Well-formed XML with the CaseSettings root and correct namespace.
  - defaultCaseOwnerType, if present, is User or Queue.
  - useSystemUserAsDefaultCaseUser, if present, is boolean, and is not combined
    with a named defaultCaseUser (mutually exclusive at the platform layer).
  - emailToCase enables both enableEmailToCase and enableOnDemandEmailToCase.
  - Each routingAddresses has addressType, routingName, caseOrigin, casePriority.
  - If a routingAddresses sets caseOwner, it also sets caseOwnerType (User or
    Queue) — the platform rejects caseOwner without it — and neither is left as
    an unfilled {PLACEHOLDER}.
  - emailAddress is NOT set in the file (it is supplied via --routing-email).
  - addressType is not E2cEasy (must use the Service Easy Setup wizard).
  - Read-only fields (emailServicesAddress, isVerified) are not set.
  - Enum values for overEmailLimitAction / unauthorizedSenderAction are valid.

Usage: python3 validate-casesettings.py <path-to-file>   (--help for this text)
Exits non-zero and prints ERROR lines to stderr if any check fails.
"""
import sys
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
Q = f"{{{NS}}}"

VALID_ADDRESS_TYPES = {"EmailToCase", "Outlook", "GmailOAuth"}
VALID_OWNER_TYPES = {"User", "Queue"}
OVER_LIMIT_ACTIONS = {"Bounce", "Discard", "Requeue"}
UNAUTHORIZED_ACTIONS = {"Bounce", "Discard"}
READONLY_FIELDS = {"emailServicesAddress", "isVerified"}

# Boolean toggles that must be "true"/"false" when present. Split by container
# so a field placed in the wrong section is flagged.
TOP_LEVEL_BOOL_TOGGLES = {"enableDraftEmails"}
EMAIL_TO_CASE_BOOL_TOGGLES = {
    "enableEmailToCase", "enableOnDemandEmailToCase", "enableHtmlEmail",
    "notifyOwnerOnNewCaseEmail", "enableE2CDeduplicateAttachments",
    "showWordCountInComposer",
}


def local(tag):
    return tag.split("}", 1)[-1]


def child_text(parent, name):
    el = parent.find(f"{Q}{name}")
    return el.text.strip() if el is not None and el.text else None


def is_placeholder(value):
    """A value left as an unfilled template token, e.g. {CASE_OWNER_...}."""
    return bool(value) and value.startswith("{") and value.endswith("}")


def validate(path):
    errors = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"XML is not well-formed: {exc}"]
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    root = tree.getroot()
    if local(root.tag) != "CaseSettings":
        errors.append(f"Root element must be CaseSettings, found '{local(root.tag)}'.")
    if not root.tag.startswith(Q):
        errors.append(f"Root must use namespace '{NS}'.")

    # CaseSettings-level Support-Settings owner / automated-user fields are
    # OPTIONAL in the source file — apply-casesettings.py preserves existing org
    # settings, or takes explicit values (validated against the org) when they
    # are not configured. Here we only enforce the structural rules that hold
    # regardless of the org.
    owner_type = child_text(root, "defaultCaseOwnerType")
    if owner_type and owner_type not in {"User", "Queue"}:
        errors.append(f"defaultCaseOwnerType must be 'User' or 'Queue', found '{owner_type}'.")

    # Default Case Owner is a paired field: the platform rejects defaultCaseOwner
    # without defaultCaseOwnerType, and defaultCaseOwnerType without a value is a
    # half-filled owner. Enforce both directions (mirrors the per-address rule).
    owner_value = child_text(root, "defaultCaseOwner")
    if owner_value is not None and owner_type is None:
        errors.append(
            "defaultCaseOwner is set without defaultCaseOwnerType — the platform "
            "requires defaultCaseOwnerType ('User' or 'Queue') whenever "
            "defaultCaseOwner is set. Add defaultCaseOwnerType, or remove "
            "defaultCaseOwner to use the org Default Case Owner.")
    if owner_type is not None and owner_value is None:
        errors.append(
            "defaultCaseOwnerType is set without defaultCaseOwner — either add a "
            "defaultCaseOwner value (active Username or Queue DeveloperName) or "
            "remove defaultCaseOwnerType.")

    # Automated Case User: 'System' (useSystemUserAsDefaultCaseUser=true) and a
    # named defaultCaseUser are mutually exclusive at the platform layer.
    use_system = child_text(root, "useSystemUserAsDefaultCaseUser")
    if use_system is not None and use_system not in {"true", "false"}:
        errors.append(
            f"useSystemUserAsDefaultCaseUser must be 'true' or 'false', "
            f"found '{use_system}'.")
    if use_system == "true" and child_text(root, "defaultCaseUser") is not None:
        errors.append(
            "useSystemUserAsDefaultCaseUser is 'true' but defaultCaseUser is "
            "also set — they are mutually exclusive. For a System automated "
            "case user, omit defaultCaseUser (optionally set systemUserEmail).")

    # Top-level Support-Settings boolean toggles (e.g. enableDraftEmails).
    for field in TOP_LEVEL_BOOL_TOGGLES:
        val = child_text(root, field)
        if val is not None and val not in {"true", "false"}:
            errors.append(f"{field} must be 'true' or 'false', found '{val}'.")

    e2c = root.find(f"{Q}emailToCase")
    if e2c is None:
        errors.append("Missing <emailToCase> block.")
        return errors

    if child_text(e2c, "enableEmailToCase") != "true":
        errors.append("emailToCase.enableEmailToCase must be 'true'.")
    if child_text(e2c, "enableOnDemandEmailToCase") != "true":
        errors.append(
            "emailToCase.enableOnDemandEmailToCase must be 'true' "
            "before routing addresses can be created."
        )

    # emailToCase section boolean toggles (enableHtmlEmail, etc.).
    for field in EMAIL_TO_CASE_BOOL_TOGGLES:
        val = child_text(e2c, field)
        if val is not None and val not in {"true", "false"}:
            errors.append(f"emailToCase.{field} must be 'true' or 'false', found '{val}'.")

    over = child_text(e2c, "overEmailLimitAction")
    if over and over not in OVER_LIMIT_ACTIONS:
        errors.append(f"overEmailLimitAction must be one of {sorted(OVER_LIMIT_ACTIONS)}, found '{over}'.")
    unauth = child_text(e2c, "unauthorizedSenderAction")
    if unauth and unauth not in UNAUTHORIZED_ACTIONS:
        errors.append(f"unauthorizedSenderAction must be one of {sorted(UNAUTHORIZED_ACTIONS)}, found '{unauth}'.")

    addresses = e2c.findall(f"{Q}routingAddresses")
    if not addresses:
        errors.append("No <routingAddresses> found — at least one is expected.")
    seen_names = set()
    for i, addr in enumerate(addresses, 1):
        label = f"routingAddresses[{i}]"
        for field in ("addressType", "routingName", "caseOrigin", "casePriority"):
            if not child_text(addr, field):
                errors.append(f"{label} missing required field '{field}'.")
        atype = child_text(addr, "addressType")
        if atype == "E2cEasy":
            errors.append(
                f"{label} uses addressType 'E2cEasy', which is not supported via Metadata API — "
                "use the Service Easy Setup wizard."
            )
        elif atype and atype not in VALID_ADDRESS_TYPES:
            errors.append(f"{label} addressType '{atype}' invalid; expected one of {sorted(VALID_ADDRESS_TYPES)}.")
        name = child_text(addr, "routingName")
        if name:
            if name in seen_names:
                errors.append(f"{label} duplicate routingName '{name}'.")
            seen_names.add(name)
        if child_text(addr, "emailAddress") is not None:
            errors.append(
                f"{label} sets 'emailAddress' — remove it; the customer-facing "
                "email is supplied at apply time via --routing-email, never in "
                "the source file.")
        for field in READONLY_FIELDS:
            if child_text(addr, field) is not None:
                errors.append(f"{label} sets read-only field '{field}' — remove it; the platform manages it.")

        # Optional per-address Default Case Owner. If caseOwner is set, it must
        # be a real value (not an unfilled placeholder) AND be paired with a
        # valid caseOwnerType — the platform rejects caseOwner without a type.
        case_owner = child_text(addr, "caseOwner")
        case_owner_type = child_text(addr, "caseOwnerType")
        if case_owner is not None:
            if is_placeholder(case_owner):
                errors.append(
                    f"{label} caseOwner is still the placeholder '{case_owner}' "
                    "— set a real active Username or Queue DeveloperName, or "
                    "remove caseOwner (and caseOwnerType) to use the org "
                    "Default Case Owner.")
            if case_owner_type is None:
                errors.append(
                    f"{label} sets caseOwner without caseOwnerType — the "
                    "platform requires caseOwnerType ('User' or 'Queue') "
                    "whenever caseOwner is set. Add caseOwnerType, or remove "
                    "caseOwner to use the org Default Case Owner.")
        if case_owner_type is not None:
            if is_placeholder(case_owner_type):
                errors.append(
                    f"{label} caseOwnerType is still the placeholder "
                    f"'{case_owner_type}' — set 'User' or 'Queue'.")
            elif case_owner_type not in VALID_OWNER_TYPES:
                errors.append(
                    f"{label} caseOwnerType must be 'User' or 'Queue', found "
                    f"'{case_owner_type}'.")
            if case_owner is None:
                errors.append(
                    f"{label} sets caseOwnerType without caseOwner — either add "
                    "a caseOwner value or remove caseOwnerType.")

    return errors


def main():
    args = [a for a in sys.argv[1:] if a not in ("--help", "-h")]
    if len(sys.argv) == 1 or "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0 if "--help" in sys.argv or "-h" in sys.argv else 2
    path = args[0]
    errors = validate(path)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"OK: {path} passed CaseSettings Email-to-Case validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
