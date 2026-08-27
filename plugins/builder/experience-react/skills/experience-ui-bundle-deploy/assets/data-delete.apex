/*
 * Anonymous Apex — clean existing seed data for ONE sobject before re-import.
 *
 * Ported verbatim from reference org-setup.mjs data delete sweep (lines 1649-1659).
 * Apply this template as-is; do NOT invent your own delete Apex.
 *
 * ORDER MATTERS: run one delete per sobject in REVERSE data-plan order (children
 * before parents) so foreign-key constraints don't block the delete. The import
 * runs in forward plan order; the delete runs in the reverse of that list.
 *
 * WHY allOrNone = false + emptyRecycleBin:
 *   - Database.delete(recs, false) deletes what it can and SKIPS records that
 *     can't be deleted (e.g. a Contact still linked to a Case) instead of
 *     aborting the whole batch. That is why the whole thing is wrapped in a
 *     try/catch that swallows the exception — a non-deletable record is expected,
 *     not a setup failure.
 *   - emptyRecycleBin frees unique fields immediately so the very next import
 *     doesn't collide with soft-deleted rows still holding those values.
 *
 * HOW TO FILL THIS IN:
 *   Replace <SObject> with the object API name. Validate it against
 *   ^[A-Za-z0-9_]+$ — letters, digits, and underscores only (validateApiName,
 *   org-setup-utils.mjs 106-116) — FIRST, since it is interpolated into a dynamic
 *   SOQL string literal; reject a malformed name as a fixture bug, never pass it
 *   through.
 */

try {
  List<SObject> recs = Database.query('SELECT Id FROM <SObject> LIMIT 10000');
  if (!recs.isEmpty()) {
    Database.delete(recs, false);
    Database.emptyRecycleBin(recs);
  }
} catch (Exception e) {
  // non-deletable records (e.g. Contact linked to Case) are skipped via allOrNone=false
}
