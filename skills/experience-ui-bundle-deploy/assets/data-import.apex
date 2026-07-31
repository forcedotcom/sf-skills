/*
 * Anonymous Apex — seed-data import (ONE sobject, ONE batch).
 *
 * Ported verbatim from reference org-setup.mjs buildApexInsert (lines 1016-1061).
 * Apply this template as-is; do NOT invent your own insert Apex.
 *
 * WHY Apex and not `sf data import tree` / REST:
 *   - DuplicateRuleHeader.allowSave = true bypasses BOTH duplicate-rule blocks
 *     AND matching-service timeouts that the REST Sforce-Duplicate-Rule-Action
 *     header cannot override. Seed fixtures are controlled app data, not user
 *     input, so bypassing duplicate rules is intentional and safe.
 *   - One machine-readable SETUP_RESULT_JSON line (not one debug per record) is
 *     parsed by the caller; a missing/truncated marker MUST be treated as a hard
 *     failure, never as "0 errors".
 *
 * HOW TO FILL THIS IN, per <SObject> file in the data plan (in plan order):
 *   1. Replace <SObject> with the object API name (e.g. Account, Contact).
 *   2. For each record, emit one `{ ... recs.add(r); }` block with an
 *      `r.put('<Field>', <literal>);` line per field. Skip the "attributes" key.
 *   3. Encode literals with these rules (from apexLiteral, lines 1003-1014):
 *        - null/undefined            -> null
 *        - boolean / number          -> the bare value (true, 42)
 *        - 'YYYY-MM-DD'              -> Date.valueOf('YYYY-MM-DD')
 *        - 'YYYY-MM-DDThh:mm...'     -> DateTime.valueOf('YYYY-MM-DD hh:mm:ss')
 *        - any other string          -> single-quoted, with \ escaped to \\
 *                                       and ' escaped to \'
 *   4. refs[] holds each record's referenceId (or _idx<N> when absent), in the
 *      SAME order as recs. Single-quote-escape each ref value.
 *   5. Keep each batch under 25000 rendered Apex chars and <= 200 records
 *      (see references/data-import.md — measured batching). Split into multiple
 *      files/runs when a plan file exceeds that.
 *
 * VALIDATION (non-negotiable): the SObject type and every field API name land as
 * bare Apex identifiers, so they MUST match ^[A-Za-z0-9_]+$ — letters, digits,
 * and underscores only (validateApiName, org-setup-utils.mjs 106-116). Reject
 * anything else as a fixture bug — never interpolate an unvalidated name.
 */

Database.DMLOptions dmlOpts = new Database.DMLOptions();
dmlOpts.DuplicateRuleHeader.allowSave = true;
List<<SObject>> recs = new List<<SObject>>();

{ <SObject> r = new <SObject>();
r.put('<Field1>', <literal1>);
r.put('<Field2>', <literal2>);
recs.add(r); }

/* ...one block per record... */

Database.SaveResult[] results = Database.insert(recs, dmlOpts);
String[] refs = new String[]{'<ref0>','<ref1>'};

List<Object> setupOut = new List<Object>();
for (Integer i = 0; i < results.size(); i++) {
  Map<String,Object> m = new Map<String,Object>{ 'ref' => refs[i] };
  if (results[i].isSuccess()) { m.put('id', results[i].getId()); }
  else { m.put('err', results[i].getErrors()[0].getMessage()); }
  setupOut.add(m);
}
System.debug('SETUP_RESULT_JSON:' + JSON.serialize(setupOut));
