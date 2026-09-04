# preset: `set-comment-value`

Worked reference example for the `consumer-goods-promotion-bo-api-deploy` skill. The
skill's default flow interviews the user for the customization; this
preset short-circuits the interview with a pre-canned answer set.

Invoke with:

```text
--preset set-comment-value
```

or, during the interview, tell the skill "use the SetCommentValue
reference".

## What it does

Copies the top-level `Comment` value from a tactic ingest payload onto
`Tactic__c.Comment__c` on the resulting Tactic record. Wired into all
three workflows (`create`, `update`, `copy`).

## Files

- `interview-answers.json` — Phase 5 interview answers the skill loads
  when this preset is chosen. Also a starting template for customers who
  want to hand-edit before running `--interview-file`.
- `SetCommentValue.cls` + `.cls-meta.xml` — the class the skill deploys.
  Namespace-agnostic: the tactic-namespace prefix is derived from
  `SObject.getSObjectType()` at runtime.
- `payloads/create.json`, `update.json`, `copy.json` — Phase 6 smoke-test
  fixtures with `REPLACED-AT-RUNTIME` markers for the ids captured
  during the run.
