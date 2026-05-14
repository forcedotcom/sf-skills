# Deployment Transcript: Business Internet Plus Bundle

This transcript captures the skills used plus the planning and execution process for deploying `business-internet-plus-bundle` with Vlocity Build.

---

## Task Summary

Deploy the `Business Internet Plus` Product2 bundle DataPack and document the end-to-end process in `deploying-omnistudio-datapacks/examples`.

---

## Skills Used

### 1) `deploying-omnistudio-datapacks` (Primary)

**Why used:** The task is DataPack deployment orchestration with Vlocity Build commands (`validateLocalData`, `packDeploy`, `packRetry`) and failure triage.

**Applied guidance:**

- Validate-first execution (`validateLocalData` before deployment).
- Deterministic job file (`projectPath`, `expansionPath`, `manifest`) for reproducible scope.
- Retry loop and failure interpretation.

### 2) `modeling-omnistudio-epc-catalog` (Supporting)

**Why used:** The deployment target is an EPC Product2 offer bundle sample with Product Child Item dependencies and companion artifacts.

**Applied guidance:**

- Confirmed Product2 offer markers and companion file consistency.
- Preserved `%vlocity_namespace%` placeholders and stable GlobalKey references.

### 3) `deploying-metadata` (Supporting preflight pattern)

**Why used:** Reused deployment preflight discipline for target org/tooling readiness and concise completion reporting.

---

## Planning Process (Executed)

1. Confirm where the source bundle artifacts were authored.
2. Stage those artifacts into a standard Vlocity expansion path under `vlocity/Product2/<global-key>/`.
3. Build a deterministic deploy job file in this example folder.
4. Run pre-deploy validation (`validateLocalData`).
5. Run actual deployment (`packDeploy`).
6. Run retry (`packRetry`) to confirm whether the failure is transient or dependency-blocking.
7. Capture findings and next safe action.

---

## Execution Details

### A) Staging for deploy

Source payload location:

- `skills/modeling-omnistudio-epc-catalog/examples/business-internet-plus-bundle`

Deploy staging location:

- `vlocity/Product2/9f1d3c4a-8e5b-4d71-9a2d-f6b719a90101`

Staged files include:

- `Business-Internet-Plus_DataPack.json`
- `Business-Internet-Plus_AttributeAssignments.json`
- `Business-Internet-Plus_ProductChildItems.json`
- `Business-Internet-Plus_PricebookEntries.json`
- `Business-Internet-Plus_PriceListEntries.json`
- `Business-Internet-Plus_ObjectFieldAttributes.json`
- `Business-Internet-Plus_OrchestrationScenarios.json`
- `Business-Internet-Plus_DecompositionRelationships.json`
- `Business-Internet-Plus_CompiledAttributeOverrides.json`
- `Business-Internet-Plus_OverrideDefinitions.json`
- `Business-Internet-Plus_ParentKeys.json`

### B) Job file used

- `skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle-deploy/deploy-business-internet-plus-bundle.yaml`

Key settings:

- `projectPath: .`
- `expansionPath: vlocity`
- `manifest: Product2/9f1d3c4a-8e5b-4d71-9a2d-f6b719a90101`

### C) Commands executed

```bash
npx --yes vlocity -sfdx.username sample-uat -job "skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle-deploy/deploy-business-internet-plus-bundle.yaml" validateLocalData

npx --yes vlocity -sfdx.username sample-uat -job "skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle-deploy/deploy-business-internet-plus-bundle.yaml" packDeploy

npx --yes vlocity -sfdx.username sample-uat -job "skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle-deploy/deploy-business-internet-plus-bundle.yaml" packRetry
```

### D) Command outcomes

`validateLocalData`:

- Success (`1 Completed`)

`packDeploy`:

- Auto-settings migration phase completed successfully.
- Bundle deploy failed with dependency error:
  - `This DataPack has a reference to another object which was not found -- Product2/21e9dce1-4f89-4f99-a7b2-9cb5d6332101`

`packRetry`:

- Failed with the same missing reference error.

---

## Root Cause

The bundle references child Product2 DataPacks that are not currently present in local expansion scope and/or target org at deploy time.

Missing child Product2 keys confirmed absent from local `vlocity/Product2`:

- `21e9dce1-4f89-4f99-a7b2-9cb5d6332101` (Managed Router)
- `43f2fd94-6114-449b-a1b4-b8dd7238b202` (Internet Security Suite)
- `64a06b24-1135-4f2e-95a1-3a5f5822c303` (Static IP Add-On)

---

## Completion Block

```text
DataPack goal: deploy
Source org: N/A (local staged payload)
Target org: sample-uat
Scope: Product2/9f1d3c4a-8e5b-4d71-9a2d-f6b719a90101
Result: failed (dependency missing)
Key findings:
- validateLocalData passed (1 completed)
- packDeploy failed: missing referenced child Product2
- packRetry failed with same error
Next step:
- Stage/deploy the three child Product2 DataPacks first (or include them in manifest), then rerun packDeploy and packRetry.
```
