# LWR Route Scaffolding — Delegation

Some LWR site templates declare route types in their theme that the retrieved bundle does not contain (commonly `too-many-requests`). If a required route is missing at deploy time, the deploy fails with a route-type validation error.

Route + view creation is owned by **`experience-lwr-site-generate`**. This skill does not duplicate that procedure. Delegate to that skill and pass through the messaging-specific context.

## When to invoke the delegate

Trigger the delegation when the messaging-widget deploy in Phase 4 fails with a missing-route or missing-view error mentioning a `routeType` that is not present under `digitalExperiences/site/<siteName>/sfdc_cms__route/`.

## What to hand off

Give `experience-lwr-site-generate` these three items:

- **Site name** — `<siteName>` (same value used throughout this skill).
- **Route type reported by the deploy error** — e.g. `too-many-requests`.
- **Retrieve directory** — `<retrieve-dir>` so the scaffolded pair lands next to the existing route/view directories.

The delegate skill covers the full procedure: `configure-content-route.md` (route file shape), `configure-content-view.md` (view file shape), and `handle-component-and-region-ids.md` (fresh-UUID stamping so the scaffolded view does not collide with existing IDs).

## Messaging-specific delta

After the delegate returns, verify the specific deploy error is cleared before proceeding:

```bash
sf project deploy validate --source-dir force-app/main/default --target-org <org-alias>
```

If the validation surfaces additional missing route types, re-invoke the delegate for each. Only proceed to Phase 4's real deploy once validation passes.

If the delegate is unavailable, fall back to Phase 6's manual Experience Builder path — do **not** attempt to scaffold routes ad-hoc from this skill.
