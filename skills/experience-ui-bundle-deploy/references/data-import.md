# Data import — protocol, batching, and reference resolution

Detail for the **data** step. Source of truth: reference `org-setup.mjs` data step
(lines 1622-1764), `buildApexInsert` (1016-1061), and `org-setup-utils.mjs`
`parseApexInsertResults` (134-183) + `planApexBatches` (204-222).

Run this step **only** when a data plan exists (`data-plan.json` in the `data/` dir). If it is
absent, no-op cleanly. **Always ask the user before importing or cleaning data** —
it deletes existing records.

## Inputs

- `data-plan.json` (in the `data/` dir) — an array of entries, in **import order**:
  ```json
  [{ "sobject": "Account", "files": ["accounts.json"], "saveRefs": true },
   { "sobject": "Contact", "files": ["contacts.json"] }]
  ```
- Each file is `{ "records": [ { "attributes": {...}, "Field": value, ... } ] }`
  (SFDX data-tree shape). `attributes.referenceId` is the record's ref handle.
- Optional `prepare-import-unique-fields.js` — if present in the project's
  `data/` dir, run it first to mangle unique fields so repeat imports don't
  collide. If the project lacks this script:
  1. Copy `assets/prepare-import-unique-fields.js` (bundled with this skill) into
     the project's `data/` directory.
  2. **Customize the `keyField` mapping** in the copied script based on the actual
     sobjects in `data-plan.json`. Map each sobject to its natural unique field
     (e.g., `Account: 'Name'`, `Contact: 'Email'`, custom object `Property__c: 'Address__c'`).
     Only sobjects listed in `keyField` will get `UniqueKey__c` stamped. Read the
     comment block in the script for guidance.
  3. Run it:
     ```bash
     cd data/
     node prepare-import-unique-fields.js
     ```
  The script self-locates via `import.meta.url` and requires `data-plan.json`
  to exist in the same directory.

## Sequence

1. **Prepare** (optional): run `prepare-import-unique-fields.js` if present.
2. **Clean** (reverse plan order): for each sobject, from last plan entry to
   first, run `assets/data-delete.apex`. Children are deleted before parents so
   FK constraints don't block the sweep. The sweep caps at `LIMIT 10000` per
   sobject (matches the reference) — if an org holds more seed rows than that, the
   surplus survives and a unique-field re-import may collide; note the cap to the
   user rather than assuming a clean slate.
3. **Import** (forward plan order): for each entry, for each file, resolve
   references, batch the records, and run `assets/data-import.apex` per batch.

## Reference resolution (`@referenceId`)

Before building a batch, walk every field value. A string value beginning with
`@` is a forward reference to a previously-inserted record's ref handle:

- `refMap` maps `referenceId -> real Salesforce Id`, populated only from entries
  whose plan entry has `"saveRefs": true` (line 1756-1757).
- For a field value `"@acctRef"`: if `refMap` has `acctRef`, replace the value
  with the real Id. If `refMap` is non-empty but the ref is unknown, log a
  warning (`unresolved ref @acctRef`) and leave the value as-is — do NOT abort
  (lines 1687-1694).

Because refs resolve from earlier inserts, plan order is load-bearing: parents
(with `saveRefs: true`) must precede the children that reference them.

## Measured batching

Do **not** guess batch sizes. Size each record's rendered Apex and pack batches
so `overhead + sum(recordSizes)` stays under the char limit, capped at the max
record count (lines 1698-1723, `planApexBatches` 204-222):

- `APEX_CHAR_LIMIT = 25000`
- `APEX_MAX_BATCH = 200`
- **overhead** = the length of `buildApexInsert(sobject, [], [])` — the fixed DML
  boilerplate rendered with zero records — so batch sizing can't drift from the
  actual emitted Apex.
- **per-record size** = the rendered `{ Sobj r = new Sobj(); ... recs.add(r); }`
  block PLUS the record's `refId` literal length (each record also grows the
  per-batch `String[] refs = new String[]{...}` line, so its ref is counted too,
  lines 1709-1717).
- **at-least-one guarantee**: a single record larger than the limit is placed
  alone in its own batch and left for Apex to accept or reject (never dropped,
  never an empty batch — `planApexBatches` line 214).

## Result protocol — `SETUP_RESULT_JSON:`

Each import batch emits exactly one machine-readable debug line:
`SETUP_RESULT_JSON:` followed by a JSON array of `{ ref, id }` (success) or
`{ ref, err }` (failure). Parse it as `parseApexInsertResults` does (134-183):

1. Find the `SETUP_RESULT_JSON:` marker; take the rest of that line up to the
   first newline.
2. **A missing or unparseable marker is a HARD FAILURE** — never read it as
   "0 errors". A truncated log line must abort the import, not let a partial
   insert look successful (lines 139-160, 1743-1748).
3. If any entry has `err`, print up to 5 of them and abort the step
   (lines 1749-1754).
4. On success with `saveRefs: true`, add each `{ref -> id}` to `refMap` for later
   entries (lines 1756-1757).

## Failure handling

- `sf apex run` non-zero AND output lacks `Compiled successfully` → the Apex
  failed to run; surface stderr and abort (lines 1738-1741).
- Any parsed record error → abort the whole data step (do not continue to the
  next sobject with a half-loaded parent).
