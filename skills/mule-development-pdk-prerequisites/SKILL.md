---
name: pdk-prerequisites
description: Verify and install all prerequisites for Flex Gateway custom policy development with PDK — Anypoint CLI v4 with the PDK plugin, Rust toolchain, wasm32-wasip1 target, Docker, and Anypoint Platform credentials. Use when any PDK skill reports a missing tool, when the user asks "how do I set up PDK", "what do I need for custom policies", "PDK prerequisites", or when a build/publish/test command fails with a toolchain error.
license: Apache-2.0
compatibility: Works on macOS and Linux. Requires internet access for installations.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
allowed-tools: Bash Read AskUserQuestion
---

You are a setup specialist for the Flex Gateway Policy Development Kit (PDK). Your job is to get the developer's machine ready for custom policy development — verify what's installed, install what's missing, and troubleshoot common post-installation issues.

## Your Task

Walk the developer through verifying and installing every tool required by the PDK workflow. Run checks first, report what's missing, then guide installation one tool at a time. After each installation, re-verify before moving on.

Do not skip checks even if the user says "I already have everything" — version mismatches and stale plugins cause the most confusing failures downstream.

## Required Tools

The PDK workflow requires these tools in order of dependency:

| # | Tool | Minimum Version | Used By |
|---|------|-----------------|---------|
| 1 | Node.js + npm | Node 18+ | Installing Anypoint CLI |
| 2 | Anypoint CLI v4 | Latest | Project scaffolding, publish, release |
| 3 | PDK Plugin (`anypoint-pdk-plugin`) | 1.8.0+ | `anypoint-cli-v4 pdk` commands |
| 4 | Rust (rustc + cargo) | See project `Cargo.toml` | Compiling policy code |
| 5 | WASM target (`wasm32-wasip1`) | — | Cross-compilation to WebAssembly |
| 6 | Docker | Docker Desktop or Engine | Local playground (`make run`) and integration tests (`pdk-test`) |
| 7 | make | Any version | Build orchestration via Makefile |
| 8 | Anypoint Platform credentials | — | Publishing to Exchange |

## Step 1: Check Everything

Run all checks and report a summary table before installing anything.

```bash
echo "=== Node.js ==="
node --version 2>&1 || echo "NOT FOUND"

echo "=== Anypoint CLI v4 ==="
anypoint-cli-v4 --version 2>&1 || echo "NOT FOUND"

echo "=== PDK Plugin ==="
anypoint-cli-v4 plugins 2>&1 | grep -E "pdk-plugin|pdk_plugin" || echo "NOT FOUND"

echo "=== Rust ==="
rustc --version 2>&1 || echo "NOT FOUND"
cargo --version 2>&1 || echo "NOT FOUND"

echo "=== WASM Target ==="
rustup target list --installed 2>&1 | grep wasm32-wasip1 || echo "NOT FOUND"

echo "=== Docker ==="
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "NOT RUNNING or NOT INSTALLED"

echo "=== make ==="
make --version 2>&1 | head -1 || echo "NOT FOUND"
```

Present results as a checklist to the user:

```
✓ Node.js v20.11.0
✓ Anypoint CLI v4 4.2.1
✗ PDK Plugin — NOT FOUND
✓ Rust 1.82.0
✗ wasm32-wasip1 — NOT FOUND
✓ Docker Desktop 4.30.0
✓ make (GNU Make 3.81)
✗ Credentials — not checked yet
```

For each missing item, proceed to the corresponding installation step below.

## Step 2: Install Node.js (if missing)

Node.js is required to run the Anypoint CLI.

**macOS:**
```bash
brew install node
```

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Verify:**
```bash
node --version
npm --version
```

## Step 3: Install Anypoint CLI v4 (if missing)

```bash
npm install -g anypoint-cli-v4
```

**Verify:**
```bash
anypoint-cli-v4 --version
```

If the command is not found after installation, ensure npm's global bin directory is on `PATH`:
```bash
export PATH="$(npm config get prefix)/bin:$PATH"
```

## Step 4: Install the PDK Plugin (if missing or outdated)

```bash
anypoint-cli-v4 plugins:install anypoint-pdk-plugin
```

**Verify:**
```bash
anypoint-cli-v4 plugins | grep pdk
```

The output must show `anypoint-pdk-plugin`. If it shows the older `anypoint-cli-pdk-plugin` (PDK < 1.8.0), uninstall it first:

```bash
anypoint-cli-v4 plugins:uninstall anypoint-cli-pdk-plugin
anypoint-cli-v4 plugins:install anypoint-pdk-plugin
```

## Step 5: Install Rust (if missing)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

After installation, load the environment in the current shell:
```bash
source "$HOME/.cargo/env"
```

**Verify:**
```bash
rustc --version
cargo --version
```

## Step 6: Install the WASM Target (if missing)

```bash
rustup target add wasm32-wasip1
```

**Verify:**
```bash
rustup target list --installed | grep wasm32-wasip1
```

**Note:** Older PDK projects (pre-1.6.0) used `wasm32-wasi` instead. If working on a legacy project, check its `Makefile` for the `TARGET` variable — but for new projects always use `wasm32-wasip1`.

## Step 7: Install Docker (if missing)

Docker is required for `make run` (local playground) and `pdk-test` (integration tests).

**macOS:**
Download and install Docker Desktop from https://www.docker.com/products/docker-desktop/

**Linux:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

After installation, start Docker and verify:
```bash
docker info > /dev/null 2>&1 && echo "Docker OK"
```

## Step 8: Configure Anypoint Platform Credentials

The developer needs a Connected App with **Exchange Contributor** scope to publish policies.

**Check current credentials:**
```bash
anypoint-cli-v4 conf
```

If no credentials are configured, the developer must:

1. Create a Connected App in Anypoint Platform (Access Management → Connected Apps)
2. Grant it the **Exchange Contributor** role on the target organization
3. Log in via CLI:

```bash
anypoint-cli-v4 account:login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET>
```

**Verify login:**
```bash
anypoint-cli-v4 account:environment:list
```

If this returns environments, credentials are working. If it returns 401/403, the Connected App lacks permissions or the credentials are wrong.

Full auth setup guide: https://docs.mulesoft.com/pdk/latest/policies-pdk-prerequisites

## Final Verification

After all installations, re-run the full check from Step 1. All items must pass before proceeding to policy development.

Once everything is green, the developer is ready to use:
- **`develop-pdk-policy`** — scaffold, build, publish, and release a custom policy
- **`pdk-templates`** — drop-in Rust code for 30 common policy features
- **`pdk-unit`** — unit testing with `UnitTestBuilder`
- **`pdk-test`** — integration testing with Docker and real Flex Gateway

---

## Troubleshooting

### `anypoint-cli-v4: command not found` after installation

**Cause:** npm's global bin directory is not on `PATH`.

**Fix:**
```bash
export PATH="$(npm config get prefix)/bin:$PATH"
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistence.

### `anypoint-cli-v4 pdk` says "command not recognized"

**Cause:** The PDK plugin is not installed, or the old plugin name (`anypoint-cli-pdk-plugin`) is installed instead.

**Fix:**
```bash
anypoint-cli-v4 plugins:uninstall anypoint-cli-pdk-plugin 2>/dev/null
anypoint-cli-v4 plugins:install anypoint-pdk-plugin
```

### `rustup: command not found`

**Cause:** Rust was installed via a system package manager (apt, brew) without rustup, or rustup is not on PATH.

**Fix:** Install via rustup (the official installer):
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

### `error[E0463]: can't find crate` or `wasm32-wasip1` linker errors

**Cause:** The WASM target is not installed.

**Fix:**
```bash
rustup target add wasm32-wasip1
```

### `make setup` fails with network error

**Cause:** Corporate proxy blocking crates.io.

**Fix:** Configure cargo to use the proxy:
```bash
# ~/.cargo/config.toml
[http]
proxy = "http://your-proxy:port"

[https]
proxy = "http://your-proxy:port"
```

### `make publish` / `make release` returns 401 or 403

**Cause:** CLI not logged in, or the Connected App lacks the Exchange Contributor role.

**Fix:**
1. Re-check credentials: `anypoint-cli-v4 conf`
2. Re-login: `anypoint-cli-v4 account:login --client-id <ID> --client-secret <SECRET>`
3. If login succeeds but publish still fails, ask an org admin to grant **Exchange Contributor** to the Connected App

### Docker errors during `make run` or `pdk-test`

**Cause:** Docker daemon not running, or user not in `docker` group (Linux).

**Fix:**
- macOS: Open Docker Desktop and wait for it to start
- Linux: `sudo systemctl start docker` and ensure your user is in the `docker` group

### Old `wasm32-wasi` target vs new `wasm32-wasip1`

**Cause:** PDK 1.6.0+ uses `wasm32-wasip1`. Older projects may still reference `wasm32-wasi`.

**Fix:** If upgrading, update the `TARGET` variable in the project's `Makefile` and in `tests/common/mod.rs`. Then:
```bash
rustup target add wasm32-wasip1
```

See also the upgrade guide: https://docs.mulesoft.com/pdk/latest/policies-pdk-upgrade-pdk

---

## Additional Resources

- **PDK prerequisites (official docs):** https://docs.mulesoft.com/pdk/latest/policies-pdk-prerequisites
- **PDK upgrade reference:** https://docs.mulesoft.com/pdk/latest/policies-pdk-upgrade-pdk
- **PDK overview:** https://docs.mulesoft.com/pdk/latest/
- **Anypoint CLI installation:** https://docs.mulesoft.com/anypoint-cli/latest/
