# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `listAssetsCommunityAsset` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: user-provided -- Anypoint organization ID hosting the portal
- `targetPortalId`: user-provided -- Portal ID the user is browsing

**Outputs:**
- `assets` (`$.assets[*]`, label `$.assets[*].name`): Assets published in the portal
- `groupId` (`$.assets[*].groupId`): Exchange groupId of an asset, used by detail-level operations
- `assetId` (`$.assets[*].assetId`): Exchange assetId of an asset
- `minorVersion` (`$.assets[*].minorVersion`): Minor version visible to the consumer

## Call 2 -- `searchCommunityAssets` (`urn:api:api-experience-hub-consumer`, POST)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `targetPortalId`: from step output `targetPortalId` -- Portal ID the user is browsing
- `searchRequest`: user-provided (example: `{'searchTerm': 'orders', 'tags': ['v2'], 'limit': 25, 'offset': 0}`) -- Search criteria (free-text query, categories, tags, paging)

**Outputs:**
- `matchingAssets` (`$.assets[*]`, label `$.assets[*].name`): Assets matching the search query

## Call 3 -- `getAssetDetails` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `targetPortalId`: from step output `targetPortalId` -- Portal ID the user is browsing
- `groupId`: from step output `groupId` -- Exchange groupId of the asset
- `assetId`: from step output `assetId` -- Exchange assetId of the asset
- `minorVersion`: from step output `minorVersion` -- Minor version to open

**Outputs:**
- `assetDetails` (`$`): Full asset metadata, including instances and tiers available to request

## Call 4 -- `getTermsAndConditions` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `targetPortalId`: from step output `targetPortalId` -- Portal ID the user is browsing
- `groupId`: from step output `groupId` -- Exchange groupId of the asset
- `assetId`: from step output `assetId` -- Exchange assetId of the asset
- `minorVersion`: from step output `minorVersion` -- Minor version whose terms to fetch

**Outputs:**
- `termsContent` (`$.content`): Markdown/HTML content of the terms and conditions

## Call 5 -- `getAssetPages` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `targetPortalId`: from step output `targetPortalId` -- Portal ID the user is browsing
- `groupId`: from step output `groupId` -- Exchange groupId of the asset
- `assetId`: from step output `assetId` -- Exchange assetId of the asset
- `minorVersion`: from step output `minorVersion` -- Minor version to fetch pages for
- `pagePath`: user-provided -- Optional documentation page path (leave empty to list all pages)

**Outputs:**
- `pageContent` (`$`): The requested documentation page (or list of pages)

## Call 6 -- `getAssetResource` (`urn:api:api-experience-hub-consumer`, GET)

**Inputs:**
- `targetOrganizationId`: from step output `targetOrganizationId` -- Anypoint organization ID hosting the portal
- `targetPortalId`: from step output `targetPortalId` -- Portal ID the user is browsing
- `groupId`: from step output `groupId` -- Exchange groupId of the asset
- `assetId`: from step output `assetId` -- Exchange assetId of the asset
- `minorVersion`: from step output `minorVersion` -- Minor version to fetch the resource from
- `resourceId`: user-provided -- Resource ID obtained from the asset detail response

**Outputs:**
- `resourceContent` (`$`): The binary/text resource content
