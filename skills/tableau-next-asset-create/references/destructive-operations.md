# Destructive and lifecycle operations

Cited by the router (`SKILL.md`). Confirm before every mutation listed here;
the whole-asset deletes have no undo.

- Component deletes (calc dimension/measure, metric, data object, logical view,
  relationship)
  → `references/sdm-tool-reference.md` (Deleting — preflight + leaf-first).
  Confirm first.
- Deleting a chart/dashboard/**whole** model/workspace is DESTRUCTIVE with no undo —
  always get explicit user confirmation before calling `delete_visualization` /
  `delete_dashboard` / `delete_semantic_model` / `delete_workspace`.
  Preflight viz/dashboard deletes with `list_asset_dependencies` (counts, not
  ids) — details in `references/dashboard-authoring.md` §7.
- `delete_visualization` can leave a broken dashboard widget behind if that viz is
  placed on a dashboard (`source` is silently nulled) — clean it up with a single
  `edit_dashboard` op: `remove_widget_from_dashboard` with the widget's
  `widgetName` (read back via `render_dashboard`/`get_dashboard`, or reused from
  an earlier upsert in the same draft). That one op deletes the definition
  **and** every page placement (`edit-dashboard.md` §6) — don't unplace first via
  `remove_widget_from_page`, that only unplaces and leaves the definition
  orphaned.
- Associating/disassociating an asset with a workspace uses `add_workspace_asset` /
  `remove_workspace_asset`. Both take **flat top-level args** (not a body wrapper).
  `assetUsageType` is `"Created"` or `"Referenced"` — this matters because
  `delete_workspace` cascade-deletes only `"Created"` assets. `remove_workspace_asset`
  takes the underlying asset's Salesforce `assetId` — the same id passed to
  `add_workspace_asset` and shown as `assetId` on `list_workspace_assets`.
- Sharing with a user or group (add / list / update / remove) →
  `references/tasks/share-asset.md`. Confirm before mutate; shapes in
  `sharing-and-promotion.md`.
- Reuse (prod → Personal Org copy) or Promotion (Personal Org package → git PR)
  → `references/tasks/promote-or-reuse.md`. `create_promotion_pull_request` is
  the package-URL step after `packageExportStatus` is Ready — not the create-
  request tool.
- Provisioning a Tableau Next **role** (`upsert_user`) is DESTRUCTIVE — never
  call it on the request turn. Preview + confirm in
  `references/tasks/provision-user.md`. ADMIN-ONLY; unauthorized → STOP (do
  not fall back to share/analyst tools).
- `delete_alert` is irreversible. Preview `alertSummary`, then
  `userConfirmed=true` (`references/tasks/manage-alert.md`).
- `delete_analytics_utterances` has no undo — confirm first
  (`references/tasks/review-verified-questions.md`).
- Response shape: several of these tools double-wrap responses as
  `{"defaultExc": "<stringified JSON>", "responseCode": <number>}` — parse
  `JSON.parse(response.defaultExc)`. On a 204 No Content success (e.g.
  `delete_dashboard`), `defaultExc` is an **empty string** (verified live), not
  JSON-parseable either way — branch on `responseCode === 204` for the success
  path rather than trying to parse `defaultExc`. The wrapping is per-tool, not
  family-wide: `edit_dashboard` is double-wrapped the same way; `create_dashboard`
  (as observed through this tool) returns a flat object with no wrapper.
  `remove_asset_share` is different: empty body on 204, failure a JSON array
  (`sharing-and-promotion.md`).
- `edit_dashboard` batches a widget/page edit atomically and stages an **unsaved
  draft by default** (top-level `autosave` unset/false) — the draft accumulates
  across successive `edit_dashboard` calls on the same dashboard until a
  `save_dashboard` op persists it (standalone, or after other mutations in the
  same batch), or `undo`/`discard_dashboard` reverts it. Never call
  `save_dashboard` automatically — only on the user's explicit confirmation
  given after they've seen the draft, even if the original request already
  said "save it" in the same message. Full mechanics:
  `references/edit-dashboard.md`.
