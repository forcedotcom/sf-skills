# harmonizing-datacloud

Schema harmonization and unification workflows for Salesforce Data Cloud.

## Use this skill for

- DMOs (Data Model Objects)
- Field mappings
- Relationships
- Identity resolution
- Unified profiles
- Data graphs
- Universal ID lookup

## Example requests

```text
"Map this DLO to ssot__Individual__dlm"
"Help me create an identity resolution ruleset"
"Why are unified profiles not appearing?"
"Show me the DMO fields before I create mappings"
```

## Common commands

```bash
sf data360 dmo list --all -o myorg 2>/dev/null
sf data360 query describe -o myorg --table ssot__Individual__dlm 2>/dev/null
sf data360 dmo mapping-list -o myorg --source Contact_Home__dll --target ssot__Individual__dlm 2>/dev/null
sf data360 identity-resolution list -o myorg 2>/dev/null
```
