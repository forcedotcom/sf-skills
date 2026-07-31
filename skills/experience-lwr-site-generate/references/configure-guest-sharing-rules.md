# Guest User Sharing Rules (Public Sites Only)

**Use when** the user asks to create or modify a guest sharing rule, mentions a username containing "Guest User" or "Site Guest User" (e.g. "ZenLease Site Guest User"), or wants to share object records with unauthenticated visitors.

## Steps

1. **Resolve the guest user identity**: If the user provides a username like "ZenLease Site Guest User", use it directly as the `<guestUser>` value (`CommunityNickname`). If a user ID is provided (e.g. `005AAC00003f8EP`), query the org to get the `CommunityNickname` first.
2. **Check for existing file**: Look for `sharingRules/{ObjectName}.sharingRules-meta.xml` locally. If missing, retrieve it from the org before editing.
3. **Generate the rule**: Follow the XML example and critical requirements below. Never use `sharingCriteriaRules` or `<role>`/`<group>` for guest rules.

If `sharingRules` metadata is not available locally in `force-app/main/default/sharingRules`, retrieve it from the org before creating new rules.

## Retrieve Full SharingRules Schema

Use the metadata MCP tool with metadataType "SharingRules" to retrieve schema.

## XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
  <sharingGuestRules>
    <fullName>ShareAccountsWithSiteGuest</fullName>
    <accessLevel>Read</accessLevel>
    <includeHVUOwnedRecords>false</includeHVUOwnedRecords>
    <label>Share Accounts With Site Guest</label>
    <sharedTo>
      <guestUser>[site Guest User's CommunityNickanme]</guestUser>
    </sharedTo>
    <criteriaItems>
      <field>Name</field>
      <operation>notEqual</operation>
      <value>null</value>
    </criteriaItems>
  </sharingGuestRules>
</SharingRules>
```

## Critical Requirements

1. **SharedTo Element**: Must use `<guestUser>{site Guest User's CommunityNickanme}</guestUser>` (not URL path prefix).
2. **includeHVUOwnedRecords**: Required field. Set to `false` unless records owned by high-volume site users should be included.
3. **One XML file per object**: Put all rules for a given object in one file. Do not create additional.

## Common Mistakes

- Using `<role>` or `<group>` instead of `<guestUser>` in sharedTo
- Omitting the required `includeHVUOwnedRecords` field
- Using `includeRecordsOwnedByAll` (that's for `sharingCriteriaRules`, not guest rules)
