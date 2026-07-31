# Phase 2.5: Custom Objects

**Required if the prompt requires a new custom Salesforce object the org doesn't have.**

```text
Identify Salesforce objects/fields the prompt requires that are NOT standard objects
    v
Load platform-custom-object-generate (once, with every new object needed)
    v
Generate object + field metadata
    v
Deploy the metadata (per platform-custom-object-generate's own deploy step)
```

This UI bundle orchestrator does **not** author custom object metadata itself — that is
out of scope for every `experience-ui-bundle-*` skill. When the prompt requires new schema (e.g.
"create a `Case__c` object with `Subject__c`"), delegate entirely to `platform-custom-object-generate`
before Phase 3. Do not invent custom object XML inline and do not defer this to Phase 3 — Phase 3's
grounding step assumes the object already exists in the org.

**Trigger conditions**: The prompt requires a custom object (`__c` suffix, or a business noun with no
standard-object equivalent) together with fields to create on it. Skip this phase if the prompt only
references standard objects (Account, Contact, Case, etc.) or objects the org already has.

**Only after this phase's deploy succeeds** does Phase 3 (Data Access) ground queries against it.

## Per-Phase Execution Guide Entry

**Phase 2.5 -- Custom Objects** (skip if the prompt only uses objects the org already has)
- 1. Load skill: Invoke `platform-custom-object-generate`
- 2. Execute: Generate the object + field metadata for every new object required by the prompt, then deploy it (per that skill's own workflow) -- do not defer the deploy to Phase 6
- 3. Verify: Confirm the object(s) and field(s) deployed successfully before Phase 3 attempts to ground against them
- 4. Checkpoint: Custom schema exists in the org -- proceed to Phase 3
- **Trigger conditions**: Prompt requires a non-standard object (typically ending `__c`) together with fields to create on it
