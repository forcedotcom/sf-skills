# Build Plan Format

Use this template in Phase 3 to print the plan before the STOP gate. Fill every section. Do not abbreviate.

---

```text
Lightning Type + Widget Build Plan: <widgetName>

PLAN: <one line in developer-facing terms, e.g.:
  "Generate a widget that renders the existing OrderStatusResponse Lightning Type"
  OR
  "Create a new Apex class, Lightning Type, and widget for AppointmentSummary">

LIGHTNING TYPE:
  Name: <TypeName>
  Source: <existing in local project | retrieved from org | newly created>
  Path: <pkgDir>/lightningTypes/<TypeName>/schema.json
  Renderer (wires the Lightning Type to the widget): <pkgDir>/lightningTypes/<TypeName>/lightningDesktopGenAi/renderer.json
  Schema fingerprint (captured before any sub-skill runs): <hex SHA-256>   # omit when source is "newly created"
  Apex class FQN: <namespace>__<ClassName>[$<InnerClass>]   # outer-class form, or inner-class form when the CLT roots on a specific inner class

APEX (only when creating a new Lightning Type — auto-engaged because this orchestrator only supports Apex-backed Lightning Types):
  Class name: <ClassName>
  Class FQN: <namespace>__<ClassName>
  Shape: outer class with @AuraEnabled fields matching the desired Lightning Type payload. Inner classes are used for nested list-element types (e.g. List<OpenOpportunity>) and for singular nested objects (e.g. Address address). The Apex shape itself is owned by platform-apex-generate; this plan records the FQN and field summary, not the class body.
  Returns: typed payload shaped to <TypeName>

WIDGET:
  Name: <widgetName>
  Output:
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json
    <pkgDir>/uiWidgets/<widgetName>/schema.json
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml
  Schema source: <derived from Apex class @AuraEnabled fields via the Lightning Type | derived from prompt fields>
  Layout intent: <one-line description of the widget composition>
  Properties omitted: <list any Apex class fields the widget intentionally drops, e.g. lastUpdatedTime, audit fields — or "none">

SUB-SKILLS THAT WILL RUN:
  <list per the chosen path's row in SKILL.md — skill IDs only>

VALIDATIONS THAT WILL RUN AFTER GENERATION:
  Widget bundle self-validation (run by platform-widget-generate):
    - widget schema.json parses and has the required root keys
    - every leaf in properties has a lightning:type
    - every {!$attrs.X} (and {!$attrs.<outer>.<inner>} for nested objects, {!$item.X} inside forEach) resolves
    - <name>.uiwidget-meta.xml is well-formed XML, root is <UiWidgetBundle>, and declares <widgetType>JSON</widgetType>
  Cross-skill checks (run by this orchestrator):
    - lightning-type-unchanged: when an existing Lightning Type was used as input, its schema.json is byte-identical to the version captured before this run
    - renderer-wires-widget: the Lightning Type's renderer.json exists and references this widget via `@widget/c/<widgetName>`, with one {!$attrs.<schemaPropertyName>} mapping per widget schema property
    - field-trace (advisory): print the @AuraEnabled fields from the outer Apex class plus every inner class referenced as a singular nested object or List<InnerClass>; print the widget schema properties (expanded for nested objects and list items); print the diff. Invented widget fields fail; omissions not declared above warn.
    - deploy-check (advisory, new-type path only): `sf project deploy --check-only --source-dir <pkgDir>/classes/<ClassName>.cls,<pkgDir>/lightningTypes/<TypeName>` is run and the result reported.

----------------------------------------------------------------
STOP — wait for the user to Approve or Decline.
The host surface may render Approve/Decline as buttons; a text reply ("approve", "yes", "go") is also accepted.
A Decline (or edits to the plan) reprints the plan; the orchestrator does not write any file until an explicit Approve.
```

---

## Notes for the model

- If the user replies with edits or declines, revise the plan and reprint it. Do not assume which sections changed.
- Approval applies only to the plan as printed. If the user later asks for additional widgets or Lightning Types, start a new planning cycle for the new ask.
- Do not print this plan inside a code fence that the user might mistake for output. The plan is conversational, not a file.
- "Properties omitted" makes intentional drops explicit. Examples of fields that often do not belong on a render surface: `lastUpdatedTime`, `createdBy`, audit timestamps, internal IDs.
