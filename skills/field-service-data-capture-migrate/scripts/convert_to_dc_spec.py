#!/usr/bin/env python3
"""
Convert a legacy FieldServiceMobile flow to a Data Capture spec JSON.

Usage:
    python3 convert_to_dc_spec.py <input_flow.xml> <output_spec.json>

Outputs a JSON spec compatible with scripts/vendor/build_flow.py's input contract.
Handles both legacy FieldServiceMobile (InputField) and modern dc* component formats.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_input  # noqa: E402
from flow_xml_utils import NS, _findtext, _findall, _findall_deep  # noqa: E402,F401
import cud_analysis  # noqa: E402

MAX_SECTION_DEPTH = 5


def _extract_right_value(cond_el: ET.Element) -> Optional[Dict[str, Any]]:
    """Return the typed rightValue of a <conditions> element as a single-key dict.

    One of {booleanValue|numberValue|stringValue|elementReference}, or None.
    """
    rv = _findall(cond_el, 'rightValue')
    if not rv:
        return None
    rv_el = rv[0]
    bool_txt = _findtext(rv_el, 'booleanValue')
    if bool_txt is not None:
        return {'booleanValue': bool_txt == 'true'}
    num_txt = _findtext(rv_el, 'numberValue')
    if num_txt is not None:
        return {'numberValue': float(num_txt)}
    ref_txt = _findtext(rv_el, 'elementReference')
    if ref_txt is not None:
        return {'elementReference': ref_txt}
    str_txt = _findtext(rv_el, 'stringValue')
    if str_txt is not None:
        return {'stringValue': str_txt}
    return None


def extract_decisions(root: ET.Element) -> List[Dict[str, Any]]:
    """Extract source <decisions> into the spec-level decisions list.

    Faithful structural extraction in document order. No interpretation
    (collapse-to-visibility is 6b; section inference is 6c).
    """
    result: List[Dict[str, Any]] = []
    for dec in _findall_deep(root, 'decisions'):
        name = _findtext(dec, 'name')
        if not name:
            continue
        entry: Dict[str, Any] = {
            'name': name,
            'label': _findtext(dec, 'label') or name,
            'defaultConnector': None,
            'defaultLabel': _findtext(dec, 'defaultConnectorLabel'),
            'rules': [],
        }
        default_conn = _findall(dec, 'defaultConnector')
        if default_conn:
            entry['defaultConnector'] = _findtext(default_conn[0], 'targetReference')

        for rule in _findall(dec, 'rules'):
            rule_name = _findtext(rule, 'name')
            if not rule_name:
                continue
            conditions: List[Dict[str, Any]] = []
            for cond in _findall(rule, 'conditions'):
                left = _findtext(cond, 'leftValueReference')
                op = _findtext(cond, 'operator')
                cond_entry: Dict[str, Any] = {
                    'leftValueReference': left,
                    'operator': op or 'EqualTo',
                }
                rv = _extract_right_value(cond)
                if rv is not None:
                    cond_entry['rightValue'] = rv
                conditions.append(cond_entry)

            connects_to = None
            conn = _findall(rule, 'connector')
            if conn:
                connects_to = _findtext(conn[0], 'targetReference')

            entry['rules'].append({
                'name': rule_name,
                'label': _findtext(rule, 'label') or rule_name,
                'conditionLogic': _findtext(rule, 'conditionLogic') or 'and',
                'conditions': conditions,
                'connectsTo': connects_to,
            })
        result.append(entry)
    return result


def extract_field_type(field_element: ET.Element) -> tuple:
    """Determine Data Capture field type from legacy field element."""
    ext_name = _findtext(field_element, 'extensionName')
    field_type_elem = _findtext(field_element, 'fieldType')
    data_type = _findtext(field_element, 'dataType')

    # Classification is keyed on the REAL FSM vocabulary: fieldType first, and
    # extensionName only for ComponentInstance. In a genuine FSM source a
    # `lightning:*` / `c:*` name never appears as a fieldType — it only ever
    # shows up as a ComponentInstance <extensionName>, and core (FieldService-
    # MobileFlowValidator) whitelists exactly one such extension:
    # forceContent:fileUpload. See references/fsm-dc-capability-catalog.md.

    # Already a DC component (partially hand-migrated source) — pass through.
    if ext_name and 'runtime_service_fieldservice:dc' in ext_name:
        comp = ext_name.split(':')[-1]
        dc_map = {
            'dcTextInput': 'ShortText', 'dcLongText': 'LongText',
            'dcEmail': 'Email', 'dcPhone': 'Phone', 'dcNumeric': 'Numeric',
            'dcCounter': 'Counter', 'dcDate': 'Date', 'dcDateTime': 'DateTime',
            'dcCheckbox': 'Checkbox', 'dcToggle': 'Toggle', 'dcAddress': 'Address',
            'dcLookup': 'Lookup', 'dcPicklist': 'Picklist', 'dcRbGroup': 'Radio',
            'dcCbGroup': 'CheckboxGroup', 'dcSignature': 'Signature',
            'dcUpFile': 'UploadFile', 'dcUpImage': 'UploadImage',
            'dcFileView': 'FileView', 'dcName': 'Name', 'dcMatrix': 'Matrix',
        }
        return dc_map.get(comp, 'ShortText'), {}

    # ComponentInstance with the only FSM-whitelisted screen extension.
    if ext_name == 'forceContent:fileUpload':
        return 'UploadFile', {}
    if ext_name == 'forceContent:imageUpload':
        return 'UploadImage', {}

    # Known standard extensions that legitimately appear on an FSM screen but
    # have no DC equivalent — name them specifically. "Advanced CSV Import"
    # (Industries CSV Data Import / DPE) is the common one.
    known_unsupported = {
        'runtime_industries_csv_dataimport:advCsv':
            'Advanced CSV Import (Industries CSV Data Import / DPE bulk import) — '
            'no DC equivalent. Rebuild the data-loading step outside the flow '
            '(e.g. Data Processing Engine) or drop it; it cannot be auto-migrated.',
        'runtime_industries_csv_dataimport:impBeg':
            'CSV Import (Industries CSV Data Import, beginner variant) — no DC '
            'equivalent; cannot be auto-migrated.',
    }
    if ext_name in known_unsupported:
        return 'DisplayText', {'unsupported': True,
                               'unsupportedType': 'customComponent',
                               'note': known_unsupported[ext_name]}

    # Any other ComponentInstance extension (custom c:*, non-whitelisted
    # lightning:*) has no DC extension point — flag as unmigratable.
    if ext_name:
        return 'DisplayText', {
            'unsupported': True,
            'unsupportedType': 'customComponent',
            'note': f'Custom/unsupported component "{ext_name}" — no DC equivalent; '
                    f'rebuild with a native dc* component in Flow Builder.'
        }

    # FieldServiceMobile InputField — map by dataType.
    if field_type_elem == 'InputField':
        # Keys mirror fsm_dc_catalog.py FIELD_TYPE_MAP / transform_flow.py; values are
        # build_flow.py TYPE_MAP spec-type names. Keep in sync with those three.
        dtype_map = {
            'Boolean': 'Checkbox', 'String': 'ShortText', 'Number': 'Numeric',
            'Double': 'Numeric', 'Currency': 'Numeric', 'Date': 'Date',
            'DateTime': 'DateTime', 'Email': 'Email', 'Phone': 'Phone',
            'Picklist': 'Picklist', 'MultiselectPicklist': 'CheckboxGroup',
            'TextArea': 'LongText', 'LongTextArea': 'LongText',
            'Name': 'Name', 'Address': 'Address', 'Toggle': 'Toggle',
            'Lookup': 'Lookup', 'Counter': 'Counter', 'Matrix': 'Matrix',
        }
        key = data_type or 'String'
        if key in dtype_map:
            return dtype_map[key], {}
        return 'DisplayText', {
            'unsupported': True, 'unsupportedType': 'unknownField',
            'note': f'InputField dataType={data_type!r} has no DC mapping; '
                    f'emitted as a read-only placeholder. Rebuild in Flow Builder.'
        }

    # Standalone FSM choice field types (real FSM vocabulary).
    if field_type_elem == 'DropdownBox':
        return 'Picklist', {'needsChoices': True}
    if field_type_elem in ('RadioButtons', 'RadioButtonGroup'):
        return 'Radio', {'needsChoices': True}
    if field_type_elem in ('MultiSelectCheckboxes', 'MultiSelectPicklist'):
        return 'CheckboxGroup', {'needsChoices': True}
    if field_type_elem == 'LargeTextArea':
        return 'LongText', {}

    if field_type_elem == 'PlainButtons':
        return 'DisplayText', {
            'unsupported': True, 'unsupportedType': 'PlainButtons',
            'note': 'CAPABILITY GAP: Data Capture has no user-facing action buttons '
                    '(only AGX_FLOW actions). No migration path — remove or redesign '
                    'in Flow Builder.'
        }

    if field_type_elem in ('DisplayText', 'DisplayRichText'):
        return 'DisplayText', {}

    if field_type_elem in ('ComponentChoice', 'ComponentMultiChoice'):
        return 'Picklist', {'needsChoices': True}

    if field_type_elem == 'Repeater':
        return 'DisplayText', {'note': 'Repeater — review manually in Flow Builder'}

    if field_type_elem in ('RegionContainer', 'Region'):
        return None, {'skip': True}  # Layout container, skip

    return 'DisplayText', {
        'unsupported': True, 'unsupportedType': 'unknownField',
        'note': f'Unknown fieldType={field_type_elem!r} (ext={ext_name!r}) has no DC '
                f'equivalent; emitted as a read-only placeholder. Rebuild in Flow Builder.'
    }


def extract_label(field_element: ET.Element) -> str:
    """Extract field label from various possible locations."""
    # Try fieldText first
    label = _findtext(field_element, 'fieldText')
    if label:
        # Strip HTML tags for cleaner labels
        import re
        label = re.sub(r'<[^>]+>', ' ', label).strip()
        label = ' '.join(label.split())
        if label:
            return label[:120]  # cap length

    # Try label inputParameter
    for param in _findall_deep(field_element, 'inputParameters'):
        if _findtext(param, 'name') == 'label':
            val = _findtext(param, 'stringValue')
            if val:
                return val

    return _findtext(field_element, 'name') or 'Untitled Field'


def extract_required(field_element: ET.Element) -> bool:
    """Extract required flag from field."""
    required_text = _findtext(field_element, 'isRequired')
    return required_text == 'true' if required_text else False


def extract_choices(field_element: ET.Element, root: ET.Element) -> Optional[List[str]]:
    """Extract choice values for picklist/radio/checkbox components."""
    choice_refs = []
    for choice_ref in _findall_deep(field_element, 'choiceReferences'):
        if choice_ref.text:
            choice_refs.append(choice_ref.text)

    if not choice_refs:
        return None

    choices = []
    for choice_name in choice_refs:
        for choice in _findall_deep(root, 'choices'):
            if _findtext(choice, 'name') == choice_name:
                label = _findtext(choice, 'choiceText') or _findtext(choice, 'label')
                if label:
                    choices.append(label)

    return choices if choices else None


def _cud_element_names(root: ET.Element) -> set:
    names = set()
    for tag in ('recordCreates', 'recordUpdates', 'recordDeletes'):
        for el in _findall_deep(root, tag):
            n = _findtext(el, 'name')
            if n:
                names.add(n)
    return names


def _source_input_assignments(cud_el: ET.Element) -> List[Dict[str, Any]]:
    """Map a source <recordCreates> element's <inputAssignments> to builder shape.

    Builder (_render_value) recognises value|valueRef|boolean|number keys.
    """
    out: List[Dict[str, Any]] = []
    for ia in _findall(cud_el, 'inputAssignments'):
        field_name = _findtext(ia, 'field')
        if not field_name:
            continue
        entry: Dict[str, Any] = {'field': field_name}
        val_els = _findall(ia, 'value')
        if val_els:
            v = val_els[0]
            ref = _findtext(v, 'elementReference')
            boolv = _findtext(v, 'booleanValue')
            numv = _findtext(v, 'numberValue')
            strv = _findtext(v, 'stringValue')
            if ref is not None:
                entry['valueRef'] = ref
            elif boolv is not None:
                entry['boolean'] = (boolv == 'true')
            elif numv is not None:
                entry['number'] = float(numv)
            elif strv is not None:
                entry['value'] = strv
        # Skip hollow inputAssignment entries (field only, no value)
        if len(entry) > 1:
            out.append(entry)
    return out


def _build_postscreen_creates(root: ET.Element,
                              consolidated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build postScreen.recordCreates entries for the consolidated safe creates."""
    by_name = {_findtext(el, 'name'): el for el in _findall_deep(root, 'recordCreates')}
    entries: List[Dict[str, Any]] = []
    names = [c['node'] for c in consolidated]
    for i, name in enumerate(names):
        el = by_name.get(name)
        if el is None:
            continue
        entry: Dict[str, Any] = {
            'name': name,
            'label': _findtext(el, 'label') or name,
            'object': _findtext(el, 'object') or '',
            'inputAssignments': _source_input_assignments(el),
        }
        entries.append(entry)
    # Chain emitted entries in order to prevent dangling connectors
    for j in range(len(entries) - 1):
        entries[j]['next'] = entries[j + 1]['name']
    return entries


_FLOW_ELEMENT_TAGS = (
    'screens', 'decisions', 'assignments', 'recordCreates', 'recordUpdates',
    'recordDeletes', 'recordLookups', 'subflows', 'loops',
)


def detect_unsupported_elements(root: ET.Element) -> List[Dict[str, str]]:
    """Flow-level constructs that DataCaptureFlow cannot run, in document order.

    Each entry is {type, name, reason} with type in {'apex','subflow','faultPath'}.
    Field-level unsupported components (custom / unknown) are collected separately
    during the screen loop, not here. Never silently dropped — this is the
    partial-migration (WI-7) surface.
    """
    out: List[Dict[str, str]] = []

    for el in _findall_deep(root, 'actionCalls'):
        name = _findtext(el, 'name')
        if name:
            out.append({'type': 'apex', 'name': name,
                        'reason': 'Apex / action call is not supported at DataCaptureFlow '
                                  'runtime (offline-first). Rebuild as a record lookup or remove.'})

    for el in _findall_deep(root, 'subflows'):
        name = _findtext(el, 'name')
        if name:
            out.append({'type': 'subflow', 'name': name,
                        'reason': 'Subflow invocation — a DataCaptureFlow subflow must be '
                                  'DataCaptureFlow-type and contain no CUD. Inline or convert; '
                                  'not auto-migrated.'})

    for tag in _FLOW_ELEMENT_TAGS:
        for el in _findall_deep(root, tag):
            if _findall(el, 'faultConnector'):
                name = _findtext(el, 'name')
                if name:
                    out.append({'type': 'faultPath', 'name': name,
                                'reason': 'Fault-path connector — DataCaptureFlow has no fault '
                                          'paths; fault handling is stripped. Review manually.'})
    return out


def _local(tag: str) -> str:
    """Strip an XML namespace from a tag: '{ns}screens' -> 'screens'."""
    return tag.rsplit('}', 1)[-1]


def _element_index(root: ET.Element) -> Dict[str, tuple]:
    """Map element name -> (localTagName, element) for named flow elements."""
    idx: Dict[str, tuple] = {}
    for tag in _FLOW_ELEMENT_TAGS:
        for el in _findall_deep(root, tag):
            name = _findtext(el, 'name')
            if name and name not in idx:
                idx[name] = (tag, el)
    return idx


def _connector_targets_of(el: ET.Element) -> List[str]:
    """All connector targetReferences carried by one element (incl. rules)."""
    targets: List[str] = []
    for conn_tag in ('connector', 'defaultConnector', 'nextValueConnector',
                     'noMoreValuesConnector'):
        for conn in _findall(el, conn_tag):
            t = _findtext(conn, 'targetReference')
            if t:
                targets.append(t)
    for rule in _findall(el, 'rules'):
        for conn in _findall(rule, 'connector'):
            t = _findtext(conn, 'targetReference')
            if t:
                targets.append(t)
    return targets


def detect_ceiling_violations(root: ET.Element) -> List[Dict[str, str]]:
    """Flag DC deploy-time ceilings decision translation can hit, in document order.

    Three classes, each an independent {name, reason}:
      1. Any element reachable from a CUD node via connectors (conservative: not
         de-duplicated against pre-CUD paths).
      2. Any element carrying a <faultConnector> (DC has no fault paths).
      3. Any <loops> (DC loop composition is constrained; flagged conservatively).
    Never silently dropped — this is the WI-7 surface.
    """
    flags: List[Dict[str, str]] = []
    idx = _element_index(root)
    cud = _cud_element_names(root)

    # 1. Post-CUD reachability: BFS from each CUD node over connectors; any element
    #    reached (other than a CUD node itself) is a post-CUD violation.
    reached: set = set()
    frontier = [t for name in cud if name in idx
                for t in _connector_targets_of(idx[name][1])]
    while frontier:
        nxt = frontier.pop()
        if nxt in reached or nxt not in idx:
            continue
        reached.add(nxt)
        frontier.extend(_connector_targets_of(idx[nxt][1]))
    for name in _ordered_element_names(root):
        if name in reached and name not in cud:
            tag = idx[name][0]
            flags.append({'name': name,
                          'reason': f'{_local_tag_singular(tag)} "{name}" runs after a CUD '
                                    f'node; DC forbids elements after create/update/delete '
                                    f'(CUD-at-end). DC will reject elements sequenced after a CUD node — '
                                    f'emitted but flagged for WI-7; restructure before deploy.'})

    # 2. Fault connectors.
    for name in _ordered_element_names(root):
        el = idx[name][1]
        if _findall(el, 'faultConnector'):
            flags.append({'name': name,
                          'reason': f'element "{name}" has a fault-path connector; DC has no '
                                    f'fault paths (fault handling is stripped). Flagged for WI-7.'})

    # 3. Loops (conservative: any loop is surfaced for manual review).
    for lp in _findall_deep(root, 'loops'):
        name = _findtext(lp, 'name')
        if name:
            flags.append({'name': name,
                          'reason': f'loop "{name}" composition is not supported in DC; '
                                    f'review manually. Flagged for WI-7.'})
    return flags


def _ordered_element_names(root: ET.Element) -> List[str]:
    """Named flow elements in document order across the flow-element tags."""
    names: List[str] = []
    for tag in _FLOW_ELEMENT_TAGS:
        for el in _findall_deep(root, tag):
            n = _findtext(el, 'name')
            if n:
                names.append(n)
    return names


def _local_tag_singular(tag: str) -> str:
    return {'decisions': 'decision', 'screens': 'screen', 'recordLookups': 'lookup',
            'subflows': 'subflow', 'assignments': 'assignment', 'loops': 'loop',
            'recordCreates': 'create', 'recordUpdates': 'update',
            'recordDeletes': 'delete'}.get(tag, tag)


def _inbound_counts(root: ET.Element) -> Dict[str, int]:
    """Count, per target element name, how many connectors point at it."""
    counts: Dict[str, int] = {}
    for tag in _FLOW_ELEMENT_TAGS:
        for el in _findall_deep(root, tag):
            for t in _connector_targets_of(el):
                counts[t] = counts.get(t, 0) + 1
    return counts


def _screen_migratable_fields(screen_el: ET.Element) -> List[str]:
    """Field names on a screen that survive extract_field_type filtering."""
    names: List[str] = []
    for field in _findall(screen_el, 'fields'):
        fname = _findtext(field, 'name')
        if not fname:
            continue
        ftype, meta = extract_field_type(field)
        if meta.get('skip') or ftype is None:
            continue
        names.append(fname)
    return names


def _resolve_left(ref: Optional[str], emitted_field_names: set) -> bool:
    """A condition left-value resolves iff its base (before any '.') is an
    emitted form field."""
    if not ref:
        return False
    return ref.split('.')[0] in emitted_field_names


def _conditions_resolvable(rule: Dict[str, Any], emitted_field_names: set) -> bool:
    # Enforces spec collapse-condition 6 (conditions reference emitted form
    # fields). We check membership, not screen ordering: the spec's "positioned
    # before the field" clause is guaranteed structurally, not verified here —
    # the gating decision is only reached after its upstream screens have run,
    # so any field its condition references is necessarily emitted earlier in a
    # valid flow. A forward reference could only arise in an already-broken
    # source flow, which is out of scope.
    for cond in rule.get('conditions') or []:
        if not _resolve_left(cond.get('leftValueReference'), emitted_field_names):
            return False
        rv = cond.get('rightValue') or {}
        if 'elementReference' in rv and not _resolve_left(
                rv['elementReference'], emitted_field_names):
            return False
    return True


def _field_dict_by_name(spec_screens: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
    for fields in spec_screens.values():
        for fd in fields:
            if fd.get('fieldName') == field_name:
                return fd
    return None


def _screen_label_by_name(root: ET.Element) -> Dict[str, str]:
    """Map each screen element NAME -> the display label the spec uses (deduped)."""
    out: Dict[str, str] = {}
    counts: Dict[str, int] = {}
    for i, s in enumerate(_findall_deep(root, 'screens'), 1):
        name = _findtext(s, 'name')
        raw = _findtext(s, 'label') or f'Screen {i}'
        c = counts.get(raw, 0) + 1
        counts[raw] = c
        label = raw if c == 1 else f'{raw} {c}'
        if name:
            out[name] = label
    return out


def _control_field(visibility: Dict[str, Any]) -> Optional[str]:
    conds = visibility.get('conditions') or []
    if not conds:
        return None
    ref = conds[0].get('leftValueReference') or ''
    return ref.split('.')[0] or None


def _find_enclosing_section(items: List[Any], control: str, depth: int) -> Optional[Dict[str, Any]]:
    """DFS for a section sentinel whose fields include `control`, honoring the
    depth cap. Returns the sentinel dict to nest into, or None."""
    if depth >= MAX_SECTION_DEPTH:
        return None
    for it in items:
        if isinstance(it, dict) and 'section' in it and 'fields' in it:
            names = {f.get('fieldName') for f in it['fields']
                     if isinstance(f, dict) and 'fieldName' in f}
            if control in names:
                return it
            deeper = _find_enclosing_section(it['fields'], control, depth + 1)
            if deeper is not None:
                return deeper
    return None


def _inject_section(spec_screens: Dict[str, Any], gated_label: Optional[str],
                    merge_label: str, section_label: str,
                    field_names: List[str], visibility: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if gated_label is None or gated_label not in spec_screens:
        return None
    gated_fields = spec_screens[gated_label]
    moved_fields = [f for f in gated_fields if f.get('fieldName') in set(field_names)]
    if len(moved_fields) != len(field_names):
        return None
    cleared: List[str] = []
    for f in moved_fields:
        if f.get('isRequired'):
            f['isRequired'] = False
            cleared.append(f['fieldName'])
    sentinel = {'section': section_label, 'visibility': visibility, 'fields': moved_fields}
    del spec_screens[gated_label]

    control = _control_field(visibility)
    enclosing = (_find_enclosing_section(spec_screens[merge_label], control, 0)
                 if control else None)
    if enclosing is not None:
        # Nest inside the enclosing section, right after its own fields.
        enclosing['fields'].append(sentinel)
        nested = True
    else:
        spec_screens[merge_label] = [sentinel] + spec_screens[merge_label]
        nested = False
    return {'label': section_label, 'fields': [f['fieldName'] for f in moved_fields],
            'cleared': cleared, 'nested': nested}


def _reconverges_transitively(root: ET.Element, screen_el: ET.Element, default_target: str,
                               idx: Dict[str, tuple], depth: int = 0,
                               visited: Optional[set] = None) -> bool:
    """Check if screen_el's onward path reaches default_target, possibly through
    intermediate collapsible gates. Bounded by MAX_SECTION_DEPTH and cycle-safe."""
    if visited is None:
        visited = set()
    if depth >= MAX_SECTION_DEPTH:
        return False

    targets = _connector_targets_of(screen_el)
    if len(targets) != 1:
        return False
    next_name = targets[0]

    # Direct reconvergence (6b single-hop case)
    if next_name == default_target:
        return True

    # Cycle check
    if next_name in visited:
        return False
    visited.add(next_name)

    # If next hop is not in index or is a side-effect element, fail
    if next_name not in idx:
        return False
    tag, el = idx[next_name]

    # If it's a screen, follow its connector recursively
    if tag == 'screens':
        return _reconverges_transitively(root, el, default_target, idx, depth + 1, visited)

    # If it's a decision, check if it's a collapsible gate with the same merge target
    if tag == 'decisions':
        # Must have exactly one rule + default
        rules = _findall(el, 'rules')
        default_conn_els = _findall(el, 'defaultConnector')
        if len(rules) != 1 or not default_conn_els:
            return False
        default_conn = _findtext(default_conn_els[0], 'targetReference')
        if not default_conn or default_conn != default_target:
            return False
        # Get rule's target
        conn_els = _findall(rules[0], 'connector')
        if not conn_els:
            return False
        rule_target = _findtext(conn_els[0], 'targetReference')
        if not rule_target or rule_target not in idx:
            return False
        rule_tag, rule_el = idx[rule_target]
        if rule_tag != 'screens':
            return False
        # Check if the rule's screen eventually reaches default_target
        return _reconverges_transitively(root, rule_el, default_target, idx, depth + 1, visited)

    # Other element types (assignment, recordCreate, etc.) are side effects → fail
    return False


# Single-condition operator inverses. IsNull is NOT here: it has no inverse
# operator, so it is negated by flipping its rightValue boolean instead.
_OPERATOR_INVERSE = {
    'EqualTo': 'NotEqualTo',
    'NotEqualTo': 'EqualTo',
    'GreaterThan': 'LessThanOrEqualTo',
    'GreaterThanOrEqualTo': 'LessThan',
    'LessThan': 'GreaterThanOrEqualTo',
    'LessThanOrEqualTo': 'GreaterThan',
}


def _negate_condition(cond: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Negate a single condition, or None if its operator has no safe inverse.

    `Contains`/`StartsWith`/`EndsWith` have no negated Flow operator, so they
    return None (the whole rule then stays a flagged decision).
    """
    op = cond.get('operator') or 'EqualTo'
    if op == 'IsNull':
        rv = cond.get('rightValue') or {}
        if 'booleanValue' not in rv:
            return None  # Malformed IsNull: bail rather than mis-negate
        current = bool(rv.get('booleanValue'))
        out = dict(cond)
        out['rightValue'] = {'booleanValue': not current}
        return out
    inverse = _OPERATOR_INVERSE.get(op)
    if inverse is None:
        return None
    out = dict(cond)
    out['operator'] = inverse
    return out


def negate_rule(conditions: List[Dict[str, Any]],
                condition_logic: str) -> Optional[tuple]:
    """Return (negated_conditions, negated_logic) or None if not provably safe.

    De Morgan: NOT(A and B) == (NOT A) or (NOT B). Negate each condition and
    flip bare `and`<->`or` only if multiple conditions. Custom conditionLogic
    (anything other than bare and/or, e.g. '1 AND (2 OR 3)') is not attempted
    -> None. Any condition with a non-invertible operator -> None.
    """
    if not conditions:
        return None
    logic = (condition_logic or 'and').strip().lower()
    if logic not in ('and', 'or'):
        return None
    negated: List[Dict[str, Any]] = []
    for cond in conditions:
        neg = _negate_condition(cond)
        if neg is None:
            return None
        negated.append(neg)
    # De Morgan: flip logic only if there are multiple conditions
    if len(conditions) > 1:
        flipped = 'or' if logic == 'and' else 'and'
    else:
        flipped = logic
    return negated, flipped


def normalize_inverted_gates(root: ET.Element,
                             decisions: List[Dict[str, Any]]) -> List[str]:
    """Rewrite inverted single-target gates into equivalent positive gates.

    Inverted shape: the DEFAULT branch targets a screen carrying the gated
    field(s); the RULE branch skips to the reconvergence point. The field is
    thus visible when the rule is FALSE. We negate the rule condition and swap
    connectors, so the decision becomes byte-for-byte a positive gate that the
    unchanged collapse_gating_decisions pass then handles (field or section).

    A decision is rewritten iff (all): exactly one rule + a defaultConnector;
    the DEFAULT target is a screen with >=1 migratable field; that screen has a
    single inbound connector; its onward path reconverges at the RULE's target;
    and negate_rule succeeds. Anything else is left untouched (falls through to
    collapse, which leaves it a decision/flag). Deterministic: document order.

    Returns the names of the decisions it normalized.
    """
    idx = _element_index(root)
    inbound = _inbound_counts(root)
    normalized: List[str] = []

    for dec in decisions:
        rules = dec.get('rules') or []
        default = dec.get('defaultConnector')
        if len(rules) != 1 or not default:
            continue
        rule = rules[0]
        rule_target = rule.get('connectsTo')
        if not rule_target:
            continue
        # The GATED screen is the DEFAULT target (inverted shape).
        if default not in idx or idx[default][0] != 'screens':
            continue
        gated_el = idx[default][1]
        if len(_screen_migratable_fields(gated_el)) == 0:
            continue
        # Single inbound to the gated screen (only this default connector).
        if inbound.get(default, 0) != 1:
            continue
        # Reconvergence: gated screen's onward path reaches the RULE's target.
        if not _reconverges_transitively(root, gated_el, rule_target, idx):
            continue
        negated = negate_rule(rule.get('conditions') or [],
                              rule.get('conditionLogic') or 'and')
        if negated is None:
            continue
        neg_conditions, neg_logic = negated
        # Rewrite in place: rule now takes the gated branch; default the merge.
        rule['connectsTo'] = default
        rule['conditions'] = neg_conditions
        rule['conditionLogic'] = neg_logic
        dec['defaultConnector'] = rule_target
        normalized.append(dec['name'])

    return normalized


def collapse_gating_decisions(
    root: ET.Element,
    decisions: List[Dict[str, Any]],
    emitted_field_names: set,
    spec_screens: Dict[str, Any],
    screen_label_by_name: Dict[str, str],
) -> tuple:
    """Collapse pure single-field gating decisions into field visibility.

    A decision collapses iff (all): exactly one rule + a defaultConnector; the
    rule targets a screen with exactly one migratable field; that screen's
    onward connector == the decision's defaultConnector (reconvergence); the
    gated screen has a single inbound connector (only this rule); and every
    condition resolves to an emitted form field. On collapse, the rule's
    conditions/logic are attached verbatim as a shape-(b) visibility block on
    the gated field, and the decision is dropped from the returned list.

    Returns (remaining_decisions, notes) where notes entries are
    {decision, field} on success or {decision, reason} for a near-miss.
    """
    idx = _element_index(root)
    inbound = _inbound_counts(root)
    remaining: List[Dict[str, Any]] = []
    notes: List[Dict[str, str]] = []

    for dec in decisions:
        rules = dec.get('rules') or []
        default = dec.get('defaultConnector')
        # 1. exactly one rule + a default connector
        if len(rules) != 1 or not default:
            remaining.append(dec)
            if len(rules) != 1:
                notes.append({'decision': dec['name'],
                              'reason': f'decision has {len(rules)} rules '
                                        f'(multi-way routing); left as decision'})
            else:
                notes.append({'decision': dec['name'],
                              'reason': 'decision has no defaultConnector; left as decision'})
            continue
        rule = rules[0]
        target = rule.get('connectsTo')
        # 4. taken branch must be a screen (no assignment/record/subflow hop)
        if not target or target not in idx or idx[target][0] != 'screens':
            remaining.append(dec)
            notes.append({'decision': dec['name'],
                          'reason': 'gate target is not a direct screen '
                                    '(side effect on branch); left as decision'})
            continue
        screen_tag, screen_el = idx[target]
        migratable = _screen_migratable_fields(screen_el)
        # 2. field count: 0 -> not a gate; 1 -> field visibility (6b); >=2 -> section (6c).
        if len(migratable) == 0:
            remaining.append(dec)
            notes.append({'decision': dec['name'],
                          'reason': 'gated screen has no migratable fields; left as decision'})
            continue
        # 3. reconvergence: screen's onward path reaches default target (transitive)
        if not _reconverges_transitively(root, screen_el, default, idx):
            remaining.append(dec)
            notes.append({'decision': dec['name'],
                          'reason': 'branches do not reconverge; left as decision'})
            continue
        # 5. single inbound to the gated screen
        if inbound.get(target, 0) != 1:
            remaining.append(dec)
            notes.append({'decision': dec['name'],
                          'reason': 'gated screen has other inbound routes; left as decision'})
            continue
        # 6. conditions resolvable to emitted form fields
        if not _conditions_resolvable(rule, emitted_field_names):
            remaining.append(dec)
            notes.append({'decision': dec['name'],
                          'reason': 'condition references data not emitted in the '
                                    'form (e.g. a record field); collapse deferred to 6e'})
            continue

        vis = {
            'conditionLogic': rule.get('conditionLogic') or 'and',
            'conditions': rule.get('conditions') or [],
        }
        if len(migratable) == 1:
            # 6b field path (unchanged).
            field_name = migratable[0]
            fd = _field_dict_by_name(spec_screens, field_name)
            if fd is None:
                remaining.append(dec)
                notes.append({'decision': dec['name'],
                              'reason': f'gated field {field_name} not found in spec screens; left as decision'})
                continue
            fd['visibility'] = vis
            notes.append({'decision': dec['name'], 'field': field_name})
        else:
            # 6c section path: >=2 fields.
            merge_label = screen_label_by_name.get(default)
            gated_label = screen_label_by_name.get(target)
            if merge_label is None or merge_label not in spec_screens:
                remaining.append(dec)
                notes.append({'decision': dec['name'],
                              'reason': 'multi-field gate reconverges to a non-screen '
                                        'element; left as decision'})
                continue
            moved = _inject_section(spec_screens, gated_label, merge_label,
                                    gated_label,
                                    migratable, vis)
            if moved is None:
                remaining.append(dec)
                notes.append({'decision': dec['name'],
                              'reason': 'gated section fields not found in spec screens; left as decision'})
                continue
            notes.append({'decision': dec['name'], 'section': moved['label'],
                          'fields': moved['fields'], 'clearedRequired': moved['cleared']})

    return remaining, notes


def _decision_targets(decision: Dict[str, Any]) -> List[str]:
    targets = []
    if decision.get('defaultConnector'):
        targets.append(decision['defaultConnector'])
    for rule in decision.get('rules') or []:
        if rule.get('connectsTo'):
            targets.append(rule['connectsTo'])
    return targets


def gate_decisions(
    decisions: List[Dict[str, Any]],
    screen_connectors: Dict[str, str],
    cud_names: set,
) -> Dict[str, Any]:
    """Partition decisions into emit vs. flag by deployability.

    A DC ``<decisions>`` element only deploys if every ``<targetReference>`` it
    carries names an element the builder actually emits, and the decision itself
    is reachable from the flow's connector graph. 6a builds screens and decisions
    but does NOT wire the assignment/CUD/lookup targets that legacy decisions
    route to (that is 6b/6c). So the only target 6a can resolve is *another
    surviving decision*, whose api-name the builder preserves verbatim.

    The gate has two transitive passes:

    1. **Resolvability** — a decision survives only if every target is itself a
       surviving decision (fixpoint; a decision pointing at a dropped decision
       is itself dropped).
    2. **Reachability** — of the resolvable set, keep only decisions reachable
       from a screen connector, propagated across decision-to-decision edges.
       An unreachable decision is an orphan and fails deploy in an
       auto-layout canvas.

    Returns ``{'kept': [...], 'flags': [...], 'screen_connectors': {...}}`` where
    ``screen_connectors`` is filtered to those targeting an emitted decision
    (all others fall through to the next screen).
    """
    names = {d['name'] for d in decisions}

    # Pass 1: resolvability fixpoint. CUD-routing decisions are unresolvable
    # by definition (CUD is never a decision), so they drop out here too, but
    # we track them separately to preserve the specific CUD-at-end reason.
    cud_flagged = {
        d['name']: sorted({t for t in _decision_targets(d) if t in cud_names})
        for d in decisions
        if any(t in cud_names for t in _decision_targets(d))
    }
    resolvable = set(names)
    changed = True
    while changed:
        changed = False
        for d in decisions:
            if d['name'] not in resolvable:
                continue
            if any(t not in resolvable for t in _decision_targets(d)):
                resolvable.discard(d['name'])
                changed = True

    # Pass 2: reachability from screen connectors, propagated across surviving
    # decision-to-decision edges.
    reached = {t for t in screen_connectors.values() if t in resolvable}
    changed = True
    while changed:
        changed = False
        for d in decisions:
            if d['name'] in reached:
                for t in _decision_targets(d):
                    if t in resolvable and t not in reached:
                        reached.add(t)
                        changed = True

    emitted = resolvable & reached
    kept: List[Dict[str, Any]] = []
    flags: List[Dict[str, str]] = []
    for d in decisions:
        if d['name'] in emitted:
            kept.append(d)
        elif d['name'] in cud_flagged:
            flags.append({
                'name': d['name'],
                'reason': (f"Decision routes directly to CUD element(s) {cud_flagged[d['name']]}; "
                           f"DC forbids Decision→CUD (CUD-at-end rule). Flagged for WI-7, not emitted."),
            })
        else:
            flags.append({
                'name': d['name'],
                'reason': ("Decision target(s) not yet wired (routes to screens/assignments/lookups "
                           "6a does not build, or is unreachable); deferred to 6b/6c, not emitted."),
            })

    kept_connectors = {
        src: tgt for src, tgt in screen_connectors.items() if tgt in emitted
    }
    return {'kept': kept, 'flags': flags, 'screen_connectors': kept_connectors}


def convert_flow_to_spec(root: ET.Element) -> Dict[str, Any]:
    """Convert a validated legacy flow root to a Data Capture spec.

    Input is the <Flow> element returned by flow_input.load_and_validate_flow;
    parsing and validation happen there, not here.
    """
    flow_label = _findtext(root, 'label') or 'Migrated Flow'

    # build_flow.py expects: screens = {screen_label: [field_dict, ...]}
    # field_dict keys: fieldName, fieldLabel, fieldType, isRequired, options
    spec: Dict[str, Any] = {
        'formTitle': flow_label,
        'formType': 'DataCaptureFlow',
        'apiVersion': _findtext(root, 'apiVersion') or '(unspecified)',
        'screens': {}
    }

    screens = _findall_deep(root, 'screens')
    screen_label_counts: Dict[str, int] = {}
    screen_connectors: Dict[str, str] = {}
    field_level_unsupported: List[Dict[str, str]] = []

    for screen_idx, screen in enumerate(screens, 1):
        raw_label = _findtext(screen, 'label') or f'Screen {screen_idx}'
        # Deduplicate screen labels
        count = screen_label_counts.get(raw_label, 0) + 1
        screen_label_counts[raw_label] = count
        screen_label = raw_label if count == 1 else f'{raw_label} {count}'

        fields_list = []

        for field in _findall(screen, 'fields'):
            field_name = _findtext(field, 'name')
            if not field_name:
                continue

            field_type, meta = extract_field_type(field)

            if meta.get('skip') or field_type is None:
                continue

            label = extract_label(field)
            required = extract_required(field)

            field_spec: Dict[str, Any] = {
                'fieldName': field_name,
                'fieldLabel': label,
                'fieldType': field_type,
                'isRequired': required,
            }

            if meta.get('needsChoices'):
                choices = extract_choices(field, root)
                if choices:
                    field_spec['options'] = choices

            if meta.get('note'):
                field_spec['_migrationNote'] = meta['note']

            if meta.get('unsupported'):
                reason = meta.get('note', '')
                field_spec['fieldLabel'] = f'[UNSUPPORTED: {field_name} — {reason}]'
                field_level_unsupported.append({
                    'type': meta.get('unsupportedType', 'unknownField'),
                    'name': field_name,
                    'reason': reason,
                })

            fields_list.append(field_spec)

        if fields_list:
            spec['screens'][screen_label] = fields_list

            # Only emitted screens (those with migratable fields) can carry a
            # connector in the output; recording a field-less screen's connector
            # would seed reachability from a screen that never exists, letting an
            # orphan decision slip through the deployability gate.
            conn = _findall(screen, 'connector')
            if conn:
                target = _findtext(conn[0], 'targetReference')
                if target:
                    screen_connectors[screen_label] = target

    all_decisions = extract_decisions(root)
    inverted_gate_names = normalize_inverted_gates(root, all_decisions)
    emitted_field_names = {
        f['fieldName'] for fields in spec['screens'].values() for f in fields
    }
    remaining_decisions, collapse_notes = collapse_gating_decisions(
        root, all_decisions, emitted_field_names, spec['screens'],
        _screen_label_by_name(root))
    summary: List[str] = []
    collapsed = [n for n in collapse_notes if 'field' in n or 'section' in n]
    if collapsed:
        spec['_collapsedDecisions'] = collapsed
    # _invertedGates must reflect gates that ACTUALLY collapsed, not just normalized
    collapsed_decision_names = {n['decision'] for n in collapsed}
    actually_inverted = [name for name in inverted_gate_names
                         if name in collapsed_decision_names]
    if actually_inverted:
        spec['_invertedGates'] = actually_inverted
    for n in collapsed:
        if 'section' in n:
            summary.append(
                f"Decision {n['decision']} collapsed into section '{n['section']}' "
                f"visibility (fields: {', '.join(n['fields'])}).")
            for cf in n.get('clearedRequired') or []:
                summary.append(
                    f"Cleared isRequired on '{cf}' (inside gated section "
                    f"'{n['section']}'); add a conditional validation rule in Flow "
                    f"Builder if it must be required when shown.")
        else:
            summary.append(
                f"Decision {n['decision']} collapsed into visibility on field "
                f"{n['field']}.")
        if n['decision'] in actually_inverted:
            item = 'section' if 'section' in n else 'field'
            summary.append(
                f"Decision {n['decision']} was an inverted-shape gate; its "
                f"condition was negated so the {item} shows on the same inputs "
                f"as the original flow.")

    cud_names = _cud_element_names(root)
    gated = gate_decisions(remaining_decisions, screen_connectors, cud_names)
    if gated['kept']:
        spec['decisions'] = gated['kept']
    if gated['flags']:
        spec['_decisionFlags'] = gated['flags']
    if gated['screen_connectors']:
        spec['_screenConnectors'] = gated['screen_connectors']

    # WI-7 structural ceilings (post-CUD / fault / loop) go in their OWN key.
    # _decisionFlags is decision-routing only; ceilings are a distinct concern
    # and the same element name legitimately appears in both surfaces, so
    # merging them would collide (name-keyed lookups would return the wrong
    # reason). Both keys plus _migrationSummary honour "flag, never drop".
    ceiling = detect_ceiling_violations(root)
    if ceiling:
        spec['_ceilingFlags'] = ceiling
        for c in ceiling:
            summary.append(f"{c['name']}: {c['reason']}")

    # WI-8: ordinal CUD-placement analysis replaces the old count-based note.
    cud_report = cud_analysis.analyze_cud_placement(root)
    consolidated: List[Dict[str, Any]] = []
    manual: List[Dict[str, Any]] = []
    for node in cud_report.cud_nodes:
        if node.verdict == "compliant":
            continue
        if node.verdict == "safe_consolidate" and node.op == "create":
            consolidated.append({
                'node': node.name, 'op': node.op,
                'from': f'mid-flow (position {node.position})', 'to': 'postScreen'})
            summary.append(
                f"CUD create '{node.name}' auto-consolidated to end-of-flow "
                f"(postScreen); was mid-flow at position {node.position}.")
        elif node.verdict == "safe_consolidate":
            reason = (f"Record {node.op} '{node.name}' is data-safe to move to "
                      f"end-of-flow, but there is no automated update/delete "
                      f"postScreen emission path — move it manually after the last "
                      f"screen.")
            manual.append({'node': node.name, 'op': node.op,
                           'position': node.position, 'reason': reason,
                           'blockers': list(node.blockers)})
            summary.append(f"{node.name}: {reason}")
        else:  # unsafe_manual
            reason = (f"Record {node.op} '{node.name}' at position {node.position} "
                      f"cannot be auto-consolidated: {'; '.join(node.blockers)}. "
                      f"Restructure manually so all CUD runs after the last screen.")
            manual.append({'node': node.name, 'op': node.op,
                           'position': node.position, 'reason': reason,
                           'blockers': list(node.blockers)})
            summary.append(f"{node.name}: {reason}")

    cud_elements_present = bool(cud_report.cud_nodes)
    if cud_elements_present:
        spec['_cudAnalysis'] = {
            'consolidated': consolidated,
            'manualRestructure': manual,
            'hasMidFlowCud': cud_report.has_midflow,
        }
    if consolidated:
        ps_creates = _build_postscreen_creates(root, consolidated)
        if ps_creates:
            post = spec.get('postScreen')
            if not isinstance(post, dict):
                post = {}
            post['recordCreates'] = ps_creates
            spec['postScreen'] = post
    if cud_report.has_midflow:
        spec['_automationNote'] = (
            'Mid-flow CUD detected — DataCaptureFlow requires all create/update/'
            'delete at end-of-flow. See _cudAnalysis for per-node consolidation '
            'and manual-restructure guidance.'
        )

    subflows = _findall_deep(root, 'subflows')

    if subflows:
        spec['_subflowNote'] = (
            f'{len(subflows)} subflow call(s) detected. '
            f'DataCaptureFlow subflows cannot contain CUD operations. '
            f'Inline any CUD logic from subflows into the main flow.'
        )

    incomplete = detect_unsupported_elements(root) + field_level_unsupported
    if incomplete:
        spec['_incompleteMigration'] = incomplete

    if summary:
        spec['_migrationSummary'] = summary

    return spec


def main():
    if len(sys.argv) != 3:
        print(f"[ERROR] Missing required argument. "
              f"Usage: {sys.argv[0]} <input_flow.xml> <output_spec.json>\n"
              f"Example: {sys.argv[0]} "
              f"force-app/main/default/flows/MyFlow.flow-meta.xml /tmp/spec.json",
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

    spec = convert_flow_to_spec(root)

    # Validate: build_flow.py requires at least one screen with at least one field
    if not spec['screens']:
        spec['screens'] = {'Migrated Screen': [
            {'fieldName': 'placeholder',
             'fieldLabel': '[Auto-migrated — no screen fields detected. Review in Flow Builder.]',
             'fieldType': 'DisplayText', 'isRequired': False}
        ]}
        spec['_migrationNote'] = 'No screen fields detected in source flow. Flow may be automation-only or use unsupported field types. Review and replace placeholder in Flow Builder.'

    with open(output_path, 'w') as f:
        json.dump(spec, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Conversion Complete: {spec['formTitle']}")
    print(f"{'='*60}")
    print(f"API Version: {spec['apiVersion']}")
    print(f"Screens: {len(spec['screens'])}")
    total_fields = sum(len(fields) for fields in spec['screens'].values())
    print(f"Fields: {total_fields}")

    notes = []
    for screen_label, fields in spec['screens'].items():
        for field in fields:
            if '_migrationNote' in field:
                notes.append(f"  - {field['fieldName']}: {field['_migrationNote']}")

    if notes:
        print(f"\nManual Configuration Required:")
        for note in notes:
            print(note)

    if '_automationNote' in spec:
        print(f"\nAutomation Review: {spec['_automationNote']}")

    if '_subflowNote' in spec:
        print(f"\nSubflow Warning: {spec['_subflowNote']}")

    if '_collapsedDecisions' in spec:
        print(f"\nCollapsed gating decisions -> visibility:")
        for n in spec['_collapsedDecisions']:
            if 'section' in n:
                print(f"  - {n['decision']} collapsed into section "
                      f"'{n['section']}' visibility "
                      f"(fields: {', '.join(n['fields'])})")
            else:
                print(f"  - {n['decision']} collapsed into visibility on "
                      f"field {n['field']}")

    if '_migrationSummary' in spec:
        print(f"\nMigration Summary:")
        for line in spec['_migrationSummary']:
            print(f"  - {line}")

    if '_incompleteMigration' in spec:
        entries = spec['_incompleteMigration']
        print(f"\nIncomplete Migration ({len(entries)} unsupported element(s) "
              f"— see the comment block at the top of the built XML):")
        for e in entries:
            print(f"  - [{e['type']}] {e['name']}: {e['reason']}")

    if '_migrationNote' in spec:
        print(f"\nNote: {spec['_migrationNote']}")

    print(f"\nSpec written to: {output_path}\n")


if __name__ == '__main__':
    main()
