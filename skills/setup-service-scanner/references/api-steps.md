# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `getTargetSystems` (`urn:api:agent-scanner-configuration-service`, GET)

**Inputs:**
- `organizationId`: from `getOrganizations` (`urn:api:access-management`), field `$.id`, matching `currentOrganization` -- Your organization's Business Group GUID

**Outputs:**
- `targetSystemId` (`$[*].id`, label `$[*].name`): The target system ID to use when creating a connection
- `targetSystemType` (`$[*].type`): The target system type (e.g., bedrock, mscopilot, vertex)

## Call 2 -- `testConnection` (`urn:api:agent-scanner-configuration-service`, POST)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Same organization ID as Step 1
- `targetSystemType`: from step output `targetSystemType` -- Target system type from Step 1 (for example, bedrock, mscopilot, vertex)
- `requestBody`: user-provided (example: `{
  "authScheme": "accessKey",
  "authParameters": "{\"accessKeyId\":\"...\",\"secretAccessKey\":\"...\",\"region\":\"us-east-1\"}"
}
`) -- Connection test parameters including:
- authScheme: Authentication scheme (e.g., "accessKey", "oauth2")
- authParameters: JSON with credentials (varies by platform)


## Call 3 -- `createScanConfigurations` (`urn:api:agent-scanner-configuration-service`, POST)

**Inputs:**
- `organizationId`: from step output `organizationId` -- Same organization ID as previous steps
- `requestBody`: user-provided (example: `{
  "name": "My Bedrock Scanner",
  "description": "Scans AWS Bedrock for services such as AI agents",
  "schedule": "{\"frequency\":\"daily\",\"time\":\"02:00\"}",
  "runPolicy": "{}",
  "connection": {
    "targetSystemId": "target-system-uuid-from-step-1",
    "authScheme": "accessKey",
    "authParameters": "{\"accessKeyId\":\"...\",\"secretAccessKey\":\"...\",\"region\":\"us-east-1\"}"
  },
  "notificationEnabled": false
}
`) -- Scanner configuration including:
- name: Display name for the scanner
- schedule: JSON schedule configuration
- runPolicy: JSON run policy (can be empty object)
- connection: Object with connection details
- notificationEnabled: Whether to send email notifications


**Outputs:**
- `scannerConfigurationId` (`$.id`): The UUID of the created scanner configuration
- `scannerState` (`$.state`): The current state of the scanner (e.g., SCHEDULED, STOPPED)
