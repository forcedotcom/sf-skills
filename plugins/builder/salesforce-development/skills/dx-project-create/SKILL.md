---
name: dx-project-create
description: "Scaffold a brand-new Salesforce DX project from scratch — pick a template, generate the project, relocate this session into it, authenticate an org, set it as default, and enable source tracking. TRIGGER when the user asks to 'create a new Salesforce project', 'create a new project for me', 'start a new Salesforce project', 'new SFDX project', 'scaffold a project', 'sf project generate', or 'set up a new org project from scratch'. DO NOT TRIGGER for: validating tools on an existing project (use platform-environment-validate or /salesforce-development:setup), org authentication on a project that already exists (use /salesforce-development:login), showing an existing project's metadata stats (use /salesforce-development:project), or creating scratch orgs in an existing project (use dx-org-manage)."
allowed-tools:
  - Bash
  - Read
---

# Creating a New Salesforce Project

Walk the user through a wizard that scaffolds a new Salesforce DX project, relocates this session into the new project, connects it to an org, and configures it for development. Run each step in order, confirming with the user before any environment-changing action.

The `salesforce-development` plugin's MCP servers (`salesforce-api-context`, `salesforce-metadata-experts`, `salesforce-lsp`) are provided by the **installed plugin**, not by the project — so they stay available in the new project automatically once the session relocates. There is no per-project `.mcp.json` to copy.

## Step 1: Choose a Project Template

Prompt the user to pick a template. Default to `standard` if they don't have a preference.

| Template | Use for |
|---|---|
| `standard` (default) | General-purpose SFDX project with the conventional `force-app` layout |
| `empty` | Bare project with minimal scaffolding |
| `analytics` | CRM Analytics (Tableau CRM) development |
| `reactinternalapp` | React-based internal app |
| `reactexternalapp` | React-based external/experience app |
| `agent` | Agentforce agent development |

## Step 2: Choose a Project Name

Prompt the user for a project name. This becomes the new directory name, so it must be a valid directory name (no spaces or path separators).

## Step 3: Generate the Project

Run in the current working directory:

```bash
sf project generate -t {template} -n {name}
```

This creates a new `{name}/` directory under the current working directory.

## Step 4: Relocate the Session Into the New Project

Modern Claude Code (v2.1.169+) can move the current session into the new directory in place — no new terminal, no relaunch, conversation history preserved. Tell the user to run:

```text
/cd {name}
```

This relocates the session: the new directory's `CLAUDE.md` is loaded, project storage moves there (so `--resume`/`--continue` find it), and the cwd becomes the project root, so all remaining `sf` commands run as plain `sf ...` with no path prefix.

`/cd` is a client-side move: it fires no hook and gives you no turn, so the session goes **quiet** the instant they run it — expected, not a hang. But it also means the message in which you hand them `/cd` is your last word until they speak again, so that message MUST end with an affordance telling them how to resume. Close it with a line like:

> Once you're in, just say **"what's next"** (or "connect an org") and I'll pick up from there.

Saying "what's next" re-engages this session and paints the position rail, which points at the next step (authenticating an org). Never imply the session will continue on its own after `/cd` — it won't.

When they re-engage, confirm the move in one short line (e.g. "You're in {name} now.") and continue to Step 5. Do **not** run `sf-context detect` or `check-tools` to "re-surface" the banner: `detect` invoked as a tool prints the raw hook JSON (not a rendered banner), and the plugin already surfaces the banner on its own — it shows the HEADLESS identity once per session (at the user's first Salesforce ask, at session start, or on their first orientation question), and paints the position rail whenever they ask "where am I" / "what's next". A dev-environment health check is available on demand via `/salesforce-development:setup`.

**Fallback for older Claude Code (before v2.1.169):** `/cd` reports `Unknown command`. In that case the user must relaunch in the new directory instead:

```bash
cd {name} && claude
```

The `salesforce-development` plugin is installed globally (via the marketplace), so a fresh session in the new directory loads it automatically and fires SessionStart — the banner and health check appear on their own, no manual `sf-context` calls needed. The remaining steps below then run from inside the project.

## Step 5: Authenticate to an Org

Authenticate the org this project will deploy to:

```bash
sf org login web --alias {alias}
```

- Prompt the user for an `--alias` so later steps can reference the org by name.
- For a **sandbox**, add `--instance-url https://test.salesforce.com`.
- For **production**, omit `--instance-url` (defaults to login.salesforce.com).

If the user already has the org authenticated, skip the login and just collect the existing alias.

## Step 6: Set as Default Org

Set the freshly authenticated org as the project's default target:

```bash
sf config set target-org {alias}
```

## Step 7: Ensure Source Tracking Is Enabled

Check whether source tracking works against the org using a deploy preview (the lightest read-only source-tracking probe):

```bash
sf project deploy preview --target-org {alias} --json
```

If this fails with an error mentioning source tracking not supported or not enabled, offer to enable it:

```bash
sf org enable tracking --target-org {alias}
```

Confirm with the user before running the enable command.

## Closing Message

Once all steps are complete, tell the user:

```text
Your project is ready! Here's what was set up:

  ✅ Project generated: {name}/
  ✅ Session relocated into {name}/ (via /cd)
  ✅ Default org: {alias}
  ✅ Source tracking: enabled (or status)

You're already working inside the new project — this same session moved
here with /cd, so just keep going. Run /salesforce-development:setup
anytime to re-check your dev environment.
```

If the user took the older-version fallback (relaunched with `cd {name} && claude` instead of `/cd`), they're in a fresh session in the project and the SessionStart banner already walked them through the environment — point them to `/salesforce-development:setup` to re-check tools.

## Rules

- Run the steps in order; confirm before any environment-changing action (login, set-default, enable tracking).
- The plugin's MCP servers come from the installed plugin, not the project — do NOT create or copy a `.mcp.json` into the new project (the plugin's config uses `${CLAUDE_PLUGIN_ROOT}`, which does not resolve in a project-level file).
- Prefer `/cd {name}` to relocate the session in place (Claude Code v2.1.169+) — a skill can't relocate the session on the user's behalf, so instruct the user to run it. Only fall back to `cd {name} && claude` (relaunch) when `/cd` reports `Unknown command` on an older build.
- The message that hands the user `/cd {name}` is your last turn until they speak again (`/cd` fires no hook), so it MUST end with a resume affordance — e.g. 'once you're in, just say "what's next".' Never promise the session will connect an org or continue on its own after `/cd`; it stays silent until the user re-engages.
- After `/cd`, do NOT run `sf-context detect` or `check-tools` to "show" the banner — `detect` as a tool prints raw JSON, and the plugin surfaces the banner itself (once per session; the position rail on orientation questions). Just confirm the move in one line and continue. Health is available on demand via `/salesforce-development:setup`.
- For sandbox login, `--instance-url https://test.salesforce.com` is REQUIRED (the CLI default points at production).
- NEVER store or display access tokens.
- For an EXISTING project that just needs tooling validated, use `platform-environment-validate` (or `/salesforce-development:setup`); for org auth on an existing project, use `/salesforce-development:login`.
