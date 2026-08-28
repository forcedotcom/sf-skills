---
name: service-de-channel-create-connect-insert
description: "Load when a channel's prerequisites are satisfied and CHANNEL_NAME is resolved, right before POSTing the channel-creation request to the Connect REST endpoint. Covers the shared Stage 4.1 (authProviderId lookup), Stage 4.2 (POST invocation), and Stage 4.3 (HTTP + business-error response classification, including the DUPLICATE_VALUE race). Per-type request-body shapes live in the per-type reference (whatsapp.md / line.md / apple.md / facebook.md). DO NOT load for type-specific prereqs (Stage 2-3) or for resolving CHANNEL_NAME."
metadata:
  version: "1.0"
  related-skills: service-de-channel-create
---

# Connect insert: authProviderId, POST, response classification (shared)

Full detail for Stage 4.1-4.3 of the channel insert, shared across all four types. The per-type
**request body** shape is in the matching per-type reference file; everything else here is identical
across types.

## Stage 4.1: Get authProviderId

`sf api request rest` manages the Salesforce OAuth session internally, so there's no
`{ACCESS_TOKEN}`/`{INSTANCE_URL}` to carry in shell state.

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id FROM AuthProvider WHERE DeveloperName = 'LiveMessageSetup'" \
  --json > "${SCRATCH_DIR}/authprovider.json"
```

- `records.length === 1` → record `{AUTH_PROVIDER_ID} = records[0].Id`.
- `records.length === 0` → `{ok:false, kind:"business", message:"No AuthProvider 'LiveMessageSetup' found — run the Messaging Setup wizard once on this org first"}`.

`authProviderId` is **org-global** — the same `LiveMessageSetup` `AuthProvider.Id` works for every
message type on that org, so a caller inserting multiple channels can reuse it. The value differs on
every org; always query, never hardcode.

## Stage 4.2: POST to the Connect endpoint

Build the type-specific body (see the per-type reference), **write it to a file** under
`${SCRATCH_DIR}` (the per-run scratch dir established in SKILL.md Stage 0.2 — under
`${outputDir}`/`${TMPDIR}`, never a bare `/tmp` path), then POST:

```bash
sf api request rest \
  "/services/data/v{API_VERSION}/connect/livemessage/channels?authProviderId=${AUTH_PROVIDER_ID}" \
  --method POST --target-org '{ORG_ALIAS}' \
  --header 'Content-Type: application/json' --header 'Accept: application/json' \
  --body @"${SCRATCH_DIR}/body.json" --include > "${SCRATCH_DIR}/connect-response.txt" 2>&1
```

**`authProviderId` is a URL query-string parameter, NOT a body field** — mandatory on every known org
and every type (Apple included). Omitting it from the URL → `400 ILLEGAL_QUERY_PARAMETER_VALUE
"Missing argument authProviderId"`. Putting it in the body → `400 JSON_PARSER_ERROR "Unrecognized
field 'authProviderId'"`. The only working form is `?authProviderId=${AUTH_PROVIDER_ID}` in the URL.

**`sf api request rest` manages the Salesforce OAuth session internally** — no bearer token is
extracted into shell state. `--include` prints the HTTP status/headers block ahead of the body — read
the status from that block, not a trailing `-w` marker.

## Stage 4.3: Classify the Connect response

**Classify by `errorCode` first, HTTP status second** — the endpoint is inconsistent about which
status it pairs with some error codes (notably Facebook's `AUTH_PROVIDER_NEEDS_AUTH`). Inspect
`response[0].errorCode` (or `.errorCode` if the body is an object, not an array) before falling back
to the status table.

| HTTP status | Body shape | Handling |
| --- | --- | --- |
| 201 | `{id, developerName, isActive:false, ...}` | Success. Record `{CHANNEL_ID}=id`, `{DEVELOPER_NAME}=developerName`. Continue to Stage 5. |
| 200 | Same shape | Idempotent hit on some orgs. Treat same as 201. |
| 400 | `[{errorCode, message}]` | Business-level rejection. See table below. |
| 401 | empty / `INVALID_SESSION_ID` | SF bearer token invalid. `{ok:false, kind:"auth", hint:"OAuth token invalid — run 'sf org login web'"}`. |
| 403 | `[{errorCode:"INSUFFICIENT_ACCESS"}]` | `{ok:false, kind:"business", errorCode:"INSUFFICIENT_ACCESS", message}`. |
| 404 | usually HTML | Endpoint unavailable / API version unsupported. `{ok:false, kind:"transport", status:404, message:"Connect endpoint unavailable — is {API_VERSION} supported?"}`. |
| 5xx | varies | `{ok:false, kind:"transport", status, message}`. |

**Business errors (HTTP 400, or any status when classified by errorCode):**

| `errorCode` | Meaning | Handling |
| --- | --- | --- |
| `DUPLICATE_VALUE` | Channel already exists (race — preflight missed it). | Re-run Stage 1 preflight; if a row now exists, emit success `created:false, path:"connect-duplicate"`. |
| `INVALID_INPUT` / `MALFORMED_REQUEST` | Body shape issue — likely a skill bug. | `{ok:false, kind:"business", errorCode, message}`; report the request body for debugging. |
| `AUTH_PROVIDER_NEEDS_AUTH` (Facebook) | OAuth not complete / token expired. | `{ok:false, kind:"oauth-not-complete", hint:"re-run Facebook OAuth to refresh the FB token"}`. |
| `INVALID_STATUS` / `UNKNOWN_EXCEPTION` mentioning "WABA"/"Meta" | Meta-side precondition failed. | `{ok:false, kind:"meta-precondition", hint:"WABA may not be shared with SF's BSP app, or the phone may not be OTP-verified on Meta", message}`. |
| any other | Unrecognized. | `{ok:false, kind:"business", errorCode, message}`. |

Per-type message-substring refinements (LINE creds, Apple precondition) are in the per-type reference
files. Return the classified envelope.
