# Agent Access Permissions & Visibility Troubleshooting

How to make a published agent visible to end users in the Lightning Experience Copilot panel.

---

## Agent Access Permissions

Employee Agents require explicit access via the `<agentAccesses>` element in Permission Sets. Without this, users won't see the agent in the Lightning Experience Copilot panel.

### Permission Set XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <agentAccesses>
        <agentName>Case_Assist</agentName>
        <enabled>true</enabled>
    </agentAccesses>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Case Assist Agent Access</label>
</PermissionSet>
```

### Key Points

- `<agentName>` must exactly match the `developer_name` in the agent's config block
- Multiple `<agentAccesses>` elements can be included for multiple agents
- `<enabled>true</enabled>` grants access; `false` or omission denies access

### Deploy and Assign

Deploy the permission set with `sf project deploy start --json --metadata "PermissionSet:<PermissionSetName>"`. Assign it to a specific user with `sf org assign permset --json --name <PermissionSetName> --on-behalf-of user@example.com`.

---

## Visibility Troubleshooting

When an Agentforce Employee Agent is deployed but not visible to users, work through these steps:

### Step 1: Verify Agent Status

Confirm the agent is active. Query `BotVersion` to check: `sf data query --json -q "SELECT Status, VersionNumber FROM BotVersion WHERE BotDefinition.DeveloperName = '<developer_name>'"`. At least one version should have `Status = 'Active'`. If none do, activate with `sf agent activate --json --api-name <developer_name>` before continuing.

### Step 2: Check for Agent Access Permission

Retrieve permission sets with `sf project retrieve start --json --metadata "PermissionSet:*"`. Search retrieved files for `<agentAccesses>` containing agent's `developer_name`. If none, create a new permission set.

### Step 3: Create Permission Set (if needed)

Create a file at `force-app/main/default/permissionsets/MyAgent_Access.permissionset-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <agentAccesses>
        <agentName>MyAgent</agentName>
        <enabled>true</enabled>
    </agentAccesses>
    <hasActivationRequired>false</hasActivationRequired>
    <label>MyAgent Access</label>
</PermissionSet>
```

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| No Agentforce icon | CopilotSalesforceUser PS not assigned | Assign CopilotSalesforceUser permission set |
| Icon visible, agent not in list | Missing agentAccesses | Add `<agentAccesses>` to permission set |
| Agent visible, errors on open | Agent not fully published | See Step 1: Verify Agent Status |
| "Agent not found" error | Name mismatch | Ensure `<agentName>` matches `developer_name` exactly |
