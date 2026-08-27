# Network metadata edit recipe (two-phase)

Ported from reference `org-setup-xml.mjs` (`addProfileToMemberGroups` lines 125-147,
`enableSelfRegInXml` lines 158-182) and `org-setup.mjs`
(`ensureNetworkMemberProfile` 524-566, `enableSelfRegistration` 580-617).

**These two edits are NOT applied together.** The reference splits them across the
deploy so the profile is a recognised site member before self-registration is
switched on:

- **Edit A** runs in **Step 3, before the main `sf project deploy start`** — it
  adds the profile to `networkMemberGroups` on the local source, so the profile
  deploys as a site member alongside everything else. (org-setup.mjs 1434-1445:
  "This must happen BEFORE the initial deploy so that the profile is a recognised
  site member when subsequent steps … are deployed.")
- **Edit B** runs in **Step 6 (the self-reg step)** — it flips
  `selfRegistration` to `true`, injects `<selfRegProfile>`, and is followed by a
  **network-only redeploy** of just that one file.

## File to edit

`<packageDir>/main/default/networks/<siteName>.network-meta.xml`

`<siteName>` is the base name of the **single** `*.network-meta.xml` file under
`networks/`. If there is more than one such file, STOP — the site is ambiguous
and the reference implementation refuses to guess (see `deriveSiteName`,
`references/self-registration.md`).

`<selfRegProfile>` must contain no XML-special characters. Reject a name with
`< > & " '` as a config error rather than escaping it — profile names are
developer-authored config, not user input.

## Edit A — add the profile to member groups (Step 3, pre-main-deploy, idempotent)

Apply this to the local source **before** the Step 3 main deploy. Do NOT deploy
the file on its own — the main deploy ships it. Best-effort: if the
`<networkMemberGroups>` node is missing, surface a loud error but continue to
deploy (the self-reg step records the authoritative failure — org-setup.mjs
540-558).

Under the existing `<networkMemberGroups>` element, ensure the self-reg profile
is listed. **Skip this edit** if `<profile><selfRegProfile></profile>` is already
present (changed: false). Otherwise insert it immediately after the opening tag,
matching the file's existing member indentation:

```xml
<networkMemberGroups>
    <profile><selfRegProfile></profile>
    <!-- ...existing members unchanged... -->
</networkMemberGroups>
```

## Edit B — enable self-registration + set the profile (Step 6, idempotent)

Apply this during the self-reg step, then redeploy only this file (below).
**Skip this edit** if `<selfRegistration>` is already `true` OR a
`<selfRegProfile>` element already exists (changed: false — same skip semantics
as the reference). Otherwise apply BOTH targeted edits:

1. Flip the flag:

   ```xml
   <selfRegistration>false</selfRegistration>   <!-- becomes -->
   <selfRegistration>true</selfRegistration>
   ```

2. Insert `<selfRegProfile>` immediately before `<selfRegistration>`, preserving
   the leading whitespace/indent of that line:

   ```xml
   <selfRegProfile><selfRegProfile></selfRegProfile>
   <selfRegistration>true</selfRegistration>
   ```

A missing `<selfRegistration>` node is an error to surface, not to silently
no-op.

## Redeploy the edited file (Edit B only)

After Edit B, deploy only the one network file (not the whole project):

```bash
sf project deploy start --target-org <org> --source-dir <path-to>/<siteName>.network-meta.xml
```

Timeout 120s. If nothing changed (Edit B was skipped), no redeploy is needed.
