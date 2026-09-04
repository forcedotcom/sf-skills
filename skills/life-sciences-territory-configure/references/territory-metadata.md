# Territory Metadata Templates

## Default Names

| Component | Display Name | Default API Name |
|-----------|-------------|-----------------|
| Territory Type | Geographical | Geographical |
| Territory Model | LSC Territory Model | LSCTerritoryModel |
| Territory (Level 1 - Region) | RD - West 20D | RDWest20D |
| Territory (Level 2 - District) | DM - San Francisco 20D02 | DMSanFrancisco20D02 |
| Territory (Level 3 - Territory) | TM - SPC - San Francisco North 20D02T11 | TMSPCSanFranciscoNorth20D02T11 |

---

## File Structure

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

---

## sfdx-project.json

```json
{
  "packageDirectories": [
    {
      "path": "force-app",
      "default": true
    }
  ],
  "namespace": "",
  "sfdcLoginUrl": "https://login.salesforce.com",
  "sourceApiVersion": "65.0"
}
```

---

## Territory Type XML Template

File: `force-app/main/default/territory2Models/<ModelApiName>/territory2Types/<TypeApiName>.territory2Type-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Territory2Type xmlns="http://soap.sforce.com/2006/04/metadata">
    <name>Geographical</name>
    <priority>1</priority>
</Territory2Type>
```

### Fields

| Field | Default Value | Description |
|-------|--------------|-------------|
| `<name>` | Geographical | Display name of the territory type |
| `<priority>` | 1 | Priority ranking (1 = highest) |

---

## Territory Model XML Template

File: `force-app/main/default/territory2Models/<ModelApiName>.territory2Model-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Territory2Model xmlns="http://soap.sforce.com/2006/04/metadata">
    <name>LSC Territory Model</name>
</Territory2Model>
```

### Fields

| Field | Default Value | Description |
|-------|--------------|-------------|
| `<name>` | LSC Territory Model | Display name of the territory model |

---

## Territory XML Templates

All territories go under: `force-app/main/default/territory2Models/<ModelApiName>/territories/`

### Level 1 — Region (Top-level territory)

File: `<Level1ApiName>.territory2-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Territory2 xmlns="http://soap.sforce.com/2006/04/metadata">
    <accountAccessLevel>Read</accountAccessLevel>
    <caseAccessLevel>None</caseAccessLevel>
    <contactAccessLevel>Edit</contactAccessLevel>
    <name>RD - West 20D</name>
    <opportunityAccessLevel>None</opportunityAccessLevel>
    <territory2Type>Geographical</territory2Type>
</Territory2>
```

### Level 2 — District (Child of Region)

File: `<Level2ApiName>.territory2-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Territory2 xmlns="http://soap.sforce.com/2006/04/metadata">
    <accountAccessLevel>Read</accountAccessLevel>
    <caseAccessLevel>None</caseAccessLevel>
    <contactAccessLevel>Edit</contactAccessLevel>
    <name>DM - San Francisco 20D02</name>
    <opportunityAccessLevel>None</opportunityAccessLevel>
    <parentTerritory>RDWest20D</parentTerritory>
    <territory2Type>Geographical</territory2Type>
</Territory2>
```

### Level 3 — Territory (Child of District)

File: `<Level3ApiName>.territory2-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Territory2 xmlns="http://soap.sforce.com/2006/04/metadata">
    <accountAccessLevel>Read</accountAccessLevel>
    <caseAccessLevel>None</caseAccessLevel>
    <contactAccessLevel>Edit</contactAccessLevel>
    <name>TM - SPC - San Francisco North 20D02T11</name>
    <opportunityAccessLevel>None</opportunityAccessLevel>
    <parentTerritory>DMSanFrancisco20D02</parentTerritory>
    <territory2Type>Geographical</territory2Type>
</Territory2>
```

### Territory Access Levels

| Field | Value | Description |
|-------|-------|-------------|
| `<accountAccessLevel>` | Read | Read access to accounts in territory |
| `<caseAccessLevel>` | None | No case access |
| `<contactAccessLevel>` | Edit | Edit access to contacts in territory |
| `<opportunityAccessLevel>` | None | No opportunity access |

### Territory Hierarchy Relationships

| Territory | Parent | Level |
|-----------|--------|-------|
| RDWest20D | (none - top level) | 1 - Region |
| DMSanFrancisco20D02 | RDWest20D | 2 - District |
| TMSPCSanFranciscoNorth20D02T11 | DMSanFrancisco20D02 | 3 - Territory |

---

## API Name Generation Rules

When the user provides a custom display name, derive the API name as follows:

1. Remove all special characters (hyphens, periods, commas, parentheses)
2. Remove all spaces
3. Ensure it starts with a letter
4. Use only alphanumeric characters
5. Keep it concise but recognizable

Examples:
- "RD - West 20D" → `RDWest20D`
- "DM - San Francisco 20D02" → `DMSanFrancisco20D02`
- "LSC Territory Model" → `LSCTerritoryModel`
- "Geographical" → `Geographical`

---

## Deployment Commands

### Deploy all territory metadata

```bash
sf project deploy start --source-dir territory-deploy/force-app --target-org <org>
```

### Activate the territory model

The activation uses `sf data update record` to set State to `'Activating'` (NOT `'Active'`). The platform handles the async transition from Activating → Active.

> **Warning to present to user before activation:** Once a Territory Model is activated, it can be deactivated but **cannot be deleted**.

**Step 1 — Query the model ID and current state:**

```bash
sf data query \
    --query "SELECT Id, State FROM Territory2Model WHERE DeveloperName = '<ModelApiName>' LIMIT 1" \
    --target-org <org> \
    --json
```

Parse the result to extract the record `Id` and `State`. If the model is not found, report an error.

**Step 2 — If State is `Planning`, update to `Activating`:**

By record ID:

```bash
sf data update record \
    --sobject Territory2Model \
    --record-id <ModelId> \
    --values "State='Activating'" \
    --target-org <org>
```

Or target by DeveloperName with `--where` (verified equivalent — no record ID lookup needed):

```bash
sf data update record \
    --sobject Territory2Model \
    --where "DeveloperName='<ModelApiName>'" \
    --values "State=Activating" \
    --target-org <org>
```

**Important:** Use `State=Activating` — setting to `'Active'` directly will fail with `INVALID_STATUS: A territory model cannot change from the Planning state to the Active state`. The platform advances Activating → Active on its own once the async job completes.

**Step 3 — If the update succeeds**, report activation initiated. The model will transition asynchronously to `Active`.

**Step 4 — If the model is NOT in `Planning` state** (e.g. already `Active` or `Activating`), report the current state and take no action.

### Verify activation

```bash
sf data query --query "SELECT Id, DeveloperName, State FROM Territory2Model WHERE DeveloperName='<ModelApiName>'" --target-org <org>
```

Report the returned `State`. If it is `Activating`, wait and query again until it reaches `Active`.

---

## Pre-deployment Checks

Before deploying, verify:

1. No existing territory model with the same DeveloperName:
   ```bash
   sf data query --query "SELECT Id, DeveloperName, State FROM Territory2Model WHERE DeveloperName='<ModelApiName>'" --target-org <org>
   ```

2. No existing territory type with the same DeveloperName:
   ```bash
   sf data query --query "SELECT Id, DeveloperName FROM Territory2Type WHERE DeveloperName='<TypeApiName>'" --target-org <org>
   ```

If either exists, inform the user and ask if they want to use a different name or reuse the existing component.
