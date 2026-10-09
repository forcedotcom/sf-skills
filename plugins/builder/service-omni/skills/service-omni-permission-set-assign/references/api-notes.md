# API notes — PermissionSetAssignment (v66)

## Schema

`PermissionSetAssignment` is a standard sObject that links a `User` (or `Group`) to a `PermissionSet` or `PermissionSetGroup`. Every "user has permission set X" relationship is one row in this table.

Fields we care about:

| Field | Type | Purpose |
|---|---|---|
| `Id` | 18-char Id (prefix `0Pa`) | The assignment row's Id; used for teardown |
| `AssigneeId` | Reference (`User.Id`) | The user receiving the assignment |
| `PermissionSetId` | Reference (`PermissionSet.Id`) | The specific PermissionSet being granted |
| `PermissionSetGroupId` | Reference (`PermissionSetGroup.Id`) | Alternative to PermissionSetId — for PSGroup assignments. Mutually exclusive with PermissionSetId. Not used by this skill. |
| `IsActive` | Boolean | Not directly writeable; managed by Salesforce |
| `SystemModstamp` | Datetime | Server-side write timestamp |

**We never set:**
- `CreatedById`, `CreatedDate`, `LastModifiedById`, `LastModifiedDate` — server-managed.
- `IsActive` — server-managed.
- `PermissionSetGroupId` — v1 skill only handles individual PermissionSets.

## Uniqueness constraint

The database has a unique index on `(AssigneeId, PermissionSetId)` — a user cannot have the same PermissionSet assigned twice. Attempting a duplicate POST raises:

```text
[
  {
    "message": "You can't add the same permission set to a user twice.",
    "errorCode": "DUPLICATE_VALUE",
    "fields": []
  }
]
```

**This is different from `GroupMember`**, where duplicate POSTs silently succeed with the existing row's Id. The DUPLICATE_VALUE handler here is reachable and correct — it treats a duplicate as "already assigned" and increments `reused_count` for that pair.

## Why we query, not upsert

`PermissionSetAssignment` has no external ID field. The Data API's upsert (`PATCH /sobjects/PermissionSetAssignment/<externalId>/<value>`) pattern is unavailable. Only:

- **POST** with `{AssigneeId, PermissionSetId}` — creates a new row (or raises DUPLICATE_VALUE).
- **DELETE** with `Id` — removes the assignment.

For an idempotent skill, we pre-detect existing pairs via SOQL, then POST only the missing ones — the same detect-then-POST pattern as `service-omni-queue-members-assign`.

## SOQL patterns used

**Locate the agent users** (by the same pattern `service-omni-agent-users-create` produces):

```sql
SELECT Id, Username
FROM User
WHERE Username IN ('agent1.<suffix>@example.com', ...)
```text

**Locate target permission sets:**

```sql
SELECT Id, Name, Label
FROM PermissionSet
WHERE Name IN ('Omni_Agent', ...)
```

- We use `Name` (not `Label`) — Name is the API identifier; Label is localizable.
- **Not `DeveloperName`** — PermissionSet does not have `DeveloperName`; `Name` IS the DeveloperName-equivalent.

**Locate existing assignments:**

```sql
SELECT Id, AssigneeId, PermissionSetId
FROM PermissionSetAssignment
WHERE AssigneeId IN ('005RZ...', '005RZ...', '005RZ...')
  AND PermissionSetId IN ('0PSRZ...', '0PSRZ...')
```text

- Scope to specific users + specific perm sets — avoids returning hundreds of unrelated rows on production-like orgs (real users have dozens of PSAs each).
- The cross-product size for our default case is 3 users × 1 perm set = 3 pairs; the query returns 0..3 rows.

## POST payload

```
POST /services/data/v66.0/sobjects/PermissionSetAssignment
{
  "AssigneeId": "005RZ0000005abcBBB",
  "PermissionSetId": "0PSRZ0000067UKT4A2"
}
```text

- Success: HTTP 201 with `{"id":"0PaRZ00000ABCDE0AB","success":true,"errors":[]}`.
- Duplicate: HTTP 400 with `[{"errorCode":"DUPLICATE_VALUE","message":"You can't add the same permission set to a user twice.",...}]`.
- Missing user or perm set: HTTP 400 with `MALFORMED_ID` — indicates a skill bug (should have been caught by pre-detect).
- License-limit error: HTTP 400 with `LICENSE_LIMIT_EXCEEDED` — some perm sets require specific user licenses (e.g. Sales Cloud PSL requires Sales Cloud license).
- License-integrity error: HTTP 400 with `FIELD_INTEGRITY_EXCEPTION — The user license doesn't allow the permission: <name>` — the perm set grants a **system permission the assignee's user license does not permit**. This is why `Omni_Agent` must NOT include license-gated system permissions such as `OmniAssistiveActionUser` (an Agentforce/assistive-actions permission requiring a Service Agent/Agentforce entitlement). `Omni_Agent` instead grants agent capability via `servicePresenceStatusAccesses`, which a standard Salesforce/Service Cloud license permits. Verified live (Service Cloud profile, Salesforce license): `OmniAssistiveActionUser` → FIELD_INTEGRITY_EXCEPTION; presence-status access → assigns cleanly.

## Self-heal deploy: presence statuses are generated from what exists on the org

A `PermissionSet` deploy fails (`no ServicePresenceStatus named <name> found`) if it references a presence status that does not exist. A VoiceCall-only org has `Available_Voice` (+ `Busy`) but not `Available_Case`; a Case-only org is the reverse. To stay target-agnostic, the self-heal step does **not** deploy a static `Omni_Agent` asset with a hardcoded `Available_Case`. Instead it queries `ServicePresenceStatus` on the org, intersects with the curated Omni demo set (`Available_Case`, `Available_Voice`, `Available_Messaging`, `Available_Chat`, `Available_Incident`, `Busy`), and generates the `servicePresenceStatusAccesses` block from only the statuses that actually exist — then deploys that generated permset from a temp SFDX project. As a result, `Omni_Agent` deploys cleanly on a Case org, a Voice org, or any mix, and the deploy never references a missing status. Run `service-omni-presence-status-deploy` first so at least one presence status exists.

## sf api request rest emits a beta warning to stderr

`sf api request rest` prints `Warning: This command is currently in beta.` to stderr. To keep stdout pure JSON, the script captures stderr with the temp-file pattern:

```bash
POST_STDERR="$(mktemp)"
POST_RESULT=$(sf api request rest ... 2>"$POST_STDERR" || true)
POST_SUCCESS=$(echo "$POST_RESULT" | jq -r '.success // false')
rm -f "$POST_STDERR"
```

Never `2>&1` — the Warning line breaks jq parsing.

## Permission required to POST PermissionSetAssignment

The user executing the sf CLI must have:

- `PermissionsAssignPermissionSets = true` (part of System Administrator profile; also included in the "Manage Permission Sets" standard permission)
- `ModifyAllData = true` (usually implied by the above)

If the CLI user lacks these, POST returns `INSUFFICIENT_ACCESS_OR_READONLY`. The skill's script translates this to "Re-authenticate as a System Administrator".

**Notable gotcha:** on some orgs, a user with `ModifyAllData=true` but WITHOUT `AssignPermissionSets=true` can query PSAs but not create them. This is a documented Salesforce behavior; our production CDOs typically bundle both perms on the SA profile, but scratch orgs sometimes ship the SA profile without `AssignPermissionSets`. If encountered, re-auth as a "true admin" or grant `AssignPermissionSets` manually.

## Teardown hook (not implemented in v1)

A future `service-omni-permission-set-remove` skill would:

1. Query `PermissionSetAssignment` where `AssigneeId IN <agent-users>` AND `PermissionSet.Name IN <target-names>`.
2. DELETE each row via `/sobjects/PermissionSetAssignment/<id>`.
3. Re-verify.

Not part of v1 coordinator's forward path — teardown is out of scope. A separate `teardown-coordinate` skill will handle it holistically.

## Why not Apex?

`PermissionSetAssignment` insert is a simple 2-field row. Apex would let us bulk-insert all N rows in one transaction (~1 API round-trip instead of N), but the tradeoffs are:

- **N is small.** At 3 users × 1 perm set = 3 POSTs, the difference is a couple of seconds.
- **Simpler debugging.** REST POSTs return structured JSON; Apex debug logs require anchored regexes.
- **License-check surface.** POST returns `LICENSE_LIMIT_EXCEEDED` immediately for the offending pair without rolling back sibling successes. A bulk Apex insert would need more code to detect and report a partial success.

Assigning hundreds of perm sets at once would be a reason to revisit this and use Apex with `Database.insert(..., false)` for partial-success semantics.
