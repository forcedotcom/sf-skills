# Scratch Org Operations

Workflow for operating on **existing** orgs with `sf`: **list**, **display**, **resume**, and
**delete**, plus the shared rules, constraints, and troubleshooting for the whole lifecycle. For
creating an org (edition, definition file, snapshot, org shape, AUTO MODE, STATE A/B, batch,
definition-file authoring), see `scratch-org-create.md`.

---

## Security posture — pure pass-through (read first)

The skill relays every input to `sf` **unchanged** and surfaces the CLI's `--json` result —
success or error — **as-is**. It does not pre-validate fields, does not normalize or translate
field names, and does not add or strip error text; the CLI already frames its own output. The one
place the skill actively protects the user is a live credential: it never runs `sf org display
--verbose` (which returns a refresh token) and it never un-redacts a token the CLI already
redacted.

The skill's own docs/examples never claim a feature is "not enabled" or that a permission is
missing — that framing is the platform's job, delivered through the CLI's own error output.

---

## List

Show the developer's scratch orgs.

```bash
sf org list --json
```

- **Default view:** active scratch orgs from `result.scratchOrgs[]` (answers "which scratch orgs
  do I have?").
- **Options (not the default):** `--all` (include expired/deleted/unknown), `--clean` (remove
  stale local entries).
- **Report per active org:** alias, username, orgId, expiration date.
- **Artifact:** write the `result.scratchOrgs[]` **array** to `scratch-org-list-result.json`.

---

## Display

Show details of one org.

```bash
sf org display --target-org <alias> --json
```

- Plain output only — always the non-verbose form above. **Never add `--verbose`, and never run
  it on request.** `--verbose` returns `sfdxAuthUrl` (a refresh token) in command output, which
  would pull a live credential into agent context. If the user needs the auth URL, direct them to
  run `sf org display --verbose` themselves in their own terminal — do not run it from this skill.
- **Report:** alias, username, orgId, instanceUrl, status, expiration.
- **Artifact:** write the **wrapped** `{status, result}` JSON to `org-display-result.json`.

> **Sanitize committed artifacts.** In any example/gold committed to the skill, the
> `accessToken` and `sfdxAuthUrl` values must be redacted — begin them with `[REDACTED]`
> regardless of CLI version (older supported CLIs do not auto-redact). Current CLIs emit
> `"[REDACTED] Use 'sf org auth show-access-token' to view"`; either the bare marker or that
> full string is acceptable. `instanceUrl` is a normal public field; keep it.

---

## Resume

Continue a create that ran with `--async` or timed out (exit code 69).

```bash
# With an explicit job/request id
sf org resume scratch --job-id <id> --json

# Otherwise, the most recent job
sf org resume scratch --use-most-recent --json
```

Behavior: if the user gives an explicit `--job-id`, use it; otherwise default to
`--use-most-recent`; if there is no recent job, surface the CLI's not-found result unchanged and
point the user to `sf org list`. Do not invent a job id. **Artifact:** write the command's JSON
as-is to `scratch-org-resume-result.json`.

---

## Delete

Delete a scratch org. **Destructive — no undo.**

```bash
sf org delete scratch --target-org <alias> --no-prompt --json
```

- **Always confirm first** ("Delete scratch org `X`?") before running — UNLESS the user already
  gave explicit deletion intent.
- **Extra-guard the default org:** if the target is the current default org, call that out in the
  confirmation.
- `--no-prompt` is passed on the CLI *after* the skill's own confirmation, so the agent isn't
  left waiting on an interactive prompt.
- **Artifact:** write the command's JSON as-is to `scratch-org-delete-result.json`.

---

## Rules / constraints

| Constraint | Rationale |
|-----------|-----------|
| Always include `--json` | Structured output for parsing success/failure |
| Create blocks until completion — do NOT poll | The command waits until the org is ready; when it returns `username`/`orgId`, the org is ready. The single post-create `sf org list` call is for artifact collection, not polling. Exception: `--async` or a timeout (exit 69) → use `sf org resume scratch` |
| Dev Hub must be resolvable | Creation requires Dev Hub access (default hub, named hub, or pick-from-list when none is set) |
| One creation source *type* per command | Edition, snapshot, and shape are mutually exclusive; a same-dimension flag override is allowed |
| Duration max is 30 days | Platform limit |
| Confirm before delete | Destructive, no undo; extra-guard the default org |

---

## Troubleshooting (errors are pass-through — surface the CLI's own message)

| Issue | Next step |
|-------|-----------|
| `No default Dev Hub org found` | Authenticate with `sf org login web --set-default-dev-hub` or name one with `--target-dev-hub` |
| `NamedOrgNotFoundError` on Dev Hub | Dev Hub not authenticated — run `sf org login web` |
| `edition value must be one of` | Use developer/enterprise/group/professional, or a partner edition (CLI flag hyphenated, e.g. `partner-developer`) |
| `Snapshot not found` | Snapshot doesn't exist in this Dev Hub — run `sf org list snapshot` to see available |
| `sourceOrg value must be 15 or 18 characters` | Source org ID format incorrect — pass the 15/18-char `00D…` org ID of the org the shape was captured from |
| Timeout during creation (exit code 69) | CLI prints a resume command with the request ID; run it or increase `--wait` next time |
| `Definition file not found` | Path is incorrect — verify the file exists (re-ask/re-list rather than guessing) |
| Partner editions unavailable | Partner editions require the Dev Hub to be a Partner Business Org |

---

## Additional resources

- `scratch-org-create.md` — creating orgs (edition, definition file, snapshot, org shape),
  AUTO MODE, STATE A/B, batch create, and definition-file authoring
- `definition_file_options.md` — features, settings, and definition-file schema
- `edition_types.md` — edition selection and the CLI-flag-vs-definition-file format distinction
- `snapshot_usage.md` — using snapshots in definition files and post-snapshot workflow
