<!-- Parent: deploying-metadata/SKILL.md -->
# Deployment Report Template

Standard output format for Salesforce deployment summaries.

## Full Report Format

```markdown
## Salesforce Deployment Report

### Pre-Deployment Checks
✓ Org authenticated: <org-alias> (<org-id>)
✓ Project validated: sfdx-project.json found
✓ Components identified: X classes, Y triggers, Z components

### Deployment Execution
→ Deployment initiated: <timestamp>
→ Job ID: <deployment-job-id>
→ Test Level: RunLocalTests

### Results
✓ Status: Succeeded
✓ Components Deployed: X/X
✓ Tests Passed: Y/Y (Z% coverage)

### Deployed Components
- ApexClass: AccountController, ContactTriggerHandler
- LightningComponentBundle: accountCard, contactList
- CustomObject: CustomObject__c

### Next Steps
1. Verify functionality in target org
2. Monitor for any post-deployment issues
3. Update documentation and changelog
```

## Compact Report Format

For quick summaries:

```markdown
✓ Deployment: [org-alias] | Job: [job-id]
  Components: X/X | Tests: Y/Y (Z% coverage)
  Status: Succeeded
```

## Failure Report Format

```markdown
## Deployment Failed

### Error Summary
✗ Status: Failed
✗ Failed Components: 2/15

### Errors
1. ApexClass: MyController
   - Line 45: Variable 'acc' does not exist

2. CustomField: Account.Custom__c
   - Missing referenced field: Contact.Email

### Suggested Actions
1. Fix compilation error in MyController.cls:45
2. Deploy Contact.Email field before Account.Custom__c
3. Re-run deployment after fixes
```

## CI/CD Pipeline Output

For automated pipelines (GitHub Actions, GitLab CI):

```yaml
deployment:
  status: success|failure
  job_id: "0Af..."
  org: "<alias>"
  components:
    total: 15
    deployed: 15
    failed: 0
  tests:
    total: 45
    passed: 45
    failed: 0
    coverage: 87.5
  duration: "2m 34s"
  errors: []
```
