# MFA Setup Reference

Step-by-step setup for enabling MFA on Experience Sites. Read this when
executing Steps 3-5 of the SKILL.md workflow.

## Deploy Permission Sets

Deploy from the skill's `assets/` directory or from your project's
`force-app/main/default/permissionsets/`:

```bash
sf project deploy start --source-dir force-app/main/default/permissionsets \
  --target-org <org-alias> --test-level NoTestRun
```

This deploys:
- **MFA_Required_For_Community** — enforces MFA via `ForceTwoFactor`
- **API_Enabled_For_Community** — grants API access (always deployed for React sites)

## Grant Guest Profile Apex Class Access

The site login page runs as the **guest user**. If the guest profile lacks access to
the UIBundle login Apex classes, users hit
`FORBIDDEN: You do not have access to the Apex class named: UIBundleLogin` and never
reach the MFA challenge (SKILL.md Step 3c).

Resolve `<guest-profile-name>` from the guest-user query in Step 3c, then run this
anonymous Apex. It diffs the guest permission set's existing class access against the
six login classes and inserts only the missing `SetupEntityAccess` entries (safe to
re-run):

```apex
// Run via: sf apex run --target-org <org-alias>
Profile guestProfile = [SELECT Id FROM Profile WHERE Name = '<guest-profile-name>'];
PermissionSet guestPs = [SELECT Id FROM PermissionSet WHERE ProfileId = :guestProfile.Id AND IsOwnedByProfile = true];

List<ApexClass> loginClasses = [SELECT Id, Name FROM ApexClass WHERE Name IN ('UIBundleLogin', 'UIBundleAuthUtils', 'UIBundleForgotPassword', 'UIBundleRegistration', 'UIBundleSocialLoginConfig', 'UIBundleChangePassword')];

Set<Id> existingAccess = new Set<Id>();
for (SetupEntityAccess sea : [SELECT SetupEntityId FROM SetupEntityAccess WHERE ParentId = :guestPs.Id AND SetupEntityType = 'ApexClass']) {
    existingAccess.add(sea.SetupEntityId);
}

List<SetupEntityAccess> toInsert = new List<SetupEntityAccess>();
for (ApexClass c : loginClasses) {
    if (!existingAccess.contains(c.Id)) {
        System.debug('Missing: ' + c.Name);
        toInsert.add(new SetupEntityAccess(ParentId = guestPs.Id, SetupEntityId = c.Id));
    }
}

if (!toInsert.isEmpty()) {
    insert toInsert;
    System.debug('Granted access to ' + toInsert.size() + ' classes');
}
```

Alternatively, deploy `<classAccess>` entries (`enabled=true`) for the same six
classes to the guest profile metadata XML.

## Assign Permission Sets

### Option A: Individual users (testing)

```bash
# Find community users
sf data query --target-org <org-alias> \
  --query "SELECT Id, Username, Name, Profile.Name FROM User WHERE UserType IN ('CspLitePortal', 'PowerCustomerSuccess', 'CustomerSuccess') AND IsActive = true" --json

# Get permission set IDs
sf data query --target-org <org-alias> \
  --query "SELECT Id, Name FROM PermissionSet WHERE Name IN ('MFA_Required_For_Community', 'API_Enabled_For_Community')" --json

# Assign MFA permission set
sf data create record --target-org <org-alias> --sobject PermissionSetAssignment \
  --values "AssigneeId='<USER_ID>' PermissionSetId='<MFA_PERM_SET_ID>'" --json

# Assign API Enabled
sf data create record --target-org <org-alias> --sobject PermissionSetAssignment \
  --values "AssigneeId='<USER_ID>' PermissionSetId='<API_PERM_SET_ID>'" --json
```

### Option B: Permission Set Group (production)

1. Setup > Permission Set Groups > New
2. Add `MFA_Required_For_Community`
3. Add `API_Enabled_For_Community`
4. Assign the group to the community profile

### Option C: CLI bulk assign

```bash
sf org assign permset --name MFA_Required_For_Community --target-org <org-alias> --json
sf org assign permset --name API_Enabled_For_Community --target-org <org-alias> --json
```

## Publish and Verify

```bash
sf community publish --name "<site-name>" --target-org <org-alias>
```

Verification steps:
1. Open an incognito/private browser window
2. Navigate to the site login page
3. Enter credentials and submit
4. MFA challenge page appears (on the `vforcesite` domain)
5. Complete verification (register authenticator app if first time)
6. Land on the site, fully authenticated

## Customize Branding (Optional)

The MFA challenge page uses `NetworkBranding` metadata. For React Experience
Sites (Site Containers), the branding admin UI is available in Setup → Digital
Experiences → Login Settings (since 264). The Metadata API path below is the
option for scripted/repeatable setup.

```bash
# Retrieve existing branding
sf project retrieve start --target-org <org-alias> \
  --metadata NetworkBranding --target-metadata-dir ./branding --unzip

# Edit networkBranding-meta.xml: loginLogo, loginFooterText, loginPrimaryColor

# Deploy updated branding
sf project deploy start --target-org <org-alias> \
  --source-dir force-app/main/default/networkBranding --test-level NoTestRun
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No MFA challenge on login | `ForceTwoFactor` not assigned | Verify `MFA_Required_For_Community` assignment |
| `API_DISABLED_FOR_ORG` after login | Missing `ApiEnabled` | Assign `API_Enabled_For_Community` |
| Default Salesforce branding | No `NetworkBranding` deployed | Deploy custom branding via Metadata API |
| `vforcesite` in MFA URL | Expected behavior | Platform serves login/MFA from Force.com Site domain |
| MFA works but site errors | Profile missing page/object access | Check community profile permissions |

## Verification Commands

Confirm permission set exists and has the right permissions:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Name, PermissionsForceTwoFactor FROM PermissionSet WHERE Name = 'MFA_Required_For_Community'" --json
```

Confirm assignment:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Assignee.Username, PermissionSet.Name FROM PermissionSetAssignment WHERE PermissionSet.Name = 'MFA_Required_For_Community'" --json
```
