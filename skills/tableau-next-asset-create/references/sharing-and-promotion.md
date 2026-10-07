# Sharing and promotion/reuse — payloads and gotchas

Load this from `tasks/share-asset.md` or `tasks/promote-or-reuse.md`. Not a
first hop.

Principal lookup, access-level rules, safe share mutation, and the Reuse /
Promotion request lifecycle live here once. Task guides stay thin.

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected.

## Contents

Intent → heading:

- Resolve a recipient / `recordId` / share row → Share: principal lookup
- `accessType` / `owner` / `viewer` / group vs user → Share: permission matrix
- Personal Org share vs production → Share: Personal Org
- Duplicate / partial batch / silent 204 / last owner → Share: safe mutation
- `defaultExc` vs empty 204 / error array → Share: response wrap
- Reuse vs Promotion, poll fields, list filters → Promote: request lifecycle
- Package URL, `sf` CLI, git/`gh` PR → Promote: pull-request recovery

---

## Share: principal lookup

**Resolve the recipient before `add_asset_share`.** Call
`search_users_and_groups` first. Pass the query as `usersAndGroupsQueryInput`
(not a bare top-level `searchTerm`). Each result item's `id` is the
`userOrGroupId` to pass.

- `searchTerm`: **Minimum 2 characters**. A single character is rejected (not
  "few results"). Matching is **case-insensitive**.
- Results interleave users and groups in `items`. Paginate with independent
  `nextUserOffset` and `nextGroupOffset` — do not add `items.length` to a
  single offset.
- `useAutoSuggest` defaults to `false`; typeahead is opt-in.
- `recipientSearchTerm` on `list_asset_shares` is a case-insensitive
  **substring** on display name / username. **No minimum length**; blank
  values are ignored. Do not treat it as the same rule as `searchTerm`.

**`recordId` is the asset's Salesforce record ID**, not its `apiName` or label.
Obtain it from `get_dashboard`, `get_visualization`, `list_workspaces`, or
`get_semantic_model`. An id that is not a known asset type (dashboard,
workspace, visualization, semantic model) returns `INVALID_INPUT`. Missing
entity-level view permission → `ACCESS_DENIED`.

**`list_asset_shares`:** do not pass `setupObjectType` — the asset type is
inferred from the `recordId` prefix.

- `limit` Defaults to **10**. No enforced maximum. Paginate; a first page is
  not the full recipient list.
- `orderBy` is only `CreatedDate` (default) or `UserDisplayName`. Anything
  else errors.
- `sortOrder` is case-sensitive: only the exact string `"ASC"` is ascending.
  `"asc"` (or anything else) silently falls back to descending.
- `filterByRecipientType` `Group` maps internally to both Group and Queue.
- Callers who are not an owner or manager of the asset get a **filtered view**
  (owner-level shares plus their own entry) with no indication that other
  rows were hidden.
- `ownerCount` is always the unfiltered total, even when `filterByAccessType`
  or `limit` narrows `recordAccessMappings`.
- Shares for deleted users/groups are silently omitted (no tombstone).

**Existing shares (update / remove):** `list_asset_shares` first, then use the
`userOrGroupId` on each entry. `update_asset_share` **Does not remap** ids —
pass the listed (shadow) value. A prod-sourced add-time id **will not match**
and the update **fails** — that is not the remove path's HTTP 204 silent
no-op.

---

## Share: permission matrix

`accessType` allowed values **vary by** `setupObjectType`. An unsupported
combination returns `INVALID_INPUT`. `commenter` and `manager` are **never**
valid for any asset type.

| `setupObjectType` | Production | Notes |
|---|---|---|
| `analyticsvisualization` | `viewer` only | Personal Org writes: `ACCESS_DENIED` (workspace only) |
| `analyticsdashboard` | `viewer` only | Personal Org writes: `ACCESS_DENIED` (workspace only) |
| `analyticsworkspace` | `viewer`, `editor`, `owner` | Personal Org: `viewer`, `editor` (not `owner`) |
| `semanticmodel` | `viewer`, `editor`, `owner` | Personal Org writes: `ACCESS_DENIED` (workspace only) |

**Groups cannot be `owner`** on any asset type → `INVALID_INPUT`.

`applicationDomain` is required on each `accessRequestItems` entry and must
literally be `"Tableau"`.

`add_asset_share` and `update_asset_share` take **top-level** parameters
alongside `recordId` — do not nest them in a `body` wrapper.

Reference shape (substitute ids from `list_*` / `search_users_and_groups`):

```json
{
  "recordId": "<18-char asset id>",
  "accessRequestItems": [
    {
      "userOrGroupId": "<id from search_users_and_groups>",
      "setupObjectType": "analyticsdashboard",
      "accessType": "viewer",
      "applicationDomain": "Tableau"
    }
  ]
}
```

---

## Share: Personal Org

**Writes** (`add_asset_share`, `update_asset_share`, `remove_asset_share`): only
`analyticsworkspace`. Any other `setupObjectType` returns `ACCESS_DENIED`
(`You can only modify sharing for workspaces in a Personal Org.`). The call
is rejected on asset type before `accessType` is checked — a personal-org
dashboard or visualization is not a `viewer` share.

**Group sharing is not supported** in Personal Orgs. Recipients must be
individual users. `ALL_USERS` as the group id returns `ACCESS_DENIED`.

**Reads:** listing shares is not restricted to workspaces — you can list shares
on dashboards, visualizations, and models there even though you cannot add /
update / remove them.

**Search:** `search_users_and_groups` **does not fail** in a Personal Org; it
returns the same results as production, and you may call either server's tool.
Only **user** results are usable as share recipients there (see group rule).
Do not skip to a "production-only" search on the belief that personal-org
search always fails.

**IDs:** `add_asset_share` stores a local **shadow ID**. `list_asset_shares`
returns that shadow on `userOrGroupId` and `userOrGroup.id`. Use the shadow
with `update_asset_share` and `remove_asset_share`. For a user who is **not
yet** in the personal org, pass the prod-sourced id from
`search_users_and_groups` into **add** — no shadow ID exists yet for that user.
Do **not** keep the prod id for remove: that call returns HTTP 204 and the
share stays. The same prod id on `update_asset_share` **fails** (no remap,
not a silent 204). List after every remove.

---

## Share: safe mutation

Confirm recipient + asset + `accessType` before add or update. Confirm before
remove — the user **loses access immediately**.

- **`sendNotificationToRecipients`:** optional; emails the recipient. The grant
  still takes effect without it.
- **Duplicate add:** that item fails with `DUPLICATE_VALUE` in
  `failedRecordShares`; other items in the same request can still succeed.
  Always inspect `failedRecordShares` on an otherwise successful response.
- **Partial update:** same `failedRecordShares` rule.
- **No existing share on update:** a **multi-item** batch reports
  `RESOURCE_NOT_FOUND` per item in `failedRecordShares`. A **single-item**
  request instead fails the call with top-level
  `RESOURCE_UPDATE_FAILURE_UNPROCESSABLE`. Verify the row via `list_asset_shares`
  before a one-item update.
- **Invalid id format on update:** `fails the entire batch` with
  `INVALID_INPUT` and `failedRecordShares` empty — not a per-item failure.
- **Minimum owner:** the API keeps **at least one owner**. Downgrading or
  removing the last owner → `INVALID_INPUT`.
- **Cannot remove your own share** → `INVALID_INPUT`. The API checks own share before
  the minimum-owner rule, so the last owner who is also the caller sees the
  own-share error.
- **Remove id mismatch / missing row:** HTTP 204 silently (looks like
  success) with **no error**. In a Personal Org, a prod-sourced add-time id
  is this silent no-op — the share remains. Verify with `list_asset_shares`
  before and after; 204 is not proof the row is gone.
- **Conversation visualizations** (`creationSource = CONVERSATION`): add and
  list GET return `INVALID_INPUT` when the ephemeral viz sharing gate is on.

To **revoke access entirely**, use `remove_asset_share` — `update_asset_share`
only changes `accessType`.

---

## Share: response wrap

`add_asset_share`, `update_asset_share`, and `search_users_and_groups`
double-wrap as `{"defaultExc": "<stringified JSON>", "responseCode": <number>}`.
Parse `JSON.parse(response.defaultExc)` (same pattern as
`sdm-tool-reference.md` Response double-wrap).

`remove_asset_share` does **not**. Success is an empty body (HTTP 204). Failure
is a raw **JSON array** (`[{"errorCode": "...", "message": "..."}]`).

`list_asset_shares` is unwrapped.

---

## Promote: request lifecycle

`create_reuse_promotion_request` is one tool for two directions — meaning flips.
Pass the create fields as **flat top-level params** (`requestType`, `assetId`,
`label`, `workspaceIdOrApiName`, `requesterComment`) — there is **no**
`dataAssetRequestInput` (or any other) body wrapper; the schema is
`additionalProperties: false` and rejects one. Create `requestType` is
`Reuse`/`Promotion` (capitalized). `list_promotion_reuse_requests` uses
lowercase `reuse` (case-insensitive); the create response also shows
`reuse` | `promotion`.

| `requestType` | `assetId` | `workspaceIdOrApiName` |
|---|---|---|
| Reuse | prod asset to copy | Personal Org **destination** workspace |
| Promotion | Personal Org asset to package | Personal Org workspace **containing** the asset |

`workspaceIdOrApiName` is an id or true apiName, **NOT the workspace label**
with spaces.

**Reuse `assetId` types:** Dashboard, Visualization, DMO, SDM, or CIO only.
Do **not** pass a Data Lake Object (`0gO`) or a Data Connection id — those
requests are rejected.

`requesterComment` is required (max **254** chars). Do not omit or pass null
— the downstream UI will break.

**Org:** caller must be in a Personal Org. Otherwise
`INVALID_INPUT: "Request is not supported in this type of org"`.

**After create — poll `get_promotion_reuse_request` by the returned `id`**
(listing a known request is not the poll path — `get_promotion_reuse_request`
is cheaper and returns more detail).

`status` is lowercase on the wire. Documented values: `requested`,
`reviewContent`, `markAcceptedOrRejected`, `accepted`, `rejected`,
`extracting`, `extractionComplete`, `migrating`, `migrationSucceeded`,
`failed`, `cancelled`, `manageCsv`, `manageAccess`, `manageDataPolicy`,
`markComplete`, `completed`.

- **Reuse:** poll `status` until the terminal `completed`
  (`taskProgressStatus: terminal`). Happy path: `requested` → `accepted` →
  `extracting` → `extractionComplete` → `migrating` → `migrationSucceeded` →
  `completed`. Do **not** wait for `migrationSucceeded` as the end state — it
  is a brief intermediate a late poll skips right past on the way to
  `completed`. **STOP** on `failed`, `cancelled`, or `rejected` — do not keep
  polling for success. When `status = rejected`, read `rejectionComment` (that
  is when it is populated) and surface it; do not invent a reason.
- **Promotion:** poll `packageExportStatus` every **10 seconds** for up to
  30 seconds until it is `ready`. **The wire value is lowercase** (`ready`,
  `packaging`, …) even though the `create_reuse_promotion_request` schema enum
  and older docs show it capitalized (`"Ready"`) — match case-insensitively; a
  strict `=== "Ready"` check never fires. Note `status` itself stays
  `requested` throughout a Promotion (it does not advance like Reuse) — gate
  only on `packageExportStatus`. If it is ready, **ask** the user before
  `create_promotion_pull_request`. If it is not ready, tell them to try
  `create_promotion_pull_request` later — do not poll indefinitely.
  `packageExportStatus` must be `ready` before `create_promotion_pull_request`.
  Same stop on Reuse-style `failed` / `cancelled` / `rejected` if `status`
  lands there before export is ready.

**`list_promotion_reuse_requests`:** optional query fields are **top-level**
(combinable) — `workspaceIdOrApiName`, `assetId`, `assetType`, `createdBy`,
`searchQueryTerm`, `status`, `taskProgressStatus`, `sortBy`, `orderBy`,
`limit`, `offset`. Do **not** nest them in a `requestParams` wrapper (that
name is the Connect Java map, not an MCP key). Always pass
`requestType=reuse` (case-insensitive). Omitting it mixes Promotion rows
into the list with no error.

- `assetId` — filter to one source prod asset.
- `createdBy` — user id of the requester.
- `searchQueryTerm` — free-text match against label / comment.
- `assetType` — `dashboard` / `visualization` / `semanticModel` / etc.
  Do not invent further values.
- `status` — **comma-separated**, e.g. `requested,extracting,migrating` for
  in-flight or `rejected,failed` for terminal. Values are **silently
  accepted** even when spelled wrong — a typo returns an empty list, not a
  validation error. Spell statuses like the get-by-id lifecycle above.
- `taskProgressStatus` — also comma-separated; **finer-grained than
  `status`**. Do not send one field's values on the other.
- `sortBy` and `orderBy` — sort key plus asc / desc. Do not invent allowed
  keys; omit unless the user named a sort.
- `limit` / `offset` — paginate. A default page size applies if `limit` is
  omitted (do not assume the first page is complete).
- For one known id, prefer `get_promotion_reuse_request` — cheaper, more
  detail.

Create/list may double-wrap: if the body looks like `defaultExc`, parse it
the same way as Share wrap. Get-by-id is unwrapped (do not assume
`defaultExc` on a failed poll).

---

## Promote: pull-request recovery

`create_promotion_pull_request` does **not** open the GitHub PR. It returns a
GET-only `presignedUrl` (expires in **5 minutes**) plus `requestId`. Download
immediately. Git / `gh pr create` is **client-side**.

1. `PROMO_DIR=/tmp/promotion_<requestId>` (and `mdapi` / `source` under it) so
   concurrent promotions do not collide.
2. `curl` the zip. Decode `&amp;` in the URL to `&` first.
3. Unzip into `$PROMO_DIR/mdapi/`.
4. If the Salesforce sf CLI is missing, **STOP**. Tell the user it is required to
   convert the package, and give them the remaining commands — do not continue.
5. Write `$PROMO_DIR/source/sfdx-project.json` as
   `{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"67.0"}`.
   Convert: `sf project convert mdapi --root-dir $PROMO_DIR/mdapi/unpackaged
   --output-dir $PROMO_DIR/source/force-app`. Output files carry a `-meta.xml`
   suffix.
6. **Ask** which directory in the target repo should receive the files. Copy
   the contents **inside** `force-app/main/default/` (not the parent folders).
7. **Ask** for the branch name. Commit, push, `gh pr create`. Title the
   promotion; body lists the datakit files and the **promotion request id**.
