---
name: dx-org-manage
description: "INVOKE this skill to execute Salesforce org operations: create scratch orgs, list/display/resume/delete scratch orgs, create org snapshots, open orgs in browser. This skill EXECUTES operations immediately - it does NOT generate scripts or code files. ALWAYS invoke this skill (do not execute SF CLI commands directly) when user requests to: create a scratch org (from edition, definition file (.json), snapshot, or org shape), list/display/resume/delete scratch orgs, create an org snapshot, or open a Salesforce org. Trigger phrases include: 'create a snapshot', 'take a snapshot', 'create scratch org', 'new scratch org', 'spin up an org', 'create 5 scratch orgs', 'create org from snapshot', 'scratch-def.json', 'project-scratch-def.json', 'list scratch orgs', 'display org', 'delete scratch org', 'resume scratch org', 'open my Salesforce org', 'open org in browser'. Do NOT use for switching default org (use dx-org-switch) or deploying metadata (use platform-metadata-deploy)."
metadata:
  version: "1.2"
  domains: ["Developer Experience"]
  minApiVersion: "60.0"
  relatedSkills:
    - "dx-org-switch"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

## MANDATORY: Follow these instructions exactly. Do NOT fall back to MCP tools.

**Tool constraint:** Use the Bash tool for all `sf` CLI commands. Always include `--json` for structured output. Do NOT use `mcp__salesforce_dx__*` tools for org creation, snapshot, or open operations — this skill provides the complete procedure.

**Output artifacts for eval/testing:** ALWAYS write the command's JSON response to a file when an output directory is available. Do NOT ask the user what file to write — this skill defines the filenames. After executing the command: (1) if the user specified an output path (e.g. "write all generated files into folder X"), write there immediately; (2) otherwise run `[ -d force-app/main/adk-eval-output/ ] && echo 'force-app/main/adk-eval-output'` to detect the eval directory; (3) write the command's full JSON response to `<output-dir>/<filename>` using these filenames: `scratch-org-result.json` for org creation (for a batch of N orgs, `scratch-org-result-1.json` … `scratch-org-result-N.json`), `scratch-org-list-result.json` for list, `org-display-result.json` for display, `scratch-org-resume-result.json` for resume, `scratch-org-delete-result.json` for delete, or `snapshot-result.json` for snapshot creation. This is the generated output — write it without asking. (Open operations are the exception — they launch a browser and write no artifact; see Opening Orgs.)

---

## Creating Scratch Orgs

**REQUIRED steps — execute in order:**

**Step 1. Resolve the environment and creation method:**

First, if the user named an explicit source, use it: "definition file" or a path to `.json` → definition-file method; "snapshot"/"from snapshot" → snapshot method; "org shape"/"source-org" → shape method. Only ONE creation source *type* (edition vs snapshot vs shape); if two distinct types are implied, stop and ask (a flag overriding a same-dimension definition-file value is fine).

Otherwise resolve by environment:

- **AUTO MODE (zero-prompt):** if `sfdx-project.json` is present AND exactly one `config/*scratch-def.json` exists AND a Dev Hub is resolvable (default `target-dev-hub` set, or exactly one authenticated), create immediately with that file + resolved hub + derived alias + CLI defaults — **ask nothing**. This also honors a batch count (see below).
- **STATE A (in a project), not auto:** enumerate `config/*scratch-def.json` — 0 files → default `--edition developer` (or author one if features/settings are wanted, see below); 1 file → use it; many → **ask which one** (never silently pick).
- **STATE B (no `sfdx-project.json`):** do NOT block and do NOT silently create a throwaway — present the guided 3-way choice (point to a project / scaffold one via `sf template generate project --name <name>` / create a throwaway here, then guide the source). See `references/scratch-org-create.md`.

**Batch — "create N scratch orgs":** there is no native count flag — loop the create command N times with N distinct aliases (`<base>-1` … `<base>-N`, each collision-guarded so it never re-points an existing org). Report each org and write one artifact per org. On a mid-loop Dev Hub limit error, surface the CLI's error unchanged and report which orgs already succeeded.

**Definition-file authoring:** if features/settings are requested and no suitable file exists, author a new purpose-named definition file (seed-then-modify; documented fields only; no-clobber), show it, and create from it. **In a non-interactive/eval context, author the file AND proceed to create without waiting** for edit confirmation. Details in `references/scratch-org-create.md` and `references/definition_file_options.md`.

**Step 2. Resolve the Dev Hub to a concrete value — then pass it explicitly.** Resolve it **once** to an actual username or alias and pass that exact value via `--target-dev-hub` on every command in Step 3. Resolution order:

1. **A Dev Hub the user named explicitly** → use it verbatim.
2. **Else the default:** the non-empty `result[0].value` from `sf config get target-dev-hub --json`.
   ```bash
   sf config get target-dev-hub --json
   ```
3. **Else the single authenticated Dev Hub.** Run **this exact command** — do NOT hand-write your own filter. A Dev Hub can appear in **any** of the `sf org list` buckets (`devHubs`, `nonScratchOrgs`, `other`, `sandboxes`, `scratchOrgs`); a filter that checks only one bucket (e.g. only `.other[]`) misses it and makes you think no hub exists:
   ```bash
   sf org list --json | jq -r '[.result.devHubs[]?, .result.nonScratchOrgs[]?, .result.other[]?, .result.sandboxes[]?, .result.scratchOrgs[]?] | map(select(.isDevHub == true).username) | unique | .[]'
   ```
   - **Exactly one** username printed → use it.
   - **Zero** printed → no hub is authenticated. **Do NOT run `sf org create` at all** — there is nothing to pass to `--target-dev-hub`, and any create attempt will fail. Instead, STOP here: advise `sf org login web --set-default-dev-hub`, and if an output directory is available write that advisory as the artifact. Do not proceed to Step 3.
   - **Two or more** → ask the user which one (do not pick arbitrarily).

- **Never invent or guess a Dev Hub name.** Fabricating a placeholder alias (e.g. `eval-target`, `my-dev-hub`, `DevHub`) is the top eval failure — the CLI correctly rejects it with `NotADevHubError`. If the command above prints nothing, that means **no Dev Hub exists in this environment** — it does NOT mean you should substitute a name. There is no valid fallback name to invent: an unresolved hub is a hard stop, not a value to guess. Do NOT run `sf org create scratch` with a made-up `--target-dev-hub`, and do NOT run it with no `--target-dev-hub` flag either (that yields `NoDefaultDevHubError`). Stop and advise `sf org login web --set-default-dev-hub`.
- The default `target-dev-hub` may be **directory-scoped** in some CLI setups (`sf config get` can return empty after a `cd`), which is why step 3's all-bucket `sf org list` check is the reliable fallback — it is not directory-scoped.
- Do NOT proceed until a concrete Dev Hub value is resolved.

**Step 3. Build and execute the command** based on method:

**Definition file:**
```bash
sf org create scratch --definition-file <path> --target-dev-hub <alias> --alias <name> --json
```

**Edition only:**
```bash
sf org create scratch --edition developer --target-dev-hub <alias> --alias <name> --json
```

**From snapshot:**
```bash
sf org create scratch --snapshot <snapshot-name> --target-dev-hub <alias> --alias <name> --json
```

**From org shape:**
```bash
sf org create scratch --source-org <source-org-id> --target-dev-hub <alias> --alias <name> --json
```
`--source-org` takes the 15-character **source org ID** — the ID of the org the shape was captured from (a `00D…` org ID), NOT the `3SR…` shape record ID shown by `sf org list shape`. Pass the ID the user gives you through unchanged. If the CLI rejects it (e.g. `InvalidIdLengthError`, `InvalidPrefixError`), surface that error verbatim and stop — do NOT truncate, reformat, guess, or retry with a different ID.

**Apply these flags when requested:**
- `--duration-days <days>` — default 7, max 30
- `--set-default` — make this the default org
- `--no-track-source` — disable source tracking (for CI/CD)

**Step 4. MANDATORY - Run org list and write output (SUCCESS path only):** This step runs only when Step 3 created an org successfully. If Step 3 returned an error, SKIP this step and follow **Error handling** below instead. After the org is created, you MUST run this command:

```bash
sf org list --json
```

Then:
1. Parse the JSON result and find the `scratchOrgs` array
2. Find the entry where `username` matches the username from Step 3's creation result
3. Extract that complete org object (it will include: alias, username, orgId, instanceUrl, loginUrl, isDefaultUsername, orgEdition, status, expirationDate, devHubUsername, and other fields the CLI returns).
4. Report to the user:
    - Created scratch org.
    - Alias: [alias from the org list entry]
    - Username: [username]
    - Org ID: [orgId]

5. If an output directory is available (per the output artifacts rule above), write that extracted org object to `<output-dir>/scratch-org-result.json` **as-is — this skill is a pass-through wrapper**. Write every field the CLI returns for that org; do NOT curate, whitelist, or drop non-secret fields (e.g. `instanceName`, `createdOrgInstance`, `signupUsername`, `orgName`, `edition` are non-secret metadata the CLI returns freely — keep them). The one thing you never emit is a live secret: `accessToken` and `sfdxAuthUrl` — and the CLI already redacts these in `--json` output (they arrive as `"[REDACTED] …"`), so simply preserve that redaction and never un-redact or re-derive the real value.

Example: If `sf org list --json` returns `{"result": {"scratchOrgs": [{"alias": "feature-dev", "username": "test@example.com", "orgId": "00D...", ...}]}}`, write the inner org object `{"alias": "feature-dev", "username": "test@example.com", "orgId": "00D...", ...}` — the full object for that org — to the file.

Write the extracted org-list entry (the resolved org record), NOT the raw creation-command response. Do NOT suggest verification steps to the user.

**Error handling (Step 3 create failed — no org was created):** Surface the CLI's error output to the user **verbatim** (no rewriting, no retry, no editing the definition file). Do NOT run Step 4 (there is no org to list/extract). If an output directory is available, write the create command's **raw error JSON as-is** to `<output-dir>/scratch-org-result.json` — this is the command's response and is the output artifact for the failed run. (For a batch, write the error to the artifact for the org that failed, and still write the success entries for any orgs that already succeeded before the failure.) Then, where the CLI's error matches one of these, add the corresponding pointer:
- "Snapshot not found" → suggest `sf org list snapshot --target-dev-hub <alias>`
- "No default Dev Hub" → advise `sf org login web --set-default-dev-hub`

**When you need more detail:**
- For the complete creation workflow (AUTO MODE, STATE A/B, batch, definition-file authoring) → load `references/scratch-org-create.md`; for list/display/resume/delete → load `references/scratch-org-operations.md`
- For available features, settings, and definition file structure → load `references/definition_file_options.md`
- For edition selection guidance and comparison → load `references/edition_types.md`
- For snapshot workflow and post-creation usage → load `references/snapshot_usage.md`

---

## Listing Scratch Orgs

**Step 1. Execute:**
```bash
sf org list --json
```
**Step 2. Report + write output:** default view = active scratch orgs from `result.scratchOrgs[]`; report alias / username / orgId / expiration per org. Document `--all` (include expired/deleted) and `--clean` as options, not the default. Write the `result.scratchOrgs[]` **array** to `<output-dir>/scratch-org-list-result.json` (per the output-artifacts rule).

**Detail:** `references/scratch-org-operations.md`.

---

## Displaying an Org

**Step 1. Execute:**
```bash
sf org display --target-org <alias> --json
```
**Step 2. Report + write output:** report alias / username / orgId / instanceUrl / status / expiration. Write the **wrapped** `{status, result}` JSON to `<output-dir>/org-display-result.json` — do NOT unwrap. In any committed example/gold, `accessToken` and `sfdxAuthUrl` must be redacted (value begins with `[REDACTED]`).

**`--verbose`:** never add it and never run it from this skill — it returns `sfdxAuthUrl` (a refresh token) into agent context. If the user needs the auth URL, tell them to run `sf org display --verbose` themselves in their own terminal.

**Detail:** `references/scratch-org-operations.md`.

---

## Resuming Scratch Org Creation

For a create that ran with `--async` or timed out (exit code 69).

**Step 1. Execute:**
```bash
sf org resume scratch --job-id <id> --json
```
If the user gave an explicit `--job-id`, use it; otherwise default to `--use-most-recent`. If there is no recent job, surface the CLI's not-found result unchanged and point the user to `sf org list` — do not invent a job id.

**Step 2. Write output:** write the command's JSON as-is to `<output-dir>/scratch-org-resume-result.json`.

**Detail:** `references/scratch-org-operations.md`.

---

## Deleting a Scratch Org

**Destructive — no undo.**

**Step 1. Confirm before running.** Ask "Delete scratch org `X`?" and wait for confirmation, UNLESS the user already gave explicit deletion intent. If the target is the current default org, call that out in the confirmation (extra-guard).

**Step 2. Execute** (only after confirmation):
```bash
sf org delete scratch --target-org <alias> --no-prompt --json
```
`--no-prompt` is passed *after* the skill's own confirmation, so the agent isn't left waiting on the CLI's interactive prompt.

**Step 3. Write output:** write the command's JSON as-is to `<output-dir>/scratch-org-delete-result.json`.

**Detail:** `references/scratch-org-operations.md`.

---

## Creating Snapshots

**REQUIRED steps — execute in order:**

**Step 1. Get inputs:**
- Source org: scratch org ID or alias (from user)
- Snapshot name: unique name (from user)
- Description: optional (from user)

**Step 2. Determine Dev Hub:** resolve to a concrete value and pass it explicitly via `--target-dev-hub` in Step 3 (same order as scratch-org creation — never guess a name):
1. A Dev Hub the user named → use it verbatim.
2. Else the default: non-empty `result[0].value` from `sf config get target-dev-hub --json`.
3. Else the single authenticated Dev Hub — run **this exact all-bucket command** (do NOT hand-write a single-bucket filter, which misses hubs that land in `devHubs`/`nonScratchOrgs`):
   ```bash
   sf org list --json | jq -r '[.result.devHubs[]?, .result.nonScratchOrgs[]?, .result.other[]?, .result.sandboxes[]?, .result.scratchOrgs[]?] | map(select(.isDevHub == true).username) | unique | .[]'
   ```
   Exactly one → use it. Zero → **do NOT run the snapshot command at all**; advise `sf org login web --set-default-dev-hub` and stop. Two or more → ask the user which.

Never fabricate a placeholder alias (e.g. `eval-target`, `my-dev-hub`) and never run the command with no `--target-dev-hub` flag — the CLI rejects a bad name with `NotADevHubError` and a missing default with `NoDefaultDevHubError`. If no hub resolves, that is a hard stop, not a value to guess.

**Step 3. Execute:**
```bash
sf org create snapshot --source-org <orgId-or-alias> --name <SnapshotName> --target-dev-hub <devHub> --json
```

With description:
```bash
sf org create snapshot --source-org <orgId-or-alias> --name <SnapshotName> --description "<desc>" --target-dev-hub <devHub> --json
```

**Step 4. Report result:** Returns JSON with SnapshotId and Status. If an output directory is available (per the output artifacts rule above), write the JSON response to `<output-dir>/snapshot-result.json`.

**Error handling:** surface the CLI's own error unchanged. For example:
- "Snapshot name already exists" → use a different unique name

**When you need more detail:**
- For complete snapshot creation workflow and flag reference → load `references/creating-snapshot.md`
- For CLI flag reference → load `references/cli_flags.md`

---

## Opening Orgs

**REQUIRED steps — execute in order:**

**Browser launch only — never `--json`, never `--url-only`.** Open is the one operation in this skill that writes NO artifact. Plain `sf org open` launches the browser and logs the user in without ever printing a login URL, so no credential enters agent context or a file. Do NOT add `--json`: `sf org open --json` returns a **live login URL** in `result.url` (`/secur/frontdoor.jsp?otp=`/`sid=<token>`) that is credential-equivalent — pulling it into context (even to redact it before writing) is the exact S1 leak the plain command avoids. Same reason `--url-only` is banned: if the user explicitly asks for the URL and not a browser (e.g. "URL only", "just give me the link", "headless/remote"), do NOT run it — tell them to run `sf org open --url-only` **themselves in their own terminal** (same handling as `sf org display --verbose`). A vague "open my org" just opens the browser.

**Step 1. Match user request to command:**

| User wants | Command |
|-----------|---------|
| Open default org | `sf org open` |
| Open specific org | `sf org open --target-org <alias>` |
| Specific browser | `sf org open --browser chrome` |
| Incognito mode | `sf org open --private` |
| Navigate to path | `sf org open --path '<path>'` |
| Open metadata file | `sf org open --source-file <file-path>` |
| URL only | **Do not run.** Tell the user to run `sf org open --url-only` locally — it returns a live login token the skill must not emit. |

**Step 2. Execute the matching command using the Bash tool.** Plain `sf org open` prints nothing on success — that is expected.

**Step 3. Report result:** Report to the user that the org (or path/metadata file) was opened in the browser. There is NO artifact to write for open operations — do not write `org-url-result.json` or any file, and do not add `--json` to produce one. If the command errors, surface it per Error handling below.

**Error handling:**
- "no target org" → advise `sf config set target-org <alias>`
- "auth error" → advise `sf org login web --alias <alias>`

**When you need more detail:**
- For complete opening org workflow and all available flags → load `references/opening-org.md`

---

## Reference File Index

Load these reference files for detailed guidance:

| File | When to read |
|------|-------------|
| `references/scratch-org-create.md` | Creating scratch orgs (edition, definition file, snapshot, org shape), AUTO MODE, STATE A/B project handling, batch create, and definition-file authoring |
| `references/scratch-org-operations.md` | Operating on existing orgs: list, display, resume, delete — plus shared lifecycle rules and troubleshooting |
| `references/definition_file_options.md` | User needs to configure org features, settings, or advanced definition file options beyond basic org creation |
| `references/edition_types.md` | User asks which edition to choose or needs to understand edition differences |
| `references/snapshot_usage.md` | User wants to use snapshots in definition files or needs post-snapshot workflow guidance |
| `references/cli_flags.md` | User needs complete snapshot CLI flag reference |
| `references/creating-snapshot.md` | Troubleshooting snapshot creation failures or need detailed snapshot workflow |
| `references/opening-org.md` | User needs to navigate to specific setup paths, open metadata files, or use advanced open flags |

## Example Files

Example command outputs for testing and troubleshooting:

| File | Purpose |
|------|---------|
| `examples/scratch-orgs/success_definition_file.json` | Successful scratch org creation using `--definition-file` |
| `examples/scratch-orgs/success_edition.json` | Successful scratch org creation using `--edition developer` |
| `examples/scratch-orgs/success_snapshot.json` | Successful scratch org creation using `--snapshot` |
| `examples/scratch-orgs/success_shape.json` | Successful scratch org creation using `--source-org` (org shape) |
| `examples/scratch-orgs/error_no_devhub.json` | Error when Dev Hub not authenticated |
| `examples/scratch-orgs/error_timeout.json` | Timeout error during org creation (exit code 69) |
| `examples/scratch-orgs/list_output.json` | `sf org list --json` output (active scratch orgs array) |
| `examples/scratch-orgs/display_output.json` | `sf org display --json` output (wrapped, tokens redacted) |
| `examples/scratch-orgs/resume_output.json` | `sf org resume scratch --json` output (completed org) |
| `examples/scratch-orgs/delete_output.json` | `sf org delete scratch --json` output |
| `examples/snapshots/success_output.json` | Successful snapshot creation |
| `examples/snapshots/error_output.json` | Common snapshot error scenario (duplicate name) |
