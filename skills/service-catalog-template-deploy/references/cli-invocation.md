# CLI Invocation Reference — Deploy Unified Catalog Template

Every operation runs through the **Salesforce CLI**. The Connect API routes are plain REST
(`sf api request rest`); the access self-heal and activation use `sf org assign …` and
`sf data …`. This skill runs a preflight probe, a read (resolve), a write (deploy), an activation, and
a read (verify).

- `--method GET|POST` — the verb.
- `--body '<json>'` (`-b`) — the POST payload. Accepts an inline JSON string, `@file.json`, or `""`
  for an empty body. GET takes no `--body`.
- `--target-org <alias>` (`-o`) — pick the org; omit to use the default-org config.
- `-i` / `--include` — prepend the HTTP status line + headers (use it to read a `403`/`404`/`500`).
- **No `--json` flag exists** on `sf api request rest`. Do not pass one.
- Path is pinned to **`v67.0`** (the version the shapes below match); the routes do not exist below
  `v65.0`. Use a higher version only if the org's own version exceeds v67.0.

## Response shape — RAW body, no wrapper

`sf api request rest` prints the **raw Connect response body** — there is **no** `{status_code, body}`
envelope around it. Read the fields **top-level**:

- GET templates → top-level `serviceProcessTemplateOutputRepresentation` (array)
- POST deploy → top-level `{ deploymentResult: string, status: "SUCCESS"|"FAILURE", templateId: string }`

**The deploy is synchronous** — there is no `jobId` and no poll endpoint for the single-template
route. Verify by re-reading (below). (Only the out-of-scope **bulk** endpoint returns a `batchJobId`.)

To read the HTTP status explicitly, add `-i`. A `403` + `FUNCTIONALITY_NOT_ENABLED [ServiceAutomationFamily]`
means the org lacks Unified Catalog; a `404` + `NOT_FOUND` means the route is below its minimum API
version (this skill targets **v67.0**; the routes do not exist below v65.0).

---

## Step 0 — Preflight access check (behavior-based, self-healing)

Unified Catalog access is **per-user**. The Step 1 GET is *also* the access probe — don't pre-check
with SOQL. Run it with `-i` to read the status:

- **`HTTP 200`** → access present (via `UnifiedCatalogAdmin` **or any persona the user already holds**
  — `UnifiedCatalogAgent`, `UnifiedCatalogCommunityUser`, or a custom equivalent). Accept it; assign
  nothing. Continue to name resolution.
- **`403` + `FUNCTIONALITY_NOT_ENABLED [ServiceAutomationFamily]`** → self-heal, in order, then
  re-probe **once**:

  ```bash
  sf org assign permsetlicense --name UnifiedCatalogAdminPsl   # layer 2: entitlement
  sf org assign permset        --name UnifiedCatalogAdmin       # layer 3: the SET flips 403→200
  # then re-run the Step 1 GET -i once
  ```

  - Now `200` → continue.
  - Still `403` → the org lacks the Unified Catalog **license** (layer 1), which a user assignment
    cannot fix. **Report and stop.** Never loop the heal.

  **The re-probe GET is the arbiter — not the assign command's exit code.** If the user was already
  assigned, `sf org assign permset` prints a **`Duplicate PermissionSetAssignment`** failure and exits
  non-zero. That is **benign** — the assignment already exists. Do not abort on it; judge success only
  by the re-probe returning `200`. (`sf org assign permsetlicense` on an existing assignment is a clean
  no-op.)

Why both assignments: the permission-set **license** (`permsetlicense`) is the entitlement and is
**necessary but not sufficient** — the permission **set** (`permset`) is what actually flips the route
from `403` to `200`. Assigning only the PSL still `403`s.

There is **no** "Designer" permission set to assign — `UnifiedCatalogAdmin` is the verified-sufficient
heal target. (A `PermissionsUnifiedCatalogDesignGAPerm` user-permission bit exists, but no dedicated
permission set carries it.) The three UC personas and their gating permission:

| Permission set | Carries |
|----------------|---------|
| `UnifiedCatalogAdmin` | `PermissionsUnifiedCatalogAdminPerm` — **verified to unlock the route** |
| `UnifiedCatalogAgent` | `PermissionsUnifiedCatalogAgentPerm` |
| `UnifiedCatalogCommunityUser` | `PermissionsUnifiedCatalogRuntimePerm` + `PermissionsAccessToServiceProcess` |

---

## Step 1 — Re-fetch the catalog and resolve the name

```bash
sf api request rest \
  '/services/data/v67.0/connect/service-automation/service-process/get-all-templates' \
  --method GET -i
```

`resolve-template.mjs` reads the top-level `serviceProcessTemplateOutputRepresentation` and matches the
user's named template case-insensitively against each `name`, returning an `action`:

- **exactly one exact-name match** → `DEPLOY`; the script returns `resolved.id` and
  `templateDependencyMetadata`, proceed
- **two or more matches** → `STOP_AMBIGUOUS`; list matches, ask for the exact name — **never pick the
  first**. This also covers a **category term** (e.g. "access") that is not itself a template name but
  appears in ≥2 template names: the request is ambiguous, so `matchCount` is the candidate count
- **zero matches, fewer than two near-matches** → `STOP_NOT_FOUND`; report requested name + list
  available names, never deploy a near-match

An exact single match short-circuits before the substring fallback, so naming an exact template (even
one whose words appear in other names) always deploys that one. Never reuse an `id` carried over from
the search skill — re-resolve from this live fetch every run.

Each element (`ServiceProcessTemplateOutputRepresentation`) carries `id`, `name`, `description`,
`type`, and `templateDependencyMetadata[]`.

- **`id`** is a **name-style string** (e.g. `itsmserviceprocess_RequestNewLaptop`), **not** an 18-char
  Salesforce Id. Use it verbatim in the deploy path.
- **`type`** is a category such as `"Service"` — **not** `Intake`/`Fulfillment` (those are *dependency*
  `templateType` values, below).

Each dependency (`DependencyDetails`) — **enum values come back in SCREAMING_SNAKE_CASE and must be
echoed verbatim**:

| Field | Live value (verbatim) |
|-------|-----------------------|
| `templateApiName` | API name of the dependency flow, e.g. `sfdc_internal__ItServiceRequestNewLaptopIntake` |
| `templateType` | `INTAKE` \| `FULFILLMENT` |
| `templateDependencyType` | `FLOW` |
| `dependencyDeploymentMedium` | `APP_FRAMEWORK` |
| `requiresDeploymentInput` | boolean — if any is `true`, collect input before deploying |

Verbatim example (live `templateDependencyMetadata` for "Request New Laptop"):

```json
[
  {
    "dependencyDeploymentMedium": "APP_FRAMEWORK",
    "requiresDeploymentInput": false,
    "templateApiName": "sfdc_internal__ItServiceRequestNewLaptopIntake",
    "templateDependencyType": "FLOW",
    "templateType": "INTAKE"
  }
]
```

---

## Step 2 — Build the deploy body

**This transformation runs in `scripts/build-deploy-payload.mjs`, not by hand** — iterating
dependencies, picking a fallback key, and passing enums through verbatim is a fixed algorithm
(authoring standard A9), so the skill invokes the script rather than constructing the body in prose.
The shape it produces is documented below for reference.

Build `flowTemplates[]` from `templateDependencyMetadata` — one element per dependency. **Echo every
enum verbatim** from the fetched metadata (SCREAMING_SNAKE_CASE); only fall back to an alternate source
key when the primary is absent, and **never normalize casing or hardcode a literal**:

```jsonc
// for each dep in templateDependencyMetadata:
{
  "templateType":               dep.templateType,                                 // verbatim: "INTAKE" | "FULFILLMENT"
  "templateApiName":            dep.templateApiName ?? dep.dependencyApiName,     // first non-empty
  "templateDependencyType":     dep.templateDependencyType ?? dep.dependencyType, // verbatim: "FLOW"
  "dependencyDeploymentMedium": dep.dependencyDeploymentMedium,                   // verbatim: "APP_FRAMEWORK" — NOT hardcoded
  "templateVariables":          {}                                               // {} unless deployment inputs collected
}
```

Do **not** write `"AppFramework"`/`"Intake"`/`"Flow"` (title-case) or hardcode
`dependencyDeploymentMedium`. The live API rejects mismatched enum casing. The verified-working body
for "Request New Laptop" was exactly:

```json
{"flowTemplates":[{"templateType":"INTAKE","templateApiName":"sfdc_internal__ItServiceRequestNewLaptopIntake","templateDependencyType":"FLOW","dependencyDeploymentMedium":"APP_FRAMEWORK","templateVariables":{}}]}
```

Full deploy call (send only the optional keys the user supplied; omit the rest entirely). Pass the
body inline or, for anything non-trivial, from a file with `--body @deploy-body.json`:

```bash
sf api request rest \
  '/services/data/v67.0/connect/service-automation/template/deploy/<templateId>' \
  --method POST \
  --body '{
    "flowTemplates": [ /* built above */ ],
    "description":    "<desc>",
    "isActive":       true,
    "deploymentMode": "Async",
    "catalog":        "<catalog>",
    "category":       "<category>"
  }'
```

Only `flowTemplates` is always present (even if `[]`). `description` / `isActive` / `deploymentMode`
(`Async` | `CrossOrg` | `Sync`) / `catalog` / `category` appear **only if the user supplied them**.
Read the top-level `status` from the response.

> **Activation caveat (live-verified):** the deploy POST lands the resulting `Product2` with
> **`IsActive=false`** regardless — passing `isActive: true` in the body is **not** a verified
> activation path. The reliable, live-proven way to activate is the post-deploy DML in Step 3. Treat
> the body `isActive` as an unverified optional passthrough; rely on Step 3 for activation.

### `serviceProcessName` drift — read this

The **67.0 OAS marks `serviceProcessName` as a required body field**, but the **tested ITXM v66
client deliberately omits it**, with a regression test asserting the minimal body is exactly
`{ "flowTemplates": [] }` and the comment: *"serviceProcessName was removed (Salesforce API rejects
it on the deploy endpoint)."* These two authoritative sources disagree.

**Resolution:** build the body **without** `serviceProcessName` first (matching the tested client). If
the org's schema requires it and rejects the body, retry once **with** `serviceProcessName` set to the
Service Process name. Either way, keep `serviceProcessName` for the return/display value — it is not
necessarily sent to the API.

---

## Step 3 — Activate, then verify by re-reading

A deployed Service Process must end up **active**, and the POST leaves `Product2.IsActive=false`. The
`serviceProcessName` is **user-supplied**, so it must never be interpolated into a Bash command or a
SOQL literal — a name carrying shell metacharacters or a stray quote could execute during command
construction or alter the query and touch an unintended `Product2`. The resolve→activate→verify
sequence therefore runs in `scripts/activate-verify.mjs` (Agent Safety + authoring standard A9), which
takes the name as an **argument** (no shell interpolation), escapes it for the SOQL literal, and
invokes `sf` via an argument array (`shell:false`):

```bash
# pass the name as an argument — the script never builds a shell/SOQL string from it.
# add --no-activate only if the user explicitly asked to leave the Service Process inactive.
node "<skill_dir>/scripts/activate-verify.mjs" "<serviceProcessName>" --target-org <alias>
```

Internally the script runs the equivalent of: resolve the deployed `Product2` by name (`WHERE
Name='…' AND UsedFor='ServiceProcess' ORDER BY CreatedDate DESC LIMIT 1`, name SOQL-escaped),
conditionally `sf data update record … -v "IsActive=true"` when it is not already active, then re-read
to confirm. It prints `{ found, id, isActive, activated, verified }` and exits 0. If an `sf` query
itself fails (auth/transport/malformed — not a genuine absence), it instead prints
`{ error: true, detail, found, id, isActive: null, activated, verified: false }` and exits **non-zero**:
treat that as a **check failure**, not a verified not-found — report the `detail` and do not claim the
deploy did or did not land.

The deployed surface for a Service Process is the `Product2` (with `UsedFor='ServiceProcess'`) plus its
intake/fulfillment Flow(s) — the Flows land active on their own; only the `Product2` needs activating.
There is no separate `ServiceProcess`/`CatalogItem` sobject to publish. Report success only when the
script's `verified` is `true` (the re-read confirms the Service Process exists **and `IsActive=true`**,
unless `--no-activate`).

> Add `--target-org <alias>` to the script (or any `sf data …` / `sf org …` call) to target a specific
> org; omit to use the default.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Enum casing | Live API returns `INTAKE`/`FULFILLMENT`/`FLOW`/`APP_FRAMEWORK` (SCREAMING_SNAKE). Echo verbatim; never title-case or hardcode `dependencyDeploymentMedium`. |
| Template `id` shape | Name-style string (`itsmserviceprocess_RequestNewLaptop`), not an 18-char Id. Use verbatim in the deploy path. |
| Template-level `type` | A category like `"Service"` — not `Intake`/`Fulfillment` (those are *dependency* `templateType` values). |
| `serviceProcessName` required vs rejected | Build without it first; retry once with it if the org rejects the body (see drift note). |
| Expecting a `{status_code, body}` wrapper | There is none — `sf api request rest` prints the **raw** body. Read `status`/`serviceProcessTemplateOutputRepresentation` top-level; use `-i` for the HTTP status. |
| Name → 0 templates | Stop; list available names; never deploy a near-match. |
| Name → 2+ templates | Stop; list matches; ask for the exact name; never pick the first. |
| POST `status: FAILURE` | Surface `deploymentResult` verbatim; stop; do not retry blindly. |
| `403` / `FUNCTIONALITY_NOT_ENABLED` on the GET probe | Per-user gap. Self-heal (Step 0): assign `UnifiedCatalogAdminPsl` **and** `UnifiedCatalogAdmin`, re-probe once. Still `403` = missing org license → report and stop. The permission **set** flips it, not the license alone. |
| Deployed `Product2` is `IsActive=false` | Expected — the POST does not activate. Activate in Step 3 via `sf data update record`. Passing body `isActive:true` is unverified; DML is the reliable path. |
| `404` / `NOT_FOUND` on GET or POST | The path is below the route's minimum API version — this skill targets **v67.0** (the routes do not exist below v65.0). Fix the version; do not fabricate. |
| Tempted to poll | Single-template deploy is synchronous — no job id; verify by re-read. |
| `requiresDeploymentInput: true` | Collect values in Phase 3; place them in `templateVariables`. |
| `INVALID_LOGIN` / auth error | The org's sf CLI auth has expired — re-authenticate with `sf org login web`. |
