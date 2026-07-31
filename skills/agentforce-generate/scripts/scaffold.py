#!/usr/bin/env python3
"""Generate metadata stubs (Flow XML, Apex classes) for missing .agent file targets.

Reads discovery report or .agent file, generates stubs for targets not found in the org.

Usage:
    python3 scripts/scaffold.py --agent-file path/to/Agent.agent -o OrgAlias --output-dir force-app/main/default
    python3 scripts/scaffold.py --agent-file path/to/Agent.agent --all --output-dir force-app/main/default
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Ensure the parent directory is in sys.path for package imports
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.discover import DiscoveryReport, TargetStatus, discover, extract_actions
from scripts.generators.flow_xml import generate_flow_xml
from scripts.generators.apex_stub import generate_apex_class, generate_apex_meta_xml, generate_callout_apex_class, generate_soql_apex_class
from scripts.generators.apex_test_stub import generate_apex_test_class
from scripts.generators.permission_set_xml import generate_permission_set_xml
from scripts.generators.remote_site_xml import generate_remote_site_xml, safe_domain_name
from scripts.org_describe import describe_sobject, match_fields


# --- Action Classification ---

# Patterns that signal HTTP callout actions
_CALLOUT_PATTERNS = re.compile(
    r'\b(api|http|https|rest|soap|external|callout|webhook|endpoint)\b'
    r'|https?://[^\s"\']+',
    re.IGNORECASE,
)

# Patterns that signal SOQL/record-based actions
_SOQL_PATTERNS = re.compile(
    r'\b(soql|query|record|sobject|object|lookup|search|find|get\s+record)\b'
    r'|__c\b',
    re.IGNORECASE,
)

# Patterns that signal auth/credential needs
_AUTH_PATTERNS = re.compile(
    r'\b(api\s*key|bearer|token|auth|credential|secret|oauth)\b',
    re.IGNORECASE,
)

# Pattern to extract domains from descriptions
_DOMAIN_PATTERN = re.compile(
    r'https?://([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)',
)


def _sanitize_apex_class_name(target_name: str) -> str:
    """Convert an apex target name to a valid Salesforce Apex class name.

    Apex class names cannot contain dots. For targets like
    'TargetService.searchProducts', convert to 'TargetServiceSearchProducts'.
    For 'utils.setVariables', convert to 'UtilsSetVariables'.
    """
    if "." not in target_name:
        return target_name
    parts = target_name.split(".")
    # PascalCase each part and join
    return "".join(p[0].upper() + p[1:] if p else "" for p in parts)


def classify_action(action_def: dict) -> str:
    """Classify an action to determine scaffold strategy.

    Examines the action description and name for signals:
    - 'callout': HTTP/REST/external API patterns detected
    - 'soql': SObject/query patterns detected
    - 'basic': No special signals

    Args:
        action_def: Action definition dict with 'name', 'description', etc.

    Returns:
        Classification string: 'callout', 'soql', or 'basic'.
    """
    text = " ".join([
        action_def.get("description", ""),
        action_def.get("name", ""),
    ])

    if _CALLOUT_PATTERNS.search(text):
        return "callout"
    if _SOQL_PATTERNS.search(text):
        return "soql"
    return "basic"


def _extract_domains(text: str) -> list[str]:
    """Extract domain names from a text string."""
    return list(set(_DOMAIN_PATTERN.findall(text)))


def _needs_auth_metadata(text: str) -> bool:
    """Check if the action description suggests auth/credential needs."""
    return bool(_AUTH_PATTERNS.search(text))


@dataclass
class ScaffoldResult:
    """Result of scaffolding operations."""
    files_created: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def scaffold(
    report: DiscoveryReport,
    output_dir: Path,
    agent_file: Path | None = None,
    target_org: str | None = None,
) -> ScaffoldResult:
    """Generate stubs for all missing targets in a discovery report.

    Args:
        report: Discovery report with found/missing targets.
        output_dir: Base output directory (e.g. force-app/main/default).
        agent_file: Path to .agent file (for extracting action I/O definitions).
        target_org: Org alias (for smart scaffold with SObject field mapping).

    Returns:
        ScaffoldResult with created files and warnings.
    """
    result = ScaffoldResult()

    # Load action definitions from .agent file for input/output info
    actions = {}
    if agent_file and agent_file.exists():
        for action in extract_actions(agent_file):
            if action.get("target_name"):
                actions[action["target_name"]] = action

    # Derive agent name for permission set naming
    agent_name = ""
    if agent_file:
        agent_name = agent_file.stem  # e.g. "OrderService"

    apex_classes = []
    seen_targets = set()
    seen_retriever_warnings = set()

    for target in report.missing:
        # Deduplicate: same target can appear in multiple topics
        if target.target in seen_targets:
            continue
        seen_targets.add(target.target)

        if target.target_type == "flow":
            _scaffold_flow(target, output_dir, actions, target_org, result)
        elif target.target_type == "apex":
            _scaffold_apex(target, output_dir, actions, target_org, result)
            apex_classes.append(_sanitize_apex_class_name(target.target_name))
        elif target.target_type == "retriever":
            if target.target_name not in seen_retriever_warnings:
                seen_retriever_warnings.add(target.target_name)
                result.warnings.append(
                    f"Retriever '{target.target_name}' must be created manually in "
                    f"Setup → Data Cloud → Data Spaces → Knowledge"
                )

    # Generate permission set if any Apex classes were scaffolded
    if apex_classes:
        perm_set_name = f"{agent_name}_Action_Access" if agent_name else "Agent_Action_Access"
        _scaffold_permission_set(apex_classes, output_dir, result, perm_set_name)

    return result


def scaffold_all(
    agent_file: Path,
    output_dir: Path,
    target_org: str | None = None,
) -> ScaffoldResult:
    """Scaffold all targets without org check (generate stubs for everything)."""
    from scripts.discover import extract_targets

    report = DiscoveryReport()
    for uri, ttype, tname in extract_targets(agent_file):
        report.targets.append(TargetStatus(
            agent_file=str(agent_file),
            target=uri,
            target_type=ttype,
            target_name=tname,
            found=False,  # Treat all as missing
        ))

    return scaffold(report, output_dir, agent_file, target_org)


def _scaffold_flow(
    target: TargetStatus,
    output_dir: Path,
    actions: dict,
    target_org: str | None,
    result: ScaffoldResult,
) -> None:
    """Generate Flow XML stub."""
    flow_dir = output_dir / "flows"
    flow_dir.mkdir(parents=True, exist_ok=True)

    action_def = actions.get(target.target_name, {})
    inputs = action_def.get("inputs", [])
    outputs = action_def.get("outputs", [])

    xml = generate_flow_xml(target.target_name, inputs, outputs)

    flow_path = flow_dir / f"{target.target_name}.flow-meta.xml"
    flow_path.write_text(xml, encoding="utf-8")
    result.files_created.append(flow_path)


def _scaffold_apex(
    target: TargetStatus,
    output_dir: Path,
    actions: dict,
    target_org: str | None,
    result: ScaffoldResult,
) -> None:
    """Generate Apex class + test class + meta XMLs, with classification-aware output."""
    classes_dir = output_dir / "classes"
    classes_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize class name — dots are invalid in Apex class names
    cls_name = _sanitize_apex_class_name(target.target_name)

    action_def = actions.get(target.target_name, {})
    inputs = action_def.get("inputs", [])
    outputs = action_def.get("outputs", [])
    classification = classify_action(action_def)
    is_callout = classification == "callout"

    description_text = action_def.get("description", "")

    # Main class — use classification-appropriate generator
    if is_callout:
        domains = _extract_domains(description_text)
        endpoint = f"https://{domains[0]}" if domains else "https://example.com/api"
        cls_code = generate_callout_apex_class(cls_name, inputs, outputs, endpoint, description=description_text)
    elif classification == "soql":
        cls_code = generate_soql_apex_class(cls_name, inputs, outputs, description=description_text)
    else:
        cls_code = generate_apex_class(cls_name, inputs, outputs, description=description_text)

    cls_path = classes_dir / f"{cls_name}.cls"
    cls_path.write_text(cls_code, encoding="utf-8")
    result.files_created.append(cls_path)

    # Meta XML
    meta_xml = generate_apex_meta_xml()
    meta_path = classes_dir / f"{cls_name}.cls-meta.xml"
    meta_path.write_text(meta_xml, encoding="utf-8")
    result.files_created.append(meta_path)

    # Test class — use the dedicated generator
    test_name = f"{cls_name}Test"
    test_code = generate_apex_test_class(cls_name, inputs, outputs, is_callout=is_callout)
    test_path = classes_dir / f"{test_name}.cls"
    test_path.write_text(test_code, encoding="utf-8")
    result.files_created.append(test_path)

    # Test meta XML
    test_meta_path = classes_dir / f"{test_name}.cls-meta.xml"
    test_meta_path.write_text(meta_xml, encoding="utf-8")
    result.files_created.append(test_meta_path)

    # Callout-specific artifacts
    if is_callout:
        # Remote Site Settings for discovered domains
        domains = _extract_domains(description_text)
        for domain in domains:
            _scaffold_remote_site(domain, description_text, output_dir, result)

        # Custom Metadata for auth if needed
        if _needs_auth_metadata(description_text):
            _scaffold_custom_metadata(cls_name, output_dir, result)


def _scaffold_remote_site(
    domain: str,
    description: str,
    output_dir: Path,
    result: ScaffoldResult,
) -> None:
    """Generate a Remote Site Setting for a callout domain."""
    remote_dir = output_dir / "remoteSiteSettings"
    remote_dir.mkdir(parents=True, exist_ok=True)

    site_name = safe_domain_name(domain)
    xml = generate_remote_site_xml(domain, f"Remote site for callout to {domain}")
    site_path = remote_dir / f"{site_name}.remoteSite-meta.xml"
    site_path.write_text(xml, encoding="utf-8")
    result.files_created.append(site_path)


def _scaffold_custom_metadata(
    action_name: str,
    output_dir: Path,
    result: ScaffoldResult,
) -> None:
    """Generate Custom Metadata Type + record for API key storage."""
    cmd_dir = output_dir / "customMetadata"
    cmd_dir.mkdir(parents=True, exist_ok=True)

    type_name = f"{action_name}_Config"
    record_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        f'    <label>{action_name} Config Default</label>\n'
        '    <protected>false</protected>\n'
        '    <values>\n'
        '        <field>apikey__c</field>\n'
        '        <value xsi:type="xsd:string" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">REPLACE_WITH_ACTUAL_KEY</value>\n'
        '    </values>\n'
        '</CustomMetadata>\n'
    )

    record_path = cmd_dir / f"{type_name}.Default.md-meta.xml"
    record_path.write_text(record_xml, encoding="utf-8")
    result.files_created.append(record_path)

    # Also generate the Custom Metadata Type definition
    type_dir = output_dir / "objects" / f"{type_name}__mdt"
    type_dir.mkdir(parents=True, exist_ok=True)

    type_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        f'    <label>{action_name} Config</label>\n'
        f'    <pluralLabel>{action_name} Configs</pluralLabel>\n'
        '    <visibility>Public</visibility>\n'
        '</CustomObject>\n'
    )
    type_path = type_dir / f"{type_name}__mdt.object-meta.xml"
    type_path.write_text(type_xml, encoding="utf-8")
    result.files_created.append(type_path)

    # Field definition for apikey__c
    fields_dir = type_dir / "fields"
    fields_dir.mkdir(parents=True, exist_ok=True)
    field_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n'
        '    <fullName>apikey__c</fullName>\n'
        '    <fieldManageability>SubscriberControlled</fieldManageability>\n'
        '    <label>API Key</label>\n'
        '    <length>255</length>\n'
        '    <type>Text</type>\n'
        '    <unique>false</unique>\n'
        '</CustomField>\n'
    )
    field_path = fields_dir / "apikey__c.field-meta.xml"
    field_path.write_text(field_xml, encoding="utf-8")
    result.files_created.append(field_path)


def _scaffold_permission_set(
    apex_classes: list[str],
    output_dir: Path,
    result: ScaffoldResult,
    perm_set_name: str = "Agent_Action_Access",
) -> None:
    """Generate permission set granting access to scaffolded Apex classes."""
    perm_dir = output_dir / "permissionsets"
    perm_dir.mkdir(parents=True, exist_ok=True)

    # Include both classes and their test classes
    all_classes = []
    for cls in apex_classes:
        all_classes.append(cls)
        all_classes.append(f"{cls}Test")

    xml = generate_permission_set_xml(perm_set_name, all_classes)
    perm_path = perm_dir / f"{perm_set_name}.permissionset-meta.xml"
    perm_path.write_text(xml, encoding="utf-8")
    result.files_created.append(perm_path)


def print_result(result: ScaffoldResult) -> None:
    """Print scaffold results."""
    if result.files_created:
        print(f"\n✅ Created {len(result.files_created)} file(s):")
        for f in result.files_created:
            print(f"   {f}")

    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for w in result.warnings:
            print(f"   {w}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Scaffold metadata stubs for missing .agent targets")
    parser.add_argument("--agent-file", type=Path, required=True, help="Path to .agent file")
    parser.add_argument("-o", "--target-org", help="Salesforce org alias (for discovery)")
    parser.add_argument("--output-dir", type=Path, default=Path("force-app/main/default"), help="Output directory")
    parser.add_argument("--all", action="store_true", help="Scaffold all targets (skip org check)")
    args = parser.parse_args()

    if not args.agent_file.exists():
        print(f"Error: {args.agent_file} not found", file=sys.stderr)
        sys.exit(1)

    if args.all:
        result = scaffold_all(args.agent_file, args.output_dir, args.target_org)
    else:
        if not args.target_org:
            print("Error: --target-org required (or use --all to skip org check)", file=sys.stderr)
            sys.exit(1)
        report = discover(args.agent_file, args.target_org)
        result = scaffold(report, args.output_dir, args.agent_file, args.target_org)

    print_result(result)


if __name__ == "__main__":
    main()
