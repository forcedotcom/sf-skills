#!/usr/bin/env python3
"""
Fully automated FieldServiceMobile → DataCaptureFlow transformer.

Handles every known migration issue:
  1. processType, environments, apiVersion, areMetricsLoggedToDataCloud
  2. Screen field type conversion:
       InputField        → ComponentInstance  (dc* component by dataType)
       DropdownBox       → ComponentChoice    + dcPicklist
       RadioButtons      → ComponentChoice    + dcRbGroup
       MultiSelectCheckboxes → ComponentMultiChoice + dcCbGroup
       LargeTextArea     → ComponentInstance  + dcLongText
       forceContent:fileUpload → ComponentInstance + dcUpFile
  3. outputAssignment removal: replaced with storeOutputAutomatically=true
     + an explicit <assignments> node after the screen to preserve variable bindings
  4. CUD-at-end enforcement (the main structural challenge):
       Pattern A: CUD → Screen   → flip (screen first, then CUD)
       Pattern B: CUD → Lookup/Assignment → hoist lookup to pre-screen phase
       Pattern C: CUD → Decision (mixed) → hoist decision to pre-screen phase
  5. Remove Constants (not allowed in DC)
  6. Remove invalid field attributes (defaultValue, dataType on ComponentChoice etc.)
  7. Deduplicate variables (case-insensitive); fix isInput on required DC vars
  8. Ensure required screen attributes (allowFinish, showFooter, nextOrFinishButtonLabel)
  9. Ensure required DC input variables (recordId, parentRecordId, parentObjectType)
 10. Reorder field children so inputParameters are contiguous
 11. Update subflow flowName references to DC version (appends _DC suffix)
 12. Detects flows with no screens (pure automation) and skips with explanation

Usage:
    python3 transform_flow.py <input.flow-meta.xml> <output.flow-meta.xml> [--dc-suffix _DC]
"""

import sys
import re
import copy
import xml.etree.ElementTree as ET
from collections import defaultdict, OrderedDict
from typing import Optional, Dict, List, Tuple, Set
from subflow_names import migrated_dc_flow_name
from manual_review_flags import detect_manual_review_flags, build_excision_flag

NS_URI = 'http://soap.sforce.com/2006/04/metadata'
NS = {'sf': NS_URI}
ET.register_namespace('', NS_URI)

CUD_TYPES = frozenset(('recordCreates', 'recordUpdates', 'recordDeletes'))
ALL_TYPES = ('screens', 'decisions', 'recordLookups', 'recordCreates',
             'recordUpdates', 'recordDeletes', 'loops', 'assignments', 'subflows',
             'actionCalls')

# ──────────────────────────────────────────────
# XML helpers
# ──────────────────────────────────────────────

def tag(n: str) -> str:
    return f'{{{NS_URI}}}{n}'

def local(el: ET.Element) -> str:
    return el.tag.split('}')[-1]

def findall(el: ET.Element, n: str) -> List[ET.Element]:
    r = el.findall(f'sf:{n}', namespaces=NS)
    return r if r else el.findall(n)

def findtext(el: ET.Element, n: str) -> Optional[str]:
    r = el.findtext(f'sf:{n}', namespaces=NS)
    return r if r is not None else el.findtext(n)

def make(name: str, text: str = None) -> ET.Element:
    el = ET.Element(tag(name))
    if text is not None:
        el.text = text
    return el

def sub(parent: ET.Element, name: str, text: str = None) -> ET.Element:
    el = ET.SubElement(parent, tag(name))
    if text is not None:
        el.text = text
    return el

# ──────────────────────────────────────────────
# Graph helpers
# ──────────────────────────────────────────────

def get_connector_targets(node_el: ET.Element) -> List[str]:
    targets = []
    for conn in (findall(node_el, 'connector') +
                 findall(node_el, 'defaultConnector') +
                 findall(node_el, 'nextValueConnector') +
                 findall(node_el, 'noMoreValuesConnector') +
                 findall(node_el, 'faultConnector')):
        t = findtext(conn, 'targetReference')
        if t:
            targets.append(t)
    for rule in findall(node_el, 'rules'):
        for conn in findall(rule, 'connector'):
            t = findtext(conn, 'targetReference')
            if t:
                targets.append(t)
    return targets


def get_fault_targets(node_el: ET.Element) -> List[str]:
    """Return the targetReferences reached via <faultConnector> only.

    Fault edges are still real graph edges (Salesforce enforces CUD-at-end on
    them), but they need separate handling from success edges: a fault handler
    cannot be hoisted "before" the CUD, so the four hoist patterns don't apply.
    """
    targets = []
    for conn in findall(node_el, 'faultConnector'):
        t = findtext(conn, 'targetReference')
        if t:
            targets.append(t)
    return targets

def build_graph(root: ET.Element) -> Tuple[Dict, Optional[str]]:
    nodes: Dict[str, Tuple[str, ET.Element, List[str]]] = {}
    for ntype in ALL_TYPES:
        for node in findall(root, ntype):
            nname = findtext(node, 'name')
            if nname:
                nodes[nname] = (ntype, node, get_connector_targets(node))
    start_target = None
    for s in findall(root, 'start'):
        for conn in findall(s, 'connector'):
            start_target = findtext(conn, 'targetReference')
    return nodes, start_target

def bfs_order(nodes: Dict, start: Optional[str]) -> List[str]:
    visited, order = set(), []
    q = [start] if start else []
    while q:
        n = q.pop(0)
        if not n or n in visited:
            continue
        visited.add(n)
        order.append(n)
        if n in nodes:
            for t in nodes[n][2]:
                if t not in visited:
                    q.append(t)
    return order

def find_violations(nodes: Dict) -> List[Tuple[str, str]]:
    """Return [(type, name)] for every non-CUD node reached by a direct connector
    edge from a CUD node.

    Edge-based, not order-based: single-visit BFS records only one discovery
    position per node, so a CUD→node edge is invisible when that same node is
    also reachable earlier via a non-CUD path (a diamond). Inspecting each CUD
    node's actual connectors catches the edge regardless of BFS discovery order.
    """
    violations = []
    seen = set()
    for _name, (ntype, _el, targets) in nodes.items():
        if ntype not in CUD_TYPES:
            continue
        for t in targets:
            if t in nodes and nodes[t][0] not in CUD_TYPES:
                key = (nodes[t][0], t)
                if key not in seen:
                    seen.add(key)
                    violations.append(key)
    return violations

def update_all_connectors(root: ET.Element, old: str, new: str) -> int:
    count = 0
    for ntype in ALL_TYPES + ('start',):
        for node in findall(root, ntype):
            for conn in (findall(node, 'connector') +
                         findall(node, 'defaultConnector') +
                         findall(node, 'nextValueConnector') +
                         findall(node, 'noMoreValuesConnector')):
                for tr in findall(conn, 'targetReference'):
                    if tr.text == old:
                        tr.text = new
                        count += 1
            for rule in findall(node, 'rules'):
                for conn in findall(rule, 'connector'):
                    for tr in findall(conn, 'targetReference'):
                        if tr.text == old:
                            tr.text = new
                            count += 1
    return count

def get_start_target(root: ET.Element) -> Optional[str]:
    for s in findall(root, 'start'):
        for conn in findall(s, 'connector'):
            return findtext(conn, 'targetReference')
    return None

def set_start_target(root: ET.Element, new_target: str):
    for s in findall(root, 'start'):
        for conn in findall(s, 'connector'):
            for tr in findall(conn, 'targetReference'):
                tr.text = new_target

def predecessors_of(root: ET.Element, name: str) -> List[str]:
    preds = []
    start_t = get_start_target(root)
    if start_t == name:
        preds.append('__start__')
    for ntype in ALL_TYPES:
        for node in findall(root, ntype):
            nname = findtext(node, 'name')
            if name in get_connector_targets(node):
                preds.append(nname)
    return preds

# ──────────────────────────────────────────────
# Component type mappings
# ──────────────────────────────────────────────

# (fieldType, dataType) → (new_fieldType, extensionName, label_style)
# label_style: 'param'=inputParameter  'fieldtext'=<fieldText>  'none'=skip
FIELD_TYPE_MAP = {
    # ComponentChoice types (use fieldText for label, keep extensionName)
    ('DropdownBox',          None): ('ComponentChoice',      'runtime_service_fieldservice:dcPicklist', 'fieldtext'),
    ('RadioButtons',         None): ('ComponentChoice',      'runtime_service_fieldservice:dcRbGroup',  'fieldtext'),
    ('RadioButtonGroup',     None): ('ComponentChoice',      'runtime_service_fieldservice:dcRbGroup',  'fieldtext'),
    ('MultiSelectCheckboxes',None): ('ComponentMultiChoice', 'runtime_service_fieldservice:dcCbGroup',  'fieldtext'),
    ('MultiSelectPicklist',  None): ('ComponentMultiChoice', 'runtime_service_fieldservice:dcCbGroup',  'fieldtext'),
    # InputField → ComponentInstance based on dataType
    ('InputField', 'Boolean'):         ('ComponentInstance', 'runtime_service_fieldservice:dcCheckbox',  'param'),
    ('InputField', 'String'):          ('ComponentInstance', 'runtime_service_fieldservice:dcTextInput', 'param'),
    ('InputField', 'Number'):          ('ComponentInstance', 'runtime_service_fieldservice:dcNumeric',   'param'),
    ('InputField', 'Double'):          ('ComponentInstance', 'runtime_service_fieldservice:dcNumeric',   'param'),
    ('InputField', 'Currency'):        ('ComponentInstance', 'runtime_service_fieldservice:dcNumeric',   'param'),
    ('InputField', 'Date'):            ('ComponentInstance', 'runtime_service_fieldservice:dcDate',      'param'),
    ('InputField', 'DateTime'):        ('ComponentInstance', 'runtime_service_fieldservice:dcDateTime',  'param'),
    ('InputField', 'Email'):           ('ComponentInstance', 'runtime_service_fieldservice:dcEmail',     'param'),
    ('InputField', 'Phone'):           ('ComponentInstance', 'runtime_service_fieldservice:dcPhone',     'param'),
    ('InputField', 'Picklist'):        ('ComponentChoice',   'runtime_service_fieldservice:dcPicklist',  'fieldtext'),
    ('InputField', 'MultiselectPicklist'):('ComponentMultiChoice','runtime_service_fieldservice:dcCbGroup','fieldtext'),
    ('InputField', 'TextArea'):        ('ComponentInstance', 'runtime_service_fieldservice:dcLongText',  'param'),
    ('InputField', 'LongTextArea'):    ('ComponentInstance', 'runtime_service_fieldservice:dcLongText',  'param'),
    ('InputField', 'Name'):            ('ComponentInstance', 'runtime_service_fieldservice:dcName',       'param'),
    ('InputField', 'Toggle'):          ('ComponentInstance', 'runtime_service_fieldservice:dcToggle',     'param'),
    ('InputField', 'Address'):         ('ComponentInstance', 'runtime_service_fieldservice:dcAddress',    'param'),
    ('InputField', 'Lookup'):          ('ComponentInstance', 'runtime_service_fieldservice:dcLookup',     'param'),
    ('InputField', 'Counter'):         ('ComponentInstance', 'runtime_service_fieldservice:dcCounter',    'param'),
    ('InputField', 'Matrix'):          ('ComponentMultiChoice','runtime_service_fieldservice:dcMatrix',   'fieldtext'),
    ('InputField', None):              ('ComponentInstance', 'runtime_service_fieldservice:dcTextInput', 'param'),
    # LargeTextArea
    ('LargeTextArea', None):           ('ComponentInstance', 'runtime_service_fieldservice:dcLongText',  'param'),
}

EXTENSION_MAP = {
    'forceContent:fileUpload': ('ComponentInstance', 'runtime_service_fieldservice:dcUpFile', 'param'),
    'forceContent:imageUpload': ('ComponentInstance', 'runtime_service_fieldservice:dcUpImage', 'param'),
    'forceContent:fileView': ('ComponentInstance', 'runtime_service_fieldservice:dcFileView', 'param'),
}

# Required inputParameters for ComponentChoice types (must be REMOVED)
CHOICE_INVALID_ATTRS = frozenset((
    'dataType', 'defaultValue', 'storeOutputAutomatically',
    'inputsOnNextNavToAssocScrn', 'styleProperties', 'inputParameters',
))

# Required attributes for ComponentChoice (must be PRESENT)
CHOICE_REQUIRED = {
    'storeOutputAutomatically': 'true',
    'inputsOnNextNavToAssocScrn': 'UseStoredValues',
}

# Invalid inputParameter names on dc* components
INVALID_PARAMS = frozenset(('required', 'disabled', 'multiple', 'accept', 'helpText', 'placeholder'))

# dc* ComponentInstance extensions that do NOT expose a `required` input
# attribute — injecting one deploys as "We can't find this input attribute:
# 'required'". Confirmed for dcCheckbox (W-24086520); dcToggle is the other
# boolean-backed component and excluded on the same rationale: an unchecked/
# off boolean is itself a valid answer, so these components have no notion of
# "required" distinct from <isRequired> already being set on the field.
NO_REQUIRED_INPUT_PARAM_EXTENSIONS = frozenset((
    'runtime_service_fieldservice:dcCheckbox',
    'runtime_service_fieldservice:dcToggle',
))

# ──────────────────────────────────────────────
# Phase 1: Screen field transformation
# ──────────────────────────────────────────────

def transform_screen_fields(root: ET.Element) -> Tuple[int, Dict[str, str]]:
    """
    Convert all screen fields to DC-compatible format.
    Returns (fields_converted, output_var_map) where output_var_map maps
    old outputAssignment variable names to new {fieldName.value} references.
    """
    converted = 0
    output_var_map: Dict[str, str] = {}  # old_var → new_reference

    for screen in findall(root, 'screens'):
        screen_name = findtext(screen, 'name') or 'Screen'
        for field in findall(screen, 'fields'):
            ft = findtext(field, 'fieldType') or ''
            ext = findtext(field, 'extensionName') or ''
            dt = findtext(field, 'dataType')
            fname = findtext(field, 'name') or 'field'

            # Collect outputAssignments before removing them
            for oa in findall(field, 'outputAssignments'):
                assign_to = findtext(oa, 'assignToReference')
                output_name = findtext(oa, 'name') or 'value'
                if assign_to:
                    # Detect duplicate assignments to same variable
                    if assign_to in output_var_map:
                        print(f"  WARNING: Multiple fields assign to variable '{assign_to}'. "
                              f"Previous: {output_var_map[assign_to]}, Now: {fname}.{output_name}. "
                              f"Only the last assignment will be preserved.", file=sys.stderr)

                    # Map old variable → new DC accessor
                    if output_name in ('value',):
                        output_var_map[assign_to] = f'{fname}.value'
                    elif output_name in ('selectedChoiceValues',):
                        output_var_map[assign_to] = f'{fname}.selectedChoiceValues'
                    else:
                        output_var_map[assign_to] = f'{fname}.{output_name}'
                field.remove(oa)

            # Already a DC component — just clean up invalid attributes
            if ext.startswith('runtime_service_fieldservice:dc'):
                _clean_dc_field(field, ft)
                continue

            # DisplayText — pass through, just remove outputAssignments (done above)
            if ft == 'DisplayText':
                continue

            # Repeater — pass through
            if ft == 'Repeater':
                continue

            # RegionContainer / Region — pass through
            if ft in ('RegionContainer', 'Region'):
                continue

            # Check extension map first
            if ext in EXTENSION_MAP:
                new_ft, new_ext, label_style = EXTENSION_MAP[ext]
                _apply_component_type(field, new_ft, new_ext, label_style, fname)
                converted += 1
                continue

            # Look up in field type map
            key = (ft, dt) if (ft, dt) in FIELD_TYPE_MAP else (ft, None)
            if key in FIELD_TYPE_MAP:
                new_ft, new_ext, label_style = FIELD_TYPE_MAP[key]
                _apply_component_type(field, new_ft, new_ext, label_style, fname)
                converted += 1
            # else: unknown type — leave as-is, deploy will surface the error

    return converted, output_var_map


def _apply_component_type(field: ET.Element, new_ft: str, new_ext: str, label_style: str, fname: str):
    """Set fieldType, extensionName, label, and required attributes on a field."""
    field_text = findtext(field, 'fieldText') or fname

    # Remove elements we're replacing
    for bad in ('fieldType', 'extensionName', 'dataType', 'defaultValue'):
        for el in findall(field, bad):
            field.remove(el)

    # Remove invalid inputParameters
    for ip in findall(field, 'inputParameters'):
        pname = findtext(ip, 'name')
        if pname in INVALID_PARAMS:
            field.remove(ip)

    # Set new fieldType and extensionName
    ft_el = make('fieldType', new_ft)
    ext_el = make('extensionName', new_ext)

    # Insert at beginning (after name)
    name_el = findall(field, 'name')
    insert_pos = 1 if name_el else 0
    field.insert(insert_pos, ext_el)
    field.insert(insert_pos, ft_el)

    if new_ft == 'ComponentInstance':
        _clean_dc_field(field, new_ft)
        # Ensure label inputParameter
        has_label = any(findtext(p, 'name') == 'label' for p in findall(field, 'inputParameters'))
        if not has_label and label_style == 'param':
            ip = make('inputParameters')
            ip.append(make('name', 'label'))
            v = sub(ip, 'value')
            v.append(make('stringValue', field_text))
            field.append(ip)

        # dc* ComponentInstance fields are LWC extension components that read
        # their own config from inputParameters, not from the flow-level
        # <isRequired> flag — Flow Builder itself emits a `required`
        # inputParameter alongside <isRequired> for these fields, and without
        # it the DC runtime silently treats the field as optional even though
        # <isRequired>true</isRequired> is present and Flow Builder's preview
        # shows it as required. (ComponentChoice/ComponentMultiChoice fields
        # don't need this — they read <isRequired> directly.)
        is_required = (findtext(field, 'isRequired') or 'false').lower() == 'true'
        has_required_param = any(findtext(p, 'name') == 'required' for p in findall(field, 'inputParameters'))
        if not has_required_param and new_ext not in NO_REQUIRED_INPUT_PARAM_EXTENSIONS:
            ip = make('inputParameters')
            ip.append(make('name', 'required'))
            v = sub(ip, 'value')
            v.append(make('booleanValue', 'true' if is_required else 'false'))
            field.append(ip)

    elif new_ft in ('ComponentChoice', 'ComponentMultiChoice'):
        # Remove invalid attributes
        for bad in ('storeOutputAutomatically', 'inputsOnNextNavToAssocScrn',
                    'inputParameters', 'styleProperties'):
            for el in findall(field, bad):
                field.remove(el)
        # Ensure fieldText (label for choice components)
        if findtext(field, 'fieldText') is None:
            field.append(make('fieldText', field_text))
        # Add required attributes
        field.append(make('storeOutputAutomatically', 'true'))
        field.append(make('inputsOnNextNavToAssocScrn', 'UseStoredValues'))


def _clean_dc_field(field: ET.Element, ft: str):
    """Clean a ComponentInstance field: remove invalid attrs, add required ones."""
    # Remove invalid inputParameters
    for ip in findall(field, 'inputParameters'):
        if findtext(ip, 'name') in INVALID_PARAMS:
            field.remove(ip)

    # Remove defaultValue (DC uses value inputParameter)
    for el in findall(field, 'defaultValue'):
        field.remove(el)

    if ft == 'ComponentInstance':
        # dc* ComponentInstance fields render their own label from the
        # `label` inputParameter; a leftover <fieldText> from the source
        # InputField/etc. field breaks rendering at DC runtime (screen gets
        # stuck with no Next/footer) even though it deploys and previews
        # fine in Flow Builder.
        for el in findall(field, 'fieldText'):
            field.remove(el)

        if findtext(field, 'storeOutputAutomatically') is None:
            field.append(make('storeOutputAutomatically', 'true'))
        if findtext(field, 'inputsOnNextNavToAssocScrn') is None:
            field.append(make('inputsOnNextNavToAssocScrn', 'UseStoredValues'))
        if findtext(field, 'styleProperties') is None:
            sp = make('styleProperties')
            va = sub(sp, 'verticalAlignment')
            va.append(make('stringValue', 'top'))
            w = sub(sp, 'width')
            w.append(make('stringValue', '12'))
            field.append(sp)


def regroup_root_children(root: ET.Element):
    """Regroup root's direct children so each element type is contiguous.

    excise_and_placeholder() always root.append()s new placeholder <screens>
    (used by CUD excision, ACTION_CALL_EXCISED, and PLATFORM_EVENT_EXCISED),
    landing them after whatever tag currently sits last (subflows, variables,
    ...) — breaking contiguity with the flow's original <screens> block and
    causing the deploy error "Element screens is duplicated at this location".
    Mirrors the variables regroup in ensure_dc_variables, generalized to any
    tag, and run once at the very end so it catches every excision site
    regardless of which phase ran it.
    """
    children = list(root)
    grouped: OrderedDict = OrderedDict()
    for child in children:
        lname = local(child)
        grouped.setdefault(lname, []).append(child)
    for child in children:
        root.remove(child)
    for children_list in grouped.values():
        for child in children_list:
            root.append(child)


def reorder_field_children(root: ET.Element):
    """Reorder screen field children so inputParameters are contiguous."""
    ORDER = ['name', 'extensionName', 'fieldType', 'fieldText', 'choiceReferences',
             'dynamicChoicesSets', 'isRequired', 'inputParameters',
             'storeOutputAutomatically', 'inputsOnNextNavToAssocScrn',
             'validationRule', 'visibilityRule', 'styleProperties']

    for screen in findall(root, 'screens'):
        for field in findall(screen, 'fields'):
            children = list(field)
            if not children:
                continue
            grouped: OrderedDict = OrderedDict()
            for child in children:
                lname = local(child)
                if lname not in grouped:
                    grouped[lname] = []
                grouped[lname].append(child)
            for child in children:
                field.remove(child)
            for key in ORDER:
                for child in grouped.pop(key, []):
                    field.append(child)
            for children_list in grouped.values():
                for child in children_list:
                    field.append(child)


# ──────────────────────────────────────────────
# Phase 2: Inject assignment nodes for output vars
# ──────────────────────────────────────────────

def inject_output_assignments(root: ET.Element, output_var_map: Dict[str, str]) -> int:
    """
    For each screen that had outputAssignments, inject an <assignments> node
    after the screen to map field output references to the old variable names.
    This preserves compatibility with downstream inputAssignments.
    """
    if not output_var_map:
        return 0

    injected = 0
    for screen in findall(root, 'screens'):
        sname = findtext(screen, 'name') or ''
        # Find if any field in this screen had output vars
        screen_fields = {findtext(f, 'name') for f in findall(screen, 'fields')}

        relevant_vars = {
            old_var: new_ref
            for old_var, new_ref in output_var_map.items()
            if new_ref.split('.')[0] in screen_fields
        }

        if not relevant_vars:
            continue

        # Get current connector target of this screen
        screen_successor = None
        for conn in findall(screen, 'connector'):
            screen_successor = findtext(conn, 'targetReference')

        # Create assignment node
        assign_name = f'Assign_{sname}_outputs'
        assign_el = make('assignments')
        assign_el.append(make('name', assign_name))
        assign_el.append(make('label', f'Assign {sname} outputs'))
        assign_el.append(make('locationX', '176'))
        assign_el.append(make('locationY', '0'))

        for old_var, new_ref in relevant_vars.items():
            item = sub(assign_el, 'assignmentItems')
            item.append(make('assignToReference', old_var))
            item.append(make('operator', 'Assign'))
            v = sub(item, 'value')
            v.append(make('elementReference', new_ref))

        # Connect: screen → assign → screen_successor
        # Update screen connector to point to assignment
        for conn in findall(screen, 'connector'):
            for tr in findall(conn, 'targetReference'):
                tr.text = assign_name

        # Connect assignment to screen's old successor
        if screen_successor:
            conn_el = sub(assign_el, 'connector')
            conn_el.append(make('targetReference', screen_successor))

        root.append(assign_el)
        injected += 1

    return injected


# ──────────────────────────────────────────────
# Phase 3: CUD ordering enforcement
# ──────────────────────────────────────────────

def _resolve_fault_path_violations(
        root: ET.Element, is_subflow: bool
) -> Tuple[int, int, List[str], List[Dict]]:
    """Sever every CUD→non-CUD fault edge and prune orphaned handler chains.

    Returns (fixed, skipped, warnings, excision_flags). For a top-level flow
    (is_subflow=False) fault edges are left in place and each is reported as a
    manual-review warning, consistent with the existing warn-only behavior for
    other unrelocatable violations.
    """
    fixed = 0
    skipped = 0
    warnings: List[str] = []
    flags: List[Dict] = []

    nodes, _ = build_graph(root)
    severed_targets: Set[str] = set()
    for cud_name, (ntype, cud_el, _targets) in nodes.items():
        if ntype not in CUD_TYPES:
            continue
        for ft in get_fault_targets(cud_el):
            if ft in nodes and nodes[ft][0] not in CUD_TYPES:
                if not is_subflow:
                    warnings.append(
                        f'CUD "{cud_name}" has a fault path to non-CUD '
                        f'[{nodes[ft][0]}] {ft}, which DataCaptureFlow rejects. '
                        f'Top-level flow left unchanged — remove or restructure '
                        f'the fault handler manually in Flow Builder.'
                    )
                    skipped += 1
                    continue
                if _remove_fault_connector(cud_el, ft):
                    severed_targets.add(ft)
                    fixed += 1

    if severed_targets:
        flags.extend(_prune_unreachable_from(root, severed_targets))
    return fixed, skipped, warnings, flags


def enforce_cud_at_end(root: ET.Element, is_subflow: bool = False) -> Tuple[int, int, List[str], List[Dict]]:
    """
    Restructure the flow so all CUD operations occur after the last screen.
    Returns (fixed_count, skipped_count, warning_messages, excision_flags).

    Patterns handled:
    A: CUD → Screen       → move screen to before CUD (confirmation pattern)
    B: CUD → Lookup       → hoist lookup to before first screen
    C: CUD → Assignment   → hoist assignment to before first screen

    When is_subflow=True, a CUD that none of the above patterns can relocate
    is excised along with its single direct gating Decision (DataCaptureFlow
    subflows cannot contain CUD at all) instead of being left as a warning.
    """
    fixed = 0
    skipped = 0
    warnings = []
    excision_flags: List[Dict] = []
    max_iterations = 50  # guard against infinite loops

    # Pre-pass: resolve CUD fault-path violations before the success-path loop.
    # A CUD's fault handler (e.g. Set_FlowError → error screen) can never be made
    # compliant: non-CUD elements are illegal after a CUD on the fault path too,
    # and a fault handler only runs if the CUD failed, so it cannot be hoisted
    # before the CUD the way patterns A-D relocate success-path targets. The
    # hoist patterns also never touch <faultConnector>, so feeding a fault-path
    # violation into them rewrites the wrong (success) edge and thrashes to the
    # iteration cap. Sever fault edges here and prune the orphaned handler chain,
    # leaving the iterative loop below to see a graph with only success edges.
    f_fixed, f_skipped, f_warnings, f_flags = _resolve_fault_path_violations(
        root, is_subflow)
    fixed += f_fixed
    skipped += f_skipped
    warnings.extend(f_warnings)
    excision_flags.extend(f_flags)

    for _ in range(max_iterations):
        nodes, start_target = build_graph(root)
        order = bfs_order(nodes, start_target)
        violations = find_violations(nodes)

        if not violations:
            break

        made_progress = False
        else_branch_hits = []  # (vtype, vname) warned+skipped via the else branch this iteration

        for vtype, vname in violations:
            nodes, start_target = build_graph(root)  # refresh after each fix
            order = bfs_order(nodes, start_target)

            if vname not in nodes:
                continue

            # Find which CUD node(s) directly point to this violating node
            cud_preds = [
                p for p in predecessors_of(root, vname)
                if p != '__start__' and p in nodes and nodes[p][0] in CUD_TYPES
            ]

            if not cud_preds:
                # Not directly connected from CUD — might be reachable through
                # another violated node; skip for now, will be picked up next iteration
                continue

            cud_name = cud_preds[0]
            _, cud_el, _ = nodes[cud_name]
            _, violating_el, v_targets = nodes[vname]

            # ── Pattern A: CUD → Screen ──────────────────────────
            if vtype == 'screens':
                # Move confirmation screen to BEFORE the CUD chain starts.
                # Find the first CUD node in execution order.
                first_cud = next((n for n in order if n in nodes and nodes[n][0] in CUD_TYPES), None)
                if not first_cud:
                    skipped += 1
                    warnings.append(f'Cannot fix screen {vname}: no first CUD found')
                    continue

                # Find predecessors of first_cud (non-CUD)
                first_cud_preds = [
                    p for p in predecessors_of(root, first_cud)
                    if p != '__start__' and (p not in nodes or nodes[p][0] not in CUD_TYPES)
                ]
                first_cud_is_start = '__start__' in predecessors_of(root, first_cud)

                # What does the screen currently point to?
                screen_successor = v_targets[0] if v_targets else None

                # Disconnect CUD from screen
                update_all_connectors(root, vname, screen_successor or '')

                # Connect screen to the first CUD
                for conn in findall(violating_el, 'connector') + findall(violating_el, 'defaultConnector'):
                    for tr in findall(conn, 'targetReference'):
                        tr.text = first_cud

                # Rewire: predecessor of first_cud now points to screen
                if first_cud_is_start:
                    set_start_target(root, vname)
                for pred in first_cud_preds:
                    if pred in nodes:
                        update_all_connectors(root, first_cud, vname)
                        # But only for this predecessor, not globally!
                        # Use targeted update on the predecessor element
                        _, pred_el, _ = nodes[pred]
                        # Undo global update, do targeted
                        update_all_connectors(root, vname, first_cud)
                        # Now do targeted
                        _replace_target_in_node(pred_el, first_cud, vname)

                fixed += 1
                made_progress = True
                break  # restart iteration

            # ── Pattern B: CUD → Lookup ──────────────────────────
            elif vtype == 'recordLookups':
                # Hoist the lookup to execute before the first screen.
                # Find the first screen in execution order.
                first_screen = next(
                    (n for n in order if n in nodes and nodes[n][0] == 'screens'), None
                )

                # What does the lookup currently point to?
                lookup_successor = v_targets[0] if v_targets else None

                # Disconnect CUD → Lookup; CUD now points to what lookup pointed to
                update_all_connectors(root, vname, lookup_successor or '')

                # Insert lookup before first screen (or at start if no screens)
                if first_screen:
                    first_screen_preds = [
                        p for p in predecessors_of(root, first_screen)
                        if p != vname  # don't include ourselves
                    ]
                    if '__start__' in first_screen_preds:
                        set_start_target(root, vname)
                        # Lookup → first_screen
                        _set_first_connector(violating_el, first_screen)
                    else:
                        for pred in first_screen_preds:
                            if pred and pred in nodes:
                                _replace_target_in_node(nodes[pred][1], first_screen, vname)
                                break
                        _set_first_connector(violating_el, first_screen)
                else:
                    # No screens — insert at start
                    old_start = get_start_target(root)
                    set_start_target(root, vname)
                    _set_first_connector(violating_el, old_start or '')

                fixed += 1
                made_progress = True
                break  # restart iteration

            # ── Pattern C: CUD → Assignment ──────────────────────
            elif vtype == 'assignments':
                # Same as Pattern B — hoist before first screen
                first_screen = next(
                    (n for n in order if n in nodes and nodes[n][0] == 'screens'), None
                )
                assign_successor = v_targets[0] if v_targets else None
                update_all_connectors(root, vname, assign_successor or '')

                if first_screen:
                    first_screen_preds = [
                        p for p in predecessors_of(root, first_screen)
                        if p != vname
                    ]
                    if '__start__' in first_screen_preds:
                        set_start_target(root, vname)
                        _set_first_connector(violating_el, first_screen)
                    else:
                        for pred in first_screen_preds:
                            if pred and pred in nodes:
                                _replace_target_in_node(nodes[pred][1], first_screen, vname)
                                break
                        _set_first_connector(violating_el, first_screen)
                else:
                    old_start = get_start_target(root)
                    set_start_target(root, vname)
                    _set_first_connector(violating_el, old_start or '')

                fixed += 1
                made_progress = True
                break

            # ── Pattern D: CUD → Decision (complex) ──────────────
            elif vtype == 'decisions':
                # A decision after CUD is allowed ONLY if it only has CUD branches.
                # If it has mixed branches, we need to move it before CUD.
                # For safety, hoist before first screen.
                first_screen = next(
                    (n for n in order if n in nodes and nodes[n][0] == 'screens'), None
                )
                dec_successor = v_targets[0] if v_targets else None
                update_all_connectors(root, vname, dec_successor or '')

                if first_screen:
                    first_screen_preds = [p for p in predecessors_of(root, first_screen)
                                          if p != vname]
                    if '__start__' in first_screen_preds:
                        set_start_target(root, vname)
                        # Decision's default connector → first_screen
                        for conn in findall(violating_el, 'defaultConnector'):
                            for tr in findall(conn, 'targetReference'):
                                tr.text = first_screen
                    else:
                        for pred in first_screen_preds:
                            if pred and pred in nodes:
                                _replace_target_in_node(nodes[pred][1], first_screen, vname)
                                break
                        for conn in findall(violating_el, 'defaultConnector'):
                            for tr in findall(conn, 'targetReference'):
                                tr.text = first_screen

                fixed += 1
                made_progress = True
                break

            else:
                msg = (
                    f'Cannot auto-fix [{vtype}] {vname} after CUD. '
                    f'Review and fix manually in Flow Builder.'
                )
                warnings.append(msg)
                skipped += 1
                else_branch_hits.append((vtype, vname, msg))

        if not made_progress:
            # Stuck — report remaining violations
            nodes, start_target = build_graph(root)
            order = bfs_order(nodes, start_target)
            remaining = find_violations(nodes)
            if is_subflow:
                handled_cuds = set()
                for vt, vn in remaining:
                    cud_preds = [
                        p for p in predecessors_of(root, vn)
                        if p != '__start__' and p in nodes and nodes[p][0] in CUD_TYPES
                    ]
                    for cud_name in cud_preds:
                        if cud_name in handled_cuds:
                            continue
                        handled_cuds.add(cud_name)
                        gate_preds = [
                            p for p in predecessors_of(root, cud_name)
                            if p != '__start__' and p in nodes and nodes[p][0] == 'decisions'
                        ]
                        if len(gate_preds) > 1:
                            warnings.append(
                                f'CUD "{cud_name}" has multiple gating Decisions '
                                f'({", ".join(gate_preds)}); only "{gate_preds[0]}" was '
                                f'excised with it — review the others manually in Flow Builder.'
                            )
                        group = ([gate_preds[0], cud_name] if gate_preds else [cud_name])
                        excision_flags.extend(
                            excise_and_placeholder(
                                root, group, 'CUD_EXCISED_IN_SUBFLOW',
                                f'CUD "{cud_name}" could not be relocated to the end of '
                                f'the subflow by any of the four hoist patterns; DataCaptureFlow '
                                f'subflows cannot contain CUD, so it was excised with its '
                                f'gating Decision.'))
                # Re-check: excising may have created fresh non-CUD-only successors that
                # are now compliant (the CUD is gone). Recompute once more; anything still
                # left is a genuinely different, non-CUD violation shape — warn as before.
                nodes, start_target = build_graph(root)
                order = bfs_order(nodes, start_target)
                remaining = find_violations(nodes)
                # The main loop's else branch (above) may have already warned+skipped
                # some of these same violations earlier in THIS iteration, before we
                # knew excision would resolve them. Strip those now-stale entries so
                # a resolved violation doesn't surface both a warning and a flag.
                remaining_set = set(remaining)
                for vt, vn, msg in else_branch_hits:
                    if (vt, vn) not in remaining_set:
                        if msg in warnings:
                            warnings.remove(msg)
                            skipped -= 1
            for vt, vn in remaining:
                warnings.append(
                    f'Could not auto-fix [{vt}] {vn} after CUD — '
                    f'complex dependency. Fix manually in Flow Builder.'
                )
                skipped += 1
            break

    # Unconditional CUD ban for subflows. The ordering loop above only excises
    # CUD that is implicated in an ordering violation, but a DataCaptureFlow used
    # as a subflow may contain NO CUD at all — even a self-ordered CUD chain
    # (e.g. Update → Create → terminal) is rejected by the calling flow with
    # "You can't use Create, Update, or Delete elements in a Data Capture flow
    # subflow." So after the ordering pass has done its work, sweep every CUD
    # node still present and excise it too. Runs after _resolve_fault_path_
    # violations and the main loop, so it operates on the final, fault-cleaned
    # graph.
    if is_subflow:
        for _ in range(max_iterations):
            nodes, _ = build_graph(root)
            remaining_cuds = [n for n, (nt, _e, _t) in nodes.items() if nt in CUD_TYPES]
            if not remaining_cuds:
                break
            cud_name = remaining_cuds[0]
            gate_preds = [
                p for p in predecessors_of(root, cud_name)
                if p != '__start__' and p in nodes and nodes[p][0] == 'decisions'
            ]
            if len(gate_preds) > 1:
                warnings.append(
                    f'CUD "{cud_name}" has multiple gating Decisions '
                    f'({", ".join(gate_preds)}); only "{gate_preds[0]}" was '
                    f'excised with it — review the others manually in Flow Builder.'
                )
            group = ([gate_preds[0], cud_name] if gate_preds else [cud_name])
            excision_flags.extend(
                excise_and_placeholder(
                    root, group, 'CUD_EXCISED_IN_SUBFLOW',
                    f'CUD "{cud_name}" was excised because DataCaptureFlow subflows '
                    f'cannot contain any Create, Update, or Delete elements'
                    + (f'; its gating Decision "{gate_preds[0]}" was excised with it.'
                       if gate_preds else '.')))

    return fixed, skipped, warnings, excision_flags


def _replace_target_in_node(node_el: ET.Element, old: str, new: str):
    """Replace old target with new in all connectors of a single node."""
    for conn in (findall(node_el, 'connector') +
                 findall(node_el, 'defaultConnector') +
                 findall(node_el, 'nextValueConnector') +
                 findall(node_el, 'noMoreValuesConnector') +
                 findall(node_el, 'faultConnector')):
        for tr in findall(conn, 'targetReference'):
            if tr.text == old:
                tr.text = new
    for rule in findall(node_el, 'rules'):
        for conn in findall(rule, 'connector'):
            for tr in findall(conn, 'targetReference'):
                if tr.text == old:
                    tr.text = new


def _remove_fault_connector(node_el: ET.Element, target: str) -> bool:
    """Delete the <faultConnector> on node_el whose targetReference is `target`.

    Success connectors are left untouched — this is deliberately fault-only so a
    CUD's illegal fault edge can be severed without disturbing its success path.
    """
    removed = False
    for conn in findall(node_el, 'faultConnector'):
        if findtext(conn, 'targetReference') == target:
            node_el.remove(conn)
            removed = True
    return removed


def _prune_unreachable_from(root: ET.Element, candidate_roots: Set[str]) -> List[Dict]:
    """Remove nodes that became unreachable after fault edges were severed.

    Only descendants of `candidate_roots` (the severed fault targets) that are no
    longer reachable from start are removed, so pre-existing dead code is left
    alone. Returns one manual-review flag per removed node.
    """
    nodes, start = build_graph(root)
    reachable = set(bfs_order(nodes, start))

    to_remove: List[str] = []
    seen: Set[str] = set()
    stack = [r for r in candidate_roots if r in nodes and r not in reachable]
    while stack:
        n = stack.pop()
        if n in seen or n not in nodes or n in reachable:
            continue
        seen.add(n)
        to_remove.append(n)
        for t in nodes[n][2]:
            if t not in reachable and t not in seen:
                stack.append(t)

    flags = []
    for n in to_remove:
        _, el, _ = nodes[n]
        root.remove(el)
        flags.append(build_excision_flag(
            n, 'CUD_FAULT_PATH_EXCISED',
            f'"{n}" was only reachable as a fault handler downstream of a CUD. '
            f'DataCaptureFlow does not allow non-CUD elements after a CUD on any '
            f'path — including the fault path — and a fault handler cannot be '
            f'hoisted before the CUD, so it was removed.'))
    return flags


def _set_first_connector(node_el: ET.Element, target: str):
    """Set/update the first <connector> targetReference on a node."""
    for conn in findall(node_el, 'connector'):
        for tr in findall(conn, 'targetReference'):
            tr.text = target
            return
    # No connector exists — create one
    conn = sub(node_el, 'connector')
    conn.append(make('targetReference', target))


def excise_and_placeholder(root: ET.Element, node_names: List[str], code: str,
                            why: str) -> List[Dict]:
    """Excise an ordered group of nodes, insert one placeholder Screen per
    excised node (chained in order), rewire predecessor -> placeholders ->
    original downstream, and return one manual-review flag dict per node.

    If the flow's start target points directly at ANY name in node_names, the
    start target is redirected to the first placeholder instead of (or in
    addition to) rewiring predecessor elements.

    Predecessors are resolved for the WHOLE group, not just node_names[0]:
    some other node in the flow may point directly at a later member of the
    group (e.g. straight at the CUD, bypassing its gating Decision). Every
    such external predecessor (excluding predecessors that are themselves
    members of the group — those are internal edges removed along with the
    group) gets every group-member reference it holds redirected to the
    first placeholder, since the whole group collapses down to the
    placeholder chain that starts there. Skipping this for multi-member
    groups leaves a dangling <targetReference> once the group's elements are
    removed below.

    node_names: ordered API names to excise as one group (CUD case:
    [decision_name, cud_name]; the other two excision sites pass a single-
    element list).
    """
    nodes, _ = build_graph(root)
    name_set = set(node_names)

    preds_by_name = {n: predecessors_of(root, n) for n in node_names}
    from_start = any('__start__' in preds_by_name[n] for n in node_names)
    pred_names = {
        p for n in node_names for p in preds_by_name[n]
        if p != '__start__' and p not in name_set and p in nodes
    }
    pred_elements = [nodes[p][1] for p in pred_names]

    _, last_el, _ = nodes[node_names[-1]]
    downstream_targets = get_connector_targets(last_el)
    downstream = downstream_targets[0] if downstream_targets else None

    elements_to_remove = [nodes[n][1] for n in node_names]
    orig_locations = {
        n: (findtext(el, 'locationX'), findtext(el, 'locationY'))
        for n, el in zip(node_names, elements_to_remove)
    }
    for el in elements_to_remove:
        root.remove(el)

    placeholder_names = [f'{n}_Excised_Placeholder' for n in node_names]
    placeholders = []
    for name, orig_name in zip(placeholder_names, node_names):
        loc_x, loc_y = orig_locations[orig_name]
        screen = make('screens')
        screen.append(make('name', name))
        screen.append(make('label', name))
        screen.append(make('locationX', loc_x if loc_x is not None else '176'))
        screen.append(make('locationY', loc_y if loc_y is not None else '0'))
        field = sub(screen, 'fields')
        field.append(make('name', f'{name}_Field'))
        field.append(make('fieldType', 'DisplayText'))
        field.append(make('fieldText',
            f"ATTENTION: The original {orig_name} was dropped since it is not "
            f"compliant with data capture. More info in the migration summary."))
        screen.append(make('allowFinish', 'true'))
        screen.append(make('showFooter', 'true'))
        screen.append(make('nextOrFinishButtonLabel', 'Next'))
        placeholders.append(screen)

    for i in range(len(placeholders) - 1):
        conn = sub(placeholders[i], 'connector')
        conn.append(make('targetReference', placeholder_names[i + 1]))
    if downstream:
        conn = sub(placeholders[-1], 'connector')
        conn.append(make('targetReference', downstream))

    for screen in placeholders:
        root.append(screen)

    if from_start:
        set_start_target(root, placeholder_names[0])
    for pred_el in pred_elements:
        for n in node_names:
            _replace_target_in_node(pred_el, n, placeholder_names[0])

    return [build_excision_flag(n, code, why) for n in node_names]


# ──────────────────────────────────────────────
# Phase 4: DC structural requirements
# ──────────────────────────────────────────────

# Builder-selection processMetadataValues that steer Flow Builder to the modern
# auto-layout Lightning canvas. Values match build_flow.py (native build path).
BUILDER_METADATA = (
    ('BuilderType',       'LightningFlowBuilder'),
    ('OriginBuilderType', 'LightningFlowBuilder'),
    ('CanvasMode',        'AUTO_LAYOUT_CANVAS'),
)


def set_builder_metadata(root: ET.Element):
    """Ensure BuilderType/OriginBuilderType/CanvasMode processMetadataValues are
    present with the auto-layout Lightning values.

    Adds missing entries; overwrites an existing entry's stringValue (e.g. FSM's
    CanvasMode=FREE_FORM_CANVAS) so the migrated flow opens in the same builder as a
    natively-built DataCaptureFlow. Other processMetadataValues are left untouched.
    """
    existing = {findtext(p, 'name'): p for p in findall(root, 'processMetadataValues')}
    for name, string_value in BUILDER_METADATA:
        pmv = existing.get(name)
        if pmv is None:
            pmv = make('processMetadataValues')
            sub(pmv, 'name', name)
            value = sub(pmv, 'value')
            sub(value, 'stringValue', string_value)
            root.append(pmv)
        else:
            value_els = findall(pmv, 'value')
            value = value_els[0] if value_els else sub(pmv, 'value')
            sv_els = findall(value, 'stringValue')
            if sv_els:
                sv_els[0].text = string_value
            else:
                sub(value, 'stringValue', string_value)


def apply_dc_metadata(root: ET.Element):
    """Change processType, fix environments, remove invalid metadata."""
    # processType
    for pt in findall(root, 'processType'):
        pt.text = 'DataCaptureFlow'

    # Remove apiVersion
    for av in findall(root, 'apiVersion'):
        root.remove(av)

    # areMetricsLoggedToDataCloud
    for el in findall(root, 'areMetricsLoggedToDataCloud'):
        root.remove(el)

    # Force status to Draft: a migrated flow must deploy INACTIVE so it is
    # validated in Flow Builder and device-tested before going live (skill
    # Step 8). The source flow's <status>Active</status> must not carry over,
    # or the deploy silently activates a never-tested flow.
    status_els = findall(root, 'status')
    if status_els:
        for st in status_els:
            st.text = 'Draft'
    else:
        root.append(make('status', 'Draft'))

    # environments: replace Default with Offline, or add if missing
    envs = findall(root, 'environments')
    if envs:
        for env in envs:
            if env.text in (None, 'Default', ''):
                env.text = 'Offline'
    else:
        root.append(make('environments', 'Offline'))

    # Remove Constants (not allowed in DataCaptureFlow)
    for el in findall(root, 'constants'):
        root.remove(el)

    # Builder-selection metadata. Flow Builder chooses its canvas/chrome from these
    # processMetadataValues, NOT from processType — a DataCaptureFlow lacking them (or
    # carrying FSM's CanvasMode=FREE_FORM_CANVAS) opens in the legacy free-form builder
    # instead of the modern auto-layout Lightning builder that a natively-built DC flow
    # gets. Force the auto-layout values so migrated flows open the same way.
    set_builder_metadata(root)

    # status: always emit Draft. The source flow's status (often Active) must
    # NOT leak through — a migrated flow is unproven until its dry-run passes and
    # it has been tested on device. deploy_flow.sh also force-rewrites <status>
    # to Draft at the deploy boundary, so this holds even for a hand-edited file.
    # Activation is a manual admin action in the org UI (SKILL.md Step 8), never
    # scripted or inherited from the source.
    status_els = findall(root, 'status')
    if status_els:
        for el in status_els:
            el.text = 'Draft'
    else:
        root.append(make('status', 'Draft'))


def ensure_screen_attrs(root: ET.Element):
    """Add required DataCaptureFlow screen attributes if missing."""
    for screen in findall(root, 'screens'):
        for attr, val in [('allowFinish', 'true'),
                          ('showFooter', 'true'),
                          ('nextOrFinishButtonLabel', 'Next')]:
            if findtext(screen, attr) is None:
                screen.append(make(attr, val))

        # DC's runtime uses allowFinish as the footer-render gate, not as a
        # "this is the last screen" marker like classic Screen Flow — a
        # legacy FieldServiceMobile screen correctly carrying
        # allowFinish=false (non-terminal, has an outgoing connector) leaves
        # the DC screen with no footer/Next button at all, blocking
        # navigation. Navigation still follows the connector graph, so this
        # is safe to force true on every screen regardless of position.
        for el in findall(screen, 'allowFinish'):
            el.text = 'true'


# Canvas node element types the Metadata API requires to carry locationX/locationY.
CANVAS_NODE_TYPES = frozenset((
    'screens', 'decisions', 'recordLookups', 'recordCreates', 'recordUpdates',
    'recordDeletes', 'loops', 'assignments', 'subflows', 'actionCalls', 'waits',
    'steps', 'apexPluginCalls', 'collectionProcessors', 'customErrors',
    'recordRollbacks', 'transforms', 'orchestratedStages',
))


def ensure_node_locations(root: ET.Element):
    """Every canvas node element must carry locationX/locationY to deploy.

    Auto-layout ignores the coordinates at runtime, but the Metadata API schema
    still requires them present: a source flow authored (or retrieved) without
    canvas coords on a screen would otherwise produce a migrated flow that fails
    to deploy with "Required field is missing: locationX". Only excised
    placeholder screens got a coordinate fallback before; pass-through nodes kept
    whatever the source had (possibly nothing). Insert both right after <label>
    (or <name>), matching the schema element order, preserving any existing pair.
    """
    for el in list(root):
        if local(el) not in CANVAS_NODE_TYPES:
            continue
        x, y = el.find(tag('locationX')), el.find(tag('locationY'))
        if x is not None and y is not None:
            continue  # already positioned — leave real coords untouched
        xv = x.text if x is not None else '176'
        yv = y.text if y is not None else '0'
        for existing in (x, y):
            if existing is not None:
                el.remove(existing)
        pos = 0
        for i, child in enumerate(list(el)):
            if local(child) in ('name', 'label'):
                pos = i + 1
        el.insert(pos, make('locationY', yv))
        el.insert(pos, make('locationX', xv))


DC_INPUT_VARS = [
    ('recordId',         'String'),
    ('parentRecordId',   'String'),
    ('parentObjectType', 'String'),
]

def ensure_dc_variables(root: ET.Element):
    """
    Ensure required DC input variables exist with correct attributes.
    Uses case-insensitive dedup — if a var with the same name (any case) exists,
    update it to be isInput=true rather than adding a duplicate.
    """
    all_vars = findall(root, 'variables')
    var_by_lower = {(findtext(v, 'name') or '').lower(): v for v in all_vars}

    for var_name, data_type in DC_INPUT_VARS:
        existing = var_by_lower.get(var_name.lower())
        if existing is not None:
            # Ensure isInput=true
            isInput_elements = findall(existing, 'isInput')
            if isInput_elements:
                # Child exists - update it to 'true'
                for el in isInput_elements:
                    if el.text != 'true':
                        el.text = 'true'
            else:
                # Child missing - add it with 'true'
                existing.append(make('isInput', 'true'))
        else:
            var_el = make('variables')
            var_el.append(make('name', var_name))
            var_el.append(make('dataType', data_type))
            var_el.append(make('isCollection', 'false'))
            var_el.append(make('isInput', 'true'))
            var_el.append(make('isOutput', 'false'))
            root.append(var_el)

    # Regroup variables to be contiguous (Salesforce schema requirement)
    all_vars_refreshed = findall(root, 'variables')
    seen_names: Set[str] = set()
    unique_vars = []
    for v in all_vars_refreshed:
        vname = (findtext(v, 'name') or '').lower()
        if vname not in seen_names:
            seen_names.add(vname)
            unique_vars.append(v)
    for v in all_vars_refreshed:
        try:
            root.remove(v)
        except ValueError:
            pass
    for v in unique_vars:
        root.append(v)


def _field_is_multiselect(field: ET.Element) -> bool:
    """True if a dcLookup field carries isMultiSelection=true."""
    for ip in findall(field, 'inputParameters'):
        if findtext(ip, 'name') == 'isMultiSelection':
            for val in findall(ip, 'value'):
                if (findtext(val, 'booleanValue') or '').lower() == 'true':
                    return True
    return False


def _accessor_suffix(field: ET.Element) -> Optional[str]:
    """Return the DC accessor suffix for a screen field, or None when it can't
    be resolved from the field alone (unknown/unconverted type, or dcName which
    has two accessors — .firstName / .lastName — the caller must choose).

    Mirrors the accessor table in SKILL.md (## Visibility rule accessor suffixes):
      choice (dcPicklist/dcRbGroup/dcCbGroup) -> selectedChoiceValues
      dcToggle                                -> isActive
      dcLookup single                         -> recordId
      dcLookup multi (isMultiSelection=true)  -> recordIds
      dcName                                  -> None (ambiguous — warn)
      other ComponentInstance                 -> value
    """
    ft = findtext(field, 'fieldType') or ''
    ext = findtext(field, 'extensionName') or ''
    if ft in ('ComponentChoice', 'ComponentMultiChoice'):
        return 'selectedChoiceValues'
    if ft == 'ComponentInstance':
        if ext.endswith('dcToggle'):
            return 'isActive'
        if ext.endswith('dcLookup'):
            return 'recordIds' if _field_is_multiselect(field) else 'recordId'
        if ext.endswith('dcName'):
            return None  # ambiguous — .firstName / .lastName
        return 'value'
    return None  # unknown / unconverted field type


def fix_screen_field_references(root: ET.Element) -> List[str]:
    """
    In DataCaptureFlow, screen fields are accessed via a typed accessor suffix
    (not the bare field name).  Fix all downstream references in recordCreates,
    recordUpdates, decisions, assignments, and loops.  The suffix per component
    type is resolved by ``_accessor_suffix`` (see the SKILL.md accessor table).

    A bare reference to e.g. a Decision routing on a dcPicklist otherwise
    deploys with: "In a Decision Outcome, a condition doesn't support "X" Equals."

    Returns a list of warnings for references the transformer could not safely
    qualify — a field whose accessor is ambiguous (dcName) or whose type could
    not be converted — so a silent bare reference is surfaced pre-deploy rather
    than discovered at dry-run.
    """
    # Map each screen field name -> its DC accessor suffix (None = can't resolve).
    screen_field_suffix: Dict[str, Optional[str]] = {}
    for screen in findall(root, 'screens'):
        for field in findall(screen, 'fields'):
            fname = findtext(field, 'name')
            if fname:
                screen_field_suffix[fname] = _accessor_suffix(field)

    if not screen_field_suffix:
        return []

    warnings: List[str] = []
    warned: Set[str] = set()

    def qualify(er_el: ET.Element):
        """Qualify a bare screen-field reference in-place; warn if unresolvable."""
        name = er_el.text
        if not name or name not in screen_field_suffix:
            return  # not a screen field, or already qualified — leave alone
        suffix = screen_field_suffix[name]
        if suffix is None:
            if name not in warned:
                warned.add(name)
                warnings.append(
                    f"Screen field '{name}' is referenced downstream but its DC "
                    f"accessor can't be auto-resolved (dcName is .firstName/"
                    f".lastName; unconverted types have none). Qualify it "
                    f"manually before deploy or the reference stays bare.")
            return
        er_el.text = f'{name}.{suffix}'

    for ntype in ('recordCreates', 'recordUpdates', 'recordDeletes',
                  'decisions', 'assignments', 'loops', 'subflows'):
        for node in findall(root, ntype):
            for er in node.iter(tag('elementReference')):
                qualify(er)
            for er in node.iter('elementReference'):
                qualify(er)

    # Also fix decision leftValueReference elements. (rightValue is a container
    # of stringValue/elementReference children, not bare text — a screen-field
    # reference there arrives as a nested <elementReference>, already handled by
    # the 'decisions' branch above — so only leftValueReference is load-bearing.)
    for dec in findall(root, 'decisions'):
        for rule in findall(dec, 'rules'):
            for cond in findall(rule, 'conditions'):
                for lv in findall(cond, 'leftValueReference'):
                    qualify(lv)

    # Qualify {!merge} references to screen fields inside formula expressions and
    # DisplayText fieldText. A bare {!ClosingReading} (or a bare ClosingReading
    # inside a formula body like IF(ClosingReading > 100, ...)) leaves the flow
    # InvalidDraft in the org — and, critically, `sf deploy --dry-run` does NOT
    # catch it (reference validity is a separate Flow layer the dry-run skips), so
    # this must be fixed at transform time, not relied on at the validation gate.
    resolvable = {n: s for n, s in screen_field_suffix.items() if s is not None}

    def qualify_merge_text(text: Optional[str]) -> Optional[str]:
        """Return text with bare screen-field refs qualified by their accessor.
        Only rewrites a name when it is NOT already followed by '.' (so an
        already-qualified `.value` is left alone). Leaves definition elements
        untouched — this only runs on formula expressions / DisplayText."""
        if not text:
            return text
        for name, suffix in resolvable.items():
            esc = re.escape(name)
            # {!Field}  ->  {!Field.suffix}   (merge-field form)
            text = re.sub(r'(\{!\s*)' + esc + r'(?!\s*\.)',
                          lambda m: m.group(1) + name + '.' + suffix, text)
            # bare Field inside a formula body: IF(Field > ...) — not preceded by
            # '.' '!' or a word char, not followed by '.' or a word char.
            text = re.sub(r'(?<![.\w!])' + esc + r'(?![.\w])',
                          name + '.' + suffix, text)
        return text

    for fm in findall(root, 'formulas'):
        for expr in findall(fm, 'expression'):
            expr.text = qualify_merge_text(expr.text)

    for screen in findall(root, 'screens'):
        for field in findall(screen, 'fields'):
            if findtext(field, 'fieldType') == 'DisplayText':
                for ft_el in findall(field, 'fieldText'):
                    ft_el.text = qualify_merge_text(ft_el.text)

    return warnings


def remove_empty_connectors(root: ET.Element):
    """Remove connector elements with empty or missing targetReference."""
    for ntype in ALL_TYPES:
        for node in findall(root, ntype):
            for conn_type in ('connector', 'defaultConnector',
                              'nextValueConnector', 'noMoreValuesConnector'):
                for conn in findall(node, conn_type):
                    tr = findtext(conn, 'targetReference')
                    if not tr or not tr.strip():
                        node.remove(conn)


def remove_platform_event_nodes(root: ET.Element) -> List[Dict]:
    """
    Remove recordCreate nodes that target platform events (not UI-visible entities).
    DataCaptureFlow can only use objects that appear in the UI. Delegates the
    excise+placeholder+rewire+flag behavior to excise_and_placeholder so this
    site behaves identically to the CUD-excision and action-call-removal sites.
    """
    def is_platform_event(obj_name: str) -> bool:
        # Platform events always end with __e suffix
        return (obj_name or '').endswith('__e')

    flags: List[Dict] = []
    for rc in list(findall(root, 'recordCreates')):
        obj = findtext(rc, 'object') or ''
        rc_name = findtext(rc, 'name') or ''
        if not is_platform_event(obj):
            continue
        flags.extend(excise_and_placeholder(
            root, [rc_name], 'PLATFORM_EVENT_EXCISED',
            f'"{rc_name}" creates platform event "{obj}", which is not a '
            f'UI-visible entity and cannot be created from a DataCaptureFlow.'))
    return flags


def remove_action_calls(root: ET.Element) -> List[Dict]:
    """
    Remove <actionCalls> nodes — DataCaptureFlow can't include Action elements
    (deploy error: 'Flows of type "Data Capture Flow" can't include Action elements').
    Delegates to excise_and_placeholder for excise+placeholder+rewire+flag behavior,
    so a dropped side-effecting call (e.g. PostToChatter) is visible inline via the
    placeholder Screen, not just in the summary.
    """
    flags: List[Dict] = []
    for ac in list(findall(root, 'actionCalls')):
        ac_name = findtext(ac, 'name') or ''
        ac_type = findtext(ac, 'actionType') or findtext(ac, 'actionName') or 'unknown'
        flags.extend(excise_and_placeholder(
            root, [ac_name], 'ACTION_CALL_EXCISED',
            f'Action elements (actionType "{ac_type}") are not allowed in '
            f'DataCaptureFlow; its side effect no longer fires. Re-express '
            f'user-facing notifications as a DisplayText field, or move the '
            f'action to a separate AutoLaunched/record-triggered flow.'))
    return flags


def fix_subflow_references(root: ET.Element, dc_suffix: str = '_DC'):
    """
    Update subflow flowName references to target the migrated DC versions.
    Delegates naming to subflow_names.migrated_dc_flow_name so discovery and
    transform stay in lockstep.
    """
    for subflow in findall(root, 'subflows'):
        for fn in findall(subflow, 'flowName'):
            if not fn.text:
                continue
            fn.text = migrated_dc_flow_name(fn.text, dc_suffix)


# ──────────────────────────────────────────────
# Main transform entry point
# ──────────────────────────────────────────────

def transform(input_path: str, output_path: str, dc_suffix: str = '_DC', is_subflow: bool = False) -> dict:
    tree = ET.parse(input_path)
    root = tree.getroot()

    label = findtext(root, 'label') or input_path
    process_type = findtext(root, 'processType') or ''

    summary = {
        'label': label,
        'skipped': False,
        'skip_reason': '',
        'fields_converted': 0,
        'output_vars_mapped': 0,
        'assignment_nodes_injected': 0,
        'cud_fixes': 0,
        'cud_skipped': 0,
        'warnings': [],
    }

    # ── Skip pure automation flows (no screens) ──
    screens = findall(root, 'screens')
    if not screens:
        summary['skipped'] = True
        summary['skip_reason'] = (
            'Flow has no screen elements — it is a pure automation flow and '
            'cannot be a DataCaptureFlow, which requires at least one screen for user input. '
            'Keep this flow as FieldServiceMobile or convert to AutoLaunchedFlow.'
        )
        return summary

    # Phase 1: metadata
    apply_dc_metadata(root)

    # Phase 1b: remove actionCalls (not allowed in DC) before graph analysis, so
    # CUD-at-end enforcement sees the post-removal execution graph.
    action_call_flags = remove_action_calls(root)

    # Phase 2: screen field transformation
    fields_converted, output_var_map = transform_screen_fields(root)
    summary['fields_converted'] = fields_converted
    summary['output_vars_mapped'] = len(output_var_map)

    # Phase 3: inject assignment nodes to preserve outputAssignment variable bindings
    injected = inject_output_assignments(root, output_var_map)
    summary['assignment_nodes_injected'] = injected

    # Phase 4: enforce CUD at end
    cud_fixed, cud_skipped, cud_warnings, cud_excision_flags = enforce_cud_at_end(root, is_subflow=is_subflow)
    summary['cud_fixes'] = cud_fixed
    summary['cud_skipped'] = cud_skipped
    summary['warnings'].extend(cud_warnings)

    # Phase 5: structural DC requirements
    ensure_screen_attrs(root)
    ensure_node_locations(root)
    ensure_dc_variables(root)
    fix_subflow_references(root, dc_suffix)

    # Phase 6: fix screen field references in downstream automation
    summary['warnings'].extend(fix_screen_field_references(root))

    # Phase 7: remove dangling empty connectors (left by restructurer)
    remove_empty_connectors(root)

    # Phase 8: remove platform event creates (not allowed in DC)
    platform_event_flags = remove_platform_event_nodes(root)

    # Phase 9: reorder field children (inputParameters must be contiguous)
    reorder_field_children(root)

    # Phase 10: detect manual-review flags
    flags = detect_manual_review_flags(root)
    summary['flags'] = cud_excision_flags + action_call_flags + platform_event_flags + flags

    # Phase 11: regroup root children (excise_and_placeholder appends new
    # <screens> at the end, which can land after subflows/variables and
    # break the "same tag type must be contiguous" DC deploy rule)
    regroup_root_children(root)

    # Write output
    ET.indent(tree, space='    ')
    tree.write(output_path, encoding='unicode', xml_declaration=True)
    with open(output_path) as f:
        content = f.read()
    if not content.startswith('<?xml'):
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' + content
    with open(output_path, 'w') as f:
        f.write(content)

    return summary


def main():
    args = sys.argv[1:]
    dc_suffix = '_DC'
    if '--dc-suffix' in args:
        idx = args.index('--dc-suffix')
        dc_suffix = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    is_subflow = '--is-subflow' in args
    if is_subflow:
        args = [a for a in args if a != '--is-subflow']

    if len(args) != 2:
        print(f'Usage: {sys.argv[0]} <input.flow-meta.xml> <output.flow-meta.xml> [--dc-suffix SUFFIX] [--is-subflow]')
        sys.exit(1)

    summary = transform(args[0], args[1], dc_suffix, is_subflow=is_subflow)

    print(f"\n{'='*60}")
    if summary['skipped']:
        print(f"SKIPPED: {summary['label']}")
        print(f"Reason: {summary['skip_reason']}")
    else:
        print(f"Transformed: {summary['label']}")
        print(f"{'='*60}")
        print(f"Fields converted:          {summary['fields_converted']}")
        print(f"Output vars mapped:        {summary['output_vars_mapped']}")
        print(f"Assignment nodes injected: {summary['assignment_nodes_injected']}")
        print(f"CUD violations fixed:      {summary['cud_fixes']}")
        print(f"CUD violations manual:     {summary['cud_skipped']}")
        if summary['warnings']:
            print(f"\nWarnings ({len(summary['warnings'])}):")
            for w in summary['warnings']:
                print(f"  - {w}")
        if summary.get('flags'):
            print(f"\n[WARN] Requires Manual Review ({len(summary['flags'])} pattern(s)):")
            for flag in summary['flags']:
                print(f"  [{flag['code']}] {flag['what']}")
                print(f"    Why: {flag['why']}")
                print(f"    Fix: {flag['recommendation']}")
    print()


if __name__ == '__main__':
    main()
