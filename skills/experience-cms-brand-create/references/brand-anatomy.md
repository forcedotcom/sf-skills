# Brand anatomy — what to edit and what to leave alone

A brand is one JSON object (the `contentBody` of a CMS brand, saved **unwrapped**
— no envelope). Its shape is fixed: the Brand Toolkit's editors, the CSS
compiler, and the preview all expect every top-level section (`colorScheme`,
`fontFamily`, `fontSize`, `typography`, `buttonStyleGroup`, …) to be present with
the same keys as the template. **Start from `assets/brand-template.json` and
change only leaf values** — never drop a section, rename a key, or invent a new
one. A missing or misspelled key doesn't error; it silently falls back, so the
preview looks wrong with no explanation.

## The two kinds of values

1. **Literals** — the actual design values. These are the ONLY things you should
   change to create a new brand:
   - Colors: `colorScheme.*` (hex strings)
   - Base font: `baseFontFamily` (a reference — see below), `baseFontSize.value`
   - Corner rounding: `borderRadius.round.value`
   - Border thickness: `borderWeight.thin.value`, etc.
   - Per-role font sizes, weights, transforms inside `typography.*` if you want
     finer control (usually leave these as references to the shared scale).

2. **References** — strings like `"{!$brand.fontFamily.arial}"` or
   `"{!$brand.colorScheme.primaryAccent}"`. These are POINTERS into other parts
   of the same brand. The toolkit resolves them at load time. This is why editing
   one color (e.g. `colorScheme.primaryAccent`) automatically re-themes every
   button and accent that points at it. **Keep the references intact** — don't
   replace a reference with a hard-coded literal, or you break the live-edit link
   that makes the brand cohesive. To change what a button looks like, change the
   `colorScheme` color it points to, not the button.

## Colors — `colorScheme` (edit these)

| Key                    | Meaning                                             | Typical |
| ---------------------- | --------------------------------------------------- | ------- |
| `root`                 | Page/background color                               | `#ffffff` (light) / a dark color (dark) |
| `contrast`             | Main text color on `root`                           | `#000000` (light) / `#ffffff` (dark) |
| `primaryAccent`        | Brand color — primary buttons, links, emphasis      | the brand's signature color |
| `primaryAccentContrast`| Text/icon color that sits ON `primaryAccent`        | usually `#ffffff` or `#000000`, whichever reads on the accent |
| `neutral`              | Muted borders, secondary text, dividers             | a mid gray |

**Do NOT hand-author `primaryAccentDerived` or `primaryAccentContrastDerived`.**
The toolkit computes them from `primaryAccent`/`primaryAccentContrast` on load (a
darker hover shade + a WCAG-contrast-checked hover text color) and rewrites them.
The template intentionally OMITS them; leave them out. The `{!...Derived}`
references inside `buttonStyleGroup` still resolve correctly because the toolkit
fills the derived values in before resolving.

Contrast matters: `contrast` must be legible on `root`, and `primaryAccentContrast`
must be legible on `primaryAccent`. When in doubt, pick black or white for the
contrast colors — whichever has the higher contrast ratio against its background.

Use 6-digit `#rrggbb` hex. (The toolkit normalizes to 8-digit `#rrggbbaa`
internally; 6-digit in and out is fine.)

## Fonts — `fontFamily` + `baseFontFamily` (choose from the catalog)

`fontFamily` is a **catalog** of available fonts; `baseFontFamily` and every
`typography.*.fontFamily` is a **reference** into that catalog
(`"{!$brand.fontFamily.<key>}"`).

To change the brand's font, point `baseFontFamily` (and, if you want headings to
match, the `typography.heading.*.fontFamily` entries) at a different catalog key.
Prefer changing `baseFontFamily` and leaving the rest referencing it through the
scale.

**Preview fidelity — important.** The preview only renders web-safe system fonts
plus "Salesforce Sans". Any other font name falls back to its generic category
(sans-serif/serif/monospace), so the preview won't show it. Stick to these
catalog keys, which all render:

- Sans-serif: `arial`, `verdana`, `tahoma`, `trebuchetMs`, `calibri`,
  `lucidaSansUnicode`, `arialBlack`, `impact`
- Serif: `georgia`, `timesNewRoman`, `palatinoLinotype`
- Monospace: `courierNew`, `lucidaConsole`

If a brand truly needs a custom/brand font, keep it as an aspiration in the brand
name/description, but pick the closest system font from the list above for the
`fontFamily` value so the preview is honest. Don't add a new `fontFamily` entry
with a name that has no web source — it will silently fall back.

## Sizes, weights, spacing, borders

These are shared scales referenced by name throughout `typography` and
`buttonStyleGroup`. Sensible edits:

- `baseFontSize.value` — the root font size in px (default 16). Bump to 17–18 for
  a more spacious feel.
- `borderRadius.round.value` — corner rounding in rem. `0` = sharp/square,
  `0.25` = default, `0.5`+ = pill-ish.
- `borderWeight.thin.value` — default border thickness in rem.
- `fontWeight.normal` — 400 by default; some brands prefer 300 (lighter) or a
  heavier body.

Leave the `spacing`, `letterSpacing`, and `fontSize` scale keys in place — the
editors and preview reference them by name. Change the `.value` inside a scale
entry if you must, but don't remove or rename the entries.

## `typography` and `buttonStyleGroup` — mostly references, edit sparingly

`typography` maps each text role (heading1–6, paragraph1–2, button, input, label)
to a font family, size, weight, line-height, letter-spacing, and transform — all
as references into the scales above. `buttonStyleGroup` (primary/secondary/
tertiary) maps button colors to `colorScheme` references and picks border radius/
width/typography.

For most brands you should NOT touch these — they inherit correctly from the
colors and fonts you set above. Edit them only for a deliberate deviation (e.g.
uppercase buttons via `textTransform: "uppercase"` on `typography.button.button1`,
or a square primary button via a different `lightning:borderRadius` reference).
When you do, change the reference target or the literal in place — keep the key
structure identical to the template.

## The one field that defines identity: `sfdc_cms:title`

`sfdc_cms:title` is the brand's display name AND its identity in the toolkit's
local list. It **must be unique** among the project's local brands — two brands
with the same title collapse into one entry in the gallery. Give every generated
brand a distinct, human-readable title (e.g. `"Sunset Coral"`, `"Acme Dark"`).
See `references/disk-contract.md` for how the title maps to the on-disk filename.
