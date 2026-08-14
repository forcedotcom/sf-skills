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
    Nested/list fields: <objectField: @apexClassType/c__<Outer>$<Inner>, ... — or "none">
      # A single nested object is one @apexClassType property; a List<ApexClass> rides INSIDE an
      # @apexClassType object (the CLT carries no lightning__listType — the list surfaces in the widget schema).
  Envelope CLT:
    Name: <toolCLT>          # convention: <toolApiName>
    Path: <pkgDir>/lightningTypes/<toolCLT>/schema.json
    Renderer (default, at bundle root — wires the widget): <pkgDir>/lightningTypes/<toolCLT>/renderer.json
    Envelope properties: actionName (text), isSuccess (boolean), outputValues (c__<responseCLT>)   # exactly these three — no others

WIDGET:
  Name: <widgetName>          # convention: <toolApiName>Widget
  Output:
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json
    <pkgDir>/uiWidgets/<widgetName>/schema.json
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml
  Schema source: derived from the response field list (name + primitive type) — a standalone contract, not tied to any Lightning Type
  List fields: <listField: element class @apexClassType/c__<Outer>$<Inner> — or "none">   # widget schema/body authored by platform-widget-generate
  Renderer binding: primitive → {!$attrs.outputValues.<field>}; nested-object leaf → {!$attrs.outputValues.<objectField>.<leaf>};
    list → {!$attrs.outputValues.<listField>} (top-level) or {!$attrs.outputValues.<wrapperField>.<listField>} (list inside wrapper)
  Layout intent: <one-line description of the widget composition, incl. how lists are rendered>
    # actionName/isSuccess are envelope-only fields (on the envelope CLT) and never widget candidates.

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
    - clt-reference-integrity: envelope CLT outputValues → c__<responseCLT>; response CLT exists; no $schema/items;
      non-primitive response fields typed @apexClassType (no CLT-level lightning__listType — lists ride inside the object)
    - renderer-wires-widget: envelope CLT renderer.json (bundle root) references the widget via @widget/c/<widgetName>,
      binding every widget property under outputValues ({!$attrs.outputValues.<property>}, or
      {!$attrs.outputValues.<objectField>.<leaf|listField>} for nested/list fields)
    - nested-list-coverage: every nested-object and list field discovered in Phase 2 is rendered by the widget
      (authored by platform-widget-generate) and bound in the renderer at the correct depth. A discovered
      nested/list field that is absent FAILS ("out of scope" / "beta single-response" are not valid drop rationales).
    - field-trace (advisory): print response @InvocableVariable fields and widget schema properties; print the diff.
      Invented widget fields fail; a response data field absent from the widget warns.

GENERATION ORDER: response CLT → widget → envelope CLT (response CLT must exist before the envelope CLT references it).

----------------------------------------------------------------
Proceeding unless you push back (reply "no", "stop", "change X"). The plan above is the record of intent.
```

---

## Notes for the model

- If the user replies with edits or declines, revise the plan and reprint. Do not assume which sections changed.
- Approval applies only to the plan as printed. A later request for another tool starts a new planning cycle.
- If the payload source is a pasted sample that nests under `outputValues.data`, record that extra level here — it changes the response CLT and every renderer binding to `{!$attrs.outputValues.data.<field>}`.
