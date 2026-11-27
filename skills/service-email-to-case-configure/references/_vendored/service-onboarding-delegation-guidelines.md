# Delegation contract — how to behave when an orchestrator delegates to you

This is the shared definition of how a skill behaves when it is driven as a leaf by an
orchestrator (for example Service Onboarding). Follow it verbatim when `delegationFrom` is
set on the call.

## Entry modes

This skill stands on its own for a direct user, **and** can be driven as a leaf by an orchestrator.
It is one skill with two entry modes, decided by a single **runtime** signal, `delegationFrom`. 
Branch on `delegationFrom`: when it is set, you were called this turn by an orchestrator; when it is absent, treat the run as a direct, standalone
conversation and use the skill's normal opening.

When delegated, three runtime values arrive with the call:

| Value | Meaning | Source |
|---|---|---|
| `intent` | Prose of what to build this turn — cites the upstream facts the orchestrator already gathered. | The orchestrator's plan / feature-mapping row. |
| `delegationFrom` | Who's driving — e.g. `"service-onboarding"`. Set **only** when delegated this turn. | Constant the orchestrator passes. |
| `discoveryMode` | How the user is being guided — tunes how you phrase things (see below). | Carried from discovery. |

**When `delegationFrom` is set, adjust as follows (the skill's own write mechanics are unchanged —
delegation changes only the entry, the confirmation cadence, and the wording):**

- **Skip the standalone orientation + menu.** The orchestrator already oriented the user and chose
  this skill; don't re-offer a top-level menu or re-explain what the feature is.
- **Read facts from `intent` first, ask only your own missing fields.** Only ask the user for a value
  the `intent` genuinely leaves open; don't re-ask what's already been answered upstream.
- **Confirmation cadence:** announce every write as you do it, but **don't re-confirm each write** —
  the upstream plan was already approved by the user. **Still explicitly confirm genuinely
  irreversible actions**, and always confirm the **target org** before the first write.
- **Never fabricate values.** Defaults-yes, fabrication-no: if the `intent` doesn't carry a required
  value, ask — don't invent one.
- **Single-hop leaf — return control, don't look ahead.** Do your work and hand control back to the
  orchestrator. Don't ask "what would you like to do next?", and don't re-delegate onward.
- **Respect headless limits.** If part of the work needs a browser the current surface can't provide,
  do what the API allows, report what remains, and hand back — never fabricate the result.

## Language by `discoveryMode`

- **`"guided"` → plain business-user language.** Lead with the outcome, not Salesforce object/field/page names.
- **Any other mode (or a direct user) → normal Salesforce terms**, as elsewhere in this skill.
- Same writes either way — only the wording changes.
