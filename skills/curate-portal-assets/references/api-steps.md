# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `getConnections` (`urn:api:api-experience-hub-management`, GET)

No inputs.

**Outputs:**
- `connectionId` (`$[*].id`, label `$[*].name`): AEH connection ID (Salesforce org link) backing the portal

## Call 2 -- `getAllApiPortalByConnectionId` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID from Step 1

**Outputs:**
- `portalId` (`$[*].id`, label `$[*].name`): ID of the portal to curate

## Call 3 -- `searchExchangeAssets` (`urn:api:api-experience-hub-management`, POST)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID from Step 1
- `portalId`: from step output `portalId` -- Portal ID from Step 2
- `searchRequest`: user-provided (example: `{'searchTerm': 'orders', 'limit': 25, 'offset': 0}`) -- Search criteria (free-text query, categories, tags, pagination)

**Outputs:**
- `candidateAssets` (`$.assets[*]`, label `$.assets[*].name`): Exchange assets available for publication in this portal
- `candidateGroupId` (`$.assets[*].groupId`): groupId of each candidate asset
- `candidateAssetId` (`$.assets[*].assetId`): assetId of each candidate asset

## Call 4 -- `addAssetsToCommunity` (`urn:api:api-experience-hub-management`, POST)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID from Step 1
- `portalId`: from step output `portalId` -- Portal ID from Step 2
- `assetsRequest`: user-provided (example: `{'assets': [{'groupId': 'f1e97bc6-315a-4490-82a7-23abe036327a', 'assetId': 'orders-api'}]}`) -- Array of Exchange asset references to publish (groupId + assetId, optional minorVersion filter)

**Outputs:**
- `publishedAssetIds` (`$[*].assetId`): The newly published asset IDs

## Call 5 -- `getAllVersionsVisibilityByGA` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `groupId`: user-provided -- Exchange groupId of the asset to inspect
- `assetId`: user-provided -- Exchange assetId of the asset to inspect

**Outputs:**
- `versionVisibilities` (`$.versions[*]`, label `$.versions[*].minorVersion`): Per-minor-version visibility state (published, hidden, profile-restricted)

## Call 6 -- `updateCommunityAsset` (`urn:api:api-experience-hub-management`, PATCH)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `groupId`: from step output `groupId` -- groupId from Step 5
- `assetId`: from step output `assetId` -- assetId from Step 5
- `visibilityUpdate`: user-provided (example: `{'versions': [{'minorVersion': '1.0', 'visibility': 'PUBLISHED'}, {'minorVersion': '2.0', 'visibility': 'HIDDEN'}]}`) -- Per-minor-version visibility payload

**Outputs:**
- `updatedAssetId` (`$.assetId`): Confirmed assetId with new visibility applied

## Call 7 -- `removeAssetFromCommunity` (`urn:api:api-experience-hub-management`, POST)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `removeRequest`: user-provided (example: `{'assets': [{'groupId': 'f1e97bc6-315a-4490-82a7-23abe036327a', 'assetId': 'legacy-orders-api'}]}`) -- Array of asset coordinates to unpublish

**Outputs:**
- `removedAssetIds` (`$[*].assetId`): Assets that were successfully removed from the portal
