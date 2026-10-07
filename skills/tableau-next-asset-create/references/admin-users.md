# Admin users and licenses — payloads and gotchas

Load this from `tasks/provision-user.md`. Not a first hop.

Tableau Next **role** provisioning is org-admin, not asset ACL. Sharing an
asset (`search_users_and_groups` / `add_asset_share`) stays on
`tasks/share-asset.md`.

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected.

## Contents

- `get_users` — list / search (ADMIN-ONLY)
- `get_license_availability` — seats before ADD or role upgrade
- `upsert_user` — ADD / UPDATE / REVOKE / DEACTIVATE (never on the request turn)

All three tools are **ADMIN-ONLY**. If any returns a permission / unauthorized
error, report it and **STOP**. Do not retry and do not fall back to analyst
tools (`search_users_and_groups`, share tools, ingest). Unauthorized here means
the current user is not a Tableau Next admin.

---

## `get_users`

Retrieve Tableau Next users for admin management. Only **Standard** users are
returned. Filters apply **server-side**, so `limit` / `offset` is the filtered
set, not the unfiltered org.

**Inputs (all optional):**

- `searchQuery` — case-insensitive substring on name, username, or email
- `role` — exact: `ADMIN`, `ANALYST`, `SELF_SERVICE_ANALYST`,
  `SELF_SERVICE_CONSUMER`, `CONSUMER`. Unrecognized values are rejected
- `license` — permission-set-license key; users whose role grants it
- `isActive` — `true` / `false`; omit for both
- `limit` — default 50, capped at 2000
- `offset` — **omit on the first page** (starts at 0)

**Returns:** `items[]` (`id`, `name`, `email`, `isActive`, plus derived `role`
and `license` when the user holds a Tableau Next role), `size`, `nextOffset`.

**Pagination.** Omit `offset` on the first call. Pass the returned
`nextOffset` back as `offset`. Continue until a page has fewer than `limit`
items (or is empty).

**Use when:** browse or find users before granting or revoking a role.

---

## `get_license_availability`

Call **before** `upsert_user` ADD or a role upgrade. When `available` is `0`
or `exhausted` is `true` for the target license class, **warn** and do not
attempt the change.

**Inputs (optional):** `licenseType` — same role enum as `get_users`. Omit to
return every Tableau Next license class.

**Returns:** `items[]` with `licenseKey`, `label`, `total`, `used`,
`available`, `exhausted`, plus `size`.

---

## `upsert_user`

Provision a Tableau Next user by role. **Never call on the turn the admin
makes the request.** Present a per-action preview (below) and wait for
explicit approval in a **separate** turn. This applies to every action,
including ones that look clear or urgent.

The caller must choose the action. This tool never infers ADD vs UPDATE vs
REVOKE vs DEACTIVATE.

### Required inputs

- `action` — `ADD` | `UPDATE` | `REVOKE` | `DEACTIVATE`
- `email` — also the login / username
- `firstName`, `lastName`
- `role` — `ADMIN` | `ANALYST` | `SELF_SERVICE_ANALYST` |
  `SELF_SERVICE_CONSUMER` | `CONSUMER`

Optional: `localeSidKey` (e.g. `en_US`), `timeZoneSidKey` (e.g.
`America/Los_Angeles`), `alias`.

`forceDeactivate` (boolean, DEACTIVATE only, default `false`) — set `true`
**only** after the admin consents to deactivate a Personal Org owner.

**Returns:** `created`, `userId`, and a human-readable `message`.

### What each action does

- **ADD** — creates a brand-new user and grants the role.
- **UPDATE** — sets an **existing** user to the role. Roles are mutually
  exclusive: switching Admin → Analyst leaves Analyst only. Permission set
  and permission-set license for the new role are granted; any other Tableau
  Next role permission set is removed.
- **REVOKE** — removes the role's permission set(s); the user remains active.
- **DEACTIVATE** — sets the user inactive (cannot log in). Role permission
  sets stay in place.

`firstName` / `lastName` apply **only on ADD**. They are ignored for UPDATE,
REVOKE, and DEACTIVATE. This tool **cannot rename** an existing user — tell
the admin that if they ask.

### ADD CONFLICT ≠ silent UPDATE

ADD fails with **CONFLICT** when a user already exists for the email. That is
intentional. **Do not** silently retry as UPDATE. Report the conflict and get
explicit confirmation before granting the role via UPDATE (UPDATE changes that
user's permissions).

### "Remove access" ≠ DEACTIVATE

Never infer DEACTIVATE from an ambiguous instruction. "Remove access" may mean
REVOKE (drop the Tableau Next role) or an **asset share** revoke
(`share-asset.md`). Ask. DEACTIVATE is the most destructive: the user loses
login and access to their Tableau Next content and assignments.

### Personal Org owner CONFLICT

The tool enforces the Personal Org owner check **server-side**. First
DEACTIVATE call: omit `forceDeactivate` (or pass `false`). If the user owns
one or more Personal Orgs, the tool does **not** deactivate them; it returns
CONFLICT stating they own a Personal Org and will be removed as owner.

Relay that to the admin. Only if they **explicitly consent** re-invoke
DEACTIVATE with `forceDeactivate=true`. Never set `forceDeactivate` true on
the first call.

### Preview formats (mandatory, all actions)

**(ADD)** Structured summary of the new user — name, email, role, permission
set(s), license type — then: "This user has not been created yet. Please
confirm to proceed."

**(UPDATE)** Side-by-side Current vs Proposed for every field that will
change (role, permission set(s), permission-set license(s)) — then: "These
changes have not been saved yet. Would you like to proceed?"

**(REVOKE)** Summarize the role and permission set(s) that will be removed.
Confirm before calling.

**(DEACTIVATE)** After describing access/content impact, show:
"⚠️ This will deactivate [name] ([email]) and revoke their access." then
"Please confirm to proceed." If the first call returns the Personal Org
owner CONFLICT, add "They will be removed as personal org owner." and
re-confirm before `forceDeactivate=true`.
