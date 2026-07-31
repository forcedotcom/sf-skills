# Worked Example — Render an Existing Apex-Backed Lightning Type

## User prompt

> Build a widget for the OrderSummary Lightning Type — show order id, customer, total, and a list of line items.

## Walkthrough

**Phase 1 — Path selection.** The prompt names a Lightning Type (`OrderSummary`) and treats it as existing → pick the `existing-lightning-type-with-widget` path. Phase 4 will load `platform-widget-generate` only, after Phase 2 confirms the type is Apex-backed.

**Phase 2 — Lightning Type discovery.** Find first, verify after.

```bash
$ rg -l 'lightning:type' force-app/**/lightningTypes/OrderSummary/
force-app/main/default/lightningTypes/OrderSummary/schema.json
```

Found in the local project. Now verify in scope — read `schema.json`. Root is `"lightning:type": "@apexClassType/orders__OrderSummary"`. Apex-backed → continue. Capture path + SHA-256 + Apex class FQN `orders__OrderSummary` (outer-class form; an inner-class root like `orders__OrderResponses$CreateResult` is also in scope and would scope the trace to that inner class). Source = `existing in local project`.

> If the root had been `lightning__objectType` (object/JSON-based), the orchestrator would have stopped here and routed the user to use `platform-custom-lightning-type-generate` and `platform-widget-generate` separately.

**Phase 3 — Build plan.** Print:

```text
Lightning Type + Widget Build Plan: orderSummaryWidget

PLAN: Generate a widget that renders the existing OrderSummary Lightning Type.

LIGHTNING TYPE:
  Name: OrderSummary
  Source: existing in local project
  Path: force-app/main/default/lightningTypes/OrderSummary/schema.json
  Renderer (wires the Lightning Type to the widget): force-app/main/default/lightningTypes/OrderSummary/renderer.json
  Schema fingerprint (captured before any sub-skill runs): <hex>
  Apex class FQN: orders__OrderSummary

WIDGET:
  Name: orderSummaryWidget
  Output:
    force-app/main/default/uiWidgets/orderSummaryWidget/orderSummaryWidget.json
    force-app/main/default/uiWidgets/orderSummaryWidget/schema.json
    force-app/main/default/uiWidgets/orderSummaryWidget/orderSummaryWidget.uiwidget-meta.xml
  Schema source: derived from Apex class @AuraEnabled fields via the Lightning Type
  Layout intent: card with header (id + customer), body (total + shipping-address fields), footer (line items list with forEach)
  Properties omitted: lastUpdatedTime (audit field, not relevant to render — proposed omission)

SUB-SKILLS THAT WILL RUN:
  platform-widget-generate

VALIDATIONS THAT WILL RUN AFTER GENERATION:
  Widget bundle self-validation (run by platform-widget-generate):
    - widget schema.json parses, root keys correct, every leaf has lightning:type
    - every {!$attrs.X} (and {!$attrs.shippingAddress.city} for the singular nested address object) resolves
    - <name>.uiwidget-meta.xml is well-formed XML, root is <UiWidgetBundle>, and declares <widgetType>JSON</widgetType>
  Cross-skill checks (run by this orchestrator):
    - lightning-type-unchanged: existing schema.json is byte-identical to the captured fingerprint
    - renderer-wires-widget: renderer.json references @widget/c/orderSummaryWidget with one {!$attrs.<schemaPropertyName>} mapping per widget schema property
    - field-trace: print @AuraEnabled fields, widget properties (with nested dot paths and list-item paths expanded), and the diff

----------------------------------------------------------------
STOP — wait for the user to Approve or Decline.
```

User picks Approve.

**Phase 4 — Generation.** Load `platform-widget-generate`. Hand it the Lightning Type schema path, the Apex class FQN (`orders__OrderSummary`), and the widget name. The widget skill derives its `schema.json` from the Apex class's `@AuraEnabled` fields:

- Primitive fields → primitive `lightning:type`.
- Singular nested inner class (e.g. `Address shippingAddress`) → `lightning__objectType`; bound in the widget body via dot-notation `{!$attrs.shippingAddress.city}`, `{!$attrs.shippingAddress.zip}`.
- `List<LineItem> lineItems` → `lightning__listType`; iterated with `forEach`/`forItem` and bound via `{!$item.<innerField>}`.

The skill omits `lastUpdatedTime` per the build plan and writes the three widget files. Then author `force-app/main/default/lightningTypes/OrderSummary/renderer.json` using the widget-rendition pattern, binding each widget attribute via `{!$attrs.<schemaPropertyName>}`. (If `renderer.json` already exists referencing a different widget or a custom LWC, STOP and surface the conflict.)

**Phase 5 — Validation.** The widget skill reports its own self-validation results. This orchestrator runs:

- `lightning-type-unchanged` — confirms the Lightning Type was untouched.
- `renderer-wires-widget` — confirms the renderer points at this widget and binds every widget schema property.
- `field-trace` — prints APEX_FIELDS / WIDGET_PROPS / INVENTED / OMITTED. The omission of `lastUpdatedTime` is in the build plan and emits no warning.

**Phase 6 — Summary.** Print files generated and each validation result by name (`lightning-type-unchanged: pass`, `renderer-wires-widget: pass`, `field-trace: pass`), followed by the deploy command.
