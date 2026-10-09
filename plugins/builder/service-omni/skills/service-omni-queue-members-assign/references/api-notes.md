# API notes — GroupMember binding for Omni Queue

## `GroupMember` sObject shape (v66)

The `GroupMember` sObject represents a user's (or nested group's) membership in a Salesforce `Group`. On Salesforce, a **Queue is a specialized `Group`** — same underlying table, distinguished by `Group.Type='Queue'` vs. `Type='Regular'` (public groups). Every membership row lives in `GroupMember`.

Fields we care about:

| Field | Type | Purpose |
|---|---|---|
| `Id` | 18-char Id | The membership row's Id, used for teardown |
| `GroupId` | Reference (`Group.Id`) | The queue/public-group this membership belongs to |
| `UserOrGroupId` | Polymorphic reference (`User.Id` or `Group.Id`) | The member being bound. For agent-to-queue bindings this is always a `User.Id` |
| `SystemModstamp` | Datetime | Server-side write timestamp; useful in idempotency checks |

**We never set:**
- `CreatedById`, `CreatedDate`, `LastModifiedById`, `LastModifiedDate` — Salesforce writes these on insert; supplying them is a compile-time error on the Data API.

## Why we query, not upsert

`GroupMember` has no external ID field and no natural composite key exposed as an upsert target. The Data API's `PATCH /sobjects/GroupMember/<externalId__c>/<value>` pattern is unavailable. The only insert paths are:

- **POST** with `{GroupId, UserOrGroupId}` — creates a new row. Duplicate `(GroupId, UserOrGroupId)` tuples raise `DUPLICATE_VALUE`.
- **Metadata API `Queue` deploy with `<queueMembers>` block** — replaces membership atomically (dangerous — will remove out-of-band members).

For a skill that must be idempotent AND non-destructive, the pattern is:

1. SOQL for existing memberships → set of `existing_user_ids`
2. Compute `missing_user_ids = expected − existing_user_ids`
3. POST one row per missing user (individually — no batching, no rollback semantics needed at this scale)
4. Re-query to confirm.

This is why the skill is called `verify-and-bind.sh`, not `upsert-and-report.sh` — no upsert primitive exists.

## SOQL patterns used

**Locate the queue:**

```sql
SELECT Id
FROM Group
WHERE DeveloperName = 'CaseQueue' AND Type = 'Queue'
```text

- `Type='Queue'` matters — a public group and a queue can share the same DeveloperName (rare, but possible on orgs with hand-crafted metadata).
- We use `DeveloperName`, not `Name` — Name is the localized label and can drift; DeveloperName is the stable API identifier.

**Locate the agent users:**

```sql
SELECT Id, Username
FROM User
WHERE Username IN ('agent1.0abc123a@example.com', 'agent2.0abc123a@example.com', 'agent3.0abc123a@example.com')
```

- We use `Username` (globally unique), not `Email` (not unique) or `Alias` (not unique).
- No `IsActive` filter — inactive users can still be queue members (they just don't receive new work); we want to bind them regardless.

**Locate existing memberships:**

```sql
SELECT Id, UserOrGroupId
FROM GroupMember
WHERE GroupId = '00GRZ000004esvR2AQ'
  AND UserOrGroupId IN ('005RZ0000005xyzAAA', '005RZ0000005abcBBB', '005RZ0000005defCCC')
```text

- Scope the query to the specific queue + specific users, not all queue members — avoids returning hundreds of unrelated rows on production-like orgs.
- The polymorphic `UserOrGroupId` filter works for User Ids; the query returns only User-typed members.

## POST payload

```
POST /services/data/v66.0/sobjects/GroupMember
{
  "GroupId": "00GRZ000004esvR2AQ",
  "UserOrGroupId": "005RZ0000005abcBBB"
}
```text

- Success: HTTP 201 with `{"id":"011RZ00000ABCDE0AB","success":true,"errors":[]}`.
- **Duplicate write:** Salesforce server-side dedupes `GroupMember` on the (`GroupId`, `UserOrGroupId`) uniqueness constraint at the persistence layer. A duplicate POST returns HTTP 201 with `success:true` and the **existing row's Id** — no `DUPLICATE_VALUE` error is raised, and no new row is created. Successive POSTs of the same tuple produce exactly one GroupMember row.
  - Implication: the skill's detect step (querying existing memberships) is the primary mechanism preventing inflated `bound_count` on re-runs. Without detect, every re-run would report all N users as newly "bound" even though no new rows were created.
  - The `DUPLICATE_VALUE` branch in the skill's script is retained for future-proofing (in case Salesforce changes this behavior in a future API version) but is not currently reachable.

## `sf api request rest` output channel

The `sf api request rest` CLI command emits a `Warning: This command is currently in beta. Any aspect of this command can change without advanced notice. Don't use beta commands in your scripts.` line to **stderr** on every invocation. The JSON response body goes to **stdout**.

**Do NOT** capture with `2>&1` when the output is going to be parsed by `jq`, because the Warning line becomes the first line of the merged stream and every subsequent `jq '.field'` call silently fails (jq returns exit-1 for non-JSON input, which gets swallowed by `|| echo "false"` fallbacks).

**Correct pattern:**
```bash
POST_STDERR=$(mktemp)
POST_RESULT=$(sf api request rest ... 2>"$POST_STDERR" || true)
POST_SUCCESS=$(echo "$POST_RESULT" | jq -r '.success // false')
# On failure, read $POST_STDERR (excluding Warning: lines) for the real error
rm -f "$POST_STDERR"
```

**Also acceptable:** `2>/dev/null` if you don't need to surface CLI-level errors (auth failures, network drops). But redirecting to a temp file preserves that visibility.

## Common failure modes and how the skill translates them

| Salesforce error | Skill translation | Actionable? |
|---|---|---|
| ~~`DUPLICATE_VALUE` on POST~~ | ~~Treat as reused~~ | **Not reachable** — GroupMember dedupes at the persistence layer (see above) |
| Non-JSON stdout (Warning line) | Skill bug — script merged stderr into stdout | Yes — use the temp-file pattern |
| `MALFORMED_ID` | Skill bug — user Id or group Id malformed before POST | Yes — file an issue against the skill |
| `INSUFFICIENT_ACCESS_OR_READONLY` on POST | Executing user lacks `ModifyAllData` or queue-write perm | Yes — re-authenticate as a System Administrator |
| `INVALID_TYPE` on GroupMember SOQL | Never seen — GroupMember is universally available | If it happens, the org is corrupt; escalate |
| `INVALID_FIELD` on `GroupMember.CreatedDate` | `GroupMember` does not expose `CreatedDate` in SOQL (nor `CreatedById`, `LastModifiedDate`, `SystemModstamp` — they exist internally but are not queryable). Non-blocking for this skill. | Query only `Id`, `GroupId`, `UserOrGroupId` — the reliably queryable columns |
| Empty `User` query result (any expected username missing) | The agent users were not created, or were created with a different `count`/suffix | Yes — re-run `service-omni-agent-users-create` with the same count |
| `Group` DeveloperName not found | The queue is missing (or was renamed) | Yes — re-run `service-omni-queue-deploy`, or create the queue manually per its click-path |

## Why individual POSTs, not composite tree

Salesforce supports `POST /composite/tree/GroupMember` for batching up to 200 inserts atomically. We deliberately avoid it here because:

- **Blast radius.** A single bad user Id rolls back all inserts in a tree request. Individual POSTs isolate failures — one duplicate doesn't sink the batch.
- **Report clarity.** Individual POST responses give us per-user status directly; parsing composite-tree responses adds ~40 lines of jq without any latency win at N ≤ 10.
- **Idempotency reasoning.** With individual POSTs, the loop `for missing_user in missing_users: POST; on-duplicate: skip` is transparent. A tree request would need pre-filtering by re-querying inside the batch, adding a race window.

For skills that need to bind hundreds of users (a v1.1 concern — supervisor tools), we'd revisit this and use `/composite/tree` with client-side duplicate stripping.

## Teardown hook (not implemented in v1)

A future `service-omni-queue-members-assign-remove` skill would:

1. Query `GroupMember` where `GroupId=<queue-id>` AND `UserOrGroupId IN <agent-user-ids>` → collect Ids to delete.
2. DELETE `/sobjects/GroupMember/<id>` one at a time.
3. Re-verify final member count.

Not part of the v1 coordinator's forward path — teardown is out of scope for the routing-setup coordinator; a separate `teardown-coordinate` skill will handle it holistically.

## Why not Apex?

Compared to `service-omni-agent-users-create`, this skill does not use Anonymous Apex because:

- **No transactional invariant.** User creation needs `insert User + System.setPassword` in one transaction — if setPassword fails, we want the User rolled back. GroupMember has no such coupling.
- **No policy enforcement.** User creation triggers profile-validation, license-consumption, and password-policy Apex-side checks that are cleaner to observe in a debug log. GroupMember insert is a simple two-field row.
- **Simpler operator debugging.** REST POSTs return structured JSON; Apex debug log parsing requires anchored regexes.

The tradeoff: an Apex approach could bulk-insert all N rows in one transaction (~1 API round-trip instead of N). At N ≤ 10 the difference is a second or two — not worth the debugging complexity.
