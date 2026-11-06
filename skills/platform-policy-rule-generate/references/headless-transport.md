# Headless Transport — `/headless/metadata` MD-CRUD

The transport for H360 policy-rule **create / read / update** is the headless-360 MCP server's `/headless/metadata` MD-CRUD endpoint, called through `dispatch` (for CREATE/UPDATE) and `dispatch_readonly` (for the GET read-back). **DELETE is a different surface**: Core has no real metadata delete (a `/headless/metadata` DELETE 405s or no-ops), so a policy is deleted over the Data 360 MCP Data Governance Access Policy tool `d360_data_governance_access_policy_delete` (see the DELETE section below). There is no `sf`/MDAPI fallback — when the headless path is unavailable or a type/op is not onboarded, surface the gap to the operator.

Always `discover` and `describe` the operation before calling it; the shapes below are the confirmed request/response contract, not a substitute for checking `describe` against the connected server version.

**Exception for `PolicyRuleDefinition`/`PolicyRuleDefinitionSet`:** these two types have no dedicated MD-CRUD operation to describe — `discover` only surfaces the `platform-policy-rule-generate` SOR itself, whose `describe` shows `"steps": []` and `"referenced_operation_ids": []`. There is nothing to describe for this specific pair. Treat that empty result as expected, not as a blocker or an error: fall through to the request/response contract documented in this file, which is authoritative for these two types. Still run `discover`/`describe` first for any other metadata type this skill might touch.

## Request Shapes

All four requests target a **bare** `/headless/metadata` URL, with no version segment:

```text
url: /headless/metadata
```

The server resolves the API version automatically — `ORG_API_VERSION` is NOT required for this MCP path (confirmed: a bare-URL dispatch response echoed `v67.0` without the caller ever supplying it). A versioned URL (`/services/data/v{ORG_API_VERSION}/headless/metadata`) also works if `ORG_API_VERSION` is already known, but is not required on the MCP path — prefer the bare URL and let the server resolve it. Do not attempt an unversioned `dispatch_readonly GET /services/data` to discover the version over MCP — that route is not MCP-reachable (`ROUTE_NOT_FOUND`).

### CREATE — `dispatch`, `method: POST`

```json
{
  "method": "POST",
  "url": "/headless/metadata",
  "body": {
    "type": "PolicyRuleDefinitionSet",
    "fullName": "<name>",
    "xmlRep": "<single-line XML>"
  }
}
```

Response: `{"results":[{"success":true,"id":"...","fullName":"...","errors":[],...}]}`.

### UPDATE — `dispatch`, `method: PUT`

Identical body shape to CREATE, with `"method": "PUT"`.

### READ / verify — `dispatch_readonly`, `method: GET`

```json
{
  "method": "GET",
  "url": "/headless/metadata",
  "queryParams": { "type": "<Type>", "fullName": "<name>" }
}
```

The response body contains `xmlRep` with the persisted XML. Use this as the verification step after every CREATE/UPDATE, and to confirm the UI-renderable-contract check (see `SKILL.md` step 12): the parent set's `xmlRep` must carry the authored `<builderCompatible>true</builderCompatible>` (or `false` if the user opted out) plus a server-set `<builderValidated>` (observed `true` when `builderCompatible=true` was authored; do not assert a specific value).

### DELETE — Data 360 MCP `d360_data_governance_access_policy_delete` (NOT `/headless/metadata`)

Delete is **not** a `/headless/metadata` verb. Core has no real metadata delete — a `/headless/metadata` DELETE `405`s, and the metadata team's interim delete is a no-op `200` that removes nothing. Route deletes over the Data 360 MCP **Data Governance Access Policy** surface instead:

```text
Data 360 MCP: execute(tool=d360_data_governance_access_policy_delete, params={ "name": "<setDeveloperName>" })
```

A `PolicyRuleDefinitionSet` created via this skill surfaces as an **Access Policy** keyed by its developer name. `access_policy_delete` is a **whole-policy delete** — one call removes the policy **and every embedded rule** (its `PolicyRuleDefinition` members). Consequences:

- There is **no leaf-before-parent ordering** and **no discrete single-rule delete**. To drop a single rule while keeping the policy, re-author the surviving rule set via `d360_data_governance_access_policy_rule_replace`.
- Sets with the default `builderCompatible: true` appear in a plain `d360_data_governance_access_policy_list`; opted-out (`false`) sets need `includeIncompatible: true` to enumerate them. `access_policy_get` and `access_policy_delete` address sets by `name` regardless.
- Confirm the delete with `d360_data_governance_access_policy_get` by `name`: a not-found result (or the policy being absent from an `includeIncompatible` list) is the success signal.

There is no `sf` CLI fallback. On the off-core Data Cloud path this delete can fail on DC connectivity — surface that as a provisioning gap to the operator.

## `xmlRep` Newlines — Flatten Defensively

The skill's generated `.policyRuleDefinition`/`.policyRuleDefinitionSet` XML is pretty-printed with newlines. Whether a multi-line `xmlRep` survives depends on the caller's transport: when the `dispatch` tool takes `body` as a structured JSON object and the client serializes the newlines as proper `\n` string escapes, a multi-line `xmlRep` is accepted and persists cleanly (confirmed live: a pretty-printed set POSTed through the headless-360 MCP `dispatch` tool returned `success:true` and read back intact — the server normalizes formatting on storage regardless). The `'body' must be a JSON object, got an unexpected type` 400 comes from a client/transport that lets a raw, unescaped newline reach the JSON body, not from the server rejecting multi-line XML per se.

Because that failure mode is transport-dependent and invisible from inside the skill, flatten `xmlRep` to a single line as the last step before dispatch anyway — it is always accepted and sidesteps any client that mangles newlines. Flatten (e.g. strip newlines and collapse redundant whitespace between tags) without otherwise altering the XML content.

## Transient Retry

The `'body' must be a JSON object` error can also appear spuriously on an otherwise-valid body. Treat a single occurrence as a flaky tool-arg serialization glitch: retry the identical clean body once before concluding the shape is unsupported.

## HTTP Error Taxonomy

| Status / error | Meaning | Action |
|---|---|---|
| `400 FIELD_INTEGRITY_EXCEPTION "Not available for deploy for this organization"` | Type/op is on the MD-CRUD allowlist, but the org lacks the feature/perm provisioning to deploy this metadata type | Org setup gap, not a skill or transport problem — surface it to the operator; do not fall back to CLI on this error alone (CLI will hit the same org gate). |
| `400 UNSUPPORTED_OPERATION` | The type/op is genuinely not on the MD-CRUD allowlist | Onboarding gap — surface it to the operator; there is no CLI fallback for this workflow. |
| `404` (on GET) | Type/op is allowlisted; the named member does not exist | Expected result for a not-yet-created component — not an error. |
| `405` / no-op `200` (on a `/headless/metadata` DELETE) | Core has no real metadata delete — the verb 405s, and the interim delete is a no-op 200 that removes nothing | Do not delete via `/headless/metadata`. Route the delete over the Data 360 MCP `d360_data_governance_access_policy_delete` tool instead (see the DELETE section above). |
| DC-connectivity error (on the Data 360 Access Policy delete) | The off-core Data Cloud delete path failed on DC connectivity | Provisioning gap — surface it to the operator; there is no `sf` CLI fallback. |

See `references/deploy-errors.md` for the full server-side error taxonomy (all errors surface on the `dispatch` path).
