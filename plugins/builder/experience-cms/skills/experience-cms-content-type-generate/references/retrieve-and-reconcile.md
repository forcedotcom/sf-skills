# Step 1e — retrieve and reconcile

Reached when the user picks a match OR provides an FQN in step 1d, OR when the caller invoked the skill with `{ fqn }` (per the invocation contract). The goal is to return `{fqn, schema}` to the caller with the schema known to match what's in the org. Retrieve is cheap — always run it for custom types so the caller never gets a schema that has silently drifted from the org.

## Namespace gate

- **Custom FQN** (`c__*`, or any non-platform namespace) → **ALWAYS run retrieve.** Namespace is the ONLY gate. Discovery, workspace confirmation, or "the org already has it" do NOT substitute for retrieve, and there is **no** "OOTB-equivalent" custom category — a `c__*` type is never treated like OOTB. Skipping retrieve for a custom type drops drift detection and is a regression.
- **OOTB / platform FQN** (`sfdc_cms__*`) → **skip retrieval entirely**: no `sf project retrieve start`, no `query_metadata`, no `describe_metadata`. `sf project retrieve` returns nothing usable for OOTB ContentTypeBundles, and the `sfdc_cms__*` schema is platform-owned and immutable — a caller cannot change it, and no downstream step needs it (content authoring is server-side; the delegated caller ignores `schema`). This skip is gated on the `sfdc_cms__*` namespace ALONE — NEVER because the FQN "was confirmed by discovery" (discovery confirms custom FQNs too; that is not a reason to skip). Return success on the FQN alone, independent of `metadata-grounding` availability:

  ```text
  { status: "success", fqn: "<fqn>", schema: null }
  ```

  This is the pre-existing behavior for OOTB picks — never retrieved, never grounding-dependent. Do NOT fail on a grounding outage, and do NOT dispatch a schema fetch just to populate the 7.5 summary (7.5 auto-skips when `schema` is null).

  **STRICTLY DO NOT fabricate a schema for the OOTB FQN from training data or prior conversations.** You may "know" that `sfdc_cms__news` typically has `title / body / summary / bannerImage / publishedDate`. That knowledge is UNRELIABLE for this org (fields vary by release, by org customizations, by API version) and emitting it as a real schema silently poisons downstream steps. Return `schema: null` — never a remembered schema.

## Retrieve (custom only, silent)

Parse `<namespace>__<DeveloperName>` — the CLI wants only the `DeveloperName` part.

**Snapshot `schema.json` only. Do NOT snapshot or restore meta.xml.** The retrieve returns each of the two bundle files with its own correct content (`schema.json` gets JSON, `<Name>.contentTypeBundle-meta.xml` gets the minimal XML wrapper). meta.xml is small and mechanically derivable from the folder name — there is nothing user-authored in it worth preserving across a retrieve.

**Ordered steps (all agent-internal, no chat output):**

1. **Snapshot local schema.** If `<sfdx-source>/contentTypes/<DeveloperName>/schema.json` exists, read its FULL contents into memory as `localSchemaBefore` (string, byte-exact). If the folder or file doesn't exist, `localSchemaBefore = null`. Do NOT read meta.xml into memory — its content plays no role in reconciliation.
2. **Run retrieve:**

   ```bash
   sf project retrieve start \
     --metadata ContentTypeBundle:<DeveloperName> \
     --target-org <orgAlias> \
     --json
   ```

   Runs against the SF CLI default org — different auth path from `metadata-grounding`, so it works even under grounding outage.

   **Foreign-file retry (macOS):** if retrieve fails with an error mentioning a foreign file inside the bundle folder — most commonly `.DS_Store` (Finder metadata file), also `Thumbs.db` (Windows) or editor swap files — silently `rm -f <sfdx-source>/contentTypes/<DeveloperName>/.DS_Store` (or the offending file) and retry the retrieve ONCE. Do NOT ask the user; the file is OS clutter, not their work. If the retry still fails, surface the raw CLI error.
3. **Determine `retrievedFromOrg`.** Parse the retrieve JSON's top-level `result`:
   - `result.success === true` AND `result.files[]` includes an entry for `ContentTypeBundle` `<DeveloperName>` → **retrieved**. Read the post-retrieve `schema.json` into `retrievedSchema`.
   - `result.success === true` with no `ContentTypeBundle` entry, OR an explicit `"cannot be found"` error in `messages[]` / `warnings[]` → **not retrieved** (org doesn't have this type).
   - Any other failure → surface the raw CLI error and exit with `error` outcome.
4. **Detect drift (only when both local and org copies exist).** **Compare `schema.json` ONLY.** Drift is present when `localSchemaBefore !== retrievedSchema` as parsed JSON trees (key order and whitespace don't count). Byte-inequality with structural equivalence = no drift.

   STRICTLY DO NOT read the post-retrieve `schema.json` and diff it against itself — that's the "no drift" bug. `localSchemaBefore` (the pre-retrieve in-memory snapshot) is the only correct left-hand side.

## Reconciliation table

Comparing `localSchemaBefore` (snapshot from step 1) against `retrievedSchema` (post-retrieve from step 2). meta.xml handling is trivial — whatever `sf project retrieve` wrote is correct; there is no snapshot to restore.

| Local `schema.json`? (before retrieve) | Retrieved from org? | Action |
|---|---|---|
| No (`localSchemaBefore === null`) | Yes | Retrieve wrote both files (`schema.json` + `<Name>.contentTypeBundle-meta.xml`) — accept as-is. Return `{fqn, schema=retrievedSchema}`. |
| Yes | Yes, and `localSchemaBefore` semantically equals `retrievedSchema` (JSON tree compare) | No drift. The retrieve rewrote meta.xml to the org's copy of the minimal XML wrapper; that's fine, leave it. Return `{fqn, schema=localSchemaBefore}`. |
| Yes | Yes, and `localSchemaBefore` differs from `retrievedSchema` in the parsed JSON tree | **Drift detected on `schema.json`.** Retrieve has already overwritten local `schema.json` — you MUST hold `localSchemaBefore` in memory through the drift prompt so `Deploy local` and `Cancel` can restore it. Go to "Drift prompt" below. |
| Yes | No (retrieve confirmed empty for this type) | Retrieve didn't touch the folder, so local is intact. **Retrieve is what confirmed org absence** — grounding's earlier response is NOT sufficient to conclude this; only a clean `sf project retrieve start` return justifies the "not in org" claim. **First print the step 7.5 schema summary of the LOCAL schema** (see `references/schema-summary-format.md`) so the user sees what they're about to deploy — a local-only bundle is the most likely case to be stale or hand-edited. Then offer to deploy: `The bundle "<Name>" exists locally but not in the org (confirmed via retrieve). Deploy it? Yes / Cancel`. On yes → skip to step 5 (dry-run) → step 7 (deploy). On cancel → emit `not_deployed` outcome per the return contract in SKILL.md § Invocation contract: `{ status: "not_deployed", fqn, schema: null, message: 'Content type "<fqn>" exists locally but is not deployed to <org>. Deploy it before creating content.' }`. Print the message and stop — do NOT run step 7.5 or step 8. |
| No | No | FQN doesn't resolve anywhere. Print `FQN "<fqn>" not found locally or in the org.` and re-dispatch the step 1d pick with an added `Try a different FQN` option, or `Cancel`. |

## Drift prompt (local ≠ org)

**Precondition state at this point:** disk currently holds the org copy of `schema.json` (retrieve overwrote it). `localSchemaBefore` holds the pre-retrieve local `schema.json` bytes in memory. meta.xml is whatever retrieve wrote — it's not tracked and doesn't need to be. The three routing branches below rely on the `localSchemaBefore` snapshot.

**Two outputs in this order, same as step 1d — chat message first, then short tool call.** The diff details go in the chat message. The tool call is ONE short question and 3 options. Do NOT pack the field list into `ask_user_tool`'s `question` field — it collapses into an unreadable paragraph.

**Output 1 — chat message (plain markdown, NOT the tool call):**

```text
Schema drift detected in "<fqn>". Differences (org vs local):

| Change | Field | Local | Org |
|---|---|---|---|
| renamed | `summary1` → `summary` | title "Summary1" | title "Summary" |
| required-list | — | ["headline", "summary1"] | ["headline", "summary"] |
```

Use whatever concise diff shape fits the actual delta — added/removed rows, renamed rows, required-list changes, type changes. Keep it factual, no editorializing. If the diff is small (1–2 changes), a bulleted list is fine:

```text
Schema drift detected in "<fqn>". Differences (org vs local):

  • renamed: `summary1` (local) → `summary` (org)
  • required list changed: local has "summary1", org has "summary"
```

**Output 2 — `ask_user_tool` (short question, 3 options):**

- **question**: `Changes detected between local and org. What would you like to do?`
- **options** (fixed order):
  1. `Deploy local to org`
  2. `Overwrite local with org`
  3. `Cancel`

Routing:

- `Deploy local to org` → **restore the schema snapshot first**: write `localSchemaBefore` back to `<sfdx-source>/contentTypes/<DeveloperName>/schema.json`. Leave meta.xml alone (retrieve wrote the correct minimal XML). Then route to step 5 (dry-run) → step 7 (deploy). On deploy success, emit `success` outcome with `{fqn, schema=localSchemaBefore}`.
- `Overwrite local with org` → nothing to do on disk (retrieve already wrote both files correctly). Emit `success` outcome with `{fqn, schema=retrievedSchema}`.
- `Cancel` → **restore the schema snapshot**: write `localSchemaBefore` back to `<sfdx-source>/contentTypes/<DeveloperName>/schema.json`, restoring the pre-retrieve `schema.json`. Leave meta.xml alone. Then emit `cancelled` outcome per SKILL.md § Invocation contract: `{ status: "cancelled", fqn: null, schema: null, message: "Cancelled. No files written." }`. Print the message and stop. Do NOT tell the user "no files written" without actually restoring `schema.json` — that message is a promise about the disk state of the schema.

## Terminal state

On any successful terminal state, return `{fqn, schema}` to the caller and continue to step 7.5 (schema summary), then step 8 (trailing prompt gate). No proposal-of-fields, no re-validation of existing types, no "approve as-is" prompt — the reconciled schema IS the source of truth. This skill is create-only and reconcile-only for existing types; do not modify field shapes.
