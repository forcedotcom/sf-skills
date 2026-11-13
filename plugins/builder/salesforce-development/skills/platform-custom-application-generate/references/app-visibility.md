# App Visibility with Profile metadata

One `applicationVisibilities` entry per Profile (or PermissionSet), deployed after (or in the same package as) the app. A Profile containing only this element merges into the existing profile; it does not reset its other settings.

```xml
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>Support_Console</application>
        <default>false</default>
        <visible>true</visible>
    </applicationVisibilities>
</Profile>
```

- `<application>` is the app's API name
- The Profile `fullName` is its metadata name, not its label: "Admin" (System Administrator), "Standard" (Standard User), "MarketingProfile" (Marketing User), "ContractManager" (Contract Manager). Look one up with Tooling `SELECT FullName FROM Profile WHERE Name = '<label>'` (one profile per query)
- `/headless/metadata` rejects metadata names with spaces or special characters ("Invalid fullName", on GET and PUT), e.g. "Tier 2 Support Agent" or "Custom%3A Support Profile" for "Custom: Support Profile". On a connected org, grant those with SetupEntityAccess rows instead
- Set `<default>true</default>` only when the user asks for this app to be the profile's default app
- To hide the app from a profile, deploy its entry with `<visible>false</visible>`
