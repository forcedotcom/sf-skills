# Step 3b — edit-fields loop

Reached when the user picks `Edit fields` at step 3b's initial approval prompt. Each round uses the same two-message pattern as the initial 3b: chat-visible table FIRST, `ask_user_tool` SECOND, in the same turn.

## Message 1 — chat-visible plain text (NOT inside `ask_user_tool`)

Reprint the current proposed-fields table so the user sees the field names, types, required flags, AND constraints they are editing. The constraints column is load-bearing — an edit like "make playerName maxLength 257" needs to survive to the next reprint so the user can verify it stuck. Format matches step 3b's initial table and step 7.5's schema summary (see `references/schema-summary-format.md`):

```text
Current fields for `<contentTypeName>`:

| # | API name | Type | Required | Constraints | Title |
|---|---|---|---|---|---|
| 1 | `title` | `lightning__textType` | yes | maxLength: 200 | Title |
| 2 | `body`  | `lightning__richTextType` | yes | — | Body |
| … | … | … | … | … | … |

Type your edits below. Examples:
  - Add: "add field matchResults as rich text"
  - Remove: "drop numberOfTeams"
  - Rename: "rename winner to champion"
  - Change: "make finalVenue required"
  - Constrain: "set playerName maxLength to 257"

Or pick a button below to approve as shown or cancel.
```

STRICTLY DO NOT summarize edits as trailing prose ("`playerName` now has `maxLength: 257`") instead of reflecting them in the Constraints column. Trailing prose disappears on the next reprint; the column survives. The table IS the current state.

## Message 2 — same turn, immediately after the table

Dispatch `ask_user_tool`:
- Question: `Type your edits, or pick an option below.`
- Options: `Approve as shown`, `Cancel`.

## Routing on the tool result — critical, do NOT stop the workflow

The `ask_user_tool` tool result will be one of three shapes. Route deterministically:

| Tool result | What to do |
|---|---|
| Exact string `Approve as shown` (option pick) | Continue to step 4. |
| Exact string `Cancel` (option pick) | Emit `cancelled` outcome per SKILL.md § Invocation contract, print `Cancelled. No files written.`, stop. |
| Anything else (free text — the user typed edit instructions) | **Treat the string as edit instructions.** Parse it (add / drop / rename / require / type-change / localizable) and apply to the field list in memory. **Set `userEditedFields = true` agent-internally** — this flag governs step 6's silent-vs-ask branching (see SKILL.md § step 3a and § step 6). Then jump back to the top of this loop (reprint the updated table + the same `Approve as shown / Cancel` prompt). Do NOT ask the user to clarify unless the instruction is genuinely ambiguous (e.g. "make X better"). |

Free-text tool result is NOT a stop signal, NOT a "non-actionable response," and NOT a request for the agent to acknowledge before continuing. It IS the user's answer to "what edits would you like?" — apply it and loop.

Do NOT skip the table reprint after applying edits — the user must always see the current state before the next prompt.
