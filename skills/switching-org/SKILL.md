---
name: switching-org
description: Use this skill when users need to switch the active Salesforce org (default org) using the Salesforce CLI. Trigger when users say "switch org", "change default org", "set my org to", "use alias", or specify a username/alias they want to use for subsequent CLI operations.
compatibility: Salesforce CLI (sf) v2+
metadata:
  author: afv-library
  version: "1.0"
---

# switching-org

Switches the active Salesforce org (default org) using the Salesforce CLI (sf). Supports either a username or an alias.

## When to Use This Skill

- User says "switch org", "change default org", or "set my org to"
- User specifies a username or alias they want to use
- User needs to change which org is targeted for subsequent CLI operations

### Examples

- "Switch to this org: user@example.com"
- "Use alias myAlias"
- "Change default org to myDev"

## Steps

1. Read input: `orgIdentifier`, and whether the user wants global scope (default: local)
2. Set the default org:
   - Local (default): `sf config set target-org=<orgIdentifier>`
   - Global (only if user explicitly requests): `sf config set target-org=<orgIdentifier> --global`
   - If this fails, report the error and suggest running `sf org login web` if the org may not be authorized.
3. Verify:
   - `sf config get target-org --json`
   - Output confirmation: `Switched org (<scope>): <value>`
4. If verification fails, report the error and advise running `sf config get target-org`.

## Official Documentation

- Salesforce CLI config (unified) reference (sf):
  https://developer.salesforce.com/docs/atlas.en-us.sfdx_cli_reference.meta/sfdx_cli_reference/cli_reference_config_commands_unified.htm#cli_reference_config_set_unified

## Notes

- Unified CLI uses keys like `target-org` and `target-dev-hub`. Legacy sfdx keys (`defaultusername`, `defaultdevhubusername`) are deprecated in this context.
- The sf CLI does not have `--local` or `--scope` flags for config set. Local scope is the default behavior.
