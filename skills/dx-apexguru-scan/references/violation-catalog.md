# ApexGuru Violation Catalog

Performance antipatterns ApexGuru detects, with what they mean and the typical fix.
Use this to explain a violation when the user asks "what does this mean / how do I
fix it?". The API's `report` carries per-violation `message`, `fixes`, and help-doc
`resources` — prefer those when present; this catalog is the fallback explanation.

| Rule (`rule`) | What it flags | Why it hurts | Typical fix |
|---------------|---------------|--------------|-------------|
| `SOQL_IN_LOOP` | A SOQL query inside a `for`/`while` loop | Each iteration issues a query → hits the 100-SOQL governor limit fast; slow | Move the query outside the loop; query once and build a `Map<Id, SObject>` keyed for lookup inside the loop |
| `DML_IN_LOOP` | `insert`/`update`/`delete`/`upsert` inside a loop | Each iteration issues DML → hits the 150-DML limit; slow | Collect records into a `List` and perform one DML statement after the loop |
| `GGD` | `Schema.getGlobalDescribe()` usage | Describes **every** object in the org — expensive, grows with org size | Use targeted describes (`SObjectType.getDescribe()`, `Schema.describeSObjects([...])`) for only the objects needed |
| `SOQL_NO_WHERE_OR_LIMIT` | SOQL with neither `WHERE` nor `LIMIT` | Full-table scan; can return huge result sets and blow the heap / row limits | Add a selective `WHERE` clause and/or a `LIMIT`; ensure filters are on indexed fields |
| `SOQL_UNUSED_FIELDS` | SELECTed fields never read | Wastes query CPU/heap fetching unused columns | Select only fields the code actually uses |

## Severity mapping

ApexGuru severities follow the standard 1–5 scale: **1 = Critical, 2 = High,
3 = Moderate, 4 = Low, 5 = Info.** `DML_IN_LOOP` and `SOQL_IN_LOOP` are usually the
highest-impact (governor-limit) findings.

## Static vs. full attribution

- **Static** findings come from source analysis alone — the antipattern exists in the
  code regardless of runtime.
- **Full** findings are enriched with production metrics — e.g. a `SOQL_IN_LOOP`
  that actually executed against large data volumes in production is prioritized
  higher. Always label which mode produced the results.
