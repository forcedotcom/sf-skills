---
name: dx-org-permission-set-assign
description: "ALWAYS USE THIS SKILL to assign permission sets to org users. Assign one or more permission sets to org users using the sf org assign permset command. TRIGGER when the user asks to assign, grant, give, add, or apply permission sets to users, admins, specific orgs, or specific users. Supports granting permissions, giving access, and adding permission sets to default admin or specific users via --on-behalf-of. DO NOT TRIGGER for listing permission sets or checking user permissions."
compatibility: Salesforce CLI (sf) v2+
metadata:
  version: "1.0"
---

# dx-org-permission-set-assign

Assigns one or more permission sets to org users using `sf org assign permset`. Handles all variants: default admin user, specific org targets, multiple permission sets, and assignment to specific users.

---

## Tool Restrictions

**Use ONLY the Bash tool** to execute `sf org assign permset`. Do NOT use MCP tools like `assign_permission_set` — ignore them completely.

---

## Scope

- **In scope**: Assigning permission sets to users via `sf org assign permset`
- **Out of scope**: Creating permission sets (use `platform-permission-set-generate`), listing permission sets, checking user permissions

---

## Required Inputs

Infer from the user's request:

- **Permission set name(s)**: Extract from user message (can be multiple)
- **Target org**: Use default unless specific alias/username mentioned
- **Target user(s)**: Default is org's default admin user; use `--on-behalf-of` if specific users mentioned

---

## Workflow

1. Match user request to command in table below
2. Execute via Bash tool: `sf org assign permset` with appropriate flags and `--json` flag
3. Return result

If error occurs, check the `failures` array in JSON output for details.

### Command Decision Table

| User intent | Execute via Bash tool |
|-------------|---------|
| Assign one permission set to default admin | `sf org assign permset --name <PermSetName> --json` |
| Assign multiple permission sets to default admin | `sf org assign permset --name <PermSet1> --name <PermSet2> --json` |
| Assign to specific org | `sf org assign permset --name <PermSetName> --target-org <alias> --json` |
| Assign to specific user(s) | `sf org assign permset --name <PermSetName> --on-behalf-of <username1> --on-behalf-of <username2> --json` |
| Assign multiple sets to specific users | `sf org assign permset --name <PermSet1> --name <PermSet2> --on-behalf-of <username1> --on-behalf-of <username2> --json` |

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use `--json` flag | Provides structured output for reliable parsing and error handling |
| Permission set names are case-sensitive | Use exact API names as they appear in the org |
| Multiple `--name` flags can be combined in one command | More efficient than separate commands per permission set |
| Multiple `--on-behalf-of` flags assign to multiple users | Batch assignment in single command; processed sequentially to avoid auth file collisions |
| Use CLI username aliases, not Salesforce User.Alias field | The `--target-org` and `--on-behalf-of` flags expect CLI aliases set via `sf alias set`, not the User object's Alias field |
| Duplicate assignments are idempotent | Re-assigning an already-assigned permission set succeeds silently |
| Partial success is possible | Command can return both successes and failures in one run; non-zero exit code if any failures |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Permission set name with spaces | Enclose in double quotes: `--name "Permission Set Name"` |
| "PermissionSet not found" error | Verify permission set exists in target org; check for typos in name |
| Assignment succeeds but user doesn't see permissions | Check `<hasActivationRequired>` in permission set metadata — may need manual activation in Setup |
| "User not found" error | Username/alias doesn't exist in target org — verify with `sf org display user --target-org <alias>` |
| Partial success (some users succeed, others fail) | Check JSON output — command returns both `successes` and `failures` arrays; exit code will be non-zero if any failures occurred |

---

## Output Expectations

The command returns JSON output with status code and result details.

See `examples/success_output.json` and `examples/error_output.json` for response structures.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `examples/success_output.json` | To understand successful assignment response structure |
| `examples/error_output.json` | To handle common error scenarios |
| `references/cli_flags.md` | For detailed explanation of all available flags |
