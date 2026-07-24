# Admin Communication Patterns

This reference provides detailed patterns for communicating with admin users during Pipeline Management setup. The goal: make the experience conversational and hide technical complexity unless the user explicitly asks to debug.

The core rules live in the **Admin Communication Guidelines** section of `SKILL.md` (background execution, parse-don't-dump, friendly language, set expectations, investigate errors silently, handle errors gracefully). This file is the detailed companion: the error-translation table, worked examples, and per-step narration templates that apply those rules.

### Silent Error Investigation Example

**Bad (showing the debugging journey):**

```text
Testing NextStep...
The sample generation hit a snag while auto-selecting an opportunity.
Let me check what opportunity data exists...
The org has 8 opportunities but none are eligible.
The --json output is being corrupted...
Found the issue: ANSI color codes break jq parsing...
Let me disable CLI color...
The config set command is being interrupted...
Let me write the config file directly...
```

**Good (silent diagnosis, surface only the solution):**

```text
Testing NextStep...
I need a test opportunity with notes to generate a sample. Let me create one...
The AI suggested: "Schedule follow-up call"
Does this look good?
```

Or if user choice is needed:

```text
Testing NextStep...
⚠ I need a test opportunity with notes to generate a sample. Would you like me to:
1. Create a sample opportunity now (~30 seconds)
2. Skip the test - the prompt is configured and will work in production
```

**What happened behind the scenes (silent):**

- Checked for eligible opportunities → found none
- Discovered ANSI color issue breaking JSON parsing → fixed with NO_COLOR=1
- Decided to either auto-create test data or offer choices
- Only showed the user the conclusion

## Time Expectations

Tell users how long operations take to prevent "is it frozen?" questions:

| Command | Typical Duration |
|---------|-----------------|
| `--check-license` | 10-30 seconds |
| `--through-phase prompts` (Call 1) | 2-4 minutes |
| `--from-phase flow` (Call 2) | 1-2 minutes |
| `add-field-suggestion.sh --verify-with-note` | 1-4 minutes |
| Stage description creation | 30-60 seconds |

## Error Translation Table

### Common Technical Errors → Admin Messages

| Technical Error | What to Say | Recovery |
|----------------|------------|----------|
| `License check failed: SalesDealAgentSettings not found` | "Your org doesn't have the Pipeline Management license. You'll need Agentforce for Sales or Agentforce 1 Sales Edition." | STOP - no action possible |
| `AgentPlatformSettings prerequisite missing` | "I need to enable the Agent Platform first. Let me do that..." | Auto-retry with prerequisite |
| `SOAP API failed: Einstein Generative AI prerequisite missing` | "I need to enable Einstein Generative AI first. Let me do that..." | Auto-retry with prerequisite |
| `Flow deployment failed: OpportunityTeamMember not accessible` | "I need to enable Opportunity Teams before deploying the automation. Let me do that now..." | Auto-retry after fix |
| `Agent bundle published but BotDefinition not found` | "The agent bundle was created but the platform hasn't fully processed it yet. Let me wait a moment and retry..." | Auto-retry after short delay |
| `Agent activation failed: BotVersion still Inactive` | "The agent definition exists but the activation step is still pending. This usually completes in a few moments. Would you like me to retry, or should we activate it manually in Setup?" | Offer retry or manual path |
| `Agent Access PSG assigned but users can't launch agent` | "The permissions are assigned but Agent Access hasn't been defined yet. Would you like me to guide you through enabling it in Setup → Agent Actions?" | Offer manual guidance (W-23242378) |
| `ECONNRESET` / `socket hang up` | "I hit a temporary network issue. Let me retry that step..." | Auto-retry once |
| `AiGenActionItem: No suggestions generated after 4 minutes` | "The test suggestion didn't generate within the expected time. This can happen in busy orgs. The setup is complete, but we couldn't verify the prompt. Would you like me to check again in a few minutes?" | Offer retry verification |
| `Field 'Risk__c' not found` | "I couldn't find a field named 'Risk__c' on the Opportunity object. Could you double-check the field API name?" | Ask for clarification |
| `Max 5 fields allowed, you selected 6` | "Pipeline Management supports up to 5 fields. You selected 6. Which one would you like to remove?" | Ask for user decision |
| `Field type incompatible: Rich Text Area` | "The field '[Field]' isn't compatible - it needs to be a plain Text field (not Rich Text Area) under 255 characters." | Ask which field to use instead |
| `OpptStageDescription missing for stage 'Prospecting'` | "I need stage descriptions before StageName suggestions can work. Would you like me to create them now?" | Offer to create descriptions |
| `OpptStageDescription already exists for stage 'Prospecting'` | "A stage description for 'Prospecting' already exists. Would you like me to update it or skip it?" | Ask for user decision |

## Example: Happy Path Flow

**User:** "Set up Pipeline Management for NextStep and StageName"

**Agent:**
```text
Let me check if your org is licensed for Pipeline Management... (this takes ~30 seconds)
[background: setup-all.sh --check-license]

✓ Your org is ready. A few quick questions:
- Which data sources should inform the agent? (Notes, Emails, Calls)
- Should the agent update fields automatically or suggest for review?
- Would you like to customize the NextStep prompt instructions?

Setting up the platform and creating the agent... (this takes ~3 minutes)
[background: setup-all.sh --fields NextStep,StageName --through-phase prompts]

✓ The platform and agent are ready. Let me show you sample suggestions for each field...

Testing NextStep...
[background: add-field-suggestion.sh --verify-with-note]
The AI suggested: "Schedule follow-up call to discuss pricing"
Reasoning: "Based on the note mentioning unresolved pricing questions"
Does this look good, or would you like me to adjust the instructions?

Testing StageName...
The AI suggested: "Qualification"
Reasoning: "Meeting notes indicate initial interest but needs budget verification"
Does this look good?

Great! Activating the automation... (this takes ~2 minutes)
[background: setup-all.sh --from-phase flow]

✓ Pipeline Management is now active! The agent will analyze your opportunities daily and suggest updates for NextStep and StageName. You can view suggestions in the Pipeline Inspection tab.
```

**What the user NEVER sees:**
- `=== Phase 1.5 ===`
- `curl -X POST https://...`
- `<?xml version="1.0"?><soapenv:Envelope>...`
- `jq -r '.result.records[0].Id'`
- Exit codes, script paths, phase numbers

## Example: Error Recovery Flow

**Scenario:** Missing prerequisite detected

**Agent:**
```text
Setting up the platform... (this takes ~3 minutes)
[background: setup-all.sh --through-phase prompts]
[exits non-zero, parse output finds: "OpportunityTeamMember not accessible"]

⚠ I need to enable Opportunity Teams before deploying the automation. Let me do that now...
[auto-fixes, retries]

✓ Done. Continuing with setup...
[continues normally]
```

**Scenario:** License blocker

**Agent:**
```text
Let me check if your org is licensed...
[background: --check-license]
[exits 1, parse finds: "SalesDealAgentSettings not found"]

⚠ Your org doesn't have the Pipeline Management license. You'll need Agentforce for Sales or Agentforce 1 Sales Edition before we can proceed.

[STOPS - no clarifying questions, no further changes]
```

**Scenario:** Verification timeout

**Agent:**
```text
Testing NextStep...
[background: add-field-suggestion.sh --verify-with-note]
[exits 0 but output says "No suggestions generated after 4 minutes"]

⚠ The test suggestion didn't generate within the expected time. This can happen when the org is busy.

The NextStep prompt is configured and will work in production. Would you like me to:
1. Try the test again (may take another 4 minutes)
2. Proceed to activating the automation - the configuration is complete
3. Skip NextStep for now

[User chooses, continue accordingly]
```

## Example: Partial Failure Handling

**Scenario:** Some fields work, one fails

**Agent:**
```text
Testing your three fields...

✓ NextStep suggestions are working
  Suggested: "Schedule pricing call"

⚠ StageName suggestions couldn't be tested - no stage descriptions found

✓ Risk__c suggestions are working
  Suggested: "Low - strong executive sponsorship"

Two out of three fields are ready. For StageName to work, I need to create opportunity stage descriptions. Would you like me to:
1. Create stage descriptions now (takes ~1 minute) and test StageName
2. Continue without StageName - you can add it later
3. Stop here so you can investigate

[User chooses, handle accordingly]
```

## When to Show Technical Details

**Default mode (no debugging requested):**
- ✅ Show: Friendly progress, checkmarks, what's happening now
- ❌ Hide: Commands, SOAP, curl, jq, phase numbers, exit codes, script paths

**Debug mode (user says "show me the error" / "debug this" / "what went wrong"):**
- ✅ Show: Last 20-30 lines of script output
- ✅ Show: The exact command that failed
- ✅ Show: Suggest next debugging steps
- ✅ Offer: "Would you like me to keep showing technical details, or switch back to simplified messages?"

## Progressive Error Recovery Pattern

```text
Step N starts
  ↓
Exits non-zero
  ↓
Parse error output
  ↓
Is it auto-recoverable? (missing prerequisite, transient network error)
  ├─ YES → Explain what's missing → Fix it → Retry Step N → Continue
  └─ NO  → Is it a known blocker? (license, permission, field not found)
         ├─ YES → Friendly explanation → Offer choices (retry/manual/stop)
         └─ NO  → "I hit an issue: [brief description]. Would you like me to retry or show you the technical details?"
```

## Monitoring Long-Running Background Tasks

After starting a background command:

```javascript
// 1. Immediately tell user what's happening and how long
"Setting up the platform and agent... (this takes ~3 minutes)"

// 2. If user asks "is it done?" while waiting
"Still working on it... platform setup usually takes 2-4 minutes."

// 3. When notified of completion, immediately respond
// DON'T make them wait for your next message
if (exit_code === 0) {
  "✓ [What completed successfully]"
} else {
  parse_and_translate_error()
}
```

## Tune-Loop Conversational Pattern

The interactive prompt verification loop should feel like a conversation, not flag documentation:

**Good:**
```text
Let me generate a sample suggestion for NextStep...
The AI suggested: "Schedule pricing call"
Reasoning: "Note mentions unresolved pricing questions"
Does this look good, or would you like me to adjust how the AI thinks about this field?

User: Make it focus more on executive engagement
Agent: Got it. Let me regenerate with that focus...
```

**Bad:**
```text
Running: bash add-field-suggestion.sh org NextStep --verify-with-note \
  --field-goal "NextStep:Analyze meeting notes..." \
  --field-instruction "NextStep:Extract..."
  
If you want to customize, pass --field-goal and --field-instruction flags.
```

## Complete Step-by-Step Narration

> **Steps are the agent's internal map, not the user's view.** SKILL.md breaks each call into numbered Steps (Call 1 = Steps 1–3, Call 2 = Steps 4–5) so *you* know what the script is doing. The user should see **one friendly progress line per call** (e.g. "Setting up the platform and agent...") plus the tune-loop, NOT a Step 1 / Step 2 / Step 3 breakdown. Narrate a call as a single continuous action; surface the internal Steps only when one fails and you need to explain what specifically broke.

### Step 0: License Check (30 sec)

**Start:**
```text
Let me first check if your org is licensed for Pipeline Management...
```

**Success (exit 0):**
```text
✓ Your org is ready. Now let me ask you a few questions about how you'd like it configured...
```

**Failure (exit 1):**
```text
⚠ I found an issue: [parse error message into friendly blocker]
You'll need [what they need] before we can proceed.
[STOP - ask no questions, make no changes]
```

### Call 1: Setup Platform & Prompts (2-4 min)

**Start:**
```text
Setting up the platform and creating the agent... (this takes ~3 minutes)
```

**Success (exit 0):**
```text
✓ The platform and agent are ready. Now let me show you a sample suggestion for each field...
```

**Failure (exit non-zero):**
- Parse last 30 lines of output
- If missing prerequisite: "I need to enable [X]. Let me do that now..." → auto-retry
- If license/permission: Explain clearly what's needed
- If transient (ECONNRESET): "I hit a network issue. Let me retry..." → auto-retry once
- If unknown: "Setup hit an issue: [brief]. Would you like me to retry or investigate?"

### Tune-Loop: Per-Field Verification (1-4 min each)

**Start:**
```text
Let me generate a sample suggestion for [FieldName]...
```

**Success (exit 0, has "Suggested:"):**
```text
The AI suggested: "[value]"
Reasoning: "[reasoning]"
Does this look good, or would you like me to adjust the instructions?
```

**Timeout (exit 0, "No suggestions generated"):**
```text
⚠ The test suggestion didn't generate in time. This can happen in busy orgs.
The [Field] prompt is configured and will work in production.
Would you like me to: (1) Try again (2) Proceed anyway (3) Skip this field?
```

**Error (exit non-zero):**
- Parse error type
- Field not found: "I couldn't find '[Field]'. Could you verify the API name?"
- Field type error: "The field isn't compatible - it needs to be plain Text under 255 chars."
- 5-field cap: "You've reached the 5-field limit. Which field should I replace?"
- Other: "I hit an issue: [friendly]. Should I skip this field or troubleshoot?"

### Call 2: Activate Flow (1-2 min)

**Start:**
```text
Great! Activating the automation... (this takes ~2 minutes)
```

**Success (exit 0):**
```text
✓ Pipeline Management is now active! The agent will analyze your opportunities daily and suggest updates for [fields]. View suggestions in the Pipeline Inspection tab.
```

**Failure (exit non-zero):**
- Parse error type
- Flow activation: "The automation is built but couldn't activate. [reason]. Let me try to fix it..."
- Agent activation: "Almost complete, but activation failed. Would you like me to retry or guide you through manual activation?"
- PSG assignment: "Everything is set up, but I couldn't assign permissions. You can assign 'Sales Management User' manually in Setup → Users."
- Other: "[Friendly description]. Would you like me to retry or try a different approach?"
