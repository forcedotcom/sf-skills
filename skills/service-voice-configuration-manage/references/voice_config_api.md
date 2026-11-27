# Voice Configuration API

The Voice Configuration Connect API manages `VoiceTelephonyDefinition` records (key prefix
`1pK`) — the native Contact Center "voice configurations" that define a dialing prefix, region,
default caller ID, a pre-dial flow, and the users/profiles assigned to them.

All endpoints share the base path
`/services/data/v68.0/connect/thb-voice-config/v1` (the native Contact Center voice-config API).

**Never extract the access token.** All calls go through `sf api request rest`, which uses the
CLI's stored session for `--target-org`. Do not pull `accessToken` out of `sf org display` and
hand-build an HTTP request with it.

**Never pass `--json` to `sf api request rest`.** The command has no `--json` flag — passing it
fails with `Error: Nonexistent flag: --json`. The raw stdout body is already JSON. (This is the
opposite of `sf data query`, which *does* need `--json` for the lookups in `lookups.md`.)

**Access.** Every endpoint requires native Contact Center admin access. A caller without it gets `403` before any work runs.

---

## Field names: input vs. output (read this first)

The fields you **send** on create/update are named differently from the fields you **read back**.
A read-then-write cycle must translate — re-sending an output body verbatim will send unknown
fields. The values are the same; only the keys differ.

| Meaning | Input key (create/update) | Output key (get/list) |
|---------|---------------------------|-----------------------|
| Dialing region | `region` | `dialingRegion` |
| Pre-dial flow Id | `callOriginationFlowId` | `preDialFlowId` |
| Default caller Id | `defaultCallerId` | `defaultCallerIdentifier` |
| Label | `name` | `name` |
| Developer name | `developerName` (create only) | `developerName` |
| Dialing prefix | `dialingPrefix` | `dialingPrefix` |
| Description | `description` | `description` |

---

## List all configurations

**`GET /configurations`** — script: `list-configurations.sh <alias>`

```bash
sf api request rest \
  "/services/data/v68.0/connect/thb-voice-config/v1/configurations" \
  --target-org <alias>
```

Success (`200`) — `VoiceConfigurationCollectionRepresentation`:

```json
{
  "configurations": [
    { "id": "1pK...", "name": "US Inbound", "developerName": "US_Inbound",
      "dialingPrefix": "+1", "dialingRegion": "US", "preDialFlowId": "300...",
      "defaultCallerIdentifier": "+14155550100" }
  ]
}
```

Each summary carries `id`, `name`, `developerName`, `dialingPrefix`, `dialingRegion`,
`preDialFlowId`, `defaultCallerIdentifier` (no dates/audit fields — get the detail for those).

---

## Create a configuration

**`POST /configurations`** — script: `create-configuration.sh <alias> <json-body>`

Request body — `CreateVoiceConfigurationInputRepresentation`:

| Field | Required | Notes |
|-------|----------|-------|
| `name` | **yes** | MasterLabel of the configuration |
| `developerName` | no | Immutable after create. If omitted, derived from `name` |
| `dialingPrefix` | no | e.g. `+1` |
| `region` | no | e.g. `US` (see `assets/regions.json`) |
| `defaultCallerId` | no | Default caller identification (a caller-line `code`) |
| `callOriginationFlowId` | no | PreDialFlow Id (a flow `durableId`) |
| `description` | no | Free text |
| `userIds` | no | Array of User Ids to assign |
| `profileIds` | no | Array of Profile Ids to assign |

> The API also accepts a `queueIds` array (queue assignment for SCV/BYOT orgs). This skill scopes
> to the native Contact Center path (users/profiles) and does not manage queues — omit `queueIds`.

```bash
sf api request rest \
  "/services/data/v68.0/connect/thb-voice-config/v1/configurations" \
  --method POST \
  --body '{"name":"US Inbound","developerName":"US_Inbound","dialingPrefix":"+1","region":"US","userIds":["005..."],"profileIds":["00e..."]}' \
  --target-org <alias>
```

Success (`200`) — `CreateVoiceConfigurationOutputRepresentation`:

```json
{ "id": "1pK..." }
```

> **Create is lenient.** A `200` with an `id` means the record was created. User/profile
> assignment, however, is best-effort — if it fails it is *not* rolled back, and the create still
> returns `200`. Always read the configuration back (`get-configuration.sh`) and confirm the
> intended `userIds`/`profileIds` are actually assigned.

---

## Get one configuration

**`GET /configurations/{configId}`** — script: `get-configuration.sh <alias> <configId>`

Success (`200`) — `VoiceConfigurationRepresentation` (note the output key names):

```json
{
  "id": "1pK...", "name": "US Inbound", "developerName": "US_Inbound",
  "dialingPrefix": "+1", "dialingRegion": "US", "preDialFlowId": "300...",
  "defaultCallerIdentifier": "+14155550100", "description": "...",
  "createdDate": "...", "lastModifiedDate": "...",
  "createdBy": "...", "lastModifiedBy": "..."
}
```

---

## Update a configuration

**`PUT /configurations/{configId}`** — script: `update-configuration.sh <alias> <configId> <json-body>`

Request body — `UpdateVoiceConfigurationInputRepresentation`. Same shape as create **minus
`developerName`** (immutable — do not send it).

- `name` is **required**.
- `userIds` / `profileIds`, when present, **replace the full assignment list**. Omit a field to
  leave those assignments untouched; send `[]` to clear them.

```bash
sf api request rest \
  "/services/data/v68.0/connect/thb-voice-config/v1/configurations/1pK..." \
  --method PUT \
  --body '{"name":"US Inbound (updated)","dialingPrefix":"+1","region":"US"}' \
  --target-org <alias>
```

Success (`200`): empty body.

---

## Delete a configuration

**`DELETE /configurations/{configId}`** — script: `delete-configuration.sh <alias> <configId>`

Success (`200`): empty body. The org's **default** voice configuration cannot be deleted
(returns `400`).

---

## Status-code mapping

| Status | Meaning | Action |
|--------|---------|--------|
| `400 BAD_REQUEST` | Invalid input, or attempt to delete the default configuration | Fix the input; a default config cannot be deleted |
| `403` | Caller lacks native Contact Center admin access | Stop; the user must be a Contact Center admin |
| `404 NOT_FOUND` | No configuration with that `configId` | Verify the Id via `list-configurations.sh` |
| `409 CONFLICT` | A configuration with this `developerName` already exists | Choose a different `developerName` or reuse the existing config |
| `500 INTERNAL_SERVER_ERROR` | Backend failure | Retry after a few seconds; escalate if persistent |

Stop and report on any non-2xx response — do not continue a multi-step operation on a failure.
