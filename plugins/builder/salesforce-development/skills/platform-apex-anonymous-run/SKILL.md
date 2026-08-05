---
name: platform-apex-anonymous-run
description: "Use this skill to run anonymous Apex against the connected Salesforce org — from a .apex file or a pasted snippet — capturing the debug log, surfacing compile and runtime errors, and summarizing results. Trigger on phrases like \"run this anonymous apex\", \"execute this script against my org\", \"run this snippet of Apex\", \"what does this code return\", or \"execute scripts/foo.apex\". Wraps verification-style scripts in a savepoint and rollback so org state is untouched, and warns before running against production. DO NOT TRIGGER for authoring .cls or .trigger files (use platform-apex-generate), running Apex unit tests (use platform-apex-test-run), or deep debug-log analysis (use platform-apex-logs-debug)."
metadata:
  version: "1.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-apex-test-run"
    - "platform-apex-logs-debug"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# platform-apex-anonymous-run

Run anonymous Apex against the connected Salesforce org via `sf apex run --file`, capture the debug log, and narrate compile-time and runtime outcomes back to the developer.

This is the agent-side equivalent of VS Code's *Execute Anonymous Apex* (document and selection) commands.

This skill is **runtime, not generation** — for authoring `.cls` / `.trigger` files use `platform-apex-generate`; for running Apex unit tests use `platform-apex-test-run`; for deep debug-log analysis (governor breakdowns, SOQL-in-loop detection) hand off to `platform-apex-logs-debug`.

---

## Tool Restrictions

**Use ONLY the Bash tool** to execute `sf apex run`, and the `Write` tool to stage snippet temp files. Do NOT use MCP tools for execution.

---

## Anonymous Apex is NOT read-only

Anonymous Apex executes with the running user's permissions and **can perform DML, callouts, and platform events**. Treat every invocation as a write unless the developer has stated otherwise.

- **Verification-style scripts (preferred for "test this"):** wrap the body in a savepoint + rollback so org state is untouched:

  ```apex
  Savepoint sp = Database.setSavepoint();
  try {
      // ... code under test ...
  } finally {
      Database.rollback(sp);
  }
  ```

- **Production org heads-up:** if the resolved `<alias>` points at a production org (no scratch/sandbox markers in `sf org display --json`), surface a clear warning before running. This is informational only — there is no automated block. Always wait for an explicit "yes, run it" before executing destructive scripts in prod.

- **Never run anonymous Apex you did not generate or have not been shown** — if the developer pastes a snippet, echo it back and confirm before executing.

---

## Workflow

### Step 1 — Identify the target org

Resolve the active org alias from configuration. If `target-org` is set, the `--target-org` flag may be omitted from the command, but always log which alias was used in the report.

```bash
sf config get target-org --json
```

Throughout this skill, `<alias>` is the resolved alias or username. If no `target-org` is set, ask the developer; do not silently default. If the org is not authenticated, re-authenticate with `sf org login web` or switch orgs with the `dx-org-switch` skill.

### Step 2 — Resolve the input mode

| Mode | When | Action |
|---|---|---|
| **File mode** | Developer points at an existing path ending in `.apex` (or any path they specify) | Run `sf apex run --file <path>` directly |
| **Snippet mode** | Developer pastes Apex code into the conversation | Write to `.sfdx/tmp/anon-<unix-ts>.apex` first, then run `sf apex run --file <tmp-path>` |

**Why a temp file for snippets, instead of an inline flag?** The current `sf apex run` CLI only supports `--file` (and interactive stdin). It does **not** expose an `--apex-code` flag. Even where inline code is supported by other tooling, multi-line Apex passed inline runs into shell-escaping pitfalls (single quotes in string literals, backslashes, embedded `$`). Writing to a temp file is the only reliable path for arbitrary snippets.

Verify CLI flags before deviating:

```bash
sf apex run --help
```

Supported flags (as of writing): `--file/-f`, `--target-org/-o`, `--api-version`, `--json`, `--flags-dir`. **Do not invent flags** — if the task asks for something not listed, surface that to the developer rather than guessing.

### Step 3 — Set up trace flags (for useful logs)

`sf apex run` returns a debug log only if a `TraceFlag` is active for the running user (or a streaming tail is attached). Recommended path — let the developer tail logs in another terminal:

```bash
sf apex tail log --target-org <alias> --color
```

This auto-creates a short-lived TraceFlag for the running user and streams logs as anonymous Apex executes. Mention this in the report so the developer can copy/paste it.

If no trace flag is set up, `sf apex run` will still execute the code and return compile/runtime status — only the *debug log body* will be missing or sparse.

### Step 4 — Snippet mode: write the temp file

Only applies when the input is a pasted snippet:

```bash
mkdir -p .sfdx/tmp
TS=$(date +%s)
# write the snippet content to .sfdx/tmp/anon-${TS}.apex via the Write tool, NOT via shell heredoc
```

Use the agent's `Write` tool (not a heredoc) so the snippet is preserved verbatim — heredocs subject the content to additional shell expansion. Echo the resolved temp path to the developer in the report. Do not auto-clean the temp file after execution — leave it under `.sfdx/tmp/` for inspection. The `.sfdx/` directory is conventionally gitignored.

### Step 5 — Execute

```bash
sf apex run --file <path> --target-org <alias> --json
```

- Always pass `--json`. Human-format output conflates compile vs runtime errors.
- If `target-org` is already configured, `--target-org` may be omitted, but log the alias used.
- The command exits non-zero on compile errors. Capture both stdout and the parsed JSON.

### Step 6 — Parse the JSON response

The `sf apex run --json` response shape (relevant fields):

```json
{
  "status": 0,
  "result": {
    "compiled": true,
    "success": true,
    "compileProblem": "",
    "exceptionMessage": "",
    "exceptionStackTrace": "",
    "line": -1,
    "column": -1,
    "logs": "...full debug log text..."
  }
}
```

Decision tree:

| `compiled` | `success` | Meaning | Surface |
|---|---|---|---|
| `false` | — | Compile failure | `compileProblem`, `line`, `column`, the offending source line |
| `true` | `false` | Runtime exception | `exceptionMessage`, `exceptionStackTrace`, plus log tail |
| `true` | `true` | Success | Whatever the script printed via `System.debug` (extracted from `logs`) |

`status !== 0` (top-level) means the CLI itself failed (not authenticated, file not found, network). Surface the raw error and stop.

### Step 7 — Surface the debug log

- **Short logs (< ~200 lines):** inline the log body in the report between fenced code blocks.
- **Large logs:** write the log to `.sfdx/tmp/anon-<ts>.log` and report the path. Include the last 30 lines inline as a tail summary.
- **Empty / missing log:** likely no active TraceFlag. Surface the Step 3 setup hint and proceed with whatever compile/runtime status was returned.

Highlight these patterns when present in the log:

| Pattern | Why it matters |
|---|---|
| `LIMIT_USAGE_FOR_NS` lines | Governor consumption snapshot — flag SOQL/DML/CPU near-limit |
| `EXCEPTION_THROWN` | Unhandled exception within the anonymous block |
| `FATAL_ERROR` | Unrecoverable error — show the full trailing block |
| `SOQL_EXECUTE_BEGIN` count > 1 inside a loop | SOQL-in-loop hint (hand off to `platform-apex-logs-debug`) |
| `DML_BEGIN` count high | Unbatched DML hint |

Do not attempt full log parsing here — surface signals only, then hand off to `platform-apex-logs-debug` for deep analysis.

### Step 8 — Report

```text
Anonymous Apex run: <one-line summary — file or snippet, success or failure>
Org: <alias>  (mode: scratch | sandbox | production)
Source: <file path or temp path for snippet>
Compile: success | <error + line:column>
Runtime: success | <exception type + message>
Limits: <CPU=x/10000ms, SOQL=y/100, DML=z/150>  (only when log includes LIMIT_USAGE_FOR_NS)
Log: <inline | path .sfdx/tmp/anon-<ts>.log>
Rollback: applied | not applied | n/a
Next: <suggested follow-up>
```

---

## Examples

### Example 1 — File mode

> "Run `scripts/seed-test-data.apex` against my default org."

1. Resolve `<alias>` from `sf config get target-org --json`.
2. Confirm the file exists; if not, stop and surface `file not found`.
3. Run `sf apex run --file scripts/seed-test-data.apex --target-org <alias> --json`.
4. Parse JSON. Report compile/runtime status, log tail, and org mode.
5. Suggest: "If this seeded real data and you'd like to verify without persisting, re-run with the rollback wrapper (snippet mode)."

### Example 2 — Snippet mode (read query)

> "Execute `System.debug([SELECT count() FROM Account]);` and tell me the count."

1. Resolve `<alias>`.
2. Echo the snippet back; confirm.
3. Write the snippet to `.sfdx/tmp/anon-<ts>.apex` (Write tool).
4. Run `sf apex run --file .sfdx/tmp/anon-<ts>.apex --target-org <alias> --json`.
5. Parse `result.logs`; extract the `USER_DEBUG` line for the count.
6. Report: "Account count = N. Source: `.sfdx/tmp/anon-<ts>.apex` (kept for reference)."

### Example 3 — Verification with rollback

> "Test that this Apex correctly upserts a Contact, then rollback."

1. Resolve `<alias>`. If prod, surface a heads-up before running.
2. Wrap the developer's snippet:

   ```apex
   Savepoint sp = Database.setSavepoint();
   try {
       // ---- developer snippet begins ----
       Contact c = new Contact(LastName = 'Smoke', Email = 'smoke@example.com');
       upsert c Email;
       System.debug('Upserted: ' + c.Id);
       // ---- developer snippet ends ----
   } finally {
       Database.rollback(sp);
       System.debug('Rolled back savepoint.');
   }
   ```

3. Write to `.sfdx/tmp/anon-<ts>.apex`, execute, parse JSON.
4. Report compile/runtime status, the upserted Id from the log, and `Rollback: applied`.

---

## Failure Modes

| Symptom | Cause | Recovery |
|---|---|---|
| `No authorization information found for ...` | Org not authenticated, or alias is wrong | Run `sf org list --json`; re-auth with `sf org login web` or use `dx-org-switch` |
| `ENOENT: no such file or directory, open '<path>'` | `.apex` file path is wrong or relative to the wrong cwd | Confirm absolute path; re-run |
| `compileProblem` non-empty in JSON | Apex compile error | Surface `compileProblem`, `line`, `column`; show that line; suggest a fix |
| `success: false` with `exceptionMessage` | Runtime exception inside the anonymous block | Surface exception type + message + stack; show governor counts if present |
| `logs` field is empty even on success | No active `TraceFlag` for running user | Tell developer to run `sf apex tail log --target-org <alias>` in another terminal, then re-run |
| `status !== 0` with no `result` | CLI / network / auth failure before execution | Surface raw stderr; do not retry blindly |
| Unrecognized flag error | Spec drift with the installed CLI | Re-check `sf apex run --help`; do not invent flags |

---

## Rules

- Always pass `--json`.
- Always resolve `<alias>` from configuration or the developer; never hardcode.
- Never use `--apex-code`-style inline flags — they are not supported by the current CLI and are escape-hostile. Always go through `--file`.
- Always echo a pasted snippet back to the developer for confirmation before executing.
- For verification-style scripts, default to wrapping in `Database.setSavepoint()` + `Database.rollback()`.
- For prod orgs, surface a heads-up but do not auto-block — the developer is in charge.
- Do not auto-delete temp files under `.sfdx/tmp/`.
- This skill executes anonymous Apex; it does not author, deploy, or test `.cls`/`.trigger` files. For those, hand off to `platform-apex-generate`, the deploy skills, or `platform-apex-test-generate`.
- For deep log analysis, hand off to `platform-apex-logs-debug`.
