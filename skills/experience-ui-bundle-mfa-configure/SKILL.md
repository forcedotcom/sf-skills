---
name: experience-ui-bundle-mfa-configure
description: "Configure Multi-Factor Authentication (MFA) for Salesforce Experience Site users. TRIGGER when: user wants to enable MFA on a community, enforce two-factor authentication for portal users, add MFA to a React Experience Site / Web App, configure ForceTwoFactor permission, create MFA permission sets for external users, or troubleshoot MFA not appearing on login. Also triggers on: MFA community, two-factor portal, ForceTwoFactor permission set, MFA Experience Cloud, MFA React site, identity verification community, MFA experience site, ForceTwoFactor permissionset-meta.xml, MFA permissionset-meta.xml. DO NOT TRIGGER when: configuring org-wide MFA for internal users (that's Setup > Identity Verification), building custom login UI components (use experience-ui-bundle-frontend-generate), or generating generic permission sets without MFA context (use platform-permission-set-generate)."
metadata:
  version: "1.1"
  domains: ["Experience"]
  minApiVersion: "47.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Experience Cloud (Customer Community / Customer Community Login)"
  relatedSkills:
    - "dx-org-permission-set-assign"
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-frontend-generate"
    - "platform-metadata-deploy"
    - "platform-permission-set-generate"
---

# Enabling MFA on Experience Sites

Enable Multi-Factor Authentication for Experience Site (Community) users by deploying the correct permission sets and verifying the platform-handled MFA challenge flow.

## Scope

**In scope:**
- Deploying `ForceTwoFactor` permission set for community users
- Deploying `ApiEnabled` permission set (required for post-login API calls)
- Assigning permission sets to community users
- Troubleshooting MFA not appearing on login
- Customizing MFA/login page branding via NetworkBranding metadata

**Out of scope — delegate elsewhere:**
- Building custom login UI → `experience-ui-bundle-frontend-generate`
- Creating generic permission sets → `platform-permission-set-generate`
- Assigning permission sets (if already deployed) → `dx-org-permission-set-assign`
- Deploying metadata to org → `platform-metadata-deploy`
- Org-wide MFA for internal Salesforce users → Setup > Identity Verification (not a skill)

---

## Prerequisites

Before using this skill, ensure the following are already in place:

| Prerequisite | Why |
|-------------|-----|
| **Experience Cloud site deployed and active** | MFA applies to community login — no site means no login flow to protect |
| **Community users exist** (or will self-register) | Permission sets are assigned to community users; the site must have a community-enabled profile |
| **Customer Community or Customer Community Login license enabled** | Required for community user profiles — without it, user creation and profile deployment will fail |
| **Network/Site published at least once** | The site must be reachable at its URL for login + MFA challenge to appear |

> **Note:** This skill does NOT handle org setup, license provisioning, or Experience Cloud site creation. If these prerequisites are missing, set them up first via Setup > Digital Experiences > All Sites > New, or deploy your site's base app bundle.

---

## Required Inputs

Gather before acting:

| Input | How to determine |
|-------|-----------------|
| **Target org** | Org alias for `sf` CLI commands |
| **Site name** | Experience Site (Network) name — resolve via `SELECT Id, Name FROM Network` (see Step 1); this is the site/Network name, NOT the `uiBundles/` app name |
| **Community users** | Which users or profiles to assign MFA to |

---

## Critical Domain Knowledge

These facts are non-obvious and frequently cause confusion:

| Fact | Detail |
|------|--------|
| **No custom UI needed** | Platform renders the MFA challenge page — no React/LWC component required |
| **ForceTwoFactor permission** | The ONLY way to enforce MFA for community users at login |
| **Org Identity Verification checkbox** | Does NOT enforce MFA for community/portal users — only for internal users |
| **vforcesite domain** | MFA challenge page is always served from the underlying Force.com Site domain — this is expected |
| **Always deploy ApiEnabled** | React Experience Sites make post-login REST/Connect API calls (`sdk.graphql`, `sdk.fetch`); without `ApiEnabled` they fail with `API_DISABLED_FOR_ORG` |
| **Social Login / SSO is separate from MFA** | React sites render configured Auth Providers via the built-in Social Login component (shipped in 264) — driven by Auth Provider setup, not by the MFA permission sets. See `references/social-login.md`. |
| **Login-page branding works for React sites** | Since 264, the NetworkBranding "Login & Registration" section is shown in Setup for Site Containers, so logo/color/footer can be customized in the UI — Metadata API still works too. |

---

## Workflow

### Step 1: Resolve the target site (Network)

These are React Experience Sites, so **both** permission sets are always deployed —
`ForceTwoFactor` (enforces MFA) and `ApiEnabled` (React sites make post-login API
calls).

Resolve the Experience Site's real name and Id from the org — do **not** assume the
`uiBundles/` app folder name is the site name. They are frequently different, and the
site name must come from the org (the deploy target), not the local project.
`<site-name>` and `<NETWORK_ID>` below come from here:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Name FROM Network" --json
```

- One site → use its `Name` as `<site-name>` and `Id` as `<NETWORK_ID>`.
- Multiple sites → ask the user which one (show the names).
- Zero sites → the site isn't deployed yet; stop and tell the user (see Prerequisites).

### Step 2: Generate permission set files

First, detect the project's source directory:

```bash
jq -r '.packageDirectories[0].path + "/main/default"' sfdx-project.json
```

Use the result as `<source-dir>` (e.g. `force-app/main/default`) for all commands below.

Write **both** permission sets (React Experience Sites always need both):

1. **Read** `assets/MFA_Required_For_Community.permissionset-meta.xml`
2. Write it to `<source-dir>/permissionsets/MFA_Required_For_Community.permissionset-meta.xml` in the user's project
3. **Read** `assets/API_Enabled_For_Community.permissionset-meta.xml`
4. Write it to `<source-dir>/permissionsets/API_Enabled_For_Community.permissionset-meta.xml`

### Step 3: Deploy to org

```bash
sf project deploy start \
  --source-dir <source-dir>/permissionsets \
  --target-org <org-alias> --test-level NoTestRun
```

### Step 3b: Validate community profile is a network member

Before assigning permission sets to users, verify that the community profile is registered as a site member. Without this, community users cannot log in at all (and MFA will never trigger).

1. **Query current network members:**

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, ParentId FROM NetworkMemberGroup WHERE NetworkId = '<NETWORK_ID>'" --json
```

2. **Check if the community profile is in the list:**

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Name FROM Profile WHERE UserType IN ('CspLitePortal', 'PowerCustomerSuccess') AND Name LIKE '%Community%'" --json
```

3. **If the profile is NOT a member**, add it to the `.network-meta.xml`:

```xml
<networkMemberGroups>
    <!-- Replace with the community profile name from Step 3b query above -->
    <profile>YOUR_COMMUNITY_PROFILE_NAME</profile>
    <!-- existing entries -->
</networkMemberGroups>
```

4. **Deploy the updated network metadata:**

```bash
sf project deploy start \
  --source-dir <source-dir>/networks \
  --target-org <org-alias> --test-level NoTestRun
```

> **IMPORTANT:** If the community profile is not a member of the network, users with that profile CANNOT log in — meaning MFA will never be triggered even if permission sets are correctly assigned. This is a common misconfiguration in freshly deployed orgs.

### Step 3c: Validate guest profile has Apex class access for login

The site login page runs as the **guest user** (unauthenticated). If the guest profile doesn't have access to login Apex classes, users will get `FORBIDDEN: You do not have access to the Apex class named: UIBundleLogin` and can never reach the MFA challenge.

1. **Find the site guest user profile:**

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Username, Profile.Name, Profile.Id FROM User WHERE UserType = 'Guest' AND IsActive = true" --json
```

2. **Grant access to any missing UIBundle login classes.** The six classes are `UIBundleLogin`, `UIBundleAuthUtils`, `UIBundleForgotPassword`, `UIBundleChangePassword`, `UIBundleRegistration`, and `UIBundleSocialLoginConfig`. Run the anonymous Apex in `references/setup.md` ("Grant Guest Profile Apex Class Access") — it diffs existing access and inserts only what's missing — or deploy `<classAccess>` entries for the same classes to the guest profile metadata XML.

> **IMPORTANT:** This is NOT MFA-specific, but without it the login page itself is broken. The skill must validate this to ensure MFA can actually be triggered. Common in freshly deployed orgs where the guest profile didn't get full class access.

### Step 4: Assign permission sets

Find community users:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Username, Name, Profile.Name FROM User WHERE UserType IN ('CspLitePortal', 'PowerCustomerSuccess', 'CustomerSuccess') AND IsActive = true" --json
```

#### If community users exist:

Find the permission set IDs:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Name FROM PermissionSet WHERE Name IN ('MFA_Required_For_Community', 'API_Enabled_For_Community')" --json
```

Assign to each user:

```bash
sf data create record --target-org <org-alias> --sobject PermissionSetAssignment \
  --values "AssigneeId='<USER_ID>' PermissionSetId='<PERM_SET_ID>'" --json
```

Alternatively, delegate to `dx-org-permission-set-assign` skill:

```bash
sf org assign permset --name MFA_Required_For_Community --target-org <org-alias> --json
sf org assign permset --name API_Enabled_For_Community --target-org <org-alias> --json
```

#### If no community users found:

Ask the user: *"No active community users found in this org. Would you like me to create a test community user so you can verify MFA is working?"*

If user agrees, create a test community user:

1. **Find the community profile** from the site's network configuration:

```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id, Name FROM Profile WHERE UserType IN ('CspLitePortal', 'PowerCustomerSuccess') AND Name LIKE '%Customer Community%'" --json
```

2. **Create an Account** (required as community user parent):

```bash
sf data create record --target-org <org-alias> --sobject Account \
  --values "Name='MFA Test Account'" --json
```

3. **Create a Contact** (linked to the Account):

```bash
sf data create record --target-org <org-alias> --sobject Contact \
  --values "FirstName='MFA' LastName='Test User' Email='mfa.testuser@<site-name>.test' AccountId='<ACCOUNT_ID>'" --json
```

4. **Create the User** with the community profile:

```bash
sf data create record --target-org <org-alias> --sobject User \
  --values "FirstName='MFA' LastName='Test User' Email='mfa.testuser@<site-name>.test' Username='mfa.testuser@<site-name>.test' Alias='mfatest' ProfileId='<PROFILE_ID>' ContactId='<CONTACT_ID>' EmailEncodingKey='UTF-8' LanguageLocaleKey='en_US' LocaleSidKey='en_US' TimeZoneSidKey='America/Los_Angeles'" --json
```

5. **Set a password** for the test user:

```bash
sf data update record --target-org <org-alias> --sobject User \
  --where "Username='mfa.testuser@<site-name>.test'" \
  --values "IsActive=true" --json
```

```bash
sf org generate password --target-org <org-alias> --on-behalf-of mfa.testuser@<site-name>.test --json
```

6. **Assign both permission sets** to the new user:

```bash
sf org assign permset --name MFA_Required_For_Community --target-org <org-alias> --on-behalf-of mfa.testuser@<site-name>.test --json
sf org assign permset --name API_Enabled_For_Community --target-org <org-alias> --on-behalf-of mfa.testuser@<site-name>.test --json
```

Report the credentials to the user so they can test:
> "Created test user: `mfa.testuser@<site-name>.test` with password: `<generated-password>`. You can use these credentials to verify MFA on your site."

> **IMPORTANT:** Community users require Account → Contact → User hierarchy. Creating a User without a linked Contact on a community profile will fail.

### Step 5: Add permission sets to site Members (networkMemberGroups)

This ensures new community users automatically get MFA assigned at the site level.

1. Find the existing `.network-meta.xml` in the project:

```bash
find . -name "*.network-meta.xml" -not -path "*/node_modules/*"
```

2. Read the file and locate the `<networkMemberGroups>` section.

3. Add the permission set entries (if not already present):

```xml
<networkMemberGroups>
    <!-- Replace with the community profile name from Step 3b query -->
    <profile>YOUR_COMMUNITY_PROFILE_NAME</profile>
    <!-- Add MFA and API permission sets -->
    <permissionSet>MFA_Required_For_Community</permissionSet>
    <permissionSet>API_Enabled_For_Community</permissionSet>
</networkMemberGroups>
```

> **IMPORTANT:** Network metadata deploys are declarative — whatever you deploy becomes the full state. Do NOT create a new `.network-meta.xml` from scratch. Always read the existing file and add entries to it.

4. Deploy the updated network metadata:

```bash
sf project deploy start \
  --source-dir <source-dir>/networks \
  --target-org <org-alias> --test-level NoTestRun
```

### Step 6: Publish and verify

```bash
sf community publish --name "<site-name>" --target-org <org-alias>
```

Verification steps:
1. Open incognito browser
2. Navigate to site login page
3. Enter credentials → MFA challenge page should appear (on vforcesite domain)
4. Complete MFA → should land on the site, logged in

---

## Rules

| Rule | Rationale |
|------|-----------|
| Never use the org-wide Identity Verification checkbox for community MFA | It only affects internal users — has no effect on community login |
| Always deploy `ApiEnabled` for React sites | Post-login API calls (`sdk.graphql`, `sdk.fetch`) will fail without it |
| Permission set names are exact — do not rename | `MFA_Required_For_Community` and `API_Enabled_For_Community` are the canonical names |
| Do not build custom MFA UI components | Platform handles the entire MFA challenge flow — custom UI would duplicate and conflict |
| Always assign before testing | Deployment alone does not activate MFA — assignment to specific users is required |

---

## Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| No MFA challenge on login | `ForceTwoFactor` permission not assigned to user | Verify PermissionSetAssignment exists for the user |
| `API_DISABLED_FOR_ORG` after login | Missing `ApiEnabled` permission | Assign `API_Enabled_For_Community` permission set |
| MFA page shows default Salesforce branding | No `NetworkBranding` metadata deployed | Read `references/branding.md` and deploy custom branding |
| `vforcesite` in MFA page URL | Expected behavior — not a bug | Platform serves login/MFA from Force.com Site domain |
| Identity Verification enabled but no community MFA | Wrong mechanism used | Use `ForceTwoFactor` via Permission Set instead |
| User already has MFA but isn't challenged | Active session exists | Test in incognito/private browser |
| Permission set deployed but MFA not enforced | Deployed but not assigned | Run assignment step — deploy != assign |
| No community users found in org | Users haven't been created or self-registered yet | Offer to create a test community user (Account → Contact → User hierarchy) for verification. Permission sets are still deployed and networkMemberGroups updated — org is MFA-ready for when users exist. |
| `FORBIDDEN: You do not have access to the Apex class named: UIBundleLogin` | Site guest profile missing Apex class access | Run Step 3c to grant guest profile access to all UIBundle login classes |
| Community user can't log in (redirects silently or gets `portal user email settings` error) | Community profile not a network member, or email deliverability not set to All Email | Add profile to `.network-meta.xml` `<networkMemberGroups>` and redeploy (Step 3b). Verify email deliverability is set to "All Email" in Setup → Email → Deliverability. |

---

## Output Expectations

Files generated in the user's project:

| File | When |
|------|------|
| `permissionsets/MFA_Required_For_Community.permissionset-meta.xml` | Always |
| `permissionsets/API_Enabled_For_Community.permissionset-meta.xml` | Always |

---

## Cross-Skill Integration

| When | Delegate to |
|------|-------------|
| User only needs to assign (already deployed) | `dx-org-permission-set-assign` |
| User needs to deploy all project metadata | `platform-metadata-deploy` |
| User wants to customize the login page UI | `experience-ui-bundle-frontend-generate` |
| User needs to create a new generic permission set | `platform-permission-set-generate` |
| User wants IDP/Social Login (different from MFA) | Supported on React sites — the built-in Social Login component renders linked Auth Providers on the login page automatically. Create the Auth Providers in Setup, then link them to the React site via the `experience-ui-bundle-deploy` social login step (`socialLogin` in `org-setup.config.json`) — the React SSO admin UI is hidden, so linking is programmatic, not a Setup click-path. See `references/social-login.md`. |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/MFA_Required_For_Community.permissionset-meta.xml` | Step 2 — writing permission set to project |
| `assets/API_Enabled_For_Community.permissionset-meta.xml` | Step 2 — always deployed |
| `references/branding.md` | When user wants to customize MFA/login page appearance |
| `references/social-login.md` | When user wants IDP/SSO/Social Login on a React site alongside or instead of MFA |
| `references/setup.md` | Steps 3–5 — detailed assignment, network membership, and publish reference |
