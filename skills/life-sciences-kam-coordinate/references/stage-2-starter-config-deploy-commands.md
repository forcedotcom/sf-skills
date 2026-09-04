# Deploy Commands Reference

Exact CLI commands for each foundation deployment step. All commands use `--target-org <org>` where `<org>` is the user-provided org alias or username.

> **Working directory (required):** Run every `sf project deploy start` command from **inside the `.lsc-starter-config/LSStarterConfig/` project root** (the directory containing `sfdx-project.json`). `sf` searches the current directory and its ancestors — never its descendants — for `sfdx-project.json`, which pins `sourceApiVersion: 65.0`. If you run from a parent directory (or an unrelated repo), `sf` cannot find the project file, silently falls back to **API 60.0**, and profile deploys fail with `Property 'viewAllFields' not valid in version 60.0` (LSC profiles use 65.0-only permissions). The `.lsc-starter-config/LSStarterConfig/...` paths shown below are for readability — `cd` into `.lsc-starter-config/LSStarterConfig/` first and use paths relative to it (e.g. `PackageComponents/objects`).

## Step 1: StandardValueSets

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/standardValueSets --target-org <org>
```

Expected files deployed:

Generic Health-Cloud value sets:
- AccountRating.standardValueSet-meta.xml
- CPSSocialPlatformProvider.standardValueSet-meta.xml
- CareSpecialtySpecialtyType.standardValueSet-meta.xml
- CasePriority.standardValueSet-meta.xml
- CaseStatus.standardValueSet-meta.xml
- HProviderProviderClass.standardValueSet-meta.xml
- HProviderProviderType.standardValueSet-meta.xml
- HealthcareProviderStatus.standardValueSet-meta.xml
- InquiryTypeEnum.standardValueSet-meta.xml
- PAAffiliationRole.standardValueSet-meta.xml

KAM value sets (the ones confirmed with the admin before deploy — see Step 1 in `stage-2-starter-config-overview.md`). Confirmations A & B cover the first eight; `ActionPlanState` and `GoalAssignmentStatus` deploy with their shipped defaults (no prompt):
- StakeholderRoleType.standardValueSet-meta.xml
- StakeholderInfluenceLevel.standardValueSet-meta.xml
- StakeholderStrength.standardValueSet-meta.xml
- TerritoryBusinessPlanStatus.standardValueSet-meta.xml
- AccountPlanStatus.standardValueSet-meta.xml
- AccPlanObjectiveStatus.standardValueSet-meta.xml
- SprintStatus.standardValueSet-meta.xml
- AssessmentTaskCategory.standardValueSet-meta.xml
- ActionPlanState.standardValueSet-meta.xml
- GoalAssignmentStatus.standardValueSet-meta.xml

## Step 2: Objects

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/objects --target-org <org>
```

Deploys objects and their sub-components (recordTypes, compactLayouts, fieldSets, webLinks, businessProcesses):
- Account (recordTypes: Business, Business_Account, Health_Care_Organization; compactLayouts, fieldSets, webLinks)
- BusinessLicense (fieldSets)
- Case (recordTypes: Medical_Info_Request, Medical_Inquiry, Question; businessProcesses)
- HealthcareProvider (recordTypes: Health_Care_Organization, Health_Care_Provider)
- HealthcareProviderSpecialty (fieldSets)
- Inquiry (recordTypes: Adverse_Event, LSC_General, Medical_Inquiry; compactLayouts, fieldSets)
- InquiryQuestion (compactLayouts)
- InquiryQuestionAnswer (compactLayouts, fieldSets)
- PersonAccount (recordTypes: Health_Care_Provider, PersonAccount; compactLayouts)
- Product2 (recordTypes: LSC_Marketing_Item, LSC_Sample)
- ProviderAcctTerritoryInfo (recordTypes: Health_Care_Organization, Health_Care_Provider)
- ProviderVisitProdDiscussion (recordTypes: Patient_Tracking, Product_Feedback)
- User (fieldSets)
- Visit (compactLayouts, fieldSets)

## Step 3: Product Specification Types

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/productSpecificationTypes --target-org <org>
```

Files:
- LSPromotionalItem.productSpecificationType-meta.xml
- LSSampleProduct.productSpecificationType-meta.xml

## Step 4: Product Specification Record Types

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/productSpecificationRecTypes --target-org <org>
```

Files:
- LSC_Sample_LSSampleProduct.productSpecificationRecType-meta.xml
- LS_MarketingItem_LSPromotionalItem.productSpecificationRecType-meta.xml

## Step 5: Quick Actions

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/quickActions --target-org <org>
```

Files:
- Account.LogAVisit.quickAction-meta.xml
- Visit.Inquiry.quickAction-meta.xml

## Step 6: LSC Custom Profile (Skeleton)

```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile --target-org <org>
```

Deploys both skeleton profiles:
- LSC Custom Profile.profile-meta.xml
- Admin.profile-meta.xml

These are minimal profiles with field permissions and application visibility. Layout assignments and flexipage overrides are added later in Steps 11 and 13.

## Verifying Deployment Success

After each deploy command, check the output. A successful deployment shows:
```text
Deploy Succeeded.
```

If deployment fails, the output shows:
```text
Deploy Failed.
```

Capture the error message and component name for the recovery flow.

## Temporary Directory Pattern

For selective deploys (layouts, flexipages), create a temp directory structure **inside the SFDX project** (a `.lsc-deploy-tmp/` under the project root — never `/tmp` or any path outside the project), then remove it when done:
```bash
mkdir -p .lsc-deploy-tmp/<metadata-type>
cp <selected-files> .lsc-deploy-tmp/<metadata-type>/
sf project deploy start --source-dir .lsc-deploy-tmp --target-org <org>
rm -rf .lsc-deploy-tmp
```

Alternatively, use `--metadata` flag with specific component names:
```bash
sf project deploy start --metadata "Layout:Account-HCO Account Layout" --metadata "Layout:Visit-LSC Visit Layout" --target-org <org>
```
</content>
