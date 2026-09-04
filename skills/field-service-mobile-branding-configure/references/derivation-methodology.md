# Derivation Methodology

How to translate a brand source (URL, hex codes, brand-guide paste, or color description) into the 14-field scheme defined in [color-fields.md](color-fields.md).

## Step 1 — Ingest the brand source

**Case A — URL provided**

1. Fetch the URL with `WebFetch`.
2. Extract color references: hex codes (`#RRGGBB`, `#RGB`), RGB values, named colors.
3. Identify the primary brand color (most prominent — used in headers, hero areas, primary CTAs).
4. Identify the secondary/interactive color (buttons, links, interactive elements).
5. Note any neutrals/grays from the brand palette.

**Case B — Brand guide text / paste provided**

1. Parse for hex codes and named colors.
2. Identify primary, secondary, neutral, and semantic (error/success) colors.
3. Note any explicit usage rules ("primary is for CTAs", "never use X on Y").

**Case C — Hex codes provided directly**

1. Accept as-is.
2. If only one color provided, ask: "Is this your primary brand color? Do you have a secondary/interactive color?"
3. Proceed to Step 2 with those anchors.

**Case D — Description only (e.g. "we're a red and white company")**

1. Ask for at least one specific hex code or a website URL.
2. Do not guess exact brand colors from descriptions alone.

## Step 2 — Identify brand anchors

From the brand source, establish two anchors. Everything else derives from them:

- **Primary brand color** — the dominant brand color, for non-interactive surfaces and the navbar.
- **Secondary/interactive color** — the color for buttons and interactive elements.

If the brand specifies separate navbar and CTA colors, use the navbar color for `NavbarBackgroundColor` and `PrimaryBrandColor`, and the CTA color for `SecondaryBrandColor`.

## Step 3 — Derive the full scheme

### Brand & Navigation

- `NavbarBackgroundColor` = primary brand anchor.
- `PrimaryBrandColor` = primary brand anchor (same as navbar — both represent the non-interactive brand surface).
- `NavbarInvertedColor` = derive from navbar luminance:
  - Dark navbar (luminance < 0.35): `#FFFFFF`
  - Light navbar (luminance ≥ 0.35): `#000000` or darkest brand neutral
- `SecondaryBrandColor` = secondary/interactive anchor from brand.
- `BrandInvertedColor` = same logic as `NavbarInvertedColor` applied to `PrimaryBrandColor` (usually `#FFFFFF`).

### Contrast Scale

Use brand neutrals if provided, otherwise use Salesforce defaults:

- `ContrastPrimaryColor` = darkest neutral, or `#000000`.
- `ContrastSecondaryColor` = dark gray, or `#444444`.
- `ContrastTertiaryColor` = medium-light gray (icons, lines), or `#9FAAB5`.
- `ContrastQuaternaryColor` = light gray (dividers, graphics), or `#E6E6EB`.
- `ContrastQuinaryColor` = very light gray (card surrounds), or `#EEEEEE`.
- `ContrastInvertedColor` = card backgrounds — almost always `#FFFFFF`.

If the brand guide specifies a neutral/gray scale, map those values to the 5 contrast steps in order from darkest to lightest.

### Feedback Colors

Use brand-specified semantic colors if available, otherwise use Salesforce defaults:

- `FeedbackPrimaryColor` = brand's error red, or `#C23934`.
- `FeedbackSecondaryColor` = brand's success color, or `#13C4A3`.
- `FeedbackSelectedColor` = `#FFFFFF` (text/icon on selected state — almost always white).

## Edge cases

- **No secondary color in brand guide** — use a 20% lighter or darker variant of the primary.
- **Monochrome brand** — use `#000000` primary, `#555555` secondary, standard contrast scale.
- **Very light primary (pastel)** — flag in the proposal: light navbar will fail contrast. Suggest using a darker brand neutral for the navbar instead.
- **Multiple `FieldServiceMobileSettings` records** — the apply targets the org-default record (`DeveloperName='Field_Service_Mobile_Settings'`, `IsDefault=true`). If the org has multiple records, query first and confirm which to update.

## Output

The scheme is a flat JSON object matching the schema in [color-fields.md](color-fields.md). Hold it in memory, validate contrast inline (SKILL.md step 4), then apply it with a single sObject PATCH after user approval (SKILL.md step 6).
