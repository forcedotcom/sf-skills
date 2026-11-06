# Feature: Priority Matrix (delegated to the `ItsmPriorityMatrix` SOR)

How the orchestrator runs the **Priority Matrix** feature, which maps each Impact × Urgency combination on
Incident to a Priority. The `ItsmPriorityMatrix` SOR's own steps and guidance decide *how*; the
orchestrator runs them itself under its **SOR hand-off protocol** and owns every user-facing gate. This file
adds what is specific to the Priority Matrix.

1. `discover` the SOR by intent (e.g. "incident priority matrix impact urgency") and `describe` the id
   `discover` returns (`ItsmPriorityMatrix`). Its own prerequisite checks fall under protocol step 2. The
   SOR serves Incident and Problem, so pass the entity type `Incident` on every call (`entityType` on the
   `Priority` read, the matrix reads, and the save; `details` on the default-priority reads).
2. Read first: the org's **active** Incident `Priority` values (`describe-priority-picklist` —
   never hardcode or invent them), the current rows (`fetch-priority-matrix`), both preferences
   (`read-priority-matrix-prefs`, one call each: `IncPriorityMatrixEnabled`, the *Turn on Automatic
   Priority Assignment for IT Service* toggle, and `IncPriorityOverrideEnabled`, the *Set priority
   manually* checkbox), and the default priority (`get-default-priority`).
3. Ask only for what's missing: which cells change, the default priority, and whether manual override
   changes. Offer only active values, and flag a saved row whose Priority is no longer active rather than
   dropping it. If the matrix is off, include turning it on in the plan — with it off, Incidents don't get
   a priority from the matrix.
4. **The save is a full replacement**: `save-priority-matrix` deletes every row it isn't sent. Build the
   complete set from the fetched rows, change only the cells the user asked to change, and keep the
   override as read unless asked. Show which cells are added, changed, or removed, the resulting default,
   and the override state, and get an explicit yes. Re-run `describe-priority-picklist` right
   before the save and send only its active values. A change to only the matrix toggle or only the
   override uses `update-priority-matrix-enablement` instead, one preference per call, confirmed the same
   way.
5. Read back with `verify-priority-matrix` (rows), `verify-default-priority`, and `verify-manual-override`
   (or `verify-priority-matrix-enablement` after a toggle-only change). Mark it `Done` only when every part
   matches.
6. Only after a real write landed this run — never on a view or a no-op — mark the Salesforce Go *Define
   Priority Matrix* step complete (`mark-priority-matrix-step-complete`, then
   `verify-priority-matrix-step-complete`). A `404` there doesn't fail the feature: tell the user to tick
   that step manually on the Salesforce Go page.
