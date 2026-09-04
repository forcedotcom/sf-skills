# Contrast Validation

The Field Service mobile app supports both light and dark mode. The `FieldServiceMobileSettings` color fields apply to **light mode**. Dark mode inverts the contrast scale automatically — but brand and feedback colors remain fixed. A scheme that passes in light mode can fail in dark mode if the brand colors clash with dark backgrounds.

The agent computes contrast ratios for the pairs below inline (the formulas are at the bottom of this file) and reports pass/fail against WCAG AA (`4.5:1` for normal text). Surface any failures to the user before applying.

## Light mode pairs

| Pair | Foreground | Background |
|---|---|---|
| Navbar text on navbar bg | `NavbarInvertedColor` | `NavbarBackgroundColor` |
| Toast/FAB text on brand bg | `BrandInvertedColor` | `PrimaryBrandColor` |
| Selected indicator on interactive | `FeedbackSelectedColor` | `SecondaryBrandColor` |
| Primary text on card bg | `ContrastPrimaryColor` | `ContrastInvertedColor` |
| Secondary text on card bg | `ContrastSecondaryColor` | `ContrastInvertedColor` |

## Dark mode pairs

In dark mode, the app inverts the contrast scale: card backgrounds become dark (`ContrastPrimaryColor`), and text becomes light (`ContrastInvertedColor`). Brand and feedback colors do **not** change.

| Pair | Effective foreground | Effective background |
|---|---|---|
| Primary text on dark card bg | `ContrastInvertedColor` | `ContrastPrimaryColor` |
| Secondary brand (interactive) on dark bg | `SecondaryBrandColor` | `ContrastPrimaryColor` |
| Feedback error on dark bg | `FeedbackPrimaryColor` | `ContrastPrimaryColor` |
| Feedback success on dark bg | `FeedbackSecondaryColor` | `ContrastPrimaryColor` |
| Navbar (unchanged in dark mode) | `NavbarInvertedColor` | `NavbarBackgroundColor` |

## Dark mode risk factors to flag

- A **very light secondary brand color** (e.g. pastel yellow, light teal) may wash out against a dark-mode card bg — check `SecondaryBrandColor` on `ContrastPrimaryColor`.
- A **light primary brand color** (e.g. CAT yellow `#FFCD11`) will have reduced contrast against light backgrounds when used as a label color in dark mode. Flag if luminance > 0.4.
- **Feedback colors** — standard red and teal/green are generally safe in dark mode. Verify if the brand specifies non-standard semantic colors.

## Luminance & contrast formulas

For `#RRGGBB`:

1. Normalize: `r = R/255, g = G/255, b = B/255`
2. Linearize each channel: if `c ≤ 0.03928 → c/12.92`, else `((c+0.055)/1.055)^2.4`
3. Relative luminance: `L = 0.2126·r + 0.7152·g + 0.0722·b`
4. Contrast ratio: `(L_lighter + 0.05) / (L_darker + 0.05)`

WCAG AA threshold for normal text: **4.5:1**.

## Common fixes for failures

| Failure | Suggested fix |
|---|---|
| Navbar pair fails (light navbar) | Use a darker brand neutral for `NavbarBackgroundColor` |
| `FeedbackSelectedColor` on `SecondaryBrandColor` fails (light interactive) | Use `#1C1C1C` or darkest brand neutral for `FeedbackSelectedColor` |
| `BrandInvertedColor` on `PrimaryBrandColor` fails (light primary) | Switch `BrandInvertedColor` to `#000000` or darkest neutral |
| `SecondaryBrandColor` on `ContrastPrimaryColor` fails in dark mode | Pick a darker variant of the interactive color, or accept reduced contrast and note it in the proposal |

Each suggested fix should specify which mode (light, dark, or both) it affects, so the user can weigh tradeoffs before applying.