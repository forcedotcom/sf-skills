---
name: commerce-react-storefront-create
description: "Stand up the commerce-b2b-headless reference React storefront in a Salesforce B2B Commerce org, end to end — discover the org's WebStores, pick one, fill the four org-specific values (WebStore Id, BuyerGroup Id, buyer permission set group, Vite org alias), build + deploy the UI Bundle, assign the site guest user the auth permission set, and hand back the live Experience Cloud storefront URL. Use whenever the user says \"create a react storefront in my org\", \"set up the headless B2B storefront\", \"deploy commerce-b2b-headless\", \"stand up a React storefront for <org-alias>\", \"get me a hosted headless commerce storefront\", or points at a cloned commerce-b2b-headless repo and wants it running against their org."
metadata:
  relatedSkills:
  - experience-ui-bundle-deploy
  version: "1.0"
  minApiVersion: "65.0"
  domains:
  - "Commerce"
  - "Experience"
  cliTools:
  - tool:
    - "git"
    semver: ">=2.0"
  - tool:
    - "jq"
    semver: ">=1.6.0"
  - tool:
    - "npm"
    semver: ">=8.0.0"
  - tool:
    - "sf"
    semver: ">=2.130.0"
---

# create-react-storefront

## What this does

Deploys the **commerce-b2b-headless** reference React storefront (a React 19 + Vite `UIBundle`
served from the Experience Cloud Site Container) into a user's B2B Commerce org and returns the
hosted storefront URL. The repo is a *reference implementation* — it ships four org-specific
values as `<…_Placeholder>` strings that throw at runtime until replaced. This skill's whole job
is to resolve those four values against the target org, then drive build → deploy → guest-user
entitlement so the storefront actually renders.

The repo's `scripts/org-setup.mjs` (`npm run setup`) automates login → build → deploy → permset →
dev-server, but it does **not** discover the WebStore, replace the placeholders, or entitle the
site's guest user (the README's own "Limitations" say there is no auto-discovery). Those
gaps are exactly the manual work below — do them, and the deploy is reliable.

**Requires:** Node 22+, `sf` CLI 2.130+, and a target org with B2B Commerce + Multi-framework React
enabled (API version `67.0+`). Only work against orgs the user owns or is authorized to modify — deploy,
Apex edits, and permission-set assignment are real, side-effecting writes.

## Fixed facts about the repo (don't re-derive these)

| Thing | Value |
|---|---|
| Repo clone URL | `https://github.com/trailheadapps/commerce-b2b-headless.git` (Step 3) |
| UI Bundle dir (`$BUNDLE`) | `force-app/main/default/uiBundles/commerceb2bheadless` |
| WebStore config file | `$BUNDLE/src/config/commerce.ts` |
| Registration Apex | `UIBundleRegistration.cls` (in the repo's Apex classes folder) |
| Vite config | `$BUNDLE/vite.config.ts` |
| Auth permission set | `UIBundleApexAccess` (grants the 6 auth Apex classes) |
| Site name | `commerceb2bheadless` — also the storefront URL path: `https://<site-domain>/commerceb2bheadless` |
| Connect `urlPathPrefix` | `commerceb2bheadlessvforcesite` (internal match key for Step 7 — **not** the URL path) |
| Default API version | `v67.0` (leave unless the org runs a different version) |

## The four values you must set

Everything else in the repo is portable. These four are environment-specific — resolve each against
the target org, then write it into the file (Steps 4a–4d): the **WebStore Id** (`0ZE…`), the default
**BuyerGroup Id** (`0ZI…`), the buyer **permission set group** DeveloperName, and the optional Vite
**org alias**.

---

## Workflow

Narrow with `sf` queries before you ask the user anything, and don't ask what a query can answer.
Two choices are always the user's to make, even when there is only one option: **which store**
(Step 2) and **where the repo lives** (Step 3). Confirm the plan (which org, which store, what will
be written and deployed) before the first write.

### Step 1 — Resolve the target org

If the user gave an org alias, use it. Otherwise list what's connected and ask which one:

```bash
sf org list --json | jq -r '.result.nonScratchOrgs[]?.alias, .result.scratchOrgs[]?.alias'
```

Confirm it's reachable. Do **not** run bare `sf org display` — it prints the org's access token into
the conversation. Project only the non-secret fields:

```bash
sf org display --target-org <alias> --json | jq -r '.result | "\(.connectedStatus) \(.instanceUrl) API \(.apiVersion)"'
```

Expect `Connected`. If it prints anything else, log in:
`sf org login web --alias <alias> --instance-url https://<my-domain>.my.salesforce.com`.

### Step 2 — Discover the org's WebStores, let the user pick

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Name, Type FROM WebStore WHERE Type = 'B2B' ORDER BY Name"
```

The storefront is B2B-only, so list only `Type = 'B2B'` stores. **Always ask the user which store
to deploy against — show every B2B store by Name and let them choose, even when there is only
one. Never pick a store on the user's behalf**, and don't fold the choice into a later plan
confirmation: the store decides which catalog, buyer groups, and pricing the deployed storefront
serves. Capture the chosen store's `Id` (`0ZE…`); this is **value #1** and also scopes the
BuyerGroup lookup in Step 4b. If the query returns nothing, the org has no B2B store provisioned —
stop and point the user at the `b2b-commerce-org-setup` plugin to create one first.

### Step 3 — Ask where the repo is, or clone it

**Ask the user first** — don't probe default locations or assume a path: do they already have a
clone of `commerce-b2b-headless` (and where is it), or should you clone it from
`https://github.com/trailheadapps/commerce-b2b-headless.git`?

**Existing clone** — set `$REPO` to the path the user gives, then verify it's the right repo:

```bash
ls "$REPO/README.md" "$REPO/force-app/main/default/uiBundles/commerceb2bheadless" >/dev/null && echo OK
```

If the check fails, tell the user what's missing and ask again — don't switch to cloning unasked.

**Clone** — the clone goes inside the current working directory. Check that directory's structure
first, so the clone doesn't silently land inside another git repo or on top of an existing folder:

```bash
pwd && ls -A
git rev-parse --show-toplevel 2>/dev/null   # prints a path ⇒ cwd is inside another git repo
ls -d commerce-b2b-headless 2>/dev/null     # prints a name ⇒ the target folder already exists
```

Propose `$(pwd)/commerce-b2b-headless` as the clone path and call out anything the check surfaced
(cwd is inside another repo; the folder already exists — offer to use it as the existing clone).
If the cwd looks like the wrong place, ask the user for a path instead of proposing one. Either
way, **wait for the user to confirm the path or give their own**. Only then clone and verify:

```bash
git clone https://github.com/trailheadapps/commerce-b2b-headless.git "<confirmed-path>"
ls "<confirmed-path>/force-app/main/default/uiBundles/commerceb2bheadless" >/dev/null && echo OK
```

If the clone fails with "Repository not found" or an auth prompt, the user's GitHub account can't
see the repo — don't stop; ask for a URL they can reach (e.g. their fork) or an existing local
clone, and continue from there. Set `$REPO` to the confirmed path.

Either way, show the user the code Step 5 will build and run on this machine, and get their OK unless
the origin is `trailheadapps/commerce-b2b-headless` on github.com (any URL form).

```bash
git -C "$REPO" remote get-url origin | sed -E 's#(://)[^/@]*@#\1#'   # credentials stripped
git -C "$REPO" log -1 --date=short --format='%h %cd'
```

Either way, the repo is a **reference implementation you adapt**, not a drop-in — the placeholder
edits below are mandatory. Skim `$REPO/README.md` to
confirm you're on a compatible version if anything looks different from the Fixed-facts table.

### Step 4 — Fill the four org-specific values

Use `Edit` to replace each placeholder in place. Do **not** deploy with any `<…Placeholder>` string
still present — the app throws at runtime and buyers hit `INSUFFICIENT_ACCESS`.

**4a — WebStore Id** → `$BUNDLE/src/config/commerce.ts`
Replace `WEBSTORE_ID: "<Webstore_Id_Placeholder>"` with the `0ZE…` Id from Step 2.

**4b — Default BuyerGroup Id** → `UIBundleRegistration.cls` `DEFAULT_BUYER_GROUP_ID`
Prefer the BuyerGroup actually bound to the chosen store; fall back to listing all:

```bash
# Preferred — the BuyerGroup(s) entitled to this store:
sf data query --target-org <alias> \
  --query "SELECT BuyerGroupId, BuyerGroup.Name FROM WebStoreBuyerGroup WHERE WebStoreId = '<0ZE…>'"
# Fallback — all BuyerGroups:
sf data query --target-org <alias> --query "SELECT Id, Name FROM BuyerGroup"
```

If more than one, show the names and let the user pick. Replace `<Buyer_Group_Id_Placeholder>` with
the `0ZI…` Id. New self-registered buyers get enrolled here so the store entitlement applies.

**4c — Buyer permission set group** → `UIBundleRegistration.cls` `BUYER_PERMISSION_SET_GROUP`

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DeveloperName, MasterLabel FROM PermissionSetGroup ORDER BY DeveloperName"
```

This must match the PSG the store hands buyers at **Commerce App → your store → Buyer Access →
Self-Registration**. Show the list, let the user confirm which one, and replace
`<Buyer_permission_set_group>` with its **DeveloperName**. Wrong/missing group ⇒ registration
succeeds but order placement fails with `INSUFFICIENT_ACCESS`.

**4d — Vite org alias (optional but recommended)** → `$BUNDLE/vite.config.ts`
If the machine has more than one org, pin the build to this one so the SDK's CSRF endpoint matches
the org's API version. Change `salesforce()` to `salesforce({ orgAlias: '<alias>' })`. Skipping it
falls back to `65.0`, which mismatches newer orgs and 401s every authenticated request.

### Step 5 — Build the UI Bundle, then hand off the deploy

The `dist/` is what gets shipped, with the WebStore Id (Step 4a) baked in at build time. Build inside
the bundle and delete any existing `dist/` first — if the build fails partway, an earlier build's
`dist/` (old or placeholder values) would otherwise deploy silently. Confirm the chosen WebStore Id
made it into the bundle before deploying.

**First, check the clone holds nothing but your Step 4 edits** — the install and build run the repo's
scripts and `vite.config.ts` on this machine. With `REPO` set to the repo's absolute path:

```bash
( set -eu -o pipefail
  cd "${REPO:?}"
  D=force-app/main/default; U=$D/uiBundles/commerceb2bheadless
  ok="( M|M |MM) ($U/src/config/commerce\.ts|$U/vite\.config\.ts|$D/classes/UIBundleRegistration\.cls)"
  ok="$ok|!! ($U/(node_modules|dist)(/.*)?|\.sf(dx)?/|.*\.tsbuildinfo)"
  left=$( { git status --porcelain --ignored -unormal --ignore-submodules=none
            git ls-files -v | sed -n 's/^[^H] /hidden-by-index-flag: /p'; } | { grep -vE "^($ok)\$" || [ $? = 1 ]; } )
  [ -z "$left" ] || { printf 'GATE FAIL:\n%s\n' "$left"; exit 1; }
  echo "GATE PASS" )
```

Only `GATE PASS` lets you continue; `GATE FAIL`, an error, or no output is a **STOP** — show the user
the output and go on only if they confirm each item (say, the Chatter change from an earlier run).
Then skim `git diff HEAD`: only the Step 4 values should differ. This doesn't vet the repo's code,
`.git` hooks, or install scripts.

Install with `npm ci`, not `npm install`: it installs exactly what the committed `package-lock.json`
pins and fails rather than resolve anything new. If it fails, stop and tell the user.

```bash
cd "$REPO/force-app/main/default/uiBundles/commerceb2bheadless" && rm -rf dist && npm ci && npm run build   # tsc -b && vite build → fresh dist/
grep -l '<0ZE…>' dist/assets/*.js >/dev/null && echo "WebStore Id baked"
```

**Before the deploy, flag the guest Chatter setting.** The repo's metadata is a demo-org
configuration: `force-app/main/default/networks/commerceb2bheadless.network-meta.xml` ships
`<enableGuestChatter>true</enableGuestChatter>`, which exposes Chatter to unauthenticated guest
users. Tell the user before deploying and offer to set it to `false`; change it only if they agree.
On a production org (or if the user isn't sure), don't deploy until they confirm they've reviewed
the README's "Review all org, site & network settings before production" section, which lists the
other network, site, profile, and permission-set flags to check.

#### Deploy — delegate

```yaml
id: deploy-source
purpose: delegate
delegates_to: experience-sites-ui-framework/experience-ui-bundle-deploy
```

The shared `experience-ui-bundle-deploy` skill owns UI Bundle deploys, so this skill keeps no deploy
recipe of its own. Use the installed skill if this client has it; otherwise `describe`
`experience-ui-bundle-deploy` and follow its served guidance — its helper scripts, including the
source-root resolver, are served with it. Point it at `$REPO` as the project and `<alias>` as the
target org, and run **only its "Deploy metadata" step** (its org-auth precondition no-ops, since
Step 1 already connected the org). Let it resolve the source root itself. The reference repo ships
no `org-setup.config.json`, so that step's self-registration pre-check doesn't apply.

Tell the user which of its other steps you are not running, and why: its build (done above, with
the stale-`dist/` delete it lacks), and its permission-set, role, self-registration, social-login,
data-import, and GraphQL steps. Step 6 here entitles the guest user, and the storefront needs
nothing else from that sequence.

The deploy ships the Apex, the UIBundle (with the fresh `dist/`), the Site/Network/digitalExperiences,
the `UIBundleApexAccess` permission set, and the buyer profile in one shot. Only if neither the
installed skill nor a `describe` of it is available, report the deploy handoff as blocked. Tell the
user it needs `experience-ui-bundle-deploy`, or offer the One-command alternative below as their
choice — don't improvise a deploy.

### Step 6 — Entitle the site's guest user (auth permission set)

The app puts every storefront route — home, category, search, product, cart, checkout, orders,
profile — behind login: an anonymous visitor is redirected to `/login`. So the site's **guest user**
only ever serves the login / register / forgot-password / reset-password pages, and the one thing it
needs is `UIBundleApexAccess` for the auth Apex classes. Find the guest user and the permset:

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Name, GuestUserId FROM Site WHERE Name = 'commerceb2bheadless'"
sf data query --target-org <alias> \
  --query "SELECT Id FROM PermissionSet WHERE Name = 'UIBundleApexAccess'"
```

Assign it (without it, `/login` 403s "no access to UIBundleLogin"):

```bash
sf data create record --target-org <alias> --sobject PermissionSetAssignment \
  --values "AssigneeId=<GuestUserId> PermissionSetId=<UIBundleApexAccessId>"
```

A `DUPLICATE_VALUE` error means the assignment already exists from an earlier run — treat it as done.
Either way, confirm it landed (expect one row; zero means redo the assignment):

```bash
sf data query --target-org <alias> \
  --query "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<GuestUserId>' AND PermissionSet.Name = 'UIBundleApexAccess'"
```

**Don't give the guest user a commerce permission set** — for example, by mirroring an LWR store
guest's permset. Anonymous browsing isn't reachable in this app, so there's nothing for it to
unlock (and an LWR store's guest often holds no such permset). If the
user later removes the login guard to allow guest browsing, B2B guest access is configured on the
store — `WebStore.OptionsGuestBrowsingEnabled`, the guest buyer profile, and a guest buyer group (the
`merchant-storefront-guest-access` skill) — and the WebStore likely also needs binding to the
headless site's Network (`WebStoreNetwork`). That path is unverified for this app, so flag it rather
than attempt it.

### Step 7 — Resolve and hand back the hosted storefront URL

The app is served at `https://<site-domain>/commerceb2bheadless`. Get the authoritative live URL from
the Connect communities endpoint, matching on the site's internal `urlPathPrefix` (which differs from
the URL path):

```bash
sf api request rest '/services/data/v67.0/connect/communities' --target-org <alias> \
  | jq -r '.communities[] | select(.urlPathPrefix=="commerceb2bheadlessvforcesite") | "\(.name)\t\(.status)\t\(.siteUrl)"'
```

Report the `siteUrl` as **"here is your hosted React Storefront"**. If `status` is not `Live`, the
site needs publishing — direct the user to **Setup → Digital Experiences → All Sites →
commerceb2bheadless → Publish** (Experience Builder), then re-fetch the URL. If the endpoint returns
nothing, construct the fallback `https://<my-domain>.my.site.com/commerceb2bheadless` — the path is
the site name, not the `vforcesite` prefix. Get `<my-domain>` from the `instanceUrl` Step 1 printed;
non-production instances use a different site-domain suffix, so tell the user to verify the URL in
All Sites.

---

## One-command alternative

If the four values are already set (Step 4 done), the repo's own orchestrator does build → deploy →
permset in one go:

```bash
cd "$REPO" && npm run setup -- --target-org <alias> --skip-dev --skip-data
```

Caveats — it does **not** replace the placeholders and it assigns `UIBundleApexAccess` to the
**current user**, not the guest user, so you **still** run Step 4 before it and Step 6 (the guest
assignment) after it. Run Step 3's origin print and Step 5's check before it too: it runs the repo's
code and installs with `npm install`, not `npm ci`. Drop `--skip-dev` only if the user wants the
local Vite dev server (`localhost:5173`) instead of / in addition to the hosted site. If the bundle
has no GraphQL codegen wired, add `--skip-graphql`.

## Troubleshooting (from the repo README)

- **`/login` returns 403 "no access to UIBundleLogin"** — guest user missing `UIBundleApexAccess`; redo Step 6.
- **Anonymous visitors land on `/login`** — by design; every storefront route requires login (Step 6). Register or log in as a buyer to browse.
- **`/commerce/...` returns 404 from the Site Container** — org is older than API version `67.0` (no Site Container support); upgrade the org.
- **Storefront shows no products** — the buyer's Account isn't in a BuyerGroup with active price book entries for the catalog.
- **Every authenticated request 401s** — Vite fell back to API `65.0`; set the org alias (Step 4d) and rebuild.
- **Order placement fails `INSUFFICIENT_ACCESS`** — wrong/missing buyer PSG (Step 4c).
- **Storefront still shows old or placeholder values after a redeploy** — a stale `dist/` shipped; delete it and rebuild (Step 5).

## Notes

- **Dual-network:** the headless storefront runs on its own Network, coexisting with the legacy LWR store's Network. Both stay in the org.
- **Don't rename** the Apex classes, `UIBundleApexAccess`, or the site URL prefix — they're cross-referenced by the React app, the permission set, and this skill's queries.
- This is a live-org workflow: name the org, the store, and every write before doing it, and never deploy against an org the user hasn't authorized.

<!-- skill-validate: ignore-start -->
<!-- codey:operations start -->
## Operations Reference

Operations this skill uses — routing and dependency reference.

| Operation | Purpose | Status | Call | Depends on |
|-----------|---------|--------|------|------------|
| `list-webstores` | read | — | `GET /services/data/v67.0/query` | — |
| `write-webstore-id-placeholder` | write | — | — | `list-webstores` |
| `list-buyer-groups-for-store` | read | — | `GET /services/data/v67.0/query` | `list-webstores` |
| `list-buyer-groups-all` | read | — | `GET /services/data/v67.0/query` | `list-buyer-groups-for-store` |
| `write-buyer-group-id-placeholder` | write | — | — | `list-buyer-groups-for-store`, `list-buyer-groups-all` |
| `list-permission-set-groups` | read | — | `GET /services/data/v67.0/query` | — |
| `write-psg-placeholder` | write | — | — | `list-permission-set-groups` |
| `write-vite-org-alias` | write | — | — | — |
| `build-ui-bundle` | write | — | — | `write-webstore-id-placeholder`, `write-buyer-group-id-placeholder`, `write-psg-placeholder`, `write-vite-org-alias` |
| `deploy-source` | delegate | — | → `experience-sites-ui-framework/experience-ui-bundle-deploy` | `build-ui-bundle` |
| `find-site-and-guest-user` | read | — | `GET /services/data/v67.0/query` | `deploy-source` |
| `find-uibundleapexaccess-permset` | read | — | `GET /services/data/v67.0/query` | `deploy-source` |
| `assign-auth-permset-to-guest` | write | — | `POST /services/data/v67.0/sobjects/PermissionSetAssignment` | `find-site-and-guest-user`, `find-uibundleapexaccess-permset` |
| `resolve-storefront-url` | read | — | `GET /services/data/v67.0/connect/communities` | `deploy-source` |
| `verify-guest-permset-assignment` | verify | — | `GET /services/data/v67.0/query` | `assign-auth-permset-to-guest` |
<!-- codey:operations end -->
<!-- skill-validate: ignore-end -->
