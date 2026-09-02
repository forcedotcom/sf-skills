---
name: pdk-test
description: Write and run integration tests for custom Flex Gateway policies using the `pdk-test` framework — Docker-based, real Flex Gateway routing, `#[pdk_test]` macro, `TestComposite` orchestration, `HttpMock` / `GrpcBin` backends, `reqwest` assertions. Use whenever the user mentions "PDK integration test", "pdk-test", "functional test PDK", "#[pdk_test]", "TestComposite", "FlexConfig", "tests/requests.rs", "make test", or asks "how do I test my policy against real Flex", "how do I set up Docker-based tests for PDK", "why does my pdk-test timeout", "how do I mock a backend in integration tests".
license: Apache-2.0
compatibility: Requires `pdk-test` 1.8.0 as a `[dev-dependencies]` entry, Docker running locally, the policy WASM built (`make build` first), and a `tests/config/registration.yaml` for Flex Gateway local-mode registration (this file is gitignored and must NOT be committed — it contains private keys).
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
allowed-tools: Bash Read Write Edit AskUserQuestion
---

You are a Flex Gateway PDK integration-testing specialist helping a developer write and run Docker-based functional tests for their custom policy using `pdk-test`.

## Your Task

Drive the developer from "I have a policy that compiles to WASM but no integration tests" to "my tests spin up a real Flex Gateway in Docker, apply the policy, send HTTP traffic, and assert on behavior end-to-end." Surface failures honestly — if Docker is not running, the WASM is not built, or registration.yaml is missing, name the root cause and stop.

## When to use this skill vs alternatives

- **`pdk-test` (this skill)** — Docker-based integration tests using `#[pdk_test]` + `TestComposite`. Slow (tens of seconds per test), but exercises real Flex Gateway routing, TLS, listener config, and multi-policy chains. Lives in `tests/requests.rs`.
- **`pdk-unit`** — in-process unit tests using `#[test]` + `UnitTestBuilder`. Fast (milliseconds), mocks the proxy-wasm host. Use for most policy logic. Supports debugging.
- **`develop-pdk-policy`** — scaffold, build, playground, publish and release lifecycle.

Decision tree:
- Behavior depends on real Flex routing, TLS termination, multi-policy chains, or listener config → **`pdk-test`** (this skill).
- Logic operates on request/response and all dependencies can be mocked → **`pdk-unit`** (separate skill).
- Need both → write `pdk-unit` first for fast feedback, then add a `pdk-test` smoke test here.

## Prerequisites

If the developer's environment is not yet set up (missing Anypoint CLI, Rust, wasm target, or Docker), defer to the **`pdk-prerequisites`** sibling skill before continuing.

Before writing any test, verify these in order:

### 1. Docker is running

```bash
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "Docker NOT running"
```

### 2. Policy WASM is built

```bash
ls target/wasm32-wasip1/release/*.wasm 2>/dev/null && echo "WASM OK" || echo "Run 'make build' first"
```

### 3. Registration file exists

```bash
ls tests/config/registration.yaml 2>/dev/null && echo "Registration OK" || echo "MISSING - see Step 2"
```

If any check fails, stop and fix before proceeding.

## Step 1: Add dev-dependencies

In `Cargo.toml`, add under `[dev-dependencies]`:

```toml
[dev-dependencies]
pdk-test = "1.8.0"
httpmock = "0.6"
reqwest = "0.11"
serde_json = "1"
anyhow = "1"
```

The `pdk-test` version should match the `pdk` version in `[dependencies]` — they are released together from the same workspace. If the project uses a workspace, use `{ workspace = true }` syntax.

## Step 2: Set up test configuration

Integration tests require configuration files under `tests/config/`:

### registration.yaml (required, gitignored)

This tells Flex Gateway how to register in local (disconnected) mode. Generate it once:

1. Go to Anypoint Platform → Runtime Manager → Flex Gateway.
2. Click **Add Gateway** → select **Docker**.
3. Copy the registration command, change `--connected=true` to `--connected=false`.
4. Run it from inside `tests/config/`. It writes `registration.yaml` there.

Alternatively, copy an existing `registration.yaml` from another PDK project or from the playground directory if you already have one.

**IMPORTANT:** Do NOT commit `registration.yaml` — it contains private keys (TLS cert + key in base64). The scaffold's `.gitignore` already excludes it. Each developer generates their own.

### logging.yaml (optional but recommended)

Enables debug-level Flex logs in tests for easier troubleshooting:

```yaml
---
apiVersion: gateway.mulesoft.com/v1alpha1
kind: Configuration
metadata:
  name: logging-config
spec:
  logging:
    runtimeLogs:
      logLevel: debug
```

## Step 3: Create tests/common/mod.rs

This module defines shared constants used across all test files:

```rust
// Copyright 2026 Salesforce, Inc. All rights reserved.

pub const POLICY_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/target/wasm32-wasip1/release");
pub const COMMON_CONFIG_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/config");

// The policy reference name used by Flex to identify the WASM artifact.
// Run `make show-policy-ref-name` or read `target/policy-ref-name.txt` after building.
pub const POLICY_NAME: &str = "<policy-ref-name>";
```

To get the correct `POLICY_NAME`:

```bash
make show-policy-ref-name 2>/dev/null || cat target/policy-ref-name.txt
```

The name is derived by `cargo anypoint get-policy-implementation-name` which combines the asset ID with the major/minor version. Do NOT try to derive it manually — always use the command above.

## Step 4: Write the first integration test

Create `tests/requests.rs`:

```rust
mod common;

use httpmock::MockServer;
use pdk_test::port::Port;
use pdk_test::services::flex::{ApiConfig, Flex, FlexConfig, PolicyConfig};
use pdk_test::services::httpmock::{HttpMock, HttpMockConfig};
use pdk_test::{pdk_test, TestComposite};

use common::*;

const FLEX_PORT: Port = 8081;

#[pdk_test]
async fn test_request_passes_through() -> anyhow::Result<()> {
    // 1. Configure the mock backend
    let backend_config = HttpMockConfig::builder()
        .port(80)
        .hostname("backend")
        .build();

    // 2. Configure the policy under test
    let policy_config = PolicyConfig::builder()
        .name(POLICY_NAME)
        .configuration(serde_json::json!({
            // Fill with your policy's configuration
        }))
        .build();

    // 3. Configure the API that Flex will serve
    let api_config = ApiConfig::builder()
        .name("ingress-http")
        .upstream(&backend_config)
        .path("/anything/echo/")
        .port(FLEX_PORT)
        .policies([policy_config])
        .build();

    // 4. Configure Flex Gateway
    let flex_config = FlexConfig::builder()
        .version("1.10.0")
        .hostname("local-flex")
        .with_api(api_config)
        .config_mounts([(POLICY_DIR, "policy"), (COMMON_CONFIG_DIR, "common")])
        .build();

    // 5. Start the test composite (spins up Docker containers)
    let composite = TestComposite::builder()
        .with_service(flex_config)
        .with_service(backend_config)
        .build()
        .await?;

    // 6. Get handles to services
    let flex: Flex = composite.service()?;
    let flex_url = flex.external_url(FLEX_PORT).unwrap();
    let upstream: HttpMock = composite.service()?;
    let mock_server = MockServer::connect_async(upstream.socket()).await;

    // 7. Set up mock expectations
    mock_server
        .mock_async(|when, then| {
            when.path_contains("/hello");
            then.status(200).body("OK");
        })
        .await;

    // 8. Send request through Flex and assert
    let response = reqwest::Client::new()
        .get(format!("{flex_url}/hello"))
        .send()
        .await?;

    assert_eq!(response.status().as_u16(), 200);
    assert_eq!(response.text().await?, "OK");

    Ok(())
}
```

## Step 5: Run the tests

```bash
# Build the WASM first (tests need the compiled artifact)
make build

# Run integration tests (requires Docker)
cargo test --test requests -- --nocapture
```

Or via the Makefile (the standard scaffold target):

```bash
make test
```

This runs `cargo test -- --nocapture`.

Integration tests are slow (~30-60s per test) because they spin up Docker containers. Use `--nocapture` to see Flex Gateway logs during debugging.

**Note:** Tests run sequentially — the framework acquires a global mutex so only one test executes at a time. This avoids Docker resource contention and cleanup races.

## Framework API Reference

### #[pdk_test] macro

Transforms an `async fn` into a test that creates a Tokio multi-thread runtime and manages the test lifecycle. The framework handles container cleanup via `Drop` on the `TestComposite`, and additionally purges any leftover containers (labeled `CreatedBy=pdk-test`) at the start of each test run.

```rust
#[pdk_test]
async fn my_test() -> anyhow::Result<()> {
    // test body
    Ok(())
}
```

### TestComposite

Orchestrates multiple Docker services (Flex + backends). Builder pattern:

```rust
let composite = TestComposite::builder()
    .with_service(flex_config)      // Flex Gateway
    .with_service(backend_config)   // HTTP mock backend
    .build()
    .await?;
```

After building, retrieve service handles:

```rust
let flex: Flex = composite.service()?;
let upstream: HttpMock = composite.service()?;
```

**Constraint:** Only ONE `HttpMock` service can be defined per test. Adding a second causes `.build().await` to return `Err(TestError::NotSupportedConfig(...))`.

**Hostname uniqueness:** Within a single test, each service of the same type must have a unique hostname. Calling `.with_service()` twice with the same hostname panics.

### FlexConfig

Configures the Flex Gateway container:

| Method | Purpose |
|--------|---------|
| `.version("1.10.0")` | Flex Gateway Docker image version |
| `.hostname("local-flex")` | Container hostname |
| `.image_name("custom/image")` | Override Docker image (default: `mulesoft/flex-gateway`) |
| `.with_api(api_config)` | Add an API configuration (also registers its port) |
| `.config_mounts([(host_path, flex_subdir)])` | Mount config directories into the container |
| `.timeout(Duration::from_secs(90))` | Readiness timeout (default: 60s) |

Readiness is determined by watching for the `"cds: added/updated"` log message from Flex. Once seen, the composite resolves and the test can send traffic.

### ApiConfig

Configures a virtual API that Flex will serve:

| Method | Purpose |
|--------|---------|
| `.name("ingress-http")` | API instance name |
| `.upstream(&backend_config)` | Backend service to forward traffic to |
| `.path("/anything/echo/")` | `destinationPath` — the base path on the backend where requests are forwarded |
| `.port(8081)` | Listener port (Flex listens on all paths on this port) |
| `.policies([policy_config])` | Inbound policies to apply (evaluated in array order) |
| `.outbound_policies([policy_config])` | Outbound policies applied on the upstream route |

**How routing works:** Flex listens on `http://0.0.0.0:{port}` for ALL incoming paths. It forwards requests to the upstream service. The `.path()` value becomes `destinationPath` in the generated Flex YAML — it controls where the backend receives the request, not which incoming paths match.

### PolicyConfig

Configures a policy to apply to an API:

| Method | Purpose |
|--------|---------|
| `.name(POLICY_NAME)` | Policy reference name (matches the WASM artifact) |
| `.configuration(serde_json::json!({...}))` | Runtime policy configuration (matches `gcl.yaml` schema) |

### HttpMockConfig

Configures an httpmock backend container:

| Method | Purpose |
|--------|---------|
| `.port(80)` | Internal listening port |
| `.hostname("backend")` | Container hostname |

### HttpMock handle

After composite starts, get the mock handle:

```rust
let upstream: HttpMock = composite.service()?;
let mock_server = MockServer::connect_async(upstream.socket()).await;
```

Then set expectations using the `httpmock` crate API:

```rust
let mock = mock_server
    .mock_async(|when, then| {
        when.method("GET").path("/api/resource");
        then.status(200)
            .header("content-type", "application/json")
            .body(r#"{"result": "ok"}"#);
    })
    .await;

// After sending a request, assert the mock was called:
mock.assert();
mock.assert_hits(1);
```

### Flex handle

```rust
let flex: Flex = composite.service()?;
let flex_url = flex.external_url(FLEX_PORT).unwrap();
// flex_url is like "http://127.0.0.1:<random-port>"
```

### GrpcBin / GripMock (gRPC testing)

For policies that interact with gRPC services:

```rust
use pdk_test::services::grpcbin::{GrpcBin, GrpcBinConfig};
use pdk_test::services::gripmock::{GripMock, GripMockConfig};
```

### HttpBin

For general-purpose HTTP echo testing:

```rust
use pdk_test::services::httpbin::{HttpBin, HttpBinConfig};
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `PDK_TEST_FLEX_IMAGE_NAME` | Override Flex Docker image name |
| `PDK_TEST_FLEX_IMAGE_VERSION` | Override Flex Docker image version |

## Test Patterns

### Pattern: Test policy blocks a request

```rust
#[pdk_test]
async fn test_policy_blocks_unauthorized() -> anyhow::Result<()> {
    // ... setup composite ...

    let response = reqwest::Client::new()
        .get(format!("{flex_url}/protected"))
        .send()  // No auth header
        .await?;

    assert_eq!(response.status().as_u16(), 401);

    Ok(())
}
```

### Pattern: Test policy modifies headers

Use `httpmock` assertions to verify headers reaching the backend:

```rust
#[pdk_test]
async fn test_policy_adds_header() -> anyhow::Result<()> {
    // ... setup composite ...

    let mock = mock_server
        .mock_async(|when, then| {
            when.header_exists("x-injected-header");
            then.status(200);
        })
        .await;

    let response = reqwest::Client::new()
        .get(format!("{flex_url}/hello"))
        .send()
        .await?;

    assert_eq!(response.status().as_u16(), 200);
    mock.assert();  // Proves the header reached the backend

    Ok(())
}
```

### Pattern: Reduce boilerplate with a config helper

Extract the config-building into a helper, but keep the `TestComposite` alive in the test scope (dropping it destroys the containers):

```rust
fn build_flex_config(policy_json: serde_json::Value) -> (FlexConfig, HttpMockConfig) {
    let backend_config = HttpMockConfig::builder()
        .port(80)
        .hostname("backend")
        .build();

    let policy_config = PolicyConfig::builder()
        .name(POLICY_NAME)
        .configuration(policy_json)
        .build();

    let api_config = ApiConfig::builder()
        .name("ingress-http")
        .upstream(&backend_config)
        .path("/anything/echo/")
        .port(FLEX_PORT)
        .policies([policy_config])
        .build();

    let flex_config = FlexConfig::builder()
        .version("1.10.0")
        .hostname("local-flex")
        .with_api(api_config)
        .config_mounts([(POLICY_DIR, "policy"), (COMMON_CONFIG_DIR, "common")])
        .build();

    (flex_config, backend_config)
}

#[pdk_test]
async fn test_with_custom_config() -> anyhow::Result<()> {
    let (flex_config, backend_config) = build_flex_config(serde_json::json!({
        "my_param": "value"
    }));

    // composite must live for the duration of the test
    let composite = TestComposite::builder()
        .with_service(flex_config)
        .with_service(backend_config)
        .build()
        .await?;

    let flex: Flex = composite.service()?;
    let flex_url = flex.external_url(FLEX_PORT).unwrap();
    // ... send requests and assert ...
    Ok(())
}
```

### Pattern: Test multiple policies in a chain

```rust
let api_config = ApiConfig::builder()
    .name("ingress-http")
    .upstream(&backend_config)
    .path("/anything/echo/")
    .port(FLEX_PORT)
    .policies([first_policy, second_policy])  // Array order determines evaluation order
    .build();
```

### Pattern: Retry for policies with async initialization

Some policies use `Clock` in their `configure` function for periodic tasks (e.g., contract polling, cache refresh). These may need a brief delay after Flex readiness before the policy logic is fully operational. This is NOT needed for most policies — only when the policy has async work during `configure`.

```rust
use tokio::time::{sleep, Duration};

// Only needed for policies that do async work in configure (Clock-based init)
sleep(Duration::from_secs(2)).await;

let response = reqwest::Client::new()
    .get(format!("{flex_url}/hello"))
    .send()
    .await?;
```

For these cases, a retry loop is more robust:

```rust
let mut last_status = 0;
for _ in 0..10 {
    let resp = reqwest::get(format!("{flex_url}/hello")).await?;
    last_status = resp.status().as_u16();
    if last_status != 503 {
        break;
    }
    sleep(Duration::from_millis(500)).await;
}
assert_eq!(last_status, 200);
```

## Running tests

```bash
# Run all integration tests
cargo test --test requests

# Run a specific test
cargo test --test requests test_clean_request_passes

# With output (see Flex logs)
cargo test --test requests -- --nocapture

# Via Makefile (standard scaffold target)
make test

# Override Flex version
PDK_TEST_FLEX_IMAGE_VERSION=1.9.0 cargo test --test requests
```

## Troubleshooting

### "Docker daemon not running" / "Cannot connect to Docker daemon"

Start Docker Desktop or the Docker daemon. `pdk-test` uses the Docker API via bollard.

### Test times out waiting for Flex readiness

The framework waits for Flex to emit `"cds: added/updated"` in stdout. If this message never appears:

- Check Docker has enough resources (CPU/memory)
- Verify the Flex image version exists: `docker pull mulesoft/flex-gateway:1.10.0`
- Check `registration.yaml` is valid — an invalid registration causes Flex to exit immediately
- Increase timeout: `.timeout(Duration::from_secs(120))`

### "WASM not found" / policy doesn't apply

- Run `make build` before tests
- Verify `POLICY_DIR` points to `target/wasm32-wasip1/release`
- Verify `POLICY_NAME` matches the output of `make show-policy-ref-name`

### Mock not hit / unexpected 404

- Remember that Flex listens on ALL paths on the configured port. The `.path()` in `ApiConfig` is the `destinationPath` on the backend, not an incoming path filter.
- Verify the mock `when` conditions match what Flex actually forwards to the backend.
- Use `--nocapture` to see Flex logs and confirm the policy is loaded.

### "No such image" error

Pull the Flex image first:

```bash
docker pull mulesoft/flex-gateway:1.10.0
```

Or override with an available version:

```bash
PDK_TEST_FLEX_IMAGE_VERSION=latest cargo test --test requests
```

### Tests pass locally but fail in CI

- CI needs Docker available (Docker-in-Docker or a Docker socket mount)
- CI may have limited resources — increase timeouts
- Each developer must generate their own `registration.yaml` (it's gitignored)

### "Only 1 HttpMock can be defined per test"

The framework enforces a single `HttpMockConfig` per `TestComposite`. If you need multiple backend behaviors, use httpmock's conditional matching (`when.path(...)`, `when.header(...)`) on the single mock server.

## Completion Checklist

After writing integration tests, verify:

- [ ] `make build` succeeds (WASM artifact is fresh)
- [ ] `tests/config/registration.yaml` exists locally (NOT committed to git)
- [ ] `tests/common/mod.rs` has the correct `POLICY_NAME` (from `make show-policy-ref-name`)
- [ ] `cargo test --test requests` passes with Docker running
- [ ] Tests cover at least: one happy-path request, one rejection/error case
