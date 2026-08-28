# Disk contract — where the brand file goes so the Brand Toolkit loads it

The Brand Toolkit (the VS Code "Brand Toolkit" panel) discovers local brands by
scanning one directory in the open workspace. To make a generated brand
loadable / editable / previewable, write ONE file to the right place with the
right name. The toolkit does the rest (derived colors, compiled CSS,
active-brand config) when the user opens or saves the brand — you do not need to
produce those.

## Where the toolkit looks

On startup and on refresh, the toolkit enumerates:

```text
<workspaceRoot>/.digitalExperience/brands/*.brand.json
```

Every file matching `*.brand.json` in that directory becomes one entry in the
toolkit's **Local** brand list, keyed by its `sfdc_cms:title`.

## What to write

Write the brand JSON (the object from `assets/brand-template.json` with your
edited leaf values) to:

```text
<workspaceRoot>/.digitalExperience/brands/<slug>.brand.json
```

- **Content:** the brand object exactly as authored — the **unwrapped body**, NOT
  wrapped in any `{ contentBody: … }` envelope. Pretty-print it (2-space indent).
- Create the `.digitalExperience/brands/` directory if it doesn't exist.

### The `<slug>` — derive it from the title the same way the toolkit does

The toolkit turns a brand title into a filename slug with this exact rule:

```js
slug = title.toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')   // any run of non-alphanumerics -> single _
            .replace(/^_|_$/g, '')          // trim leading/trailing _
        || 'brand'                          // fallback if the title had no alphanumerics
```

Examples: `"Sunset Coral"` -> `sunset_coral`; `"Acme — Dark!"` -> `acme_dark`;
`"2024 Refresh"` -> `2024_refresh`.

Matching this rule keeps the file the toolkit writes on Save consistent with the
file you create, so you don't end up with a duplicate. If a
`<slug>.brand.json` already exists and you intend a NEW brand (not an overwrite),
append the lowest free numeric suffix (`<slug>_2`, `<slug>_3`, …) — the same
scheme the toolkit's "Save as New" uses.

## What you do NOT write (the toolkit generates these)

- **`<slug>.css`** — the compiled `--tm-*` stylesheet. The toolkit compiles it
  from the brand JSON when the user saves. Don't author CSS.
- **`.digitalExperience/config/activeBrand.json`** — records which brand is
  active. The toolkit writes it on Save. Don't create it just to author a brand;
  creating one out of band can point "active" at a brand that isn't selected.
- **`primaryAccentDerived` / `primaryAccentContrastDerived`** inside the JSON —
  the toolkit computes these on load. Omit them (the template omits them).

## After writing — how the user sees it

1. Open the **Brand Toolkit** panel in VS Code (Command Palette → the theme /
   brand preview command).
2. The new brand appears in the **Local** tab, listed by its `sfdc_cms:title`.
   If the panel was already open, use its refresh so the new file is picked up.
3. Selecting it renders the live preview, computes the derived hover colors, and
   opens the property editors. From there the user can tweak and **Save** (which
   writes the compiled `.css` and `activeBrand.json`).

## Quick verification checklist

- [ ] File is at `<workspaceRoot>/.digitalExperience/brands/<slug>.brand.json`.
- [ ] JSON is valid and parses (no trailing commas, quoted keys).
- [ ] It is the unwrapped brand body (top-level `sfdc_cms:title`, `colorScheme`,
      `fontFamily`, … — NOT `{ contentBody: … }`).
- [ ] `sfdc_cms:title` is present and unique among existing local brands.
- [ ] `<slug>` matches the slug rule applied to the title.
- [ ] No `*Derived` color keys were hand-authored.
- [ ] Every font referenced resolves to a system font or "Salesforce Sans" (see
      `references/brand-anatomy.md`) so the preview renders it.
