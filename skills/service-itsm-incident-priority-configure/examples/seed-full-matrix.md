# Seeding a Full Matrix

Seed all cells at once with the conventional Impact × Urgency mapping. With the sf-CLI Tooling API path, each cell is its own POST — there is no server-side "replace whole matrix" endpoint. Compose the plan first, confirm with the user, then dispatch one POST per cell.

## Pre-requisites

1. Fetch the entity's active picklist values — see `../references/sf-cli-invocation.md` § Picklist extraction.
2. Read the current matrix rows via Tooling SOQL. If the matrix is non-empty and the user asked to *seed*, ask whether they want to **replace** (delete existing rows first) or **augment** (add only missing cells) — do not seed blindly on top of existing rows.
3. Confirm the conventional mapping below uses only values in the fetched picklists. If the org has customized picklists, adjust the plan before dispatch — do not silently coerce.

## Conventional mapping (defaults only)

```text
Impact ↓ / Urgency →   High       Medium     Low
High                    Critical   High       Moderate
Medium                  High       Moderate   Low
Low                     Moderate   Low        Low
```

Treat as a starting point; customers often grow to 4–5 levels per axis and add `Trivial` / `Emergency`. Confirm the resulting priorities with the user before dispatch.

## Dispatch — one POST per row

Replace `<alias>` with the user's target-org alias. Pick starting `<unique>` as `max(current DeveloperName suffix) + 1`, incrementing for each row.

```bash
# One row per POST — repeat for each of the nine cells.
# Pass each body inline with --body '{...}'; sf api request rest also accepts
# --body @file, but inline keeps the payload in the skill's control.
sf api request rest \
  "/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig" \
  --method POST \
  --header "Content-Type:application/json" \
  --body '{"ReferenceObject": "Incident", "Impact": "High", "Urgency": "High", "Priority": "Critical", "DeveloperName": "ServiceOpPriorityConfigIncidentSeed0", "MasterLabel": "ServiceOpPriorityConfigIncidentSeed0"}' \
  --target-org <alias>

# Repeat for rows 1–8 with the mapping above (increment the Seed<N> suffix).
```

Each POST returns `201 {"id": "<Id>", "success": true}`. If any POST returns a non-2xx, halt and surface the raw response — do not continue seeding partially.

For a scripted seed, iterate the mapping array in the caller's language of choice (bash + `jq`, node, etc.). Every row must be validated against the Phase-1 picklists before dispatch — the Tooling REST endpoint accepts garbage values silently.

## Replace vs. augment

The Tooling API path is not atomic across rows. Two choices:

**Augment (recommended):** For each conventional row, check the Phase-2 snapshot. Only POST rows whose `(Impact, Urgency)` coordinate is not already present. Existing rows keep their current Priority. The server does NOT enforce uniqueness on `(ReferenceObject, Urgency, Impact)`, so a POST on an already-present coordinate silently persists as a duplicate row — dedup is client-side only.

**Replace:** First `sf data delete record --sobject ServiceOpPriorityConfig --use-tooling-api --record-id <Id>` for every existing row, then POST the conventional set. Between the delete and the last POST the matrix is *partially populated* — the runtime priority derivation will use whatever rows are present at each moment. Warn the user before choosing replace.

Do not seed blindly on an entity with existing rows — surface the current state and confirm the intended semantics (replace vs. augment) with the user before Phase 4.
