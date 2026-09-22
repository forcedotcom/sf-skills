# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `getTiers` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: user-provided -- Anypoint organization ID hosting the portal
- `portalId`: user-provided -- Portal ID the user belongs to
- `groupId`: user-provided -- Exchange groupId of the target asset
- `assetId`: user-provided -- Exchange assetId of the target asset
- `minorVersion`: user-provided -- Minor version the consumer wants access to
- `instanceId`: user-provided -- API instance ID (environment) to contract against

**Outputs:**
- `tiers` (`$.tiers[*]`, label `$.tiers[*].name`): SLA tiers offered on this instance
- `tierId` (`$.tiers[*].id`): Tier ID passed to the create-contract call

## Call 2 -- `getGrantTypesByInstanceId` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `instanceId`: from step output `instanceId` -- API instance ID

**Outputs:**
- `instanceGrantTypes` (`$.grantTypes[*]`): Grant types the instance supports

## Call 3 -- `getGrantTypesByApplicationId` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: user-provided -- ID of the application that will hold the contract

**Outputs:**
- `applicationGrantTypes` (`$.grantTypes[*]`): Grant types the application can use

## Call 4 -- `createContract` (`urn:api:api-experience-hub-consumer`, POST)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `groupId`: from step output `groupId` -- Exchange groupId of the target asset
- `assetId`: from step output `assetId` -- Exchange assetId of the target asset
- `minorVersion`: from step output `minorVersion` -- Minor version for the contract
- `contractRequest`: user-provided (example: `{'applicationId': 'a1b2c3d4-0000-0000-0000-000000000000', 'tierId': 12345, 'acceptedTerms': True}`) -- Contract payload (application, tier, optional custom fields)

**Outputs:**
- `contractId` (`$.id`): The newly created contract ID (may be PENDING until approved)
- `contractStatus` (`$.status`): Current status — typically APPROVED or PENDING

## Call 5 -- `getContractsByApplicationId` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- Application to audit

**Outputs:**
- `applicationContracts` (`$.contracts[*]`, label `$.contracts[*].assetName`): Contracts held by this application
- `contractIds` (`$.contracts[*].id`): Contract IDs for deeper inspection

## Call 6 -- `getContract` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- Application holding the contract
- `contractId`: from step output `contractIds` -- Specific contract ID

**Outputs:**
- `contractDetails` (`$`): Full contract details (status, tier, associated asset/instance)

## Call 7 -- `assignSlaTierToContract` (`urn:api:api-experience-hub-consumer`, PATCH)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `portalId`: from step output `portalId` -- Portal ID
- `applicationId`: from step output `applicationId` -- Application holding the contract
- `contractId`: from step output `contractIds` -- Contract whose tier is changing
- `tierId`: from step output `tierId` -- New SLA tier ID

**Outputs:**
- `updatedContractId` (`$.id`): Contract ID confirmed with the new tier applied
