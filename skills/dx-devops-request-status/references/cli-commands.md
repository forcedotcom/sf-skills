# DevOps Center Request Status CLI Command Reference

Reference for `sf devops request status` with its JSON output schema and error handling. This is a **read-only** status check — it issues no mutations. The command is keyed on the **request token** returned by `dx-devops-promote` (the promote response).

## Command Summary

| Command | Purpose | Required Flags | Mutates? |
|---------|---------|---------------|----------|
| `sf devops request status` | Get the current status of a request by its request token | `-i/--request-token`, `-o/--target-org` | No (read-only) |

**Org authentication** — verify before any command:
```bash
sf org display --json
```

---

## Request Status (Read-Only)

Returns the current status of a request identified by its request token. Safe to run repeatedly — it never changes pipeline state.

```bash
sf devops request status \
  --request-token a0B000000000001 \
  --target-org my-devops-org \
  --json
```

### Flags

| Flag | Description |
|------|-------------|
| `-i, --request-token` | (required) Request token from the promote response. **Field-name note:** the value comes from the promote response's async identifier — observed as `.result.requestId` on a `promote` response (e.g. `{"status":"PROMOTE_IN_PROGRESS","requestId":"0Xt...","promotedWorkitemIds":[...]}`), while `request status` echoes it back as `.result.requestToken`. Capture it robustly: `jq -r '.result.requestId // .result.requestToken // .result.promotionId // .result.asyncOperationId'` |
| `-o, --target-org` | (required) Username or alias of the target org. Not required if the `target-org` config variable is set |
| `--api-version` | Override the API version used for API requests made by this command |
| `--json` | Format output as JSON (always use for headless parsing) |
| `--flags-dir` | Import flag values from a directory (global flag) |

### Result fields

| Field | Meaning |
|-------|---------|
| `.result.id` | Internal record ID of the async operation (e.g. `8MwWt00000DDuPtKAL`) |
| `.result.status` | **Request-processing** state, UPPERCASE and **operation-prefixed** (`PROMOTE_IN_PROGRESS`, `PROMOTE_SUCCESS`, `DEPLOY_FAILED`, ...). Reports whether the request finished — NOT whether the deploy succeeded. Match on the suffix (see Status Value Vocabulary) |
| `.result.message` | Human-readable summary (e.g. `"Deployment failed"`, `"Inspection completed successfully"`) |
| `.result.errorDetails` | **The outcome oracle.** `null` on success; on failure an escaped JSON *string* `{"errorType": "...", "errorMessage": "..."}` |
| `.result.requestToken` | Echo of the token you queried |
| `.result.requestCompletionDate` | Completion timestamp, or `null` while still processing / on failure |

> **CRITICAL — two-level semantics.** `.result.status` and the top-level `status` (CLI exit code) can BOTH be success while the underlying operation failed. The authoritative failure signal is a **non-null `.result.errorDetails`**. Always check `errorDetails`, not just `status`.

### JSON Output Schema (in progress)

```json
{
  "status": 0,
  "result": {
    "id": "8MwWt00000DDuPtKAL",
    "status": "IN_PROGRESS",
    "message": null,
    "errorDetails": null,
    "requestToken": "1c07586d-88e1-432c-bcfd-89abc43db874",
    "requestCompletionDate": null
  },
  "warnings": []
}
```

### JSON Output Schema (success)

Request finished AND `errorDetails` is `null`:

```json
{
  "status": 0,
  "result": {
    "id": "8MwWt00000DDu9lKAD",
    "status": "SUCCESS",
    "message": "Inspection completed successfully",
    "errorDetails": null,
    "requestToken": "1c07586d-88e1-432c-bcfd-89abc43db874",
    "requestCompletionDate": "2026-08-17T12:47:18.000+0000"
  },
  "warnings": []
}
```

### JSON Output Schema (failure — note `status: "SUCCESS"`!)

The request finished (`status: "SUCCESS"`), but the deploy FAILED. `errorDetails` is populated and `message` says so. This is the trap — do not read `status` alone:

```json
{
  "status": 0,
  "result": {
    "id": "8MwWt00000DDuPtKAL",
    "status": "SUCCESS",
    "message": "Deployment failed",
    "errorDetails": "{\"errorType\":\"DEPLOYMENT_FAILURE\",\"errorMessage\":\"classes/HelloMCP.cls-meta.xml: Invalid api version:0.0 (classes/HelloMCP.cls-meta.xml)\"}",
    "requestToken": "708b2286-bbf3-4621-9531-6d94334ff763",
    "requestCompletionDate": null
  },
  "warnings": []
}
```

---

## Status Value Vocabulary

`.result.status` reports whether the **request** finished processing (UPPERCASE) and is **operation-PREFIXED** — the value carries the operation name plus a state suffix, e.g. `PROMOTE_IN_PROGRESS`, `PROMOTE_SUCCESS`, `DEPLOY_FAILED`. Match on the **suffix**, never on a bare exact token, so any prefix (`PROMOTE_`, `DEPLOY_`, `VALIDATE_`, ...) is handled:

| Suffix (glob) | Category | Action |
|--------|----------|--------|
| `*_NEW` / `*_QUEUED` / `*_PENDING` | Non-terminal | Keep polling |
| `*_IN_PROGRESS` / `*_STARTED` / `*_RUNNING` | Non-terminal | Keep polling |
| `*SUCCESS*` / `*SUCCEEDED*` / `*COMPLETED*` | Request finished | **Then check `errorDetails`** — null = operation succeeded; non-null = operation FAILED |
| `*FAILED*` / `*FAILURE*` / `*ERROR*` / `*CANCELED*` / `*ABORTED*` | Request finished (failure) | Operation failed — report `errorDetails` |

Reaching a terminal `.result.status` is necessary but NOT sufficient for success. The final gate is `.result.errorDetails == null`. Check failure suffixes BEFORE success so a `*_FAILED` never slips through.

Example real value from a `promote` response the token was minted by: `"status": "PROMOTE_IN_PROGRESS"` with `"message": "Promotion started successfully"`.

### Deriving the true outcome deterministically

Do not hand-roll this classification — `scripts/poll-status.sh` owns it so the two-level rule stays consistent across the one-shot and polling paths. For a single check, invoke `--once` and branch on the exit code:

```bash
scripts/poll-status.sh --once a0B000000000001 my-devops-org
# 0 = succeeded · 2 = operation failed (status suffix *FAILED*/*ERROR*/*CANCELED*,
#     or a *SUCCESS* status with non-null errorDetails) · 4 = still processing · 1 = query error
```

The script glob-matches the operation-prefixed `.result.status` suffix (checking failure suffixes before success so a `*_FAILED` never slips through), then applies the `.result.errorDetails` failure oracle before reporting success.

---

## Error Handling

Distinguish three cases:
1. **Failed query** — CLI/auth/token problem; top-level `status != 0`. Fix the token or auth.
2. **Failed operation** — valid query, request finished, but `.result.errorDetails` is non-null (even if `.result.status == "SUCCESS"`). Report the parsed `errorType`/`errorMessage`.
3. **Still processing** — valid query, `.result.status` non-terminal. Keep polling.

**Request token not found (failed query):**
```json
{ "status": 1, "name": "NOT_FOUND", "message": "No request found for the provided token", "exitCode": 1 }
```

**Missing request-token flag (failed query):**
```json
{ "status": 1, "name": "MissingRequiredFlag", "message": "Missing required flag --request-token", "exitCode": 1 }
```

**Authentication failure (failed query):**
```json
{ "status": 1, "name": "NoOrgFound", "message": "No org configuration found for target-org. Run 'sf org login web' to authenticate.", "exitCode": 1 }
```

**Rate limit / throttle (failed query):**
```json
{ "status": 1, "name": "REQUEST_LIMIT_EXCEEDED", "message": "TotalRequests Limit exceeded.", "exitCode": 1 }
```
Back off — increase the polling interval; never poll below the 5-second floor.

---

## Authentication Requirements

`sf devops request status` requires:

1. **Authenticated org**: `sf org login web` or JWT auth (for CI)
2. **DevOps Center enabled**: org must have DOCe provisioned
3. **Read access** to the request being queried

Auth is the caller's responsibility — this skill contains no auth logic. In CI, use a JWT-authenticated service-account alias with least-privilege scopes.
