# Scratch Org Creation

Workflow for **creating** a scratch org with `sf` from any source (edition, definition file,
snapshot, org shape), including AUTO MODE, STATE A/B resolution, batch create, and definition-file
authoring. For list / display / resume / delete, see `scratch-org-operations.md`.

---

## Security posture — pure pass-through (read first)

The skill relays every input to `sf` **unchanged** and surfaces the CLI's `--json` result —
success or error — **as-is**. It does not pre-validate fields, does not normalize or translate
field names, and does not add or strip error text; the CLI already frames its own output.

The one rule the skill enforces is about its **own documentation**: fields not listed in
`definition_file_options.md` are simply relayed to the CLI unchanged, and if the CLI doesn't
accept a field it reports the error itself. When authoring a definition file, write only the
documented fields (see `definition_file_options.md`); if a user's existing file contains fields
this reference doesn't document, relay it unchanged — never reproduce those lines into a
committed artifact.

The skill's own docs/examples never claim a feature is "not enabled" or that a permission is
missing — that framing is the platform's job, delivered through the CLI's own error output.

---

## Creation sources (publicly documented)

A scratch org is created from exactly one of these sources:

| Source | Def-file key | CLI flag |
|--------|--------------|----------|
| Edition | `edition` | `--edition <value>` |
| Org shape | `sourceOrg` | `--source-org <source org id>` |
| Snapshot | `snapshot` | `--snapshot <name>` |

**Strict single-source across distinct source *types*.** A request must resolve to exactly ONE
source type (edition vs shape vs snapshot). If two **distinct** types are implied at once (e.g.
a definition file sets `snapshot` and the user also asks for a shape) → **stop and ask** which
one. This is NOT the flag-override case: a CLI flag overriding a *same-dimension* definition-file
value (`--edition enterprise` over the file's `edition: "Developer"`, or `--snapshot X` over the
file's snapshot) is normal, documented behavior — allow it (see `definition_file_options.md`
"CLI Flag Overrides").

---

## Create — resolve the environment before prompting

### AUTO MODE — zero-prompt fast path

When the environment is **unambiguous**, ask nothing and create immediately. Unambiguous means
ALL of:

- **In an SF project** — `sfdx-project.json` present, and
- **Exactly one** `config/*scratch-def.json`, and
- **A resolvable Dev Hub** — a default `target-dev-hub` is set, OR exactly one Dev Hub is
  authenticated.

In that case use the single definition file, the resolved Dev Hub, an auto-derived alias, and
the CLI defaults — no project menu, no definition-file picker, no Dev Hub prompt, no alias
prompt. This also covers a batch request ("create 5 scratch orgs" — see **Batch create** below).

If ANY condition is ambiguous (0 or ≥2 definition files, no project, no resolvable Dev Hub, or a
conflicting explicit source), fall through to the guided flow below. AUTO MODE is a shortcut over
the same resolution logic — it only skips prompts when exactly one answer is possible.

### Detect entry state

A project is NOT required to create an org — the hard requirements are a creation source and a
resolvable Dev Hub. But the entry state decides how the source is resolved. Detect it:

```bash
[ -f sfdx-project.json ] && echo STATE_A || echo STATE_B
```

> **Dev Hub is directory-scoped — resolve it to a concrete value first.** The default
> `target-dev-hub` is read from the current directory's config, so `sf config get target-dev-hub`
> can return empty after you `cd` into a project directory even when a hub is authenticated.
> Resolve the hub to an actual username/alias **before** changing directories (per Step 2 of
> SKILL.md: explicit → `sf config get` → the single `isDevHub: true` org from `sf org list`) and
> pass that value explicitly via `--target-dev-hub` on every `create` command. Never fabricate a
> placeholder hub name when resolution comes back empty — advise `sf org login web
> --set-default-dev-hub` and stop.

**STATE A — inside an SF project.** Enumerate definition files by the conventional name:

```bash
ls config/*scratch-def.json 2>/dev/null
```

- **0 files:** if the user wants features/settings → author one (see **Authoring a definition
  file** below); otherwise default to `--edition developer`.
- **1 file:** use it (today's behavior).
- **many files:** **ask which one** — never silently pick. Multiple scratch-def files is a
  supported, common pattern.

> **Assumption:** auto-detect matches the convention `config/*scratch-def.json` only. A
> definition file can have any name (`--definition-file` accepts any `.json`) — if the user's file
> is off-convention (e.g. `config/dev.json`), they **name it explicitly** and that path always
> works; only silent auto-detect is convention-scoped.

**STATE B — NOT in an SF project.** No `config/`, so no auto-detect is possible. **Always guide —
never silently create a throwaway.** Create works with no project, so this is guidance, not a
gate; present a short plain-language choice and act on the answer:

1. **Point to an existing SF project** — the user gives a path to a directory containing
   `sfdx-project.json`; operate there (= STATE A: unlocks `config/` auto-detect, def-file
   authoring, source tracking).
2. **Scaffold a new project** — **ask where** (target directory, default: current dir) and a
   project name, then:

   ```bash
   sf template generate project --name <name>
   ```

   (`sf project generate` is deprecated.) Then = STATE A. Never scaffold into an assumed path —
   confirm location and name first.
3. **Create a throwaway org right here** — no project. Then **guide the creation source** — ask
   which kind: edition (`developer`/`enterprise`/`group`/`professional`), shape
   (`--source-org <source org id>`), or snapshot (`--snapshot <name>`). One source only.
   - **Simple case → bare command:** for a plain edition/shape/snapshot with no custom config,
     run the command directly — no file needed.
   - **Features/settings wanted → author a STANDALONE definition file:** the fix is a *file*, not
     a project. Author a `scratch-def.json` **inside the current working directory** (a relative
     path such as `scratch-def.json` or `config/scratch-def.json`) and create with
     `--definition-file <relative path>`. Never construct an absolute path or write outside the
     cwd; if the user wants it elsewhere, have them provide the existing path explicitly. This
     carries nested `settings` (which cannot be CLI flags) without scaffolding a project. Only
     recommend stepping up to option 1/2 when the user also wants source tracking or a
     saved/tracked workspace.

Frame it plainly (the user may know nothing about Salesforce): options 1–2 are for "keep working
on this," option 3 for "just need a quick org." Features/settings do NOT force a project — a
standalone definition file (option 3) carries them fine.

### Selection order (when nothing conflicts)

Explicit user-named source wins → else (STATE A only) auto-detect `config/*scratch-def.json` →
else, **STATE A only**, default `--edition developer`. STATE B never falls through to a silent
default — it always presents the guided choice above.

### Dev Hub selection

Resolve the hub **once** to a concrete username/alias and pass it explicitly via `--target-dev-hub`.
Precedence: user-specified hub > non-empty `result[0].value` from `sf config get target-dev-hub
--json` > the single authenticated Dev Hub. Use the default `target-dev-hub` **silently** — do NOT
confirm or second-guess it just because multiple Dev Hubs are authenticated; the user overrides by
naming a hub.

For the third step, run **this exact command** — do NOT hand-write your own `sf org list` filter. A
Dev Hub can appear in **any** bucket (`devHubs`, `nonScratchOrgs`, `other`, `sandboxes`,
`scratchOrgs`); a filter that inspects only one bucket (e.g. only `.other[]`) silently misses the
hub and makes you conclude none exists — the top eval failure:

```bash
sf org list --json | jq -r '[.result.devHubs[]?, .result.nonScratchOrgs[]?, .result.other[]?, .result.sandboxes[]?, .result.scratchOrgs[]?] | map(select(.isDevHub == true).username) | unique | .[]'
```

Exactly one username printed → use it. Zero → no hub authenticated: **do NOT run `sf org create`
at all** (there is nothing to pass to `--target-dev-hub`); advise `sf org login web
--set-default-dev-hub` and stop. Two or more → list them and ask the user to pick — don't dead-end
with an error. **Never** fabricate a placeholder alias (e.g. `eval-target`, `my-dev-hub`, `DevHub`),
which the CLI rejects with `NotADevHubError`, and never run create with no `--target-dev-hub` flag,
which yields `NoDefaultDevHubError`. A command that prints nothing means no Dev Hub exists in this
environment — that is a hard stop, not a signal to invent a name. Note the default `target-dev-hub`
may be directory-scoped in some setups (empty after a `cd`), so this all-bucket `sf org list` check
— which is not directory-scoped — is the reliable fallback.

### Alias

Strongly recommended; **auto-derive if absent** so the org always has a friendly handle for later
list/display/delete. If the user gives an alias, use it; otherwise derive one and tell the user
what was chosen. Not a blocking prompt.

Slugification and the collision guard are **deterministic** — do NOT re-implement the recipe by
hand each run (it drifts: `my-app` vs `my_app` vs `myapp`). Run the shipped helper, which encodes
both steps and always yields the same alias for the same inputs and existing-alias set:

```bash
# Single alias (slugified + collision-guarded)
bash assets/derive-alias.sh "<base name>"
```

- **Base name:** the `sfdx-project.json` `default: true` package directory name (STATE A; if none
  is marked default, use `packageDirectories[0]`), or the cwd basename (STATE B), or the
  user-supplied alias. The script slugifies it (lowercase, non-alphanumerics → hyphens). The same
  slug feeds the authored definition file's `<purpose>-scratch-def.json` name. If the base
  slugifies to empty (script exits non-zero), ask the user for an explicit alias rather than
  invent one.
- **Collision guard (built in):** the script checks `sf org list --json` and, if the alias is
  already taken, appends `-2`, `-3`, … until it is free. This matters because the CLI does **not**
  reject a reused alias — it silently *re-points* the alias to the new org (the old org loses it).

### Build and execute

```bash
# Definition file
sf org create scratch --definition-file <path> --target-dev-hub <alias> --alias <name> --json

# Edition only
sf org create scratch --edition developer --target-dev-hub <alias> --alias <name> --json

# From snapshot
sf org create scratch --snapshot <snapshot-name> --target-dev-hub <alias> --alias <name> --json

# From org shape
sf org create scratch --source-org <source-org-id> --target-dev-hub <alias> --alias <name> --json
```

> `--source-org` takes the 15- or 18-character **source org ID** — the ID of the org the shape was
> captured from (a `00D…` org ID), NOT the `3SR…` shape record ID shown by `sf org list shape`.
> Pass the ID the user gives you through unchanged; on a CLI rejection (`InvalidIdLengthError`,
> `InvalidPrefixError`) surface the error verbatim and stop — do not truncate, reformat, guess, or
> retry with a different ID.

Common optional flags:

- `--duration-days <days>` — expiration (max 30; CLI default 7)
- `--set-default` — make this the default org
- `--no-track-source` — disable source tracking (CI/CD)
- `--wait <minutes>` — number of minutes to wait for the org to be ready
- `--async` — return immediately; resume later

**This is a BLOCKING command.** It waits until the org is fully created (or times out). When
it returns success with `username` and `orgId`, the org is **ready to use** — do NOT poll with
`sf org list` waiting for it to become ready; the command already waited. (The one `sf org list`
call in the report step below is for artifact collection, **not** polling.) Only use `--async`
to check status later with `sf org resume scratch`.

### Batch create — "create N scratch orgs"

There is **no native count flag**. Loop the create command N times, one distinct alias per org.
Generate all N collision-guarded aliases up front with the helper's count argument:

```bash
# N distinct aliases: <base>-1 … <base>-N, each collision-guarded
bash assets/derive-alias.sh "<base name>" <N>
```

Base = user-given, else the derived handle. Each emitted alias is already collision-guarded (an
existing `<base>-2` bumps to `<base>-2-2`), so pass one per create call.
Never reuse one alias across the loop — the CLI would silently re-point each org onto the last.
Each call is blocking. Report a per-org summary and write one artifact per org. If the Dev Hub
hits its active-scratch-org limit partway through, surface the CLI's own error unchanged and
report which orgs already succeeded — do not silently stop or retry.

### Report the result

After creation, run `sf org list --json` **once** for artifact collection (this is not polling),
find the entry whose `username` matches the creation result, and report:

- Alias, Username, Org ID
- Expiration and default status as facts, e.g. *"Created scratch org `X`, expires in 7 days (not
  set as default)."*

### Async / timeout → resume

On `--async` or a timeout (**exit code 69**), the CLI prints a resume command with a job/request
ID. Proactively capture it and surface the exact command so the user is never stranded (see the
Resume section in `scratch-org-operations.md`):

```bash
sf org resume scratch --job-id <request-id> --json
```

---

## Authoring a definition file (seed-then-modify)

When features/settings are requested and no suitable definition file exists (STATE A into
`config/`, or STATE B option 3 as a standalone file), do NOT synthesize JSON from scratch —
**start from a seed and modify it**, then let the user review:

1. **Seed source (priority):** (1) an existing definition file in `config/` (copy as base), else
   (2) the one `sf template generate project` scaffolds (`config/project-scratch-def.json`), else
   (3) the minimal seed shipped with this skill: `assets/scratch-def.seed.json`.
2. **Modify** per the requested features/settings using the schema in
   `definition_file_options.md`. The features/settings space is open-ended — compose whatever the
   user asks for generically; do not pattern-match a fixed catalog. Nested `settings` **cannot**
   be CLI flags, so any such request → a definition file (standalone or in `config/`).
3. **Write location:** STATE A → `config/<purpose>-scratch-def.json`; STATE B option 3 → a
   relative path inside the cwd (e.g. `scratch-def.json` or `config/scratch-def.json`), then
   create with `--definition-file <relative path>`. Never construct an absolute path or write
   outside the cwd.
4. **No-clobber:** always write a **new purpose-named** file; never overwrite an existing file
   (especially `config/project-scratch-def.json`) without explicit confirmation.
5. **Interactive:** show the result and let the user accept / edit / request changes.
   **Non-interactive (eval/CI):** author the file AND proceed to create without waiting for edit
   confirmation.

Author only documented fields (`edition`, `features`, `settings`, `snapshot`, `sourceOrg`,
`orgName`, `adminEmail`, `description`, `hasSampleData`, `release`). Include `orgName` whenever
the skill authors a file. A bare `--edition` create with no definition file does not need a
user-supplied name — the CLI auto-populates the org name.

---

## Additional resources

- `scratch-org-operations.md` — list, display, resume, delete
- `definition_file_options.md` — features, settings, and definition-file schema
- `edition_types.md` — edition selection and the CLI-flag-vs-definition-file format distinction
- `snapshot_usage.md` — using snapshots in definition files and post-snapshot workflow
