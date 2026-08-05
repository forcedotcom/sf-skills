---
description: Sign out of one or all Salesforce orgs (sf org logout). Confirms before destructive action.
allowed-tools:
  - Bash
argument-hint: "[--target-org <alias>] [--all]"
---

Log out of one or more Salesforce orgs.

Workflow:

1. **Parse arguments** ($ARGUMENTS):
   - `--target-org <alias>` → log out of a specific org
   - `--all` → log out of every authenticated org
   - No arguments → list current orgs and ask which to log out of

2. **If no arguments:** call `sf org list --json`, present the orgs in a numbered list, and ask the user which to log out of.

3. **Confirm before action:** show the alias(es) about to be logged out and require explicit "yes" confirmation. This is destructive and the user will need to re-authenticate to use the org again.

4. **Run the logout:**
   ```bash
   sf org logout --target-org <alias> --no-prompt
   # or
   sf org logout --all --no-prompt
   ```

5. **Report:** confirm which orgs are now logged out. If the project's current `target-org` was logged out, suggest the user pick a new default via `/salesforce-development:set-default <alias>` or authenticate fresh via `/salesforce-development:login`.

Rules:
- ALWAYS confirm before logging out
- NEVER log out without explicit user input (no auto-cleanup)
- If the user logs out of the target-org, their next deploy/data command will fail until they reconfigure
