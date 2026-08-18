---
name: experience-ui-bundle-deploy
description: "MUST activate when the project has a uiBundles/*/src/ directory and the task involves deploying to an org or post-deploy org setup. Deploys a UI bundle app and runs ordered setup: org auth, build, metadata deploy, permission-set and role assignment, Experience Cloud self-registration, social login / SSO / IDP linking (Auth Providers + SAML SSO configs on a React site), seed-data import, and GraphQL schema fetch + codegen. Trigger signals: *.network-meta.xml, org-setup.config.json (with a socialLogin block), data-plan.json, sfdx-project.json, or mentions of deploy, org setup, or social login / SSO / IDP linking on an Experience site. DO NOT TRIGGER when: creating a new UI bundle project (use experience-ui-bundle-project-generate); styling pages without deploying (use experience-ui-bundle-frontend-generate); adding a feature such as auth, search, or file upload without deploying (use the matching experience-ui-bundle-*-generate skill); configuring MFA permission sets (use experience-ui-bundle-mfa-configure)."
metadata:
  version: "1.2"
  domains: ["Experience", "Developer Experience"]
  relatedSkills:
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-mfa-configure"
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
- **`org-setup.config.json`** (optional) — drives permset assignment, role,
  self-registration, and social login. Absent keys mean "skip that step".
  **Exception:** if the file is missing but `permissionsets/` has permsets to
  assign, don't silently skip — scaffold the config or gather equivalent inputs
  (see step 4).
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

## Step 6b — Enable social login (config-gated)

Run only when `org-setup.config.json` has a `socialLogin` block. If the block is
absent, `loadSocialLoginConfig` returns null and the step is hidden — no-op
cleanly and say so. This step is **non-destructive and idempotent** (it only adds
missing links/members), so — unlike self-registration and data import — it does
**not** require asking first.

This links the site's configured **Auth Providers** (OAuth) and **SAML SSO
configs** to the site so the built-in Social Login component renders their
buttons on the React login page. On React (Site Container) sites the SSO admin UI
is hidden, so the linking is done programmatically via `AuthConfig` /
`AuthConfigProviders` records — you cannot do it by clicking through Setup. Full
detail, sub-steps, and port-provenance: `references/social-login.md`.

Config shape (see `references/config-scaffold.md` for the full schema):

```json
{ "socialLogin": {
    "communityMemberProfile": "Customer Community User",
    "authProviderNames": ["Google", "My_SAML_Provider"],
    "communityUserPermset": "myapp_Guest_User_Api_Access"
} }
```

Sequence (mirrors reference `org-setup.mjs` `main()` social-login step, which runs
**after** self-registration and **before** the data/GraphQL steps):

Apply the `assets/` templates **verbatim** (like the self-reg/data steps) — full
runnable commands for each sub-step are in `references/social-login.md`:

1. **Derive the site** — run `scripts/derive-site-name.sh` (single
   `*.network-meta.xml`; stop if zero/ambiguous). Social login needs the site to
   resolve its `AuthConfig`.
2. **Enable "Allow standard external profiles"** — deploy
   `assets/Communities.settings-meta.xml` via Metadata API (from a throwaway
   minimal project; see the reference). Required so the SSO registration handler
   can create users on standard community profiles; without it auth providers fail
   user insert with `FIELD_INTEGRITY_EXCEPTION`. A "already active" warning is a
   non-fatal skip.
3. **Link Auth Providers to the site `AuthConfig`** — run
   `assets/social-login-auth-providers.apex` verbatim (substitute `<siteName>`,
   `<ProviderNamesList>`, `<ApiVersion>`) to create the missing
   `AuthConfigProviders` junctions, then read its `|DEBUG|` lines (table in the
   reference). All-or-nothing: if any configured `authProviderNames` entry has no
   matching `AuthProvider` (OAuth) or `SamlSsoConfig` (SAML) record, it emits
   `MISSING_PROVIDERS` and links nothing — create/fix them in Setup first.
   Already-linked providers are skipped (idempotent).
4. **Add the community member profile to `NetworkMemberGroup`** — resolve the
   Network + Profile Ids and create the membership if absent (`sf data` commands in
   the reference). Without it, SSO-registered users hit `NO_ACCESS: User was not
   authorized for the community`.
5. **(Optional) Assign `communityUserPermset` to community users** — only when
   configured. Grants `ApiEnabled` so `getCurrentUser()` (`/chatter/users/me`)
   works for SSO-created users.

> **IMPORTANT:** A `socialLogin` block present but skipped is a silent-failure
> trap — the app deploys fine, but no social-login buttons ever appear on the
> login page and there is no error explaining why. Do not silently skip: run the
> step when the block is present, or state clearly that it was absent.

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

Setup ends here — the steps above (including the config-gated 6b social login)
are the complete sequence. Local dev preview (`npm run dev:preview`) is a separate
developer action, not part of setup; if the user asks to preview the site, see
`references/dev-preview.md`.

## Critical rules

- Deploy metadata **before** fetching schema — custom objects/fields appear only
  after deploy.
- Assign permissions **before** schema fetch — the caller may lack FLS otherwise.
- Re-run schema fetch + codegen **after every** metadata deploy that changes
  objects, fields, or permissions.
- Never silently skip permission assignment, self-registration, social login, or
  data import — either the convention file/config block is present (run it, asking
  first for the destructive ones) or it's absent (skip cleanly and say so). A
  present-but-skipped `socialLogin` block means no login buttons appear with no
  error to explain it.
- Discover the source path from `sfdx-project.json`; never hardcode
  `force-app/main/default`.
- Apply the `assets/` Apex and XML templates **verbatim** — they encode
  duplicate-rule bypass, `allOrNone=false` deletes, idempotency, SOQL-safety, and
  (for social login) the all-or-nothing provider pre-check and the
  DML-not-allowed-on-`AuthConfigProviders` REST-callout insert — all easy to get
  wrong by hand.

## Interaction order (summary)

1. Authenticate org
2. Build UI bundles (pre-deploy)
3. Deploy metadata (deploy-license gate if self-reg configured)
4. Assign permission sets (config-driven assignee)
5. Assign role (if configured)
6. Enable self-registration (if configured — ask first)
6b. Enable social login (if `socialLogin` configured — idempotent, no ask needed)
7. Import data (if data plan exists — ask first)
8. Fetch GraphQL schema + codegen + final build
