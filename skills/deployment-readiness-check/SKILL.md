---
name: deployment-readiness-check
description: Comprehensive pre-deployment validation checklist for Salesforce releases. Use before deploying to production to catch metadata issues, test coverage gaps, and configuration errors.
license: Apache-2.0
compatibility: Requires Salesforce CLI, jq, bash
metadata:
  author: afv-library
  version: "1.0"
allowed-tools: Bash Read
---

## When to Use This Skill

Use this skill before deploying Salesforce metadata to production (or higher environments) to:
- Validate metadata quality and completeness
- Check test coverage meets organizational standards
- Verify security settings and permissions
- Identify configuration issues before deployment
- Generate deployment documentation

## Prerequisites

- Salesforce CLI installed and authenticated to target org
- `jq` command-line JSON processor installed
- Bash shell (Linux, macOS, or WSL on Windows)
- Source metadata in SFDX project format

## Step 1: Run Metadata Validation

Execute the validation script to check for common metadata issues:

```bash
bash scripts/check_metadata.sh
```

The script validates:
- **Metadata format** - Ensures all XML is well-formed
- **API versions** - Checks for outdated API versions
- **Deprecated features** - Identifies deprecated components
- **Naming conventions** - Validates standard naming patterns
- **File completeness** - Ensures meta.xml files are present

Review the output for any warnings or errors before proceeding.

## Step 2: Verify Test Coverage

Check that your Apex test coverage meets organizational standards:

```bash
# Run all tests and generate coverage report
sf apex test run --test-level RunLocalTests --result-format human --code-coverage --wait 10

# Check coverage percentage
sf apex get test --test-run-id <test-run-id> --code-coverage --result-format json | jq '.summary.testRunCoverage'
```

**Minimum requirements**:
- Overall org coverage: ≥75% (Salesforce minimum)
- Individual class coverage: ≥75% (recommended)
- No classes with 0% coverage

If coverage is below threshold:
1. Identify uncovered classes using the coverage report
2. Add test methods to increase coverage
3. Rerun tests until requirements are met

## Step 3: Security and Permissions Review

Review security settings and permissions to ensure proper access controls:

1. **Profile and Permission Set Review**
   - Check that custom profiles/permission sets follow least-privilege principle
   - Verify admin permissions are not granted to standard users
   - Ensure sensitive objects have appropriate FLS

2. **Sharing Rules and OWD**
   - Review Organization-Wide Defaults are appropriate
   - Validate sharing rules grant necessary access without over-sharing
   - Check for public groups with excessive membership

3. **API Access**
   - Verify Connected Apps have appropriate scopes
   - Check Named Credentials use secure authentication
   - Review Remote Site Settings are necessary

Consult the [security checklist reference](references/security_checklist.md) for detailed guidance.

## Step 4: Configuration Validation

Verify configuration settings are deployment-ready:

```bash
# Check for hardcoded URLs or IDs
grep -r "https://.*\.salesforce\.com" force-app/main/default/
grep -r "[a-zA-Z0-9]{15,18}" force-app/main/default/ | grep -v "meta.xml"

# Validate Custom Settings and Custom Metadata
sf project retrieve start --metadata CustomObject:*__c
```

**Configuration checklist**:
- [ ] No hardcoded production URLs in code
- [ ] No hardcoded record IDs
- [ ] Custom Settings configured correctly for target org
- [ ] Custom Metadata Types populated appropriately
- [ ] Email templates reference correct org email
- [ ] Reports and Dashboards folders have correct permissions

## Step 5: Review Dependencies

Check for dependency conflicts or missing components:

```bash
# Generate dependency report
sf project deploy validate --manifest package.xml --test-level RunLocalTests --verbose

# Check for missing dependencies
grep -i "error.*component" deployment_log.txt
```

Common dependency issues:
- Missing Custom Fields referenced in code
- Validation Rules referencing deleted fields
- Workflows or Process Builders using deprecated actions
- Lightning Components with missing design resources

See [dependency troubleshooting guide](references/dependency_resolution.md) for solutions.

## Step 6: Generate Deployment Checklist

Use the deployment checklist template to document your release:

```bash
cp assets/deployment_checklist.md deployment_checklist_$(date +%Y%m%d).md
```

Fill out the checklist with:
- [ ] Deployment date and time window
- [ ] Components being deployed (attach package.xml)
- [ ] Test execution results and coverage
- [ ] Backup verification (data and metadata)
- [ ] Rollback procedure documented
- [ ] Stakeholders notified
- [ ] Post-deployment validation steps
- [ ] Monitoring plan for 24-48 hours

## Step 7: Execute Pre-Deployment Validation

Run a validation-only deployment to catch issues before actual deployment:

```bash
# Validate deployment without committing
sf project deploy validate \
  --manifest package.xml \
  --test-level RunLocalTests \
  --verbose

# Save the validation ID for quick deploy
sf project deploy start --use-most-recent-validation --async
```

**Benefits of validation**:
- Tests run in production environment
- Identifies environment-specific issues
- Generates Quick Deploy ID for faster deployment
- No changes committed until you confirm

Review validation results and address any failures before scheduling deployment.

## Step 8: Prepare Rollback Plan

Document rollback procedures before deploying:

1. **Backup current state**
   ```bash
   sf project retrieve start --manifest package.xml --target-org production
   git tag pre-deployment-$(date +%Y%m%d) && git push --tags
   ```

2. **Test rollback procedure** in sandbox:
   - Deploy previous version of metadata
   - Verify functionality is restored
   - Document any data cleanup required

3. **Establish rollback criteria**:
   - Critical bugs found within 2 hours
   - Core functionality broken
   - Performance degradation >50%
   - Data integrity issues

See [rollback procedures reference](references/rollback_procedures.md) for detailed steps.

## Post-Deployment Validation

After successful deployment, verify the release:

1. **Smoke tests** - Execute critical user workflows
2. **Monitor logs** - Check debug logs for errors (24-48 hours)
3. **Query test data** - Verify triggers and automation work correctly
4. **User acceptance** - Confirm with stakeholders functionality works
5. **Performance check** - Review governor limit usage in logs

## Common Issues and Solutions

### Issue: Test Coverage Drops Below 75%

**Cause**: New Apex classes added without sufficient tests.

**Solution**:
1. Run `sf apex test run --code-coverage` to identify gaps
2. Add test methods covering uncovered lines
3. Revalidate coverage

### Issue: Validation Fails with "Component Not Found"

**Cause**: Missing dependency in package.xml.

**Solution**:
1. Review error message for missing component
2. Add component to package.xml
3. Retrieve component from source org if needed
4. Revalidate

### Issue: Permission Errors After Deployment

**Cause**: FLS or object permissions not deployed correctly.

**Solution**:
1. Verify profiles/permission sets are in package.xml
2. Check that CustomObject metadata includes field permissions
3. Deploy profiles separately if needed
4. Use Permission Set Groups for complex permission hierarchies

## Best Practices

1. **Always validate before deploying** - Never deploy directly to production without validation
2. **Run full test suite** - Use RunLocalTests, not NoTestRun
3. **Deploy during maintenance windows** - Minimize impact on users
4. **Communicate with stakeholders** - Notify before, during, and after deployment
5. **Monitor post-deployment** - Watch logs and user feedback for 24-48 hours
6. **Document everything** - Maintain deployment logs and decisions
7. **Use version control tags** - Tag releases for easy rollback

## References

- [Security Checklist](references/security_checklist.md) - Detailed security review steps
- [Dependency Resolution Guide](references/dependency_resolution.md) - Solve dependency conflicts
- [Rollback Procedures](references/rollback_procedures.md) - Step-by-step rollback guide
- [Deployment Checklist Template](assets/deployment_checklist.md) - Reusable checklist

## Automation Opportunities

Consider automating this skill:
- **CI/CD Integration** - Run validation script in pipeline
- **Scheduled Coverage Checks** - Monitor test coverage daily
- **Auto-generated Documentation** - Create deployment notes from package.xml
- **Slack/Email Notifications** - Alert team of deployment status
