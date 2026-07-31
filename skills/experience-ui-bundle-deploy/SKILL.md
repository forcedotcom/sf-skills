---
name: experience-ui-bundle-deploy
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves deploying, pushing to an org, or post-deploy org setup. Use this skill to deploy a UI bundle app to a Salesforce org and run the full ordered setup: org authentication, pre-deploy build, metadata deploy, permission-set assignment, role assignment, Experience Cloud self-registration, seed-data import, and GraphQL schema fetch plus codegen. Activate when a uiBundles/ project also has files like *.network-meta.xml, org-setup.config.json, a data-plan.json in the data/ dir, or sfdx-project.json and the user mentions deploying, pushing, org setup, or post-deploy tasks. DO NOT TRIGGER when: creating a new UI bundle project from scratch (use experience-ui-bundle-project-generate); styling or editing pages in an existing app without deploying (use experience-ui-bundle-frontend-generate); adding a specific feature such as auth, search, or file upload without deploying (use the matching experience-ui-bundle-*-generate skill)."
metadata:
  version: "1.1"
  relatedSkills:
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-project-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  minApiVersion: "66.0"
allowed-tools: Bash Read Write Edit
---

# Deploying a UI Bundle App

Deploy order is load-bearing: a step's output is the next step's precondition
(deploy before schema fetch; permissions before schema fetch; role/self-reg
before the schema the guest user must see). This is the canonical setup sequence,
ported from the reference `org-setup.mjs`. The `org-setup.mjs` line
citations in `references/` are port-provenance (why each rule exists) pointing at
that external reference script — not files shipped with this skill — so you don't
need to open them to run the steps.

Run each step in order. **Every optional step is presence-driven**: if its
convention file is absent, no-op cleanly and move on — do not fabricate config.
For the two destructive/expensive steps (self-registration, data import),
**ask the user before running**.

## Inputs to gather up front

Read these from the project; **ask the user** only for what's missing:

- **Target org** — alias/username for `--target-org`. Ask if not obvious.
- **Source root** — run `scripts/get-source-root.sh` to resolve the metadata
  source dir from `sfdx-project.json` (`packageDirectories[0].path` + `/main/default`).
  It exits non-zero if the project file is missing or malformed. Never hardcode
  `force-app/main/default`.
- **`org-setup.config.json`** (optional) — drives permset assignment, role, and
  self-registration. Absent keys mean "skip that step". **Exception:** if the
  file is missing but `permissionsets/` has permsets to assign, don't silently
  skip — scaffold the config or gather equivalent inputs (see step 4).
- **`data-plan.json`** (optional, in the project's `data/` dir) — presence enables the data step.

## Step 1 — Org authentication (always)

Unconditional precondition; cannot be skipped. If the org is already connected
(`sf org display --target-org <org> --json` succeeds), no-op. Otherwise:

```bash
sf org login web --alias <org>
```

A failed login aborts the whole setup before deploy.

## Step 2 — Pre-deploy UI bundle build

Build **every** UI bundle so `dist/` exists before metadata deploy (UI bundle
entities deploy the built output). For each bundle dir under `uiBundles/`:

```bash
npm install
npm run build
```

Run when deploying UI bundles and `dist/` is missing or source changed.

## Step 3 — Deploy metadata

If self-registration is configured:

1. **Deploy license pre-check first** (see `references/license-checks.md`) — it
   blocks the deploy with a clear, license-naming message instead of a cryptic
   failure.
2. **Add the self-reg profile to `networkMemberGroups`** on the local source —
   apply **Edit A** of `assets/network-selfreg-xml-recipe.md`. This must happen
   **before** this deploy so the profile ships as a recognised site member; do
   NOT deploy the network file on its own here (this deploy ships it). Best-effort
   and idempotent — skip if already a member.

Then deploy the whole project (all metadata) by pointing `--source-dir` at the
resolved source root:

```bash
sf project deploy start --source-dir <sourceRoot> --target-org <org>
```

`<sourceRoot>` is the value from `scripts/get-source-root.sh` (e.g.
`force-app/main/default`). Always pass `--source-dir`. Do NOT run bare
`sf project deploy start` with no path: that command relies on source-tracking to
decide what to deploy, and on an org without source-tracking (most non-scratch
orgs) it aborts with *"This org does not have source-tracking enabled … specify
the files or a manifest to deploy."* Passing `--source-dir` deploys the same full
set on both source-tracked and non-tracked orgs and never emits that hint. If the
deploy reports conflicts on a source-tracked org, re-run with `--ignore-conflicts`
— do NOT roll back or reduce the deployed set.

Do NOT hand-build a `package.xml`, assemble a `--metadata-dir` mdapi zip, or
otherwise convert to metadata-format — none of that is needed and it is not part
of this flow.

Timeout 180s. Must complete before permission assignment and schema fetch —
objects, fields, and permission sets appear in the org only after deploy.

## Step 4 — Assign permission sets

Discover permission sets under `<packageDir>/main/default/permissionsets/`. If
none exist and none were passed explicitly, skip.

**If permsets exist but `org-setup.config.json` is missing, do NOT silently
skip.** A missing config makes every discovered permset resolve to `skip`, so
nothing gets assigned and the later GraphQL schema comes back incomplete (the
caller lacks FLS). Instead, help the user supply the assignments — either scaffold
`org-setup.config.json` from `assets/org-setup.config.template.json` or gather the
per-permset assignee inputs for a one-off run. Full schema + scaffolding flow:
`references/config-scaffold.md`. Confirm intent before writing the file or
assigning — don't fabricate assignees.

Otherwise assign each per its config assignee (`org-setup.config.json` →
`permsetAssignments`), where each assignee is one of `currentUser`, `guestUser`,
or `skip` (default `skip`):

```bash
sf org assign permset --name <permset> --target-org <org> [--on-behalf-of <guestUsername>]
```

- **currentUser** — omit `--on-behalf-of`.
- **guestUser** — resolve the site's guest username first (see the guest-user
  section in `references/self-registration.md`). If the site can't be derived or
  no guest user resolves, **skip that permset** and record the reason — don't
  abort the others.
- Treat "Duplicate … PermissionSet" and "not found … target org" as skips, not
  failures.

Required so GraphQL introspection returns the correct schema (the caller needs
FLS on custom fields).

## Step 5 — Assign role (config-gated)

Run only when `org-setup.config.json` has `role: { assignee: "currentUser",
roleName: "<UserRole>" }`. Assigning a role to the current user is what lets
Experience Cloud self-registration work. Idempotent — skip if the user already
has a role. Detail + exact queries: `references/role-assignment.md`.

## Step 6 — Enable self-registration (config-gated) — ask first

Run only when `org-setup.config.json` has
`selfRegistration: { selfRegProfile, accountName }`. **Ask the user before
running.** Sequence (full detail in `references/self-registration.md`):

1. **License pre-check** (soft skip) — if the org lacks a seat on the profile's
   license, warn and skip; it is not a failure. See `references/license-checks.md`.
2. **Derive the site** — run `scripts/derive-site-name.sh`; it outputs the site
   name (the base name of the single `*.network-meta.xml`) or exits non-zero when
   zero or more than one exist (ambiguous — stop).
3. **Flip self-reg on + redeploy the network file** — apply **Edit B** of
   `assets/network-selfreg-xml-recipe.md` (set `selfRegistration=true`, inject
   `<selfRegProfile>`), then redeploy only that one file. Idempotent — skip both
   if already enabled. (Edit A, the member-group add, already happened in step 3.)
4. **Create the Account + NetworkSelfRegistration** — apply
   `assets/network-selfreg.apex` (idempotent; both are query-then-create; run 4a
   and 4b as two separate `sf apex run` invocations).

## Step 7 — Data import (presence-driven) — ask first

Run `scripts/find-data-plan.sh` first. If it exits non-zero, **skip this step** —
do not prompt and do not error; just move on to step 8 (a brief "no data plan,
skipping data import" note is fine). There is nothing to import without a plan.
On success it prints the plan's path (it searches recursively, so both a
project-root `data/` and a `<packageDir>/main/default/data/` layout resolve).

When it exists: **always ask the user before importing or cleaning data** — it
deletes existing records first. Apply the verbatim templates; do not improvise
Apex:

1. Run `scripts/find-prep-script.sh`. If it succeeds, it prints the path of a
   `prepare-import-unique-fields.js` that ships with the app — run that first; it
   deduplicates re-runs by stamping stable unique keys on the record files.
   Invoke it the way that copy expects (its interface varies —
   see `references/data-import.md`). If it exits non-zero, there is no prep
   script — skip to the clean step.
2. **Clean** in reverse plan order (children before parents) with
   `assets/data-delete.apex`.
3. **Import** in forward plan order with `assets/data-import.apex`, resolving
   `@referenceId` refs and batching by measured size.

Protocol, `@referenceId` resolution, measured batching, and the
`SETUP_RESULT_JSON` parse-and-hard-fail rule: `references/data-import.md`.

## Step 8 — GraphQL schema fetch + codegen

Run from the UI bundle directory, **after** deploy and permission assignment
(the schema reflects org state and the caller's FLS):

```bash
npm install
SF_TARGET_ORG=<org> npm run graphql:schema
npm run graphql:codegen
npm run build
```

Detail: `references/graphql.md`. Re-run schema fetch + codegen after every deploy
that changes objects, fields, or permissions.

## Done

Setup ends here — the 8 steps above are the complete sequence. Local dev preview
(`npm run dev:preview`) is a separate developer action, not part of setup; if the
user asks to preview the site, see `references/dev-preview.md`.

## Critical rules

- Deploy metadata **before** fetching schema — custom objects/fields appear only
  after deploy.
- Assign permissions **before** schema fetch — the caller may lack FLS otherwise.
- Re-run schema fetch + codegen **after every** metadata deploy that changes
  objects, fields, or permissions.
- Never silently skip permission assignment, self-registration, or data import —
  either the convention file is present (run it, asking first for the destructive
  ones) or it's absent (skip cleanly and say so).
- Discover the source path from `sfdx-project.json`; never hardcode
  `force-app/main/default`.
- Apply the `assets/` Apex and XML templates **verbatim** — they encode
  duplicate-rule bypass, `allOrNone=false` deletes, idempotency, and SOQL-safety
  that are easy to get wrong by hand.

## Interaction order (summary)

1. Authenticate org
2. Build UI bundles (pre-deploy)
3. Deploy metadata (deploy-license gate if self-reg configured)
4. Assign permission sets (config-driven assignee)
5. Assign role (if configured)
6. Enable self-registration (if configured — ask first)
7. Import data (if data plan exists — ask first)
8. Fetch GraphQL schema + codegen + final build
