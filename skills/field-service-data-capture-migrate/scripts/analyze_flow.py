#!/usr/bin/env python3
"""
Analyze a Field Service Mobile flow and generate a migration assessment.

Usage:
    python3 analyze_flow.py <input_flow.xml> <output_analysis.json>

Outputs a JSON report with:
- Screen and field inventory
- Component compatibility mapping (via the authoritative capability catalog)
- A Data Capture Gap Report: components with NO DC equivalent + capability gaps
- Automation complexity
- Risk score (GREEN/YELLOW/RED)
- Manual intervention checklist

Classification is keyed on the REAL FSM Flow vocabulary (fieldType first,
extensionName only for ComponentInstance) via scripts/fsm_dc_catalog.py — NOT
Lightning component names. See references/fsm-dc-capability-catalog.md.
"""

import sys
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsm_dc_catalog as catalog
import flow_input  # noqa: E402
from flow_xml_utils import NS, _findtext, _findall, _findall_deep  # noqa: E402,F401
import cud_analysis  # noqa: E402


def analyze_flow(root: ET.Element) -> Dict[str, Any]:
    """Generate analysis from a validated flow root.

    Input is the <Flow> element returned by flow_input.load_and_validate_flow;
    parsing and validation happen there, not here.
    """
    flow_name = _findtext(root, 'label') or 'Unknown'
    process_type = _findtext(root, 'processType') or 'Unknown'
    api_version = _findtext(root, 'apiVersion') or '(unspecified)'

    screens = _findall_deep(root, 'screens')
    screen_count = len(screens)

    fields: List[Dict[str, Any]] = []
    manual_steps: List[str] = []
    # Gap report: FSM components that will NOT migrate to DC.
    component_gaps: List[Dict[str, Any]] = []

    for screen_idx, screen in enumerate(screens, 1):
        screen_name = _findtext(screen, 'name') or f'Screen{screen_idx}'
        screen_label = _findtext(screen, 'label') or screen_name

        for field in _findall(screen, 'fields'):
            field_name = _findtext(field, 'name')
            field_type = _findtext(field, 'fieldType')
            data_type = _findtext(field, 'dataType')
            extension = _findtext(field, 'extensionName')

            result = catalog.classify(field_type, data_type, extension)
            status = result['status']

            fields.append({
                'name': field_name,
                'screen': screen_label,
                'fieldType': field_type,
                'dataType': data_type,
                'extensionName': extension,
                'dcExtension': result['dc_extension'],
                'dcFieldType': result['dc_field_type'],
                'status': status,
                'note': result['note'],
            })

            if catalog.is_gap(status):
                component_gaps.append({
                    'field': field_name,
                    'screen': screen_label,
                    'fieldType': field_type,
                    'extensionName': extension,
                    'status': status,
                    'reason': result['note'],
                })
                manual_steps.append(
                    f'{status}: field "{field_name}" ({field_type}'
                    f'{"/" + extension if extension else ""}) on screen '
                    f'"{screen_label}" — {result["note"]}'
                )

    # Automation elements
    automation = {
        'decisions': len(_findall_deep(root, 'decisions')),
        'recordLookups': len(_findall_deep(root, 'recordLookups')),
        'recordCreates': len(_findall_deep(root, 'recordCreates')),
        'recordUpdates': len(_findall_deep(root, 'recordUpdates')),
        'recordDeletes': len(_findall_deep(root, 'recordDeletes')),
        'apexCalls': len(_findall_deep(root, 'actionCalls')),
        'subflowCalls': len(_findall_deep(root, 'subflows')),
        'loops': len(_findall_deep(root, 'loops')),
    }

    # Capability-level gaps that this specific flow actually triggers.
    triggered_capability_gaps = _triggered_capability_gaps(root, automation)

    if automation['apexCalls'] > 0:
        manual_steps.append('Convert Apex callouts to record lookups (Data Capture is offline-first — no Apex at runtime)')
    if automation['subflowCalls'] > 0:
        manual_steps.append('Ensure subflows are DataCaptureFlow type and contain no CUD; inline or convert AutoLaunched subflows')

    # Coverage counts
    mapped_count = sum(1 for f in fields if f['status'] == catalog.MAPPED)
    gap_count = len(component_gaps)
    total_fields = len(fields)

    cud_report = cud_analysis.analyze_cud_placement(root)
    cud_placement = {
        'hasMidFlowCud': cud_report.has_midflow,
        'compliant': [n.name for n in cud_report.cud_nodes if n.verdict == 'compliant'],
        'safeConsolidate': [n.name for n in cud_report.cud_nodes
                            if n.verdict == 'safe_consolidate'],
        'unsafeManual': [
            {'node': n.name, 'position': n.position,
             'reason': '; '.join(n.blockers) or 'mid-flow CUD'}
            for n in cud_report.cud_nodes if n.verdict == 'unsafe_manual'
        ],
    }
    for n in cud_report.cud_nodes:
        if n.verdict == 'safe_consolidate':
            manual_steps.append(
                f"Mid-flow {n.op} '{n.name}' (position {n.position}) — safe to "
                f"consolidate to end-of-flow.")
        elif n.verdict == 'unsafe_manual':
            manual_steps.append(
                f"Mid-flow {n.op} '{n.name}' (position {n.position}) — unsafe: "
                f"{'; '.join(n.blockers)}. Restructure manually.")

    # Risk score
    if gap_count == 0 and automation['apexCalls'] == 0 and automation['subflowCalls'] == 0:
        risk_score = 'GREEN'
    elif total_fields and gap_count <= total_fields * 0.2:
        risk_score = 'YELLOW'
    else:
        risk_score = 'RED'

    # WI-8: a hazardous-but-deployable mid-flow CUD must never read GREEN.
    if cud_placement['unsafeManual'] and risk_score == 'GREEN':
        risk_score = 'YELLOW'

    analysis = {
        'flowName': flow_name,
        'processType': process_type,
        'apiVersion': api_version,
        'screenCount': screen_count,
        'fieldCount': total_fields,
        'fields': fields,
        'automation': automation,
        'coverage': {
            'mapped': mapped_count,
            'gaps': gap_count,
        },
        # AC#3: the gap-detection output section, feeding WI-7/WI-10.
        'dataCaptureGapReport': {
            'componentGaps': component_gaps,
            'capabilityGaps': triggered_capability_gaps,
            'hasGaps': bool(component_gaps or triggered_capability_gaps),
        },
        'cudPlacement': cud_placement,
        'riskScore': risk_score,
        'manualSteps': manual_steps,
    }

    return analysis


def _triggered_capability_gaps(root: ET.Element, automation: Dict[str, int]) -> List[Dict[str, str]]:
    """Filter the catalog's capability gaps down to the ones this flow triggers."""
    triggered: List[Dict[str, str]] = []
    gaps = {g['gap']: g for g in catalog.capability_gaps()}

    # No actions/buttons — triggered by PlainButtons fields OR actionCalls.
    has_plain_buttons = any(
        (_findtext(f, 'fieldType') == 'PlainButtons')
        for s in _findall_deep(root, 'screens')
        for f in _findall(s, 'fields')
    )
    if has_plain_buttons:
        triggered.append(gaps['No actions / buttons'])

    if automation['apexCalls'] > 0:
        triggered.append(gaps['No Apex / action calls'])

    # Fault paths — any element carrying a <faultConnector>.
    if _findall_deep(root, 'faultConnector'):
        triggered.append(gaps['No fault paths'])

    if automation['subflowCalls'] > 0:
        triggered.append(gaps['Subflows: DC-type only, no CUD'])

    cud = automation['recordCreates'] + automation['recordUpdates'] + automation['recordDeletes']
    if cud > 0:
        triggered.append(gaps['CUD only at end of flow'])

    return triggered


def main():
    if len(sys.argv) != 3:
        print(f"[ERROR] Missing required argument. "
              f"Usage: {sys.argv[0]} <input_flow.xml> <output_analysis.json>\n"
              f"Example: {sys.argv[0]} "
              f"force-app/main/default/flows/MyFlow.flow-meta.xml /tmp/analysis.json",
              file=sys.stderr)
        sys.exit(2)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        root, warnings = flow_input.load_and_validate_flow(input_path)
    except flow_input.FlowValidationError as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)

    for w in warnings:
        print(w.message, file=sys.stderr)

    analysis = analyze_flow(root)

    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Migration Analysis: {analysis['flowName']}")
    print(f"{'='*60}")
    print(f"Process Type: {analysis['processType']}")
    print(f"API Version: {analysis['apiVersion']}")
    print(f"Screens: {analysis['screenCount']}")
    print(f"Fields: {analysis['fieldCount']}")
    print(f"\nComponent Coverage:")
    print(f"  Mapped to DC:   {analysis['coverage']['mapped']} fields")
    print(f"  Gaps (no path): {analysis['coverage']['gaps']} fields")
    print(f"\nAutomation Elements:")
    for key, count in analysis['automation'].items():
        if count > 0:
            print(f"  {key}: {count}")

    gap_report = analysis['dataCaptureGapReport']
    print(f"\n{'─'*60}")
    print(f"DATA CAPTURE GAP REPORT")
    print(f"{'─'*60}")
    if not gap_report['hasGaps']:
        print("  No functionality gaps detected — all components map to DC.")
    else:
        if gap_report['componentGaps']:
            print(f"  Components with no DC equivalent ({len(gap_report['componentGaps'])}):")
            for g in gap_report['componentGaps']:
                ext = f"/{g['extensionName']}" if g['extensionName'] else ''
                print(f"    - [{g['status']}] {g['field']} ({g['fieldType']}{ext})")
                print(f"        {g['reason']}")
        if gap_report['capabilityGaps']:
            print(f"  Capability-level gaps triggered ({len(gap_report['capabilityGaps'])}):")
            for g in gap_report['capabilityGaps']:
                print(f"    - {g['gap']}: {g['detail']}")

    print(f"\nRisk Score: {analysis['riskScore']}")
    if analysis['manualSteps']:
        print(f"\nManual Steps Required ({len(analysis['manualSteps'])}):")
        for step in analysis['manualSteps']:
            print(f"  - {step}")

    print(f"\nFull analysis written to: {output_path}\n")


if __name__ == '__main__':
    main()
