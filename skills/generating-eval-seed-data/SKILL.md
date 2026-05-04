---
name: generating-eval-seed-data
description: "Generate minimal seed-data stubs for Salesforce metadata evaluation datasets in the afv-library. Use this skill to create seed-data directories containing lightweight dependency declarations (custom fields, objects, Apex class stubs) that a dataset's gold file references. TRIGGER when: user says generate seed data, create seed-data stubs, populate seed-data, dataset dependencies, gold file dependencies, add supporting metadata for eval, or wants to set up prerequisite objects/fields for a test dataset. Also use when the user mentions seed-data, eval fixtures, stub generation, or asks to fill in the seed-data directory for any skill's tests/evals/ dataset. SKIP when: user wants to generate the gold file itself (use the domain-specific generating skill), wants to run evals (use eval runner tooling), or wants to create a new skill from scratch (use creating-sf-skill)."
license: LICENSE.txt has complete terms
metadata:
  version: "1.0"
  stage: Draft
  related-skills: "creating-sf-skill, generating-custom-field, generating-custom-object, generating-apex"
allowed-tools: Bash(sf project generate, sf project deploy start, cp, rm, mkdir, find, ls) Read Write
---

# Generating Eval Seed Data

Generate seed-data **stubs** — minimal supporting metadata dependencies — for evaluation datasets in the afv-library. Stubs declare the bare-minimum custom objects, fields, relationships, and Apex classes that a dataset's gold file references, just enough so the gold file can be validated in isolation.

## Scope

- **In scope**: Analyzing gold files to identify custom dependencies, generating minimal stub XML/Apex for those dependencies, validating stubs deploy successfully via dry-run, and populating the `seed-data/` directory.
- **Out of scope**: Generating the gold file itself (delegate to the domain-specific skill), creating new eval datasets or prompt.md files (delegate to `creating-sf-skill`), deploying metadata to production orgs.

---

## Required Inputs

Gather before proceeding:

- **Dataset path**: Path to a single dataset (`skills/<name>/tests/evals/<dataset>/`) or a domain path containing multiple datasets. Always ask if not provided.
- **Target org alias**: The Salesforce org alias for dry-run validation (e.g., `myDevOrg`). Ask if not provided.

Defaults unless specified:
- API version: `62.0`
- Stub style: absolute minimum elements per metadata type (see `references/stub-rules.md`)

---

## Workflow

All steps are sequential. Do not skip or reorder.

### Phase 1 — Identify and Read

1. **Identify the dataset(s)**
   - If the path contains `tests/evals/<datasetName>` (or has `prompt.md` / `gold/` directly inside), treat as a single dataset.
   - Otherwise, look for `tests/evals/` subdirectory. If it exists, list all subdirectories — each is a dataset. Process them all.
   - If neither pattern matches, ask the user to clarify.

2. **Read the gold file(s)**
   - Look for gold files in `{dataset_path}/gold/`. These are Salesforce metadata XML or Apex files.
   - If gold files exist, proceed to step 3.
   - If gold files do NOT exist, ask: "This dataset has no gold file. Would you like me to generate one from `prompt.md`?" If yes, read `prompt.md` and generate a plausible gold file, then proceed.

3. **Read stub generation rules** — load `references/stub-rules.md` before analyzing.

### Phase 2 — Analyze and Generate

4. **Analyze dependencies**
   - Read all gold files and identify every custom dependency. Look for:
     - **Custom fields** (`__c`): referenced in formulas, conditions, assignments, or relationship traversals (`__r.Name` implies a lookup `__c`)
     - **Custom objects** (`__c`): any custom object the gold metadata lives on or references via lookups
     - **Apex classes**: parent classes, interfaces, or utility classes referenced by gold code
   - For each dependency, determine: metadata type, correct API name, minimum required attributes.
   - Standard Salesforce objects (Account, Contact, Case, etc.) and their standard fields do NOT need stubs.

5. **Generate stubs**
   - Create the `seed-data/` directory structure following the rules in `references/stub-rules.md`.
   - Include ONLY the minimum elements per metadata type — no optional attributes.
   - For picklists: only include values explicitly referenced in the gold file.

6. **Compare against example** — verify output matches patterns in `examples/stub-examples.md`.

### Phase 3 — Validate

7. **Validate with dry-run deployment**
   - Create a temporary SFDX project:
     ```bash
     cd /tmp && sf project generate --name seed-data-validation-$(date +%s) --template empty
     ```
   - Read the temp project's `sfdx-project.json` to resolve the deploy path — do not hardcode `force-app/main/default/`. Extract `packageDirectories[].path` (use the entry with `"default": true`; if none, use the first entry).
   - Copy seed-data and gold files into the resolved deploy path:
     ```bash
     cp -r {dataset_path}/seed-data/* {temp_project}/{resolved_path}/
     cp -r {dataset_path}/gold/* {temp_project}/{resolved_path}/
     ```
   - Run dry-run:
     ```bash
     sf project deploy start --dry-run -d "{resolved_path}" --target-org {target_org} --test-level NoTestRun --wait 10 --json
     ```

8. **Auto-fix on failure**
   - Parse JSON error output and fix issues (missing fields, invalid types, missing relationships).
   - Re-run dry-run after each fix. Max 3 retries.
   - If still failing after 3 retries, report remaining errors and ask for guidance.

9. **Copy validated stubs back**
   - Replace `{dataset_path}/seed-data/` with the validated versions.
   - Only copy back stub files you generated — do NOT copy gold file content into seed-data.

10. **Clean up and report**
    - Delete the temporary SFDX project.
    - Report: files generated, validation status, any fixes applied.
    - For multiple datasets, print a summary table:

      | # | Dataset | Stubs Generated | Validation | Notes |
      |---|---------|----------------|------------|-------|
      | 1 | … | … | … | … |

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Stubs include ONLY minimum required elements | Optional attributes add noise and can cause unexpected deployment errors |
| Never invent picklist values beyond what gold references | Extra values create false dependencies and mislead evaluators |
| Standard objects/fields never get stubs | They exist in every org; stubs would be redundant and can conflict |
| Always validate via dry-run before finalizing | Catches missing dependencies and malformed XML before the contributor sees them |
| API version defaults to 62.0 | Matches current afv-library convention; override only if gold file specifies otherwise |
| Copy back only stub files, not gold files | Mixing gold content into seed-data corrupts the dataset structure |
| Never hardcode `force-app/main/default/` — always read `sfdx-project.json` | Customers customize the package directory path; hardcoding breaks non-default projects |
| Reference cross-skills by name, never by filesystem path | Skill catalog layout varies across AFV installations; hardcoded paths break portability |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Relationship traversal (`__r.Name`) implies a lookup field | Generate a Lookup stub for the corresponding `__c` field |
| Gold file references a field on a standard object | Only generate the custom field stub, not the standard object definition |
| Multiple gold files reference the same custom object | Generate the object stub once; place field stubs under the same object directory |
| Picklist referenced in formula via `ISPICKVAL` | Extract only the specific value string from the formula; do not add other values |
| Gold file has no custom dependencies | Skip stub generation; report "no seed-data needed" |
| Dry-run fails with `DUPLICATE_DEVELOPER_NAME` | A stub conflicts with an existing org object — rename or skip |

---

## Output Expectations

Deliverables:
- Stub metadata files: `{dataset_path}/seed-data/objects/{ObjectName}/fields/{FieldName}.field-meta.xml`
- Stub object definitions: `{dataset_path}/seed-data/objects/{ObjectName}/{ObjectName}.object-meta.xml`
- Stub Apex classes: `{dataset_path}/seed-data/classes/{ClassName}.cls` + `.cls-meta.xml`
- Console report: list of generated files, validation status, fixes applied

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Generate the gold file for a dataset | Domain-specific skill (`generating-validation-rule`, `generating-apex`, etc.) |
| Create a new skill with eval datasets | `creating-sf-skill` |
| Generate a complete custom field (not a stub) | `generating-custom-field` |
| Generate a complete custom object (not a stub) | `generating-custom-object` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stub-rules.md` | Phase 2, step 3 — before generating any stubs |
| `examples/stub-examples.md` | Phase 2, step 6 — to verify generated output matches expected patterns |
