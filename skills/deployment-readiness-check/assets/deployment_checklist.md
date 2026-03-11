# Salesforce Deployment Checklist

**Deployment Date**: _________________  
**Deployment Time Window**: _________ to _________  
**Environment**: ☐ Production ☐ Sandbox ☐ UAT  
**Deployment Lead**: _________________  
**Release Version**: _________________

---

## Pre-Deployment

### 1. Code & Configuration Review

- [ ] All code reviewed and approved via pull request
- [ ] Code follows organizational coding standards
- [ ] No debugging statements or console.logs in production code
- [ ] API versions are current (API 56.0+)
- [ ] Hard-coded IDs/URLs removed (use Custom Settings or Custom Metadata)
- [ ] Comments and documentation are up-to-date

### 2. Testing

- [ ] All unit tests pass locally
- [ ] Test coverage meets minimum requirements (≥75% org-wide)
- [ ] Integration tests executed successfully
- [ ] User acceptance testing (UAT) completed
- [ ] Regression testing performed for existing features
- [ ] Performance testing validates no degradation

**Test Results**:
- Total classes: _____
- Test coverage: _____%
- Failed tests: _____
- Test run ID: _________________

### 3. Security Review

- [ ] Profile/permission set changes reviewed
- [ ] Field-level security validated
- [ ] Sharing rules appropriate for data sensitivity
- [ ] No admin permissions granted to standard users
- [ ] Connected Apps use appropriate OAuth scopes
- [ ] Named Credentials use secure authentication
- [ ] Sensitive data is encrypted or masked

### 4. Dependencies

- [ ] All metadata dependencies identified
- [ ] Missing components added to package.xml
- [ ] External system dependencies documented
- [ ] API integrations tested in target environment
- [ ] Third-party packages compatible with deployment

### 5. Backup & Rollback

- [ ] Pre-deployment backup completed
  - Metadata backup: ☐ Yes ☐ N/A
  - Data backup: ☐ Yes ☐ N/A
  - Backup location: _________________
- [ ] Rollback procedure documented and tested
- [ ] Rollback criteria defined
- [ ] Emergency contacts list current

### 6. Documentation

- [ ] Release notes prepared
- [ ] Deployment guide created
- [ ] User training materials ready (if applicable)
- [ ] Help documentation updated
- [ ] Known issues documented
- [ ] FAQ prepared for support team

### 7. Communication

- [ ] Stakeholders notified of deployment schedule
- [ ] Users notified of system downtime (if applicable)
- [ ] Support team briefed on changes
- [ ] Change advisory board approval obtained
- [ ] Post-deployment communication template ready

### 8. Validation

- [ ] Validation deployment successful in production
- [ ] Quick Deploy ID obtained: _________________
- [ ] Validation results reviewed and approved
- [ ] All deployment warnings addressed

**Validation Command**:
```bash
sf project deploy validate --manifest package.xml --test-level RunLocalTests --verbose
```

---

## Deployment Execution

### 9. Pre-Deployment Actions

- [ ] Announced maintenance window to users
- [ ] Disabled scheduled jobs/batch processes (if required)
  - Jobs disabled: _________________
- [ ] Created deployment tag in git: _________________
- [ ] Verified target org connectivity
- [ ] Team on standby for deployment

### 10. Deployment

**Deployment Start Time**: _________

- [ ] Deployment initiated via validated package or change set
- [ ] Deployment progress monitored
- [ ] Test execution in progress
- [ ] Any deployment errors addressed immediately

**Deployment Command**:
```bash
sf project deploy start --use-most-recent-validation
# OR
sf project deploy start --manifest package.xml --test-level RunLocalTests
```

**Deployment ID**: _________________

**Deployment End Time**: _________

**Duration**: _________ minutes

### 11. Post-Deployment Verification

- [ ] Deployment completed successfully
- [ ] All tests passed in production
- [ ] Deployment results reviewed (no warnings/errors)
- [ ] Smoke tests executed successfully
- [ ] Critical user workflows verified:
  - [ ] Workflow 1: _________________
  - [ ] Workflow 2: _________________
  - [ ] Workflow 3: _________________
- [ ] Re-enabled scheduled jobs/batch processes
- [ ] Debug logs show no new errors

### 12. Post-Deployment Actions

- [ ] Stakeholders notified of successful deployment
- [ ] Users notified system is available
- [ ] Release notes published
- [ ] Support team provided with deployment summary
- [ ] Monitoring dashboard reviewed

---

## Post-Deployment Monitoring (24-48 Hours)

### 13. System Monitoring

- [ ] **Day 1** - Monitor debug logs for errors
  - Errors found: ☐ Yes ☐ No
  - If yes, describe: _________________
- [ ] **Day 1** - Review governor limit usage
  - Limits exceeded: ☐ Yes ☐ No
- [ ] **Day 1** - Check user-reported issues
  - Issues reported: ☐ Yes ☐ No
- [ ] **Day 2** - Confirm automation working correctly
- [ ] **Day 2** - Validate data integrity
- [ ] **Day 2** - Review performance metrics

### 14. User Acceptance

- [ ] Key users confirmed functionality works
- [ ] No critical bugs reported
- [ ] User feedback collected
- [ ] Support tickets categorized by severity

**Feedback Summary**:
_________________

---

## Rollback (If Required)

**Rollback Decision**: ☐ Yes ☐ No

**Reason**: _________________

- [ ] Stakeholder approval for rollback obtained
- [ ] Users notified of rollback
- [ ] Rollback procedure executed
- [ ] Rollback verified successful
- [ ] Post-rollback communication sent

**Rollback Time**: _________

---

## Deployment Summary

### Components Deployed

| Component Type | Count | Examples |
|----------------|-------|----------|
| Apex Classes   |       |          |
| Apex Triggers  |       |          |
| LWC            |       |          |
| Flows          |       |          |
| Custom Objects |       |          |
| Custom Fields  |       |          |
| Profiles       |       |          |
| Perm Sets      |       |          |
| Other          |       |          |

**Total Components**: _____

### Deployment Metrics

- Validation time: _________ minutes
- Deployment time: _________ minutes
- Test execution time: _________ minutes
- Total elapsed time: _________ minutes
- Downtime (if any): _________ minutes

### Issues Encountered

| Issue | Severity | Resolution | Time to Resolve |
|-------|----------|------------|-----------------|
|       |          |            |                 |
|       |          |            |                 |

**Total Issues**: _____

---

## Sign-Off

### Deployment Team

**Deployment Lead**: _________________ Date: _________  
**Developer(s)**: _________________ Date: _________  
**QA Lead**: _________________ Date: _________  
**DevOps Engineer**: _________________ Date: _________

### Stakeholders

**Product Owner**: _________________ Date: _________  
**Business Analyst**: _________________ Date: _________  
**Release Manager**: _________________ Date: _________

---

## Post-Deployment Review

**Review Date**: _________________

### What Went Well
1. _________________
2. _________________
3. _________________

### What Could Be Improved
1. _________________
2. _________________
3. _________________

### Action Items
- [ ] Action: _________________ Owner: _________ Due: _________
- [ ] Action: _________________ Owner: _________ Due: _________
- [ ] Action: _________________ Owner: _________ Due: _________

---

## Attachments

- [ ] package.xml
- [ ] Test results report
- [ ] Deployment log
- [ ] Release notes
- [ ] Rollback procedure (if executed)
- [ ] Post-deployment monitoring reports

**Storage Location**: _________________

---

**Notes**:
_________________
_________________
_________________
