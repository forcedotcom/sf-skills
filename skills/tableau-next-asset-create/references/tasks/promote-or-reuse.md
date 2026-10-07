# Task: Reuse a prod asset or promote a Personal Org asset

**Reuse** copies a production Dashboard, Visualization, DMO, SDM, or CIO
into a Personal Org workspace. **Promotion** packages a Personal Org asset
and, after the export is ready, lands datakits in a git repo via a reviewed
PR. Both use `create_reuse_promotion_request`; only Promotion then uses
`create_promotion_pull_request`.

Not a greenfield create (`build-end-to-end.md` / `create_semantic_model`) and
not sharing with a user (`share-asset.md`).

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **Confirmation (this guide):** confirm `requestType` (Reuse vs Promotion),
  `assetId`, workspace, label, and `requesterComment` before create. After a
  Promotion export is `Ready`, **ask again** before
  `create_promotion_pull_request`. Ask for the target directory and branch
  name — do not invent them.

## Steps

Direction flip, poll fields (`status` vs `packageExportStatus`), list
filters, HTTP 400, and the client-side convert/`gh` procedure are in
**`../sharing-and-promotion.md`** (§Promote).

1. Confirm Personal Org context. Create is rejected outside it.
2. `create_reuse_promotion_request` with a non-empty `requesterComment`
   (max 254 chars).
   Reuse: prod `assetId` + Personal Org destination workspace. Promotion:
   Personal Org `assetId` + the workspace that contains it.
3. Poll **`get_promotion_reuse_request`** with the returned id (not an
   unfiltered list). Reuse: wait for the terminal `completed` (not
   `migrationSucceeded`, a transient intermediate a late poll skips); **STOP**
   on `failed` / `cancelled` / `rejected` (`rejectionComment` when rejected).
   Promotion: poll `packageExportStatus` for lowercase `ready` (10s × 30s
   window); `status` stays `requested` throughout.
4. Survey outstanding Reuse work with `list_promotion_reuse_requests` and
   top-level `requestType=reuse` (not a `requestParams` wrapper). For one
   known id, get-by-id.
5. Promotion only, after user confirm: `create_promotion_pull_request`, then
   the download / `sf` convert / copy / `gh pr create` recovery path in the
   deep ref. Stop if `sf` is missing.
