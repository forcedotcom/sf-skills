<!-- Parent: deploying-metadata/SKILL.md -->
# Salesforce Deployment Workflow Examples

This file contains practical examples of common Salesforce deployment scenarios using the deploying-metadata skill.

## Example 1: Basic Production Deployment

### User Request:
```
"Deploy my changes to production with full test coverage"
```

### Skill Execution:

1. **Pre-deployment checks**
   ```bash
   sf org display --target-org production
   sf project deploy start --dry-run --test-level RunLocalTests --target-org production --wait 30
   ```

2. **Validation output**
   ```
   ✓ Deployment validation succeeded
   ✓ Tests passed: 145/145 (92% coverage)
   ✓ Components validated: 23
   ```

3. **Quick deploy** (using validation ID)
   ```bash
   sf project deploy quick --job-id 0Af5g00000XXXXX --target-org production
   ```

4. **Final output**
   ```
   ## Salesforce Deployment Report

   ✓ Status: Succeeded
   ✓ Components Deployed: 23/23
   ✓ Tests Passed: 145/145 (92% coverage)
   ✓ Duration: 8m 32s

   ### Deployed Components:
   - ApexClass: AccountController, ContactTriggerHandler, LeadProcessor
   - ApexTrigger: AccountTrigger, ContactTrigger
   - LightningComponentBundle: accountCard, contactList
   ```

---

## Example 2: Selective Component Deployment

### User Request:
```
"Deploy only the new Lightning Web Components to sandbox"
```

### Skill Execution:

1. **Identify LWC components**
   ```bash
   # Find all LWC components
   ls -R force-app/main/default/lwc/
   ```

2. **Deploy specific directory**
   ```bash
   sf project deploy start \
     --source-dir force-app/main/default/lwc \
     --target-org dev-sandbox \
     --test-level NoTestRun \
     --wait 15
   ```

3. **Output**
   ```
   ✓ Deployment succeeded
   ✓ Components Deployed:
     - accountCard (LWC)
     - contactList (LWC)
     - opportunityBoard (LWC)
   ```

---

## Example 3: Hotfix Deployment

### User Request:
```
"I need to deploy an urgent bug fix in AccountController to production"
```

### Skill Execution:

1. **Verify the specific file**
   ```bash
   cat force-app/main/default/classes/AccountController.cls
   ```

2. **Run targeted tests**
   ```bash
   sf apex run test \
     --tests AccountControllerTest \
     --target-org production \
     --wait 5
   ```

3. **Deploy single class**
   ```bash
   sf project deploy start \
     --source-dir force-app/main/default/classes/AccountController.cls \
     --target-org production \
     --test-level RunSpecifiedTests \
     --tests AccountControllerTest \
     --wait 10
   ```

4. **Verification**
   ```bash
   sf project deploy report --job-id <job-id> --target-org production
   ```

---

## Example 4: Manifest-Based Deployment

### User Request:
```
"Deploy using the package.xml manifest for release v2.3"
```

### Skill Execution:

1. **Read manifest file**
   ```bash
   cat manifest/package-v2.3.xml
   ```

2. **Validate deployment**
   ```bash
   sf project deploy start \
     --manifest manifest/package-v2.3.xml \
     --target-org production \
     --dry-run \
     --test-level RunLocalTests \
     --wait 30
   ```

3. **Quick deploy**
   ```bash
   sf project deploy quick --job-id 0Af5g00000XXXXX --target-org production
   ```

---

## Example 5: Scratch Org Development Workflow

### User Request:
```
"Create a scratch org and deploy my feature branch"
```

### Skill Execution:

1. **Create scratch org**
   ```bash
   sf org create scratch \
     --definition-file config/project-scratch-def.json \
     --alias feature-branch-123 \
     --duration-days 7 \
     --set-default
   ```

2. **Push source**
   ```bash
   sf project deploy start --target-org feature-branch-123
   ```

3. **Assign permission sets**
   ```bash
   sf org assign permset --name AdminPermSet --target-org feature-branch-123
   ```

4. **Import test data**
   ```bash
   sf data import tree --plan data/sample-data-plan.json --target-org feature-branch-123
   ```

5. **Open org**
   ```bash
   sf org open --target-org feature-branch-123
   ```

---

## Example 6: Deployment Rollback

### User Request:
```
"The deployment failed, I need to rollback to the previous version"
```

### Skill Execution:

1. **Retrieve current production metadata** (if not backed up)
   ```bash
   sf project retrieve start \
     --manifest manifest/package-production.xml \
     --target-org production
   ```

2. **Check out previous version from git**
   ```bash
   git checkout v2.2-stable
   ```

3. **Deploy previous version**
   ```bash
   sf project deploy start \
     --manifest manifest/package-v2.2.xml \
     --target-org production \
     --test-level RunLocalTests \
     --wait 30
   ```

4. **Verify rollback**
   ```bash
   sf org open --target-org production
   ```

---

## Example 7: Destructive Changes

### User Request:
```
"Remove the deprecated CustomObject__c and old Apex classes"
```

### Skill Execution:

1. **Create destructiveChanges.xml**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Package xmlns="http://soap.sforce.com/2006/04/metadata">
       <types>
           <members>DeprecatedClass1</members>
           <members>DeprecatedClass2</members>
           <name>ApexClass</name>
       </types>
       <types>
           <members>CustomObject__c</members>
           <name>CustomObject</name>
       </types>
       <version>66.0</version>
   </Package>
   ```

2. **Deploy with destructive changes**
   ```bash
   sf project deploy start \
     --manifest manifest/package.xml \
     --post-destructive-changes manifest/destructiveChanges.xml \
     --target-org production \
     --test-level RunLocalTests \
     --wait 30
   ```

   > Current SF CLI releases support this combined pattern correctly, including runs where the manifest deploys one set of components while a destructive changes file deletes different components in the same operation.

---

## Example 8: Multi-Environment Deployment

### User Request:
```
"Deploy to dev, then staging, then production after each passes validation"
```

### Skill Execution:

1. **Deploy to Dev**
   ```bash
   sf project deploy start --target-org dev --test-level NoTestRun --wait 10
   ```

2. **Deploy to Staging**
   ```bash
   sf project deploy start --target-org staging --test-level RunLocalTests --wait 20
   ```

3. **Validate Production**
   ```bash
   sf project deploy start --target-org production --dry-run --test-level RunLocalTests --wait 30
   ```

4. **Deploy to Production** (after manual approval)
   ```bash
   sf project deploy quick --job-id <validation-job-id> --target-org production
   ```

---

## Example 9: Code Coverage Analysis

### User Request:
```
"Check my code coverage and identify classes that need more tests"
```

### Skill Execution:

1. **Run all tests**
   ```bash
   sf apex run test \
     --test-level RunLocalTests \
     --target-org dev \
     --code-coverage \
     --result-format human \
     --wait 15
   ```

2. **Analyze coverage report**
   ```
   Overall Code Coverage: 87%

   Classes with <75% coverage:
   - LeadProcessor: 62%
   - OpportunityHelper: 71%
   - AccountBatchProcessor: 45%

   Recommendations:
   1. Add test methods for LeadProcessor.processLeads()
   2. Test error handling in OpportunityHelper
   3. Create comprehensive tests for AccountBatchProcessor
   ```

---

## Example 10: Deployment Error Recovery

### User Request:
```
"Deployment failed with 'INVALID_CROSS_REFERENCE_KEY' error"
```

### Skill Execution:

1. **Analyze error**
   ```
   Error: INVALID_CROSS_REFERENCE_KEY
   Component: CustomObject__c.SomeLookupField__c
   Message: Field references non-existent object
   ```

2. **Identify dependency**
   ```bash
   grep -r "ReferencedObject__c" force-app/
   ```

3. **Solution provided**
   ```
   The error indicates that SomeLookupField__c references an object
   that doesn't exist in the target org.

   Solutions:
   1. Deploy the referenced object first
   2. Include both objects in the same deployment
   3. Update the field to reference a different object
   4. Check if the referenced object exists: sf org list metadata --metadata-type CustomObject
   ```

4. **Deploy with dependencies**
   ```bash
   # Include both in manifest
   sf project deploy start \
     --manifest manifest/package-with-dependencies.xml \
     --target-org production
   ```

---

## Tips for Successful Deployments

1. **Always validate first** - Use `--dry-run` for production
2. **Monitor test execution** - Watch for test failures early
3. **Check code coverage** - Ensure >75% minimum
4. **Deploy incrementally** - Smaller deployments are easier to troubleshoot
5. **Use version control** - Tag releases for easy rollback
6. **Document changes** - Keep deployment logs
7. **Test in sandbox** - Never test directly in production
8. **Handle dependencies** - Deploy referenced metadata first

---

*These examples demonstrate common patterns. The deploying-metadata skill adapts to your specific use case and provides guided assistance.*
