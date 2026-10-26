---
name: omni-gateway-dump
description: |
  Interpret the contents of an Omni Gateway diagnostic dump ZIP file to identify
  the live state of API instances, service bindings, policy configuration, and
  known anomalies. Use when the user has a gateway dump file and wants to
  understand what was deployed at the time of capture, find orphaned or missing
  resources, compare live state against the conf.d configuration, or diagnose a
  gateway failure using a support-submitted dump.
---

# Analyze Gateway Dump

## Dump Format Reference

The dump is a ZIP archive containing a `dump/` directory with flat JSON files.
Each JSON file holds an array of Kubernetes-style resources with `apiVersion`, `kind`, `metadata`, `spec`, and `status` fields.

```
dump-<timestamp>.zip
└── dump/
    ├── api-instances.json        # Live ApiInstance resources
    ├── policy-bindings.json      # Live PolicyBinding resources
    ├── services.json             # Live Service resources
    ├── configurations.json       # Gateway Configuration (includes registration)
    ├── extensions.json           # Policy extension definitions (may be large — skip unless needed)
    └── control-node-storage.json # Gateway agent ID: {"store": "<agentId>"}
```

Note: dumps from newer gateway versions may include additional files. Index all files found.

### Key Fields to Read Per Resource

- `metadata.name` — resource identity
- `metadata.namespace` — resource scope (`default`, `gateway`, or environment UUID)
- `metadata.labels["flex.mulesoft.com/deployment-desired-status"]` — on ApiInstances: `STARTED` or `STOPPED`
- `spec` — the live deployed configuration
- `status.conditions` — `[{type: "Ready", status: "True|False"}]` indicates operational state

### Sample Resource Structure

An ApiInstance has:
```json
{
  "apiVersion": "gateway.mulesoft.com/v1beta1",
  "kind": "ApiInstance",
  "metadata": {
    "name": "apii-4808971-flex-test-api",
    "namespace": "676c8822-4ae3-44c2-afd8-df46ae69f202",
    "labels": {
      "flex.mulesoft.com/apiinstance-id": "4808971",
      "flex.mulesoft.com/apiinstance-name": "flex-test-api",
      "flex.mulesoft.com/deployment-desired-status": "STARTED"
    }
  },
  "spec": {
    "address": "http://0.0.0.0:8081/",
    "policies": [...]
  },
  "status": {
    "conditions": [{"type": "Ready", "status": "True"}]
  }
}
```

A PolicyBinding has:
```json
{
  "apiVersion": "gateway.mulesoft.com/v1alpha1",
  "kind": "PolicyBinding",
  "metadata": {"name": "internal-pe-env-api-context", "namespace": "default"},
  "spec": {
    "targetRef": {"kind": "Selector", "selector": {"kind": "ApiInstance"}},
    "policyRef": {"name": "api-context"}
  },
  "status": {"conditions": [{"type": "Ready", "status": "True"}]}
}
```

A Configuration entry (for registration):
```json
{
  "apiVersion": "gateway.mulesoft.com/v1alpha1",
  "kind": "Configuration",
  "metadata": {"name": "registration"},
  "spec": {
    "platformConnection": {
      "agentId": "3710bdd7-...",
      "anypoint": "https://anypoint.mulesoft.com",
      "assetName": "flex1"
    }
  }
}
```

## Analysis Checklist

### Step 1 — Unzip and index

Extract the dump and list all files:

```bash
unzip dump.zip -d dump-analysis/
ls -la dump-analysis/dump/
```

For each JSON file, count the resources and record in a table:

| File | Resource Count | Notes |
|------|---------------|-------|
| api-instances.json | | |
| policy-bindings.json | | |
| services.json | | |
| configurations.json | | |
| extensions.json | | Skip unless investigating a specific policy |
| control-node-storage.json | — | Agent ID only |

If additional files are present, note them in a "Other files" section.

Also record gateway metadata from:
- **Agent ID:** `control-node-storage.json` → `store` value
- **Platform connection:** `configurations.json` → resource with `metadata.name: registration` → `spec.platformConnection.anypoint`, `spec.platformConnection.assetName`
- **Dump timestamp:** ZIP filename (format: `dump-<timestamp>.zip`)

### Step 2 — Build resource inventory

Read all resources from `api-instances.json`, `policy-bindings.json`, `services.json`, and `configurations.json`. For each, produce a comprehensive table:

| Kind | Name | Namespace | Ready Status | Desired Status | Notes |
|------|------|-----------|--------------|---|---------|

Populate columns:
- **Ready Status:** Extract from `status.conditions[type="Ready"].status`. If absent, mark as `Unknown`.
- **Desired Status:** For ApiInstances, extract from `metadata.labels["flex.mulesoft.com/deployment-desired-status"]`. For other resources, leave blank.
- **Notes:** Any critical field values, label context, or anomalies observed.

Sort by resource kind, then by namespace, then by name for readability.

### Step 3 — Cross-reference PolicyBindings → ApiInstances

For each PolicyBinding in the inventory:

1. Check the `spec.targetRef` field:
   - **If `kind: ApiInstance` with `name`:** Verify that `name` exactly matches an ApiInstance in `api-instances.json`. If no match, flag as **orphaned** (the policy references a non-existent API instance and will silently not apply).
   - **If `kind: Selector` with `selector.kind: ApiInstance`:** The policy is global and applies to all ApiInstances. This is valid; note it in the table but do not flag as an error.
   - **If `kind` is something else or `targetRef` is malformed:** Flag as **malformed**.

2. For each orphaned or malformed PolicyBinding, record:
   - PolicyBinding name
   - Reason (e.g., "targetRef.name 'xyz' does not match any ApiInstance")

### Step 4 — Cross-reference Services → ApiInstances

For each Service in `services.json`:

1. **System services** (namespace `x-flex-internal` or label `managed-by: flex-static`) are internal gateway resources. Do not flag as potentially unused.

2. **User-defined services** (namespace `gateway`, `default`, or an environment UUID):
   - Check if the Service name is referenced in any ApiInstance under `spec.services` or in any PolicyBinding.
   - If not referenced by any ApiInstance or PolicyBinding, mark as **potentially unused** (may be a leftover from a previous deployment).

3. Record any potentially unused Services:
   - Service name
   - Namespace
   - Last reference check result

### Step 5 — Identify anomalies

Scan all resources for health and consistency issues:

**Critical issues (block API execution):**
- Resources with `status.conditions[type="Ready"].status: False` — extract the condition message if present.
- ApiInstances missing `spec.address` or with an invalid address format.
- PolicyBindings missing `spec.targetRef` or `spec.policyRef`.
- PolicyBindings with a non-existent `policyRef.name` (the referenced policy definition does not exist in `extensions.json` or is not available).

**Warning issues (may indicate configuration drift):**
- ApiInstances with `metadata.labels["flex.mulesoft.com/deployment-desired-status"]: STOPPED` but `status.conditions[type="Ready"].status: True` (desired != actual).
- Resources with missing `metadata.namespace` or `metadata.labels`.
- JSON parse errors during extraction (indicates a corrupt or incomplete dump).

### Step 6 — Compare against conf.d (if provided)

If the user also provides their `conf.d/` directory or local configuration files:

1. **Index local files:** Parse all YAML or JSON files in `conf.d/` and extract resource names, kinds, and namespaces.

2. **In dump but not in conf.d:** Resource exists in the live gateway dump but not in the user's local configuration. Possible causes:
   - Resource is managed by the control plane (connected mode deployment).
   - Resource is a stale deployment that was not removed from the gateway.
   - User's local conf.d is out of sync with the deployed version.

3. **In conf.d but not in dump:** Resource is configured locally but not present in the live dump. Possible causes:
   - File has a syntax error and was rejected at deploy time.
   - Gateway crashed or was restarted before persisting the resource.
   - Resource was manually deleted from the gateway after initial deployment.

4. Record mismatches:
   - Filename/resource name
   - Kind
   - Status (in dump only / in conf.d only)

### Step 7 — Produce dump analysis report

Structure your findings as follows:

```
# Gateway Dump Analysis Report

**Dump file:** [filename]
**Captured:** [timestamp or datetime]
**Gateway agent ID:** [agentId from control-node-storage.json]

## Gateway Registration

- **Platform URL:** [from configurations.json spec.platformConnection.anypoint]
- **Asset name:** [from configurations.json spec.platformConnection.assetName]

## Resource Inventory

[Table from Step 2]

## Anomalies

### Critical Issues (Ready: False or Malformed)

[List each resource with its Ready status and condition message, or "None found"]

Example:
- **ApiInstance `apii-123-api`** (namespace `env-456`): Ready=False, condition: "Pod failed to start: OOMKilled"
- **PolicyBinding `rate-limit-binding`**: malformed targetRef, references non-existent ApiInstance `apii-999-api`

### Orphaned PolicyBindings

[List each PolicyBinding that references a non-existent ApiInstance, or "None found"]

Example:
- **PolicyBinding `deprecated-policy`** targets ApiInstance `apii-old-deployment` which does not exist in the dump

### Potentially Unused Services

[List each Service not referenced by any ApiInstance or PolicyBinding, or "None found"]

Example:
- **Service `backend-cache`** (namespace `gateway`): not referenced by any ApiInstance

### Configuration Drift (conf.d vs. dump)

[If conf.d was provided, show mismatches. Otherwise, note "No local configuration provided for comparison."]

Example:
- **In dump only:** `configurations.json` entries not in local conf.d (possible control-plane managed resources)
- **In conf.d only:** `api-instances.yaml` entries not in dump (possible file not deployed)

## Escalation Recommendation

- **No anomalies:** Gateway state appears healthy at the time of dump capture. No immediate action required.
- **Warnings present:** Configuration drift or unused resources detected. Recommend reviewing the "Potentially Unused Services" and "Configuration Drift" sections. Reconcile local conf.d with dump state.
- **Critical issues present:** Ready=False resources or orphaned bindings indicate active problems. Immediate escalation recommended. Provide this dump and the gateway logs (see `omni-gateway-logs` skill) to support.
```

## Related Skills

- **omni-gateway-diagnose** — Start here if you have an error symptom and need to decide what to investigate.
- **omni-gateway-logs** — Pair with the dump to correlate live state against log errors and trace request flows.
- **omni-gateway-config** — Compare the local `conf.d/` configuration against this dump to identify drift or missing deployments.

## Tips for Effective Dump Analysis

1. **Start with anomalies:** If the report shows no critical issues, the gateway state was likely stable at capture time. Focus on warnings and drift.
2. **Use timestamps:** Compare dump timestamp with error logs. Errors after the dump timestamp are new; errors before indicate pre-existing issues.
3. **Check namespaces:** Resources in different namespaces may be intentional (environment isolation). Do not assume all namespaces are equivalent.
4. **PolicyBinding selectors:** Global policies (Selector + ApiInstance) apply to all APIs. Verify that the intended policy is actually configured correctly.
5. **Extensions file:** Only inspect `extensions.json` if investigating a specific policy definition or if policy bindings reference undefined policies. The file is often large and can be skipped for routine analysis.
6. **Agent ID:** If the agent ID in the dump does not match the expected gateway agent in your Anypoint environment, the dump may be from a different gateway or a stale backup.
