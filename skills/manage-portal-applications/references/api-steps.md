# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `getApplications` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: user-provided -- Anypoint organization ID hosting the portal
- `portalId`: user-provided -- Portal ID the user belongs to

**Outputs:**
- `applications` (`$.applications[*]`, label `$.applications[*].name`): Your existing applications in this portal
- `applicationId` (`$.applications[*].id`): ID used by the per-application operations

## Call 2 -- `checkExistenceApplicationName` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `nameCheckRequest`: user-provided (example: `{'name': 'orders-prod-client'}`) -- The candidate application name to check for uniqueness

**Outputs:**
- `nameAvailable` (`$.available`): Whether the proposed name is free to use

## Call 3 -- `createApplication` (`urn:api:api-experience-hub-consumer`, POST)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `groupId`: user-provided -- groupId of the asset to bind the application to (if required by portal policy)
- `assetId`: user-provided -- assetId of the asset to bind the application to
- `minorVersion`: user-provided -- minor version of the asset
- `applicationRequest`: user-provided (example: `{'name': 'orders-prod-client', 'description': 'Production client for the Orders API', 'redirectUris': ['https://app.example.com/callback']}`) -- Application metadata and OAuth/OIDC settings

**Outputs:**
- `createdApplicationId` (`$.id`): The new application ID
- `clientId` (`$.clientId`): OAuth client ID issued to the application
- `clientSecret` (`$.clientSecret`): OAuth client secret (shown only at creation — store it securely)

## Call 4 -- `updateApplication` (`urn:api:api-experience-hub-consumer`, PUT)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- ID of the application to update
- `applicationUpdate`: user-provided (example: `{'name': 'orders-prod-client', 'description': 'Production client for the Orders API (v2)', 'redirectUris': ['https://app.example.com/v2/callback']}`) -- Updated application metadata

**Outputs:**
- `updatedApplicationId` (`$.id`): Confirmed ID of the updated application

## Call 5 -- `resetClientSecretForApplication` (`urn:api:api-experience-hub-consumer`, POST)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- ID of the application to rotate

**Outputs:**
- `newClientSecret` (`$.clientSecret`): Newly generated client secret (store it securely — only shown once)

## Call 6 -- `getApplicationDetailById` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- ID of the application to inspect

**Outputs:**
- `applicationDetails` (`$`): Current application metadata (clientId present; secret never returned)

## Call 7 -- `deleteApplication` (`urn:api:api-experience-hub-consumer`, DELETE)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- ID of the application to delete

**Outputs:**
- `deletedApplicationId` (`$.id`): Confirmation of the deleted application
