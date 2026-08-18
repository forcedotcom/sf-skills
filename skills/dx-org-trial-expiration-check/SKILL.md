---
name: dx-org-trial-expiration-check
description: "Check when Salesforce orgs expire (or already expired) and what to do about it, for one org, the default org, or across all authenticated orgs, using the Salesforce CLI (sf). Use when the user asks about org or trial expiration, \"when does my trial expire\", \"is my trial org still active\", \"how many days are left\", \"which orgs are expiring soon\", wants to filter orgs expiring within N days, needs machine-readable (JSON/CSV) output for cron or alerting, wants to back up an at-risk org before it lapses, or asks how to extend or renew an expiring trial or Developer Edition org. Covers trial editions, Developer Edition orgs (anything with a TrialExpirationDate), and scratch orgs (via sf org list). DO NOT TRIGGER for sandbox refresh timing, for creating, deleting, or switching the active org, or for non-Salesforce trials such as AWS, Netflix, or other vendors — this skill reads expiration and prints guidance, it does not modify orgs."
allowed-tools: Read, Bash(bash), Bash(sf data query), Bash(sf org list), Bash(sf config get), Bash(jq), Bash(date)
metadata:
  version: "2.0"
  domains: ["Developer Experience"]
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Org Expiration Check

Determine when a Salesforce org expires, how many days remain, and whether it
has already expired — for one org, the default org, or every authenticated org.
Results are **prioritized** (already-expired and soonest-expiring first) with a
one-line summary. The skill can also emit machine-readable output for alerting,
print **backup** commands for an at-risk org, and explain how to **renew** an
expiring trial or Developer Edition org.

## When to use

Trigger on requests like:

- "When does my trial org expire?" / "Is it still active or has it expired?"
- "How many days are left on my trial?"
- "Which of my orgs are expiring soon?" / "expiring within 30 days?"
- "Alert me / set up a cron job for expiring orgs" (use `--json` + `--fail-if-expiring`).
- "Back up my org before it expires" (use `--preserve`).
- "How do I extend / renew my trial (or Developer Edition) org?" (use `--renew`).

This skill covers **trial editions, Developer Edition orgs** (anything with a
`TrialExpirationDate`), and **scratch orgs** (via the `expirationDate` from
`sf org list`).

## When NOT to use

Do **not** trigger this skill for:

- **Sandbox refresh timing** — that is not an expiration date.
- **Creating, deleting, or switching orgs** — this skill only *reads*
  expiration and *prints* guidance; it never creates, deletes, refreshes, or
  changes the active/default org. (To switch the default org, use
  `dx-org-switch`.)
- **Non-Salesforce trials** — e.g. AWS free tier, Netflix, or any other
  vendor's trial. This skill is Salesforce-only.

## How expiration is determined

- **Trial / Developer Edition orgs:** the authoritative source is the org's
  `Organization.TrialExpirationDate` field, read via SOQL (`sf data query`).
  This field is `null` for paid/production orgs, which therefore report **no
  trial expiration** — that is expected, not an error.
- **Scratch orgs:** the `expirationDate` reported by `sf org list` (no SOQL
  query is issued for scratch orgs).

## Steps

1. **CRITICAL:** Run the bundled helper script, which handles date math (days
   remaining, expired, expiring-soon warnings), prioritized sorting, and
   structured output, and works on macOS and Linux. Always invoke it by
   **absolute path** from the skill directory — never `./scripts/`, which
   resolves against the user's current directory and will either run the wrong
   script or fail.

   **Before executing, verify:**
   - [ ] `<skill_dir>` is an absolute path (starts with `/`), not a relative path
   - [ ] The path points at this skill's own directory (the one containing this SKILL.md)

   ```bash
   bash "<skill_dir>/scripts/check_expiration.sh" <alias-or-username>   # one org
   bash "<skill_dir>/scripts/check_expiration.sh"                       # default org (target-org config)
   bash "<skill_dir>/scripts/check_expiration.sh" --all                 # every authenticated org
   bash "<skill_dir>/scripts/check_expiration.sh" --all --within 30     # only orgs expiring within 30 days
   ```

   `<skill_dir>` is the absolute path to the directory containing this SKILL.md.

2. Relay the script output to the user. When an org could not be queried,
   surface the `sf org login web` command the script prints so the user can
   authenticate. Pick optional flags based on what the user asked for (see
   below): `--preserve` when they want to save their work, `--renew` when they
   ask how to extend, `--json`/`--csv` for automation, `--fail-if-expiring`
   for a cron/CI gate.

## Options

| Flag | Purpose |
|------|---------|
| `--all`, `-a` | Check every authenticated org. |
| `--within <days>`, `-w` | Show only orgs expiring within N days (includes already-expired; omits paid/production). `--within=30` also works. |
| `--json` | Emit a JSON array of org records (data only). |
| `--csv` | Emit CSV rows (data only). |
| `--preserve` | Print backup commands for expiring/expired orgs. |
| `--renew` | Print trial/DE extension & reactivation guidance. |
| `--fail-if-expiring[=N]` | Exit 3 if any org expires within N days (default 7). |
| `--no-scratch` | Exclude scratch orgs (trial/DE only). |
| `--help`, `-h` | Show usage. |

Flag order is flexible and flags combine (e.g. `--all --within 30 --json`).

## Prioritized output

Human output is grouped by urgency — **Expired** first, then **Expiring soon**
(within 7 days, flagged `Warning`), then **Active**, then **No trial expiration**,
then any orgs that could not be queried — and ends with a one-line summary:

```text
Org expiration status for all authenticated orgs:

Expired:
  old-trial                       trial/DE edition expired 2026-06-20  (EXPIRED 19 day(s) ago)

Expiring soon (within 7 day(s)):
  almost-up                       trial/DE edition expires 2026-07-14  (expires in 5 day(s)  Warning)

Active (not expiring soon):
  acme-trial                      trial/DE edition expires 2026-08-15  (expires in 37 day(s))
  my-scratch                      scratch org expires 2026-07-25  (expires in 16 day(s))

No trial expiration (paid/production):
  prod                            no trial expiration (paid/production org)

Summary: 1 expired, 1 expiring within 7 day(s), 2 active, 1 with no expiration.
```

## Structured output for alerting and cron (`--json` / `--csv`)

For dashboards, spreadsheets, or scheduled jobs, use `--json` or `--csv` to get
machine-readable records (no prose). Each record has `org`, `kind`,
`expirationDate`, `daysRemaining` (negative = expired, `null` = no expiration),
`status`, and `orgId`. This is deterministic and needs no LLM in the loop.

```bash
# JSON, filtered to orgs expiring within 30 days:
bash "<skill_dir>/scripts/check_expiration.sh" --all --within 30 --json
```

**Cron watchdog** — `--fail-if-expiring[=N]` exits `3` (and prints an `ALERT:`
line to stderr) if any org expires within N days (default 7), so a scheduled
job can page you before an org lapses:

```bash
# crontab: every morning at 9, alert if anything expires within 7 days
0 9 * * *  bash "<skill_dir>/scripts/check_expiration.sh" --all --fail-if-expiring 7 \
             || mail -s "Salesforce org expiring soon" me@example.com
```

## Preserve your work before an org lapses (`--preserve`)

When an org expires you lose access to its metadata and data. `--preserve`
prints ready-to-run backup commands (metadata manifest + `retrieve`, and a bulk
data export) for each expiring or already-expired org. It only *prints* the
commands — review and run them yourself:

```bash
bash "<skill_dir>/scripts/check_expiration.sh" my-trial --preserve
```

## Extend or renew a trial / Developer Edition org (`--renew`)

`--renew` prints the current guidance for keeping an org alive, and surfaces the
Org IDs of at-risk orgs so the steps are actionable:

- **Partners:** request a Trial Org extension (up to +12 months) via
  `partners.salesforce.com` → **Ask Agentforce** → "I want to extend my Trial
  Org", providing the Org ID. Eligible while active or expired < 30 days; not
  for LDV orgs. (Salesforce Help article 000387818.)
- **Nonprofits:** email your Account Executive with subject "Trial Extension"
  and the trial-starter email, Org ID, and username; AMER
  `PowerOfUsDesk@salesforce.com`, other regions `myaccount@salesforce.com` /
  1-800-NO-SOFTWARE. Works even if already expired. (Article 004754220.)
- **Developer Edition:** DE orgs have no subscription clock but are deactivated
  after prolonged inactivity (~180 days without a login); log in periodically.
  If locked (not yet deleted), open a Salesforce Customer Support case to
  reactivate — once permanently deleted, an org cannot be recovered.
- To keep a standard trial's data/config, convert/subscribe to a paid edition
  before it lapses.

## Exit codes

- `0` success
- `1` an org could not be queried (auth/connection error)
- `2` bad usage or a missing dependency (`sf` or `jq`)
- `3` `--fail-if-expiring` threshold breached (at least one org expiring)

When both apply, a `--fail-if-expiring` breach (`3`) takes precedence over an
auth error (`1`): the alerting signal wins so a watchdog still fires. If your
job must also detect unreachable orgs, run `--json` and inspect the records for
`status: "auth_error"` in addition to checking the exit code. Note that an org
whose credentials fail cannot be date-checked, so it never counts toward a
`--fail-if-expiring` breach on its own.

`--fail-if-expiring` with no explicit number treats a following **all-numeric**
argument as the day count (e.g. `--fail-if-expiring 12345`). In the rare case an
org's alias is purely numeric, pass the org first (`check_expiration.sh 12345
--fail-if-expiring 7`) so it isn't mistaken for the threshold.

## Authentication

If an org isn't authenticated (no saved credentials, or an expired/revoked
token), the script does not fail silently — it prints the exact command to log
in and then re-run:

```text
  my-trial                       not authenticated — no saved credentials for this org

  To authenticate, run one of:
    sf org login web --alias "my-trial"
    sf org login web --alias <my-alias> --instance-url https://test.salesforce.com
  Then re-run this check. List existing logins with:  sf org list
```

`sf org login web` opens a browser to complete the OAuth flow. Use
`--instance-url https://test.salesforce.com` for sandboxes, or a custom My
Domain URL where applicable.

## Manual fallback (if the script is unavailable)

```bash
# Trial/DE expiration for one org (null = not a trial / paid org):
sf data query --query "SELECT Id, TrialExpirationDate FROM Organization" --target-org <org> --json

# Scratch org expiration comes from the org list, not SOQL:
sf org list --json
```

## Notes

- Requires the Salesforce CLI (`sf`) and `jq` on the PATH, plus at least one
  authenticated org (`sf org login web`).
- Avoid launching many `sf` commands concurrently — the CLI can be slow under
  contention. The script queries orgs sequentially for this reason.
- `sf org list` exposes a `trailExpirationDate` (note the typo) field that is
  often `null`; the script does not rely on it for trial/DE orgs — it uses the
  SOQL `TrialExpirationDate`, which is reliable. It does use `expirationDate`
  from the list for scratch orgs.
