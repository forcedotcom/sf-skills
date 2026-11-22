---
name: omni-gateway-config
description: |
  Read and validate YAML configuration files in an Omni Gateway conf.d directory.
  Use when a gateway returns unexpected 4xx/5xx errors after a config change and
  the user suspects a misconfiguration; when a new PolicyBinding or ApiInstance
  was added and is silently not taking effect; when conf.d files were edited
  manually and the user wants to catch errors before restarting the gateway; or
  when omni-gateway-diagnose determines that conf.d is the likely root cause.
---

# Validate Gateway Config

## Config Format Reference

Gateway configuration lives in:
- **Linux (systemd):** `/usr/local/share/mulesoft/flex-gateway/conf.d/`
- **Docker:** Host path mounted with `-v <host-path>:/usr/local/share/mulesoft/flex-gateway/conf.d`
- **Kubernetes:** ConfigMap or PV mounted at the same internal path

Each file may contain one or more `---`-separated YAML documents. A single `.yaml` file
containing multiple resources is just as valid as one resource per file.

### Valid apiVersions

| apiVersion | When to use |
|------------|-------------|
| `gateway.mulesoft.com/v1alpha1` | All stable kinds (ApiInstance, PolicyBinding, Service, Configuration, Extension, Secret, Contract) |
| `gateway.mulesoft.com/v1beta1` | Newer Configuration sub-kinds: `circuitBreaker`, `tracing` |

Any other value (including absent, `v1`, or misspelled) causes the resource to be silently ignored by the gateway.

### Resource Kinds

| Kind | Purpose |
|------|---------|
| `ApiInstance` | A proxied API: listen address, optional inline services+routes, optional inline policies |
| `PolicyBinding` | Attaches a policy (Extension or built-in) to an ApiInstance or Service |
| `Service` | An upstream backend service (address only) |
| `Configuration` | Global gateway settings — exactly one sub-kind per resource |
| `Extension` | A policy implementation; wraps an `envoy-filter` or extends another Extension |
| `Secret` | TLS certificate and key material (base64-encoded) |
| `Contract` | Client contract: clientId/secret + SLA rate limits |

### `ApiInstance` Fields

Required:
- `metadata.name`
- `spec.address` — the listen address; must use `http://` or `https://` scheme

`metadata.namespace` is optional. When present, the value is user-defined — it is **not** required to equal `gateway`.

`metadata.labels` is optional. Connected-mode gateways often set `"mulesoft.com/apiInstanceId": "<id>"`.

**Routing style A — inline services (self-contained):**
```yaml
spec:
  address: http://0.0.0.0:8080
  services:
    upstream:
      address: https://httpbin.org:443
      routes:
        - rules:
            - path: /api(/.*) 
```

**Routing style B — standalone Service + route PolicyBinding:**
```yaml
# ApiInstance (no services block)
spec:
  address: http://0.0.0.0:8080
---
# Separate Service resource
kind: Service
spec:
  address: https://httpbin.org:443
---
# Route PolicyBinding wires them together
kind: PolicyBinding
spec:
  targetRef:
    name: my-api
  policyRef:
    name: route
  config:
    destinationRef:
      name: httpbin
```

Both styles are valid. They may not be mixed on the same `ApiInstance`.

**Inline policy attachment** (optional, alternative to standalone PolicyBindings):
```yaml
spec:
  address: http://0.0.0.0:8080
  policies:
    - policyRef:
        name: auth
    - policyRef:
        name: xss-protection
      rules:
        - path: /secure(/.*) 
```

### `PolicyBinding` Fields

Required:
- `metadata.name`
- `spec.targetRef.name`
- `spec.policyRef.name`

Optional:
- `spec.targetRef.kind` — defaults to `ApiInstance`. Use `Service` for outbound policies (e.g., credential injection, idle timeout applied to an upstream).
- `spec.policyRef.kind` — defaults to `Extension` when omitted.
- `spec.config` — policy-specific configuration object.
- `spec.order` — integer; lower = earlier execution. Controls ordering when multiple bindings target the same ApiInstance.
- `spec.rules[]` — path/method conditions to scope this binding to a subset of requests.

Example outbound (Service-targeted) PolicyBinding:
```yaml
kind: PolicyBinding
spec:
  targetRef:
    kind: Service
    name: httpbin
  policyRef:
    name: idle-timeout-flex
  config:
    timeout: 1
```

### `Service` Fields

Required:
- `metadata.name`
- `spec.address` — the upstream URL

Address scheme rules:
- `http://` — standard HTTP cleartext
- `https://<host>:<port>` — HTTPS; port must be explicit (e.g., `:443`)
- `h2://<host>:<port>` — gRPC over HTTP/2 cleartext; port must be explicit

### `Configuration` Sub-Kinds

Each `Configuration` resource must contain **exactly one** of these sub-keys under `spec`:

| Sub-key | Purpose | Required apiVersion |
|---------|---------|---------------------|
| `logging` | Log outputs, runtime log level, access log routing | v1alpha1 |
| `forwardProxy` | Outbound HTTP/HTTPS proxy settings | v1alpha1 |
| `defaultTLS` | Outbound TLS version, ciphers, trusted CA | v1alpha1 |
| `sharedStorage` | Redis connection (standalone or Sentinel) | v1alpha1 |
| `resourceLimits` | Max apiInstances and policies the gateway will load | v1alpha1 |
| `circuitBreaker` | Connection pool thresholds | **v1beta1** |
| `tracing` | Distributed tracing provider | **v1beta1** |

Example `logging` Configuration:
```yaml
apiVersion: gateway.mulesoft.com/v1alpha1
kind: Configuration
metadata:
  name: logging
spec:
  logging:
    outputs:
      - name: default
        type: file
        parameters:
          file: /dev/stdout
    runtimeLogs:
      logLevel: info
      outputs:
        - default
    accessLogs:
      outputs:
        - default
```

Example `sharedStorage` Configuration:
```yaml
apiVersion: gateway.mulesoft.com/v1alpha1
kind: Configuration
metadata:
  name: shared-storage
spec:
  sharedStorage:
    redis:
      address: redis.internal:6379
      password: secret
```

### `Extension` Fields

Required:
- `metadata.name`
- `spec.extends[]` — list of `{name: <extension-or-filter-name>}` references

### `Secret` Fields

Required:
- `metadata.name`
- `spec.tls.crt` — base64-encoded certificate
- `spec.tls.key` — base64-encoded private key

### `Contract` Fields

Required:
- `metadata.name`
- `spec.apiId` — must match an `ApiInstance.metadata.name`
- `spec.client.id` and `spec.client.secret`

Optional:
- `spec.sla` — SLA tier name and rate limit rules

---

## Validation Checklist

### Step 1 — Parse and inventory all documents

- Read all `.yaml` / `.yml` files in `conf.d/`. Each file may contain multiple `---`-separated documents.
- For each document: extract `apiVersion`, `kind`, `metadata.name`, `metadata.namespace` (if present).
- Report a flat inventory table across all documents:

| File | Doc # | apiVersion | Kind | Name | Namespace | Parseable |
|------|-------|------------|------|------|-----------|-----------|
| `my-api.yaml` | 1 | v1alpha1 | ApiInstance | my-api | — | ✅ |
| `my-api.yaml` | 2 | v1alpha1 | PolicyBinding | my-route | — | ✅ |
| `broken.yaml` | 1 | — | — | — | — | ❌ |

If a document cannot be parsed, flag it immediately as corrupt and skip further checks for that document.

### Step 2 — Per-resource structural validation

For each document:

1. **apiVersion** must be `gateway.mulesoft.com/v1alpha1` or `gateway.mulesoft.com/v1beta1`. Absent or any other value = **hard error**.
2. **kind** must be one of the 7 known kinds. Unknown kind = warning (may be a future CRD or a typo).
3. **`metadata.name`** must be present and non-empty.
4. **Required fields per kind** must be present (see Config Format Reference above).
5. **Configuration**: exactly one sub-key must exist under `spec`. Zero or multiple sub-keys = **hard error**.
6. **`circuitBreaker` / `tracing` Configuration**: must use `v1beta1` — using `v1alpha1` for these = **hard error**.

### Step 3 — ApiInstance routing style check

For each `ApiInstance`:

1. Determine routing style: **inline** (has `spec.services`) vs **standalone** (no `spec.services`; relies on a separate `Service` + `route` PolicyBinding).
2. If **inline**: each `spec.services.<name>` must have an `address` field.
3. If inline with `routes`: `routes[].rules[].path` should be a non-empty string.
4. If `spec.address` binds to `localhost` instead of `0.0.0.0`: **flag as misconfiguration** — gateway is only reachable from within the same host/container.
5. If `spec.address` uses `https://`: note that TLS termination requires a TLS `PolicyBinding` referencing a `Secret` or an `Extension` with TLS configuration.
6. If `spec.policies[]` is present: note whether the same `ApiInstance` also has standalone `PolicyBindings` targeting it — both are valid, but note the coexistence so the user understands combined ordering.

### Step 4 — Cross-reference checks

**4a. PolicyBinding target exists:**
- If `targetRef.kind` is `ApiInstance` or absent: `targetRef.name` must match an `ApiInstance.metadata.name` in conf.d.
- If `targetRef.kind` is `Service`: `targetRef.name` must match a `Service.metadata.name` in conf.d.
- Unmatched = **orphaned PolicyBinding** → policy silently not applied at runtime.

**4b. PolicyBinding policy reference:**
- `policyRef.name` should match an `Extension.metadata.name` in conf.d or be a known built-in.
- Known built-ins include: `route`, `route-weighted`, `tls`, `idle-timeout-flex`, `rate-limiting-flex`, `access-log`.
- Unknown policy name = warning (may be provided by the installed gateway version; not necessarily broken).

**4c. Port conflicts:**
- No two `ApiInstance` resources may bind the same port in `spec.address` *unless* they use different base paths (e.g., `0.0.0.0:8080/api/a` and `0.0.0.0:8080/api/b`).
- Same port + same or no path = **hard error** (bind failure at runtime).

**4d. Contract → ApiInstance:**
- `Contract.spec.apiId` must match an `ApiInstance.metadata.name`. Unmatched = hard error.

**4e. Extension chain:**
- `Extension.spec.extends[].name` should resolve to another `Extension` in conf.d or a known built-in filter.
- Unresolved chain = warning.

### Step 5 — Service address checks

For each `Service` resource and each inline `spec.services.<name>.address`:

1. **HTTPS without explicit port:** `https://hostname` without a port = warning (Envoy defaults to `:443` but omitting it is error-prone across gateway versions).
2. **gRPC (`h2://`) upstream:** If this service is used by an `ApiInstance` that does not appear to have gRPC-aware configuration, add a note that the upstream expects HTTP/2 cleartext.
3. **`localhost` upstream:** Works only in Docker/same-host deployments where both the gateway and backend run in the same network namespace. Flag with a contextual note.

### Step 6 — Configuration sub-kind checks

For each `Configuration` resource, apply sub-kind-specific checks:

- **`sharedStorage.redis.address`:** must be `host:port` format. Missing port = warning.
- **`defaultTLS.outboundPolicyCalls.minVersion` / `maxVersion`:** Valid values are `"1.0"`, `"1.1"`, `"1.2"`, `"1.3"`. Warn if `minVersion` is below `"1.2"` (weak TLS).
- **`logging.runtimeLogs.logLevel`:** Valid values are `debug`, `info`, `warn`, `error`, `fatal`. Warn if `debug` in a production context (performance impact).
- **`forwardProxy` with `basicAuth`:** credentials are in plaintext in the file — warn and recommend using a `Secret` resource or environment variable injection.

### Step 7 — Output format

Produce a structured validation report:

```
## Gateway Config Validation Report

### File Inventory
<table from Step 1>

### Structural Issues
<issues from Step 2, by file/doc, or "None found">

### Routing & Policy Issues
<issues from Steps 3–4, or "None found">

### Service Address Issues
<issues from Step 5, or "None found">

### Configuration Issues
<issues from Step 6, or "None found">

### Recommended Fixes
<numbered list, highest-impact first>

### Overall Status
✅ Config appears valid — ready to deploy.
  — OR —
❌ N hard error(s), M warning(s) found.
   Hard errors must be fixed before deploying.
   Warnings are safe to deploy but should be reviewed.
```

---

## Known Misconfigurations Reference

| Misconfiguration | Detection | Severity | Impact |
|-----------------|-----------|----------|--------|
| `spec.address` uses `localhost` (ApiInstance) | String match | **Error** | Gateway unreachable externally |
| `spec.address` uses `localhost` (Service) | String match | Warning | Works only in same-host deployments |
| Missing `apiVersion` | Field absent | **Error** | Resource silently ignored by gateway |
| Wrong `apiVersion` (e.g., `v1`, `v2alpha1`) | String match | **Error** | Resource silently ignored by gateway |
| `circuitBreaker`/`tracing` using `v1alpha1` | Version+kind match | **Error** | Feature not recognized |
| Orphaned PolicyBinding (targetRef not found) | Cross-reference | **Error** | Policy silently not applied |
| Two ApiInstances on same port, no path difference | Duplicate check | **Error** | Bind failure at runtime |
| `Configuration` with zero sub-keys | Field check | **Error** | No-op configuration |
| `Configuration` with multiple sub-keys | Field check | **Error** | Undefined behavior |
| `Contract.spec.apiId` not matching any ApiInstance | Cross-reference | **Error** | Contract never enforced |
| HTTPS Service address missing port | Regex match | Warning | Brittle — varies by gateway version |
| `Secret` with non-base64 values | Heuristic check | Warning | TLS initialization failure |
| Plaintext credentials in `forwardProxy.basicAuth` | Field presence | Warning | Credentials stored in version control |
| `debug` log level in `Configuration` | Value check | Warning | Performance impact in production |

---

## Related Jobs

- `omni-gateway-diagnose` — end-to-end triage when errors are already happening; invokes this skill when conf.d is available
- `omni-gateway-logs` — read gateway logs to correlate config issues with runtime errors
- `omni-gateway-install` — if the registration YAML in conf.d appears malformed, re-run the registration steps
