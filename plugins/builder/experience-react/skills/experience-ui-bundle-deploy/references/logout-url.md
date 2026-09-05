# Logout URL — steer Sign Out back to this site

Detail for the **logoutUrl** step (SKILL.md step 3b). The step is executed by the
deterministic helper `scripts/set-logout-url.mjs` (a faithful port of the
reference `org-setup.mjs` logout-URL logic); this file covers **why** it exists
and **how** to run it, not a re-specification of the algorithm.

Source of truth for the behavior: reference `org-setup.mjs` `ensureLogoutUrl`
(1103-1169) and the `main()` logout-URL step (2137-2148); the pure resolution
helpers in `org-setup-url.mjs` (`isAbsoluteLogoutUrl`, `firstPathSegment`,
`pickCommunityBaseUrl`, `resolveLogoutUrl`) and the XML helpers in
`org-setup-xml.mjs` (`assertSafeLogoutUrl`, `setLogoutUrl`) — all reproduced in
`scripts/set-logout-url.mjs`. Config schema: `org-setup-config-schema.mjs`
(93, `logoutUrl: z.string().min(1).optional()`).

Provenance: this step ports the "logout redirects to the login page of a
different site" fix, added to `org-setup.mjs` but not previously reflected in this
skill.

Run this step **only** when a top-level `logoutUrl` is set in
`org-setup.config.json`. If it is absent, the step is a clean no-op — say so.
Unlike self-registration and data import, it is **non-destructive and
idempotent**, so it does **not** require asking first.

## Why it matters

An Experience Cloud site with no `<logoutUrl>` on its Network sends a logging-out
member to the **org default-site login page**. In an org hosting more than one
Experience/CLWR site, that default is a *different* community — so Sign Out drops
the user on the wrong site's login page. Setting `<logoutUrl>` to this site's own
URL steers logout back here (the user reloads as Guest on the same site).

## Why it runs AFTER deploy (step 3b, not folded into deploy)

The platform **rejects a relative logout URL** at deploy time: *"The logout page
URL must be an absolute URL."* But a shipped template must stay
domain-independent, so apps ship a **site-relative** path (e.g.
`"logoutUrl": "/propertyrentalapp/"`) that is valid on every org they deploy to.
Resolving that to the absolute URL the platform requires needs the site's
Experience Cloud **origin**, which is only discoverable (via the Connect
communities API) once the site exists — i.e. after the main deploy. An
already-absolute config value (`http(s)://…`) is used as-is, with no lookup.

## How to run

```bash
node scripts/set-logout-url.mjs \
  --logout-url "<logoutUrl from org-setup.config.json>" \
  --network-file <sourceRoot>/networks/<site>.network-meta.xml \
  --target-org <org> \
  --site <site> \
  --deploy
```

Derive `<site>` first with `scripts/derive-site-name.sh` (it prints the base name
of the single `*.network-meta.xml`, or exits non-zero when zero or more than one
exist — an ambiguous site is skipped, never guessed). Omit `--deploy` to resolve
and write the file **without** deploying (e.g. to inspect the change first).

### What the helper does (so you don't re-derive it)

- **Resolves** the config value to an absolute URL: already-absolute → used
  verbatim; site-relative → its origin is matched from the org's communities
  (`/connect/communities`, at the org's current API version), **path-first** then by site name, and it
  refuses to fall back to an arbitrary community (resolving against the wrong
  origin would silently produce a valid-but-wrong URL).
- **Writes** `<logoutUrl>` into the network metadata idempotently — replaces an
  existing value in place, or inserts a new node in the canonical alphabetical
  position; an already-correct value is a byte-for-byte no-op (no deploy).
- **Rejects** a URL containing an XML-special character (`& < > " '`) rather than
  escaping it.
- **Deploys** only the one network file (with `--deploy`).

### Exit-code contract (best-effort)

| Exit | Meaning | What the step should do |
|------|---------|-------------------------|
| `0` | Applied (changed), already-correct (unchanged), or deployed | Report success; continue. |
| `3` | **Recoverable skip** — network file missing, origin unresolvable, XML-special char, or deploy failed | **Do not treat as a setup failure.** Continue the rest of setup; tell the user to set the logout URL manually. |
| `1` | Usage / argument error | Fix the invocation. |

On a skip, tell the user to **set the logout URL manually in the site's
Administration settings** (Setup → Digital Experiences → the site →
Administration → Login & Registration → Logout URL).

## Config shape

```json
{ "logoutUrl": "/propertyrentalapp/" }
```

- Top-level key (a sibling of `permsetAssignments` / `socialLogin`), optional.
- A **site-relative path** (recommended — domain-independent) or an absolute
  `http(s)` URL. A relative value is resolved to absolute at deploy time; an
  absolute value is used as-is.
- Like `selfRegistration` / `socialLogin`, there is **no `siteName`** — the site
  is derived from the single `networks/<site>.network-meta.xml`.
