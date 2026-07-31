"""Generate Permission Set XML granting classAccesses to Apex classes."""

from __future__ import annotations


def generate_permission_set_xml(
    perm_set_name: str,
    apex_class_names: list[str],
) -> str:
    """Generate a Permission Set XML with classAccesses entries.

    Args:
        perm_set_name: The permission set API name (e.g. Agent_Action_Access).
        apex_class_names: List of Apex class names to grant access to.

    Returns:
        Permission Set XML string.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">',
        f"    <label>{perm_set_name}</label>",
    ]

    for class_name in apex_class_names:
        lines.extend([
            "    <classAccesses>",
            f"        <apexClass>{class_name}</apexClass>",
            "        <enabled>true</enabled>",
            "    </classAccesses>",
        ])

    lines.append("</PermissionSet>")

    return "\n".join(lines) + "\n"
