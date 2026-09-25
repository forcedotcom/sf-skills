---
name: experience-ui-bundle-project-generate
description: "Generates a minimal, ready-to-develop SFDX starter project from template instead of hand-scaffolding files. Use this skill when starting a brand-new Salesforce UI bundle app (React or Angular) and the initial project must be scaffolded — trigger phrases include create, start, or scaffold a new UI bundle app, generate a starter project, or use a prebuilt/starter template. DO NOT TRIGGER when: editing, styling, or adding pages or components to an EXISTING app (use experience-ui-bundle-frontend-generate); configuring ui-bundle.json or metadata files (use experience-ui-bundle-metadata-generate); deploying to an org (use experience-ui-bundle-deploy); when the user explicitly says they want to hand-scaffold from scratch; or when creating a brand-new standalone Salesforce project that also needs full setup — relocating the session, connecting an org, setting the default, and enabling source tracking (use dx-project-create in the salesforce-development plugin)."
metadata:
  version: "1.2"
  domains: ["Experience"]
  relatedSkills:
    - "experience-ui-bundle-app-coordinate"
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-metadata-generate"
    - "experience-ui-bundle-salesforce-data-access"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Using a UI Bundle Template

Before building a Salesforce UI bundle app from scratch, offer the user a **prebuilt starter template**. The Salesforce CLI generates these — a complete, deployable SFDX project (UI bundle + toolchain + an `npm run setup` automation) — in one command. Starting from a starter is faster and less error-prone than hand-scaffolding.

The CLI command is `sf template generate project`.

## Step 1: Offer the choice

**Determine the framework.** It is normally already decided by the calling context — either passed down by the root/coordinator skill that invoked this one, or stated in the user's request. Use that.

The frameworks this skill supports are exactly the reference files under `<SKILL_DIR>/references/`, each named `<framework>-project-generate.md` (so `react` → `<SKILL_DIR>/references/react-project-generate.md`). This is the single source of truth — adding a framework means adding a reference file, nothing here changes.

- **If the framework is known** — open `<SKILL_DIR>/references/<framework>-project-generate.md`.
- **If it is unknown** (a standalone run where nobody said which) — list `<SKILL_DIR>/references/`, derive the supported set by stripping the `-project-generate.md` suffix from each filename, and ask the user to pick one of those. If the user names a framework with no matching reference file, it is not supported here — hand off to `experience-ui-bundle-app-coordinate` to scaffold from scratch.

Each reference lists that framework's `--template` flags and what each starter contains. Pick the one that fits the user's audience (internal vs. external).

**If the user prefers to start from scratch** (or neither template fits), stop here and let `experience-ui-bundle-app-coordinate` scaffold a new project. This skill is opt-in — do not force a template.

Once the user picks, carry the chosen `--template` flag into Step 2.

## Step 2: Generate the project into the target root

The project contents must land **directly at the target root `$DEST`** — so `sfdx-project.json` sits at `$DEST/sfdx-project.json`, with no extra wrapper subfolder. `sf template generate project` always nests its output under a `--name` subfolder, so `<SKILL_DIR>/scripts/generate-project.mjs` generates into `$DEST`, flattens the subfolder's contents up into `$DEST` (overwriting anything already there on conflict), and removes the now-empty subfolder — all through Node's `fs`/`child_process` APIs, so it runs the same way on Windows cmd/PowerShell as it does on macOS/Linux/Git Bash.

- `<SKILL_DIR>` = the absolute path to **this skill's own directory** — the folder containing this `SKILL.md`; resolve it from the skill path in context
- **`$NAME`** — the project name (alphanumerical only — no spaces, hyphens, underscores, or special characters). Ask the user for it. It also names the UI bundle, so it shows up inside the project.
- **`$DEST`** — the target root directory the contents land in (use `.` for the current directory).
- **`$TEMPLATE`** — the `--template` flag value from the framework reference chosen in Step 1 (e.g. `reactinternalapp`).

Run the script with the actual, literal values substituted for `$NAME`, `$DEST`, and `$TEMPLATE` — do not use shell variable assignment/interpolation (`NAME=...` / `$NAME` / `%NAME%` / `$env:NAME`) since that syntax differs across bash, cmd, and PowerShell and this command must work in all three:

```sh
node "<SKILL_DIR>/scripts/generate-project.mjs" "<name>" "<dest>" "<template>"
```

The script prints `OK: project root landed at <dest> (...)` and exits 0 on success. It exits non-zero (with a clear stderr message) if `sf template generate project` fails, the generated project has no `sfdx-project.json`, or the flatten didn't leave a valid project root — stop and surface the failure rather than continuing.

`sfdx-project.json` must sit at `$DEST/sfdx-project.json`. The project also contains `package.json`, `force-app/main/default/uiBundles/$NAME/` (the UI bundle), `scripts/`, `config/`, and `README.md`. See the framework reference from Step 1 for the specific bundle contents.

## Step 3: Install dependencies (you do this — do NOT hand off uninstalled)

If the generated project ships **without** `node_modules`, **install dependencies yourself before handing the project back** — a fresh template is not runnable (preview/build/lint all fail) until deps are present. The user should receive a ready-to-develop project.

There are **multiple** `package.json` files, each needing its own install:
- the **project root** (`$DEST/package.json`), and
- the **UI bundle** dir under `$DEST/force-app/main/default/uiBundles/$NAME/` — this holds the toolchain the preview server loads, so it must have `node_modules` too.

`<SKILL_DIR>/scripts/install-deps.mjs` runs `npm install` for the root and for every UI bundle that has a `package.json` (via Node's `child_process` with an explicit `cwd` — no `cd &&` shell chaining), then verifies `node_modules` landed everywhere it installed:

```sh
node "<SKILL_DIR>/scripts/install-deps.mjs" "<dest>"
```

Substitute the literal `$DEST` value from Step 2 for `<dest>`. The script prints `OK: all dependencies installed.` and exits 0 on success; it exits non-zero with a listed summary of which install(s) failed otherwise. First-run install of the bundle is the heavy step; expect a short wait. If an install fails, surface it — don't hand off a half-installed project.

## Step 4: Confirm and hand off

`install-deps.mjs` already prints a verification summary (root + each UI bundle's `node_modules`) as part of Step 3. To look around the generated project yourself, use your own file-listing/read tools rather than a shell `ls` — that works identically regardless of the underlying OS shell.

The project is now ready to develop and deploy. If there's a `README.md` in the template, take a look at it to see if there is any extra step or guidance for the user.

From here, continue development with the other ui-bundle skills (`experience-ui-bundle-frontend-generate`, `experience-ui-bundle-salesforce-data-access`, `experience-ui-bundle-deploy`, etc.) against the now-scaffolded project — scaffolding and dependency install are already done.

## Notes

- The starters are **minimal** — no seeded sample data or custom objects. Build the rest with the other ui-bundle skills.
- These templates use the `uiBundles` metadata convention. The UI bundle directory and meta XML are named after the project name you pass to `--name`.
- `sf template generate project --help` lists all available templates if the flag names ever change.
