---
description: Set the project's target-org (the org that all sf commands run against by default). If no org is named, lists the authenticated orgs for the user to pick.
allowed-tools:
  - Bash
argument-hint: "[alias-or-username] [--global]"
---

Set the active target-org for the current project (or globally).

Workflow:

1. **Parse arguments** ($ARGUMENTS):
   - `<alias-or-username>` (optional) — which org to make the default. If omitted (e.g. the user said "connect an org" with no name), help them pick in step 2.
   - `--global` (optional) — write to user-level config instead of project-level

2. **List the authenticated orgs:**
   ```bash
   sf org list --json
   ```
   - **If no org was named:** present the authenticated orgs as a short numbered list (alias · username · status) and ask which one to set as the default. Use the org they choose as `<alias>` below. If the list is empty, tell the user to authenticate first via `/salesforce-development:login --alias <name>` (a browser login), then stop.
   - **If an org was named:** confirm the alias/username appears in the list. If not, tell the user to authenticate first via `/salesforce-development:login --alias <name>`.

3. **Set the target-org:**
   ```bash
   # Project-local (default)
   sf config set target-org <alias>

   # User-global
   sf config set target-org <alias> --global
   ```

4. **Verify the change:**
   ```bash
   sf org display --target-org <alias> --json
   ```

Rules:
- Default is project-local (`.sf/config.json`) which is what most users want
- Use `--global` only when the user is working outside any specific project
- If the alias/username can't be found in `sf org list`, do not silently proceed
