---
name: experience-ui-bundle-2gp-deploy
description: "MUST activate when the user wants to package, distribute, or install/upgrade/uninstall/promote a UI Bundle as a Salesforce second-generation (2GP) package (project may contain uiBundles/ or sfdx-project.json for packaging tasks; install/upgrade tasks may lack local bundle files). Handles making a bundle packageable, choosing managed/unlocked flavor, creating package/version with sf package, installing/upgrading in another org, and debugging failures. TRIGGER on packaging, 2GP, managed package, unlocked package, AppExchange, package version, sf package, sf package install, sf package upgrade, install a package, upgrade a package, cross-org distribution. DO NOT TRIGGER for plain source deploy to one org (use experience-ui-bundle-deploy) or scaffolding a new bundle (use experience-ui-bundle-project-generate). Apply piecemeal — do ONLY the part asked."
metadata:
  version: "1.0"
  domains: ["Experience"]
  minApiVersion: "58.0"
  relatedSkills:
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-project-generate"
  accessCheck:
    - type: "orgPref"
      value: "Package2Enabled"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Package an existing UI Bundle (2GP)

How to take a **UI Bundle that already exists in the current project**
(under `<packageDir>/uiBundles/<name>/`, where `<packageDir>` is the package
directory from `sfdx-project.json` — commonly `force-app/main/default`) and ship
it as a **second-generation package** (2GP), then install / upgrade / uninstall
it in another org.

**This is reference knowledge, not a runbook to execute top-to-bottom.** The
user already has a project and a built (or buildable) bundle. Read their intent
and apply only the matching part:

**Answer only what was asked.** Give the commands for the one part the user
needs plus the org each targets and any genuine caveat — nothing else. Do **not**
restate the other parts, re-explain the flavor table, or replay the full
build→create→install→promote sequence when the user asked about a single step. A
debug question wants the fix, not a packaging tutorial; an install question wants
the `sf package install` line and the subscriber-vs-Dev-Hub distinction, not
Part 1 and Part 2. Brevity is correctness here.

| The user wants to… | Go to |
|---|---|
| Decide managed vs. unlocked | [Choose a flavor](#choose-a-flavor) |
| Make the bundle packageable / wire a CustomApplication | [Part 1](#part-1--make-the-existing-bundle-packageable) |
| Create the package or a new version | [Part 2](#part-2--create-the-package-dev-hub-only) |
| Install / upgrade / uninstall / promote | [Part 3](#part-3--install--upgrade--uninstall--promote) |
| Debug a failure | [Part 4](#part-4--debug--inspect) + [Troubleshooting](#troubleshooting) |

This skill is for **packaging and cross-org distribution** (`sf package …`). For
plain source deploy of a bundle into one org (`sf project deploy …`), use
**experience-ui-bundle-deploy** instead. Never `sf project generate` or
`sf template generate ui-bundle` here — the project and bundle exist.
`MyReactApp` / `force-app` / `force-app/main/default` are placeholders; substitute
the user's real bundle name and their `<packageDir>` everywhere they appear
below. Resolve `<packageDir>` deterministically — never guess `[0]` in a
multi-package project — with:

```bash
packageDir="$(scripts/find-bundle-package-dir.sh <bundleName>)"   # walks packageDirectories; picks the entry whose tree contains uiBundles/<bundleName>/
```

---

## Step 0 — Confirm the orgs (do this before touching any org)

Do **not** assume the default org. Ask the user, or read `sf org list`, then
restate what you'll use:

- **Dev Hub** (`devhub`) — where the package is created, versions are built, and
  source is deployed. **Always required.**
- **Subscriber** (`subscriber`) — the org you install into. **Only required for
  install / upgrade / uninstall.**

```bash
sf org list                                            # connected orgs + default Dev Hub
sf org list --json | jq -r '.result.nonScratchOrgs[]?.alias'
```

Rules:
- **Create-only task** (package or version) → one Dev Hub is enough; **don't ask
  for a subscriber.**
- **Install task** → confirm **both**, and confirm *which is which*. Installing
  into the Dev Hub by mistake is a common, messy error.

Substitute the real aliases for `devhub` / `subscriber` everywhere below.

**ID legend (packaging):** `0Ho…` package · `04t…` installable version
(SubscriberPackageVersionId) · `05i…` Package2Version · `08c…` version-create
request · `0Hf…` install request · `06y…` uninstall request.

**ID legend (runtime, useful when debugging a broken subscriber):** `9YE…` UI
Bundle row · `9YF…` UIBundleApplication junction · `02u…` CustomApplication /
TabSet · `0Zu…` ManagedContentSpace (workspace) · `0ap…` ManagedContentChannel
(WEB_APP). A missing App Launcher tile after install almost always traces back
to one of these being absent or misprovisioned.

---

## Prerequisite — the 2GP toggle everyone forgets

2GP needs a **manual Setup toggle on the Dev Hub** that no CLI command or
metadata deploy can flip. **Setup → Dev Hub**, both on:

1. **Enable Dev Hub**, and
2. **Enable Unlocked Packages and Second-Generation Managed Packages** ← the real gate.

Until #2 is on, `sf package create` returns `NOT_FOUND` and any `Package2` query
returns `sObject type 'Package2' is not supported`. There is no CLI workaround —
flip the toggle. Verify before starting:

```bash
# clean "0 records" = 2GP ON;  "sObject type 'Package2' is not supported" = toggle OFF
sf data query --target-org devhub --use-tooling-api --query "SELECT Id FROM Package2 LIMIT 1"
sf org display --target-org devhub --json | jq '.result.isDevHub'
```

---

## Choose a flavor

All three are 2GP (same `sf package` CLI). Pick before creating — it drives the
namespace, how the bundle is named on install, and coexistence.

| | **Managed** | **Unlocked — namespaced** | **Unlocked — org-dependent** |
|---|---|---|---|
| Namespace | required | required | none (empty `""`) |
| Source visibility | hidden (IP-protected) | visible / editable | visible / editable |
| Installs as | `ns__Name` | `ns__Name` | bare `Name` (flat) |
| Coexists with a local same-name bundle | yes (ns-filtered) | yes (ns-filtered) | no — collides |
| Upgrade behavior | clean replace (locked) | replace, **overwrites subscriber edits** | replace, **overwrites subscriber edits** |
| Rollback risk on failed upgrade | yes | yes | none |
| Typical use | ISV / AppExchange distribution | org-agnostic sharing, source open | package depends on metadata already in the target org |

Namespaced flavors (managed, unlocked-namespaced) need a namespace **registered
and linked to this Dev Hub** (App Launcher → *Namespace Registries*). No
registered namespace? Use **org-dependent unlocked** — it needs none.

### How linking works (namespace ⇄ Dev Hub)

The namespace lives in a separate **Developer Edition (DE) org** that owns it;
the Dev Hub *borrows* it via a linked registration. Concretely:

1. Sign up a DE org and register a namespace on it (Setup → Package Manager →
   Namespace Registrations).
2. In the Dev Hub, App Launcher → *Namespace Registries* → **Link Namespace**,
   log in with the DE org's credentials to link the namespace to this Dev Hub.
3. Set `namespace` in `sfdx-project.json` to the linked namespace slug. If the
   value here isn't linked to the target Dev Hub, `sf package version create`
   fails with a namespace error (see [Troubleshooting](#troubleshooting)).

One DE org can carry multiple namespaces, and one Dev Hub can link multiple DE
orgs — so a single Dev Hub can build packages under several namespaces. The
namespace is **locked in at version-create time** and travels with every UI
Bundle row inside the built version; you cannot change it later.

---

## Runtime model — why the flavor matters

You do not have to explain this to answer a routine question. Reach for it when
the user asks *why*: why managed hides source, why namespaced installs are
`ns__Name`, why some URLs look different, or why an unlocked upgrade wiped
their edits.

- **Origin isolation.** Every installed UI Bundle renders from its own origin on
  `*.salesforce.app`, distinct from `salesforce.com` core UI. Tiers:
  - `salesforce.com` — 1st-party core UI
  - `*.salesforce.app` — 2nd-party AFS-hosted bundles (no namespace)
  - `<ns>.salesforce.app` — 3rd-party / namespaced (managed + unlocked-namespaced)
  Because each namespace gets its own subdomain, two bundles from different
  packages can coexist without cross-origin bleed.
- **IP protection is a managed-only property.** For **managed** packages,
  `getSourceZip()` returns null in subscriber orgs — the compiled `dist/` is
  stored as opaque content and never handed back. For **unlocked** (namespaced
  or org-dependent), the served binary is fully readable by the subscriber.
- **Install semantics.** Managed and unlocked-namespaced install as `ns__Name`
  and can coexist with a local same-name bundle. Org-dependent unlocked has no
  namespace — it installs as bare `Name` and collides with a local bundle of
  the same developer name.
- **Delta upgrade.** On `sf package install` of a newer `04t…`, the platform
  compares content-index hashes of each incoming `dist/` asset against what's
  already stored and **skips any asset whose hash is unchanged** — a patch that
  touches one bundle re-writes only that bundle's changed files. Developer-owned
  artifacts (`dist/`, `ui-bundle.json`, ISV base permission sets) are replaced;
  subscriber-owned state (subscriber-created permission sets, custom metadata,
  provisioned domain) is preserved.
- **Kill switch.** Setup → Security → *Multi-Framework Domains* → disable a
  provisioned domain. Immediate 404; metadata stays installed; reversible.

---

## Part 1 — make the existing bundle packageable

Prepare the project so it can be packaged and used in-org. Apply only what the
request needs.

### 1a. Set API version + namespace in `sfdx-project.json`

The `namespace` here decides which flavor you can build (see table above), so set
it deliberately — there is no safe default. Substitute the user's real registered
namespace for `<ns>`; use `""` for org-dependent.

```bash
# namespaced (managed / unlocked-namespaced): <ns> MUST be registered & linked to this Dev Hub
node -e "const fs=require('fs'),f='sfdx-project.json',j=JSON.parse(fs.readFileSync(f)); j.sourceApiVersion='68.0'; j.namespace='<ns>'; fs.writeFileSync(f,JSON.stringify(j,null,2))"

# org-dependent unlocked: no namespace
node -e "const fs=require('fs'),f='sfdx-project.json',j=JSON.parse(fs.readFileSync(f)); j.sourceApiVersion='68.0'; j.namespace=''; fs.writeFileSync(f,JSON.stringify(j,null,2))"

cat sfdx-project.json    # confirm namespace + sourceApiVersion before packaging
```

- Managed / namespaced-unlocked → `namespace` = a registered, linked namespace.
- Org-dependent unlocked → leave `namespace` as `""`.
- Setting a namespace that isn't registered to this Dev Hub fails the build later
  (see [Troubleshooting](#troubleshooting)).

### 1b. Build the bundle — `dist/` must exist before packaging

```bash
cd force-app/main/default/uiBundles/MyReactApp        # the real bundle dir
npm install --no-audit --no-fund
npm run build
cd -
```

Package or deploy **before** `dist/` exists and the app installs but **renders
blank** — the bundle ships with its built assets. Always build first.

### 1c. Wire a CustomApplication (only if the bundle must be launchable as a Salesforce app)

Skip this step when the bundle is already referenced another way (embedded in a
FlexiPage, Experience Cloud site, etc.). Otherwise **read**
`<SKILL_DIR>/assets/CustomApplication.app-meta.xml` (where `<SKILL_DIR>` is the
absolute path to this skill's own directory), replace every `MyReactApp` with
the real bundle developer name, and **write** the result to the user's project
under `<packageDir>/applications/`. Author `<uiBundle>` with the bundle's
**developer name** — inside the same package no prefix is needed; cross-namespace
it resolves as `ns__Name` (namespaced) or `c__Name` (no namespace).

The three fields the App Launcher tile actually cares about — installed
subscribers won't see a broken tile if they're set correctly:

- `<uiType>Lightning</uiType>` — required for the App Launcher to render it
- `<navType>Standard</navType>` — standard navigation container
- `<formFactors>Large</formFactors>` — desktop form factor (validation is
  install-time only, so a missing/wrong value passes deploy but hides the tile)

```bash
mkdir -p force-app/main/default/applications
# then write the substituted template to:
#   force-app/main/default/applications/<BundleName>.app-meta.xml
```

### 1d. Deploy source to the Dev Hub (so metadata exists before `package create`)

```bash
sf project deploy start --source-dir force-app --target-org devhub --api-version 68.0 --wait 30
```

### 1e. Grant app visibility via a permission set (only if 1c added a CustomApplication and the app must be reachable without a manual Setup click)

Read `<SKILL_DIR>/assets/PermissionSet.permissionset-meta.xml`, replace
`MyReactApp` with the real bundle name (both in `<application>` and the label),
write the result into the user's project, then deploy and assign:

```bash
mkdir -p force-app/main/default/permissionsets
# write the substituted template to:
#   force-app/main/default/permissionsets/<BundleName>_Access.permissionset-meta.xml
sf project deploy start --source-dir force-app/main/default/permissionsets/MyReactApp_Access.permissionset-meta.xml --target-org devhub --api-version 68.0 --wait 30
sf org assign permset --name MyReactApp_Access --target-org devhub
```

---

## Part 2 — create the package (Dev Hub only)

No subscriber org involved. `sf package create` runs **once** (registers the
`0Ho…` container); you build installable `04t…` versions repeatedly after. Pick
the one flavor you chose above:

```bash
# managed
sf package create --name MyReactApp --package-type Managed --path force-app --target-dev-hub devhub

# unlocked, namespaced  (namespace comes from sfdx-project.json)
sf package create --name MyReactApp --package-type Unlocked --path force-app --target-dev-hub devhub

# unlocked, org-dependent (no namespace)
sf package create --name MyReactApp --package-type Unlocked --org-dependent --path force-app --target-dev-hub devhub
```

Then build a version:

```bash
sf package version create --package MyReactApp --installation-key-bypass --wait 20 --target-dev-hub devhub
# a specific/patch version instead:
sf package version create --package MyReactApp --version-number 1.0.1 --wait 20 --target-dev-hub devhub
```

`--version-number 1.0.0.NEXT` auto-bumps the build number; a fixed `1.0.1` pins
it. `--installation-key-bypass` builds an unprotected version (no key to
install); omit it and pass `--installation-key <key>` to gate installs.

### Robust version-create (survives a slow Dev Hub queue)

`--wait` can time out while the build sits queued, losing the request handle.
Submit async, capture the `08c…` id, poll:

```bash
REQ=$(sf package version create --package MyReactApp --installation-key-bypass \
  --skip-validation --target-dev-hub devhub --json | jq -r '.result.Id')
echo "request: $REQ"
while :; do
  J=$(sf package version create report -i "$REQ" --target-dev-hub devhub --json)
  ST=$(echo "$J" | jq -r '.result[0].Status'); echo "status: $ST"
  case "$ST" in
    Success) echo "$J" | jq -r '.result[0].SubscriberPackageVersionId'; break;;
    Error)   echo "$J" | jq -r '.result[0].Error[]? // "build failed"'; break;;
  esac
  sleep 30
done
```

`--skip-validation` is faster but produces a **beta** version (can't be promoted,
and beta can't upgrade beta — see Part 3). Drop it for a releasable build. Resume
a queued build anytime:
`sf package version create report -i 08c… --target-dev-hub devhub`

---

## Part 3 — install / upgrade / uninstall / promote

**Confirm the subscriber alias first (Step 0).** Everything here hits the
subscriber — except **promote**, which runs on the Dev Hub.

```bash
# fresh install
sf package install --package 04t… --target-org subscriber --wait 10
#   add --installation-key <key> if the version was built with one
#   add --publish-wait 10 to wait for the version to finish publishing

# upgrade (newer version over the old)
sf package install --package 04t…v2 --target-org subscriber --upgrade-type Mixed --wait 10
#   --upgrade-type: Mixed (default) | DeprecateOnly | Delete (destructive — care)

# uninstall
sf package uninstall --package 04t… --target-org subscriber --wait 20

# promote a managed version to released/immutable — runs on the DEV HUB, irreversible
sf package version promote --package 04t… --target-dev-hub devhub
```

**Beta can't upgrade beta.** A `--skip-validation` (beta) v0.2 over a beta v0.1
fails with *"Cannot upgrade beta package."* Either **promote** v0.1 (managed) or
**uninstall** v0.1 first, then install v0.2.

**Unlocked upgrades overwrite subscriber edits** to the bundle. Org-dependent has
no rollback on a failed upgrade; namespaced flavors do.

### Robust install (confirm it actually landed)

`sf package install --wait` can exit 0 while the request is still IN_PROGRESS —
a false success. Verify:

```bash
sf package install --package 04t… --target-org subscriber --wait 20 --no-prompt
sf package installed list --target-org subscriber --json \
  | jq -r '.result[]? | select(.SubscriberPackageVersionId=="04t…") | .SubscriberPackageVersionId'
```

Prints nothing → still processing server-side; poll `sf package installed list`
a few minutes before concluding it failed.

---

## Part 4 — debug / inspect

Mostly read-only. Reach for these to diagnose a failure or inspect state.

```bash
# Dev Hub state
sf org display --target-org devhub --json | jq '{isDevHub:.result.isDevHub, user:.result.username, instance:.result.instanceUrl, api:.result.apiVersion}'

# Is 2GP on?  (the #1 root cause)
sf data query --target-org devhub --use-tooling-api --query "SELECT Id, Name, NamespacePrefix, ContainerOptions FROM Package2"

# Packages & versions on the Dev Hub
sf package list --target-dev-hub devhub
sf package version list --packages MyReactApp --target-dev-hub devhub --verbose

# Version-create failures — status + Error[]
sf package version create list --target-dev-hub devhub
sf package version create report -i 08c… --target-dev-hub devhub
sf data query --target-org devhub --use-tooling-api \
  --query "SELECT Id, Status, Package2Id, Error FROM Package2VersionCreateRequest ORDER BY CreatedDate DESC LIMIT 5"

# A version's details
sf package version report --package 04t… --target-dev-hub devhub

# What's installed in the subscriber
sf package installed list --target-org subscriber --json \
  | jq -r '.result[]? | "\(.SubscriberPackageName) \(.SubscriberPackageVersionNumber) \(.SubscriberPackageVersionId)"'

# Install/uninstall stuck IN_PROGRESS
sf package install report   --request-id 0Hf… --target-org subscriber
sf package uninstall report --request-id 06y… --target-org subscriber

# Deploy failures (before you can even package)
sf project deploy start --source-dir force-app --target-org devhub --dry-run --wait 30
sf project deploy report --target-org devhub

# Bundle renders blank — confirm built assets shipped
ls -la force-app/main/default/uiBundles/MyReactApp/dist
```

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `sObject type 'Package2' is not supported` | 2GP toggle OFF — **Setup → Dev Hub** → enable "Unlocked & Second-Gen Managed Packages" (manual, no CLI fix). |
| `sf package create` → `NOT_FOUND` | Same — 2GP not provisioned. Enable toggle, re-auth. |
| `isDevHub: false/null` after enabling | Cached CLI login — re-auth. Trust the `Package2` query + `package create`, not the cached flag. |
| `version create` hangs / `--wait` times out | Build queued. Use the async submit + `version create report -i 08c…` poll; resume later with the same id. |
| `install --wait` exits 0 but app missing | Still IN_PROGRESS server-side. Confirm with `sf package installed list`; poll a few minutes. |
| "Cannot upgrade beta package" | Beta can't upgrade beta. Promote v0.1 (managed) or uninstall it first, then install v0.2. |
| Namespace error on managed/namespaced build | Namespace not registered/linked to this Dev Hub (App Launcher → *Namespace Registries*), or switch to org-dependent unlocked (no namespace). |
| App installs but renders blank | Bundle not built before deploy/package — `npm run build`, confirm `dist/`, redeploy, rebuild the version. |
| Installed into the wrong org | Wrong alias confirmed in Step 0. Re-check `sf org list`; `subscriber` ≠ `devhub`. |
| Org-dependent bundle collides with a local one | Both use a bare (null-prefix) name. Use a namespaced flavor, or rename. |

## Notes

- **Confirm orgs first.** Dev Hub always; subscriber only for install/upgrade/
  uninstall. Don't ask for a subscriber on a create-only task.
- **Order for a full run:** build bundle → deploy source → `package create`
  (once) → `package version create` (each release) → `install` → `promote`
  (managed only).
- For internal Salesforce packaging questions, the authoritative channel is
  **#packaging**.
- **Authoritative external docs** (for deeper reference):
  - Second-Generation Managed Packaging Developer Guide —
    <https://developer.salesforce.com/docs/atlas.en-us.pkg2_dev.meta/pkg2_dev/sfdx_dev_dev2gp.htm>
    (managed / AppExchange flavor: workflow, components, distribution, push
    upgrades, 1GP→2GP gaps).
  - Unlocked packages share the same `sf package` CLI; see the "Unlocked
    Packages" section of the same guide for the unlocked-namespaced and
    org-dependent flavors.
