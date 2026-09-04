---
name: life-sciences-territory-configure
description: "Use this skill to create and activate a Territory Type, Territory Model, and Territories for Life Sciences Cloud. Trigger when the user says 'set up territories', 'create territory model', 'configure territory hierarchy for Life Sciences', 'territory setup for LSC', or 'create territories for Life Sciences Cloud'. Creates a Geographical territory type, an LSC Territory Model, and a 3-level territory hierarchy (Region, District, Territory). Confirms names with the user, shows a preview, then deploys and activates the model. DO NOT TRIGGER when: user wants to validate prerequisites, assign users to territories, create territory assignment rules, or run the full end-to-end Life Sciences Cloud setup / orchestration (that is the `life-sciences-fieldsalesrep-coordinate` orchestrator's job — this skill runs only as a standalone territory setup)."
metadata:
  version: "1.0"
  minApiVersion: "65.0"
  domains: ["Life Sciences"]
  relatedSkills:
    - life-sciences-fieldsalesrep-coordinate
    - life-sciences-prerequisites-validate
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Life Sciences Territory Setup

Creates and activates a Territory Type, Territory Model, and a 3-level Territory hierarchy for Life Sciences Cloud using the `sf` CLI.

## Scope

- **In scope**: Creating territory type, territory model, and territories; activating the territory model
- **Out of scope**: Assigning users to territories, creating territory assignment rules, validating prerequisites

### Off-topic requests

If the user asks for something unrelated to this skill (either at the start or mid-execution), do not attempt it. Tell the user you did not understand the request, then show what you *can* help with: setting up Life Sciences Cloud territories (this skill), and — if relevant — point them to `life-sciences-prerequisites-validate` for prerequisite checks or `life-sciences-fieldsalesrep-coordinate` for the full end-to-end setup. Then stop and wait.

---

## Required Inputs

Gather before proceeding:

- **Target org**: The org alias or username to deploy to (from `sf config get target-org` or user-specified)

---

## Workflow

### Phase 1 — Present Default Names and Get Confirmation

1. **Show the user the default names** that will be used for the territory components. Read `references/territory-metadata.md` for the exact XML templates and default names.

Present the names in a table:

```markdown
| Component | Default Name |
|-----------|-------------|
| Territory Type | Geographical |
| Territory Model | LSC Territory Model |
| Territory (Level 1 - Region) | RD - West 20D |
| Territory (Level 2 - District) | DM - San Francisco 20D02 |
| Territory (Level 3 - Territory) | TM - SPC - San Francisco North 20D02T11 |
```

2. **Ask the user** if they are fine with these names or want to change any of them. Ask for each component individually:
   - "Are you fine with the Territory Type name **'Geographical'** or would you like to change it?"
   - "Are you fine with the Territory Model name **'LSC Territory Model'** or would you like to change it?"
   - "Are you fine with the Region territory name **'RD - West 20D'** or would you like to change it?"
   - "Are you fine with the District territory name **'DM - San Francisco 20D02'** or would you like to change it?"
   - "Are you fine with the Territory name **'TM - SPC - San Francisco North 20D02T11'** or would you like to change it?"

3. **If the user wants to change a name**, ask them for the new name they'd like to use. Record the updated name.

### Phase 2 — Preview and Confirm

4. **Display a complete preview** of what will be created, showing the final XML for each component with the confirmed names. Use the templates from `references/territory-metadata.md` and substitute any user-provided names.

Show the preview in this format:

```text
=== Territory Type ===
Name: <confirmed name>
Priority: 1

=== Territory Model ===
Name: <confirmed model name>

=== Territory Hierarchy ===
Level 1 (Region): <confirmed region name>
  └── Level 2 (District): <confirmed district name>
        └── Level 3 (Territory): <confirmed territory name>

Access Levels (all territories):
- Account: Read
- Contact: Edit
- Case: None
- Opportunity: None
```

5. **Ask for final confirmation**: "Ready to create and deploy these territory components? (yes/no)"

If user says no, go back to Phase 1.

### Phase 3 — Create and Deploy

6. **Create a temporary SFDX project structure** for deployment. Read `references/territory-metadata.md` for the exact file structure and XML content.

The directory structure must be:

```text
territory-deploy/
├── sfdx-project.json
└── force-app/
    └── main/
        └── default/
            └── territory2Models/
                ├── <ModelApiName>.territory2Model-meta.xml
                └── <ModelApiName>/
                    ├── territory2Types/
                    │   └── <TypeApiName>.territory2Type-meta.xml
                    └── territories/
                        ├── <Level1ApiName>.territory2-meta.xml
                        ├── <Level2ApiName>.territory2-meta.xml
                        └── <Level3ApiName>.territory2-meta.xml
```

7. **Generate API names** from user-confirmed display names:
   - Remove special characters, spaces, and hyphens
   - Use PascalCase for the API name
   - Territory type API name is derived from the type display name
   - Territory model API name is derived from the model display name (remove spaces)
   - Territory API names are derived from territory display names (remove spaces, hyphens, special chars)

8. **Write the metadata files** using the templates from `references/territory-metadata.md` with confirmed names.

9. **Deploy the metadata** using:
   ```bash
   sf project deploy start --source-dir territory-deploy/force-app --target-org <org>
   ```

10. **Check deployment status** — if it fails, show the error and suggest remediation.

    > **STOP-GATE (component count).** The single deploy package must land the **complete** hierarchy: 1 Territory2Type + 1 Territory2Model + 3 Territory2 records (one Region, one District, one Territory). Confirm the deploy result reports **0 component failures** AND verify the territories exist before activating:
    > ```bash
    > sf data query --query "SELECT COUNT(Id) c FROM Territory2 WHERE Territory2Model.DeveloperName = '<ModelApiName>'" --target-org <org> --json
    > ```
    > The count MUST be 3. A parent-reference failure (e.g. the District deploying before its Region) can land a partial hierarchy — a Level-3 territory with no path to its Region silently breaks downstream user/visit territory assignment. Do NOT activate the model (Phase 4) until all 3 territories are present with 0 deploy failures.

### Phase 4 — Activate Territory Model

11. **Report that the model deployed in Planning state** and ask the user if they want to activate it. Include this warning:

    > **Note:** Once a Territory Model is activated, it can be deactivated but **cannot be deleted**. Do you want to proceed with activation?

12. **If the user confirms activation**, activate the model by querying its record ID then updating its State to `'Activating'` (not `'Active'` — the platform transitions asynchronously from Activating → Active):

    ```bash
    # Query the model ID and current state
    sf data query --query "SELECT Id, State FROM Territory2Model WHERE DeveloperName = '<ModelApiName>' LIMIT 1" --target-org <org> --json
    ```

    If the model is in `Planning` state, update it:

    ```bash
    sf data update record --sobject Territory2Model --record-id <ModelId> --values "State='Activating'" --target-org <org>
    ```

    See `references/territory-metadata.md` for the full activation logic including error handling.

13. **Verify activation** — the platform transitions asynchronously from `Activating` → `Active`. Query to confirm:
    ```bash
    sf data query --query "SELECT Id, DeveloperName, State FROM Territory2Model WHERE DeveloperName='<ModelApiName>'" --target-org <org>
    ```
    If still `Activating`, wait a moment and query again until it reaches `Active`.

14. **If the user declines activation**, report that the model is in Planning state and can be activated later from Setup.

15. **Report success** — confirm to the user that all components are created, and report the model's current state (`Planning`, `Activating`, or `Active`).

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Create exactly one territory per level — one Level-1 Region, one Level-2 District, one Level-3 Territory (3 territories total) | Skill produces a single representative hierarchy branch, not a fully populated multi-child tree |
| Always confirm names before creating | User may want to customize territory names for their org |
| Show preview before deploying | User should see exactly what will be created |
| Deploy all components together | Territory hierarchy has dependencies (parent references) |
| Warn user before activation that model cannot be deleted once active | Irreversible action — user must explicitly consent |
| Set State to `'Activating'` (not `'Active'`) when updating the record | The platform handles the async transition from Activating → Active |
| Target the update by `--record-id <ModelId>` or `--where "DeveloperName='<ModelApiName>'"` | Both forms work for `sf data update record`; use whichever is convenient |
| Clean up temp directory after deploy | Don't leave deployment artifacts behind |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Territory model already exists with same name | Check first with a query; ask user if they want a different name |
| Territory type already exists | Check first; reuse existing type if it matches |
| Deploy fails due to parent territory not found | Ensure all territories are in the same deployment package |
| Setting State to `'Active'` directly fails with `INVALID_STATUS` | Always set State to `'Activating'` — the platform transitions to Active asynchronously |
| Model state shows `Activating` after update | This is normal — activation is async. Wait and re-query until `Active` |
| API name conflicts | Ensure generated API names don't conflict with existing metadata |

---

## Output Expectations

Deliverables:
- Created Territory Type with confirmed name
- Created Territory Model with confirmed name
- Created 3-level territory hierarchy with confirmed names
- Territory Model activated (or manual activation steps if programmatic activation fails)
- Confirmation message showing all created components and their status

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/territory-metadata.md` | During all phases — contains XML templates, file structure, and default values for territory components |
