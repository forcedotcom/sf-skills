<!-- Parent: handling-sf-data/SKILL.md -->
# Test Data Best Practices

Use this guide when creating or troubleshooting org data for demos, automation validation, integration checks, or post-deploy smoke testing.

## Describe-first rule

Before creating or updating records, validate the object shape with:

```bash
sf sobject describe --sobject ObjectName --target-org <alias> --json
```

Use describe output to confirm:
- required fields
- createable and updateable fields
- valid picklist values
- parent relationships
- fields that should be excluded from the payload

### Handy filters

```bash
# Required + createable fields
jq '.result.fields[] | select(.nillable==false and .createable==true) | {name, type}'

# Picklist values for one field
jq '.result.fields[] | select(.name=="Status__c") | .picklistValues[].value'

# Fields that are not createable
jq '.result.fields[] | select(.createable==false) | .name'
```

## CLI-first for straightforward CRUD

Prefer `sf data` commands when the workflow is simple and direct.

```bash
sf data create record \
  --sobject Account \
  --values "Name='Bulk Test 001' Industry='Technology'" \
  --target-org <alias> \
  --json
```

Use anonymous Apex when you need:
- multi-object orchestration in one transaction
- reusable factory logic
- rollback via savepoint
- complex branching that would be awkward in shell commands

## Pre-flight checklist

Before data creation:
- [ ] target object exists in the org
- [ ] required parent records exist
- [ ] required fields are known
- [ ] picklist values are validated from describe output
- [ ] non-createable fields are excluded
- [ ] cleanup plan is ready

## Common failure patterns

| Failure | Likely cause | Fix |
|---|---|---|
| `REQUIRED_FIELD_MISSING` | Required field omitted | add describe-backed required values |
| invalid picklist value | guessed value | inspect real picklist values first |
| non-writeable field error | field is not createable/updateable | remove it from the payload |
| `INVALID_CROSS_REFERENCE_KEY` | missing or wrong parent Id | create/query parent first |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | validation rule blocked test data | use a valid scenario or adjust setup |

## Bounded retry strategy

Use a small, explicit retry loop:

1. **Attempt 1** — run the primary CLI command
2. **Attempt 2** — retry once with corrected parameters
3. **Attempt 3** — re-run describe, verify assumptions, and pivot if needed
4. **Stop** — provide a manual workaround or alternate loading strategy

Do not keep repeating the same failing shape.

## Manual fallback options

If direct record creation keeps failing:
- switch to tree import for parent-child data
- switch to anonymous Apex for transactional setup
- split the operation into parent-first then child records
- provide the user with an exact manual setup checklist

## Cleanup expectations

Whenever test data is created, provide one of:
- delete-by-ID commands
- delete-by-pattern guidance
- delete-by-created-date guidance
- rollback script or savepoint flow

## Related references

- [sf-cli-data-commands.md](sf-cli-data-commands.md)
- [test-data-patterns.md](test-data-patterns.md)
- [cleanup-rollback-guide.md](cleanup-rollback-guide.md)
- [orchestration.md](orchestration.md)
