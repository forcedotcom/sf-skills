# Site publish + membership verification (Step 5b)

Setting the **Preferred Digital Experience Site** (`SLACK_PREFERRED_SITE`) and assigning the Step 4
permission sets are necessary but **not sufficient** for an employee to actually see IT Service records in
the Slack app. Three silent gaps remain — each of which lets every low-level write return `200`/`201` while
the end result is still broken. **Verify them separately — they are three distinct states, not one:**

- **(a) activation** — the preferred site (its **`Network`**) is not **`Live`** — a portal in
  `UnderConstruction` (or `DownForMaintenance`) serves nothing to employees;
- **(b) membership** — the target employee is **not a `NetworkMember`** of that site — a non-member can't
  see the portal's records even when the site is Live; and
- **(c) publication** — the site's **Builder pages are unpublished**. Activation (`Network.Status = 'Live'`)
  and publication are **separate go-live states**: a Live network with unpublished pages still 404s / shows
  "under construction". `Network.Status` does **not** prove the pages were published.

On any org where the portal hasn't been activated/published or the user's profile/permset isn't on the
site's Members list, the Slack "IT Service" record lists come back **empty / access-denied** — yet no
permset assignment failed, no org preference is wrong, and the Slack connection is fine. So the skill's
terminal "setup complete" message is materially wrong. **Run all three checks after Step 5 and before any
success summary; a failure of any one is a blocking finding.**

> **Programmatic remediation exists — this is not UI-only.** Activation and membership go through the
> **Metadata API** (`Network` status → `Live`; `NetworkMemberGroup` for members) and publication goes
> through the **community-publish** step `experience-portal-create` owns — there is no Connect API for any of them (a `PATCH /connect/communities/<id>`
> returns 405). These are the same verified paths `experience-portal-create` uses in its Step 3
> (Activate → Add Members → Publish); hand the remediation to that skill rather than treating it as a
> manual builder-only action. Builder clicks are only the fallback when the operator prefers the UI.

## Check (a) — the preferred site is Live

The site Id to check is whatever `SLACK_PREFERRED_SITE` resolves to (read it back in Step 5.2) — a
`Network` Id (`0DB...`).

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name, Status FROM Network WHERE Id = '<preferred site Network Id>'" }
)
```

- **`Status = 'Live'`** → published; check passes.
- **Anything else** (`UnderConstruction`, `DownForMaintenance`) → **blocking**. Surface it in plain
  language — "the employee portal *\<Name\>* isn't published yet, so employees won't see anything in Slack
  until it's live" — and give the remediation below. Do **not** report setup complete.

### Remediation — activate the Network (programmatic path preferred)

`Network.Status` is not writable through the org-values or a direct SObject/Connect `PATCH` here (a
`PATCH /connect/communities/<id>` returns **405**). The **verified programmatic path is a Metadata-API
`Network` deploy** setting `<status>Live</status>` — the same activation step `experience-portal-create`
runs in its Step 3. **Hand activation to `experience-portal-create` (Activate → Add Members → Publish)**;
that skill owns the `Network` metadata deploy and the reachability check. After it activates, re-run
check (a) to confirm `Status = 'Live'`.

Builder fallback (only if the operator prefers the UI): **Digital Experience Builder → open the site →
Publish** — but note that clicking Publish in the builder both activates *and* publishes, whereas the
programmatic path treats them separately (check (c)). Don't claim an API activated it if you handed it off
to the UI. (If the org needs the portal *created* in the first place, that is also the
`experience-portal-create` hand-off from Step 3, not this check.)

## Check (b) — the target user is a site member

For **each** user assigned in Step 4 (the same confirmed employee user Ids):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id FROM NetworkMember WHERE NetworkId = '<preferred site Network Id>' AND MemberId = '<user Id>'" }
)
```

- **≥1 row** → the user is a member; check passes for that user.
- **`0` rows** → **blocking** for that user. Surface it — "\<user\> isn't a member of the *\<Name\>*
  portal, so they won't see IT Service records in Slack" — with the remediation below.

`NetworkMember.MemberId` is the `User` Id. Membership is usually granted **by profile or permission set**
(the site's Members list), not per-user — so one fix typically covers many users at once.

### Remediation — add members (programmatic path preferred)

`NetworkMember` is not directly writable through a public Connect/SObject write here, but membership **is**
grantable programmatically: adding a **Profile** or **permission set** to the site's Members list is a
**Metadata-API `NetworkMemberGroup`** deploy — the same "Add Members" step `experience-portal-create` runs
in its Step 3. **Hand membership to `experience-portal-create`**, which owns the `NetworkMemberGroup`
metadata (with its column discipline). Adding a profile/permset covers all users who hold it at once.

Builder fallback (only if the operator prefers the UI): **Experience Builder → open the site →
Administration → Members** → add the employee's **Profile** (or a **permission set** the employee holds) to
the *Selected* Members list → **Save**.

After membership is granted, re-run check (b) for the affected user(s) to confirm a `NetworkMember` row now
exists. Don't claim an API added the member if you handed it off to the UI.

## Check (c) — the site's Builder pages are published

Activation (check (a)) makes the `Network` addressable; it does **not** publish the Builder pages. A Live
network whose pages were never published still serves "under construction" / 404s, so employees see nothing
in Slack. Publication is a **separate go-live mutation** and must be verified on its own.

There is no `Network` column that cleanly reports "pages published," so verify publication the way
`experience-portal-create` does — confirm the site is reachable end to end after a publish, and treat a
never-published site (one that has only ever been activated) as **not published**:

- If the site was provisioned/activated but the **community-publish step has never completed** for it →
  **blocking**. Surface it — "the employee portal *\<Name\>* is active but its pages aren't published yet,
  so employees will see 'under construction' in Slack" — with the remediation below.

### Remediation — publish the site (programmatic path preferred)

Publication has **no Connect API**; the verified path is the community-publish CLI step, polled to
completion on `BackgroundOperation` — exactly `experience-portal-create`'s Step 3 "Publish" step. **Hand
publication to `experience-portal-create`**; it publishes the site by name against the org and waits for
the returned `jobId` to reach `Status: Complete`.

Builder fallback (only if the operator prefers the UI): **Digital Experience Builder → open the site →
Publish**. After publication completes, re-confirm reachability. Don't claim an API published it if you
handed it off to the UI.

## Reporting

Only after **all three** checks — (a) activation, (b) membership, (c) publication — pass for the chosen site
and every Step-4 user may the skill proceed to Step 6 (or emit the success summary). If any check fails, the
user-facing message must name the specific blocking finding(s) and the remediation (prefer the
`experience-portal-create` programmatic hand-off; UI as fallback) — not a green "setup complete."
