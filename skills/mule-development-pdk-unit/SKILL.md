---
name: pdk-unit
description: Write and run unit tests for custom Flex Gateway policies built with the Policy Development Kit (PDK) — wire up `src/tests/`, build a first `UnitTestBuilder` test, mock HTTP/gRPC upstreams with closures or `TraceBackend`, factor reusable `TestConfig` helpers, assert on responses / headers / violations, run with `make test` or `cargo test`, troubleshoot init-sleep races, authority mismatches, and feature-gate skew. Use whenever the user mentions "PDK unit test", "pdk-unit", "UnitTestBuilder", "test my policy", "cargo test PDK", "mock backend PDK", "Flex Gateway policy unit testing", `with_http_upstream_from_authority`, `with_entrypoint`, `TraceBackend`, or asks "how do I test a Flex Gateway policy", "how do I mock an upstream in pdk-unit", "why is my policy timer not firing in tests". For full `pdk-unit` API reference see `pdk-templates/templates/unit_testing.md`. For scaffolding / build / publish see `develop-pdk-policy`.
license: Apache-2.0
compatibility: Requires `pdk-unit` 1.8.0+ as a `[dev-dependencies]` entry (the scaffold from `anypoint-cli-v4 pdk policy-project create` adds it automatically). Some patterns require feature gates that vary by PDK version — `experimental` and `experimental_local_mode` for advanced fixtures, `enable_stop_iteration` for policies using `into_headers_body_state` / `into_body_state` (PDK 1.8.0+). The `pdk-unit` crate must enable the same feature flags as the matching `pdk` dependency.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
allowed-tools: Bash Read Write Edit AskUserQuestion
---

You are a Flex Gateway PDK unit-testing specialist helping a developer add fast, in-process unit tests to their custom policy using `pdk-unit`.

## Your Task

Drive the developer from "I have a policy crate but no tests" to "`make test` is green with the patterns the policy actually needs": decision (unit vs integration), `src/tests/` wiring, a first green test, mocking upstreams, asserting on responses/headers/violations, and troubleshooting the half-dozen failure modes that aren't obvious from compiler output. Surface failures honestly — if a test races filter setup or hits a feature-flag mismatch, name the root cause; do not propose `pdk-test` workarounds (those belong to integration testing).

**Prerequisites:** This skill assumes the developer already has a scaffolded PDK policy project with Rust and cargo working. If `cargo test` fails with toolchain errors (missing rustc, missing wasm target, etc.), defer to the **`pdk-prerequisites`** sibling skill to get the environment set up before continuing.

## When to use this skill vs alternatives

- **`pdk-unit` (this skill)** — in-process, fast (milliseconds), uses `#[test]` + `UnitTestBuilder`, lives in `src/tests/`. Mocks upstreams with closures. Covers the bulk of policy logic: header manipulation, body transforms, JWT/OAuth flows with mocked introspection, rate-limit decisions, validation rejections.
- **`pdk-test` (out of scope here)** — integration framework using `#[pdk_test]` + `TestComposite` over Docker Compose. Slow (tens of seconds), real Flex routing. The scaffold ships an example at `tests/requests.rs`. Use when behavior depends on real Flex plumbing (TLS termination, multi-policy chains, listener config). Not owned by this skill.
- **`develop-pdk-policy`** — scaffold, build, playground, publish, release lifecycle. Start there if no project exists yet.

## Step 1: Decide unit vs integration

Most policy logic is unit-testable. Quick decision tree:

- Logic operates on request/response and any external dependency can be mocked → **`pdk-unit`** (this skill).
- Behavior depends on real Flex routing, TLS termination, listener config, or chains of real policies → **graduate to `pdk-test`** (the scaffold's `tests/requests.rs` is the entry point).
- Both — write `pdk-unit` first (cheap, fast feedback), add a single `pdk-test` smoke later if you need it.

This is a sanity gate, not a blocker. Most policies stay in `pdk-unit`.

## Step 2: Wire up `src/tests/`

The scaffold from `anypoint-cli-v4 pdk policy-project create` ships `tests/` (integration tests using `pdk-test`) but does NOT create `src/tests/` for unit tests. You add it manually:

1. **Create the directory and module file.**
   ```bash
   mkdir -p src/tests
   ```
   Drop in `templates/tests_module_wiring.rs` as `src/tests/mod.rs`. Edit the `mod <name>;` lines to match the test files you'll create.

2. **Wire it into `src/lib.rs`.** Add at the top level (outside any function):
   ```rust
   #[cfg(test)]
   mod tests;
   ```
   The `#[cfg(test)]` gate keeps the test module out of the production WASM build.

3. **Verify dev-dependencies.** The scaffold adds `pdk-unit = "<version>"` to `[dev-dependencies]` in `Cargo.toml`. Confirm two things:
   - The `pdk-unit` version matches the `pdk` version in `[dependencies]` (a `pdk` 1.8.0 + `pdk-unit` 1.7.0 mix usually fails to link).

## Step 3: Write your first test

Drop `templates/hello_test.rs` as `src/tests/hello.rs`. Then run:

```bash
make test                                 # build + cargo test -- --nocapture
# or, faster inner loop:
cargo test hello_world -- --nocapture     # single test, no build
```

Expected: one passing test. The skeleton is:

```rust
let mut tester = UnitTestBuilder::default()
    .with_backend(ok_backend)              // default upstream returns 200 OK
    .with_config(r#"{"stringProperty": "default"}"#)  // see config gotcha below
    .with_entrypoint(crate::configure);    // your policy's #[entrypoint] fn

let response = tester.request(UnitHttpRequest::get().with_path("/"));
assert_eq!(response.status_code(), 200);
```

**Config gotcha**: pass JSON that satisfies every `required` field declared in `definition/gcl.yaml`. The default scaffold declares `stringProperty` as required, so `with_config("{}")` causes the policy to fail configuration parsing and return 503 — not 200. Replace the JSON with whatever your `gcl.yaml` requires, or delete required fields you don't need.

**Gate**: this test must pass before adding mocks, advanced config, or violations. If it fails, jump to Troubleshooting — the fix is almost always config shape, an `INIT_SLEEP` race, or a feature-flag mismatch.

## Step 4: Add config and upstream mocks

### 4a. Centralise config with a `TestConfig` builder

Drop `templates/test_config_helper.rs` as `src/tests/common.rs`. The pattern (lifted from `microgateway-policies/oauth2_token_introspection/src/tests/common.rs`) is:

- A `TestConfig::base()` returning the JSON config that 80% of tests want.
- `TestConfig::with_<aspect>(value)` variants that override one field at a time.
- A `tester(config: String)` helper that builds the tester with the standard backend, applies the config, and calls `tester.sleep(INIT_SLEEP)` before returning.

Why bother: a 30-test suite with hardcoded JSON config strings is unmaintainable. Centralising means a config-shape change is one edit, not thirty. Keep the JSON keys in sync with `definition/gcl.yaml`.

### 4b. Mock outbound HTTP upstreams

Drop `templates/upstream_mock.rs` as `src/tests/upstream.rs`. Two upstream types:

- **`with_backend(backend)`** — the default passthrough upstream the policy proxies to. One per tester.
- **`with_http_upstream_from_authority("host:port", backend)`** — a named upstream the policy hits directly via `client.request(&config.service)`. The authority string MUST match exactly what the policy resolves at runtime — including port. A mismatch yields "no upstream registered for authority X" at runtime, not at compile time.

Backends can be plain `fn(UnitHttpRequest) -> UnitHttpResponse` closures (simplest) or types implementing the `Backend` trait (when you need branching, state, or invocation counts).

### 4c. Capture what the policy SENT upstream

Drop `templates/trace_backend_capture.rs` as `src/tests/trace.rs`. `TraceBackend` wraps any `Backend` and records every call. After the request flows, drain the recording with `.next()` and assert on what made it through:

```rust
let captured: Rc<TraceBackend<fn(UnitHttpRequest) -> UnitHttpResponse>> =
    Rc::new(TraceBackend::new(ok_backend));
// ... use Rc::clone(&captured) in .with_backend()
let upstream_request = captured.next().expect("backend received request");
assert_eq!(upstream_request.header("authorization"), Some("Bearer xyz"));
```

Use this whenever you care about what the policy DID, not just what came back.

## Step 5: Assert on responses, headers, and violations

Three assertion targets cover ~95% of tests:

- **Status**: `assert_eq!(response.status_code(), 401);`
- **Headers** (case-insensitive, normalized to lowercase): `assert_eq!(response.header("x-foo"), Some("bar"));` — note `header()` returns `Option<&str>`.
- **Violations** (the canonical "I rejected this request" signal): `response.violation()` returns `Option<PolicyViolation>`. Drop `templates/violation_assertion.rs` as `src/tests/violation.rs` for a reusable `assert_violation_generated()` helper.

**The `INIT_SLEEP` gotcha.** Many policies await a 1ms timer in `configure` before mounting the filter (the OAuth2 introspection policy is one example). Without `tester.sleep(Duration::from_millis(10))` after `with_entrypoint(...)`, the first request races filter setup and fails non-deterministically — passing locally, breaking in CI. Hardcode `INIT_SLEEP = Duration::from_millis(10)` in `src/tests/common.rs` and call `tester.sleep(INIT_SLEEP)` after every `with_entrypoint(...)`. The included templates already do this.

## Pattern Index

| Pattern | Template | Summary |
|---|---|---|
| Smallest possible test | `templates/hello_test.rs` | `UnitTestBuilder` + GET + assert 200. The compile-test target. |
| Reusable config + tester wiring | `templates/test_config_helper.rs` | `TestConfig::base()` + `tester(config)` helper. Drop into `src/tests/common.rs`. |
| Outbound upstream mock | `templates/upstream_mock.rs` | `with_http_upstream_from_authority` + closure backend + `INIT_SLEEP`. |
| Capture sent requests | `templates/trace_backend_capture.rs` | `Rc<TraceBackend>` + `.next()` for asserting on what the policy sent. |
| Violation rejection | `templates/violation_assertion.rs` | `response.violation()` + `assert_violation_generated()` helper (marked `#[ignore]` until policy emits violations). |
| `src/tests/` module wiring | `templates/tests_module_wiring.rs` | Shape of `src/tests/mod.rs` + the `#[cfg(test)] mod tests;` line for `src/lib.rs`. |

## Running tests

```bash
cargo test --lib                           # unit tests only — fast inner loop (recommended)
cargo test --lib <name> -- --nocapture     # single unit test with println! / log output
make test                                  # full path: build (WASM) + ALL tests (unit AND integration)
cargo test                                 # ALL tests (unit AND integration)
```

**Important**: the scaffolded `Makefile` target `make test` runs `cargo test`, which executes BOTH the unit tests in `src/tests/` AND the integration tests in `tests/requests.rs` (the `#[pdk_test]` ones using Docker Compose). Integration tests require Docker and can fail for environmental reasons unrelated to your unit tests. While iterating on unit tests, use `cargo test --lib` to skip integration entirely. CI should run `make test` to gate both layers.

## Troubleshooting

### Test passes locally, fails non-deterministically in CI

**Cause**: First request races filter setup. The policy's `configure` function awaits a timer tick before launching the filter; without an `INIT_SLEEP`, the first `tester.request(...)` runs before the filter is mounted.

**Fix**: After `with_entrypoint(crate::configure)`, call `tester.sleep(Duration::from_millis(10))`. Use the `INIT_SLEEP` constant from `templates/test_config_helper.rs` consistently.

### "no upstream registered for authority X"

**Cause**: The authority string passed to `with_http_upstream_from_authority` does not match what the policy resolves `&config.service` to at runtime. Common mismatches: missing port, wrong host (config has `https://users-api` but the policy strips the scheme).

**Fix**: Print the resolved authority once from inside the policy (`info!("calling {:?}", &config.service);`), run any test, and copy the exact string. Pin it as a `const UPSTREAM_AUTHORITY: &str = "...";` in `src/tests/common.rs`.

### `with_entrypoint(crate::configure)` does not compile

**Cause**: The policy's `#[entrypoint]` function isn't named `configure`. Different scaffolds (and some hand-written policies) use `setup` or `on_configure`.

**Fix**: Look at `src/lib.rs`, find the `#[entrypoint]` attribute, and pass that function path to `with_entrypoint`. The function is whatever fn the launcher calls once at policy load.

### Timer-driven behavior not firing in tests

**Cause**: Calling `tester.request(...)` does not advance simulated time. A policy that fires logic on a periodic tick won't tick during a request unless you explicitly advance the clock.

**Fix**: `tester.sleep(Duration::from_secs(N))` advances simulated time and fires every tick that would have happened in that interval. Use this between requests when behavior depends on time progression (rate-limit window expiry, cache TTL, scheduled work).

## When to graduate to `pdk-test`

Some behaviors `pdk-unit` cannot honestly cover: TLS termination, real listener wiring, mTLS, real connector chains, version-skew between policy WASM and Flex runtime. For those, the scaffold ships `tests/requests.rs` using `#[pdk_test]` + `TestComposite` (Docker Compose with a real Flex container). That's the integration framework. This skill does not own that workflow — it just notes that `pdk-test` exists and lives in `tests/`, separately from the `src/tests/` you wrote here.

## Full `pdk-unit` API reference

The complete `pdk-unit` API surface — every `UnitTestBuilder` method, the request/response builders, all backend variants, gRPC mocking with `#[protobuf_grpc_backend]`, LDAP credential mocking, contract / SLA testing, stop-iteration mode, the `dw2pel` DataWeave helper — lives in `pdk-templates/templates/unit_testing.md` (sibling skill, 279 lines). Read it when you need a method this skill didn't show. Do not re-derive — that file is the canonical snapshot.

## Additional Resources

- **`pdk-templates/templates/unit_testing.md`** — full `pdk-unit` API reference (sibling skill).
- **`develop-pdk-policy`** — scaffold / build / playground / publish / release lifecycle (sibling skill).
- **PDK overview**: https://docs.mulesoft.com/pdk/latest/
