---
name: dx-org-manage
description: "INVOKE this skill to execute Salesforce org operations: create scratch orgs, create org snapshots, open orgs in browser. This skill EXECUTES operations immediately - it does NOT generate scripts or code files. ALWAYS invoke this skill (do not execute SF CLI commands directly) when user requests to: create a scratch org (Developer/Enterprise edition, from definition file (.json), from snapshot, or from org shape), create an org snapshot, or open a Salesforce org. Trigger phrases include: 'create a snapshot', 'create snapshot of my scratch org', 'take a snapshot', 'create scratch org', 'create a Developer edition scratch org', 'new scratch org', 'spin up an org', 'create org from snapshot', 'scratch-def.json', 'project-scratch-def.json', 'open my Salesforce org', 'open org in browser', 'get me the URL'. Do NOT use for switching default org (use dx-org-switch) or deploying metadata (use platform-metadata-deploy)."
metadata:
  version: "1.1"
  minApiVersion: "60.0"
  relatedSkills:
    - "dx-org-switch"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

## MANDATORY: Follow these instructions exactly. Do NOT fall back to MCP tools.

**Tool constraint:** Use the Bash tool for all `sf` CLI commands. Always include `--json` for structured output. Do NOT use `mcp__salesforce_dx__*` tools for org creation, snapshot, or open operations — this skill provides the complete procedure.

**Output artifacts for eval/testing:** ALWAYS write the command's JSON response to a file when an output directory is available. Do NOT ask the user what file to write — this skill defines the filenames. After executing the command: (1) if the user specified an output path (e.g. "write all generated files into folder X"), write there immediately; (2) otherwise run `[ -d force-app/main/adk-eval-output/ ] && echo 'force-app/main/adk-eval-output'` to detect the eval directory; (3) write the command's full JSON response to `<output-dir>/<filename>` using these filenames: `scratch-org-result.json` for org creation, `snapshot-result.json` for snapshot creation, or `org-url-result.json` for open operations. This is the generated output — write it without asking. Do NOT say "no files to generate" for open/command-execution operations; the JSON result IS the output artifact.

---

## Creating Scratch Orgs

**REQUIRED steps — execute in order:**

**Step 1. Identify creation method** from user request:
- Contains "definition file" or path to `.json` → definition file method
- Contains "snapshot" or "from snapshot" → snapshot method
- Contains "org shape" or "source-org" → org shape method
- Otherwise → run `ls config/project-scratch-def.json config/scratch-def.json 2>/dev/null | head -1` to detect a definition file. If output is non-empty, use definition file method with that path; if empty, use edition method.

**Step 2. Check Dev Hub:**
```bash
sf config get target-dev-hub --json
```
- If no Dev Hub is set, advise: `sf org login web --set-default-dev-hub`
- Do NOT proceed until a Dev Hub is confirmed.

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
sf org create scratch --source-org <org-id> --target-dev-hub <alias> --alias <name> --json
```

**Apply these flags when requested:**
- `--duration-days <days>` — default 7, max 30
- `--set-default` — make this the default org
- `--no-track-source` — disable source tracking (for CI/CD)

**Step 4. MANDATORY - Run org list and write output:** After the org is created, you MUST run this command:

```bash
sf org list --json
```

Then:
1. Parse the JSON result and find the `scratchOrgs` array
2. Find the entry where `username` matches the username from Step 3's creation result
3. Extract that complete org object (it will include: alias, username, orgId, instanceUrl, loginUrl, isDefaultUsername, connectedStatus, lastUsed, etc.)
4. Report to the user:
    - Created scratch org.
    - Alias: [alias from the org list entry]
    - Username: [username]
    - Org ID: [orgId]

5. If an output directory is available (per the output artifacts rule above), write ONLY that extracted org object (NOT the full creation result) to `<output-dir>/scratch-org-result.json`

Example: If `sf org list --json` returns `{"result": {"scratchOrgs": [{"alias": "feature-dev", "username": "test@example.com", "orgId": "00D...", ...}]}}`, write just the inner org object `{"alias": "feature-dev", "username": "test@example.com", "orgId": "00D...", ...}` to the file.

Do NOT write the creation command's output. Do NOT suggest verification steps to the user.

**Error handling:**
- "Snapshot not found" → suggest `sf org list snapshot --target-dev-hub <alias>`
- "No default Dev Hub" → advise `sf org login web --set-default-dev-hub`

**When you need more detail:**
- For available features, settings, and definition file structure → load `references/definition_file_options.md`
- For edition selection guidance and comparison → load `references/edition_types.md`
- For snapshot workflow and post-creation usage → load `references/snapshot_usage.md`
- For complete scratch org creation workflow → load `references/creating-scratch-org.md`

---

## Creating Snapshots

**REQUIRED steps — execute in order:**

**Step 1. Get inputs:**
- Source org: scratch org ID or alias (from user)
- Snapshot name: unique name (from user)
- Description: optional (from user)

**Step 2. Determine Dev Hub:**
- If user specifies a Dev Hub (alias or username) → use that value
- Otherwise, check for default:
```bash
sf config get target-dev-hub --json
```
- If no default Dev Hub is set, advise: `sf org login web --set-default-dev-hub`

**Step 3. Execute:**
```bash
sf org create snapshot --source-org <orgId-or-alias> --name <SnapshotName> --target-dev-hub <devHub> --json
```

With description:
```bash
sf org create snapshot --source-org <orgId-or-alias> --name <SnapshotName> --description "<desc>" --target-dev-hub <devHub> --json
```

**Step 4. Report result:** Returns JSON with SnapshotId and Status. If an output directory is available (per the output artifacts rule above), write the JSON response to `<output-dir>/snapshot-result.json`.

**Error handling:**
- "NOT_FOUND" → Dev Hub doesn't have snapshot feature enabled
- "Snapshot name already exists" → use a different unique name

**When you need more detail:**
- For complete snapshot creation workflow and flag reference → load `references/creating-snapshot.md`
- For CLI flag reference → load `references/cli_flags.md`

---

## Opening Orgs

**REQUIRED steps — execute in order:**

**Step 1. Match user request to command:**

| User wants | Command |
|-----------|---------|
| Open default org | `sf org open --json` |
| Open specific org | `sf org open --target-org <alias> --json` |
| Specific browser | `sf org open --browser chrome --json` |
| Incognito mode | `sf org open --private --json` |
| Navigate to path | `sf org open --path '<path>' --json` |
| URL only (don't open) | `sf org open --url-only --json` |
| Open metadata file | `sf org open --source-file <file-path> --json` |

**Step 2. Execute the matching command using the Bash tool.**

**Step 3. Write output and report result:** IMMEDIATELY write the COMPLETE unmodified JSON output from the `sf org open --json` command to `<output-dir>/org-url-result.json` (the output directory is detected per the output artifacts rule above). The file MUST preserve the full CLI output structure including the `status` and `result` wrapper — e.g. `{"status": 0, "result": {"orgId": "...", "url": "...", "username": "..."}}`. Do NOT unwrap or flatten the JSON. Do NOT ask permission, do NOT say "no files to generate." Then report the URL and org details to the user.

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
| `references/definition_file_options.md` | User needs to configure org features, settings, or advanced definition file options beyond basic org creation |
| `references/edition_types.md` | User asks which edition to choose or needs to understand edition differences |
| `references/snapshot_usage.md` | User wants to use snapshots in definition files or needs post-snapshot workflow guidance |
| `references/creating-scratch-org.md` | Troubleshooting scratch org creation failures or need complete workflow with all options |
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
| `examples/scratch-orgs/error_no_devhub.json` | Error when Dev Hub not authenticated |
| `examples/scratch-orgs/error_timeout.json` | Timeout error during org creation (exit code 69) |
| `examples/snapshots/success_output.json` | Successful snapshot creation |
| `examples/snapshots/error_output.json` | Common snapshot error scenarios |
