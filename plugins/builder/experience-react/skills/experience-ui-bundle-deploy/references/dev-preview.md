# Dev preview — launch the local site against an org

Detail for the **optional preview** step. This documents how the user's project
typically implements the preview flow (via an `org-setup-dev.mjs` script and
a `package.json` entry that invokes it).

This is **not part of setup** — it is a separate, long-lived developer action.
It assumes the org is **already** deployed and permissioned (run the 8 setup
steps first). It does **not** log in and does **not** deploy metadata; it only
refreshes the local GraphQL types against the org, then starts the Vite dev
server.

## Command

```bash
npm run dev:preview -- [--target-org <alias>] [--ui-bundle-name <name>]
```

- `--target-org <alias>` — target org. If omitted, the script prompts to pick an
  authenticated org (or uses the default org).
- `--ui-bundle-name <name>` — the folder under `uiBundles/`. If omitted, it
  auto-detects the single bundle or prompts when there is more than one.

Run it from the **project root** (the `npm` script `cd`s into the bundle itself).

## Flow (what the script does, in order)

1. Resolve the target org (`--target-org` else prompt / default org).
2. Resolve the UI bundle dir under `uiBundles/` (`--ui-bundle-name` else
   auto-detect / picker).
3. `npm install` in the UI bundle.
4. `SF_TARGET_ORG=<org> npm run graphql:schema` — introspect the live schema.
5. `npm run graphql:codegen` — regenerate typed operations from that schema.
6. `npm run dev` — launch the Vite dev server. **Blocking** — it runs until the
   user stops it with Ctrl+C.

## Local preview limitations

`npm run dev:preview` runs the app in the Vite dev server with `sdk.fetch` proxied
to the org **outside the Experience site's guest/community context**. Some auth
surfaces therefore **cannot be exercised locally** — this is expected, not a
misconfiguration:

- **Social Login buttons do not render.** The built-in Social Login component calls
  `/auth/social-login-config`, which returns no providers because `Site.getBaseUrl()`
  is blank outside the site context — even when providers are correctly linked
  (SKILL.md step 6b). The Social Login section simply renders nothing.
- **Password / MFA login does not complete.** `Site.login()` cannot establish the
  site session, so login returns *"Your login attempt has failed…"* and any MFA
  challenge never renders.

Test social login and MFA on the **published** site login page
(`https://<domain>.site.com/<site-path>/login`), not on `localhost`.

`npm run dev:preview` prints this same warning to the CLI just before it launches
the dev server, so the limitation is visible even without reading this reference.

## When to use it vs. the setup GraphQL step

- **Setup step 8** (`references/graphql.md`) refreshes schema/types and then
  `npm run build`s the bundle for deployment — it terminates.
- **Preview** re-runs the same schema + codegen refresh but then launches the
  live dev server instead of building. Use it after setup (or after any later
  deploy that changed objects/fields/permissions) when the user wants to see the
  site locally against real org data.

Because it re-introspects the schema every launch, a preview started after a new
deploy already reflects the latest org state — no separate step-8 rerun is needed
just to preview.
