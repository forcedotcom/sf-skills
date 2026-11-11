---
name: omni-gateway-logs
description: |
  Parse and interpret Omni Gateway log output to surface errors, warnings, and
  anomalies. Use when the user shares gateway logs and wants to understand what
  went wrong, identify upstream connectivity failures, find TLS or authentication
  errors, diagnose policy evaluation problems, or get a structured summary of
  log activity with recommended next steps.
---

# Inspect Gateway Logs

## Log Format Reference

Omni Gateway produces logs in two formats depending on the deployment platform.

### Docker format

```
[component][level] message
```

Examples:

```
[flex-gateway-agent][info] Running Envoy XDS Service...
[flex-gateway-agent][error] Error authorizing https://anypoint.mulesoft.com: Post "https://anypoint.mulesoft.com/accounts/oauth2/token": dial tcp 54.173.213.129:443: connect: connection timed out
[flex-gateway-envoy][info] all dependencies initialized. starting workers
[flex-external-processor][info] Ext Proc Server successfully started.
[flex-gateway-agent][warn] Registration is using v1 version, but some metrics are only supported for v2. Please renew your registration to avoid errors.
```

### Kubernetes format (structured)

```
<ISO-timestamp> LEVEL [pod-name] component - message
```

Examples:

```
2026-02-26T22:56:56.935Z INFO [pbtest1-766cbd68f9-g2r7n] flex-gateway-agent - Running Envoy XDS Service...
2026-02-26T23:01:13.53Z ERROR [pbtest1-766cbd68f9-g2r7n] flex-gateway-agent - Error authorizing https://stgx.anypoint.mulesoft.com: Post "https://anypoint.mulesoft.com/accounts/oauth2/token": dial tcp 54.173.213.129:443: connect: connection timed out
2026-02-26T22:56:57.447Z INFO [pbtest1-766cbd68f9-g2r7n] flex-gateway-agent - Creating gateway
```

In Kubernetes, multiple pods appear in the same log stream; each line includes the pod name in brackets.

### Component glossary


| Component                  | What it does                                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `flex-gateway-agent`       | Main agent: gateway lifecycle, registration with Anypoint, config management, token refresh, control-plane sync |
| `flex-gateway-envoy`       | Envoy proxy: HTTP/HTTPS/gRPC routing, TLS termination, upstream connections, xDS config consumer                |
| `flex-gateway-fluent`      | Fluent Bit: log collection and forwarding                                                                       |
| `flex-external-processor`  | External processor (Java): handles external-processing policies                                                 |
| `open-telemetry-collector` | OpenTelemetry collector: metrics and tracing export                                                             |


## Normal Startup Sequence

A healthy gateway startup produces these INFO messages in order. Use this as a reference to identify where startup stalled:

```
Running Envoy XDS Service...
RTMDataSource: Starting
KubernetesDataSource: Starting          ← Kubernetes only
Creating gateway
Processing commands
Validating gateway
Generating config
Gateway: Platform=... Mode=connected ReplicaName=...
Writing envoy bootstrap configuration to /var/tmp/mulesoft/flex-gateway/envoy.json
RTMDataSource: Change configuration
flex-gateway-envoy: Starting
flex-gateway-fluent: Starting
flex-external-processor: Starting
all dependencies initialized. starting workers     ← from flex-gateway-envoy
Anypoint websocket: connected                       ← connected mode only
open delta watch ID:1 for ...Cluster...             ← xDS subscriptions active
open delta watch ID:2 for ...Listener...
```

If the log cuts off before `all dependencies initialized. starting workers`, the gateway did not finish starting.

## How to Obtain Logs

### Linux (systemd)

```bash
# View last 200 log lines
sudo journalctl -u flex-gateway -n 200 --no-pager

# Stream logs in real-time
sudo journalctl -u flex-gateway -f

# View logs within a time window
sudo journalctl -u flex-gateway --since "2026-06-08 14:00:00" --until "2026-06-08 15:00:00"
```

### Docker

```bash
# View last 200 log lines
docker logs --tail=200 flex-gateway

# Stream logs in real-time
docker logs -f flex-gateway

# View logs with timestamps
docker logs --timestamps flex-gateway
```

### Kubernetes

Replace `<namespace>` and `<pod-name>` with the values from your cluster. If you don't know the pod name, list pods first.

```bash
# Find gateway pods
kubectl get pods -n <namespace> -l app.kubernetes.io/name=flex-gateway

# View logs from a specific pod
kubectl logs -n <namespace> <pod-name> --tail=200

# View logs from all gateway pods
kubectl logs -n <namespace> -l app.kubernetes.io/name=flex-gateway --all-containers=true --tail=100

# View logs from a previous (crashed) pod instance
kubectl logs -n <namespace> <pod-name> --previous

# Stream logs in real-time
kubectl logs -n <namespace> <pod-name> -f
```

## How to Enable Debug Logging

To enable debug-level logs, create a Configuration resource in the user conf.d directory.

Create or edit `/usr/local/share/mulesoft/flex-gateway/conf.d/logging.yaml`:

```yaml
apiVersion: gateway.mulesoft.com/v1alpha1
kind: Configuration
metadata:
  name: logging
spec:
  logging:
    runtimeLogs:
      logLevel: debug
```

On Kubernetes, add this as a ConfigMap entry mounted into the conf.d volume. The gateway picks up the change without a restart.

To revert to INFO logging, change `logLevel` to `info` or delete the Configuration resource.

**Note:** There is no `flexctl` command to enable debug logging. The Configuration YAML is the only supported method and works identically in connected and local modes.

## Analysis Checklist

### Step 1 — Parse by severity

Count occurrences of each severity level. Use these keywords:

- **Docker:** `][error]`, `][warn]`, `][info]`, `][debug]`
- **Kubernetes:** `ERROR`, `WARN`, `INFO`, `DEBUG`

**Decision logic:**

- Zero `error` lines and few `warn` lines → gateway is likely healthy. Report the baseline and stop unless the user is investigating a specific problem.
- Any `error` lines present, or the user reports an issue → continue to Steps 2–4.

### Step 2 — Identify components

Group error and warning lines by their component prefix:

- `**flex-gateway-agent` errors** → registration failures, token refresh failures, Anypoint connectivity, lifecycle issues, config processing errors
- `**flex-gateway-envoy` errors** → upstream connectivity, TLS, routing, or xDS config issues
- `**flex-external-processor` errors** → policy execution failures (DataWeave, LDAP, ext-proc policies)
- `**flex-gateway-fluent` errors** → log forwarding failures (non-critical for gateway traffic)
- `**open-telemetry-collector` errors** → metrics/tracing export failures (non-critical for gateway traffic)

Note which components are generating errors and at what point in the lifecycle.

### Step 3 — Deduplicate repeated errors

Identical or structurally similar error messages often repeat many times. Collapse these into a single entry with a count:

- Instead of: "Error authorizing [https://anypoint.mulesoft.com](https://anypoint.mulesoft.com)" repeated 14 times
- Report: "**14× `flex-gateway-agent`**: `Error authorizing https://anypoint.mulesoft.com: ... connection timed out`"

This separates signal from noise and makes the analysis readable.

### Step 4 — Check for known failure patterns

Match errors and warnings against this table:


| Log pattern                                                                                                                     | Severity                 | Likely cause                                                                                                                      | Next step                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Error authorizing https://*.anypoint.mulesoft.com: ... connect: connection timed out`                                          | ERROR                    | Gateway cannot reach Anypoint OAuth endpoint to refresh its token                                                                 | Check network/firewall rules: the gateway must be able to reach `anypoint.mulesoft.com` (or the appropriate region endpoint) on port 443; verify egress rules from the pod/host |
| `Max retries reached for token authorization: ...`                                                                              | ERROR                    | Sustained failure to refresh the Anypoint OAuth token; gateway is now disconnected from the control plane                         | Immediate: restore connectivity to `anypoint.mulesoft.com`; gateway continues serving cached config but won't receive updates                                                   |
| `Processing commands errors: (Ingress .../...: the resource is not allowed in connected mode)`                                  | ERROR                    | A Kubernetes `Ingress` resource is present but the gateway is running in connected mode — Ingress is only supported in local mode | Remove the `Ingress` resource; in connected mode, use `ApiInstance` resources managed via Anypoint Runtime Manager instead                                                      |
| `Registration is using v1 version, but some metrics are only supported for v2. Please renew your registration to avoid errors.` | WARN                     | Registration was created with an older version of `flexctl`                                                                       | Re-register the gateway using the current `flexctl register` command; invoke `omni-gateway-install` skill (registration steps)                                                                           |
| `MetricsScheduler: flex_startup event error: ... connect: connection timed out`                                                 | WARN                     | Cannot report startup metrics to Anypoint (non-critical: gateway traffic is unaffected)                                           | Check Anypoint connectivity; analytics events will be missing for this startup                                                                                                  |
| `MetricsScheduler: flex_snapshot event error: ... connect: connection timed out`                                                | WARN                     | Cannot report periodic metrics to Anypoint (non-critical: gateway traffic is unaffected)                                          | Check Anypoint connectivity; analytics data will have gaps                                                                                                                      |
| `upstream connect error or disconnect/reset before headers`                                                                     | ERROR (Envoy access log) | Upstream service not reachable or closed connection                                                                               | Verify the `spec.services[*].address` in the ApiInstance; confirm upstream is running and accepting connections                                                                 |
| `TLS handshake failed` / `certificate verify failed` / `CERTIFICATE_VERIFY_FAILED`                                              | ERROR                    | TLS misconfiguration, expired certificate, or incomplete certificate chain                                                        | Check certificate validity and expiration; review TLS config in conf.d                                                                                                          |
| `Deprecated field: type envoy.config.cluster.v3.Cluster Using deprecated option ... http2_protocol_options`                     | WARNING (Envoy)          | Envoy using a deprecated internal config field                                                                                    | **Expected and harmless** — known issue in current Omni Gateway versions; ignore unless other problems are present                                                              |
| `Token expiring soon (in ...)`                                                                                                  | INFO                     | Normal Anypoint OAuth token refresh cycle                                                                                         | **Expected and normal** — gateway is proactively refreshing its token; not an error                                                                                             |


### Step 5 — If logs are truncated or incomplete

If the log excerpt is cut off or covers too short a window:

1. Ask the user: when did the issue start? Request a longer window (e.g., last 1000 lines or last hour).
2. Provide the appropriate streaming or time-scoped command for their platform (see "How to Obtain Logs" above).
3. If there was a triggering event (deployment, config change, restart, traffic spike), ask the user to anchor it with a timestamp so you can focus on that window.

### Step 6 — If errors are sparse or the cause is unclear

If the logs contain few errors but the user reports a problem:

1. Enable debug logging using the Configuration YAML method above.
2. Ask the user to reproduce the failing request or wait for the issue to recur.
3. Re-collect logs using the appropriate platform command.
4. Return to Step 1 with the verbose logs.

Debug logs reveal timing issues, intermediate state transitions, token refresh details, and policy evaluation steps that INFO logs omit.

### Step 7 — Produce structured summary

Output a structured analysis block:

```
## Log Analysis Summary

Period: <start timestamp> – <end timestamp> (or "unknown" if timestamps absent)
Total lines analyzed: <N>
Log level: <INFO / DEBUG / TRACE / mixed>
Platform: <Docker / Kubernetes / Linux>
Mode: <connected / local / unknown>

### Severity Counts
- ERROR: N
- WARN: N
- INFO: N
- DEBUG/TRACE: N

### Component Breakdown
- `flex-gateway-agent`: N lines, X errors
- `flex-gateway-envoy`: N lines, X errors
- `flex-external-processor`: N lines, X errors
- `flex-gateway-fluent`: N lines, X errors
- `open-telemetry-collector`: N lines, X errors

### Top Issues (deduplicated)
1. [Nx flex-gateway-agent] Error authorizing ... connection timed out — hypothesis
2. [Nx flex-gateway-agent] Processing commands errors: Ingress ... — hypothesis
3. ...

### Startup Completion
Gateway reached "all dependencies initialized" / "Anypoint websocket: connected": YES / NO / UNKNOWN

### Root Cause Hypothesis
<One or two sentences on the likely root cause based on patterns and timeline.>

### Recommended Next Steps
1. <Specific action, e.g., "Check egress firewall rules: gateway needs port 443 access to anypoint.mulesoft.com">
2. <Specific action, e.g., "Run `omni-gateway-config` — error suggests an Ingress resource is present">
3. <Specific action, e.g., "Re-register the gateway with current flexctl to upgrade from v1 registration">
```

## Related Jobs

- `**omni-gateway-diagnose**` — End-to-end triage router when you need to decide which investigation path to take.
- `**omni-gateway-config**` — When analysis points to a configuration issue in conf.d.
- `**omni-gateway-install**` — When logs show the gateway failed to register, lost control-plane connection, or has a v1 registration warning (re-run the registration steps).

