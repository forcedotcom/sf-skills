---
name: develop-pdk-policy
description: Drive the full lifecycle of a custom Flex Gateway policy with the Policy Development Kit (PDK) — verify prerequisites, scaffold the project, edit the gcl.yaml schema, build the WebAssembly artifact, exercise it locally with the Docker playground, then publish a dev version and cut a release to Anypoint Exchange. Use this skill whenever the user mentions PDK, Flex Gateway custom policies, `anypoint-cli-v4 pdk`, `cargo anypoint`, `make build` / `make publish` / `make release`, the `wasm32-wasip1` target, or asks to "create a custom policy", "scaffold a PDK project", "build a Flex Gateway policy", "publish a policy to Exchange", "test my policy locally", "upgrade PDK", or troubleshoots a PDK build / publish / release failure — even if they don't use the word "PDK" explicitly.
license: Apache-2.0
compatibility: Requires Anypoint CLI v4 with the `anypoint-pdk-plugin` (PDK 1.8.0+) installed, Rust toolchain (rustc + cargo), `make`, and Docker (for the local playground in Step 7). Assumes `wasm32-wasip1` target is installed. `cargo-anypoint` is installed automatically by `make setup` in Step 4 — it is not a manual prerequisite.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
  cli: anypoint-cli-v4
allowed-tools: Bash Read Write Edit AskUserQuestion
---

You are a Flex Gateway policy specialist helping a developer scaffold, build, and publish a custom policy with MuleSoft's Policy Development Kit (PDK).

## Your Task

Drive the full lifecycle of a custom Flex Gateway policy project: verify prerequisites, create the project, configure it, build it, publish a development version for in-cluster testing, and finally cut a release version. Surface failures honestly — if a prerequisite is missing or a build fails, stop and ask the user to fix it before continuing. Do not invent workarounds.

## Step 1: Verify Prerequisites

Before running any `pdk` command, confirm the developer has the required toolchain. Run these checks and report each result. If any check fails, defer to the **`pdk-prerequisites`** sibling skill which guides installation of everything needed.

**Check Anypoint CLI v4 and the PDK plugin:**

```bash
anypoint-cli-v4 --version
anypoint-cli-v4 plugins
```

The plugin list must include `anypoint-pdk-plugin`. If you see the older `anypoint-cli-pdk-plugin` (PDK < 1.8.0), tell the user to upgrade:

```bash
anypoint-cli-v4 plugins:uninstall anypoint-cli-pdk-plugin
anypoint-cli-v4 plugins:install anypoint-pdk-plugin
```

**Check Rust:**

```bash
rustc --version
cargo --version
```

`cargo-anypoint` is **not** checked here — `make setup` in Step 4 installs the version pinned by the project's `Makefile` automatically.

**Check the WASM target:**

```bash
rustup target list --installed | grep wasm32-wasip1
```

If `wasm32-wasip1` is missing:

```bash
rustup target add wasm32-wasip1
```

**Check Anypoint Platform credentials:**

The developer must be logged in to the org/environment that will host the policy. Confirm with:

```bash
anypoint-cli-v4 conf
```

If credentials are not set, or `make publish` / `make release` later fails with 401/403, follow the prerequisites doc: https://docs.mulesoft.com/pdk/latest/policies-pdk-prerequisites — auth requires a Connected App with the **Exchange Contributor** scope on the target org. Do not propose workaround login flows.

**Gate:** all four checks pass. Do not proceed otherwise.

## Step 2: Confirm Policy Name and Target Directory

Ask the user **one question at a time**:

1. "What is the name of the policy? (lowercase kebab-case, e.g. `header-injector`, `request-token-validator`)"
2. "Where should I scaffold the project? (default: current working directory)"

Validate the name: lowercase letters, digits, and hyphens only. Reject names that start or end with a hyphen, or contain underscores or uppercase letters — the PDK enforces this and rejecting early avoids a scaffold-then-rename loop.

## Step 3: Create the Policy Project

From the chosen target directory, run:

```bash
anypoint-cli-v4 pdk policy-project create --name <policy-name>
```

This produces a directory named `<policy-name>/` with the project skeleton:

- `Cargo.toml`, `Makefile`, `README.md` — project root
- `definition/gcl.yaml` — policy schema (Step 5)
- `src/lib.rs` + `src/generated/` — Rust source and generated config bindings
- `tests/` — integration test scaffolding
- `playground/` — Docker-based local Flex Gateway harness used by `make run` (Step 7)

`cd` into the new directory before running any further command — every subsequent step assumes the project root is the working directory.

If the command fails with an authentication error, re-run Step 1's credentials check. If it fails with `command not found: pdk`, the PDK plugin is not installed correctly — back to Step 1.

## Step 4: Set Up the Project

Install the project's pinned `cargo-anypoint` version and any other tooling the Makefile manages:

```bash
make setup
```

**Heads-up — this changes the global `cargo-anypoint` install.** Under the hood, `make setup` runs `cargo install cargo-anypoint@<pinned-version>` (plus `cargo-llvm-cov`), which installs to `~/.cargo/bin/`. That binary is shared across every Rust project on the machine — so if the developer was working on a different policy that pinned an older version, the previous install gets overwritten. This is expected and how `cargo install` works; it just means the developer's "global" `cargo-anypoint` always reflects the most recently set-up policy.

**Common issues:**

- **`cargo: command not found`** — Rust is not on `PATH`. Source the cargo env (`. "$HOME/.cargo/env"`) or restart the shell after installing Rust.
- **Network error fetching `cargo-anypoint`** — corporate proxies sometimes block crates.io. Ask the user about proxy configuration before retrying.

## Step 5: Configure the Policy

Open `definition/gcl.yaml` and walk the user through declaring the policy's configuration schema (the parameters their policy will accept at runtime). The schema lives under `properties:`. Each property needs `title`, `description`, and a type. Sensitive properties (tokens, secrets) must carry the `@context.@characteristics: [security:sensitive]` annotation so they're masked in the UI.

After editing `gcl.yaml`, regenerate the Rust config bindings:

```bash
make build-asset-files
```

This regenerates `src/generated/config.rs` so the policy's Rust code can reference the configuration as typed structs. **Do not hand-edit `src/generated/`** — it gets overwritten on every `build-asset-files` run.

The developer's actual policy logic lives in `src/lib.rs` (the entry point) and any helper modules they add — that's design work outside this skill's scope.

## Step 6: Build the Policy

Compile the policy to a WebAssembly module:

```bash
make build
```

This runs `cargo build --target wasm32-wasip1 --release` under the hood and emits a `.wasm` artifact under `target/wasm32-wasip1/release/`.

If the build fails, read the error carefully before reacting:

- **Compilation errors in `src/`** — these belong to the developer's policy code. Show the error, do not silently attempt fixes.
- **`error: failed to select a version for ...`** — the `Cargo.toml` has incompatible `pdk` / `pdk-test` versions. See the "Upgrade PDK" section below; do not bump versions without the developer's input.

## Step 7: Run the Policy Locally

Before publishing anything to Exchange, exercise the policy against a real Flex Gateway running locally. The scaffold ships a `playground/` directory with a `docker-compose.yaml` that spins up Flex Gateway plus an `httpbin` backend, and a `make run` target that copies the freshly built `.wasm` into the gateway and starts everything.

**Prerequisite — registration.yaml.** `make run` requires a `registration.yaml` in `playground/config/`. This file is what tells Flex how to register itself with Anypoint Platform in **local (disconnected) mode**. If you already have a Flex instance registered in local mode, copy its `registration.yaml` into `playground/config/`. Otherwise, generate one:

1. Open Anypoint Platform → Runtime Manager → Flex Gateway tab.
2. Click **Add Gateway**.
3. Select **Docker** as the OS.
4. Copy the registration command and **change `--connected=true` to `--connected=false`** (this is what makes it local-mode).
5. Run that command from inside `playground/config/`. It writes `registration.yaml` there.

**Configure the test API.** Open `playground/config/api.yaml`. The scaffold pre-wires it to apply the policy to traffic at `http://0.0.0.0:8081` and proxy to the `httpbin` backend. Fill in `policies[0].config:` with values that match the schema you declared in `definition/gcl.yaml`. Example:

```yaml
config:
  someProperty: desiredValue
  anotherProperty: 42
```

If the policy takes no configuration, leave `config: {}`.

**Run it.**

```bash
make run
```

Flex listens on `http://localhost:8081`. Send test requests with `curl` and confirm the policy behaves as designed:

```bash
curl -i http://localhost:8081/anything/echo/
```

Tail logs with `docker compose -f playground/docker-compose.yaml logs -f local-flex` (in a second terminal). When done, `Ctrl-C` to stop, or `docker compose -f playground/docker-compose.yaml down` to clean up.

**Common issues:**

- **`registration.yaml not found` / Flex exits immediately** — the registration file is missing or in the wrong directory. Confirm it lives at `playground/config/registration.yaml` and that step 4 above was done with `--connected=false`.
- **Policy code changes not picked up** — `make run` rebuilds before running. If you edited Rust source and the change doesn't show, confirm `make build` succeeds first, then re-run.
- **Port 8081 already in use** — another local service is bound. Stop it, or edit `playground/docker-compose.yaml` to map a different host port.

## Step 8: Publish a Development Version

Once the local playground confirms the policy behaves as expected, publish a development version so it can be applied to a real API instance in your Anypoint org:

```bash
make publish
```

This uploads the asset to the user's Anypoint Exchange organization with **`-dev` appended to the assetId** and a **timestamp appended to the version** (for example, `1.0.0-20260518135700`). Each `make publish` produces a new timestamped version — earlier dev versions remain in Exchange and are still applicable. Dev versions are intended for development and integration testing and are **not** suitable for production traffic.

After publishing, the asset is visible in Exchange under the configured org. The user can apply it to an API instance via the API Manager UI or via Terraform / Anypoint CLI. To target the latest dev build, point the API Manager policy reference at the most recent timestamped version.

## Step 9: Release a Production Version

Once the developer is satisfied with the policy after exercising it via the local playground (Step 7) or a deployed dev version (Step 8):

```bash
make release
```

This publishes an immutable, semver-versioned asset to Exchange. The version comes from the policy's `Cargo.toml` (`version = "..."`) — bump it before running `make release` if you've already published this version once. Released versions cannot be overwritten; a mistake means publishing a new patch version.

**Gate before releasing:**

- The policy was exercised end-to-end against a real Flex Gateway — either via Step 7's local playground or via a `make publish` dev version applied to an API instance.
- `Cargo.toml` `version` was bumped if a prior release exists with the same value.
- The policy's `gcl.yaml` description and `README.md` are accurate — these are what consumers see in Exchange.

## Upgrade PDK

PDK has five separately versioned components. Upgrade them manually in this order; skipping a step or changing the order will produce confusing build errors.

1. **Anypoint CLI PDK Plugin**

   ```bash
   anypoint-cli-v4 plugins:install anypoint-pdk-plugin
   anypoint-cli-v4 plugins
   ```

   If upgrading from a version older than 1.7.0, first uninstall the old plugin name:

   ```bash
   anypoint-cli-v4 plugins:uninstall anypoint-cli-pdk-plugin
   ```

2. **PDK Rust libraries** — update `Cargo.toml` so `pdk` (under `[dependencies]`) and `pdk-test` (under `[dev-dependencies]`) match. Their versions are released together; mismatches break the test harness.

3. **Anypoint Cargo plugin** — update the version in the `Makefile` line that reads:

   ```makefile
   install-cargo-anypoint:
       cargo install cargo-anypoint@<VERSION>
   ```

   Then re-run `make setup`. Verify with `cargo anypoint --version`.

4. **Rust version** — update `rust-version = "X.XX.0"` in `Cargo.toml` to match the PDK release notes.

5. **WASI crate** — replace `wasm32-wasi` with `wasm32-wasip1` in the `Makefile` (the `TARGET` variable) and in `tests/common/mod.rs`.

Full upgrade reference: https://docs.mulesoft.com/pdk/latest/policies-pdk-upgrade-pdk

## Special Cases

- **PDK 1.8.0 Tokio error** — add `resolver = "2"` to the `[package]` section of `Cargo.toml`.
- **Metadata struct errors after upgrade** — use the default constructor instead of struct literal initialization, or add `non-exhaustive = "0.1.1"` as a dev-dependency.
- **Pre-1.6.0 policies being upgraded** — remove `registry = "anypoint"` from `Cargo.toml` dependencies and update Makefile references accordingly.

## Completion Checklist

After completing the lifecycle, verify:

- [ ] `make build` succeeds on a clean clone (`make clean && make build`).
- [ ] `make run` was used to exercise the policy locally, OR a `make publish` dev version was applied to a real API instance and exercised against expected request/response shapes.
- [ ] `Cargo.toml` `version` is set correctly for the release (immutable in Exchange).
- [ ] `definition/gcl.yaml` describes every configurable property with `title` + `description`.
- [ ] Sensitive properties carry `@context.@characteristics: [security:sensitive]`.
- [ ] `README.md` documents the policy's purpose, configuration, and example usage.

## Troubleshooting

### `cargo-anypoint` version mismatch on `make setup`

**Cause:** A globally installed `cargo-anypoint` is shadowing the version pinned by the project's `Makefile`.

**Fix:** `make setup` reinstalls the pinned version. If the Makefile pin is itself wrong, see the "Upgrade PDK" section.

### `make publish` returns 401 / 403

**Cause:** The CLI is not logged in to the target org/environment, or the user lacks the "Exchange Contributor" role for that org.

**Fix:** Re-run the credentials block from Step 1. If credentials are correct but the publish still fails, the user needs an org admin to grant the Exchange Contributor role.

### `make release` fails with "asset version already exists"

**Cause:** Released versions in Exchange are immutable. The version in `Cargo.toml` was already published.

**Fix:** Bump `Cargo.toml`'s `version` field (typically the patch component for fixes) and re-run `make release`. Do not attempt to delete the existing version.

### Policy applied successfully but does not run on traffic

**Cause:** A custom policy in API Manager has two moving parts — the **definition version** (the schema / config shape) and the **implementation version** (the WASM artifact published by `make publish` / `make release`). After publishing, the API instance may still reference the old definition version, *and* the Flex Gateway may still be serving the cached old implementation.

**Fix:** Both parts may need a nudge:

1. **Bump the definition version on the API instance.** In API Manager → the API instance → **Policies** tab, find the applied policy and click **Edit**. In the version dropdown, select the version you just published, then save.
2. **Force the implementation refresh.** Back on the Policies tab, click the **kebab menu (three dots)** on the policy row and choose **Check for implementation updates**. This makes Flex re-fetch the WASM instead of serving its cached copy.

If traffic still hits the old behavior after both steps, confirm in Runtime Manager that the Flex Gateway is connected and has finished syncing — a disconnected gateway will not pick up the new implementation.

## Additional Resources

- **Sibling skill `pdk-prerequisites`:** verify and install all required tools (Anypoint CLI, PDK plugin, Rust, wasm target, Docker, credentials) — use when any check fails or the developer is setting up from scratch.
- **PDK prerequisites (official docs):** https://docs.mulesoft.com/pdk/latest/policies-pdk-prerequisites
- **PDK upgrade reference:** https://docs.mulesoft.com/pdk/latest/policies-pdk-upgrade-pdk
- **PDK overview:** https://docs.mulesoft.com/pdk/latest/
- **Custom policy examples (docs):** https://docs.mulesoft.com/pdk/latest/policies-pdk-policy-templates
- **Sibling skill `pdk-templates`:** vetted Rust snippets for 30 PDK features (JWT, OAuth2, rate limiting, header manipulation, gRPC, DataWeave, etc.) — drop-in code for `src/lib.rs`.
- **Sibling skill `pdk-unit`:** unit-testing workflow for custom policies — wire `src/tests/`, write `UnitTestBuilder` tests, mock upstreams, assert on responses/violations, run `make test`.

---

**Need help?** Failing at a specific step usually means a tooling version mismatch. Re-run Step 1 — it's cheap and rules out the most common class of issues before deeper debugging.
