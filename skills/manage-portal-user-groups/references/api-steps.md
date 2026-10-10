# API Steps Reference

Full parameter sourcing and output mapping for each API call in `SKILL.md`, mirrored from the machine-validated `api:`/`operationId` step blocks in the mulesoft-dx source skill.

## Call 1 -- `getConnections` (`urn:api:api-experience-hub-management`, GET)

No inputs.

**Outputs:**
- `connectionId` (`$[*].id`, label `$[*].name`): AEH connection ID backing the portal

## Call 2 -- `getAllApiPortalByConnectionId` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID from Step 1

**Outputs:**
- `portalId` (`$[*].id`, label `$[*].name`): ID of the portal whose user groups you'll manage

## Call 3 -- `getAllProfilesByPortal` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID

**Outputs:**
- `userGroups` (`$.profiles[*]`, label `$.profiles[*].name`): Existing user groups (profiles) on the portal
- `userGroupId` (`$.profiles[*].id`): ID of a specific user group, used by update/delete

## Call 4 -- `createUserGroup` (`urn:api:api-experience-hub-management`, POST)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `userGroupRequest`: user-provided (example: `{'name': 'Gold Tier Consumers', 'description': 'Members granted access to premium APIs'}`) -- Definition of the new user group

**Outputs:**
- `createdUserGroupId` (`$.id`): The newly created user group ID

## Call 5 -- `updateUserGroup` (`urn:api:api-experience-hub-management`, PATCH)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `userGroupId`: from step output `userGroupId` -- ID of the user group to update
- `userGroupRequest`: user-provided (example: `{'name': 'Gold Tier Consumers (EU)', 'description': 'Members granted access to premium EU-region APIs'}`) -- Updated name/description for the user group

**Outputs:**
- `updatedUserGroupId` (`$.id`): Confirmed ID of the updated user group

## Call 6 -- `deleteUserGroup` (`urn:api:api-experience-hub-management`, DELETE)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `userGroupId`: from step output `userGroupId` -- ID of the user group to delete

**Outputs:**
- `deletedUserGroupId` (`$.id`): Confirmation of the deleted user group

## Call 7 -- `getGroupMappings` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID

**Outputs:**
- `groupMappings` (`$.mappings[*]`, label `$.mappings[*].idpGroupName`): Existing IdP-to-AEH group mappings
- `groupMappingId` (`$.mappings[*].id`): ID used to delete a mapping

## Call 8 -- `addAdditionalGroupMapping` (`urn:api:api-experience-hub-management`, POST)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `mappingRequest`: user-provided (example: `{'idpGroupName': 'gold-tier-consumers', 'userGroupId': '00G1a000000abcD'}`) -- Mapping between an external IdP group and an AEH user group

**Outputs:**
- `createdGroupMappingId` (`$.id`): The newly created mapping ID

## Call 9 -- `deleteGroupMappings` (`urn:api:api-experience-hub-management`, DELETE)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `groupMappingId`: from step output `groupMappingId` -- ID of the mapping to remove

**Outputs:**
- `deletedGroupMappingId` (`$.id`): Confirmation of the removed mapping
