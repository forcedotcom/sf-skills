# Number Management API

All endpoints share the base path `/services/data/v68.0/connect/number-management/v1`.

**Never extract the access token.** All calls go through `sf api request rest`, which uses
the CLI's stored session for `--target-org`. Do not pull `accessToken` out of `sf org display`
and hand-build an HTTP request with it.

**Never pass `--json` to `sf api request rest`.** This beta command has no `--json` flag —
passing it fails with `Error: Nonexistent flag: --json`. The raw stdout body is already JSON
(unlike `sf data query`, which does support and need `--json` for its `.result.records[]`
envelope).

## Fetch available default numbers

**`GET /numbers`**

Query parameters:

| Param | Values | Notes |
|-------|--------|-------|
| `countryCode` | `US`, `CA` | |
| `phoneNumberType` | `10DLC`, `Toll Free` | URL-encode the space in `Toll Free` as `%20` |

```bash
sf api request rest \
  "/services/data/v68.0/connect/number-management/v1/numbers?countryCode=US&phoneNumberType=Toll%20Free" \
  --target-org <alias>
```

Response:

```json
{ "phoneNumbers": ["+14155551234", "+14155551235", "+14155551236"] }
```

## Procure a number

**`POST /number`**

```bash
sf api request rest \
  "/services/data/v68.0/connect/number-management/v1/number" \
  --method POST \
  --body '{"phoneNumberType":"Toll Free","country":"US","phoneNumber":"+14155551234"}' \
  --target-org <alias>
```

Success (`201`):

```json
{ "phoneNumber": "+14155551234" }
```

## Reconcile number state

**`POST /numberStateReconcile`**

```bash
sf api request rest \
  "/services/data/v68.0/connect/number-management/v1/numberStateReconcile" \
  --method POST \
  --body '{"phoneNumber":"+14155551234"}' \
  --target-org <alias>
```

Success (`200`): empty body. Used to force the platform to reconcile a procured
number's downstream `CommunicationChannelLine` state.

## Status-code mapping

| Status | Meaning | Action |
|--------|---------|--------|
| `400 BAD_REQUEST` | Invalid country / number type / field | Fix the input and retry |
| `403 RESOURCE_NOT_AVAILABLE` | Max number limit reached | Stop; user must free capacity or request more |
| `404 NOT_FOUND` | Number does not exist (procurement likely failed) | Re-run procurement |
| `409 CONFLICT` | Number already procured | Ask the user to select a different number |
| `500 INTERNAL_SERVER_ERROR` | Backend failure | Retry after a few seconds; escalate if persistent |
