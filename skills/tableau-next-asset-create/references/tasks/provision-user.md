# Task: Provision / list Tableau Next users / check licenses

Grant, change, revoke, or deactivate a Tableau Next **role**, list users, or
check license seats. This is org-admin work, not an asset share.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for
  that `tableau-next-*` server tool (`shared-gates.md`).
- **ADMIN-ONLY.** Unauthorized → report and STOP. Do not fall back to
  `search_users_and_groups` or share tools.
- **Confirmation (this guide):** never call `upsert_user` on the request
  turn. Preview per `../admin-users.md`, wait for an explicit yes.

## When **not** to use these tools

- **Share / revoke access on a dashboard, viz, workspace, or SDM** →
  `share-asset.md` (`search_users_and_groups` + `add_asset_share` /
  `remove_asset_share`). "Give Alice viewer access to this dashboard" is a
  share, not a role grant.
- **Workspace membership** (`add_workspace_asset`) is not a share and not
  a role provision.

## Steps

Preview formats, ADD CONFLICT, rename-not-supported, remove≠DEACTIVATE,
Personal Org `forceDeactivate`, and license `available=0` / `exhausted`
are in **`../admin-users.md`**.

1. **List / find users** — `get_users`. Omit `offset` on the first page;
   paginate with `nextOffset`. Filters apply server-side.
2. **Check seats** — `get_license_availability` before ADD or a role
   upgrade. If `available` is 0 / `exhausted` is true, warn and stop.
3. **Mutate** — only after a confirmed preview: `upsert_user` with the
   admin-chosen `action` (`ADD` / `UPDATE` / `REVOKE` / `DEACTIVATE`).
   ADD CONFLICT on existing email → do not silently retry as UPDATE.
