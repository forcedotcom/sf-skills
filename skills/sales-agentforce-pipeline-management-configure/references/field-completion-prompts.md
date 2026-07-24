# Field Completion Prompt Templates

This reference covers adding Pipeline Management field-update suggestions for Opportunity text fields beyond the two the pipeline ships with (`NextStep` and `StageName`).

Everything here was verified end-to-end on a live org (deploy → activate → generate). The canonical XML lives at `assets/field-completion-template.genAiPromptTemplate-meta.xml`; the automation that fills it in and wires the flow is `scripts/add-field-suggestion.sh`.

> **Naming note — "Field Generation" vs "Field Completion".** The prompt-template metadata `<type>` is `einstein_gpt__fieldCompletion` (used everywhere in metadata, filenames, and this repo — do not change it). In the **Setup UI** (Prompt Builder), Salesforce labels this template category **"Field Generation"**. They are the same thing: an admin looking in Setup should look for **Field Generation**, not "Field Completion".

---

## Use the script — do not hand-author

**`scripts/add-field-suggestion.sh` is the supported path.** It performs the full, order-sensitive sequence deterministically so you never have to guess version identifiers or edit the flow by hand:

> **Field cap:** Pipeline Management manages at most **5 Opportunity fields total**, and the two OOTB fields (`NextStep`, `StageName`) count toward that 5. `add-field-suggestion.sh` enforces this — when the flow already wires 5 fields, adding a new one fails with a "field cap reached" error (adding a field already wired is an idempotent no-op and is never blocked). To add a 6th, remove one first (decline an OOTB field during `setup-all.sh`, or strip it from the flow).


```bash
cd scripts
./add-field-suggestion.sh <org-alias> <FieldApiName> \
  [--label "Human Label"] \
  [--instruction "one line of field-specific extraction guidance"] \
  [--goal "one sentence: what the model should think about"] \
  [--name RecommendXforOpp] \
  [--opp <OpportunityId>] \
  [--verify-with-note] \
  [--skip-flow]
```

Example (the exact call verified on the org):

```bash
./add-field-suggestion.sh pipeline-mgmt-org Deal_Momentum__c \
  --label "Deal Momentum" \
  --goal "how much forward momentum this deal has and what is stalling it" \
  --instruction "Summarize momentum signals: engagement cadence, stakeholder involvement, and blockers." \
  --verify-with-note
```

What the script does, in order:

1. **Validate the field** — describes the Opportunity and confirms the field is plain Text (`type=string`) or Text Area ≤ 255 (`type=textarea`, not `htmlFormatted`), `updateable`, not calculated, length ≤ 255. If the field exists in the Tooling `FieldDefinition` but not in the describe, it reports "field has no FLS" and prints the exact `FieldPermissions` grant command instead of failing silently.
2. **Fill the canonical template** — substitutes placeholders into `assets/field-completion-template.genAiPromptTemplate-meta.xml`, preserving the OOTB instruction body verbatim.
3. **Deploy + activate (the version round-trip)** — deploys `Published` with no version identifiers, retrieves the platform-generated `<versionIdentifier>`, sets it as `<activeVersionIdentifier>`, and redeploys to activate. Confirms active via the `/einstein/prompt-templates` endpoint.
4. **Wire the flow** — idempotently adds the field API name to the `Process_Field_Update_Suggestions` flow's `AddOppFieldsToCollection` assignment (skipped with `--skip-flow`).
5. **Verify (optional, `--verify-with-note`)** — seeds a ContentNote on a sample opportunity and calls the synchronous `/generations` endpoint, printing the generated JSON.

Only read the rest of this doc if you need to understand *why* the pattern is shaped the way it is, or to debug a failure.

---

## Prerequisites

- The field must be a **standard or custom text field** on Opportunity — plain Text (`type=string`) or Text Area ≤ 255 (`type=textarea`, not `htmlFormatted`). Long Text Area (length > 255), Rich Text Area (`htmlFormatted`), picklist, formula, and non-text fields are not supported.
- `SuggestedNewValue` is capped at the **field's own length** (≤ 255). The script sets the cap from the field's `length` automatically.
- The field must be **FLS-accessible** to the running user. A freshly deployed custom field has no field-level security and is invisible to `sf sobject describe` until you grant it — this is the single most common first-run failure.
- A field can have only **one** field-completion prompt template.

---

## Verified template structure (v67)

The canonical asset is the source of truth. The invariants below are what make it work; do not "simplify" them.

| Element | Correct value | Common wrong value to avoid |
|---------|---------------|-----------------------------|
| `<type>` | `einstein_gpt__fieldCompletion` | `field_generation` |
| Input `<apiName>` | `RelatedEntity` (platform-fixed for MDAPI-authored templates) | `Opportunity` |
| Input `<referenceName>` | `Input:Opportunity` | — |
| Body merge fields | `{!$Input:Opportunity.<field>}` | `{!$Input:Opportunity}` |
| `<relatedField>` | object-qualified: `Opportunity.<field>` | bare `<field>` |
| Grounding | a `<templateDataProviders>` block (`flow://sales_pipe_mgmt__GetOppGroundingData`) is **required** | omitting it |
| `<status>` | `Published` | `Draft` |
| Version | none at author time — added by the deploy round-trip | hand-authored `versionNumber` / `activeVersion` |

There is **no** `templateType`, `versionNumber`, or `activeVersion` element. The correct activation field is `<activeVersionIdentifier>`, and its value is the platform-generated `<versionIdentifier>` returned by a retrieve — never hand-authored or guessed.

**`GenAiPromptTemplate` IS CLI-retrievable** for user-created templates (this is how the script gets the version identifier). Only the managed `sales_pipe_mgmt__*` templates are non-retrievable. Any doc or comment claiming user templates cannot be retrieved is wrong and was the root cause of prior version-identifier guessing.

The instruction body is the OOTB Pipeline Management body verbatim; only the field name and two field-specific lines (goal + instruction) change. Character caps inside the body: `SuggestedNewValue` = the field length, `Reasoning` = 250, `Snippet` = 100, `DueDate` = `"30 days"`.

---

## The three requirements for a field to produce suggestions

A field generates `AiGenActionItem` records only when **all three** hold:

1. **Template deployed and activated** — `<status>Published</status>` with a valid `<activeVersionIdentifier>` (the script's round-trip).
2. **Field added to the flow** — the field API name is a `<stringValue>` in the `AddOppFieldsToCollection` assignment (collection `OpportunityFields`), which feeds the `getOrExecFieldUpdtSuggestion` action's `fieldApiNames` parameter.
3. **Field FLS-accessible** — the running/agent user can read and edit the field.

Missing any one produces zero suggestions with no error.

---

## Data source grounding flow

Every field-completion template references `{!$Flow:sales_pipe_mgmt__GetOppGroundingData.Prompt}` — a PromptFlow (not a schedule-triggered flow) provisioned by Pipeline Management. It gathers `ContentNote`, `EmailMessage` (if Einstein Activity Capture is on), and call transcripts (if Einstein Conversation Insights is on) from the last 30 days and formats them into the prompt input.

Do **not** change this reference, invoke the flow directly, or build your own replacement. See `references/data-sources.md` for enabling the underlying data products.

---

## Verifying generation

Two ways to confirm a template works:

**Synchronous (deterministic, preferred for testing)** — the `/generations` endpoint returns the model output directly, proving prompt + grounding + field binding are all correct:

```bash
sf api request rest "/services/data/v64.0/einstein/prompt-templates/<TemplateName>/generations" \
  --method POST --target-org "$ORG" \
  --body '{"isPreview":false,"inputParams":{"valueMap":{"Input:Opportunity":{"value":{"id":"<oppId>"}}}},"additionalConfig":{"numGenerations":1,"temperature":0,"applicationName":"PromptTemplateGenerationsInvocable"}}'
```

`.generations[0].text` is the JSON output; `.prompt` is the fully resolved prompt. Note `isPreview` **must** be `false` — preview mode cannot resolve the `GetOppGroundingData` data provider (a preview-mode limitation, not a config error). This is exactly what `--verify-with-note` runs.

**Asynchronous (the real pipeline)** — suggestions land as `AiGenActionItem` records ~3 minutes after the schedule-triggered flow runs. Query them by Opportunity and field:

```bash
sf data query -q "SELECT Id, Subject, Status, SuggestedNewValue FROM AiGenActionItem WHERE Type = 'FIELD_UPDATE' AND ParentId = '<oppId>' ORDER BY CreatedDate DESC" --target-org "$ORG" --json 2>/dev/null
```

`ParentId` = the Opportunity Id (filterable), `Subject` = the field API name (e.g. `Risk__c`). Poll ≥ 240s before concluding failure — a short poll is the #1 false negative. There is **no** `FieldCompletion` object.

---

## Troubleshooting

### No suggestions generated (async)
Check the three requirements above in order: is the template active (`/einstein/prompt-templates`)? Is the field in the flow's `AddOppFieldsToCollection` collection? Does the running user have FLS? Then confirm the grounding flows are active (`SELECT ApiName, IsActive FROM FlowDefinitionView WHERE NamespacePrefix='sales_pipe_mgmt'`) and that the test opportunity is eligible (`IsClosed=false`, `CloseDate` within +90 days) with recent notes/emails/calls. Poll ≥ 240s.

### `/generations` returns empty SuggestedNewValue
The template is fine; the opportunity has no grounding data in the last 30 days. Seed a ContentNote (`--verify-with-note` does this) or use an opportunity with recent activity.

### Field "not found on Opportunity"
The field has no FLS and is invisible to describe. The script detects this and prints the `FieldPermissions` grant; run that command, then re-run.

### Deploy succeeds but template never activates
You likely skipped the version round-trip or hand-authored an identifier. Let the script own activation — deploy Published with no identifiers, retrieve the real `<versionIdentifier>`, set `<activeVersionIdentifier>`, redeploy.

---

## Notes

- Only **text fields** (`type=string`, length ≤ 255) are supported.
- Each field gets exactly **one** template; re-running the script for an existing field is idempotent.
- Suggestions are `AiGenActionItem` records; `DueDate` of `"30 days"` means they expire after 30 days.
- Always use `2>/dev/null` on `sf … --json` piped to jq, and `sf api request rest` (not raw curl) on this org.
