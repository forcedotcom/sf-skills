---
name: dx-org-devhub-configure
description: "Enable Dev Hub on a Salesforce org and view its scratch org allocation, using the Salesforce CLI (sf). Use when someone wants to turn on or enable Dev Hub, set up an org to create scratch orgs or second-generation (2GP) and unlocked packages, check whether Dev Hub is already enabled, see how many scratch orgs they can create (Active and Daily scratch org limits, remaining allocation), configure Dev Hub preferences such as packaging, org shape export, or scratch org snapshots, or list the active scratch orgs created from a Dev Hub. Enabling deploys the enableScratchOrgManagementPref setting, is irreversible, needs a System Administrator (ModifyAllData or ModifyMetadata), and does not work in sandboxes. DO NOT TRIGGER for creating or deleting individual scratch orgs, for switching the default org (use dx-org-switch), or for trial or org expiration dates (use dx-org-trial-expiration-check)."
allowed-tools: Read, Bash(bash), Bash(sf api request rest), Bash(sf data query), Bash(sf org list), Bash(sf org login web), Bash(sf org login device), Bash(sf project deploy), Bash(sf config get), Bash(sf org display), Bash(sf org open), Bash(jq)
metadata:
  version: "1.0"
  # DevHubSettings metadata + the Tooling API DevHubSettings endpoint require
  # API 47.0 or later (see scripts/devhub.sh SETTINGS_API_VERSION).
  minApiVersion: "47.0"
  relatedSkills:
    - "dx-org-switch"
    - "dx-org-trial-expiration-check"
  # Enabling needs ModifyAllData OR ModifyMetadata (either suffices). accessCheck
  # is a flat array with no OR operator, so declaring both would read as AND and
  # could falsely gate an admin holding only one. Declare the canonical
  # System-Administrator perm; the OR alternative stays documented in the
  # description and body.
  accessCheck:
    - type: "userPerm"
      value: "ModifyAllData"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Enable Dev Hub & View Scratch Org Allocation

Enable **Dev Hub** on a Salesforce org, verify whether it is already on, and see
the org's **scratch org allocation** (Active and Daily limits and how many
remain) — for the default org or a named org. The skill can also configure Dev
Hub sub-preferences (packaging, org shape export, scratch org snapshots) and
list the active scratch orgs created from a Dev Hub.

Dev Hub is the org feature that lets you **create and manage scratch orgs** and
**second-generation (2GP) / unlocked packages**.

## When to use

Trigger on requests like:

- "Enable Dev Hub" / "Turn on Dev Hub" / "Set up this org for scratch orgs."
- "Is Dev Hub enabled on my org?" / "Check if Dev Hub is on."
- "How many scratch orgs can I create?" / "What's my scratch org allocation /
  limit?" / "How many scratch orgs do I have left?"
- "Turn on packaging / 2GP / unlocked packages" / "Enable org shape export" /
  "Enable scratch org snapshots" (Dev Hub sub-preferences).
- "List the scratch orgs on my Dev Hub."

## When NOT to use

Do **not** trigger this skill for:

- **Creating or deleting an individual scratch org** — that is
  `sf org create scratch` / `sf org delete scratch`, a different workflow. This
  skill enables the *Dev Hub feature* and reports *allocation*; it does not
  create scratch orgs.
- **Switching the default/active org** — use `dx-org-switch`.
- **Trial or org expiration dates** ("when does my org expire") — use
  `dx-org-trial-expiration-check`.

## How Dev Hub enablement is determined

The standard object **`ScratchOrgInfo`** is provisioned and becomes queryable
**only when Dev Hub is enabled**. So a successful `SELECT COUNT() FROM
ScratchOrgInfo` means Dev Hub is **ON**; an `INVALID_TYPE` error means it is
**OFF**. This is the reliable signal.

> Do **not** infer enablement from `sf org list limits` alone: it reports
> `ActiveScratchOrgs` / `DailyScratchOrgs` rows even on orgs where Dev Hub is
> **off**, so limits show allocation but not enablement.

## How enabling works (important)

- The Dev Hub master switch is the **deployable** Metadata API field
  **`DevHubSettings.enableScratchOrgManagementPref`**. There is **no**
  `enableDevHub` field and **no** dedicated `sf` command to turn it on —
  deploying this setting is exactly what the Setup toggle does.
- **Enabling is irreversible** — once on, Dev Hub cannot be turned off.
- **Requires** a user with **ModifyAllData** or **ModifyMetadata** (a **System
  Administrator** has these). A user without them gets `INSUFFICIENT_ACCESS`.
- **Cannot** be enabled in a **sandbox**, or in an org that has a **registered
  namespace**.
- Available in **Developer, Enterprise, Performance, Unlimited**, and **trial**
  editions.

## Steps

1. **CRITICAL:** Run the bundled helper script, which handles Dev Hub detection,
   the enablement deploy (with a safe dry-run default), allocation math, and
   structured output, and works on macOS and Linux. Always invoke it by
   **absolute path** from the skill directory — never `./scripts/`, which
   resolves against the user's current directory and will either run the wrong
   script or fail. The script self-checks this: if `$0` is not absolute it exits
   with a usage error, so pass the full path to `<skill_dir>` (the directory
   containing this SKILL.md).

   ```bash
   bash "<skill_dir>/scripts/devhub.sh" <alias-or-username>            # status: on? + allocation
   bash "<skill_dir>/scripts/devhub.sh"                               # default org (target-org)
   bash "<skill_dir>/scripts/devhub.sh" <org> --allocation           # allocation only
   bash "<skill_dir>/scripts/devhub.sh" <org> --enable               # validate enabling (dry run)
   bash "<skill_dir>/scripts/devhub.sh" <org> --enable --apply       # actually enable (irreversible)
   bash "<skill_dir>/scripts/devhub.sh" <org> --list-scratch         # list active scratch orgs
   bash "<skill_dir>/scripts/devhub.sh" <alias> --instance-url <url> --enable --apply  # log in first, then enable
   bash "<skill_dir>/scripts/devhub.sh" <url>                        # bare instance URL: log in to it
   ```

   When the user supplies an instance URL (their My Domain, sandbox, or
   pre-release/scratch login URL — e.g.
   `https://my-domain.my.salesforce.com`), pass that exact URL with
   `--instance-url <url>` — the script accepts Salesforce-owned hostnames and logs in with
   `sf org login web --instance-url <url>` and then continues. A bare URL
   positional is accepted as shorthand for the same thing.

   `<skill_dir>` is the absolute path to the directory containing this SKILL.md.

2. **For enablement, default to a dry run first.** Run `--enable` (no `--apply`)
   to validate the deploy, then relay the result. Because enabling is
   **irreversible**, only run `--enable --apply` when the user has clearly asked
   to actually enable Dev Hub. Applied operations require an explicit org alias
   or username; the script refuses to mutate an implicit default org. If the
   deploy is rejected for permissions, surface the Setup-UI fallback it prints.

3. Relay the script output. When an org can't be queried, surface the
   `sf org login web` command the script prints so the user can authenticate.
   Pick optional flags based on the request (see below): `--allocation` for
   limits only, `--list-scratch` to enumerate scratch orgs, `--packaging` /
   `--snapshots` / `--shape` to turn on sub-preferences, `--json` for automation.

## Before you finish

Verify these before returning your answer:

- [ ] **CRITICAL:** Invoked the helper via its **absolute path** (`bash "<skill_dir>/scripts/devhub.sh" …`), never `./scripts/` (the script rejects a non-absolute `$0`).
- [ ] Did **not** run `--apply` unless the user clearly asked to actually enable Dev Hub or deploy a preference — enabling is **irreversible**.
- [ ] Relayed the script's own output (status/allocation or the login/Setup-UI guidance it printed), rather than substituting a hand-written answer.

## Options

| Flag | Purpose |
|------|---------|
| `--allocation`, `-A` | Show only the scratch org allocation (Active/Daily). |
| `--list-scratch`, `-l` | List active scratch orgs created from this Dev Hub. |
| `--enable`, `-e` | Enable Dev Hub (deploys `enableScratchOrgManagementPref=true`). Dry run unless `--apply`. |
| `--configure`, `-c` | Configure sub-preferences without (re)enabling the master switch. Pair with a pref flag. |
| `--packaging` | `enablePackaging2=true` (Unlocked + 2GP packages). |
| `--snapshots` | `enableScratchOrgSnapshotPref=true`. |
| `--shape` | `enableShapeExportPref=true`. |
| `--scratch-management` | `enableScratchOrgManagementPref=true` (the Dev Hub switch). |
| `--pref KEY=VALUE` | Any `DevHubSettings` sub-pref (KEY starts with `enable`, VALUE `true`/`false`). Repeatable. |
| `--apply` | Actually deploy to the explicit org argument. Default for `--enable`/`--configure` is a validate-only dry run. |
| `--login` | Authenticate an org first via `sf org login web` (opens a browser), then run the action. |
| `--instance-url <url>` | Log in to a specific instance (My Domain, sandbox, or pre-release/scratch instance) with `sf org login web --instance-url <url>`. Implies `--login`. |
| `--json` | Emit machine-readable JSON. |
| `--fail-if-disabled` | Exit `3` if Dev Hub is not enabled (CI/cron gate). |
| `--help`, `-h` | Show usage. |

`--enable` may be combined with sub-pref flags to enable and configure at once
(e.g. `--enable --packaging --apply`). If omitted, the org defaults to
`target-org`, then `target-dev-hub`.

## Output examples

The script prints the authoritative output at runtime. If you need to calibrate
what an enabled-vs-disabled status transcript looks like (including the
allocation table and the enable/Setup-UI guidance), read
[`examples/status-output.md`](examples/status-output.md) — otherwise skip it to
keep this workflow lean.

## Structured output for automation (`--json`)

Use `--json` in any mode for machine-readable output (no prose). Status returns
`devHubEnabled`, `status`, and an `allocation` object; enablement returns
`success`, `applied`, and `devHubVerifiedState`. Deterministic, no LLM needed.

```bash
bash "<skill_dir>/scripts/devhub.sh" my-devhub --json
# {"org":"my-devhub","devHubEnabled":true,"status":"enabled", ... }
```

`--fail-if-disabled` exits `3` (and prints an `ALERT:` line to stderr) if Dev
Hub is not enabled, so a scheduled job can gate on it.

## Exit codes

- `0` success
- `1` an org could not be queried, or a deploy failed (auth/connection/deploy)
- `2` bad usage or a missing dependency (`sf` or `jq`)
- `3` Dev Hub is not enabled (only when `--fail-if-disabled` is set)

## Authentication

If the org isn't authenticated yet, the skill can log in for you with
`--login` (or `--instance-url <url>`), then continue with the requested action
in the same run — this is the preferred path when the user provides an instance
URL:

Substitute the user's actual instance URL for `<url>` (shown here as the generic
`https://my-domain.my.salesforce.com` placeholder):

```bash
# Log in to a specific instance (My Domain / pre-release / sandbox), then enable:
bash "<skill_dir>/scripts/devhub.sh" my-alias \
  --instance-url https://my-domain.my.salesforce.com --enable --apply

# Bare instance URL as shorthand — logs in to it, then reports status:
bash "<skill_dir>/scripts/devhub.sh" https://my-domain.my.salesforce.com

# Just authenticate an org (no other action):
bash "<skill_dir>/scripts/devhub.sh" my-alias --login
```

`sf org login web` opens a browser for the OAuth flow; complete it promptly (the
session times out). A supplied positional (`my-alias`) becomes the CLI alias; a
positional that looks like a URL (contains `://`) is taken as the
`--instance-url` to log in to. The script accepts only HTTPS Salesforce-owned
hostnames for this option. Omit `--instance-url` for standard
production/DE/trial logins (`login.salesforce.com`). If the browser flow keeps
timing out, the script prints the `sf org login device` fallback for a
code-based login.

If an org isn't authenticated and no login flag was passed, the script instead
prints the exact command to log in and re-run — using the instance URL you
supplied when there is one:

```text
  my-org                         could not query org (...)

  To authenticate against https://my-domain.my.salesforce.com, run:
    sf org login web --instance-url "https://my-domain.my.salesforce.com" --alias "my-org"
  Or let this script log you in and continue in one step:
    devhub.sh "my-org" --instance-url "https://my-domain.my.salesforce.com" --login
  Then re-run. List existing logins with:  sf org list
```

## Manual fallback (if the script is unavailable)

```bash
# Detect Dev Hub (INVALID_TYPE error means OFF; a count means ON):
sf data query --query "SELECT COUNT() FROM ScratchOrgInfo" --target-org <org> --json

# Enable Dev Hub via the Tooling API (what the Setup toggle does; irreversible):
sf api request rest "/services/data/v47.0/tooling/sobjects/DevHubSettings/DevHub" \
  --method PATCH \
  --body '{"FullName":"DevHub","Metadata":{"enableScratchOrgManagementPref":true}}' \
  --target-org <org>

# Or enable in the UI: Setup > Quick Find > "Dev Hub" > turn Enable Dev Hub On.

# View scratch org allocation:
sf org list limits --target-org <org> --json | jq '.result[] | select(.name|test("ScratchOrg"))'
```

## Notes

- Requires the Salesforce CLI (`sf`) and `jq` on the PATH, plus at least one
  authenticated org (`sf org login web`).
- After enabling, set the org as your default Dev Hub:
  `sf config set target-dev-hub <org>`.
- Enabling **packaging** (`enablePackaging2`) requires Dev Hub to be on first —
  `--enable --packaging` handles the ordering in a single deploy.
- Non-admin users still need object access (Read/Create on `ScratchOrgInfo` and
  `ActiveScratchOrg`) to create/view scratch orgs, and the "Create and Update
  Second-Generation Packages" permission to build 2GP/unlocked packages.
- To *switch* the default org use `dx-org-switch`; to check *expiration* use
  `dx-org-trial-expiration-check`.
