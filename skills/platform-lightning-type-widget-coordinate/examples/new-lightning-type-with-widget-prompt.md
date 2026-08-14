# Worked Example — Create a New Apex-Backed Lightning Type With a Widget

## User prompt

> Generate a Lightning Type and a widget for an account briefing — fields: account name, owner, last activity date, top three open opportunities.

> Note: the user did not mention Apex. This orchestrator only supports Apex-backed Lightning Types, so the `new-lightning-type-with-widget` path implicitly engages `platform-apex-generate` because the new typed Lightning Type requires a backing Apex class. The orchestrator surfaces this Apex step in the Phase 3 build plan so the developer sees what it intends to do.

## Walkthrough

**Phase 1 — Path selection.** User asks for a new Lightning Type plus a widget. Pick the `new-lightning-type-with-widget` path: `platform-apex-generate` → `platform-custom-lightning-type-generate` → `platform-widget-generate`. Apex backing for the typed payload is implied; do not ask the user to confirm Apex is wanted.

**Phase 2 — Lightning Type discovery.** **Skipped.** The prompt is explicit about creating a new Lightning Type, so there is no existing schema to discover and no fingerprint to capture.

**Phase 3 — Build plan.** Print:

```text
Lightning Type + Widget Build Plan: accountBriefingWidget

PLAN: Create a new Apex class, Lightning Type, and widget for AccountBriefing.

LIGHTNING TYPE:
  Name: AccountBriefing
  Source: newly created
  Path: force-app/main/default/lightningTypes/AccountBriefing/schema.json
  Renderer (wires the Lightning Type to the widget): force-app/main/default/lightningTypes/AccountBriefing/renderer.json
  Apex class FQN: c__AccountBriefing

APEX (only when creating a new Lightning Type — auto-engaged because this orchestrator only supports Apex-backed Lightning Types):
  Class name: AccountBriefing
  Class FQN: c__AccountBriefing
  Shape: outer class with @AuraEnabled fields (accountName, ownerName, lastActivityDate, primaryContact: Contact, openOpportunities: List<OpenOpportunity>). Contact is an inner class for a singular nested object. OpenOpportunity is an inner class for nested list elements. The Apex shape itself is owned by platform-apex-generate.
  Returns: typed payload shaped to AccountBriefing

WIDGET:
  Name: accountBriefingWidget
  Output:
    force-app/main/default/uiWidgets/accountBriefingWidget/accountBriefingWidget.json
    force-app/main/default/uiWidgets/accountBriefingWidget/schema.json
    force-app/main/default/uiWidgets/accountBriefingWidget/accountBriefingWidget.uiwidget-meta.xml
  Schema source: derived from Apex class @AuraEnabled fields via the Lightning Type
  Layout intent: header card (name + owner + last activity + primary contact name/title via dot-notation), body list (top opportunities with forEach over List<OpenOpportunity>)
  Properties omitted: none

SUB-SKILLS THAT WILL RUN:
  platform-apex-generate
  platform-custom-lightning-type-generate
  platform-widget-generate

VALIDATIONS THAT WILL RUN AFTER GENERATION:
  Widget bundle self-validation (run by platform-widget-generate):
    - widget schema.json parses, root keys correct, every leaf has lightning:type
    - every {!$attrs.X} (and {!$attrs.primaryContact.name} for the singular nested contact object, {!$item.X} inside forEach) resolves
    - <name>.uiwidget-meta.xml is well-formed XML, root is <UiWidgetBundle>, and declares <masterLabel>, <description>, and <widgetType>JSON</widgetType>
  Cross-skill checks (run by this orchestrator):
    - renderer-wires-widget: renderer.json references @widget/c/accountBriefingWidget with one {!$attrs.<schemaPropertyName>} mapping per widget schema property
    - field-trace: print @AuraEnabled fields from AccountBriefing plus inner classes Contact and OpenOpportunity, widget properties (with nested dot paths and list-item paths expanded), and the diff
    - deploy-check: `sf project deploy --check-only --source-dir force-app/main/default/classes/AccountBriefing.cls,force-app/main/default/lightningTypes/AccountBriefing` (RUN the command — do not assume).

----------------------------------------------------------------
STOP — wait for the user to Approve or Decline.
```

User picks Approve.

**Phase 4 — Generation.**

1. Load `platform-apex-generate`. Author `AccountBriefing.cls` (outer class with `@AuraEnabled` fields including `Contact primaryContact` as a singular nested object and `List<OpenOpportunity> openOpportunities` as a list-element collection; `Contact` and `OpenOpportunity` are inner classes). Capture FQN `c__AccountBriefing` (outer-class form for this example).
2. Load `platform-custom-lightning-type-generate`. Author `lightningTypes/AccountBriefing/schema.json` with `lightning:type: "@apexClassType/c__AccountBriefing"` (outer-class form).
3. Load `platform-widget-generate`. Pass the Lightning Type schema path, the Apex class FQN, and the widget name. The widget skill derives its `schema.json` and writes the three widget files. `Contact primaryContact` becomes a `lightning:type: "@apexClassType/c__AccountBriefing$Contact"` property bound via `{!$attrs.primaryContact.name}` etc.; `List<OpenOpportunity>` becomes a `lightning__listType` property whose body iterates with `forEach`/`forItem` and binds `{!$item.<innerField>}`.
4. Author `lightningTypes/AccountBriefing/renderer.json` using the **widget rendition pattern** (see `platform-custom-lightning-type-generate/SKILL.md` step 4): a thin wrapper whose first child is `"definition": "@widget/c/accountBriefingWidget"` with attribute mappings binding each widget attribute to a Lightning Type schema property via `{!$attrs.<schemaPropertyName>}`.

**Phase 5 — Validation.** The widget skill reports its own self-validation results. This orchestrator runs `renderer-wires-widget`, `field-trace`, and `deploy-check` (the `sf project deploy --check-only ...` command above). Reporting `pass` without running `deploy-check` is a hard violation — report `not run` instead.

**Phase 6 — Summary.** Print each validation result by name and value (`renderer-wires-widget: pass`, `field-trace: pass`, `deploy-check: pass`), files generated, and the deploy command.
