# Data Cloud Community Plugin Setup

The orchestrating-datacloud family uses a **community `sf data360` CLI runtime**. sf-skills does not vendor or fork that plugin.

## Why this setup exists

- keeps sf-skills focused on skills, prompts, docs, and templates
- lets the upstream runtime continue to evolve independently
- avoids MCP and keeps execution deterministic

## Prerequisites

- Node.js 18+
- yarn
- Salesforce CLI (`sf`)
- git
- a Data Cloud-enabled org authenticated with `sf org login web -a <alias>`

## Recommended setup path

The command examples below assume the skill is installed under `~/.claude/skills/` via the full Claude Code installer. If you are working from a cloned sf-skills repo instead, run the same scripts from that checkout path.

If you use the Python installer, it can install this optional runtime for you:

```bash
python3 ~/.claude/sf-skills-install.py --with-datacloud-runtime
```

Or use the helper script directly:

```bash
bash ~/.claude/skills/orchestrating-datacloud/scripts/bootstrap-plugin.sh
```

By default it clones the plugin into `~/.sf-community-tools/datacloud/sf-cli-plugin-data360`, installs dependencies, compiles it, and links it into the local Salesforce CLI.

## Manual setup

```bash
git clone https://github.com/Jaganpro/sf-cli-plugin-data360.git
cd sf-cli-plugin-data360
yarn install
npx tsc
node ~/.claude/skills/orchestrating-datacloud/scripts/generate-manifest.mjs .
sf plugins link .
```

## Verification

```bash
sf data360 man
bash ~/.claude/skills/orchestrating-datacloud/scripts/verify-plugin.sh
bash ~/.claude/skills/orchestrating-datacloud/scripts/verify-plugin.sh myorg
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o myorg --json
```

For newer command families such as `sf data360 query hybrid` and recent pagination fixes, update the community runtime to the latest upstream commit by re-running the bootstrap helper.

`sf data360 doctor` is useful, but it is not the only readiness signal. On partially provisioned orgs it can fail even when other read-only Data Cloud commands still work. The helper script treats `doctor` as advisory and falls back to additional smoke checks.

Use `diagnose-org.mjs` when you need phase-specific readiness classification instead of a simple pass/fail check. It helps distinguish:
- empty-but-enabled modules
- feature-gated modules
- query-plane issues
- runtime/auth failures

## Output-noise tip

When using linked community plugins, stderr can include warning noise. For normal usage, prefer:

```bash
sf data360 dmo list --all -o myorg 2>/dev/null
sf data360 segment list -o myorg 2>/dev/null
```

## Troubleshooting

### ESM auto-transpile warning

If you see `Warning: @gthoppae/sf-cli-plugin-data360 is a linked ESM module and cannot be auto-transpiled`, generate the oclif command manifest:

```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/generate-manifest.mjs ~/.sf-community-tools/datacloud/sf-cli-plugin-data360
```

This tells oclif to use pre-compiled output directly instead of attempting auto-transpilation. The `npx oclif manifest` alternative may fail on newer Node.js versions due to `@oclif/core` version mismatches.

### Clone error references `gthoppae/sf-cli-plugin-data360`

If the clone failure mentions `gthoppae/sf-cli-plugin-data360`, your local `~/.claude/sf-skills-install.py` copy is outdated. Refresh the installer first, then retry the optional runtime install:

```bash
python3 ~/.claude/sf-skills-install.py --force-update
python3 ~/.claude/sf-skills-install.py --with-datacloud-runtime
```

Or rerun the latest installer directly from GitHub:

```bash
curl -sSL https://raw.githubusercontent.com/Jaganpro/sf-skills/main/tools/install.py | python3 - --with-datacloud-runtime
```

### Plugin not found after install

If `sf` was installed globally (with `sudo`), the default data directory may be root-owned. Set `SF_DATA_DIR` in your shell profile:

```bash
export SF_DATA_DIR="${HOME}/.local/share/sf"
```

Then re-run `sf plugins link .` from the plugin directory, or re-run the bootstrap script.

## What to do if the plugin is missing

1. run the bootstrap script
2. re-open your shell if `sf` plugin discovery is stale
3. verify with `sf data360 man`
4. only then start live Data Cloud work

## Setup guidance reminder

The runtime can help you **detect** missing capability, but it cannot fully replace Setup for:
- initial Data Cloud provisioning / tenant creation
- license assignment
- every org-wide feature enablement step

When a module is gated, guide users toward the right setup area instead of promising a fully programmatic enablement flow. See [feature-readiness.md](feature-readiness.md).

## Scope reminder

This setup is for the Data Cloud product family:
- `orchestrating-datacloud`
- `connecting-datacloud`
- `preparing-datacloud`
- `harmonizing-datacloud`
- `segmenting-datacloud`
- `activating-datacloud`
- `retrieving-datacloud`

For STDM/session tracing/parquet work, use `observing-agentforce` instead of this plugin-focused family.
