---
name: generating-third-party-mcp-server-registration
description: "Use this skill when a Salesforce org needs to act as a CLIENT of a non-Salesforce-hosted (third-party) MCP server. Generates four metadata files: External Credential, External Service Registration, Named Credential, and Permission Set. Trigger when users mention \"connect my org to a third-party MCP\", \"agent uses external MCP tools\", \"register an external MCP endpoint\", \"set up External Credential for MCP\", \"call out to an MCP server from Salesforce\". DO NOT use this skill when the user wants to (a) consume a Salesforce-hosted or first-party packaged MCP server, or (b) publish/expose an MCP server FROM Salesforce so external clients (Cursor, Claude, etc.) can call into the org."
compatibility: Salesforce Metadata API v65.0+
---

# Generating MCP Server Registration Metadata

## Scope

This skill covers exactly one MCP integration shape:

> **Salesforce as client → non-Salesforce-hosted (third-party) MCP server.**

The four files generated configure the org to make outbound calls to an MCP endpoint hosted outside Salesforce.

### Out of scope — STOP and do not generate files if any apply

- The MCP server is hosted on a `*.salesforce.com`, `*.force.com`, or `*.my.salesforce-sites.com` domain, or is delivered by a Salesforce-published managed package. These typically ship their own External Credential and only need permission-set assignment.
- The user wants to **publish** an MCP server from the org so external agentic clients (Cursor, Claude Desktop, Copilot, etc.) can consume it. That requires Apex action classes, GenAiFunction / GenAiPlugin metadata, an Experience Site or Connected App for the endpoint, and is NOT covered here.
- The user is asking about Agentforce **using** MCP tools that already exist in the org. That is an Agentforce configuration task, not a registration task.

If the request matches any of the above, surface the mismatch to the user instead of proceeding.

## Required Inputs

Resolve these values before generating files. Prefer reading from `sfdx-project.json` over asking the user.

1. `FILE_PATH` (Optional): Path under which the metadata folders (`externalCredentials/`, `namedCredentials/`, `externalServiceRegistrations/`, `permissionsets/`) will be created.
   - Read the package directory from `packageDirectories` in `sfdx-project.json`.
   - Default to the entry where `"default": true`. If multiple package directories exist and none is marked default, ask the user which to use.
   - **Resolve the metadata root inside the package directory.** Salesforce DX projects commonly nest source under `main/default/` before the metadata folders. After identifying the package directory (e.g., `force-app`):
     - If `<packageDir>/main/default` exists, set `FILE_PATH` to `<packageDir>/main/default` (e.g., `force-app/main/default`).
     - Otherwise, set `FILE_PATH` to the package directory itself (e.g., `force-app`).
   - The user may override the resolved value by explicitly providing one. When overridden, use the value as-is and skip the `main/default` check.
2. `NAMESPACE` (Optional): The package namespace.
   - Read from the `namespace` field in `sfdx-project.json`.
   - If a non-empty namespace is defined, append `__` to the end (e.g., `myns` becomes `myns__`).
   - If `namespace` is missing or empty in `sfdx-project.json`, confirm with the user that no namespace is needed before proceeding. On confirmation, treat as an empty string `""`.
3. `MCP_SERVER_NAME` (Required): Developer name of the MCP service. Must satisfy ALL of the following:
   - Must start with a letter.
   - May contain only letters, numbers, and underscores.
   - Must not contain consecutive underscores.
   - Must not end with an underscore.
   - Maximum 40 characters.
4. `MCP_SERVER_URL` (Required): The endpoint URL for the MCP server.
   - The user may supply the value with an `http://` or `https://` prefix.
   - If no protocol prefix is provided, prepend `https://` before substitution.

---

## Workflow

### Step 0: Confirm the integration shape (required)

Before resolving any inputs, ask the user to confirm exactly one of the following. If the answer is anything other than option 1, stop and direct the user appropriately rather than generating files.

1. **My org needs to call out to a third-party MCP server hosted outside Salesforce.** → Proceed with this skill.
2. **My org needs to call a Salesforce-hosted or packaged MCP server (1st-party).** → Stop. The third-party External Credential pattern this skill produces uses `<authenticationProtocol>Custom</authenticationProtocol>` with `NoAuthentication`, which is incorrect for first-party endpoints. Ask the user for the package or vendor's setup guide.
3. **I want to expose tools from my org as an MCP server that external clients consume.** → Stop. This is an MCP-host scenario and requires GenAiPlugin / GenAiFunction / Apex action metadata, not the registration files this skill generates.

If the user is unsure, ask: *"Are you trying to let your Salesforce org **call** an MCP server, or **be** an MCP server?"* Then map their answer to options 1–3.

### Step 1: Resolve inputs

- Replace instances of `{FILE_PATH}`, `{NAMESPACE}`, `{MCP_SERVER_NAME}`, and `{MCP_SERVER_URL}` in the file paths and file contents with the resolved values.
- For the `<schema>` and `<serviceBinding>` elements in File 2, do a textual substitution on the encoded string. Do not parse the value as JSON before substitution.
- Create these files relative to the project root directory.

### Step 2 (sanity check): Validate the endpoint domain

If `MCP_SERVER_URL` resolves to a Salesforce-owned domain (`*.salesforce.com`, `*.force.com`, `*.my.salesforce-sites.com`, `*.lightning.force.com`), pause and re-confirm with the user that this is genuinely a third-party server reachable on that domain (e.g., a Mulesoft proxy or a custom Site endpoint) rather than a packaged or platform MCP. The third-party `NoAuthentication` template is rarely correct for Salesforce-owned endpoints.

---

## Architecture

The four metadata files reference each other to form a single MCP server registration. Generate all four; any one missing breaks the chain.

```
  External Service Registration (File 2)
              │
              │ <namedCredential>
              ▼
  Named Credential (File 3)
              │
              │ <externalCredential>
              ▼
  External Credential (File 1) ◀──── Permission Set (File 4)
              │                       grants access via
              │                       <externalCredentialPrincipalAccesses>
              │                              │
              └── <parameterGroup> "MCPAuthentication" is
                  referenced as the trailing suffix of
                  <externalCredentialPrincipal>
```

Reference chain at deploy time:

- File 2 → File 3 via `<namedCredential>{NAMESPACE}{MCP_SERVER_NAME}</namedCredential>`
- File 3 → File 1 via `<externalCredential>{NAMESPACE}{MCP_SERVER_NAME}</externalCredential>`
- File 4 → File 1 via `<externalCredentialPrincipal>{NAMESPACE}{MCP_SERVER_NAME}-MCPAuthentication</externalCredentialPrincipal>` (the suffix after the dash must match File 1's `<parameterGroup>`)

### File 1: External Credential

**Path:** `{FILE_PATH}/externalCredentials/{MCP_SERVER_NAME}.externalCredential-meta.xml`

The `<parameterGroup>` value `MCPAuthentication` (line shown below) is referenced by File 4's `<externalCredentialPrincipal>` as the trailing segment after the dash. If you change the `<parameterGroup>` value here, you must change the matching suffix in File 4.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <authenticationProtocol>Custom</authenticationProtocol>
    <externalCredentialParameters>
        <parameterGroup>DefaultGroup</parameterGroup>
        <parameterName>Custom</parameterName>
        <parameterType>AuthProtocolVariant</parameterType>
        <parameterValue>NoAuthentication</parameterValue>
    </externalCredentialParameters>
    <externalCredentialParameters>
        <parameterGroup>MCPAuthentication</parameterGroup>
        <parameterName>MCPAuthentication</parameterName>
        <parameterType>NamedPrincipal</parameterType>
        <sequenceNumber>1</sequenceNumber>
    </externalCredentialParameters>
    <label>{MCP_SERVER_NAME}</label>
</ExternalCredential>
```

### File 2: External Service Registration

**Path:** `{FILE_PATH}/externalServiceRegistrations/{MCP_SERVER_NAME}.externalServiceRegistration-meta.xml`

The `tools` and `resources` arrays inside `<schema>` are intentionally left empty at registration time. They are populated automatically once an authenticated connection is established with the MCP server. After establishing the connection, instruct the user to retrieve the updated metadata from the org so the populated arrays are reflected in source.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalServiceRegistration xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>{MCP_SERVER_NAME}</label>
    <namedCredential>{NAMESPACE}{MCP_SERVER_NAME}</namedCredential>
    <namedCredentialReference>{MCP_SERVER_NAME}</namedCredentialReference>
    <registrationProviderType>ModelContextProtocol</registrationProviderType>
    <schema>{&quot;serverDescriptor&quot;:{&quot;protocolVersion&quot;:&quot;2025-06-18&quot;,&quot;serverInfo&quot;:{&quot;name&quot;:&quot;{MCP_SERVER_NAME}&quot;,&quot;version&quot;:&quot;1.0.0&quot;}},&quot;tools&quot;:[],&quot;resources&quot;:[]}</schema>
    <schemaType>ModelContextProtocol</schemaType>
    <serviceBinding>{&quot;protocolVersion&quot;:&quot;2025-06-18&quot;,&quot;serverInfo&quot;:{&quot;name&quot;:&quot;{MCP_SERVER_NAME}&quot;,&quot;version&quot;:&quot;1.0.0&quot;},&quot;instructions&quot;:null}</serviceBinding>
    <status>Incomplete</status>
    <systemVersion>8</systemVersion>
</ExternalServiceRegistration>
```

### File 3: Named Credential

**Path:** `{FILE_PATH}/namedCredentials/{MCP_SERVER_NAME}.namedCredential-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <allowMergeFieldsInBody>true</allowMergeFieldsInBody>
    <allowMergeFieldsInHeader>true</allowMergeFieldsInHeader>
    <calloutStatus>Enabled</calloutStatus>
    <generateAuthorizationHeader>true</generateAuthorizationHeader>
    <label>{MCP_SERVER_NAME}</label>
    <namedCredentialParameters>
        <parameterName>Url</parameterName>
        <parameterType>Url</parameterType>
        <parameterValue>{MCP_SERVER_URL}</parameterValue>
    </namedCredentialParameters>
    <namedCredentialParameters>
        <externalCredential>{NAMESPACE}{MCP_SERVER_NAME}</externalCredential>
        <parameterName>ExternalCredential</parameterName>
        <parameterType>Authentication</parameterType>
    </namedCredentialParameters>
    <namedCredentialType>SecuredEndpoint</namedCredentialType>
</NamedCredential>
```

### File 4: Permission Set

**Path:** `{FILE_PATH}/permissionsets/{MCP_SERVER_NAME}_Perm_Set.permissionset-meta.xml`

The `-MCPAuthentication` suffix in `<externalCredentialPrincipal>` must match the `<parameterGroup>` value defined in File 1 (the second `<externalCredentialParameters>` block). The two are linked: changing one without the other breaks the principal reference at deploy time.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Perm set for MCP Server "{MCP_SERVER_NAME}"</description>
    <externalCredentialPrincipalAccesses>
        <enabled>true</enabled>
        <externalCredentialPrincipal>{NAMESPACE}{MCP_SERVER_NAME}-MCPAuthentication</externalCredentialPrincipal>
    </externalCredentialPrincipalAccesses>
    <hasActivationRequired>false</hasActivationRequired>
    <label>{MCP_SERVER_NAME} - Permission Set</label>
    <objectPermissions>
        <allowCreate>false</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>false</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>UserExternalCredential</object>
        <viewAllFields>false</viewAllFields>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
</PermissionSet>
```

---

## Verification Checklist

Before deploying, verify:

- [ ] `MCP_SERVER_NAME` satisfies all naming rules: starts with a letter; contains only letters, numbers, and underscores; no consecutive underscores; no trailing underscore; no more than 40 characters.
- [ ] All four metadata files were created at the expected paths:
  - [ ] `{FILE_PATH}/externalCredentials/{MCP_SERVER_NAME}.externalCredential-meta.xml`
  - [ ] `{FILE_PATH}/externalServiceRegistrations/{MCP_SERVER_NAME}.externalServiceRegistration-meta.xml`
  - [ ] `{FILE_PATH}/namedCredentials/{MCP_SERVER_NAME}.namedCredential-meta.xml`
  - [ ] `{FILE_PATH}/permissionsets/{MCP_SERVER_NAME}_Perm_Set.permissionset-meta.xml`
- [ ] If any one of the four files failed to generate, revert ALL files. The four references form a chain (see [Architecture](#architecture)); a partial set is invalid and will fail to deploy.
- [ ] The `-MCPAuthentication` suffix in File 4's `<externalCredentialPrincipal>` matches the `<parameterGroup>` value in File 1.

---

## Deployment

After generating the four files, instruct the user to deploy them together. Substitute `{MCP_SERVER_NAME}` with the resolved value:

```bash
sf project deploy start \
  --metadata "ExternalCredential:{MCP_SERVER_NAME}" \
  --metadata "NamedCredential:{MCP_SERVER_NAME}" \
  --metadata "ExternalServiceRegistration:{MCP_SERVER_NAME}" \
  --metadata "PermissionSet:{MCP_SERVER_NAME}_Perm_Set"
```

Once the deployment succeeds, instruct the user to assign the permission set:

```bash
sf org assign permset -n {MCP_SERVER_NAME}_Perm_Set
```
