# Code Analyzer Violations

For each Code Analyzer violation, always include:

- The rule name translated to plain English
- The exact line number
- The fix direction (without writing code)

## Rule-name translations (examples)

| Rule name | Plain-language meaning | Fix direction |
|---|---|---|
| `ApexCRUDViolation` | A SOQL query or DML was made without checking object-level permissions first | Add a `Schema.sObjectType.<Object>.isAccessible()` (or `isCreateable`/`isUpdateable`) check before the operation |
| `ApexSharingViolations` | A class that performs data access does not declare sharing enforcement | Add `with sharing` (or an explicit `without sharing` with justification) to the class declaration |
| `ApexDangerousMethods` | A dangerous or disallowed method was used | Replace with the safe, supported alternative |
| `EmptyCatchBlock` | An exception is being swallowed silently | Log or handle the exception rather than leaving the catch block empty |

When a rule isn't in this table, translate it from its name and message into a plain-language description of what was violated, then give the fix direction.

## Plain-language rule

Never paste raw stack traces, JSON payloads, or internal Salesforce error codes into the output. Always translate to file name, method, line, and plain description.

## Fix location for violations

Code Analyzer violations almost always indicate a **production-code** fix — the static-analysis rule is flagging the code under test, not the test itself. Flag these as **Fix location: Production code** and track them separately from test-quality issues.
