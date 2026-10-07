# Task: Share or revoke access to a Tableau Next asset

Grant, inspect, change, or revoke a **user or group** share on a dashboard,
visualization, workspace, or semantic model. This is not workspace
membership (`add_workspace_asset` / `remove_workspace_asset`) and not
deleting the asset itself.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **Confirmation (this guide):** show recipient + asset + `accessType` and
  wait for an explicit yes before `add_asset_share` or `update_asset_share`.
  `remove_asset_share` is destructive — the user **loses access immediately**.
  Confirm first.
- Granting a Tableau Next **role** (Analyst, Admin, …) is `provision-user.md`,
  not this guide.

## Steps

Lookup, access-level matrix, Personal Org rules, partial-batch / silent-204
recovery, and wrap vs unwrap are in **`../sharing-and-promotion.md`** (§Share).

1. Resolve the asset `recordId` (Salesforce id, not apiName/label) from
   `get_dashboard` / `get_visualization` / `list_workspaces` /
   `get_semantic_model`.
2. **New grant:** search_users_and_groups first (name or email →
   `userOrGroupId`). Then `add_asset_share` with `applicationDomain: "Tableau"`
   and an `accessType` allowed for that `setupObjectType`.
3. **Inspect / verify / change / revoke:** list_asset_shares first. Update
   and remove use the listed `userOrGroupId` (Personal Org: the **shadow ID**).
   To **revoke access entirely**, call `remove_asset_share` — do not set a
   weaker `accessType` on update.
4. Always read `failedRecordShares` on add/update. After remove, list again
   if you need to prove the row is gone (HTTP 204 is not proof).
