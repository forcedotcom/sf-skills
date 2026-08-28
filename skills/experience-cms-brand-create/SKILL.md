---
name: experience-cms-brand-create
description: "Author a Salesforce Digital Experience brand (a \"brand.json\") so the VS Code Brand Toolkit can load, edit, and preview it. Use this skill whenever someone wants to: create a brand, make a new brand, generate a brand from a description or a color/logo/mood, add a brand to a project so the Brand Toolkit picks it up, scaffold a brand.json, theme a Digital Experience site, or turn a brand idea (\"a dark luxury brand\", \"match our logo\", \"coral + rounded + friendly\") into a loadable brand. Also use it when the user mentions \"Brand Toolkit\", \"theme manager brand\", \"brand token\", \"colorScheme\", \"primaryAccent\", \".digitalExperience/brands\", \"sfdc_cms:title\", or a \"brand.json\" that should show up in the Brand Toolkit. Do NOT use this skill to apply an existing brand's voice, tone, or guidelines to generated content (use experience-cms-brand-apply), to search Salesforce CMS for existing brands, or to search for images, media, or logos (use experience-content-media-search)."
metadata:
  version: "1.0"
  domains: ["Experience"]
  relatedSkills:
    - "experience-cms-brand-apply"
    - "experience-content-media-search"
---

# Create a Brand for the Brand Toolkit

Generates a Digital Experience **brand** — one `brand.json` file — from a user's
description, and writes it where the VS Code **Brand Toolkit** will discover it,
so the user can immediately load, edit, and preview the brand.

A brand is a single JSON object of design tokens: colors (`colorScheme`), a font
catalog and base font (`fontFamily` / `baseFontFamily`), size/spacing/border
scales, per-role `typography`, and `buttonStyleGroup` definitions. Most of it is
fixed structure with internal references; **you create a brand by starting from a
known-good template and changing only the leaf values** (colors, font choice,
border radius, base size) plus a unique name.

The Brand Toolkit owns everything downstream: it computes derived hover colors,
compiles the `--tm-*` CSS, and manages the active-brand config on Save. Your job
is just the `brand.json`.

> **Related:** This skill *creates* a new brand definition. To *apply* an existing
> brand's voice, tone, and guidelines to generated content, use the
> `experience-cms-brand-apply` skill instead.

## Reference material

Read each reference when its step arrives — don't inline everything up front:

- **`assets/brand-template.json`** — the known-good full brand to clone. This
  is your starting point for EVERY brand. Copy it, then change leaves.
- **`references/brand-anatomy.md`** — which fields are literals you should edit vs
  references you must leave intact; the `colorScheme` guide; the font catalog and
  which fonts actually render in the preview; the derived-colors rule. Read before
  editing values.
- **`references/disk-contract.md`** — exactly where the file goes
  (`.digitalExperience/brands/<slug>.brand.json`), the title→slug rule, and what
  the toolkit generates so you don't. Read before writing the file.

## Interactive flow

Walk these steps in order. When you have an interactive user, ask before assuming
and confirm the design back before writing; in a single-turn, headless, or CLI run
with no user to answer, state the choices you inferred and write in the same run
rather than waiting for a confirmation that cannot arrive (see Step 3). Steps 1–5
create the brand file and complete the task. After they finish, an optional
post-completion action — opening the Brand Toolkit to preview/edit — is described
in **"After completion"** below; it is not part of the required workflow.

### Step 1: Gather the brand intent

Find out what the brand should feel like. If the user already gave a description
("a dark, premium fintech brand in deep purple"), extract from it; otherwise ask
briefly for:

- **Name** — a short, human-readable brand name (becomes `sfdc_cms:title`, must be
  unique in the project). If they don't offer one, propose one from the vibe.
- **Primary/brand color** — the signature accent. Accept a hex, a named color, or
  a description ("Salesforce blue", "warm coral"). Convert to a `#rrggbb` hex.
- **Light or dark** — does the page background read light or dark? This sets
  `root` and `contrast`.
- **Personality** (optional) — corners (sharp vs rounded), font feel (clean sans,
  classic serif, techy mono), density. Map these to `borderRadius`, `fontFamily`
  choice, and `baseFontSize`.

If a logo or image is provided, sample its dominant color for `primaryAccent` and
judge light/dark from its background. Keep it to a couple of questions — infer the
rest from the vibe and confirm in Step 3.

### Step 2: Build the brand from the template

1. Read `assets/brand-template.json` — this is your base. Read
   `references/brand-anatomy.md` so you know which leaves are safe to change.
2. Copy the template and override ONLY leaf values:
   - `sfdc_cms:title` → the unique brand name.
   - `colorScheme.root` / `contrast` → per light or dark (e.g. light: `#ffffff` /
     `#000000`; dark: a dark bg / `#ffffff`).
   - `colorScheme.primaryAccent` → the brand color.
   - `colorScheme.primaryAccentContrast` → black or white, whichever is legible on
     the accent.
   - `colorScheme.neutral` → a mid gray that reads on `root`.
   - `baseFontFamily` (and, to match, the `typography.heading.*.fontFamily`
     entries) → a reference to a catalog key whose font actually renders in the
     preview (see the anatomy doc's font list).
   - Optional personality: `borderRadius.round.value`, `borderWeight.thin.value`,
     `baseFontSize.value`, `fontWeight.normal`.
3. Do NOT: add `*Derived` color keys, drop or rename any section/key, replace a
   `{!$brand....}` reference with a literal, or use a font name outside the
   renderable catalog. The structure must stay identical to the template.
4. Sanity-check contrast: `contrast` on `root`, and `primaryAccentContrast` on
   `primaryAccent`, must be legible. Prefer black/white for the contrast colors.

### Step 3: Confirm the design (or, if headless, state it and proceed)

Assemble a compact summary of the concrete choices — name, the four or five hex
colors (with a note on light/dark), the font, and any corner/size/weight tweaks.
Then branch on whether a user can actually answer:

- **Interactive run (a user can reply):** show the summary and ask the user to
  confirm or adjust. Iterate here rather than after the file is on disk.
- **Single-turn / headless / CLI / CI run (no user to confirm):** do **not** pause
  for a confirmation that cannot arrive. State the choices you inferred and proceed
  straight to Step 4, writing the file in the same run.

When you can't tell which mode you're in, prefer stating your choices and
proceeding over stalling — a written brand the user can adjust beats a hang.

### Step 4: Write the brand file

Follow `references/disk-contract.md`:

1. Derive `<slug>` from the confirmed title using the exact slug rule in that doc.
2. Ensure `<workspaceRoot>/.digitalExperience/brands/` exists.
3. If `<slug>.brand.json` already exists and this is a NEW brand, append the
   lowest free numeric suffix (`_2`, `_3`, …).
4. Write the brand object (unwrapped body, 2-space pretty-printed) to
   `<workspaceRoot>/.digitalExperience/brands/<slug>.brand.json`.
5. Do NOT write the `.css` or `activeBrand.json` — the toolkit generates those on
   Save.

### Step 5: Validate the file

Run the verification checklist in `references/disk-contract.md` (valid JSON;
unwrapped body; present + unique `sfdc_cms:title`; slug matches title; no
hand-authored `*Derived` keys; fonts renderable).

## After completion (optional): Open the Brand Toolkit to preview and edit

The numbered workflow above is complete once Step 5 passes — the brand file is the
deliverable and stands on its own. This section is a **separate, optional action,
not a workflow step**, and only applies inside VS Code. Opening the Brand Toolkit
is just a convenience for previewing/editing. **Skip it entirely** (the brand is
already done — just tell the user where the file was written) when any of these
hold:

- The user isn't working in VS Code, or asked for the brand file only / "just
  create it" / "don't open anything" / a headless, scripted, or CI context.
- There's no `.digitalExperience` project / VS Code workspace around the file
  (e.g. you wrote to a standalone folder outside a Salesforce DX project).
- You can't tell you're in an interactive VS Code session (e.g. a plain CLI or
  agent run with no desktop) — **don't** fire the launcher speculatively; a
  `vscode://` deep link can otherwise cold-start or error out. When unsure, ask
  the user whether to open the Brand Toolkit rather than assuming.

Only when the user is in VS Code and wants to preview/edit, open the **Brand
Toolkit** (Theme Preview) panel by running the terminal command that matches the
user's operating system. All three open the SAME deep link — only the OS launcher
differs; run exactly one (the one for the current OS):

- macOS:
  `open "vscode://salesforce.salesforcedx-vscode-ui-preview/open-brand-manager"`
- Linux:
  `xdg-open "vscode://salesforce.salesforcedx-vscode-ui-preview/open-brand-manager"`
- Windows (PowerShell):
  `Start-Process "vscode://salesforce.salesforcedx-vscode-ui-preview/open-brand-manager"`

VS Code routes the link to the Live Preview (ui-preview) extension, which opens
the Brand Toolkit panel. Then tell the user:

> The Brand Toolkit is open in VS Code. Your new brand "<title>" is in the
> **Local** tab — select it to preview and fine-tune it; the toolkit computes the
> hover colors and compiles the CSS, and **Save** persists your tweaks.

If the panel was already open, the new brand may need a refresh in the Local tab
to appear. If nothing opens, the deep link requires the Live Preview extension
(`salesforce.salesforcedx-vscode-ui-preview`) to be installed and active — fall
back to telling the user to run **SFDX: Open Theme Preview** from the Command
Palette.

## Guardrails

- **Clone the template; don't write a brand from scratch.** A hand-built brand
  almost always drops a key the editors/compiler/preview expect, and the failure
  is silent (wrong-looking preview, no error).
- **Edit literals, keep references.** Changing a `colorScheme` color re-themes
  every button/accent that references it — that's the point. Replacing a reference
  with a literal breaks that link.
- **Never author derived colors.** `primaryAccentDerived` /
  `primaryAccentContrastDerived` are computed by the toolkit on load. Omit them.
- **Only use fonts that render in the preview** (system fonts + "Salesforce
  Sans"). Any other name silently falls back, so the preview misleads.
- **`sfdc_cms:title` must be unique.** Duplicate titles collapse into one entry in
  the toolkit's local list.
- **One file only.** Write `<slug>.brand.json`; let the toolkit produce the `.css`
  and `activeBrand.json`.
- **The brand file is the deliverable; opening the toolkit is optional.** Steps
  1–5 fully complete the task. Only run the Brand Toolkit launcher (see "After
  completion" above) inside VS Code when the user wants to preview/edit — never
  fire a `vscode://` deep link in a headless, CLI, CI, or non-project context. When
  in doubt, skip it and tell the user where the file is.
