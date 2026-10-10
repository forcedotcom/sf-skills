# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `uploadAsset` (`urn:api:exchange-experience`, POST)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Your organization's Business Group GUID
- `groupId`: user-provided (example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`) -- The group ID for the asset (typically matches your organization ID)
- `assetId`: user-provided (example: `inventory-api`) -- A unique identifier for the asset in kebab-case
- `version`: user-provided (example: `1.0.0`) -- Semantic version for the asset

**Outputs:**
- `groupId` (`$.groupId`): The group ID of the published asset
- `assetId` (`$.assetId`): The asset ID of the published asset
- `assetVersion` (`$.version`): The version of the published asset

## Call 2 -- `listEnvironments` (`urn:api:access-management`, GET)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Organization ID from Prerequisites

**Outputs:**
- `environmentId` (`$.data[*].id`, label `$.data[*].name`): Selected environment ID (e.g., Production, Sandbox)

## Call 3 -- `getGatewayTargets` (`urn:api:api-portal-xapi`, GET)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Organization ID
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2

**Outputs:**
- `targetId` (`$.rows[*].id`, label `$.rows[*].name`): Selected gateway target ID
- `targetName` (`$.rows[*].name`): Name of the selected gateway target
- `gatewayVersion` (fixed value `1.0.0`): Gateway version to use for deployment. The targets response may return "-" instead of a real version; use "1.0.0" as the default.

## Call 4 -- `createApiInstance` (`urn:api:api-manager`, POST)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Your organization's Business Group GUID
- `environmentId`: from step output `environmentId` -- Target environment ID from Step 2
- `groupId`: from step output `groupId` -- Exchange asset group ID from Step 1
- `assetId`: from step output `assetId` -- Exchange asset ID from Step 1
- `assetVersion`: from step output `assetVersion` -- Exchange asset version from Step 1
- `instanceLabel`: user-provided (example: `cars-api-v1`) -- A human-readable label for this API instance (e.g., "cars-api-v1")
- `technology`: fixed value `flexGateway` -- Gateway technology — this skill targets Omni Gateway deployments
- `endpoint.isCloudHub`: fixed value `None` -- Must be null for flexGateway technology (not false — false causes a validation error)
- `endpoint.proxyUri`: user-provided (example: `http://0.0.0.0:8081/`) -- The proxy listener URI. Ask the user which port the Omni Gateway should listen on, then use http://0.0.0.0:<port>/
- `endpoint.uri`: user-provided, optional (example: `https://backend.example.com/api/v1`) -- The upstream backend URL for the API. Ask the user if they want to provide it now or configure it later.

**Outputs:**
- `environmentApiId` (`$.id`): The API instance ID in API Manager

## Call 5 -- `createProxyDeployment` (`urn:api:proxies-xapi`, POST)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Organization ID
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2 (used in both the URL path and the request body for HY deployment type)
- `environmentApiId`: from step output `environmentApiId` -- API instance ID from Step 4
- `type`: fixed value `HY` -- Deployment type for self-managed Omni Gateway (HY = Hybrid)
- `targetId`: from step output `targetId` -- Omni Gateway target ID from Step 3
- `targetName`: from step output `targetName` -- Omni Gateway target name from Step 3
- `gatewayVersion`: fixed value `1.0.0` -- Gateway version for deployment. Use "1.0.0" as the default.
- `overwrite`: fixed value `False` -- Whether to overwrite an existing deployment

**Outputs:**
- `deploymentId` (`$.id`): The ID of the proxy deployment

## Call 6 -- `getExchangePolicyTemplates` (`urn:api:api-portal-xapi`, GET)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Organization ID
- `apiInstanceId`: from step output `environmentApiId` -- API instance ID from Step 4 (filters for compatible templates)
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2
- `latest`: fixed value `true` -- Return only the latest version of each template
- `includeConfiguration`: fixed value `true` -- Include the configuration schema for each template

**Outputs:**
- `policyGroupId` (`$[*].groupId`, label `$[*].assetId`): Exchange group ID of the selected policy template
- `policyAssetId` (`$[*].assetId`): Exchange asset ID of the selected policy template
- `policyAssetVersion` (`$[*].version`): Exchange version of the selected policy template (gateway-compatible)
- `policyConfiguration` (`$[*].configuration`): Configuration schema with gateway-compatible property names and defaults

## Call 7 -- `applyApiInstancePolicy` (`urn:api:api-manager`, POST)

**Inputs:**
- `organizationId`: from `listMe` (`urn:api:access-management`), field `$.user.organization.id` -- Organization ID
- `environmentId`: from step output `environmentId` -- Environment ID from Step 2
- `environmentApiId`: from step output `environmentApiId` -- API instance ID from Step 4 (or provided manually)
- `groupId`: from step output `policyGroupId` -- Policy Exchange group ID from Step 6
- `assetId`: from step output `policyAssetId` -- Policy Exchange asset ID from Step 6
- `assetVersion`: from step output `policyAssetVersion` -- Policy Exchange version from Step 6

**Outputs:**
- `policyId` (`$.id`): The ID of the applied policy instance
