# Lookups — resolving the Ids a voice configuration needs

The create/update inputs in `voice_config_api.md` take **record Ids** (`callOriginationFlowId`,
`userIds`, `profileIds`) and a **caller-line code** (`defaultCallerId`). These are org-specific —
never hardcode them. Resolve them first with the lookup scripts below, pick the matching entry and
report it, then pass the selected values into `create-configuration.sh` / `update-configuration.sh`.
Present the list of choices only if a human is available to pick.

These lookups are **not** Connect endpoints. They read standard/Tooling objects with
`sf data query`, which — unlike `sf api request rest` — **does** take `--json` (its records live
under `.result.records[]`). Each script shapes the result with `jq` into a small, named list.

| Need to fill | Script | Source object | Query API |
|--------------|--------|---------------|-----------|
| `callOriginationFlowId` | `lookup-flows.sh` | `FlowDefinitionView` | standard |
| `userIds` | `lookup-users.sh` | `PermissionSetAssignment` | standard |
| `profileIds` | `lookup-profiles.sh` | `Profile` | standard |
| `defaultCallerId` | `lookup-caller-lines.sh` | `CommunicationChannelLine` | **Tooling** |
| `region` / `dialingPrefix` | *(none — static)* | `assets/regions.json` | — |

---

## Flows — `lookup-flows.sh <alias>`

Active, unmanaged auto-launched flows eligible as the pre-dial flow.

```sql
SELECT DurableId, ApiName, Label, ProcessType FROM FlowDefinitionView
WHERE IsActive = true AND ProcessType = 'AutoLaunchedFlow' AND ManageableState = 'unmanaged'
ORDER BY Label ASC LIMIT 2000
```

Output: `{ "flows": [ { "durableId", "apiName", "label" } ] }`.
Pass a chosen `durableId` as `callOriginationFlowId`.

---

## Users — `lookup-users.sh <alias>`

Active users holding a native Contact Center permission set. A user with more than one of the
sets is returned once (deduped by `AssigneeId`).

```sql
SELECT AssigneeId, Assignee.Name, Assignee.Username FROM PermissionSetAssignment
WHERE PermissionSet.Name IN
  ('ContactCenterAgentNativeCCaaS','ContactCenterSupervisorNativeCCaaS','ContactCenterAdminNativeCCaaS')
  AND Assignee.IsActive = true
ORDER BY Assignee.Name ASC LIMIT 2000
```

Output: `{ "users": [ { "id", "name", "username" } ] }`.
Pass chosen `id` values in the `userIds` array.

---

## Profiles — `lookup-profiles.sh <alias>`

```sql
SELECT Id, Name FROM Profile ORDER BY Name ASC LIMIT 500
```

Output: `{ "profiles": [ { "id", "name" } ] }`.
Pass chosen `id` values in the `profileIds` array.

---

## Caller lines — `lookup-caller-lines.sh <alias>`

Live caller-line numbers. `CommunicationChannelLine` is a **Tooling** object, so this script
passes `--use-tooling-api`.

```sql
SELECT Id, Code FROM CommunicationChannelLine
WHERE CodeStatus = 'Live' AND CliStatus IN ('DEFAULT_CLI','CLI_ENABLED')
ORDER BY LastModifiedDate DESC LIMIT 2000
```

Output: `{ "callerLines": [ { "id", "code" } ] }`.
Pass a chosen `code` (the E.164 number) as `defaultCallerId`.

---

## Regions / dialing prefix — static (no query)

Regions are **not queryable** — the Setup UI computes them in-process from a phone-number
library (supported regions + their country calling codes). This skill ships a static list in
`assets/regions.json` with `{ regionCode, displayName, dialingPrefix }` entries. Use it to pick
the matching `region` (e.g. `US`) and its `dialingPrefix` (e.g. `+1`) and report the choice;
present the list only if a human is available to pick. Both fields are plain strings on the
input; if the requested region is already known, you can pass them directly without consulting
the list.
