# `sf package push-upgrade` — CLI reference

Verified against `@salesforce/cli` 2.145.6 (`sf package push-upgrade <cmd> --help`). Re-run
`--help` to confirm flags on newer CLI versions. All commands target the **Dev Hub / package-owning
org** via `-v/--target-dev-hub` (or the `target-dev-hub` config var).

Common global flags on every subcommand: `--json`, `--flags-dir <dir>`, `--api-version <value>`.

### Surviving CLI drift

The CLI has two output contracts with **opposite** stability — treat them differently:

- **`--json`** is the machine contract. Keys map to the `PackagePushRequest` API fields and change
  rarely (with deprecation). **Parse this** whenever the skill reads output programmatically. The
  documented key sets below were captured from live `--json` runs.
- **The human table** is display-only. Column order, labels, and even which columns appear (e.g. the
  `Num Orgs *` decorations) are presentation and can change in any CLI release. **Never parse the
  table.**
- **Flags** can also change. If a command errors or output looks unexpected, run
  `sf package push-upgrade <cmd> --help` to re-verify against the installed CLI version rather than
  trusting this file — this reference is a snapshot, `--help` is ground truth.
- For counts/rollups the skill needs, prefer **direct object queries** (`PackagePushJob GROUP BY
  Status`) over anything the CLI only surfaces in its table — object fields are the stable source.

---

## schedule — create a push upgrade request

```bash
sf package push-upgrade schedule -v <devhub> -p <04t> [-l <orgIds> | -f <csv>] [-t <UTC>] [--migrate-to-2gp]
```

| Flag | Required | Meaning |
|------|----------|---------|
| `-p, --package <04t>` | yes | Package **version** ID (starts `04t`) the orgs are upgraded **to**. Must be an active, non-beta version. |
| `-v, --target-dev-hub <alias>` | yes | Dev Hub that owns the package. |
| `-l, --org-list <ids>` | one of -l/-f | Comma-separated subscriber org IDs to upgrade. |
| `-f, --org-file <csv>` | one of -l/-f | CSV file, **one org ID per line, no header**. All listed orgs must have a version **lower** than `--package`. |
| `-t, --start-time <UTC>` | no | Earliest UTC datetime Salesforce should attempt the upgrade, e.g. `"2026-08-11T09:00:00"`. Omit to start ASAP. |
| `--migrate-to-2gp` | no | Push-migrate orgs that have the **1GP** version installed to the converted 2GP version. |

Returns a **push request ID** (starts `0DV`). Capture it.

**Output (verified via `--json`).** `result` is a single object with keys `PushRequestId` (the `0DV` —
note the key is `PushRequestId`, not `Id`), `ScheduledStartTime`, and `Status`. A freshly scheduled
request comes back with status **`Pending`** (not `Created`) when a future `--start-time` is set. Parse
`PushRequestId` from `--json` rather than scraping the table. **`ScheduledStartTime` is populated only
when you pass `--start-time`** — for an ASAP schedule (no `--start-time`) it can be **absent/null** in
the response, so don't rely on it being present in the immediate case.

Examples:
```bash
# At a specific time, from a CSV
sf package push-upgrade schedule --package 04txyz --start-time "2024-12-06T21:00:00" \
  --org-file upgrade-orgs.csv --target-dev-hub myHub

# As soon as possible
sf package push-upgrade schedule --package 04txyz --org-file upgrade-orgs.csv --target-dev-hub myHub

# 1GP -> 2GP push migration
sf package push-upgrade schedule --migrate-to-2gp --package 04txyz \
  --start-time "2024-12-06T21:00:00" --org-file upgrade-orgs.csv --target-dev-hub myHub
```

**Schedule-time validation failures write a local log and create no job rows.** If `schedule` rejects
the request — e.g. `INVALID_OPERATION: The specified SubscriberOrganizationKey is not eligible to
receive this upgrade` for a non-subscriber or otherwise ineligible org id — the CLI writes an error log
to `<cwd>/job_errors/push_request_<id>_errors.log` (relative to your **current working directory**, so
it can land in your repo), and the resulting `PackagePushRequest` is stranded at `Created` with **zero
`PackagePushJob` rows**. Nothing is queryable: `PackagePushJob`/`PackagePushError` return no rows for
this failure mode, so the request's error lives **only** in `schedule`'s exit code / stderr / `--json`
output and that local log file. Check `schedule`'s own result — don't rely on SOQL polling to reveal a
schedule-time rejection.

---

## list — status of push requests for a package

```bash
sf package push-upgrade list -v <devhub> -p <033> [-l <days>] [-s <status>] [--show-push-migrations-only]
```

| Flag | Required | Meaning |
|------|----------|---------|
| `-p, --package <033>` | yes | **Package** ID (starts `033`, not the 04t version) to report on. |
| `-v, --target-dev-hub <alias>` | yes* | Dev Hub. Not required if `target-dev-hub` config is set. |
| `-l, --scheduled-last-days <n>` | no | Only requests scheduled within the last *n* days. |
| `-s, --status <value>` | no | Filter by `Created`, `Cancelled`, `Pending`, `In Progress`, `Failed`, or `Succeeded`. |
| `--show-push-migrations-only` | no | Only 1GP→2GP push-migration requests. |

All filters are AND-ed. Example:
```bash
sf package push-upgrade list --package 033xyz --scheduled-last-days 30 --target-dev-hub myHub
```

**Output — parse `--json`, not the table.** `--json` `result` is an **array** of records; each record's
stable keys (verified via `--json`): `Id`, `PackageVersionId`, `PackageVersion`, `Status`,
`ScheduledStartTime`, `StartTime`, `EndTime`, `IsMigration`. The human table additionally shows
display-only decorations such as `Num Orgs Scheduled` / `Num Orgs Upgraded Fail` / `Num Orgs Upgraded
Success` and a version name/number — these are **not** in `--json` and their columns/labels can change
between CLI versions. For a durable per-status org rollup, query `PackagePushJob GROUP BY Status`
(see `soql-recipes.md`) rather than scraping the table.

---

## report — detail for one push request

```bash
sf package push-upgrade report -v <devhub> -i <0DV>
```

| Flag | Required | Meaning |
|------|----------|---------|
| `-i, --push-request-id <0DV>` | yes | The request ID returned by `schedule`. |
| `-v, --target-dev-hub <alias>` | yes* | Dev Hub (or config var). |

**Output — parse `--json`.** `--json` `result` is a **single object** with stable keys (verified):
`Id`, `PackageVersionId`, `PackageVersion`, `Status`, `ScheduledStartTime`, `StartTime`, `EndTime`,
`DurationSeconds`. (Note the shape differs from `list`: `report` returns one object with
`DurationSeconds`; `list` returns an array with `IsMigration`.) `report` gives request-level status
only — for per-org detail and errors, go to `PackagePushJob` / `PackagePushError`.

---

## abort — cancel a scheduled push request

```bash
sf package push-upgrade abort -v <devhub> -i <0DV>
```

| Flag | Required | Meaning |
|------|----------|---------|
| `-i, --push-request-id <0DV>` | yes | Request to cancel. |
| `-v, --target-dev-hub <alias>` | yes* | Dev Hub (or config var). |

Only requests with status **`Created` or `Pending`** can be aborted. In-progress or completed
requests cannot.

---

## Enablement / eligibility (from docs)

- **2GP managed:** available only for packages that **passed AppExchange security review**; enable the
  feature by logging a **Salesforce Partner Community support case**. CLI + API (no UI).
- **Unlocked:** push upgrades enabled by default. CLI + API.
- **1GP managed:** API + UI only (no CLI schedule); use `--migrate-to-2gp` when pushing the converted
  2GP version onto 1GP installs.
- Scheduling requires the **Create and Update Second-Generation Packages** user permission.
