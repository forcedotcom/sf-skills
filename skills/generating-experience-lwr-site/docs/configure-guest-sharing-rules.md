# Guest User Sharing Rules (Public Sites Only)

**Use when** the user explicitly wants to make the site **public** (accessible to unauthenticated visitors). If the site is private/login-required, guest sharing rules are not needed.
If sharingRules metadata is not available locally in force-app/main/default/sharingRules, retrieve it from the org before creating new rules.

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
