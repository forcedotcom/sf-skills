# Canonical Agent Path — Two Calls with Interactive Tune-Loop

Because an agent-driven run is **always non-interactive** (a piped stdin forces `--non-interactive`), the script cannot pause to let the user shape and approve each field's prompt. So split the run and own the interactive tuning yourself, between the two calls:

```bash
cd skills/sales-agentforce-pipeline-management-configure/scripts

# CALL 1 — enablement through prompt templates, then STOP before the flow.
# This call still runs ALL prerequisites: Einstein Generative AI, Agentforce Agent, Enhanced
# Notes, Opportunity Team, Pipeline Inspection, Pipeline Management enablement, agent-user/PSG
# provisioning, BotDefinition publish/activate, Agent Access — nothing is skipped.
bash setup-all.sh <org-alias> --fields "NextStep,Risk__c" \
  --field-goal "NextStep:<text>" --field-instruction "NextStep:<text>" \
  --through-phase prompts

# TUNE-LOOP (you drive this, per non-StageName field). Generate a note tailored to the
# field's instruction, seed it, run a synchronous generation, show the result, and LOOP
# UNTIL THE USER APPROVES:
bash add-field-suggestion.sh <org-alias> <Field> --skip-flow --force \
  --goal "<goal>" --instruction "<instruction>" \
  --verify-with-note --note "<sample note written to exercise THIS field's instruction>"
#   → shows "Suggested: …" + "Reasoning: …". Relay both to the user.
#   → user approves → next field. User wants a change → re-run with adjusted --goal/--instruction/--note.
#   → NO output (blocked): show why, then ask the user immediately — retry / proceed-unverified / skip.
#     "proceed" wires the field live but flag it as UNVERIFIED.

# ALSO show the DEFAULT suggestion for every SELECTED field the user left UNCUSTOMIZED
# (StageName always; NextStep when no goal/instruction was given), so they can decide to
# keep or change the default even though they didn't tune it:
bash scripts/verify-prompt-generation.sh <org-alias> <Field> <oppId>
#   → relay "Suggested / Reasoning". Keep → done. Change NextStep → tune it via add-field-suggestion.sh
#     (above). Change StageName → adjust its stage descriptions (--create-stage-descriptions).

# CALL 2 — build & activate the flow (approved fields only), activate agent, recalc PSG, verify.
bash setup-all.sh <org-alias> --fields "NextStep,Risk__c" --from-phase flow
```

## Rules for the Agent Driving This

- **The tune-loop IS Call-1 prompt verification.** Seeding a note and running `add-field-suggestion.sh --verify-with-note` (showing "Suggested / Reasoning") is how each field's prompt is verified. There is no separate "run prompt verification" step to trigger afterward — if you completed the tune-loop, verification happened.
- **Show a default suggestion for every SELECTED field, even uncustomized ones.** `StageName` and an uncustomized `NextStep` still generate a default suggestion — surface it (via `verify-prompt-generation.sh <org> <field> <oppId>`) so the user can decide whether to keep or change the default they never explicitly tuned. `StageName` can't be tuned via `add-field-suggestion.sh` (managed picklist template, no override), but its suggestion is shaped by its **stage descriptions** — change those (`--create-stage-descriptions` / edit `OpptStageDescription`) to change it. Never pull in fields the user didn't select.
- **`StageName` needs stage descriptions to generate.** Its grounding is created in **Call 1** (Phase 4c.5, only when `StageName` is selected) *before* the StageName prompt is tested — so a StageName default can be shown during Call 1's tune-loop.
- **Call 2 (`--from-phase flow`) is MANDATORY.** Call 1 stops *before* the flow is built, so a run that ends after Call 1 has **no** `Process_Field_Update_Suggestions` flow and generates **zero** scheduled suggestions. The setup is incomplete until Call 2 builds and activates the flow. Always run both calls.
- **Collect goal/instruction up front** (clarifying Q5) for every non-`StageName` field the user wants customized. Do **not** silently keep the OOTB/default prompt without asking — the script cannot ask for you.
- **Loop until the user approves** each field's suggestion. Do not treat the first generation as final.
- Pass the SAME `--fields` set to both calls. StageName (if selected) needs no per-field tune *iteration* (managed picklist template), but DO still show its default suggestion for the user to accept or adjust.
- To re-inspect any field's prompt outside the loop, run `bash scripts/verify-prompt-generation.sh <org> <field>` (pass the **field** name — e.g. `NextStep`, `Risk__c` — not a raw template name; it resolves the managed/derived template for you).
- Prefer this two-call path over a single unattended run whenever a human is available to review prompts.

## How to Narrate to the User

Run all commands in background. Narrate in plain language. Check exit codes and translate errors to admin-friendly messages. See `references/admin-communication.md` for detailed patterns.

**Step 0 — License check** (30 sec): "Checking if your org is licensed..." → pass "Ready" or warn "[blocker]"

**Call 1 — Setup platform & prompts** (2-4 min): "Setting up the platform and agent..." → pass "Ready. Let me show you sample suggestions..." or warn "[auto-retry or explain]"

**Tune-loop** (1-4 min per field): "Generating sample for [Field]..." → Show suggestion + "Does this look good?" → Iterate if needed or handle timeout/error with choices

**Call 2 — Activate** (1-2 min): "Activating the automation..." → pass "Pipeline Management is live!" or warn "[explain + offer retry/manual]"

## Internal Step Map (Reference Only)

The narration lines above are the user-facing view. The internal step map below is *your* reference for what each call does — surface it only when a step fails and you need to explain what broke.

**Call 1 — Enablement through prompt templates** *(stops before the flow)* — `--through-phase prompts`

- **Step 1 — Enabling prerequisites & the data source**: SOAP API prerequisites, platform prerequisites (Einstein Generative AI, Agentforce Agent, Enhanced Notes, Opportunity Team, Pipeline Inspection), Pipeline Management enablement, and the autonomous-mode setting.
- **Step 2 — Provisioning the agent**: agent user + PSG assignment, agent architecture verification, and Agent Access.
- **Step 3 — Setting up & verifying the field prompt**: create stage descriptions first if `StageName` is selected (its grounding), deploy/activate the selected fields' prompt templates, then the interactive tune-loop — seed a note, generate, relay "Suggested / Reasoning" to the user (including the default for uncustomized `StageName`/`NextStep`), and loop until they approve each field.

**Call 2 — Building & activating the flow** *(goes live)* — `--from-phase flow`

- **Step 4 — Building & activating the flow**: build the schedule-triggered flow with the approved fields only, then activate it.
- **Step 5 — Finishing & verifying**: user permissions and final verification.
