# dx-packaging-push-upgrade-configure

A Salesforce agent skill that plans, schedules, and monitors **package push upgrades** from a
Dev Hub — end-to-end.

Push upgrades change a package **in the customer's org without their action**, so the skill's
default posture is **generate → preview → confirm → run**: it never calls `schedule` or `abort`
until the user has seen the batch plan and org list and said go.

## What it does

- **Resolves** the package (`033`) and a valid target version (`04t`) against the Dev Hub.
- **Finds subscribers** via `PackageSubscriber`, then applies eligibility filters (installed only,
  below target, production vs sandbox, org status, subscriber restrictions).
- **Batches a schedule** per best practices — pilot in sandboxes, stagger production, off-peak by
  time zone, avoid risky windows — and generates the per-batch org CSVs.
- **Runs** the `sf package push-upgrade schedule` commands after explicit confirmation.
- **Monitors** results via CLI and `PackagePushRequest` / `PackagePushJob` / `PackagePushError`,
  and verifies the upgrade actually landed.

Supports 2GP managed, unlocked, and 1GP→2GP push migrations (`--migrate-to-2gp`).

## Inputs

The skill reads these from the request; provide whichever you have:

- `033…` → package ID
- `04t…` → target package version ID
- `0DV…` → existing push request ID (jumps straight to monitoring)
- a Dev Hub alias/username → the package-owning org (defaults to the configured `target-dev-hub`)

### Prerequisites

- Salesforce CLI (`sf`) authenticated to the Dev Hub / package-owning org.
- 2GP managed packages must have passed AppExchange security review and have push upgrades enabled
  via a Partner Support case. Unlocked packages have them enabled by default.
- The *Create and Update Second-Generation Packages* user permission on the Dev Hub.

## Layout

| File | Purpose |
| --- | --- |
| `SKILL.md` | The skill definition and the phase-by-phase workflow. |
| `references/cli-reference.md` | Verified `sf package push-upgrade` subcommands and flags. |
| `references/objects.md` | Field reference for the push-upgrade objects. |
| `references/soql-recipes.md` | Ready-to-run subscriber and monitoring queries. |
| `references/best-practices.md` | Timing, testing, staggering, and communication guidance. |
