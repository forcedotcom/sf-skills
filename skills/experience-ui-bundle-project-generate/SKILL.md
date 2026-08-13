---
name: experience-ui-bundle-project-generate
description: "Generates a minimal, ready-to-develop SFDX starter project from template instead of hand-scaffolding files. Use this skill when starting a brand-new Salesforce UI bundle app (any supported frontend framework) and the initial project must be scaffolded — trigger phrases include create, start, or scaffold a new UI bundle app, generate a starter project, or use a prebuilt/starter template. DO NOT TRIGGER when: editing, styling, or adding pages or components to an EXISTING app (use experience-ui-bundle-frontend-generate); configuring ui-bundle.json or metadata files (use experience-ui-bundle-metadata-generate); deploying to an org (use experience-ui-bundle-deploy); or when the user explicitly says they want to hand-scaffold from scratch."
metadata:
  version: "1.2"
  relatedSkills:
    - "experience-ui-bundle-app-coordinate"
    - "experience-ui-bundle-metadata-generate"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-salesforce-data-access"
    - "experience-ui-bundle-deploy"
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

The frameworks this skill supports are exactly the reference files under [`references/`](references/), each named `<framework>-project-generate.md` (so `react` → `references/react-project-generate.md`). This is the single source of truth — adding a framework means adding a reference file, nothing here changes.

- **If the framework is known** — open `references/<framework>-project-generate.md`.
- **If it is unknown** (a standalone run where nobody said which) — list `references/`, derive the supported set by stripping the `-project-generate.md` suffix from each filename, and ask the user to pick one of those. If the user names a framework with no matching reference file, it is not supported here — hand off to `experience-ui-bundle-app-coordinate` to scaffold from scratch.

Each reference lists that framework's `--template` flags and what each starter contains. Pick the one that fits the user's audience (internal vs. external).

**If the user prefers to start from scratch** (or neither template fits), stop here and let `experience-ui-bundle-app-coordinate` scaffold a new project. This skill is opt-in — do not force a template.

Once the user picks, carry the chosen `--template` flag into Step 2.

## Step 2: Generate the project into the target root

The project contents must land **directly at the target root `$DEST`** — so `sfdx-project.json` sits at `$DEST/sfdx-project.json`, with no extra wrapper subfolder. `sf template generate project` always nests its output under a `--name` subfolder, so generate into the `$DEST` dir, then move the contents from the subfolder up into `$DEST`, overwriting anything already there on conflict. Remove the empty subfolder at the end.

- `<SKILL_DIR>` = the absolute path to **this skill's own directory** — the folder containing this `SKILL.md`; resolve it from the skill path in context
- **`$NAME`** — the project name (alphanumerical only — no spaces, hyphens, underscores, or special characters). Ask the user for it. It also names the UI bundle, so it shows up inside the project.
- **`$DEST`** — the target root directory the contents land in (use `.` for the current directory).

```sh
NAME=MyApp   # project name the user chose; also names the UI bundle
DEST=.       # target root directory (the contents land directly here, no NAME/ wrapper)

# the --template flag from the framework reference chosen in Step 1
TEMPLATE=reactinternalapp   # example placeholder — replace with the flag from your Step-1 reference

mkdir -p "$DEST"
sf template generate project --name "$NAME" --template "$TEMPLATE" --output-dir "$DEST"

# Flatten the generated $DEST/$NAME contents up into $DEST (see <SKILL_DIR>/scripts/flatten-project.mjs).
# Use the absolute skill-dir path — a relative ./scripts/ would resolve against $DEST, not the skill.
node "<SKILL_DIR>/scripts/flatten-project.mjs" "$DEST/$NAME" "$DEST"
rm -rf "$DEST/$NAME"
```

> `<SKILL_DIR>/scripts/flatten-project.mjs` moves every generated entry (incl. dotfiles) into `$DEST`, overwriting any existing file/dir of any type on conflict while preserving unrelated files the user already had in `$DEST`. The per-entry `rmSync` + `renameSync` is what guarantees the template's files win on conflict (including a file-vs-directory type mismatch).

### Verify

After generation, confirm the contents landed at the root (not in a `$NAME/` subfolder):

```sh
test -f "$DEST/sfdx-project.json" && echo "OK: project root landed" || echo "FAILED"
```

`sfdx-project.json` must sit at `$DEST/sfdx-project.json`. The project also contains `package.json`, `force-app/main/default/uiBundles/$NAME/` (the UI bundle), `scripts/`, `config/`, and `README.md`. See the framework reference from Step 1 for the specific bundle contents. If `sfdx-project.json` is missing or is one level down in `$DEST/$NAME/`, the flatten did not run — re-check before continuing.

## Step 3: Install dependencies (you do this — do NOT hand off uninstalled)

If the generated project ships **without** `node_modules`, **install dependencies yourself before handing the project back** — a fresh template is not runnable (preview/build/lint all fail) until deps are present. The user should receive a ready-to-develop project.

There are **multiple** `package.json` files, each needing its own install:
- the **project root** (`$DEST/package.json`), and
- the **UI bundle** dir under `$DEST/force-app/main/default/uiBundles/$NAME/` — this holds the toolchain the preview server loads, so it must have `node_modules` too.

```sh
# 1. project root ($DEST was set in Step 2)
( cd "$DEST" && npm install )

# 2. each UI bundle
for b in "$DEST"/force-app/main/default/uiBundles/*/; do
  [ -f "$b/package.json" ] && ( cd "$b" && npm install )
done
```

> First-run install of the bundle is the heavy step; expect a short wait. If an install fails, surface it — don't hand off a half-installed project.

## Step 4: Confirm and hand off

Verify the project landed and is installed:

```sh
ls "$DEST" # sfdx-project.json, package.json, force-app/, scripts/, README.md ...
ls "$DEST"/force-app/main/default/uiBundles/*/node_modules >/dev/null && echo "bundle deps installed"
```

The project is now ready to develop and deploy. If there's a `README.md` in the template, take a look at it to see if there is any extra step or guidance for the user.

From here, continue development with the other ui-bundle skills (`experience-ui-bundle-frontend-generate`, `experience-ui-bundle-salesforce-data-access`, `experience-ui-bundle-deploy`, etc.) against the now-scaffolded project — scaffolding and dependency install are already done.

## Notes

- The starters are **minimal** — no seeded sample data or custom objects. Build the rest with the other ui-bundle skills.
- These templates use the `uiBundles` metadata convention. The UI bundle directory and meta XML are named after the project name you pass to `--name`.
- `sf template generate project --help` lists all available templates if the flag names ever change.
