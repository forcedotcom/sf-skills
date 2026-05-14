# Validation Transcript: Business Internet Plus Bundle Deployment

This transcript captures the skills used and the planning/execution process to validate deployment readiness for the `business-internet-plus-bundle` sample.

---

## Task Summary

Validate deployment for the `Business Internet Plus` bundle and document the process in a new `examples` folder under `deploying-omnistudio-datapacks`.

---

## Skills Used

### 1) `deploying-omnistudio-datapacks` (Primary)

**Why used:** The task is Vlocity Build deployment validation for DataPacks (`validateLocalData`, deployment preflight, and scope verification).

**Applied from skill guidance:**

- Validate-first workflow (`validateLocalData` before deploy).
- Required context checks (tooling readiness, org auth, deterministic scope).
- Job-file driven validation with explicit manifest targeting.

### 2) `deploying-metadata` (Supporting)

**Why used:** Deployment preflight practices overlap with org readiness checks.

**Applied from skill guidance:**

- Confirm CLI and org context before execution.
- Capture result and safe next action in a completion block.

### 3) `modeling-omnistudio-epc-catalog` (Supporting)

**Why used:** The target bundle payload was generated as an EPC Product2 offer bundle sample, so EPC-specific structure and guardrails were validated before deployment checks.

**Applied from skill guidance:**

- Confirm offer markers (`SpecificationType=Offer`, `SpecificationSubType=Bundle`).
- Confirm root PCI + child PCI composition.
- Confirm companion bundle artifacts and GlobalKey consistency.

---

## Planning Process (Executed)

1. Locate the `business-internet-plus-bundle` payload and confirm all companion JSON artifacts exist.
2. Run preflight checks for deployment tooling:
   - `vlocity` CLI availability.
   - Salesforce org auth context for target alias.
3. Run file-level integrity checks:
   - JSON parse for all bundle artifacts.
   - Product2 + PCI + attribute consistency checks.
4. Create a deterministic Vlocity Build job file in this example folder for reproducible validation.
5. Execute `validateLocalData` against the bundle scope and record outcome.
6. Summarize result, findings, and safe next actions.

---

## Execution Log

### A) Bundle discovery

- Located bundle payload at:
  - `skills/modeling-omnistudio-epc-catalog/examples/business-internet-plus-bundle`
- Confirmed 11 companion JSON files exist (`DataPack`, `AttributeAssignments`, `ProductChildItems`, pricing files, orchestration/decomposition files, overrides, and parent keys).

### B) Tooling and org preflight

- `vlocity` global binary check: **not installed globally** (`command not found`).
- `npx vlocity` check: **available** (`Vlocity Build v1.17.21`).
- `sf org list --json`: org context available; target alias `sample-uat` is connected.

### C) File-level integrity validation

Local JSON validation checks passed:

- Missing files: `0`
- JSON parse errors: `0`
- Product identity checks: name and product code match expected values.
- Offer checks: `SpecificationType=Offer` and `SpecificationSubType=Bundle`.
- Composition checks: `1` root PCI and `3` child PCI records.
- Attribute checks: `3` attribute assignment records.
- Key integrity checks: PCI parent references match Product2 GlobalKey.

### D) Vlocity validateLocalData execution

Job file used:

- `skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle/deploy-business-internet-plus-bundle.yaml`

Command:

```bash
npx --yes vlocity -sfdx.username sample-uat -job "skills/deploying-omnistudio-datapacks/examples/business-internet-plus-bundle/deploy-business-internet-plus-bundle.yaml" validateLocalData
```

Result:

- `ValidateLocalData success: 0 Completed`

Interpretation:

- Validation command executed successfully.
- `0 Completed` indicates no DataPack records were processed for this scope layout.
- This is consistent with the sample payload being stored as a documentation/example artifact rather than a standard `vlocity/` expansion deployment path.

---

## Validation Outcome

```text
DataPack goal: validate deployment readiness
Source org: N/A
Target org: sample-uat
Scope: deploy-business-internet-plus-bundle.yaml + Product2/9f1d3c4a-8e5b-4d71-9a2d-f6b719a90101
Result: partial
Key findings:
- Bundle JSON payload is internally consistent and structurally valid.
- Vlocity validateLocalData ran successfully but processed 0 DataPacks in current example-folder scope.
Next step:
- Stage the bundle into a standard Vlocity expansion path (for example under `vlocity/Product2/<global-key>/`) and rerun `validateLocalData`, then `packDeploy` and `packGetDiffs`.
```
