# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `listMe` (`urn:api:access-management`, GET)

No inputs.

**Outputs:**
- `organizationId` (`$.user.organization.id`): Root organization Business Group GUID
- `organizationName` (`$.user.organization.name`): Organization display name

## Call 2 -- `listEnvironments` (`urn:api:access-management`, GET)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Organization ID from Step 1

**Outputs:**
- `environmentId` (`$.data[*].id`, label `$.data[*].name`): Selected environment ID

## Call 3 -- `listApiInstances` (`urn:api:api-manager`, GET)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Organization ID from Step 1
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2

**Outputs:**
- `environmentApiId` (`$.assets[*].apis[*].id`, label `$.assets[*].apis[*].instanceLabel`): The API instance ID to apply the policy to

## Call 4 -- `getExchangePolicyTemplates` (`urn:api:api-portal-xapi`, GET)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Organization ID from Step 1
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2
- `apiInstanceId`: from step output `environmentApiId` -- API instance ID from Step 3 (filters for compatible templates)
- `includeConfiguration`: fixed value `true` -- Include the configuration schema for each template
- `latest`: fixed value `true` -- Return only the latest version of each template

**Outputs:**
- `policyGroupId` (`$[*].groupId`, label `$[*].assetId`): Exchange group ID of the selected policy template
- `policyAssetId` (`$[*].assetId`): Exchange asset ID of the selected policy template
- `policyAssetVersion` (`$[*].version`): Exchange version of the selected policy template (gateway-compatible)
- `policyConfiguration` (`$[*].configuration`): Configuration schema with gateway-compatible property names and defaults

## Call 5 -- `applyApiInstancePolicy` (`urn:api:api-manager`, POST)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Organization ID from Step 1
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2
- `environmentApiId`: from step output `environmentApiId` -- API instance ID from Step 3
- `groupId`: from step output `policyGroupId` -- Policy Exchange group ID from Step 4
- `assetId`: from step output `policyAssetId` -- Policy Exchange asset ID from Step 4
- `assetVersion`: from step output `policyAssetVersion` -- Policy Exchange version from Step 4

**Outputs:**
- `policyId` (`$.id`): The ID of the applied policy instance
