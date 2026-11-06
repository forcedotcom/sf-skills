# AgentScript Compiler Setup and Provenance

For every authoring, repair, or audit task with an existing `.agent` file, run
the bundled compiler locally before target-org validation. This is the cheap,
repeatable first pass even when the customer has an authenticated org. The
customer should not need to clone this skills repository or modify their
project dependencies.

## Provider order

Use the first working local provider and record it:

1. an explicit `AGENTSCRIPT_SDK_ENTRY` override, when the user supplied one;
2. the last successfully verified SDK in the skill-owned cache;
3. an AgentScript SDK already installed in the customer project or skill host;
4. the public npm package installed into the skill-owned cache;
5. a fresh build from the public `salesforce/agentscript` source repository.

After the local pass, use target-org validation when an authenticated org is
available. The two checks are complementary: the local compiler provides fast
feedback, while the org establishes what that deployment target accepts. Use a
bounded static review only when no local compiler or org validation surface is
available.

An absent or unauthenticated org is not a reason to skip the local compiler.
Local compilation does not require org access. Do not report “no org” as the
cause of **compiler not used**; attempt the local providers below and report the
actual setup or loading failure if none works.

Compiler setup must not become an all-or-nothing gate. Try each applicable
install provider once. If installation fails, retain the error, continue with
the strongest remaining validation surface, and state **compiler not used**
with the cause rather than abandoning the authoring or audit result.

## Install from npm

Resolve the installed `agentforce-generate` skill directory and run:

```bash
node <skill-directory>/scripts/setup-agentscript-sdk.mjs --npm --json
```

The setup script installs the pinned public
`@sf-agentscript/agentforce` package into the user cache, not the customer
project or global npm prefix. It then runs a compiler smoke test and records the
resolved package version and entry point.

If evidence indicates that the bundled npm pin is behind the currently
published package, retry once with an exact newer version or `latest` and retain
the resolved version:

```bash
node <skill-directory>/scripts/setup-agentscript-sdk.mjs \
  --npm --version latest --force --json
```

Do not call a package current merely because `latest` resolved. Compare its
diagnostics with the syntax under review, the public source revision when
needed, and the deployment org before release.

## Build from public source

Use the source fallback when the npm package is unavailable, cannot load, or
appears older than the syntax under review:

```bash
node <skill-directory>/scripts/setup-agentscript-sdk.mjs \
  --source --source-ref main --force --json
```

This downloads `https://github.com/salesforce/agentscript.git` into the same
skill-owned cache, records the exact fetched commit, installs its pinned pnpm
dependencies, builds the Agentforce SDK and its dependencies, and runs the same
compiler smoke test. It requires Git, either pnpm or Corepack-provided pnpm, and
the operating-system build prerequisites required by the selected public
source revision. A missing native build prerequisite is an installation failure
to report and fall back from; it is not a reason to abandon the audit.

Use a tag or commit with `--source-ref` when reproducibility matters. A source
build can be newer than the deployment org; it is evidence about that source
revision, not proof that an org accepts the same syntax.

## Use and report the compiler

Run the bundled indexer after setup:

```bash
node <skill-directory>/scripts/index-agent.mjs <agent-file>
```

The JSON result includes a `compiler` object. Always carry these fields into
the audit or authoring report:

- provider: ambient npm, cached npm, public source, or explicit entry;
- exact npm package and resolved version, when applicable;
- exact source commit, when applicable;
- compiler entry path;
- whether target-org validation also ran.

If the indexer was not run, say so. If it failed before loading a compiler,
report **compiler not used** and the reason. Never describe a prompt-only or
regex inspection as compiler validation.

## Overrides and cache

- `AGENTSCRIPT_SDK_ENTRY` selects a specific built SDK entry file.
- `AGENTFORCE_GENERATE_CACHE` selects a different cache root.
- `XDG_CACHE_HOME` changes the standard cache root.

The default cache is `.cache/agentforce-generate` under the current user's home
directory. Setup writes only below the selected cache root and does not install
global packages.
