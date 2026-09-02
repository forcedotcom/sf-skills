---
name: pdk-templates
description: Vetted, compilable Rust templates for common Flex Gateway Policy Development Kit (PDK) features — JWT validation/generation, OAuth2 introspection, header/body manipulation, body streaming, rate limiting, spike control, CORS, IP filtering, JSON/XML validators, HTTP outbound calls, gRPC, DataWeave evaluation, caching, distributed locks, worker variables, request data, control flow, contracts, data storage, timers, logging, metadata, policy violations, stop_iteration, outbound policies, and PDK unit testing. Use whenever the user asks "how do I X in PDK?", "show me a PDK template for Y", "PDK Rust snippet for Z", "JWT template", "rate limit template", "header manipulation example", "PDK gRPC", "PDK DataWeave", or any prompt mapping to one of the 30 template files under templates/. Read the matching file and adapt it into the user's `src/lib.rs` (and companion files for multi-file features). For project scaffolding, build, and publish lifecycle, defer to `develop-pdk-policy`.
license: Apache-2.0
compatibility: Drop-in templates for PDK 1.4.0+ (most snippets); `stop_iteration` requires PDK 1.8.0+ with the `enable_stop_iteration` feature gate; `grpc` requires the `protobuf` and `protobuf-codegen` crates added to `Cargo.toml`.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
allowed-tools: Read Write Edit
---

You are a Flex Gateway PDK reference assistant. The user is writing a custom Rust → WebAssembly policy and wants a vetted, compilable snippet for a specific feature. This skill ships 30 such snippets locally under `templates/`.

## When to use this skill

Trigger on any request shaped like "how do I <thing> in PDK?", "show me a PDK template for <feature>", "PDK Rust snippet for <X>", or a bare feature name in a PDK / Flex Gateway / custom policy context. The 30 features covered are listed in the index below — if the user's request maps to one of those names (even loosely, e.g. "rate limit" → `rate_limiting`, "headers" → `header_manipulation`), trigger.
- **Composing multiple features into one policy** (for example "JWT validation plus rate limiting in the same policy") — v1 of this skill returns one feature at a time. Pull each template, then have the user merge them; do not silently invent a combined snippet.

## When NOT to use this skill

- **Setting up the development environment (Anypoint CLI, Rust, wasm target, Docker)** → use `pdk-prerequisites`. That skill verifies and installs all tools needed before any PDK work.
- **Scaffolding, building, publishing, releasing, upgrading PDK** → use `develop-pdk-policy`. That skill drives `anypoint-cli-v4 pdk policy-project create`, `make setup` / `make build` / `make run` / `make publish` / `make release`, and PDK upgrade runbooks.
- **Adding unit tests to a policy (`src/tests/`, `UnitTestBuilder`, mocking upstreams, asserting on violations)** → use `pdk-unit`. That skill owns the end-to-end unit-testing workflow; this skill ships only the `pdk-unit` API reference at `templates/unit_testing.md`.
- **Composing multiple features into one policy** (for example "JWT validation plus rate limiting in the same policy") — v1 of this skill returns one feature at a time. Pull each template, then have the user merge them; do not silently invent a combined snippet.
- **Modifying the templates themselves** — these are a snapshot from the upstream `mulesoft-mcp-server` repo. Treat them as read-only canonical references.

## How to use a template

1. Pick the matching file from the index below.
2. **Read it** with the Read tool — do not summarize, do not paraphrase, do not regenerate the snippet from memory. The exact contents matter (imports, type signatures, callback shape).
3. **Adapt it** to the user's policy:
   - Rename functions if the user's `lib.rs` already defines `request_filter` / `response_filter` / `configure`.
   - Wire any references to `Config` to the user's actual `gcl.yaml` property names. The templates use placeholder names like `exampleService`, `exampleDateweaveProperty`, `example-hmac-secret-with-256-bits-long`. Replace them.
   - For features that read configuration (`dataweave`, `http_call`, `grpc`, etc.), make sure the user's `definition/gcl.yaml` declares the matching `properties:` block — see "Multi-file features" below for which property name each template expects.
   - **Trim what the user didn't ask for.** Many templates (`header_manipulation`, `body_manipulation`, `body_stream`, `dataweave`, `http_call`, `grpc`, `cors`) ship with both a `request_filter` and a `response_filter` to show every injection point. If the user only asked about request-side behavior (or only response-side), call out which half they can delete and remove the corresponding `.on_response(...)` / `.on_request(...)` from the launcher builder. Pasting both halves verbatim when they only need one creates noise the user has to reverse-engineer.
4. **For multi-file bundles**, deliver every file in the bundle and tell the user explicitly where each goes in their project tree. Do not deliver only `lib.rs` and let the user discover later that they also need a `gcl.yaml` change or a Cargo dep.
5. After editing, suggest the user re-run `make build-asset-files` (only if `gcl.yaml` changed — that regenerates `src/generated/config.rs`) and `make build`.

## Template index

### Request / response handling

| Feature | Template | Summary |
|---|---|---|
| `header_manipulation` | `templates/header_manipulation.rs` | Read, set, add, remove, and bulk-replace request and response headers. |
| `body_manipulation` | `templates/body_manipulation.rs` | Read and replace request/response bodies. |
| `body_stream` | `templates/body_stream.rs` | Stream request/response bodies in chunks. |
| `request_data` | `templates/request_data.rs` | Read method, scheme, host, path, query, and authority from a request. |
| `control_flow` | `templates/control_flow.rs` | Short-circuit a request with a synthetic response (`Flow::Break`). |

### Identity and access control

| Feature | Template | Summary |
|---|---|---|
| `authentication` | `templates/authentication.rs` | Read and set the request's resolved authentication principal. |
| `jwt` | `templates/jwt.rs` | Validate a JWT signature and extract claims/headers. |
| `jwt_generate` | `templates/jwt_generate.rs` | Mint a new signed JWT from claims. |
| `oauth2_token_introspection` | `templates/oauth2_token_introspection.rs` | Introspect an OAuth2 access token (RFC 7662). |
| `ip_filter` | `templates/ip_filter.rs` | Allow/deny by client IP / CIDR. |
| `contracts` | `templates/contracts.rs` | Validate Anypoint API contracts (`client_id` / `client_secret`). |

### External calls

| Feature | Template | Summary |
|---|---|---|
| `http_call` | `templates/http_call/` | Outbound HTTP requests against a configured `service` (multi-file: `lib.rs` + `gcl.yaml`). |
| `grpc` | `templates/grpc/` | Outbound gRPC against a `service` with protobuf codegen (multi-file: 5 files). |
| `dataweave` | `templates/dataweave/` | Evaluate a DataWeave expression against `payload`, `attributes`, `vars`, `authentication` (multi-file: `lib.rs` + `gcl.yaml`). |
| `outbound` | `templates/outbound/gcl.yaml` | Marker `gcl.yaml` declaring an outbound-only policy (no Rust). |

### Validation and transformation

| Feature | Template | Summary |
|---|---|---|
| `json_validator` | `templates/json_validator.rs` | Validate a JSON body against a JSON Schema. |
| `xml_validator` | `templates/xml_validator.rs` | Validate an XML body against an XSD. |

### Rate, spike, and concurrency

| Feature | Template | Summary |
|---|---|---|
| `rate_limiting` | `templates/rate_limiting.rs` | Token-bucket rate limiter with quota windows. |
| `spike_control` | `templates/spike_control.rs` | Spike arrest with queueing. |
| `cache` | `templates/cache.rs` | Per-policy in-memory cache for response or computed values. |
| `lock` | `templates/lock.rs` | Distributed advisory lock for a critical section. |

### Observability and meta

| Feature | Template | Summary |
|---|---|---|
| `logger` | `templates/logger.rs` | Emit structured logs at `info`, `warn`, `error`. |
| `metadata` | `templates/metadata.rs` | Read policy/runtime metadata (org, env, API instance, gateway). |
| `policy_violation` | `templates/policy_violation.rs` | Emit a structured policy-violation event for analytics. |
| `timer` | `templates/timer.rs` | Schedule a timer callback after N milliseconds. |

### State

| Feature | Template | Summary |
|---|---|---|
| `data_storage` | `templates/data_storage.rs` | Persistent KV store shared across workers. |
| `worker_variable` | `templates/worker_variable.rs` | Per-worker variable (no cross-worker sharing). |

### Other

| Feature | Template | Summary |
|---|---|---|
| `cors` | `templates/cors.rs` | Handle CORS preflight and response headers. |
| `stop_iteration` | `templates/stop_iteration/` | Mutate body and headers in a single state transition (multi-file: `lib.rs` + `Cargo.toml.snippet` — requires PDK 1.8.0+ with `enable_stop_iteration`). |
| `unit_testing` | `templates/unit_testing.md` | `pdk-unit` API reference (setup + worked example using `UnitTestBuilder`). For the end-to-end unit-testing workflow — wiring `src/tests/`, mocking upstreams, asserting on violations — use the sibling skill `pdk-unit`. |

## Multi-file features

Some features need more than just a `src/lib.rs` change. Always deliver the whole bundle and tell the user which file goes where.

### `dataweave/` — `templates/dataweave/`

- `lib.rs` → user's `src/lib.rs`.
- `gcl.yaml` → merge the `properties.exampleDateweaveProperty` block (with `format: dataweave` and the `bindings` map) into the user's `definition/gcl.yaml`. The Rust template calls `config.example_dateweave_property.evaluator()`, so the GCL property name in camelCase must produce that snake_case field on the generated `Config` struct. After editing, run `make build-asset-files`.

### `http_call/` — `templates/http_call/`

- `lib.rs` → user's `src/lib.rs`.
- `gcl.yaml` → merge the `properties.service` block (with `format: service`) into `definition/gcl.yaml`. The `service` format is what unlocks `client.request(&config.service)` in the Rust template. Run `make build-asset-files`.

### `stop_iteration/` — `templates/stop_iteration/`

- `lib.rs` → user's `src/lib.rs`.
- `Cargo.toml.snippet` → merge into `Cargo.toml`:
  - `pdk` dependency must be `>= 1.8.0` and carry `features = ["enable_stop_iteration"]`.
  - If the user is on an older PDK, send them to `develop-pdk-policy`'s upgrade runbook before applying this template.

### `grpc/` — `templates/grpc/`

- `lib.rs` → user's `src/lib.rs`.
- `gcl.yaml` → merge `properties.exampleService` (with `format: service`) into `definition/gcl.yaml`.
- `build.rs` → user's `build.rs` at the project root. Generates Rust bindings from `proto/example.proto` at compile time.
- `proto/example.proto` → user's `proto/example.proto`. They will likely replace `ExampleService` and the message shapes with their actual service contract.
- `Cargo.toml.snippet` → merge:
  - `[dependencies]` add `protobuf = "3.5.0"`.
  - `[build-dependencies]` add `protobuf-codegen = "3.5.0"`.
- After all edits, run `make build-asset-files` then `make build`.

**Filename consistency gotcha.** If you rename `proto/example.proto` to something more meaningful (e.g. `proto/user.proto` for a `UserService`), three places must agree or the build breaks:
1. The `.proto` file's path on disk.
2. `build.rs` line `.input("proto/<name>.proto")`.
3. The `lib.rs` import `use crate::<name>::{...};` — `protobuf-codegen` emits one Rust module per `.proto` file, named after the file stem. Keep all three in sync.

### `outbound/` — `templates/outbound/gcl.yaml`

- `gcl.yaml` only → merge into `definition/gcl.yaml`. The `metadata/capabilities/injectionPoint: outbound` label converts the policy into an outbound policy. The user can then add request/response filters by composing with `header_manipulation` or `http_call` templates.

## Source of truth

Canonical PDK template documentation: https://docs.mulesoft.com/pdk/latest/policies-pdk-policy-templates

For lifecycle questions (scaffold, build, run locally, publish, release, upgrade), use the `develop-pdk-policy` skill.
