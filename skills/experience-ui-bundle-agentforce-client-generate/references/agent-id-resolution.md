# Agent ID Resolution

## SOQL Query

```bash
sf data query \
  --query "SELECT BotDefinition.Id, BotDefinition.DeveloperName, BotDefinition.MasterLabel, Status FROM BotVersion WHERE BotDefinition.AgentType = 'AgentforceEmployeeAgent' ORDER BY BotDefinition.CreatedDate ASC" \
  --json
```

- Queries `BotVersion` (not `BotDefinition`) because only `BotVersion` has the `Status` field (`Active` / `Inactive`)
- Filters on `AgentType = 'AgentforceEmployeeAgent'` to return only Employee Agents (excludes Service Agents)

## Response Structure

```json
{
  "status": 0,
  "result": {
    "records": [
      {
        "BotDefinition": {
          "Id": "0Xxxx0000000001CAA",
          "DeveloperName": "Property_Manager_Agent",
          "MasterLabel": "Property Manager Agent"
        },
        "Status": "Active"
      }
    ]
  }
}
```

## Activation Path

Agents cannot be activated programmatically:

> Setup → Agentforce Agents → click agent name → Agent Builder → Activate

## Manual Lookup (without sf CLI)

> Setup → Agentforce Agents → click agent name → copy ID from URL

## Validation

`agentId` must match: `^0Xx[a-zA-Z0-9]{15}$`
