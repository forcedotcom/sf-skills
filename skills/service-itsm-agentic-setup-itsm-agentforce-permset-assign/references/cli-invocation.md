# CLI Invocation — service-itsm-agentic-setup-itsm-agentforce-permset-assign

Every read and write in this skill uses the **Salesforce CLI (`sf`)** against the CLI's stored session for `--target-org <alias>`. **Never extract the access token** from `sf org display` — hand-building a raw HTTP request bypasses the CLI session and leaks a bearer token into shell context.

## `--json` rule

- `sf data query` **takes** `--json`. Results come back in a `{status, result: {records: [...]}}` envelope — that's what the classifier scripts expect.
- `sf api request rest` does **not** — its raw stdout body is already JSON. Passing `--json` here errors on some Connect endpoints.
- `sf org assign permset` **takes** `--json`. Its `result` field carries `{ successes: [...], failures: [...] }`.

## Discovery read (Phase 1)

Fixed-lookup query over the three Core-shipped Fulfiller persona `PermissionSet.Name` values (see `permset-topology.md`). The namespace on all three is `force` — do NOT filter by `NamespacePrefix`.

```bash
sf data query \
  -q "SELECT Id, Name, Label, LicenseId \
      FROM PermissionSet \
      WHERE Name IN ( \
        'IncidentFulfiller', \
        'ProblemFulfillerPermSet', \
        'ChangeRequestFulfillerPermSet' \
      )" \
  --target-org <alias> --json
```

Interpret the result:

- **≥1 row** ⇒ Branch A (assign). Ask the user which persona to assign — do NOT auto-select.
- **Zero rows** ⇒ Branch B (hand-off). The ITSM AddOn(s) are not provisioned; route to `service-itsm-agentic-setup-agentforce-studio-validate`.

There is no separate `InstalledSubscriberPackage` or namespace-wide `PermissionSetLicense` query in Phase 1 — the persona lookup above is sufficient because Core AddOn provisioning materializes the persona `PermissionSet` rows directly.

## Identity read (Phase 2a)

```bash
sf api request rest "/services/data/v67.0/" --method GET --target-org <alias>
```

Response `identity` is a URL ending in `/<orgId>/<userId>`. Take the last path segment starting with `005` as the running user Id via `scripts/resolve-target-user.mjs`. Do **not** call `USER_ID()` (Apex-only), `/chatter/users/me`, or `/connect/user-profiles/me` — those either fail against REST or 403 when Chatter/Communities is off.

For a named user, resolve by `Username`:

```bash
sf data query -q "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" \
  --target-org <alias> --json
```

## Idempotency reads (Phase 2b)

Substitute `<permsetId>` with the SELECTED persona's `Id` and `<pslId>` with the SELECTED persona's `LicenseId` (both from Phase 1's `candidates[]`).

```bash
sf data query -q "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSetId = '<permsetId>'" \
  --target-org <alias> --json > /tmp/psa-existing.json

# Only when needsPsl:true on the selected persona:
sf data query -q "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicenseId = '<pslId>'" \
  --target-org <alias> --json > /tmp/psla-existing.json
```

When the selected persona's `needsPsl:false` (its `PermissionSet` has no backing `LicenseId`), SKIP the PSLA query — pass the sentinel `NO-PSL` to `classify-assignment-state.mjs`.

## Writes (Phase 2d)

Assign the PSL first, then the permission set — the license backs the permset, and the assignment is not fully effective until the seat is held. When `needsPsl:false`, skip the PSL POST entirely and only run `sf org assign permset`.

```bash
# PSL first — POST to the sObject endpoint (no bulk API dependency). needsPsl:true only.
sf api request rest "/services/data/v67.0/sobjects/PermissionSetLicenseAssign" \
  --method POST \
  --body '{"AssigneeId":"<userId>","PermissionSetLicenseId":"<pslId>"}' \
  --target-org <alias>
```

Response envelope: `{"id":"0Pk...","success":true,"errors":[]}` on assignment; `[{"errorCode":"DUPLICATE_VALUE",...}]` when the user already holds it (treat as success).

```bash
# Permset — sf CLI subcommand, supports --on-behalf-of for a named user.
# <permsetName> is the selected persona's DeveloperName (from candidates[].Name).
sf org assign permset --name "<permsetName>" \
  --on-behalf-of <userId> \
  --target-org <alias> --json
```

Response envelope: `result.successes[]` and `result.failures[]`. A `failure.message` matching `Duplicate id` / `already has` is idempotent success.

## Verify read (Phase 4)

```bash
sf api request rest "/services/data/v67.0/actions/custom/generatePromptResponse" \
  --method GET --target-org <alias>
```

Response can be either `{actions: [ {name, ...}, ... ]}` (legacy) or `{actions: {<name>: {...}, ...}}` (newer). The Fulfiller agent-configure skill's Phase 1b provides the specific `svc_itsm_intelligence__*` names to look for; passed as the second arg to `classify-action-surface.mjs`.

## Common error responses (surface verbatim)

| Status / errorCode | Meaning | Handling |
|---|---|---|
| `400 DUPLICATE_VALUE` on PSL POST | User already holds this PSL | Idempotent success; not a failure |
| `400 INSUFFICIENT_ACCESS` on PSL POST | PSL seat exhausted | STOP the write; tell the user how many seats are in use vs licensed |
| `401 Unauthorized` on any call | CLI session expired for the target alias | `sf org login web --alias <alias>` and retry |
| `403 FUNCTIONALITY_NOT_ENABLED` on the verify GET | The `generatePromptResponse` custom-action endpoint is gated on this user | Same signal as Branch A but for the discovery route — surface it and check whether the assigned persona permset actually gates the target actions |
| `404 Not Found` on `sf org assign permset` | Permset name does not exist on this org | Re-run Phase 1 discovery; the org state may have changed |
