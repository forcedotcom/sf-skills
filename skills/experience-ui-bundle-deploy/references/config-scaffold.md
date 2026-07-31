# org-setup.config.json — schema and scaffolding when it's missing

`org-setup.config.json` (at the project root) drives three steps: permission-set
assignment (step 4), role assignment (step 5), and self-registration (step 6).
Source of truth for the schema: reference `org-setup-config-schema.mjs`
(zod `.strict()` — unknown keys are rejected); consumption:
`loadPermsetConfig` / `resolveAssignment` (org-setup.mjs 464-478).

## Why a missing file is a trap for the permset step

When the file is absent, `loadPermsetConfig` returns
`{ defaultAssignee: 'skip', assignments: {} }` (org-setup.mjs 466), so **every**
permission set discovered under `permissionsets/` resolves to `skip` and is
silently not assigned. The deploy looks successful, but GraphQL introspection
(step 8) then returns an incomplete schema because the caller lacks FLS.

So: **permset folder present + config file absent = help the user create the
config (or gather equivalent inputs) rather than silently skipping.** Do not
fabricate assignments — confirm intent first (see below).

## Full schema

Every top-level key is optional; each object is strict (no extra keys).

```json
{
  "permsetAssignments": {
    "defaultAssignee": "currentUser | guestUser | skip",
    "assignments": {
      "<PermissionSetApiName>": { "assignee": "currentUser | guestUser | skip" }
    }
  },
  "role": { "assignee": "currentUser", "roleName": "<UserRole name>" },
  "selfRegistration": { "selfRegProfile": "<Profile API name>",
                        "accountName": "<display name>" }
}
```

- **`assignee`** is a closed set: `currentUser`, `guestUser`, or `skip` — never a
  raw username. `defaultAssignee` applies to any discovered permset not named in
  `assignments`; it defaults to `skip` when the `permsetAssignments` block is
  present but omits it.
- **No `siteName` anywhere** — for `guestUser` the site is derived from the single
  `networks/<siteName>.network-meta.xml` the app ships. If the assignee is
  `guestUser` and the site can't be derived or the guest user can't be resolved,
  that permset is skipped and recorded, not fatal (see step 4).
- **`role.assignee`** must be `currentUser` (the only value the flow honors);
  `roleName` is a non-empty `UserRole` name.
- **`selfRegistration`** has no license field — the required license is derived
  from `selfRegProfile` (see `references/license-checks.md`).

## Scaffolding flow (permset folder present, config missing)

1. **List the permission sets** under `<packageDir>/main/default/permissionsets/`
   (their file base names are the API names) so the choice is concrete.
2. **Ask the user, per permset, who to assign it to** — `currentUser`,
   `guestUser`, or `skip`. Default a whole-set answer to `currentUser` (not
   `skip`) since the folder exists on purpose; only use `guestUser` for permsets
   meant for the site's guest user. Also ask whether they want a `role` and/or
   `selfRegistration` block while you're writing the file (both optional).
3. **Offer two equivalent paths** — let the user pick:
   - **Write the file**: copy `assets/org-setup.config.template.json` to
     `org-setup.config.json` at the project root and fill in the answers. This is
     durable — re-runs and the reference `npm run setup` both read it.
   - **One-off inputs**: if they don't want a file, treat their answers as the
     config for this run only (assign each permset per the stated assignee via
     step 4's `sf org assign permset` command). Nothing persists.
4. **Validate before relying on it**: keys must match the strict schema exactly
   (e.g. it's `permsetAssignments`, not the singular `permsetAssignment`), and
   `assignee` values must be one of the three literals. Reject anything else and
   re-ask rather than writing an invalid file.

Prefer writing the file when the user is unsure — it makes the behavior
reproducible and matches what the reference tooling expects.
