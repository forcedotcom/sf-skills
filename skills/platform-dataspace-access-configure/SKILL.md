---
name: platform-dataspace-access-configure
description: "Use this skill to configure or inspect Salesforce Data Cloud DataSpace access for permission sets. Grants dataspace-level access via MDAPI PermissionSet XML with dataspaceScopes elements, optionally grants object-level access to DMO, DLO, or CIO objects via the Object Access Grants Connect API, and inspects existing scopes via read-only PermissionSet metadata retrieval. TRIGGER when: user needs to create or update a permission set with DataSpace access, grant access to a specific dataspace, list permission sets with access to a DataSpace, configure dataAccessLevel/objectAccessLevel, add RBAC object access grants, or list/remove object access grants for a permission set + DataSpace pair. DO NOT TRIGGER when: the task is a generic permission set without dataspace access (use platform-permission-set-generate), the request is about data ingestion/streams (use data360-prepare), or the work involves creating dataspaces themselves rather than granting access to them."
metadata:
  version: "1.0"
  domains: ["Platform", "Data 360"]
  minApiVersion: "67.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["python3"]
      semver: ">=3.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# platform-dataspace-access-configure

Configure DataSpace access in Salesforce Data Cloud using a two-layer model:

1. **DataSpace-level access** — grant a `PermissionSet` access to a DataSpace by embedding a `<dataspaceScopes>` element in the permission set XML and deploying via MDAPI.
2. **Object-level access (optional)** — grant that permission set access to specific DMO / DLO / CIO objects within the DataSpace using the Object Access Grants Connect API.

The MDAPI layer is required to establish the PermissionSet → DataSpace linkage. The Connect API layer is optional and only needed when access should be scoped to specific objects rather than governed entirely by data governance policies.

---

## Decide the Case First

Pick exactly one case from the table below before writing any files. Each case has a different output shape.

| Case | User intent | Permission set state | Files to emit |
|---|---|---|---|
| **A. Create new permset with DS access** | "create a permission set called X with dataspace scope Y" | does NOT exist yet | `permissionsets/<Name>.permissionset-meta.xml` **and** `package.xml` |
| **B. Add DS access to existing permset** | "grant existing permission set X access to dataspace Y" | already deployed (may contain other permissions) | patched `permissionsets/<Name>.permissionset-meta.xml` **and** `package.xml` — see Case B workflow below |
| **C. Object-level grant only** | "grant permset X access to object Z (in dataspace Y)" — permset + scope already configured | already deployed with `dataspaceScopes` | `api-request.json` (Connect API body). NO permission set XML, NO `package.xml` |
| **D. Inspect existing DS access** | "which permission sets have access to dataspace Y?" | any | chat/report only. NO deployable files, NO runtime API mutation |

Only emit the files listed for the case you picked. Emitting Case A/B files for a Case C prompt (or vice versa) is a correctness failure — extra files change the deployment shape.

> **Case B — critical:** PermissionSet MDAPI deploy is a **full metadata replace**. Every `<objectPermissions>`, `<fieldPermissions>`, `<userPermissions>`, `<tabSettings>`, `<applicationVisibilities>`, `<recordTypeVisibilities>`, `<customPermissions>`, `<pageAccesses>`, `<classAccesses>`, `<customMetadataTypeAccesses>`, `<customSettingAccesses>`, `<externalDataSourceAccesses>` element you omit from the redeploy is **deleted from the org**. Before adding `<dataspaceScopes>` to an existing permset, retrieve the current XML and patch it — do not hand-author from scratch.

### Case B workflow

1. Retrieve the existing permission set:
   ```bash
   sf project retrieve start --metadata PermissionSet:<Name> --target-org <alias>
   ```
2. Open the retrieved `permissionsets/<Name>.permissionset-meta.xml`. Keep every element already there.
3. Insert the `<dataspaceScopes>` block for the target DataSpace (element order in the file does not matter for MDAPI). If the file already has a `<dataspaceScopes>` block **for this same DataSpace**, replace only that block. Leave every `<dataspaceScopes>` block for other DataSpaces untouched — one block per DataSpace. For a requested scope removal, remove only the matching block and deploy; omitting the block revokes that DataSpace grant. Verify by retrieving the PermissionSet and confirming the matching `<dataspaceScopes>` block is absent.
4. Write `package.xml` listing the permset in `<members>`.
5. Redeploy with `sf project deploy start`.

---

## When This Skill Owns the Task

Trigger this skill when the user wants to:
- Create a permission set that grants access to a Data Cloud DataSpace
- Add or modify `dataspaceScopes` on an existing permission set
- Grant a permission set access to specific DMO / DLO / CIO objects in a DataSpace
- List which permission sets have a DataSpace scope and inspect its access levels
- Configure `dataAccessLevel` and `objectAccessLevel` for a DataSpace scope
- List or remove object access grants for a permission set + DataSpace pair

Delegate elsewhere when:
- The permission set has no DataSpace access at all → `platform-permission-set-generate`
- The task is creating the DataSpace itself → `data360-orchestrate`
- The task is ingesting data or configuring streams → `data360-prepare`

---

## Layer 1 — DataSpace-Level Access (MDAPI)

Embed a `<dataspaceScopes>` element inside the `PermissionSet` XML. Deploy with MDAPI.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Data Cloud Analyst</label>
    <description>Data cloud analyst access to the default dataspace</description>
    <hasActivationRequired>false</hasActivationRequired>
    <dataspaceScopes>
        <dataspaceScope>default</dataspaceScope>
        <dataAccessLevel>ALL</dataAccessLevel>
        <objectAccessLevel>BY_POLICY</objectAccessLevel>
    </dataspaceScopes>
</PermissionSet>
```

### Element Rules

| Element | Required | Valid Values | Purpose |
|---|---|---|---|
| `<dataspaceScopes>` | yes | parent element (plural) | Container for a single dataspace scope grant |
| `<dataspaceScope>` | yes | DataSpace API name (e.g. `default`) | Which DataSpace this grant is for |
| `<dataAccessLevel>` | yes | `NONE`, `CONTROLLED_BY_PARENT`, `ALL` | Row-level data access within the DataSpace |
| `<objectAccessLevel>` | yes | `BY_POLICY`, `ALL_IN_DATASPACE` | Object-level access. `BY_POLICY` defers to data governance policies. `ALL_IN_DATASPACE` is only allowed when `dataAccessLevel` is `CONTROLLED_BY_PARENT` |

### Common Mistakes

- **Wrong parent name** — using `<dataspaceScopeAccess>` instead of `<dataspaceScopes>`. Deployment fails silently or with cryptic errors.
- **Wrong child name** — using `<dataspaceScopeName>` instead of `<dataspaceScope>`.
- **Wrong enum values** — `ViewAllRows` / `Read` / `OWNER` / `EDIT` are not valid. Use `NONE`, `CONTROLLED_BY_PARENT`, or `ALL` for `dataAccessLevel`; use `BY_POLICY` or `ALL_IN_DATASPACE` for `objectAccessLevel`. See Element Rules table for allowed combinations. Deployment error `-379999659` means invalid enum.
- **Multiple scopes in one element** — `<dataspaceScopes>` grants access to exactly one DataSpace. To grant access to multiple, add multiple `<dataspaceScopes>` blocks.

### Package Layout (Case A and Case B)

A deployable bundle for Layer 1 always contains **both** files:

```text
<output-root>/
  package.xml
  permissionsets/<Name>.permissionset-meta.xml
```

`package.xml` (required — list every permission set being deployed in `<members>`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Data_Cloud_Analyst</members>
        <name>PermissionSet</name>
    </types>
    <version>67.0</version>
</Package>
```

Deploy:

```bash
sf project deploy start --source-dir force-app/main/default/permissionsets/ --target-org <alias>
```

---

## Read-Only DataSpace Scope Inspection — Case D

Use Case D when the user asks which permission sets have access to a DataSpace,
or asks to inspect `dataAccessLevel` and `objectAccessLevel` without making a
change.

**Never query `DataspaceScope` or `DataspaceScopeAccess` with SOQL.** Those
objects are not a supported query surface for this relationship. Do not try
SOQL as discovery, fallback, or troubleshooting.

1. Retrieve PermissionSet metadata into an isolated temporary local project and
   output directory. Do not retrieve into the user's existing metadata tree. Save
   the skill repository path first (as an absolute path if possible):
   ```bash
   REPO_ROOT="<absolute/path/to/sf-skills-internal>"  # or $(pwd) if you're in the repo root
   WORK_DIR=$(mktemp -d)
   sf project generate --name dataspace-scope-inspection --output-dir "$WORK_DIR"
   cd "$WORK_DIR/dataspace-scope-inspection"
    sf project retrieve start --json \
      --metadata "PermissionSet:*" --target-org <alias> \
      --output-dir "$WORK_DIR/retrieved"
    ```
    Inspect the JSON result before continuing. A nonzero command status, a failed
    `result.status`, warnings, or an unexpectedly low `result.fileProperties`
    count means the retrieve may be incomplete. Report that limitation rather
    than treating the result as empty, and do not fall back to SOQL.
2. Run the inspection script from the skill directory (do not rely on relative paths
   after `cd` changed the working directory). Supply the retrieved directory and optional DataSpace name:
   ```bash
   "$REPO_ROOT/skills/platform-dataspace-access-configure/scripts/inspect-dataspace-scopes.sh" \
     "$WORK_DIR/retrieved" "<DataSpace API name, if given>"
   ```
   Report the output to the user, one result per line.

Case D is read-only with respect to the org. Do not deploy metadata, assign a
permission set, execute Apex, perform record DML, or make a POST, PUT, PATCH, or
DELETE request. Do not generate `package.xml`, PermissionSet XML, or
`api-request.json` in the user's workspace as part of inspection. Remove the
temporary work directory after reporting: `rm -rf "$WORK_DIR"`. The scope-level
`objectAccessLevel` is not an inventory of explicit object grants; inspect those
separately with the read-only object-access-grants endpoint only when requested.

---

## Layer 2 — Object-Level Access (Connect API) — Case C

Only needed when `objectAccessLevel` is not `BY_POLICY`, or when governance policies do not cover the target objects. Grants are runtime — **no MDAPI deploy, no `package.xml`, no permission set XML**. The only artifact for a Case C task is a single `api-request.json` describing the Connect API call.

### Resolve the API version first

Every Connect API `endpoint` in this layer contains an `/services/data/v<apiVersion>/…` segment. **Do not hardcode `v67.0`.** Resolve the target org's actual API version before writing the envelope so the request matches the org's supported surface:

```bash
sf org display --target-org <alias> --json | jq -r '.result.apiVersion'
```

- Substitute the returned value (e.g. `67.0`, `68.0`) into the `endpoint` as `v<apiVersion>`.
- If the org can't be queried (offline authoring, no alias yet), fall back to the `minApiVersion` from this skill's frontmatter (`67.0`) — the endpoint was introduced there and any newer version accepts the same body.
- If the user explicitly specifies a version in the prompt, use that verbatim.

In the templates below, `{apiVersion}` is a placeholder. Replace it with the resolved API version (e.g., `67.0`, `68.0`) before emitting `api-request.json`.

### `api-request.json` — canonical shape

Emit the request as a self-describing envelope with `method`, `endpoint`, `headers`, `body`, and `expectedResponse`. Do NOT emit only the body — reviewers and downstream tooling read the envelope.

```json
{
  "method": "POST",
  "endpoint": "/services/data/v{apiVersion}/ssot/data-governance/object-access-grants",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "permissionSetName": "Data_Cloud_Analyst",
    "dataSpaceName": "default",
    "objectApiName": "Account__dlm"
  },
  "expectedResponse": {
    "status": 201,
    "body": {
      "permissionSetName": "Data_Cloud_Analyst",
      "dataSpaceName": "default",
      "objectApiName": "Account__dlm"
    }
  }
}
```

### Bulk Grant

Same `api-request.json` envelope shape. `endpoint` gains the `/actions/bulk-create` suffix, `body.objectApiName` is replaced by the list-valued `body.objectApiNames`, and `expectedResponse` omits the `body` field because bulk responses return per-object status entries rather than the flat request payload (see Gotchas below).

```json
{
  "method": "POST",
  "endpoint": "/services/data/v{apiVersion}/ssot/data-governance/object-access-grants/actions/bulk-create",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "permissionSetName": "Data_Cloud_Analyst",
    "dataSpaceName": "default",
    "objectApiNames": ["Account__dlm", "Contact__dlm", "Opportunity__dlm"]
  },
  "expectedResponse": {
    "status": 201
  }
}
```

### List Grants

Same envelope shape with `method: "GET"`, query parameters on the `endpoint`, and no `body`.

```json
{
  "method": "GET",
  "endpoint": "/services/data/v{apiVersion}/ssot/data-governance/object-access-grants?permissionSetName=Data_Cloud_Analyst&dataSpaceName=default",
  "headers": {
    "Accept": "application/json"
  },
  "expectedResponse": {
    "status": 200
  }
}
```

### Revoke Grant

Same envelope shape with `method: "DELETE"`, the object API name as a path segment, and `expectedResponse.status: 204` (No Content).

```json
{
  "method": "DELETE",
  "endpoint": "/services/data/v{apiVersion}/ssot/data-governance/object-access-grants/Account__dlm?permissionSetName=Data_Cloud_Analyst&dataSpaceName=default",
  "headers": {
    "Accept": "application/json"
  },
  "expectedResponse": {
    "status": 204
  }
}
```

### Object Types

- **DMO** (Data Model Object) — unified profile objects, suffix `__dlm`
- **DLO** (Data Lake Object) — raw ingested data, suffix `__dll`
- **CIO** (Calculated Insight Object) — computed metrics, suffix `__cio`

---

## Combined Setup — Case A + Case C from a Cold Start

Use this section ONLY when the user is starting from nothing and asks for both the permset+scope AND per-object grants in a single request. If the user's prompt is only about the Connect API grant (Case C) — for example "grant Account__dlm access; the permset and dataspace scope already exist" — SKIP this section entirely and emit only `api-request.json` from Layer 2.

The commands below are operator-facing `sf` CLI invocations (a runnable cold-start walkthrough), NOT the artifact you emit. For a normal Case C task the artifact is a single `api-request.json` envelope as documented in Layer 2 above.

**Goal:** Grant `Data_Cloud_Analyst` permission set access to `Account__dlm` and `Contact__dlm` in the `default` DataSpace.

**Step 1 — Deploy PermissionSet with DataSpace scope (MDAPI):**

```xml
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Data Cloud Analyst</label>
    <description>Data cloud analyst access to the default dataspace</description>
    <hasActivationRequired>false</hasActivationRequired>
    <dataspaceScopes>
        <dataspaceScope>default</dataspaceScope>
        <dataAccessLevel>ALL</dataAccessLevel>
        <objectAccessLevel>BY_POLICY</objectAccessLevel>
    </dataspaceScopes>
</PermissionSet>
```

```bash
sf project deploy start --source-dir permissionsets/ --target-org <alias>
```

**Step 2 — Grant object access (Connect API):**
*(Required here because the `default` DataSpace has no governance policies covering `Account__dlm` and `Contact__dlm`. Skip Step 2 when `BY_POLICY` policies already govern the target objects — Layer 1 alone is sufficient.)*

Resolve the org's API version first (see [Resolve the API version first](#resolve-the-api-version-first) above), then substitute it into the `--path` value:

```bash
API_VERSION=$(sf org display --target-org <alias> --json | jq -r '.result.apiVersion')

sf org api rest --target-org <alias> \
  --method POST \
  --path "/services/data/v${API_VERSION}/ssot/data-governance/object-access-grants/actions/bulk-create" \
  --body '{
    "permissionSetName": "Data_Cloud_Analyst",
    "dataSpaceName": "default",
    "objectApiNames": ["Account__dlm", "Contact__dlm"]
  }'
```

**Step 3 — Verify:**

```bash
sf org api rest --target-org <alias> \
  --path "/services/data/v${API_VERSION}/ssot/data-governance/object-access-grants?permissionSetName=Data_Cloud_Analyst&dataSpaceName=default"
```

---

## Rules and Constraints

| Rule | Reason |
|---|---|
| Use `<dataspaceScopes>` (plural) as parent, `<dataspaceScope>` (singular) as child | XML schema requirement; other names deploy-fail |
| `dataAccessLevel` values: `NONE`, `CONTROLLED_BY_PARENT`, `ALL` only | Other values (e.g. `OWNER`, `ViewAllRows`) are rejected |
| `objectAccessLevel` values: `BY_POLICY`, `ALL_IN_DATASPACE` only | Other values (e.g. `READ`, `EDIT`, `Read`) are rejected. `ALL_IN_DATASPACE` requires `dataAccessLevel=CONTROLLED_BY_PARENT` |
| Prefer `BY_POLICY` when data governance policies exist | Delegates row/column filtering to central policy — no per-object grants needed |
| One `<dataspaceScopes>` block per DataSpace | Repeat the block for multiple DataSpaces on the same permission set |
| Org must have Data Cloud provisioned to deploy `<dataspaceScopes>` | On non-Data-Cloud orgs, the element is ignored or rejected |
| Do not query `DataspaceScope` / `DataspaceScopeAccess` via SOQL | Not queryable; use Case D PermissionSet Metadata API retrieval to inspect existing scopes. Never use SOQL as a fallback. |

---

## Gotchas

| Issue | Resolution |
|---|---|
| Deployment fails with error `-379999659` | Check enum values — `dataAccessLevel` must be `NONE`/`CONTROLLED_BY_PARENT`/`ALL`; `objectAccessLevel` must be `BY_POLICY`/`ALL_IN_DATASPACE` |
| Permission set deploys but users still can't query DataSpace data | Layer 2 not applied — objects need explicit grants if `objectAccessLevel != BY_POLICY` |
| Bulk-create returns `AlreadyExists` for some objects | Idempotent — safe to retry; response shows per-object status |
| Connect API returns 404 for object grants endpoint | Org lacks Data Cloud provisioning, or the resolved API version is below the minimum. The endpoint was introduced in `v67.0` — re-run `sf org display --json` to confirm the org's `apiVersion` field is `67.0` or later, and substitute that value into the `endpoint` path |
| Retrieved PermissionSet XML shows different element names than deployed | Metadata API sometimes echoes legacy names on retrieve — always author with current names |
