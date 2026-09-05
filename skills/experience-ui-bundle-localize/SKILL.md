---
name: experience-ui-bundle-localize
description: "MUST activate to localize / internationalize a uiBundles/*/src/ project (React or Angular): extract hardcoded user-facing strings into Custom Labels, wire a runtime i18n library over the Platform SDK backend, add labels for another language, or troubleshoot label rendering across locales. Triggers: user-facing string literals in component files, a CustomLabels.labels-meta.xml, a src/i18n/ directory or label-manifest.ts, translation call sites, or requests to 'translate / localize / internationalize / support another language.' Scope: authenticated B2E UI Bundles and B2C site bundles. Use experience-ui-bundle-site-generate instead for site language configuration or sfdc_cms__languageSettings. DO NOT TRIGGER for B2B site bundles, building app shell/UI or styling, reading/writing/refreshing records (use experience-ui-bundle-salesforce-data-access), generating a new bundle (use experience-ui-bundle-frontend-generate), deploying (use experience-ui-bundle-deploy), or authoring translations in Translation Workbench."
metadata:
  version: "1.2"
  domains: ["Experience"]
  minApiVersion: "68.0"
  relatedSkills:
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-salesforce-data-access"
    - "experience-ui-bundle-site-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["npm"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Localize a UI Bundle

Localize a UI Bundle: extract user-facing strings into Salesforce Custom Labels, wire a
runtime i18n library over the Platform SDK backend, and verify labels across locales.

This file is the **framework-neutral workflow + guardrail spine**. The framework-specific
detail — which i18n library, the translation call convention, the files scanned, the wiring
shape, and the depth docs — lives in a per-framework reference.

## The one-paragraph mental model

A UI Bundle can't use compile-time label imports the way LWC does (`@salesforce/label/*`
resolves inside the platform's compiler, which your standalone bundle doesn't go through).
Instead, your app **fetches labels at runtime** through the Salesforce GraphQL UI API and
hands them to a standard i18n library to render. The Platform SDK provides the runtime
plumbing: a detector that reads the user's language, a backend that fetches labels over
GraphQL, and a context fetch. You write two thin files — a short init that wires the SDK
pieces into your i18n library, and a manifest listing which labels your app uses — then
author the labels themselves as Salesforce Custom Labels metadata. The exact library and
call convention are framework-specific; see your framework reference.

---

## Step 0: Route the task

| The task is… | Go to |
|---|---|
| Bundle doesn't exist yet | **experience-ui-bundle-frontend-generate** skill |
| Deploying the app with its labels | **experience-ui-bundle-deploy** skill |
| Configuring site languages or `sfdc_cms__languageSettings` | **experience-ui-bundle-site-generate** skill |
| Localizing an existing bundle | **Determine the framework (below), then the workflow** |

**Determine the framework.** It is normally already decided by the calling context — passed
down by the coordinator skill that invoked this one, or stated in the user's request. Use that.

The frameworks this skill supports are exactly the reference folders under
`<SKILL_DIR>/references/`, each containing a `localize.md` (so `react` →
`<SKILL_DIR>/references/react/localize.md`). This is the single source of truth — adding a
framework means adding a reference folder, nothing here changes.

- **If the framework is known** — open `<SKILL_DIR>/references/<framework>/localize.md` and
  keep it alongside this spine. It supplies the library, the call convention, the files to
  scan, and the wiring code.
- **If it is unknown** (a standalone run where nobody said which) — run the deterministic
  detector on the app / uiBundle root before asking anyone:

  ```bash
  bash "<SKILL_DIR>/scripts/detect-framework.sh" "<app-or-uiBundle-root>"
  ```

  It combines an `angular.json` at/above the root, `@angular/core` / `react` in any
  non-`node_modules` `package.json`, and source-file signatures, then prints one token and
  sets a matching exit code:
  - `react` or `angular` (exit 0) → use that framework. **Do not ask the user** — the
    detection is deterministic. Open `<SKILL_DIR>/references/<framework>/localize.md`.
  - `ambiguous` (exit 2) → both frameworks are present. List `<SKILL_DIR>/references/` and ask
    the user which one to localize. If they name a framework with no matching reference folder,
    it is not supported here — stop.
  - `unknown` (exit 3) → **no supported framework detected. Terminate the workflow.** Do not
    guess and do not proceed: report that neither React nor Angular signals were found in the
    bundle, so localization cannot continue, and stop here.

Throughout the steps below, `<framework>` means the folder chosen here. The deterministic
check scripts split by coupling:
- **Framework-neutral, shared in `<SKILL_DIR>/scripts/`** — `detect-framework.sh` (the Step-0
  detector above), `check-org-api-version.sh` and `detect-bundle-type.sh` (pure org/metadata
  checks), and `check-manifest-registered.sh` (agnostic skeleton; it takes `--framework
  <framework>` to select the call-site grammar).
- **Framework-specific, under `<SKILL_DIR>/references/<framework>/`** — `check-i18n-wired.sh`
  (its manifest-into-backend detection is i18n-library-shaped, so each framework ships its own).

---

## Preconditions: verify before editing

| # | Requirement | Verify | If missing |
|---|---|---|---|
| 1 | It's a `uiBundles/*/src/` project (React or Angular) | Project structure matches | Not a UI Bundle → route to the correct skill |
| 2 | Platform SDK, UI Bundle, and build-plugin siblings installed and aligned (≥11.49.3) | `package.json` in the UI bundle dir | Tell user to align and upgrade them; cannot proceed |
| 3 | You can identify where the app mounts | Read the entry file (see the framework reference) | No clear mount point → ask user to point it out |
| 4 | Target org actually supports API v68.0+ (runtime label GraphQL for UI Bundles ships in Release 264) | Run the runtime org-release check below | Org's max API version is below v68.0 (Release 262 or older) → cannot proceed; retarget a Release 264+ org or upgrade the org |
| 5 | The bundle is authenticated B2E or the request/context explicitly identifies a B2C site, not B2B | Run the bundle-type detection below and use the request/context for site product identity | Explicit B2B → reject; site type not explicit → ask the user and stop until confirmed; B2C also requires precondition 6 |
| 6 | For B2C only, an admin has enabled `GraphQLApiOrgPrefForGuestUsers` | Ask the admin to confirm the org preference is already enabled | Do not enable it; explain that guest GraphQL returns HTTP 403 without it and stop (dependency: W-23854208) |

**Runtime org-release check (precondition 4).** The `platform.labels` GraphQL path that resolves labels at runtime for UI Bundles ships in Salesforce Release 264 (API v68.0 or higher). A `sourceApiVersion` in `sfdx-project.json` records what you declared, not what the org supports, so a newer CLI pointed at an older org can pass a static file check and then fail at runtime. Query the org's actual maximum API version before wiring anything:

```bash
bash <SKILL_DIR>/scripts/check-org-api-version.sh <org-alias-or-username>
```

Exit `0` → the org supports v68.0+, proceed. Exit `1` → the org is too old or unreachable; do not write i18n wiring or labels, report the version mismatch to the user and stop. (`sf api request rest` inside the script keeps authentication at the CLI transport layer, so no access token enters context.)

**Bundle-type detection (precondition 5).** The bundle's type decides which localization branch applies. It is framework-agnostic (pure Salesforce metadata). Pass the full path to the bundle dir; the script derives the metadata root from it, so the current directory does not matter:

```bash
bash <SKILL_DIR>/scripts/detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>
```

Act on the exit-code contract: `0` → authenticated app (B2E or in-core internal), use the B2E branch; `10` → bound public site app-container candidate, meaning metadata proves site binding and guest access but **not** B2C versus B2B; `11` → bound non-public/unsupported site, stop; `12` → both CustomApplication and one site binding exist, ask which runtime context is the localization target; `13` → multiple matching Experience site bindings, show the reported site names and ask which site/runtime context is the target; `2` → unbound/unknown, report the script output and stop rather than guessing.

For exit `10`, route by explicit request/context: if it says **B2C**, confirm precondition 6 and use the B2C branch; if it says **B2B**, reject it; if product type is not explicit, ask the user whether the site is B2C or B2B and stop until confirmed. For exits `12` and `13`, require the user to choose the runtime context (and site for exit `13`), then apply that branch's fallback and prerequisites. Never infer B2C from `DigitalExperienceConfig`, `appSpace`, `appContainer`, or `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED`; the authentication value means guest access is enabled.

For B2C, only an org admin may enable `GraphQLApiOrgPrefForGuestUsers`; never provision or change it. Without it, guest label requests return HTTP 403. Track availability through W-23854208.

If a precondition isn't met, stop: report the specific block to the user and record a plan item to return once it's resolved. Do not add i18n wiring or TODO markers to a B2B or unknown bundle.

---

## Workflow: the five steps

Each step has a **completion criterion** and a **confirm-before-continue** pause. Framework
specifics (file extensions, the translation call, the install, the init code) come from
`<SKILL_DIR>/references/<framework>/localize.md`.

### Step 1: Detect

**Goal:** Scan the framework's component files for user-facing hardcoded strings. (The
framework reference names the file extensions to scan.)

**What to scan:**
- String literals shown to users in markup: `Welcome` in a heading → candidate
- String props shown to users: `placeholder="Enter name"` → candidate
- User-facing accessible text: `aria-label`, `aria-describedby`, `alt` → candidate (a screen-reader user hears these, so they must localize too)

**What to skip:**
- Import statements
- Object keys / property names
- `data-*` attributes (machine-readable)
- Test IDs (`data-testid`, `id` attributes)
- Text already wrapped in a translation call
- Console logs, error messages thrown to developers (not user-facing)
- Class names, file paths, technical constants

**Action:**
1. Scan the `src/` directory for the framework's component files
2. Extract candidates, showing file path + line number for each
3. Show the list to the developer

**Completion criterion:**
Developer confirms the list (or edits it to remove false positives).

**Pause:** "I found N user-facing strings across M components. Here's the list: [show file:line + string]. Look right? [confirm / edit the list / skip some]"

---

### Step 2: Extract

**Goal:** For each confirmed string, add a Custom Label and replace the literal with a translation call.

**Action for each string:**
1. **Propose a key name**, format: `<Context>_<Role>` (e.g., `"Welcome"` → `Welcome_Text`, `"Save"` → `Save_Button`, `"Failed to save"` → `Save_Failed_Message`). Follow naming: PascalCase words, underscores between parts, descriptive enough to be unique.
2. **Add the label** to `force-app/main/default/labels/CustomLabels.labels-meta.xml`:
   ```xml
   <labels>
     <fullName>Welcome_Text</fullName>
     <language>en_US</language>
     <protected>false</protected>
     <shortDescription>Welcome banner heading</shortDescription>
     <value>Welcome</value>
   </labels>
   ```
   (Full XML structure: `references/common/label-xml.md`)
3. **Replace the string** in the component with your framework's translation call, and add
   any required import/injection. The exact call convention is in the framework reference.

**Completion criterion:**
Every confirmed string has both a `CustomLabels` entry and a translation call in its original location.

**Pause:** "For each string I'll add a Custom Label and replace the literal with a translation call. Here are the proposed keys: [show string → namespace:Key mapping]. Apply these edits? [y / review each]"

---

### Step 3: Register

**Goal:** Add each key to the label manifest so the i18n runtime knows to fetch it.

**Action:**
1. Add each key to the manifest array in `src/i18n/label-manifest.ts`:
   ```typescript
   export const labelManifest = [
     "c:Welcome_Text",
     "c:Save_Button",
     "c:Save_Failed_Message",
   ];
   ```
   If the file doesn't exist yet, Step 4 scaffolds it; the completion check below reports its absence, so don't test for the file by hand.

**Completion criterion:**
Run `check-manifest-registered.sh` from the UI bundle dir (it scans `src/` relative to the current directory) and report any errors it returns. It owns the deterministic inspection: it cross-checks every translation call site against the manifest and treats a missing `label-manifest.ts` (when call sites exist) as a failure. A key that's called but not registered renders as its own literal name at runtime with no error, the silent-fail trap this guards.

```bash
cd <path-to-uiBundles/<name>/ dir>   # scripts scan src/ relative to here
bash <SKILL_DIR>/scripts/check-manifest-registered.sh --framework <framework>
```

Branch on the exit code: `0`, every key is registered (or there are no call sites to gate), proceed. `1`, the manifest is missing or the listed keys aren't in it; scaffold or add them (Step 4 scaffolds the file) and re-run. `64`, usage error, the source dir doesn't exist (wrong cwd or bad argument); this is **not** a "keys missing" result, do not scaffold or register, fix the path and re-run.

**Pause:** "Added N entries to label-manifest.ts. check-manifest-registered.sh passed: [confirm]."

---

### Step 4: Wire

**Goal:** Ensure the i18n wiring exists; scaffold it if the app has no i18n yet. The install
command, the wiring code, and the B2E vs B2C fallback configuration are all in the framework
reference (`references/<framework>/localize.md` and its `i18n-setup.md`).

**Check:**
Run `check-i18n-wired.sh` from the UI bundle dir (it scans `src/` relative to the current directory) and report what it returns. The script owns the whole deterministic inspection: it looks for the framework's i18n wiring (React: an `initI18n()` init file called at boot; Angular: `provideTranslateService`/`TranslateModule.forRoot` registering a custom `TranslateLoader`, loaded at boot via `TranslateService.use`), and when that exists it also reports whether the label manifest is imported and actually reaches the label backend/loader. Do not re-derive any of this by reading files yourself.

```bash
cd <path-to-uiBundles/<name>/ dir>   # scripts scan src/ relative to here
bash <SKILL_DIR>/references/<framework>/check-i18n-wired.sh
```

Branch on the **exit code** (the printed message names the specific file/symbol for your report, but the decision is the code):
- Exit `0` → fully wired, the manifest reaches the label backend/loader; just add new keys.
- Exit `1` → no i18n wiring exists; scaffold the whole setup per the framework reference.
- Exit `2` → the wiring exists but is incomplete (React: init not called at boot; Angular: loader not registered, or registered but no boot-time `TranslateService.use`); do **not** re-scaffold or overwrite it. Add only the missing wiring the message names, then re-run.
- Exit `3` → wired at boot but the script **could not confirm** the manifest reaches the backend/loader. This last check is a textual heuristic: the manifest may be wired through a variable, spread, factory, or helper the script can't see, so treat exit 3 as "verify before editing," not "definitely broken." Open the file the message names and confirm before reconciling; never re-scaffold or duplicate wiring that already works.
- Exit `64` → usage error: the source dir doesn't exist (wrong cwd or bad argument). This is **not** a "no wiring" result; do not scaffold. Fix the path and re-run.

**B2C override — applies even at exit `0`:** the wiring check only proves i18n *exists*, not that it is correct for B2C. A seed with B2E wiring — `dir = ctx.dir` and a loader with **no** `labelFallback` — passes `check-i18n-wired.sh` at exit `0` but is **wrong for a B2C site**. If the site is B2C, don't stop at "add new keys": open `src/i18n/index.ts` (or the framework's init file) and, using `resolvedLang` (= `SFDC_ENV.language || ctx.lang`; the detector does not read `SFDC_ENV.language`), (a) add `labelFallback: "USER_DEFAULT"`, (b) set direction from it — `i18next.dir(resolvedLang)`, never `ctx.dir`, and (c) initialize in it — React `lng: resolvedLang` in `i18next.init`; Angular `translate.use(resolvedLang)`. See `references/<framework>/i18n-setup.md`. Never leave B2E wiring on a B2C site.

**Completion criterion:**
The i18n wiring exists and is called once at boot; the manifest reaches the label backend/loader. For B2C, all three `resolvedLang` overrides are applied — `USER_DEFAULT` fallback, display language (React `lng`, Angular `translate.use`), and `i18next.dir(resolvedLang)` direction — not the seed's B2E defaults.
Follow the framework reference for the exact scaffold and never clobber existing wiring.

**Pause:** "i18n setup [exists / created]. It's loaded at boot: [confirm]."

---

### Step 5: Verify

**Goal:** Guide the developer to verify labels render in a second language.

**Action:** Follow the branch-specific procedure in `references/common/verifying.md`.

For **B2E**, activate a second language, author or retrieve its translation metadata, build against the target org, deploy only the target bundle and label metadata, then change the authenticated user's Language and reload.

For **B2C**, verify configured site languages, URL routing, `SFDC_ENV.language`, the full-reload language switcher, localized local preview, guest GraphQL access, and cache clearing as detailed in the framework reference.

Deploying the bundle, labels, and translations does not publish the Experience site. Treat `sf community publish` as a separate go-live mutation: show the exact site and target org, then wait for explicit user confirmation immediately before running it.

**If it doesn't render:** check the gotchas in `references/common/gotchas.md`:
- Unregistered manifest key (Step 3 missed a label)
- API-version mismatch (built against a different org)
- Stale label cache (React: `i18next_res_*` in localStorage; Angular: in-memory, reload refetches)
- B2C guest GraphQL 403 (`GraphQLApiOrgPrefForGuestUsers` is not admin-enabled)
- B2C route, site language, and `SFDC_ENV.language` disagree

**Completion criterion:**
Labels render in ≥2 locales, or the blocking gotcha is identified.

**Pause:** "To verify: activate a second language in Translation Workbench, author a translation (I can scaffold the XML), build/deploy, and reload. Want me to scaffold the translation file for [language]? [y / I'll do it manually]"

---

## Edge cases: handle gracefully

- **Already-localized code**: detect existing translation-call usage / a populated manifest; offer to *add to* the setup rather than re-scaffold everything.
- **No strings found**: report cleanly and stop; do not invent work.
- **App has no i18n setup yet**: Step 4 scaffolds the two files first before Step 3 can register anything.
- **Partial setup** (manifest exists but init missing, or vice-versa), reconcile what's present; never clobber existing wiring.
- **B2B site**: explicitly reject it. B2C support does not imply B2B support.

---

## Guardrails: never regress these

1. **Never machine-translate deployable metadata.** Scaffold one well-formed `<Translations>` document with a closed `<customLabels>` block per label and XML-escaped English source text. Preserve placeholders and parse both metadata files before completion. Translators replace scaffold values by hand or through Translation Workbench; never call an MT API for them.
2. **Never register a key that has no label.** Manifest entry count must equal label count (Step 3 criterion). An unregistered key renders as its own literal name with no console warning. It's the most common localization bug.
3. **Never clobber existing i18n wiring.** If Step 4 finds an existing `initI18n()`, reconcile (add the manifest import if missing) rather than replace the whole file.
4. **Every file must be customer-safe.** No `webapps`, core-only paths, or internal infrastructure references anywhere. Write as if for an external customer in an SFDX project.
5. **Never publish a B2C site implicitly.** Metadata deployment and site publication are separate. Run `sf community publish` only after showing the site and org and receiving explicit confirmation for that publication.

---

## Commands & layout

```text
<project-root>/                          ← SFDX project root
└── force-app/main/default/
    ├── labels/CustomLabels.labels-meta.xml          ← English base labels
    ├── translations/<locale>.translation-meta.xml   ← one per translated language
    └── uiBundles/<your-bundle>/
        ├── package.json
        └── src/
            ├── i18n/
            │   ├── index.ts              ← init wiring (you write this once)
            │   └── label-manifest.ts     ← list of labels to fetch (you maintain this)
            └── components/               ← components call the translation function
```

| Command | Run from | Purpose |
|---|---|---|
| Install i18n dependencies (see `references/<framework>/localize.md`) | UI bundle dir | Install the framework's i18n libraries (Step 4) |
| `npm run build` | UI bundle dir | Build the app (API version bakes in, set target-org first) |
| See `references/<framework>/verifying.md` | Project root | Review and deploy the exact target bundle + changed label metadata to an explicit org |
| `sf project retrieve start --metadata Translations:<locale>` | Project root | Pull translations authored in Translation Workbench |

---

## Pre-flight checklist: completion criteria for the whole run

- [ ] Every confirmed string has both a `CustomLabels` entry and a translation call
- [ ] `label-manifest.ts` entry count == label count (no unregistered keys)
- [ ] i18n wiring present and called once at boot; manifest wired into the label backend/loader
- [ ] B2C only: guest GraphQL preference confirmed, `USER_DEFAULT` configured, and site language route matches `SFDC_ENV.language`
- [ ] B2E only: no fallback override; the framework reference's default is preserved
- [ ] Labels render in ≥2 locales (or the blocking gotcha is named)
- [ ] No hand-written machine translations landed in `*-meta.xml` (only scaffold-and-guide)
- [ ] Both metadata files parse as XML; the translation scaffold has one `<Translations>` root and one closed block per label
