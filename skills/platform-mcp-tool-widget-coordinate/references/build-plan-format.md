# Build Plan Format

Use this template in Phase 3 to print the plan before proceeding. Fill every section. Do not abbreviate. Do not print inside a code fence the user might mistake for output — the plan is conversational.

---

```text
MCP Tool Widget Build Plan: <widgetName>

PLAN: <one line in developer-facing terms, e.g.:
  "Render the GetAccountSummary MCP tool output with an account-summary widget">

TOOL / SOURCE:
  Tool API name: <toolApiName>
  Payload source: <action: Actions REST describe of <ActionApiName> | apex: class <ClassName> | sample: pasted tool-output>
  Response class FQN: <namespace>__<ClassName>.<ResponseClass>   # apex source only; omit for action/sample

LIGHTNING TYPES (two object-based CLTs of equal standing — named for what each models, not by role; both carry root-level "lightning:tags": ["mcp"]):
  Response CLT:
    Name: <responseCLT>          # convention: <toolApiName>Response
    Path: <pkgDir>/lightningTypes/<responseCLT>/schema.json
    Properties: <field: lightning:type, ...>   # 1:1 with response @InvocableVariable fields
  Envelope CLT:
    Name: <toolCLT>          # convention: <toolApiName>
    Path: <pkgDir>/lightningTypes/<toolCLT>/schema.json
    Renderer (default, at bundle root — wires the widget): <pkgDir>/lightningTypes/<toolCLT>/renderer.json
    Envelope properties: actionName (text), isSuccess (boolean), outputValues (c__<responseCLT>), <plus any others>

WIDGET:
  Name: <widgetName>          # convention: <toolApiName>Widget
  Output:
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json
    <pkgDir>/uiWidgets/<widgetName>/schema.json
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml
  Schema source: derived from the response field list (name + primitive type) — a standalone contract, not tied to any Lightning Type
  Renderer binding: each widget attribute maps to {!$attrs.outputValues.<field>}
  Layout intent: <one-line description of the widget composition>
  Properties omitted: <response fields the widget intentionally drops, with rationale — or "none">
    # actionName/isSuccess never appear here — they are envelope-only and never candidates for the widget.
    # Default omissions to declare when present in the response: isSuccess, errorMessage, status, message
    # (operational/status indicators, not display data) — each needs its own one-line rationale, not just the field name.

SUB-SKILLS THAT WILL RUN:
  platform-custom-lightning-type-generate   (response CLT, then envelope CLT)
  platform-widget-generate                  (widget bundle)
  (renderer.json authored inline in the envelope CLT by this orchestrator)

VALIDATIONS THAT WILL RUN AFTER GENERATION:
  Widget bundle self-validation (run by platform-widget-generate):
    - widget schema.json parses and has the required root keys
    - every leaf in properties has a lightning:type
    - every {!$attrs.X} resolves to a widget schema property
    - <name>.uiwidget-meta.xml is well-formed, root <UiWidgetBundle>, declares <widgetType>JSON</widgetType>
  Cross-skill checks (run by this orchestrator):
    - clt-reference-integrity: envelope CLT outputValues → c__<responseCLT>; response CLT exists; no $schema/items
    - renderer-wires-widget: envelope CLT renderer.json (bundle root) references the widget via @widget/c/<widgetName>,
      binding every widget property as {!$attrs.outputValues.<property>}
    - field-trace (advisory): print response @InvocableVariable fields and widget schema properties; print the diff.
      Invented widget fields fail; omissions not declared above warn.

GENERATION ORDER: response CLT → widget → envelope CLT (response CLT must exist before the envelope CLT references it).

----------------------------------------------------------------
Proceeding unless you push back (reply "no", "stop", "change X"). The plan above is the record of intent.
```

---

## Notes for the model

- If the user replies with edits or declines, revise the plan and reprint. Do not assume which sections changed.
- Approval applies only to the plan as printed. A later request for another tool starts a new planning cycle.
- "Properties omitted" makes intentional drops explicit — e.g. `status`, `message`, internal IDs that do not belong on the render surface.
- If the payload source is a pasted sample that nests under `outputValues.data`, record that extra level here — it changes the response CLT and every renderer binding to `{!$attrs.outputValues.data.<field>}`.
