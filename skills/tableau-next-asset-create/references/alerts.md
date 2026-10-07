# Data alerts — payloads and gotchas

Load this from `tasks/manage-alert.md`. Not a first hop.

Ongoing **monitors**, not one-off questions. `analyze_data` answers "why did
EMEA sales drop"; these tools persist a watch. Do **not** mix the two files.

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected.

## Contents

- `create_alert` / `update_alert` — NL monitor; preview then `userConfirmed`
- `get_alerts` — list / poll / resolve `savedDataAlertId`
- `delete_alert` — irreversible; same preview ritual

Live sidecars **clear** `targetEntityId`, `targetEntityType`, and
`targetEntityState` before delegation — **do not look up or pin an SDM**.

---

## Shared ritual (create and update)

**`conversationContext` (required).** First turn: the user's request as
plain text, e.g. "alert me when EMEA bookings drop more than 10% week over
week". On a **follow-up** (after `clarificationNeeded`, or when confirming
a preview), send the **full prior transcript** as a JSON array of turns in
chronological order:

```json
[{"role":"USER","value":"..."},{"role":"AGENT","value":"..."}]
```

Include your previous question as an `AGENT` turn and the user's reply as
the last `USER` element. Do **not** send only the latest message on a
follow-up — the backend needs prior turns to resolve what was agreed.

**Preview.** First call returns `confirmationRequired` + `alertSummary`.
Show that to the user, then retry with `userConfirmed=true`. Do not set
`userConfirmed` on the first call.

**Never display `savedDataAlertId`.** It is an internal id for follow-up
edits. Share `manageAlertsLink` (when returned) so the user can view, edit,
or delete the alert in the UI.

**Timeout ≠ failure.** The create/edit may still apply in the backend.
Retrying on a timeout can **duplicate**. Poll `get_alerts` a few times to
verify; do not immediately re-call create/update.

---

## `create_alert`

New monitor from a natural-language description.

**Required:** `conversationContext` (above). Do **not** pin
`targetEntityId` / `targetEntityType` / `targetEntityState`.

**Returns:** preview fields on the first call; once created:
`savedDataAlertId`, `explanatoryReasoning`, and (when present)
`manageAlertsLink`; or `clarificationNeeded`.

**Use when:** the user wants ongoing monitoring of a metric.

---

## `update_alert`

**FULL REPLACEMENT** of the alert's configuration, not a merge — anything
you omit is dropped. The alert keeps its id, subscriptions, and external
references.

**Required:** `savedDataAlertId` from `get_alerts`; `conversationContext` —
the **complete** desired configuration, not just the delta (e.g. "alert me
when EMEA bookings drop more than 15% week over week, checked every
Monday"). Same follow-up transcript rule. Do **not** pin an SDM.

**Returns:** `confirmationRequired` + `alertSummary` first (show it, then
retry with `userConfirmed=true`); `savedDataAlertId` (unchanged) and
`explanatoryReasoning` once applied; or `clarificationNeeded` if more
detail is needed or the alert can't be edited this way (delete and
recreate). Never display `savedDataAlertId`. `manageAlertsLink` is a
**create** return — do not expect it on update.

Confirm the id with `get_alerts` first. Timeout → poll `get_alerts`.

---

## `get_alerts`

Retrieve the **caller's** existing Tableau Next data alerts (LEX,
AgentForce, MCP). Do not supply an owner.

**Returns:** items with `id`, `name`, `schedule`, `threshold` / `condition`,
and delivery destinations.

**Use when:** "what alerts do I have", resolve an id before update/delete,
or poll after a timeout.

---

## `delete_alert`

Permanently delete one of the **caller's** alerts by `savedDataAlertId`
(from `get_alerts`). Irreversible — the alert stops firing and cannot be
recovered.

First call returns `confirmationRequired` + `alertSummary`. Show it, then
retry with `userConfirmed=true`. Success returns `deletedDataAlertId`.

Only the caller's own alerts can be deleted.
