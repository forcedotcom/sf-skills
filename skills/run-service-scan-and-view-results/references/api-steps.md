# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `executeWorkflowFromConfiguration` (`urn:api:agent-scanner-configuration-service`, POST)

**Inputs:**
- `organizationId`: from `getOrganizations` (`urn:api:access-management`), field `$.id`, matching `currentOrganization` -- Your organization's Business Group GUID
- `scannerConfigurationId`: from `getScanConfigurations` (`urn:api:agent-scanner-configuration-service`), field `$.content[*].id` -- The scanner configuration to execute

## Call 2 -- `getScannerRunHistory` (`urn:api:agent-scanner-configuration-service`, GET)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Same organization ID as Step 1
- `scannerId`: from step output `scannerConfigurationId` -- The scanner configuration ID (used as scanner ID)
- `page`: fixed value `0` -- Page number (0-indexed)
- `size`: fixed value `20` -- Number of results per page

**Outputs:**
- `scanRunId` (`$.content[0].id`): The most recent scan run ID
- `scanStatus` (`$.content[0].status`): Current status (RUNNING, COMPLETED, FAILED, ABORTED)
- `startedAt` (`$.content[0].startedAt`): When the scan started
- `endedAt` (`$.content[0].endedAt`): When the scan completed (null if still running)

## Call 3 -- `getStagingAssetsByScanRunId` (`urn:api:agent-scanner-configuration-service`, GET)

**Inputs:**
- `scannerId`: from step output `scannerId` -- The scanner ID
- `scanRunId`: from step output `scanRunId` -- The scan run ID from Step 2
- `page`: fixed value `0` -- Page number (0-indexed)
- `size`: fixed value `0` -- Use 0 to get all results without pagination

**Outputs:**
- `assetId` (`$.content[*].assetId`): The asset ID in Exchange (if published)
- `assetName` (`$.content[*].name`): Name of the discovered service
- `stagingStatus` (`$.content[*].stagingStatus`): Status (NEW, EXISTING, PUBLISHED, FAILED)
- `operationPerformed` (`$.content[*].operationPerformed`): What action was taken (CREATE, UPDATE, DELETE, SKIP)
