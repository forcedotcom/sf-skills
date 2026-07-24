# Field Completion Prompt Template Guide

This guide is about the **two field-specific lines** you supply when adding a new Opportunity field-completion suggestion. The template structure itself is fixed and owned by `assets/field-completion-template.genAiPromptTemplate-meta.xml`; `scripts/add-field-suggestion.sh` fills it in, deploys, activates, and wires the flow. See `references/field-completion-prompts.md` for the full end-to-end mechanics.

You do **not** author the whole prompt or use Prompt Builder. You only decide two things:

- `--goal` — one sentence naming what the model should think about for this field.
- `--instruction` — one line of field-specific extraction guidance.

Everything else in the prompt (data-source block, JSON output rules, character self-check, source-ID extraction rules) is the OOTB Pipeline Management body, reused verbatim. Getting the two lines right is the whole job.

---

## Where the two lines land

Inside the fixed template body, the script substitutes:

```text
You must think about @@FIELD_GOAL@@
...extract information in order to provide the suggested new value for the "@@FIELDLABEL@@" field... @@FIELD_INSTRUCTION@@
```

So `--goal` completes "You must think about …" and `--instruction` is appended after the standard extraction sentence. Write them to read naturally in those slots.

The template already enforces: `SuggestedNewValue` ≤ the field's own length, `Reasoning` ≤ 250 chars, `Snippet` ≤ 100 chars, `DueDate` = `"30 days"`, and a `Sources` array of `{source, snippet}` objects (never a flat string array). Do **not** restate or contradict those caps in your two lines — the field length cap is set automatically from the field's `length`.

---

## Worked examples

Each example shows only the two values you pass to the script; the field must be a text field (`type=string`, length ≤ 255).

### Risk (a `Risk__c` custom field, mirroring the OOTB NextStep/Stage prompt shape)

```bash
--goal "what puts this opportunity at risk of slipping, stalling, or being lost, so the rep can proactively address it"
--instruction "If there is any mention of budget concerns, competition, decision-maker or stakeholder changes, timeline slips, unresolved objections, or loss of engagement, you must strictly include that in your suggested risk, reasoning, and snippets."
```

### Next Strategic Initiative (`Next_Strategic_Initiative__c`, Text 255)

```bash
--goal "the customer's strategic business goal or initiative that this opportunity supports"
--instruction "Focus on business outcomes in the customer's own words (look for \"our goal is\", \"we're trying to\", \"strategic priority\"); if multiple goals appear, pick the one most frequently or most recently emphasized."
```

### Primary Competitor (`Primary_Competitor__c`, Text 255)

```bash
--goal "which competitors the prospect is evaluating and how they compare"
--instruction "Extract explicit competitor names and the specific concern or comparison raised; if several are mentioned, choose the one discussed most or first."
```

---

## Writing good goal/instruction lines

### ✅ Good

- **Specific about what to extract** — names the signals to look for.
- **Grounded** — tells the model to use only what's in the data sources.
- **Customer-centric** — business outcomes, not product features.
- **Handles absence** — the fixed body already returns empty values when no data exists; your instruction should reinforce, not fight, that.

### ❌ Avoid

| Anti-pattern | Example | Why it fails |
|---|---|---|
| Too vague | "Update this field based on the opportunity." | No guidance on what to extract. |
| Assumes data exists | "Populate with the customer's Q3 revenue goal and sponsor's name." | Forces fabrication when the data is absent. |
| Product-centric | "List which features the customer wants." | Ignores the customer's business context. |
| Restating caps wrongly | "SuggestedNewValue must be 500 characters." | The template already caps at the field length; a conflicting number confuses the model. |

---

## Verifying a new field's output

Use `--verify-with-note` (seeds a ContentNote, then calls the synchronous `/generations` endpoint) or call it manually:

```bash
sf api request rest "/services/data/v64.0/einstein/prompt-templates/<TemplateName>/generations" \
  --method POST --target-org "$ORG" \
  --body '{"isPreview":false,"inputParams":{"valueMap":{"Input:Opportunity":{"value":{"id":"<oppId>"}}}},"additionalConfig":{"numGenerations":1,"temperature":0,"applicationName":"PromptTemplateGenerationsInvocable"}}'
```

A correct response looks like this (note the object-form `Sources` and the literal `"30 days"` DueDate — verified live):

```json
{
  "FieldName": "Deal_Momentum__c",
  "SuggestedNewValue": "Low momentum due to budget freeze, no executive sponsor, and competitor evaluation.",
  "OriginalValue": "",
  "Reasoning": "The June 20 call with Sarah Chen flagged a Q3 budget freeze and departure of the sponsor; a note records active evaluation of competitor Onyx.",
  "DueDate": "30 days",
  "Sources": [
    { "source": "069SB000008L2yHYAS", "snippet": "Sarah Chen: budget is frozen until the Q3 review." }
  ]
}
```

The real (async) suggestions land as `AiGenActionItem` records — query by `ParentId` (Opportunity Id) and `Subject` (field API name), `Type = 'FIELD_UPDATE'`. There is no `FieldCompletion` object.

---

## Common issues

| Issue | Cause | Fix |
|---|---|---|
| Field always returns empty | Instruction too strict, or opportunity has no recent notes/emails/calls | Broaden the instruction; seed a note (`--verify-with-note`) or use an active opportunity |
| Model fabricates data | Goal/instruction implies data that isn't there | Reword to "if present"; the fixed body already forbids ungrounded output |
| Output exceeds field length | Field length ≤ your content need | Pick a field with adequate length; the cap is the field's own `length` |
| Template never activates | Version round-trip skipped or identifier hand-authored | Let the script own activation — never guess `<activeVersionIdentifier>` |

---

## Further reading

- `references/field-completion-prompts.md` — full deploy/activate/wire/verify mechanics and the three requirements for a field to produce suggestions.
- `references/data-sources.md` — enabling Einstein Conversation Insights, Activity Capture, and Enhanced Email so `GetOppGroundingData` has content.
- `references/flow-clone-from-template.md` — how `Process_Field_Update_Suggestions` invokes `getOrExecFieldUpdtSuggestion`.
