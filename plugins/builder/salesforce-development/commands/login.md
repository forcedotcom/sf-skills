---
description: Authenticate to a new Salesforce org via the browser (sf org login web). Optionally set the org as the project's default target.
allowed-tools:
  - Bash
argument-hint: "[--alias <name>] [--instance-url <url>] [--set-default]"
---

Authenticate to a Salesforce org. The user can pass:
- `--alias <name>` to label the auth (e.g., `myDevHub`, `customerSandbox`)
- `--instance-url <url>` for non-production endpoints (e.g., `https://test.salesforce.com` for sandboxes, `https://login.salesforce.com` for production — production is the default if omitted)
- `--set-default` to set this org as the project's `target-org` after auth

Workflow:

1. **Parse the arguments** ($ARGUMENTS) the user provided. Extract alias, instance-url, and set-default flag.

2. **Run the login command:**
   ```bash
   sf org login web {--alias $ALIAS} {--instance-url $URL}
   ```
   This opens a browser for OAuth. Tell the user clearly: "A browser window will open. Complete the login flow and return here."

3. **Handle browser-isn't-available case:** If the user is on a remote shell or the browser won't open, fall back to:
   ```bash
   sf org login device-code {--alias $ALIAS} {--instance-url $URL}
   ```
   which prints a code the user enters at salesforce.com/setup/connect.

4. **After successful auth:** if the user passed `--set-default`, run:
   ```bash
   sf config set target-org $ALIAS
   ```
   Otherwise, suggest they run `/salesforce-development:set-default <alias>` if they want to use this org for the current project.

5. **Verify:** print a one-liner with the new org's alias, edition, and instance URL:
   ```bash
   sf org display --target-org $ALIAS --json
   ```
   so the user sees the connected state.

Rules:
- Always use `--json` on `sf` commands so you can parse outcomes
- Do NOT log access tokens or any auth secrets
- If the user doesn't supply an alias, the auth saves under their username — recommend they pass `--alias` for easier reference later
- For sandbox auth, `--instance-url https://test.salesforce.com` is required
