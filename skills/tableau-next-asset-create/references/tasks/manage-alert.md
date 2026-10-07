# Task: Create / update / list / delete a data alert

Persist an ongoing Tableau Next data monitor. One-off "why did this number
move" questions are `analyze-data.md`, not this guide.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for
  that `tableau-next-*` server tool (`shared-gates.md`).
- **Confirmation (this guide):** first `create_alert` / `update_alert` /
  `delete_alert` call is a preview. Show `alertSummary`, then retry with
  `userConfirmed=true`. `delete_alert` is irreversible.

## When **not** to use these tools

- **One-off interpretation** ("why did EMEA sales drop", "compare regions
  last quarter") → `analyze-data.md` / `analyze_data`. Do not pin an SDM
  there either.
- **A saved chart of current state** → `create-viz.md` / `build-dashboard.md`.

## Steps

Transcript-on-follow-up, do-not-pin-SDM, timeout-poll, full replacement on
update, and never-show-`savedDataAlertId` are in **`../alerts.md`**.

1. **List** — `get_alerts` (caller's alerts only).
2. **Create** — `create_alert` with `conversationContext`. Do **not** look
   up or pin `targetEntity*`. Preview, then `userConfirmed=true`.
3. **Update** — resolve `savedDataAlertId` via `get_alerts`, then
   `update_alert` with the **complete** desired configuration (omit = drop).
4. **Delete** — `get_alerts` then `delete_alert` after preview.
5. **Timeout** — poll `get_alerts`; do not immediately re-create.
