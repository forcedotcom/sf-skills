# Trigger Handlers Reference

## Handler List

The following trigger handlers must be activated:

1. AffiliationUniquenessGenericHandler
2. AffiliationUniquenessHandler
3. HardAffiliationHandler
4. AffiliationReciprocalHandler
5. HealthcareProviderAffiliationHandler
6. AffiliationPrimaryChangeHandler
7. AffiliationAccountUpdateHandler
8. TerrAcctRcmdActionSharingHandler
9. TerrAccRcmActStatusUpdateHandler
10. CaseMSLQueueHandler
11. CaseChangeOwnershipHandler
12. CaseShareToCreatorHandler
13. StagePathPermissionsHandler
14. AccountPlanDeleteChildrenHandler
15. AccountPlanChangeStatusHandler
16. SetAccPlanPercentCompleteHandler
17. AcctPlanObjDeleteChildrenHandler
18. SetAccObjectPercentCompleteHandler
19. ActionPlanDeleteChildrenHandler
20. SetSprintPercentCompleteHandler
21. SetGoalAsgmtPercentCompleteHandler
22. SetActionPlanPercentCompleteHandler
23. AssessmentTaskDeleteAPItemHandler
24. AssessmentTaskSharingHandler
25. TerritoryBusinessPlanDeleteHandler
26. GoalAssignmentDeleteHandler
27. TerritoryBusPlanChangeStatusHandler
28. SetTerrBusPlanPrcntCompleteHandler

## Activation Method

Trigger handlers in Life Sciences Cloud are **`LifeScienceTriggerHandler`** records — a standard Tooling API entity (NOT a managed `lsc4ce__TriggerHandler__c` custom object). All queries and updates MUST use `--use-tooling-api`. Relevant fields:

- `DeveloperName` — the handler name (e.g. `AffiliationUniquenessGenericHandler`)
- `IsActive` — the active flag (Boolean)
- `ObjectApiName` — the object the handler runs on

> **Verified behavior:** the standard-API sobject name `lsc4ce__TriggerHandler__c` does NOT exist and returns `sObject type '...' is not supported`. `LifeScienceTriggerHandler` is only accessible via the Tooling API. A freshly-deployed org typically has ~185 handlers, all `IsActive=false` initially; the 28 below are the subset the starter config activates.

### Preferred: Query then Update (Tooling API)

First, get the handler's Id and current state:
```bash
sf data query --query "SELECT Id, DeveloperName, IsActive FROM LifeScienceTriggerHandler WHERE DeveloperName = '<HandlerName>'" --target-org <org> --use-tooling-api --json
```

Then activate by Id:
```bash
sf data update record --sobject LifeScienceTriggerHandler --record-id <Id> --values "IsActive=true" --target-org <org> --use-tooling-api
```

### Batch: query all inactive IDs in one call, then update each

Individual query-then-update per handler is slow (each `sf` invocation has startup overhead; 28 sequential handlers can exceed 2 minutes). Fetch all still-inactive IDs in ONE query, then loop the updates.

> **STOP-GATE (do not drop the last handler).** Build the update loop so it processes **every** returned ID. Two failure modes to avoid: **(1)** a naive `while read` over a *captured* ID list drops the final ID when that list has no trailing newline (the classic "27 of 28" bug); **(2)** an unquoted `for id in $IDS` loop relies on **bash word-splitting**, which **zsh does NOT do by default** — under zsh the whole multiline blob stays a single `$id`, every update fails on an invalid record-id, and you get **"0 of 28"**. Do NOT use either. The portable, shell-agnostic, drop-safe pattern is to pipe `jq` (which newline-terminates every record, including the last) into `while IFS= read -r id` via **process substitution** `< <(...)`: it behaves identically in bash and zsh and keeps the loop in the current shell so the counter survives. After the loop, always re-run the Verification query below and confirm the active count equals the full handler count (28) before proceeding — if it is short, identify the straggler(s) by name and activate each individually.

Use a single query filtered to `IsActive = false` (already-active handlers are skipped automatically — re-running is safe but wasteful), then loop with one of the safe patterns:

```bash
ORG=<org>
n=0; total=0
# Pipe jq (newline-terminates EVERY record, incl. the last) into `while read` via
# process substitution `< <(...)`. Portable across bash AND zsh; the loop stays in the
# current shell so $n/$total survive. Never `for id in $IDS` (zsh won't word-split it).
while IFS= read -r id; do
  total=$((total+1))
  sf data update record --sobject LifeScienceTriggerHandler --record-id "$id" \
    --values "IsActive=true" --target-org "$ORG" --use-tooling-api >/dev/null && n=$((n+1))
  echo "  ...$n activated"
done < <(sf data query \
  --query "SELECT Id FROM LifeScienceTriggerHandler WHERE IsActive = false AND DeveloperName IN ('AffiliationUniquenessGenericHandler','AffiliationUniquenessHandler','HardAffiliationHandler','AffiliationReciprocalHandler','HealthcareProviderAffiliationHandler','AffiliationPrimaryChangeHandler','AffiliationAccountUpdateHandler','TerrAcctRcmdActionSharingHandler','TerrAccRcmActStatusUpdateHandler','CaseMSLQueueHandler','CaseChangeOwnershipHandler','CaseShareToCreatorHandler','StagePathPermissionsHandler','AccountPlanDeleteChildrenHandler','AccountPlanChangeStatusHandler','SetAccPlanPercentCompleteHandler','AcctPlanObjDeleteChildrenHandler','SetAccObjectPercentCompleteHandler','ActionPlanDeleteChildrenHandler','SetSprintPercentCompleteHandler','SetGoalAsgmtPercentCompleteHandler','SetActionPlanPercentCompleteHandler','AssessmentTaskDeleteAPItemHandler','AssessmentTaskSharingHandler','TerritoryBusinessPlanDeleteHandler','GoalAssignmentDeleteHandler','TerritoryBusPlanChangeStatusHandler','SetTerrBusPlanPrcntCompleteHandler')" \
  --target-org "$ORG" --use-tooling-api --json | jq -r '.result.records[].Id')
echo "Activated $n of $total inactive handler(s)."
```

If every one of the 28 was already active, the query returns zero rows and the loop is a no-op — that is a valid PASS, not a failure.

### Verification

After activation, confirm the active count equals the full handler count (28) — count directly rather than eyeballing rows:
```bash
sf data query --query "SELECT COUNT(Id) active FROM LifeScienceTriggerHandler WHERE IsActive = true AND DeveloperName IN ('AffiliationUniquenessGenericHandler','AffiliationUniquenessHandler','HardAffiliationHandler','AffiliationReciprocalHandler','HealthcareProviderAffiliationHandler','AffiliationPrimaryChangeHandler','AffiliationAccountUpdateHandler','TerrAcctRcmdActionSharingHandler','TerrAccRcmActStatusUpdateHandler','CaseMSLQueueHandler','CaseChangeOwnershipHandler','CaseShareToCreatorHandler','StagePathPermissionsHandler','AccountPlanDeleteChildrenHandler','AccountPlanChangeStatusHandler','SetAccPlanPercentCompleteHandler','AcctPlanObjDeleteChildrenHandler','SetAccObjectPercentCompleteHandler','ActionPlanDeleteChildrenHandler','SetSprintPercentCompleteHandler','SetGoalAsgmtPercentCompleteHandler','SetActionPlanPercentCompleteHandler','AssessmentTaskDeleteAPItemHandler','AssessmentTaskSharingHandler','TerritoryBusinessPlanDeleteHandler','GoalAssignmentDeleteHandler','TerritoryBusPlanChangeStatusHandler','SetTerrBusPlanPrcntCompleteHandler')" --target-org <org> --use-tooling-api --json
```
The returned `active` count MUST be **28**. If it is fewer, list the still-inactive names (query the same set with `IsActive = false`), activate each straggler individually, and re-run this count until it reads 28. Do NOT proceed to the next step while any handler is inactive.

### Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `sObject type 'lsc4ce__TriggerHandler__c' is not supported` | Wrong object name / missing tooling flag | Use `LifeScienceTriggerHandler` with `--use-tooling-api` |
| "No records found" | Handler `DeveloperName` doesn't exist in the org | The managed package may not have created it yet; skip and note |
| Command times out activating all 28 | Sequential per-handler `sf` calls are slow | Fetch all inactive IDs in one query, then loop updates (see the safe-loop patterns above); skip already-active ones |
| "27 of 28 activated" / last handler skipped | A `while read` over a *captured* list dropped the final unterminated line | Use the jq-piped `while IFS= read -r` via process substitution shown above; re-run the count check and activate any straggler individually |
| "0 of 28 activated" (loop ran once, all IDs mashed into one value) | An unquoted `for id in $IDS` loop under **zsh**, which does not word-split unquoted params — `$IDS` stayed one multiline string | Use the jq-piped `while IFS= read -r` via process substitution shown above (portable across bash/zsh); never rely on `for` word-splitting |
| "Insufficient access" | User lacks edit permission on the tooling entity | User needs appropriate permission set |

### Progress Reporting

Report activation progress:
```text
Activating trigger handlers: 15/28 complete...
```

If any handler fails, collect all failures and report at the end:
```text
3 handlers could not be activated:
  - CaseMSLQueueHandler: No record found
  - StagePathPermissionsHandler: Field not found
  - AssessmentTaskSharingHandler: Insufficient access

25/28 handlers activated successfully.
Options:
  1. Retry failed handlers
  2. Skip and continue to next step
```
</content>
