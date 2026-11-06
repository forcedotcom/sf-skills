---
name: dx-packaging-push-upgrade-configure
description: "Use this skill to plan, schedule, and monitor Salesforce package push upgrades from a Dev Hub. Finds subscriber orgs via the PackageSubscriber object, resolves and validates the target package version, builds a best-practice batched schedule (pilot sandboxes, then staggered off-peak production batches), generates the per-batch org-ID CSV, and — only after explicit confirmation — runs the sf package push-upgrade CLI commands, then monitors PackagePushRequest, PackagePushJob, and PackagePushError. Supports 2GP managed, unlocked, and 1GP-to-2GP push migrations. TRIGGER when the user wants to push a package upgrade to subscribers, find who has a package installed and at what version, batch a rollout by region, or schedule, monitor, or abort a push upgrade. DO NOT TRIGGER for post-install configuration of an installed package (use dx-pkg-post-install-configure), creating or versioning a package, or installing a package into one org."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  relatedSkills:
    - "dx-pkg-post-install-configure"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck: "UserPermissions.PermissionsPackaging2"
---

Plan and drive a Salesforce **package push upgrade** end-to-end: find subscriber orgs, resolve the
target version, batch a schedule per best practices, generate the org CSV, run the `sf` CLI
`push-upgrade` commands **after explicit confirmation**, and monitor the results.

Push upgrades change a package **in the customer's org without their action**. This is outward-facing
and hard to reverse. The default posture of this skill is **generate → preview → confirm → run**:
never call `push-upgrade schedule` or `push-upgrade abort` until the user has seen the batch plan and
the org list and said go. See `references/best-practices.md` before scheduling anything to production.

## Inputs

Gather these from the user's request; parse identifiers loosely wherever they appear:
- A token starting with `033` → the package ID (`MetadataPackageId` for queries, `--package` for `list`).
- A token starting with `04t` → the target package **version** ID (`--package` for `schedule`).
- A token starting with `0DV` → an existing push request ID (jump straight to Phase 5, monitoring).
- A Dev Hub **alias or username** → the org the push-upgrade objects and commands run against.

If the Dev Hub is not given, **assume the default Dev Hub owns the package and verify by querying**
rather than prompting up front:
1. Read the default from `sf config get target-dev-hub --json`. If none is set, skip to step 3.
2. Probe that hub for the package — reuse Phase 1's resolution query against the given `033`/`04t`
   (or `SELECT Id, Name FROM MetadataPackage` if only a name is known). If it returns the package,
   you've confirmed ownership and done Phase 1 in one step — proceed, naming the resolved Dev Hub.
3. Only if the probe **fails** (no matching rows, or an auth/permission error), fall back to asking:
   run `sf org list --json` and ask the user which Dev Hub owns the package, then re-probe.

This keeps the happy path unattended while still catching a wrong/empty hub before any subscriber
query or plan. Push upgrade objects and commands run against the **Dev Hub / package-owning org**, not
a subscriber org.

---

## Phase 0 — Confirm scope and prerequisites

Establish these before doing anything else; ask only for what you can't infer:

1. **Package type** — 2GP managed, unlocked, or a 1GP→2GP migration (`--migrate-to-2gp`).
   - 2GP managed push upgrades require the package to have **passed AppExchange security review**,
     and the feature must be enabled via a **Salesforce Partner Support case**. Unlocked packages
     have push upgrades enabled by default.
2. **Dev Hub is authenticated** — `sf org display --target-org <devhub> --json`. If it fails, tell the
   user to run `sf org login web --alias <devhub>` and wait.
3. **Permission** — scheduling needs the *Create and Update Second-Generation Packages* user permission
   on the Dev Hub. If a later command fails with an auth/permission error, surface that as the likely cause.

Do not assume security-review/enablement status — if the user hasn't confirmed it, note it as a
prerequisite they must verify, and continue building the plan (it's still valid).

---

## Phase 1 — Resolve the package and target version

Goal: end with a confirmed **033 package ID** and a **04t target version ID** that is a valid push target.

> If the Dev Hub was resolved via the default-hub probe in **Inputs** above, that probe already ran
> this resolution query — you may already have the package/version in hand. Don't re-query; pick up at
> validation (step 2).

1. If only the 04t is known, resolve its package and version number:
   ```bash
   sf data query --target-org <devhub> \
     --query "SELECT Id, MetadataPackageId, Name, MajorVersion, MinorVersion, PatchVersion, BuildNumber, ReleaseState, IsDeprecated FROM MetadataPackageVersion WHERE Id = '<04t>'"
   ```
2. Validate the target version is a legal push target:
   - `ReleaseState = Released` (not `Beta`) and `IsDeprecated = false`. The CLI requires an
     **active, non-beta** version.
   - It must be **higher** than the versions subscribers currently run (Phase 2 confirms this).
   - Push upgrades follow the **same manageability rules** as customer-initiated upgrades — you can't
     push a change a normal upgrade couldn't make (e.g. deleting components, deprecated-then-removed).
3. If the user only gave a 033, list candidate versions so they can pick the target:
   ```bash
   sf data query --target-org <devhub> \
     --query "SELECT Id, Name, MajorVersion, MinorVersion, PatchVersion, BuildNumber, ReleaseState FROM MetadataPackageVersion WHERE MetadataPackageId = '<033>' AND ReleaseState = 'Released' ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC"
   ```

See `references/objects.md` for full field lists.

---

## Phase 2 — Find subscriber orgs (PackageSubscriber)

Query `PackageSubscriber` **on the Dev Hub / License Management Org** to discover who has the package
installed and at what version. `OrgKey` is the org ID that goes in the CSV.

Baseline query (installed subscribers on production orgs, below the target version):
```bash
sf data query --target-org <devhub> \
  --query "SELECT OrgKey, OrgName, OrgStatus, OrgType, InstanceName, MetadataPackageVersionId, InstalledStatus, HasRestrictionEnabled FROM PackageSubscriber WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i'"
```

Then apply the **eligibility filters** — this is where the skill adds judgment. Walk the user through:

- **Currently installed only** — `InstalledStatus = 'i'` (`'u'` = uninstalled/not installed).
- **Not already on the target** — exclude rows whose `MetadataPackageVersionId` equals the target 04t,
  and resolve each subscriber's version numbers so you push only to orgs strictly *below* the target.
  Push upgrades can't downgrade; an org **already at** the target is a **silent no-op** (request/job
  report `Succeeded`, no error), not a detectable failure — so filter these out up front.
- **Production vs sandbox** — `OrgType`. Best practice is to pilot in **sandboxes** first, then
  production. Offer to split the list by `OrgType`.
- **Org status** — `OrgStatus` is `Active`/`Demo`/`Free`/`Inactive`/`Trial`, and is **independent of
  `OrgType`** (a Production org can be `Trial`/`Demo`/`Free`). Typically exclude only `Inactive`
  (`OrgStatus != 'Inactive'`); do **not** whitelist `= 'Active'` or you'll silently drop live
  non-`Active` production subscribers.
- **Respect subscriber restrictions** — if the package lets subscribers block push upgrades, skip rows
  where `HasRestrictionEnabled = true` or `CustomUpgradeType = 'BlockedBySubscriber'`. Pushing to a
  restricted org will error; filter them out up front and report the count.

Report a summary table (counts by `OrgType`, by current version, restricted/excluded) so the user can
sanity-check the population before batching. See `references/soql-recipes.md` for ready-to-run variants.

---

## Phase 3 — Build the batched schedule (best practices)

**Do not write any `.csv` file in this phase.** The plan is the only deliverable here — CSVs are a
Phase 4 action, created only after the user approves and you are about to run `schedule`. Before you
end this turn, confirm you have written at most one file (the plan itself); if you find yourself
about to call a file-write tool with a `.csv` path, stop — that belongs in Phase 4, not here.

Do **not** dump every org into one request. Propose a batch plan grounded in
`references/best-practices.md`:

- **Pilot first.** Batch 0 = your own test orgs and/or customer **sandboxes**. Recommend a soak period
  (a week+ for sandboxes) before production.
- **Stagger production.** Start small (e.g. 50–100 orgs of 1,000), grow batches only after clean runs.
- **Off-peak, by time zone.** Schedule each batch for the subscribers' local late-evening/night; group
  by `InstanceName`/time zone where possible. `--start-time` is **UTC** — state the local-time intent
  and the UTC value you computed.
- **Avoid risky windows.** No month/quarter/year-end; wait **3–4 weeks after a major Salesforce
  release** before major pushes; avoid Salesforce maintenance windows.

Produce a concrete plan the user approves, e.g.:

```text
Batch  Population              Count  Local target       --start-time (UTC)
0      Sandboxes (pilot)       12     immediate          (omit -t)
1      Prod, AMER off-peak     80     Tue 02:00 PT       2026-08-11T09:00:00
2      Prod, EMEA off-peak    140     Wed 02:00 CEST     2026-08-12T00:00:00
3      Prod, APAC off-peak     60     Thu 02:00 AEST     2026-08-12T16:00:00
...
```

Convert each batch with the UTC offset in force **on the push date**, not the region's standard offset
(e.g. PDT is UTC−7 and CEST is UTC+2 in summer; AEST is UTC+10 until Sydney moves to AEDT, UTC+11, in
October). Regions east of UTC cross the date line: 02:00 local on Thursday is **Wednesday** in UTC, so
the UTC date in `--start-time` is the day before the local date. Show both in the plan.

For each batch, show the org-ID CSV **inline as a fenced code block** — one `OrgKey` per line, no
header, one org ID per row — labeled with the filename it will be saved under (e.g.
`push-batch-1-amer.csv`). Confirm the contents with the user. Don't create the `.csv` files while
planning; write them in Phase 4, only once the user approves and you are about to run `schedule`.

---

## Phase 4 — Schedule (confirm, then run)

**Show the exact commands and the org counts, then wait for explicit confirmation** before running any
`schedule`. Once approved, write each batch's CSV file (contents exactly as confirmed in Phase 3), then
run one command per batch:

```bash
sf package push-upgrade schedule \
  --target-dev-hub <devhub> \
  --package <04t-target-version> \
  --org-file push-batch-1-amer.csv \
  --start-time "2026-08-11T09:00:00"
```

Notes and variants:
- Omit `--start-time` to run **as soon as possible**.
- Use `--org-list <id1,id2,...>` instead of `--org-file` for a handful of orgs.
- For a **1GP→2GP push migration**, add `--migrate-to-2gp` (required when the target orgs have the 1GP
  version installed).
- Each successful `schedule` returns a **`0DV` push request ID** — capture every one; you need them to
  monitor and to abort.

After scheduling, record the batch → `0DV` mapping for the user (a small table).

---

## Phase 5 — Monitor, triage, and abort

**Prefer the CLI for status; it takes the 15-char `0DV` from `schedule` directly** (no need to expand
the ID). Only drop to SOQL for per-org detail, errors, or a durable status rollup.

> **Not every failure yields a queryable row.** A request rejected at **schedule time** (e.g. an
> ineligible/non-subscriber org id → `INVALID_OPERATION`) is stranded at `Created` with **zero
> `PackagePushJob` rows**, so the SOQL below returns nothing. Its only trace is `schedule`'s own
> output/exit code and a local `<cwd>/job_errors/push_request_<id>_errors.log` file — pair SOQL polling
> with checking `schedule`'s result; don't read "no job rows" as "nothing went wrong."

**Report** one request — the primary status check:
```bash
sf package push-upgrade report --target-dev-hub <devhub> --push-request-id <0DV>
```

**List** all requests for the package (033):
```bash
sf package push-upgrade list --target-dev-hub <devhub> --package <033> --scheduled-last-days 30
```
Filter with `--status` — the CLI enum is `Created | Cancelled | Pending | In Progress | Failed |
Succeeded` (note the CLI uses `Cancelled`/`In Progress`; the **object** picklist uses
`Canceled`/`InProgress` — see `references/objects.md`). Add `--show-push-migrations-only` for migrations.

When reading either command programmatically, add `--json` and parse the stable keys — do **not** scrape
the human table (its columns, including the `Num Orgs *` counts, are display-only and vary by CLI
version). See `references/cli-reference.md` → "Surviving CLI drift".

### Dropping to SOQL — resolve the full 18-char Id first

The `0DV` returned by `schedule` is **15 characters**. The CLI accepts it as-is, but for direct object
queries there are two gotchas the live run exposed:
- **Do not** guess the 3-char suffix (e.g. appending `4A2`) to build the 18-char Id — it varies per record.
- **`Id LIKE '<0DV>%'` is not supported** on ID fields — it errors.

Resolve the canonical 18-char Id once (a 15-char value **is** valid in an `Id =` filter), then reuse it:
```bash
sf data query --target-org <devhub> --json \
  --query "SELECT Id, Status FROM PackagePushRequest WHERE Id = '<0DV>'"
```

**Status rollup (durable source)** — for "how many orgs succeeded/failed," query the jobs directly
rather than relying on CLI table decorations:
```bash
sf data query --target-org <devhub> \
  --query "SELECT Status, COUNT(Id) total FROM PackagePushJob WHERE PackagePushRequestId = '<0DV-18char>' GROUP BY Status"
```

From that rollup, **report progress explicitly** — don't just echo the raw counts:

- **% complete** = `(Succeeded + Failed) / total` — the fraction of orgs Salesforce has finished
  attempting. State how many remain `Pending`/`InProgress`.
- **% success** = `Succeeded / (Succeeded + Failed)` — the quality signal. Divide by orgs *attempted*,
  **not** `total`, or still-queued orgs will drag the number down and read like failures.
- **Across batches**, report the *overall rollout* as **% complete = orgs attempted / total planned**
  (e.g. 40 of 80 = 50%), keeping per-batch **% success** separate. Don't headline a single blended
  "% now on the target version" — attempted-vs-planned and succeeded-vs-attempted are different signals,
  and collapsing them misstates where the rollout stands.

The job `Status` picklist is `Created | Pending | InProgress | Succeeded | Failed | Canceled` (the object
uses `InProgress`/`Canceled` — one word — unlike the CLI's `In Progress`/`Cancelled`).

**Per-org detail and errors** — go to the objects when a request shows failures. One `PackagePushJob`
is created per org; failures attach `PackagePushError` rows:
```bash
sf data query --target-org <devhub> \
  --query "SELECT Id, SubscriberOrganizationKey, Status, StartTime, EndTime FROM PackagePushJob WHERE PackagePushRequestId = '<0DV-18char>'"

sf data query --target-org <devhub> \
  --query "SELECT PackagePushJobId, ErrorSeverity, ErrorType, ErrorTitle, ErrorMessage, ErrorDetails FROM PackagePushError WHERE PackagePushJobId IN (SELECT Id FROM PackagePushJob WHERE PackagePushRequestId = '<0DV-18char>')"
```
`ErrorType` values include `DeployError`, `ApexTestFailure`, `LockingFailure`, `IneligibleUpgrade`.
Summarize failures by `ErrorType` so the user can decide whether to re-push a subset.

### Decide: continue, hold, or re-push (when the failure rate is high)

Staggering only pays off if you **act on a bad batch before the next one runs**. After each batch:

1. **Gate the next batch on this batch's result.** Compute the batch's failure rate from the rollup
   above. If it exceeds your tolerance for the blast radius — a reasonable default is **≥10–20%**,
   tighter for large batches — **hold the rollout**: do **not** schedule the next batch, and `abort`
   any next batch already sitting in `Pending`. You **cannot** abort a request that's already
   `InProgress` or completed (see Abort below), so the real lever is the *unstarted* batch, never the
   running one — never promise to stop a batch that's already executing.
2. **Triage by `ErrorType` before you decide — not every failure means stop.**
   - `LockingFailure` / `IneligibleUpgrade` are often **transient or filterable** (org temporarily
     busy, or an org slipped to/above the target). Usually safe to **re-push the affected subset**
     after retrying or excluding them, without halting the plan.
   - `DeployError` / `ApexTestFailure` usually signal a **real defect in the version**. Stop the
     rollout, fix the package, cut and validate a **new version**, and restart — don't re-push the
     same build and expect a different result.
3. **Re-push a subset, not everyone.** Build a fresh CSV of only the failed `OrgKey`s
   (`PackagePushJob WHERE Status = 'Failed'`) once the cause is understood or a fix is shipped, then
   re-run Phase 4 for just that list.

### Confirm the upgrade actually landed

A `Succeeded` request/job is the request's own view. For real proof, verify the **installed version**:

- **On the Dev Hub** — re-query `PackageSubscriber`; the row's `MetadataPackageVersionId` should equal the
  target 04t. This snapshot can briefly **race** the push (a check moments after `Succeeded` may still
  show the old version) — re-query rather than concluding it failed.
  ```bash
  sf data query --target-org <devhub> --json \
    --query "SELECT OrgKey, MetadataPackageVersionId, SystemModstamp FROM PackageSubscriber WHERE MetadataPackageId = '<033>' AND OrgKey = '<orgId>'"
  ```
- **Inside the subscriber org** (ground truth, if you can authenticate to it) — check
  `InstalledSubscriberPackage`. Note `SubscriberPackage.NamespacePrefix` **can't be filtered** in the
  WHERE clause; select it and filter client-side:
  ```bash
  sf data query --target-org <subscriber-org> --use-tooling-api --json \
    --query "SELECT SubscriberPackage.Name, SubscriberPackage.NamespacePrefix, SubscriberPackageVersionId, SubscriberPackageVersion.MajorVersion, SubscriberPackageVersion.MinorVersion, SubscriberPackageVersion.PatchVersion, SubscriberPackageVersion.BuildNumber FROM InstalledSubscriberPackage"
  ```

**Abort** — only requests in `Created` or `Pending` can be aborted (an in-progress/completed one can't).
Takes the 15-char `0DV` directly:
```bash
sf package push-upgrade abort --target-dev-hub <devhub> --push-request-id <0DV>
```
Confirm with the user before aborting.

---

## Output discipline

Write a single, focused plan the user can act on — not an exhaustive report:
- Include only the sections the request calls for. Discovery-only, verification-only, or hold/abort
  requests do **not** need a batch schedule — don't invent one.
- State each computed number once (%, counts, decisions). One triage table beats five per-error sections.
- Give each command block once. Don't emit speculative re-schedule/re-query blocks for steps the user
  hasn't reached unless they asked for the forward plan.
- Show CSV contents inline as fenced code blocks, and do **not** write separate `.csv` files while
  planning — the plan stays the single deliverable. The files are only created at schedule time (Phase 4).
- Lead with the decision, then a one-to-two-sentence reason. Cut restatement.

## Guardrails

- **Never** run `schedule` or `abort` without showing the command + affected org count and getting a yes.
- The target version must be **active, non-beta, released, non-deprecated**. Push upgrades **can't
  downgrade**, so the target must be **≥** each org's installed version. An org **already at** the
  target is a **silent no-op** — the request and its job report `Succeeded` (no `PackagePushError`), it
  does **not** fail — so exclude same-version orgs up front instead of relying on a failure to catch them.
- `--start-time` is **UTC** — always show the local-time intent alongside the UTC value you send.
- Filter out restricted orgs (`HasRestrictionEnabled = true`) before scheduling; don't let the request
  fail on them.
- **Hold the rollout on a bad batch.** If a batch's failure rate exceeds your threshold, do not schedule
  the next batch (and `abort` any next batch still `Pending`) until the errors are triaged — an
  `InProgress` or completed batch can't be stopped, so the only lever is the unstarted one.
- Push upgrades can affect customer **data**, not just metadata. If the version includes destructive or
  integration-breaking changes (validation rules, formula fields, removed components), call it out and
  push to sandboxes first.
- New/changed components are assigned **only to admins** by default. If the version adds features users
  need, remind the user to ship a **post-install script + permission set** (see best-practices).

## References

- `references/cli-reference.md` — verified `sf package push-upgrade` subcommands and flags.
- `references/objects.md` — field reference for PackageSubscriber, PackagePushRequest, PackagePushJob,
  PackagePushError, MetadataPackageVersion.
- `references/soql-recipes.md` — ready-to-run subscriber and monitoring queries.
- `references/best-practices.md` — timing, testing, staggering, and communication guidance.
