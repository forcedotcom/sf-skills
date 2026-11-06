# Push upgrade best practices

Source: Salesforce "Push Upgrade Best Practices" (2GP dev guide). Push upgrades change a package in a
customer's org **without their action** — poor planning "can result in significant customer
satisfaction issues," and buggy upgrades can affect **data**, not just metadata.

---

## Timing & scheduling

- Give customers an **upgrade timeline** up front: when and how often you'll push.
- **Avoid disruptive windows**: month-end, quarter-end, year-end, audit cycles, and any period when the
  customer lacks staff to verify.
- Schedule for the customer's **off-peak hours** (late evening/night). Account for time zones —
  **group orgs by time zone** (use `InstanceName` as a proxy) and schedule each group separately.
  `--start-time` is **UTC**; convert deliberately.
- Steer clear of **Salesforce maintenance windows**, and ideally **wait 3–4 weeks after a major
  Salesforce release** before pushing major upgrades.

## Testing (a higher bar than customer-pulled upgrades)

- Push to **your own test orgs first**, then log in and verify.
- Where possible, push to **customer sandboxes first** and allow **a week or more** to test, validate,
  and fix before touching production.
- Add an **Apex test-on-install** for basic sanity checks during the upgrade.

## Staggering / batching

- **Don't push to everyone at once.** Staggering protects support capacity and catches issues early.
- Start with **small production batches** (e.g. 50–100 of 1,000 customers); enlarge batches only after
  clean runs build confidence.

## Customer trust & communication

- You are responsible for ensuring customer orgs **aren't adversely affected**.
- Avoid changes that can break customer integrations (new **validation rules**, **formula fields**,
  removed components). If unavoidable, **test thoroughly and communicate well in advance**.
- **Enhancing an existing feature:** use a **post-install script** to auto-assign new components via
  **permission sets** — by default, new/changed components are assigned **only to admins**.
- **Brand-new features:** do **not** auto-assign. Coordinate with org admins on access and rollout timing.

---

## Eligibility reminders

- **2GP managed:** must have **passed AppExchange security review**; enable via a **Partner Community
  support case**. Manageability rules for normal upgrades also apply to pushes.
- **Unlocked:** enabled by default.
- Target version must be **active, non-beta, released, non-deprecated**, and **strictly higher** than
  each target org's installed version.
- **Subscriber restrictions:** if a subscriber has restricted push upgrades
  (`HasRestrictionEnabled = true` / `CustomUpgradeType = 'BlockedBySubscriber'`), exclude them — the
  request errors on restricted orgs.

## A sane rollout template

1. Push to internal test orgs → verify by logging in.
2. Push to customer **sandboxes** → soak ≥ 1 week.
3. Production **pilot** batch (50–100), off-peak, one time zone → monitor `PackagePushJob`/`PackagePushError`.
4. Grow production batches by time zone, off-peak, avoiding risky windows, only after clean runs.
5. Ship a post-install script + permission set if the version adds features users need immediately.
