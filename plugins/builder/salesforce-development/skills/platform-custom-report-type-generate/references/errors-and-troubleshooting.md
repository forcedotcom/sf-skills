# Common Authoring Errors

Read this when a generated `.reportType-meta.xml` is rejected during deployment or fields don't appear in the report builder. Use these to validate the authored XML before handing it off; deployment itself is outside this skill's scope.

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid object name 'X'` on `<baseObject>` | Primary object doesn't exist or isn't deployed | Deploy the custom object before the CRT |
| `Invalid relationship name 'X'` on `<join>` | Used the field API name instead of the child relationship name, or forgot `__r` | Use the child relationship name (e.g. `Projects__r` for a custom relationship) |
| `Invalid field 'X' for object 'Y'` | Field doesn't exist on `<table>`, used label instead of API name, or field not yet deployed | Verify field API name; deploy dependent fields first |
| `Invalid category value 'X'` | Typo or non-existent category | Use a valid `ReportTypeCategory` value (see `category-values.md`); use `other` for general-purpose custom-object CRTs |
| Inner join after outer join | A nested `<join>` has `<outerJoin>false</outerJoin>` following an earlier outer join | Switch the nested join to `<outerJoin>true</outerJoin>`, or restructure so inner joins come first |
| Fields from joined object not visible in report builder | `<table>` in `<sections>` for the joined object doesn't use the dotted relationship path | Change `<table>` to the full path (e.g. `Account.Projects__r` not `Project__c`) |
| `Cannot change base object` on update | Attempted to change `<baseObject>` after initial deploy | Create a new CRT with the new primary object; retire the old one |
| File not found / fullName mismatch | File name doesn't match `<fullName>` | Rename file so `<fullName>.reportType-meta.xml` matches |

## Handling Conflicting Join Requirements

When a user wants both "include primary records without children" AND "exclude children that lack their own children" — those constraints are inexpressible in a single CRT join chain (Rule 7 forbids inner-after-outer). Three workarounds:

1. **All-outer + report-level filter** — keep all joins outer and filter at report time (e.g. `Case ID ≠ null`). Pragmatic, but every report author must remember the filter.
2. **Flip the base object** — base on the deepest required object. Lose primary-without-children but gain the inner-join guarantee. Lookup fields on the new base let you traverse back up for context.
3. **Two CRTs** — one all-outer for "all primary records," one inner-chained for "only primary records with full children." Users pick the right one.

Surface this trade-off to the user rather than picking silently.
