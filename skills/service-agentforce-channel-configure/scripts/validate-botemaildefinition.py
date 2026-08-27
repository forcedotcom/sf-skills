#!/usr/bin/env python3
"""Validate a BotEmailDefinition source file for Email-to-Case Agentforce replies.

BotEmailDefinition is the Metadata API type (API v68.0+) that links an
Agentforce Service Agent to Service Email. It is deployed in METADATA format
(--metadata-dir), then referenced from an Email-to-Case routing address via the
routing address's <botEmailDefinition> field.

The WSDL complexType extends Metadata with SIX child fields, none marked
minOccurs="0" -- so all are required on create, and there are no
platform-generated read-only fields to strip:

  botDefinition   - developer/API name of the AgentforceServiceAgent (Bot) to link.
  emailTemplate   - FOLDER-QUALIFIED developer name of the reply email template.
  label           - display label for the email definition.
  legalDisclaimer - legal disclosure / footer text (>= 10 chars).
  replyAll        - boolean; whether the agent replies-all vs. reply-to-sender.
  signature       - email signature block (>= 10 chars).

Checks the structural rules the platform's save-time validation enforces, so
they hold before deploying:
  - Well-formed XML with the BotEmailDefinition root and correct namespace.
  - All six required fields are present and non-empty.
  - legalDisclaimer and signature are each at least 10 characters
    (save-time MinLengthNotMet check -- these are silently accepted by a naive
    template but rejected by the org).
  - emailTemplate is folder-qualified (contains a '/'); a bare name fails the
    deploy with "no EmailTemplate named X found".
  - replyAll is a boolean literal ('true' or 'false').
  - No <fullName> element inside the file (the fullName is the file name for a
    top-level component; a <fullName> child is rejected on deploy).

Usage: python3 validate-botemaildefinition.py <path-to-file>   (--help for this text)
Exits non-zero and prints ERROR lines to stderr if any check fails.
"""
import sys
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
Q = f"{{{NS}}}"

REQUIRED_FIELDS = (
    "botDefinition",
    "emailTemplate",
    "label",
    "legalDisclaimer",
    "replyAll",
    "signature",
)
BOOLEAN_FIELDS = {"replyAll"}
# Save-time MinLengthNotMet check on the org rejects these below 10 chars.
MIN_LENGTH_FIELDS = {"legalDisclaimer": 10, "signature": 10}


def local(tag):
    return tag.split("}", 1)[-1]


def child_text(parent, name):
    el = parent.find(f"{Q}{name}")
    return el.text.strip() if el is not None and el.text else None


def validate(path):
    errors = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"XML is not well-formed: {exc}"]
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    root = tree.getroot()
    if local(root.tag) != "BotEmailDefinition":
        errors.append(
            f"Root element must be BotEmailDefinition, found '{local(root.tag)}'.")
    if not root.tag.startswith(Q):
        errors.append(f"Root must use namespace '{NS}'.")

    # fullName is the file name for a top-level component; a <fullName> child
    # in the source file is rejected on deploy.
    if root.find(f"{Q}fullName") is not None:
        errors.append(
            "Remove the <fullName> element — for a top-level component the "
            "fullName is the file name (e.g. My_Email_Def in "
            "My_Email_Def.botEmailDefinition-meta.xml), not a child element.")

    for field in REQUIRED_FIELDS:
        value = child_text(root, field)
        if not value:
            errors.append(f"Missing required field '{field}'.")
            continue
        if field in BOOLEAN_FIELDS and value not in ("true", "false"):
            errors.append(
                f"Field '{field}' must be 'true' or 'false', found '{value}'.")
        if field in MIN_LENGTH_FIELDS and len(value) < MIN_LENGTH_FIELDS[field]:
            errors.append(
                f"Field '{field}' must be at least {MIN_LENGTH_FIELDS[field]} "
                f"characters (save-time MinLengthNotMet check); found "
                f"{len(value)} ('{value}').")
        if field == "emailTemplate" and "/" not in value:
            errors.append(
                f"Field 'emailTemplate' must be folder-qualified "
                f"(e.g. unfiled$public/{value}); a bare name fails the deploy "
                f"with 'no EmailTemplate named {value} found'.")

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
    print(f"OK: {path} passed BotEmailDefinition validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
