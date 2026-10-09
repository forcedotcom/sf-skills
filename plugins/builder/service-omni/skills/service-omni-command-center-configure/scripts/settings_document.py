#!/usr/bin/env python3
"""Inspect or safely mutate a retrieved OmniChannel Settings document."""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple


METADATA_NS = "http://soap.sforce.com/2006/04/metadata"
FIELDS = (
    "enableCommandCenterForServiceV2",
    "enableConversationMonitoring",
    "enableAgentSneakPeek",
    "enableClientSneakPeek",
    "enableWhisperMessaging",
    "enableSkillsAndQueueActions",
)


def parse_document(path: Path) -> Tuple[ET.ElementTree, ET.Element]:
    tree = ET.parse(path)
    return tree, tree.getroot()


def find_element(root: ET.Element, name: str) -> Optional[ET.Element]:
    return root.find(f"{{{METADATA_NS}}}{name}")


def inspect(path: Path) -> int:
    _, root = parse_document(path)
    settings = {}
    for name in FIELDS:
        element = find_element(root, name)
        text = (element.text or "").strip().lower() if element is not None else ""
        settings[name] = {
            "present": element is not None,
            "value": text == "true" if text in {"true", "false"} else None,
        }
    print(json.dumps({"settings": settings}, separators=(",", ":")))
    return 0


def render(source: Path, destination: Path, assignments: List[str]) -> int:
    tree, root = parse_document(source)
    requested = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise ValueError(f"Invalid assignment: {assignment}")
        name, value = assignment.split("=", 1)
        if name not in FIELDS:
            raise ValueError(f"Unsupported setting: {name}")
        if value not in {"true", "false"}:
            raise ValueError(f"Invalid boolean for {name}: {value}")
        requested[name] = value

    if "enableCommandCenterForServiceV2" not in requested:
        raise ValueError("enableCommandCenterForServiceV2 must be requested")

    for name, value in requested.items():
        element = find_element(root, name)
        if element is None:
            element = ET.SubElement(root, f"{{{METADATA_NS}}}{name}")
        element.text = value

    ET.register_namespace("", METADATA_NS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="UTF-8", xml_declaration=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="operation", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("path", type=Path)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("source", type=Path)
    render_parser.add_argument("destination", type=Path)
    render_parser.add_argument("assignments", nargs="+")

    args = parser.parse_args()
    try:
        if args.operation == "inspect":
            return inspect(args.path)
        return render(args.source, args.destination, args.assignments)
    except (ET.ParseError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
