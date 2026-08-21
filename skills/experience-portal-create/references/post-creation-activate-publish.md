# Post-Creation: Activate, Add Members, Publish (make the site reachable)

`POST /connect/communities` (and the self-service site API) only **provisions** the site — it comes
back `UnderConstruction` with **no members** and **unpublished pages**. In that state the site URL
is **not reachable** (a bare `https://<domain>.my.site.com/<prefix>` returns an error / "under
construction" page). Three post-creation steps make it actually work, in this order:

1. **Activate** the Network (`status` → `Live`)
2. **Add members** (profiles/permission sets that can access the site)
3. **Publish** the Experience Builder pages

> **Tooling note — this is the one place the skill steps outside headless-360.** There is **no
> Connect API** for activating or publishing an Experience Builder site, and
> `PATCH /connect/communities/<id>` returns **405 METHOD_NOT_ALLOWED** (the endpoint is GET/HEAD
> only). Activation and membership go through the **Metadata API** (deploy the `Network`), and
> publish goes through the **`sf community publish` CLI**. Use these here even though the rest of
> the skill is headless-360-only — they are the verified working paths (confirmed live against
> `orgfarm-825d2dfcc4`).

---

## Why the site looked "broken"

A freshly created Experience site:

- has `status: UnderConstruction` on its `Network` — not addressable until set `Live`;
- has only the admin profile as a member — no employee/customer profiles can reach it;
- has **unpublished** Builder pages — even once Live, the pages 404 / show "under construction"
  until published.

Also note the **URL path**: Aura Employee/Customer sites serve at the `/s`-style path and login at
`.../<prefix>/login` (or `.../<prefix>/s/login`), **not** the bare `.../<prefix>`. Confirm the
exact `loginUrl` / `siteUrl` from `GET /connect/communities/<networkId>` before telling the user
the site is broken.

---

## Step 1 — Activate the Network (status → Live)

Retrieve the Network metadata, flip `status`, redeploy. (Site name = the community `name`.)

```bash
sf project retrieve start --metadata "Network:<Site Name>" -o <org-alias>
```

Edit `force-app/main/default/networks/<Site Name>.network-meta.xml`:

```xml
<status>UnderConstruction</status>   <!-- change to -->
<status>Live</status>
```

```bash
sf project deploy start --metadata "Network:<Site Name>" -o <org-alias>
```

Verify via headless-360:

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/connect/communities/<networkId>"
)
```

`status` must now read `Live`.

---

## Step 2 — Add members (profiles / permission sets)

Community membership is **group-based** — you add **profiles** (and/or permission sets), not
individual users. Users holding a member profile become members automatically. `networkMemberGroups`
in the same `Network` metadata holds these; add a `<profile>` (or `<permissionSet>`) child and
redeploy.

> **"Unified Employee" is a Profile, not a UserRole.** Verify the exact name first — a `UserRole`
> query for it returns 0 rows; it is a **Standard Profile** (`SELECT Id, Name, UserType FROM Profile
> WHERE Name = 'Unified Employee'`). Metadata uses the profile **Name** (`Unified Employee`), not
> the Id.

Edit the same `<Site Name>.network-meta.xml`:

```xml
<networkMemberGroups>
    <profile>admin</profile>
    <profile>Unified Employee</profile>   <!-- added -->
</networkMemberGroups>
```

```bash
sf project deploy start --metadata "Network:<Site Name>" -o <org-alias>
```

Verify via headless-360 (`ParentId` = the added profile's Id):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, NetworkId, ParentId FROM NetworkMemberGroup WHERE NetworkId = '<networkId>'" }
)
```

> **`NetworkMemberGroup` column discipline:** it exposes `Id`, `NetworkId`, `ParentId` — **no**
> `MemberType`, and **no** `Parent.Name` relationship. Selecting those returns `INVALID_FIELD` /
> "Didn't understand relationship 'Parent'". Query `ParentId` and match it to a `Profile.Id` you
> looked up separately.

Steps 1 and 2 can be combined into a **single** `Network` deploy (flip `status` **and** add the
member group in one edit) to save a round-trip.

---

## Step 3 — Publish the Experience Builder pages

No Connect API exists for this; use the CLI. It publishes all Builder pages and kicks off a
background job.

```bash
sf community publish --name "<Site Name>" -o <org-alias>
```

Returns `{ id, jobId, status, url, message }` — "We're publishing your changes now."

Poll the job to completion via headless-360 (regular `/query`, only `Id, Status`):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Status FROM BackgroundOperation WHERE Id = '<jobId>'" }
)
```

Wait for `Status: Complete`.

---

## Final verification

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/connect/communities/<networkId>"
)
```

Confirm `status: Live`. Give the user the **login URL** (`.../<prefix>/login`), not the bare
prefix. Members on the added profile(s) can now sign in.

---

## Gotchas index

| Issue | Fix |
|-------|-----|
| Bare site URL `.../<prefix>` not reachable | The site serves at `.../<prefix>/login` (and the app at `/s`). Read `loginUrl` from `GET /connect/communities/<id>` — don't assume the bare prefix works. |
| `PATCH /connect/communities/<id>` → 405 METHOD_NOT_ALLOWED | The communities endpoint is GET/HEAD only. Activate via `Network` **Metadata** deploy (`status: Live`), not a Connect PATCH. |
| Site stays `UnderConstruction` after create | Expected — creation only provisions. Deploy `Network` with `status: Live` to activate. |
| Members can't reach the site | Only admin is a member on create. Add the target profile(s) to `networkMemberGroups` and redeploy. |
| "Unified Employee" not found as a role | It's a **Profile**, not a `UserRole`. Use the profile Name in `networkMemberGroups`. |
| `NetworkMemberGroup` `MemberType` / `Parent.Name` → INVALID_FIELD | Select only `Id, NetworkId, ParentId`; resolve `ParentId` against `Profile.Id`. |
| Published pages still 404 after activation | Activation (Network → Live) and **publish** are separate. Run `sf community publish` and wait for the `BackgroundOperation` to reach `Complete`. |
| No Connect API for activate/publish | By design — use Metadata API (`Network`) for activate + members, and `sf community publish` for publish. These are the verified paths. |
