# Rollback Procedures

This guide provides step-by-step instructions for rolling back a Salesforce deployment if issues are discovered after release.

## When to Rollback

Execute a rollback when:
- **Critical functionality is broken** and cannot be hotfixed quickly
- **Data integrity issues** are discovered
- **Performance degradation** exceeds 50% of baseline
- **Security vulnerabilities** are introduced
- **Stakeholder approval** to rollback is obtained

Do NOT rollback for:
- Minor UI issues that don't impact functionality
- Issues that can be hotfixed in < 2 hours
- Edge cases affecting < 5% of users
- Cosmetic problems

## Pre-Rollback Checklist

Before initiating rollback:

- [ ] Confirm the issue severity justifies rollback
- [ ] Obtain stakeholder approval
- [ ] Notify all users of upcoming rollback
- [ ] Backup current production state (post-deployment)
- [ ] Verify pre-deployment backup is available
- [ ] Review rollback plan with team
- [ ] Prepare communication for completion

## Rollback Methods

### Method 1: Redeploy Previous Version (Recommended)

**Best for**: Metadata-only deployments with no data changes.

**Steps**:

1. **Retrieve pre-deployment state from version control**:
   ```bash
   git checkout pre-deployment-YYYYMMDD
   ```

2. **Validate rollback deployment**:
   ```bash
   sf project deploy validate \
     --manifest manifest/package.xml \
     --test-level RunLocalTests \
     --target-org production
   ```

3. **Deploy previous version**:
   ```bash
   sf project deploy start \
     --manifest manifest/package.xml \
     --test-level RunLocalTests \
     --target-org production
   ```

4. **Verify rollback**:
   - Test critical user flows
   - Check for errors in debug logs
   - Confirm with stakeholders

**Timeline**: 30-60 minutes

### Method 2: Selective Component Rollback

**Best for**: When only specific components are problematic.

**Steps**:

1. **Identify problematic components**:
   - Review error logs
   - Isolate failing functionality
   - List components to rollback

2. **Create targeted package.xml**:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <types>
           <members>ProblematicClass</members>
           <name>ApexClass</name>
       </types>
       <version>59.0</version>
   </Package>
   ```

3. **Retrieve previous version of components**:
   ```bash
   git show pre-deployment-YYYYMMDD:force-app/main/default/classes/ProblematicClass.cls > temp/ProblematicClass.cls
   ```

4. **Deploy only those components**:
   ```bash
   sf project deploy start \
     --manifest rollback-package.xml \
     --target-org production
   ```

**Timeline**: 15-30 minutes

### Method 3: Destructive Changes

**Best for**: When new components must be removed entirely.

**Steps**:

1. **Create destructiveChanges.xml**:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <types>
           <members>NewComponentToDelete</members>
           <name>ApexClass</name>
       </types>
       <version>59.0</version>
   </Package>
   ```

2. **Create empty package.xml**:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <version>59.0</version>
   </Package>
   ```

3. **Deploy destructive changes**:
   ```bash
   sf project deploy start \
     --manifest package.xml \
     --pre-destructive-changes destructiveChanges.xml \
     --test-level RunLocalTests \
     --target-org production
   ```

4. **Verify deletion**:
   ```bash
   sf org list metadata --metadata-type ApexClass --target-org production
   ```

**Timeline**: 20-40 minutes

## Data Rollback Considerations

If the deployment included data changes:

### Option A: Restore from Backup

1. **Locate pre-deployment data backup**:
   - Data Export Service snapshot
   - Backup tool (OwnBackup, Spanning, etc.)
   - Manual CSV exports

2. **Restore data**:
   ```bash
   sf data import tree --plan data-backup/data-plan.json --target-org production
   ```

3. **Validate data integrity**:
   - Run data quality checks
   - Verify record counts
   - Check relationships

**Timeline**: 1-4 hours (depending on data volume)

### Option B: Reverse Data Changes (Scripted)

1. **Identify affected records**:
   ```bash
   sf data query --query "SELECT Id FROM Account WHERE LastModifiedDate >= YESTERDAY"
   ```

2. **Apply reverse operations**:
   - Create Apex script to reverse changes
   - Test in sandbox first
   - Execute in production

**Timeline**: 2-6 hours

## Post-Rollback Steps

After rollback is complete:

1. **Verify Functionality**:
   - [ ] Execute smoke tests
   - [ ] Confirm critical workflows work
   - [ ] Check automation (triggers, flows) operates correctly
   - [ ] Review debug logs for errors

2. **Communication**:
   - [ ] Notify users rollback is complete
   - [ ] Send post-mortem summary to stakeholders
   - [ ] Update status page / internal wiki

3. **Root Cause Analysis**:
   - [ ] Document what went wrong
   - [ ] Identify why issues weren't caught pre-deployment
   - [ ] Update deployment checklist to prevent recurrence
   - [ ] Schedule retrospective with team

4. **Next Steps**:
   - [ ] Fix issues in development environment
   - [ ] Add test cases to catch similar issues
   - [ ] Re-validate deployment in sandbox
   - [ ] Schedule new deployment with fixes

## Emergency Contacts

**Production Issues**:
- On-call DevOps: [contact info]
- Salesforce Support: [premier support phone]
- Release Manager: [contact info]

**Stakeholder Notifications**:
- Product Owner: [contact info]
- Business Analyst: [contact info]
- Executive Sponsor: [contact info]

## Rollback Decision Matrix

| Severity | Impact | Rollback? | Timeline |
|----------|--------|-----------|----------|
| **Critical** | >50% users affected, core functionality broken | Yes | Immediate (< 1 hour) |
| **High** | 10-50% users affected, workaround exists | Consider | Within 2-4 hours |
| **Medium** | <10% users affected, non-critical features | No, hotfix instead | Plan fix for next release |
| **Low** | Edge case, cosmetic issues | No | Address in backlog |

## Lessons Learned Template

After each rollback, document lessons learned:

```markdown
# Rollback Post-Mortem: [Date]

## Deployment Summary
- Deployment date/time: [timestamp]
- Components deployed: [list]
- Rollback date/time: [timestamp]
- Rollback method used: [method]

## Issue Description
[Describe what went wrong]

## Root Cause
[Why did the issue occur?]

## Detection
- How was the issue discovered?
- How long after deployment?
- Who reported it?

## Impact
- Number of users affected: [count]
- Business processes impacted: [list]
- Duration of impact: [timespan]

## Resolution
- Rollback timeline: [start - end]
- Additional fixes required: [list]

## Prevention
- What tests would have caught this?
- Process improvements needed:
- Deployment checklist updates:

## Action Items
- [ ] [Action item with owner]
- [ ] [Action item with owner]
```

## Best Practices

1. **Practice rollbacks in sandbox** - Don't wait for an emergency to learn the process
2. **Maintain detailed backups** - Automate metadata and data backups before every deployment
3. **Use version control tags** - Tag every production deployment for easy identification
4. **Document everything** - Keep a deployment log with timestamps and decisions
5. **Communicate proactively** - Keep stakeholders informed throughout the process
6. **Set time limits** - If rollback takes >2 hours, consider alternative approaches
7. **Test the rollback** - Validate in sandbox that the rollback process works

## Rollback Scripts Repository

Keep commonly-used rollback scripts in version control:

```
scripts/rollback/
├── rollback-apex.sh          # Rollback Apex classes
├── rollback-lwc.sh           # Rollback Lightning Web Components
├── rollback-flows.sh         # Rollback flows and processes
├── rollback-data.sh          # Restore data from backup
└── verify-rollback.sh        # Post-rollback verification
```

## Testing Rollback Procedures

**Quarterly rollback drill**:
1. Deploy a test change to sandbox
2. Wait 1 hour
3. Execute full rollback procedure
4. Time the process
5. Document any issues
6. Update procedures as needed

This ensures the team is prepared when a real rollback is needed.
