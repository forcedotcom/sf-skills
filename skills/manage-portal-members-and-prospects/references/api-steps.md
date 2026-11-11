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
- `portalId` (`$[*].id`, label `$[*].name`): ID of the portal to manage

## Call 3 -- `getProspects` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID

**Outputs:**
- `prospects` (`$.prospects[*]`, label `$.prospects[*].email`): Pending prospects awaiting admin decision
- `prospectId` (`$.prospects[*].id`): Prospect ID used by the approve/reject operations

## Call 4 -- `approveProspect` (`urn:api:api-experience-hub-management`, PATCH)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `prospectId`: from step output `prospectId` -- The prospect being approved
- `approvalRequest`: user-provided (example: `{'userGroups': [{'id': '00G1a000000abcD'}]}`) -- User groups to assign to the new member on approval

**Outputs:**
- `approvedUserId` (`$.userId`): The user ID of the newly approved member

## Call 5 -- `rejectProspect` (`urn:api:api-experience-hub-management`, DELETE)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `prospectId`: from step output `prospectId` -- The prospect being rejected

**Outputs:**
- `rejectedProspectId` (`$.id`): The rejected prospect's ID (for audit)

## Call 6 -- `getCommunityUsers` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID

**Outputs:**
- `members` (`$.users[*]`, label `$.users[*].email`): Active portal members
- `userId` (`$.users[*].id`): Portal-member user ID used by per-member operations

## Call 7 -- `getCommunityUser` (`urn:api:api-experience-hub-management`, GET)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `userId`: from step output `userId` -- Portal-member user ID

**Outputs:**
- `memberUserGroups` (`$.userGroups[*]`, label `$.userGroups[*].name`): Current user groups assigned to the member

## Call 8 -- `addGroupMappingToUser` (`urn:api:api-experience-hub-management`, PUT)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `targetUserId`: from step output `userId` -- Portal-member user ID
- `userGroupsRequest`: user-provided (example: `{'userGroups': [{'id': '00G1a000000abcD'}, {'id': '00G1a000000efgH'}]}`) -- Full replacement set of user groups for this member

**Outputs:**
- `updatedUserId` (`$.userId`): Confirmed member ID with new assignments applied

## Call 9 -- `disableCommunityUser` (`urn:api:api-experience-hub-management`, PATCH)

**Inputs:**
- `connectionId`: from step output `connectionId` -- Connection ID
- `portalId`: from step output `portalId` -- Portal ID
- `targetUserId`: from step output `userId` -- The member to disable

**Outputs:**
- `disabledUserId` (`$.userId`): Confirmed disabled member ID
