# Step 1d — discovery prompt template

Show top 5 matches in a table, then ask the user to pick. That's it.

## Build the combined list

1. Collect local matches from step 1b (folders under `<sfdx-source>/contentTypes/`) — always unfiltered, never subject to the workspace-content-types check below.
2. Collect org-side rows per step 1c's Flow 1/Flow 2 routing:
   - **Flow 1 (grounding ran):** the **intersection** of `search_metadata`'s rows and `get_content_types_for_workspace`'s FQNs — a row must appear in both to be an org candidate. If `get_content_types_for_workspace` itself was unavailable, fall back to every `search_metadata` row unfiltered (grounding already ranked them).
   - **Flow 2 (grounding unavailable):** every `get_content_types_for_workspace` row that semantically matches `intent` (same domain-reasoning as step 1b), applied directly since there's no grounding rank to intersect against.
   - Empty org-side set is valid in either flow — do not widen or retry to avoid it.
3. Dedupe: same bundle in both local and org-side = one row, `Location = local, org`.
4. Sort: OOTB first, then org-custom, then local-only. Within a group, keep grounding's ranking.
5. Cap at 5 (`combined = combined.slice(0, 5)`). Rest discarded — users reach them via `Provide an FQN`.

**Row count formula: `min(combined.length, 5)`. Always.** If grounding returned 6 rows and the top row is a perfect match, `combined.length` is still 5, table has 5 rows. Rows 2–5 are what the user compares the top match against — never drop them because "the top one is obviously it."

## Has matches (`combined.length ≥ 1`)

**Output 1 — chat message (plain markdown, no preamble sentence above it):**

```text
Top <N> matching content types:

| FQN | Description | Location |
|---|---|---|
| c__PressRelease | Corporate announcements with headline, body, quote. | local, org |
| c__NewsArticle | News item with byline, body, category, publish date. | org |
| c__BlogPost | Blog post with author, body, tags, publish date. | org |
```

- Header: `Top <N> matching content types:` (or `Top 1 matching content type:` when N=1).
- Columns: `FQN | Description | Location`, in that order. No other columns.
- FQN column: always namespaced (`c__X`, `sfdc_cms__x`).
- Description: ≤80 chars, truncate with `…`.
- Location: `local`, `org`, `local, org`, `org (OOTB)`, or `local, org (OOTB)`.
- Row count: `combined.length` — every row goes in.

**Output 2 — `ask_user_tool`:**

- **question**: `Found matches. Pick one:`
- **options** (fixed order):
  1. `Use existing: <row-1 FQN>`
  2. `Provide an FQN`
  3. `Create new: <newName>`
  4. `Cancel`

**`<newName>` — avoid clashing with any FQN in the table.** Default: `contentTypeName`. But if `c__<contentTypeName>` (or any namespace variant) is a row in the table, `Create new: <contentTypeName>` would be indistinguishable from `Use existing: <same FQN>` — pick a related-but-distinct name instead:

- synonym: `PressRelease` → `PressAnnouncement`
- noun swap: `PressRelease` → `ReleasePress`
- suffix: `PressRelease` → `PressReleaseV2`, `PressReleaseRecord`
- domain hint from the user's intent: `NewsArticle` → `Editorial`, `Bulletin`

Pick whichever feels most natural for the domain. Never emit `Create new: <Name>` when the same name already appears in the table.

## Zero matches (`combined.length === 0`)

- **question**: `No matches found. Create a new one?`
- **options**: `Create new: <contentTypeName>` / `Cancel`

Add `Provide an FQN` as option 1 when the caller delegated (`suppressCreateContentPrompt === true` or supplied `fqn`).

Precede the tool call with a one-line chat message:

- Grounding ran cleanly (Flow 1, regardless of `get_content_types_for_workspace` outcome): `No matches found for "<contentTypeName>" in your project or the connected org.`
- Grounding unavailable, workspace check ran (Flow 2): `No matches found for "<contentTypeName>" in your project (checked supported content types for this workspace — metadata-grounding unavailable).`
- Both unavailable: `No matches found for "<contentTypeName>" in your project (org check skipped — grounding unavailable).`

**Direct-invocation shortcut (optional):** direct user invocation + zero matches → skip the tool call, print `No matches found for "<contentTypeName>". Creating a new one.` and auto-proceed to step 2.

## Routing

- `Use existing: <fqn>` → step 1e with that FQN.
- `Provide an FQN` → dispatch `ask_user_tool` with question `Type the FQN in namespace__DeveloperName format (e.g. c__BlogPost, sfdc_cms__article)`, free-text or `Cancel`. On reply → step 1e.
  - **No literal angle brackets in `ask_user_tool` question or option text.** The tool renders through an HTML-escaping layer, so `<foo>` shows up as `&lt;foo&gt;` in chat. Placeholders like `<contentTypeName>` in these templates are variables — substitute the real value BEFORE dispatching. If you actually want a format-marker literal, use plain words (`namespace__DeveloperName`) without brackets.
  - **Invalid-FQN re-ask.** If the user's reply doesn't match `^[A-Za-z][A-Za-z0-9]*__[A-Za-z][A-Za-z0-9]*$` (e.g. `abc`, `foo bar`, `c_BlogPost` with one underscore), re-dispatch `ask_user_tool` with question `"<what the user typed>" isn't a valid FQN — expected namespace__DeveloperName (e.g. c__BlogPost). Try again, or cancel.` and the same free-text / `Cancel` options. Same no-angle-bracket rule applies. Loop until the reply matches or the user cancels.
- `Create new: <Name>` → step 2.
- `Cancel` → exit.
