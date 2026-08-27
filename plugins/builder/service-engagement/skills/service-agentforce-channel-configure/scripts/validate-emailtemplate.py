#!/usr/bin/env python3
"""Validate an SFX EmailTemplate source pair for Agentforce Service Agent email.

BotEmailDefinition only accepts a template that is a Lightning (SFX) email
template, has an HTML body, contains two literal ASA placeholder tokens, and
lives in a public folder. This script validates the source artifact Branch C
deploys (the fallback-template create branch) so those rules hold before deploy:

  - The .email-meta.xml root is EmailTemplate in the metadata namespace.
  - uiType is 'SFX'  (a classic 'Aloha' template is rejected by the platform;
    uiType is also set-once, so it must be correct at create time).
  - type is 'custom' (an HTML/custom body; 'text'/'visualforce' won't carry the
    HTML tokens).
  - The companion .email body (same base name) exists, is non-blank, and
    contains BOTH literal tokens, exactly:
      [[[GENERATED_CONTENT]]]  and  [[[LEGAL_DISCLOSURE]]].

Public-folder placement (folder must be public, e.g. unfiled$public) is a
deploy-path/permission concern, not visible in the file pair, so it is checked
against the file's directory only as a warning.

Usage: python3 validate-emailtemplate.py <path-to-.email-meta.xml>   (--help for this text)
Exits non-zero and prints ERROR lines to stderr if any check fails.
"""
import os
import sys
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
Q = f"{{{NS}}}"

REQUIRED_TOKENS = ("[[[GENERATED_CONTENT]]]", "[[[LEGAL_DISCLOSURE]]]")


def local(tag):
    return tag.split("}", 1)[-1]


def child_text(parent, name):
    el = parent.find(f"{Q}{name}")
    return el.text.strip() if el is not None and el.text else None


def validate(meta_path):
    errors = []
    try:
        tree = ET.parse(meta_path)
    except ET.ParseError as exc:
        return [f"XML is not well-formed: {exc}"]
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    root = tree.getroot()
    if local(root.tag) != "EmailTemplate":
        errors.append(
            f"Root element must be EmailTemplate, found '{local(root.tag)}'.")
    if not root.tag.startswith(Q):
        errors.append(f"Root must use namespace '{NS}'.")

    ui_type = child_text(root, "uiType")
    if ui_type != "SFX":
        errors.append(
            f"uiType must be 'SFX' (Lightning email template) for Agentforce "
            f"Service Agent email; found '{ui_type}'. A classic 'Aloha' "
            f"template is rejected, and uiType cannot be changed after create.")

    tmpl_type = child_text(root, "type")
    if tmpl_type != "custom":
        errors.append(
            f"type must be 'custom' (an HTML body) to carry the ASA tokens; "
            f"found '{tmpl_type}'.")

    # Companion .email body: same base name, .email extension.
    if meta_path.endswith(".email-meta.xml"):
        body_path = meta_path[: -len("-meta.xml")]
    else:
        body_path = os.path.splitext(meta_path)[0] + ".email"
    try:
        with open(body_path, encoding="utf-8") as fh:
            body = fh.read()
    except OSError:
        errors.append(
            f"Companion HTML body '{os.path.basename(body_path)}' not found "
            f"next to the meta file — the SFX template needs an .email body.")
        body = ""

    if body_path and not body.strip():
        errors.append(
            "The email body is blank — BotEmailDefinition rejects a template "
            "with no HTML value (EmailTemplateDoesntContainHtmlValue).")

    for token in REQUIRED_TOKENS:
        if token not in body:
            errors.append(
                f"The email body is missing the required ASA token '{token}' — "
                f"BotEmailDefinition rejects a template without it. Add it "
                f"verbatim (it is a literal token, not a merge field).")

    return errors


def folder_warning(meta_path):
    """Public-folder placement can't be proven from the file, but a private
    (user) folder is a common mistake — nudge if the path looks non-public."""
    parent = os.path.basename(os.path.dirname(os.path.abspath(meta_path)))
    if parent and parent != "unfiled$public" and not parent.endswith("$public"):
        return (f"NOTE: template is under folder '{parent}'. BotEmailDefinition "
                f"requires a PUBLIC folder (e.g. unfiled$public or a folder "
                f"whose AccessType is Public). Confirm the deploy target folder "
                f"is public.")
    return None


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
    note = folder_warning(path)
    if note:
        print(note, file=sys.stderr)
    print(f"OK: {path} passed SFX EmailTemplate ASA validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
