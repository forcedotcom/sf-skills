---
name: dx-project-create
description: "Scaffold a Salesforce DX project from any template (standard, agent, analytics, React/Angular/Vue app), move the session in, connect an org, enable source tracking. Use to create a Salesforce/SFDX project. DO NOT TRIGGER for: existing UI-bundle apps (experience-ui-bundle-frontend-generate); UI-bundle scaffold in a larger build (experience-ui-bundle-project-generate, experience-ui-bundle-app-coordinate); tool checks (platform-environment-validate); org login (login); scratch orgs (dx-org-manage)."
metadata:
  domains: ["Developer Experience"]
  relatedSkills:
    - "experience-ui-bundle-project-generate"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-deploy"
    - "platform-environment-validate"
    - "dx-org-manage"
  cliTools:
    - tool: ["npm"]
      semver: ">=8.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
allowed-tools:
  - Bash
  - Read
---

# Creating a New Salesforce Project

Walk the user through a wizard that scaffolds a new Salesforce DX project, relocates this session into the new project, connects it to an org, and configures it for development. Run each step in order, confirming with the user before any environment-changing action.

The plugin's MCP servers come from the **installed plugin**, not the project, so they stay available after the session relocates. There is no per-project `.mcp.json` to copy.

## Step 1: Choose a Project Template

This skill scaffolds **every** template the CLI offers, including UI-bundle web apps (React, Angular, Vue), so creating a project never requires installing another plugin. Once the project exists, the `experience-ui-bundle-*` skills own *building it out* (pages, components, deploy).

Read the template set **live from the CLI**, never from a baked-in list, because Salesforce adds templates over time:

```bash
sf template generate project --help
```

Parse the `-t, --template=<option>` line's `<options: a|b|c|…>` list; those names are the authoritative set. Fallback, only if the live list cannot be read: `standard`, `empty`, `analytics`, `agent`, `reactinternalapp`, `reactexternalapp`, `angularinternalapp`, `angularexternalapp`. Vue (`vueinternalapp`) is left out of the fallback because stable CLI builds reject it; newer builds list it in the live parse. If the parse failed and the user wants Vue, say the template list could not be read and ask them to update the Salesforce CLI. UI-bundle templates are named `<framework><audience>app`; internal = employee-facing, already authenticated; external = customer/partner-facing with login, registration, and profile.

**Intent shortcut first.** Take it **only when the request resolves to exactly one template in the live list.** Otherwise use the picker; never guess. Resolve `{template}` directly when:

- The request **names a non-UI template**: "empty/minimal project" → `empty`; "analytics project" → `analytics`; "agent project" → `agent`; "standard project" → `standard`.
- The request is a **UI-bundle app where the live list leaves one match for the framework and audience given**: "internal React app" → `reactinternalapp`; "customer-facing Angular portal" → `angularexternalapp`; "Vue app" → `vueinternalapp` (the only Vue template, so no audience to ask).

**A description of the app is NOT a template name.** "A personal todo app", "an inventory tracker", "a CRM for my team" say *what* to build, not *which* template, so they do not qualify for the shortcut. Do not infer `standard` (or any template) from the app's purpose; `standard` being the picker's default does not license skipping the picker.

Everything else goes to the picker, including:
- a bare "new project" with no template named (the picker defaults to **Standard**),
- a described app with no template or framework named, and
- a **partially specified UI app**, such as "create a React app" with no audience. Never assume an audience; skip the top-level picker and ask only the missing piece in the follow-up below.

**Otherwise ask one `AskUserQuestion` — "What kind of project?"** (single-select, four options). `AskUserQuestion` caps at four choices, so the picker shows the four most-requested kinds; **`empty` is deliberately omitted** and reached only via the shortcut.

- **Standard** → `standard` (default): general-purpose `force-app` metadata project (Apex, LWC, objects, flows).
- **Agentforce agent** → `agent`: ships a sample Local Info Agent.
- **CRM Analytics** → `analytics`: adds the `waveTemplates` directory.
- **UI web app (React / Angular / Vue)** → a UI-bundle starter. Ask a follow-up `AskUserQuestion` ("Which UI framework?") with one option per framework in the live list. Then, only if the chosen framework has both `internal` and `external` templates, ask "Who is the audience?" (internal or external). A framework with a single template needs no audience question.

The resolved template is `{template}`, which feeds Step 3. When the live CLI adds a template, it surfaces through the live parse; only add a keyword to the intent shortcut if it is a rarely-picked non-UI template.

## Step 2: Choose a Project Name

Prompt the user for a project name. It becomes the new directory name **and is interpolated into the shell commands below**, so it MUST be strictly validated before any command uses it — never pass a raw name through.

**Validate, then reject-and-re-prompt.** Run this check on the candidate before it is used anywhere. Pass the candidate inside single quotes, exactly as typed. The regexes live in the command, so the check is deterministic:

```bash
node -e 'const [kind, value] = process.argv.slice(1); const re = {name: /^[A-Za-z0-9][A-Za-z0-9_-]*$/, namespace: /^(?=.{1,15}$)[A-Za-z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$/, package: /^[A-Za-z0-9_][A-Za-z0-9_-]*(\/[A-Za-z0-9_][A-Za-z0-9_-]*)*$/, apiversion: /^[0-9]+\.0$/}[kind]; process.exit(re.test(value) ? 0 : 1)' name '{candidate}' && echo valid || echo invalid
```

Use `name` as the kind for the project name. Step 3 reuses this same command with `namespace`, `package`, or `apiversion` as the kind. Reject without running the command if the candidate contains a single quote or a line break, because it cannot be quoted safely. If the check prints `invalid`, explain why (spaces, path separators, a leading `.` or `..`, or shell metacharacters such as `; | & $ > < ( ) \` "`) and ask again. A name like `proj;rm -rf ~` never reaches a shell command. The commands below also quote `"{name}"` as a backstop, but the check is the guard.

## Step 3: Generate the Project

**Verify before generating** — do not run the command until you can check both:

- ☐ The `{name}` about to be interpolated is the **exact value that printed `valid` from the Step 2 check** (kind `name`) — not a raw, re-edited, or user-echoed string. If it never passed validation, go back to Step 2.
- ☐ `{template}` is one of the CLI's advertised options from Step 1.
- ☐ No `{name}/` directory already exists in the current working directory — the generate would fail (or risk clobbering an existing project) if it does. Check with `[ -e "{name}" ]` first; if it exists, don't overwrite: tell the user and go back to Step 2 for a different name.

Run in the current working directory:

```bash
sf template generate project -t {template} -n "{name}"
```

This creates a new `{name}/` directory under the current working directory, with `sfdx-project.json` at the root the session will relocate into. (`sf project generate` is a deprecated alias; use `template generate project`.)

**Optional flags — add only when the user asks, never prompt for them:**

| Flag | Use |
|---|---|
| `--lwc-language typescript` | Author Lightning web components in TypeScript (default `javascript`) |
| `-s, --namespace <ns>` | Namespace for the project and connected scratch orgs |
| `-p, --default-package-dir <dir>` | Rename the default package directory (default `force-app`) |
| `-x, --manifest` | Also generate a `package.xml` for change-set-based development |
| `--api-version <NN.0>` | Set `sourceApiVersion` in `sfdx-project.json` |

Run the Step 2 check on each flag value before interpolating it, with the matching kind: `namespace` for `--namespace`, `package` for `--default-package-dir` (it accepts a subpath such as `src/main`, not only a single name), and `apiversion` for `--api-version`. Drop a flag whose value prints `invalid`, or ask the user for a corrected value. Never pass `-d, --output-dir`: the project must land at `./{name}` for `/cd {name}` to work.

**UI-bundle templates carry npm dependencies. Do NOT install them for the user.** A UI-bundle starter (`react*`, `angular*`, `vue*`) can't preview or build until its dependencies are installed, and first-run install takes minutes, so it's the developer's explicit call. Do **not** run `npm install` yourself. Tell the user in the closing message that dependencies aren't installed yet and hand them the commands.

## Step 4: Relocate the Session Into the New Project

Modern Claude Code (v2.1.169+) can move the current session into the new directory in place — no new terminal, no relaunch, conversation history preserved. Tell the user to run:

```text
/cd {name}
```

This relocates the session: the new directory's `CLAUDE.md` is loaded, project storage moves there (so `--resume`/`--continue` find it), and the cwd becomes the project root, so all remaining `sf` commands run as plain `sf ...` with no path prefix.

`/cd` is a client-side move: it fires no hook and gives you no turn, so the session goes **quiet** the instant they run it — expected, not a hang. But it also means the message in which you hand them `/cd` is your last word until they speak again, so that message MUST end with an affordance telling them how to resume. Close it with a line like:

> Once you're in, just say **"what's next"** (or "connect an org") and I'll pick up from there.

Saying "what's next" re-engages this session and paints the journey nudge, which points at the next step (authenticating an org). Never imply the session will continue on its own after `/cd` — it won't.

When they re-engage, confirm the move in one short line (e.g. "You're in {name} now.") and continue to Step 5. Do **not** run `sf-context detect` or `check-tools` to "re-surface" the banner: `detect` invoked as a tool prints the raw hook JSON (not a rendered banner), and the plugin already surfaces the banner on its own — it shows the HEADLESS identity once per session (at the user's first Salesforce ask, at session start, or on their first orientation question), and paints the journey nudge whenever they ask "where am I" / "what's next". A dev-environment health check is available on demand via `/salesforce-development:setup`.

**Fallback for older Claude Code (before v2.1.169):** `/cd` reports `Unknown command`. In that case the user must relaunch in the new directory instead:

```bash
cd "{name}" && claude
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

For a **UI-bundle** project, the scaffold is done but its npm dependencies are **not installed**. Tell the user the app needs them before it can preview or build, and hand them the template's own getting-started commands to run from inside the project when they're ready:

```bash
npm install                # project root tooling
npm run sf-project-setup   # installs and builds the UI bundle, then starts the dev server
```

Then add a line pointing at the follow-on skills. **Make the pointer framework-specific**, because the front-end build skill is React-only:

- **React** (`react*`) → `experience-ui-bundle-frontend-generate` builds pages and components (React/TypeScript-specific: shadcn/ui, react-router, `appLayout.tsx`/`routes.tsx`), and `experience-ui-bundle-deploy` ships the app.
- **Angular** (`angular*`) and **Vue** (`vue*`) → there is **no** front-end skill for them. Do **NOT** point at `experience-ui-bundle-frontend-generate`: it requires a React `appLayout.tsx`/`routes.tsx`/`src/components/ui/` and rejects other bundles. Build from the starter's own `README`; `experience-ui-bundle-deploy` still ships it (deploy is framework-agnostic).

Those skills live in the `experience-react` plugin. If the user doesn't have it, that only affects *building* the app; the project they have is complete and deployable as-is.

## Rules

- Run the steps in order; confirm before any environment-changing action (login, set-default, enable tracking).
- Do NOT create or copy a `.mcp.json` into the new project. The plugin's config uses `${CLAUDE_PLUGIN_ROOT}`, which does not resolve in a project-level file.
- Prefer `/cd {name}` to relocate the session in place (Claude Code v2.1.169+). A skill can't do it on the user's behalf, so instruct the user to run it. Fall back to `cd "{name}" && claude` only when `/cd` reports `Unknown command`.
- The message that hands the user `/cd {name}` is your last turn until they speak again (`/cd` fires no hook), so it MUST end with a resume affordance, e.g. 'once you're in, just say "what's next".' Never promise the session will continue on its own after `/cd`.
- After `/cd`, do NOT run `sf-context detect` or `check-tools` to "show" the banner: `detect` as a tool prints raw JSON, and the plugin surfaces the banner itself. Confirm the move in one line and continue. Health is on demand via `/salesforce-development:setup`.
- For sandbox login, `--instance-url https://test.salesforce.com` is REQUIRED (the CLI default points at production).
- NEVER store or display access tokens.
- The project name is user input that flows into shell commands. Run the Step 2 check (kind `name`) and reject-and-re-prompt BEFORE using it, and quote `"{name}"` in every command. Validation is the guard, quoting is the backstop.
- For an EXISTING project that needs tooling validated, use `platform-environment-validate` (or `/salesforce-development:setup`); for org auth on an existing project, use `/salesforce-development:login`.
- This skill owns **greenfield project creation** for every template, UI-bundle included: scaffold, relocate, connect an org, enable tracking. Do NOT hand the initial scaffold to another plugin, and never run `npm install` for the user. The one boundary: when the UI-bundle scaffold is just a **composed step** of building out a UI-bundle app (driven by `experience-ui-bundle-app-coordinate`, no full project setup wanted), that is `experience-ui-bundle-project-generate`'s job. Building or editing an existing UI-bundle app is always theirs.
