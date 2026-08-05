#!/usr/bin/env python3
"""Discover which .agent file targets (flows, apex classes, retrievers) exist in a Salesforce org.

Reads .agent files to extract target: values (flow://, apex://, retriever://),
queries the org via sf CLI, and reports found/missing targets with fuzzy suggestions.

Usage:
    python3 scripts/discover.py --agent-file path/to/Agent.agent -o OrgAlias
    python3 scripts/discover.py --agent-dir force-app/main/default/aiAuthoringBundles -o OrgAlias
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Suggestion:
    """A similar resource found in the org."""
    name: str
    similarity: float  # 0.0–1.0


@dataclass
class TargetStatus:
    """Status of one .agent target."""
    agent_file: str
    target: str           # e.g. "flow://Get_Order_Status"
    target_type: str      # "flow", "apex", "retriever"
    target_name: str      # "Get_Order_Status"
    found: bool = False
    details: str = ""
    suggestions: list[Suggestion] = field(default_factory=list)


@dataclass
class IoMismatch:
    """A mismatch between expected and actual I/O parameters."""
    target_name: str
    field_name: str
    direction: str  # "input" or "output"
    expected_type: str
    actual_type: str
    issue: str  # "missing", "type_mismatch", "extra"


@dataclass
class DiscoveryReport:
    """Collection of target statuses."""
    targets: list[TargetStatus] = field(default_factory=list)
    io_mismatches: list[IoMismatch] = field(default_factory=list)

    @property
    def found(self) -> list[TargetStatus]:
        return [t for t in self.targets if t.found]

    @property
    def missing(self) -> list[TargetStatus]:
        return [t for t in self.targets if not t.found]

    @property
    def all_found(self) -> bool:
        return all(t.found for t in self.targets)


def extract_targets(agent_file: Path) -> list[tuple[str, str, str]]:
    """Extract target: values from an .agent file.

    Returns list of (target_uri, target_type, target_name) tuples.
    e.g. ("flow://Get_Order_Status", "flow", "Get_Order_Status")
    """
    content = agent_file.read_text(encoding="utf-8")
    targets = []
    # Match target: "flow://Name" or target: "apex://Name" or target: "retriever://Name"
    for match in re.finditer(r'target:\s*"?(flow|apex|retriever)://([^"\s]+)"?', content):
        target_type = match.group(1)
        target_name = match.group(2)
        target_uri = f"{target_type}://{target_name}"
        targets.append((target_uri, target_type, target_name))
    return targets


def extract_actions(agent_file: Path) -> list[dict]:
    """Extract action definitions from an .agent file for scaffolding.

    Returns list of dicts with keys: name, target, target_type, target_name, inputs, outputs.
    """
    content = agent_file.read_text(encoding="utf-8")
    actions = []
    # Simple regex-based extraction of action blocks
    # Matches patterns like:
    #   action_name:
    #       ...
    #       target: "flow://Name"
    current_action = None
    current_inputs = []
    current_outputs = []
    in_inputs = False
    in_outputs = False

    for line in content.splitlines():
        stripped = line.strip()

        # Detect target line
        target_match = re.match(r'target:\s*"?(flow|apex|retriever)://([^"\s]+)"?', stripped)
        if target_match and current_action:
            current_action["target_type"] = target_match.group(1)
            current_action["target_name"] = target_match.group(2)
            current_action["target"] = f"{target_match.group(1)}://{target_match.group(2)}"
            # Target terminates input/output collection
            in_inputs = False
            in_outputs = False
            continue

        # Detect description line (captures action description for classification)
        desc_match = re.match(r'description:\s*"(.+)"', stripped)
        if desc_match and current_action and "description" not in current_action:
            current_action["description"] = desc_match.group(1)
            continue

        # Detect inputs/outputs sections
        if stripped == "inputs:":
            in_inputs = True
            in_outputs = False
            continue
        elif stripped == "outputs:":
            in_outputs = True
            in_inputs = False
            continue

        # Detect action start (indented name followed by colon)
        action_match = re.match(r'^(\t{2,3}|\s{6,12})(\w+):\s*$', line)
        if action_match:
            # Save previous action
            if current_action and current_action.get("target"):
                current_action["inputs"] = current_inputs
                current_action["outputs"] = current_outputs
                actions.append(current_action)
            current_action = {"name": action_match.group(2)}
            current_inputs = []
            current_outputs = []
            in_inputs = False
            in_outputs = False
            continue

        # Collect complex_data_type_name for the last collected param
        cdt_match = re.match(r'complex_data_type_name:\s*"([^"]+)"', stripped)
        if cdt_match:
            last_list = current_inputs if in_inputs else (current_outputs if in_outputs else None)
            if last_list:
                last_list[-1]["complex_data_type_name"] = cdt_match.group(1)
            continue

        # Collect input/output parameters (match "name: type" on stripped text)
        param_match = re.match(r'^(\w+):\s*(string|number|boolean|date|datetime|id|object)\b', stripped)
        if param_match:
            param = {"name": param_match.group(1), "type": param_match.group(2)}
            if in_inputs:
                current_inputs.append(param)
            elif in_outputs:
                current_outputs.append(param)

    # Don't forget the last action
    if current_action and current_action.get("target"):
        current_action["inputs"] = current_inputs
        current_action["outputs"] = current_outputs
        actions.append(current_action)

    return actions


def _query_org(query: str, target_org: str) -> list[dict]:
    """Run SOQL query via sf CLI."""
    cmd = ["sf", "data", "query", "--query", query, "-o", target_org, "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
        return data.get("result", {}).get("records", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []


def _check_flows(names: list[str], target_org: str) -> dict[str, bool]:
    """Check which flows exist in the org."""
    records = _query_org(
        "SELECT ApiName FROM FlowDefinitionView WHERE IsActive = true",
        target_org,
    )
    org_flows = {r["ApiName"] for r in records if "ApiName" in r}
    return {name: name in org_flows for name in names}


def _check_apex(names: list[str], target_org: str) -> dict[str, bool]:
    """Check which Apex classes exist in the org."""
    records = _query_org(
        "SELECT Name FROM ApexClass WHERE Status = 'Active'",
        target_org,
    )
    org_classes = {r["Name"] for r in records if "Name" in r}
    return {name: name in org_classes for name in names}


def _check_retrievers(names: list[str], target_org: str) -> dict[str, bool]:
    """Check which retrievers (DataKnowledgeSpace) exist in the org."""
    records = _query_org(
        "SELECT DeveloperName FROM DataKnowledgeSpace",
        target_org,
    )
    org_retrievers = {r["DeveloperName"] for r in records if "DeveloperName" in r}
    return {name: name in org_retrievers for name in names}


def _suggest_similar(name: str, available: list[str], threshold: float = 0.4) -> list[Suggestion]:
    """Find similar names in the org using fuzzy matching."""
    suggestions = []
    name_lower = name.lower()
    name_tokens = set(re.split(r"[_\s]|(?<=[a-z])(?=[A-Z])", name))

    for candidate in available:
        # Sequence matching
        seq_score = difflib.SequenceMatcher(None, name_lower, candidate.lower()).ratio()

        # Jaccard keyword overlap
        cand_tokens = set(re.split(r"[_\s]|(?<=[a-z])(?=[A-Z])", candidate))
        if name_tokens and cand_tokens:
            jaccard = len(name_tokens & cand_tokens) / len(name_tokens | cand_tokens)
        else:
            jaccard = 0.0

        score = max(seq_score, jaccard)
        if score >= threshold:
            suggestions.append(Suggestion(name=candidate, similarity=round(score, 2)))

    return sorted(suggestions, key=lambda s: s.similarity, reverse=True)[:3]


def _rest_api_get(path: str, target_org: str) -> dict | None:
    """Call a Salesforce REST API endpoint via sf CLI."""
    cmd = ["sf", "org", "open", "-o", target_org, "--json", "--url-only"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        instance_url = data.get("result", {}).get("url", "")
        # Extract base URL (everything before /secur/ or similar)
        import urllib.parse
        parsed = urllib.parse.urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None

    # Use sf api to call REST endpoint
    cmd = ["sf", "api", "request", "rest", path, "-o", target_org, "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


# Flow type to .agent type mapping for validation
_FLOW_TYPE_TO_AGENT = {
    "STRING": "string",
    "NUMBER": "number",
    "CURRENCY": "number",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "DATETIME": "datetime",
}


def validate_action_io(
    target_type: str,
    target_name: str,
    expected_inputs: list[dict],
    expected_outputs: list[dict],
    target_org: str,
) -> list[IoMismatch]:
    """Validate that an existing target's I/O matches what the .agent file declares.

    For flows, queries the Actions REST API to get actual parameter schema.
    For apex, queries the Tooling API for @InvocableVariable fields.

    Args:
        target_type: "flow" or "apex".
        target_name: The API name of the target.
        expected_inputs: Input params declared in the .agent file.
        expected_outputs: Output params declared in the .agent file.
        target_org: Salesforce org alias.

    Returns:
        List of IoMismatch entries (empty if everything matches).
    """
    mismatches = []

    if target_type == "flow":
        mismatches = _validate_flow_io(target_name, expected_inputs, expected_outputs, target_org)
    elif target_type == "apex":
        mismatches = _validate_apex_io(target_name, expected_inputs, expected_outputs, target_org)

    return mismatches


def _validate_flow_io(
    flow_name: str,
    expected_inputs: list[dict],
    expected_outputs: list[dict],
    target_org: str,
) -> list[IoMismatch]:
    """Validate flow I/O via the custom/flow REST API."""
    mismatches = []
    api_path = f"/services/data/v{66}.0/actions/custom/flow/{flow_name}"
    result = _rest_api_get(api_path, target_org)
    if not result:
        return mismatches

    # Parse actual inputs/outputs from the REST response
    actual_inputs = {}
    actual_outputs = {}
    for param in result.get("result", result).get("inputs", []):
        name = param.get("name", "")
        ptype = param.get("type", "").upper()
        actual_inputs[name] = _FLOW_TYPE_TO_AGENT.get(ptype, "string")

    for param in result.get("result", result).get("outputs", []):
        name = param.get("name", "")
        ptype = param.get("type", "").upper()
        actual_outputs[name] = _FLOW_TYPE_TO_AGENT.get(ptype, "string")

    # Check expected inputs exist
    for inp in expected_inputs:
        name = inp["name"]
        if name not in actual_inputs:
            mismatches.append(IoMismatch(
                target_name=flow_name, field_name=name, direction="input",
                expected_type=inp.get("type", "string"), actual_type="",
                issue="missing",
            ))
        elif actual_inputs[name] != inp.get("type", "string"):
            mismatches.append(IoMismatch(
                target_name=flow_name, field_name=name, direction="input",
                expected_type=inp.get("type", "string"), actual_type=actual_inputs[name],
                issue="type_mismatch",
            ))

    # Check expected outputs exist
    for out in expected_outputs:
        name = out["name"]
        if name not in actual_outputs:
            mismatches.append(IoMismatch(
                target_name=flow_name, field_name=name, direction="output",
                expected_type=out.get("type", "string"), actual_type="",
                issue="missing",
            ))

    return mismatches


def _validate_apex_io(
    class_name: str,
    expected_inputs: list[dict],
    expected_outputs: list[dict],
    target_org: str,
) -> list[IoMismatch]:
    """Validate Apex I/O by querying the class body for @InvocableVariable fields."""
    mismatches = []
    records = _query_org(
        f"SELECT Body FROM ApexClass WHERE Name = '{class_name}' LIMIT 1",
        target_org,
    )
    if not records:
        return mismatches

    body = records[0].get("Body", "")
    # Extract @InvocableVariable field names from Request/Response classes
    # Simple regex: find field declarations after @InvocableVariable
    field_pattern = re.compile(r'@InvocableVariable[^;]*\n\s*public\s+\w+\s+(\w+)\s*;')
    actual_fields = set(field_pattern.findall(body))

    for inp in expected_inputs:
        if inp["name"] not in actual_fields:
            mismatches.append(IoMismatch(
                target_name=class_name, field_name=inp["name"], direction="input",
                expected_type=inp.get("type", "string"), actual_type="",
                issue="missing",
            ))

    for out in expected_outputs:
        if out["name"] not in actual_fields:
            mismatches.append(IoMismatch(
                target_name=class_name, field_name=out["name"], direction="output",
                expected_type=out.get("type", "string"), actual_type="",
                issue="missing",
            ))

    return mismatches


def discover(agent_file: Path, target_org: str, validate_io: bool = False) -> DiscoveryReport:
    """Run discovery for a single .agent file.

    Args:
        agent_file: Path to the .agent file.
        target_org: Salesforce org alias.
        validate_io: If True, validate I/O parameters for found targets.
    """
    report = DiscoveryReport()
    raw_targets = extract_targets(agent_file)

    if not raw_targets:
        return report

    # Deduplicate targets (same action can appear in multiple topics)
    seen_uris = set()
    unique_targets = []
    for uri, ttype, tname in raw_targets:
        if uri not in seen_uris:
            seen_uris.add(uri)
            unique_targets.append((uri, ttype, tname))
    raw_targets = unique_targets

    # Group by type
    by_type: dict[str, list[tuple[str, str]]] = {"flow": [], "apex": [], "retriever": []}
    for uri, ttype, tname in raw_targets:
        by_type.setdefault(ttype, []).append((uri, tname))

    # Check each type
    checkers = {
        "flow": (_check_flows, "SELECT ApiName FROM FlowDefinitionView WHERE IsActive = true", "ApiName"),
        "apex": (_check_apex, "SELECT Name FROM ApexClass WHERE Status = 'Active'", "Name"),
        "retriever": (_check_retrievers, "SELECT DeveloperName FROM DataKnowledgeSpace", "DeveloperName"),
    }

    for ttype, targets in by_type.items():
        if not targets:
            continue

        checker_fn, query, field_name = checkers[ttype]
        names = [t[1] for t in targets]
        found_map = checker_fn(names, target_org)

        # Get all available resources for fuzzy matching
        all_records = _query_org(query, target_org)
        available = [r[field_name] for r in all_records if field_name in r]

        for uri, name in targets:
            status = TargetStatus(
                agent_file=str(agent_file),
                target=uri,
                target_type=ttype,
                target_name=name,
                found=found_map.get(name, False),
            )
            if not status.found:
                status.suggestions = _suggest_similar(name, available)
            report.targets.append(status)

    # Validate I/O for found targets
    if validate_io:
        actions = {a["target_name"]: a for a in extract_actions(agent_file) if a.get("target_name")}
        for target in report.found:
            if target.target_type in ("flow", "apex") and target.target_name in actions:
                action_def = actions[target.target_name]
                mismatches = validate_action_io(
                    target.target_type,
                    target.target_name,
                    action_def.get("inputs", []),
                    action_def.get("outputs", []),
                    target_org,
                )
                report.io_mismatches.extend(mismatches)

    return report


def discover_dir(agent_dir: Path, target_org: str, validate_io: bool = False) -> DiscoveryReport:
    """Run discovery for all .agent files in a directory."""
    combined = DiscoveryReport()
    for agent_file in sorted(agent_dir.rglob("*.agent")):
        sub_report = discover(agent_file, target_org, validate_io=validate_io)
        combined.targets.extend(sub_report.targets)
    return combined


def print_report(report: DiscoveryReport) -> None:
    """Print a human-readable discovery report."""
    if not report.targets:
        print("No targets found in .agent file(s).")
        return

    print(f"\n{'=' * 60}")
    print(f"Discovery Report: {len(report.targets)} target(s)")
    print(f"{'=' * 60}")

    # Found targets
    if report.found:
        print(f"\n✅ Found ({len(report.found)}):")
        for t in report.found:
            print(f"   {t.target}")

    # Missing targets
    if report.missing:
        print(f"\n❌ Missing ({len(report.missing)}):")
        for t in report.missing:
            print(f"   {t.target}")
            for s in t.suggestions:
                print(f"      💡 Did you mean: {s.name} ({s.similarity:.0%} match)?")

    # I/O mismatches
    if report.io_mismatches:
        print(f"\n⚠️  I/O Mismatches ({len(report.io_mismatches)}):")
        for m in report.io_mismatches:
            if m.issue == "missing":
                print(f"   {m.target_name}: {m.direction} '{m.field_name}' not found in org target")
            elif m.issue == "type_mismatch":
                print(f"   {m.target_name}: {m.direction} '{m.field_name}' type mismatch — expected {m.expected_type}, got {m.actual_type}")

    print(f"\n{'=' * 60}")
    if report.all_found:
        print("All targets found in org.")
    else:
        print(f"{len(report.missing)} target(s) missing. Run /adlc-scaffold to generate stubs.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Discover .agent file targets in a Salesforce org")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent-file", type=Path, help="Path to a single .agent file")
    group.add_argument("--agent-dir", type=Path, help="Directory containing .agent files")
    parser.add_argument("-o", "--target-org", required=True, help="Salesforce org alias")
    parser.add_argument("--validate-io", action="store_true", help="Validate I/O parameters for found targets")
    args = parser.parse_args()

    if args.agent_file:
        if not args.agent_file.exists():
            print(f"Error: {args.agent_file} not found", file=sys.stderr)
            sys.exit(1)
        report = discover(args.agent_file, args.target_org, validate_io=args.validate_io)
    else:
        if not args.agent_dir.exists():
            print(f"Error: {args.agent_dir} not found", file=sys.stderr)
            sys.exit(1)
        report = discover_dir(args.agent_dir, args.target_org, validate_io=args.validate_io)

    print_report(report)

    # Exit with non-zero if any targets are missing
    sys.exit(0 if report.all_found else 1)


if __name__ == "__main__":
    main()
