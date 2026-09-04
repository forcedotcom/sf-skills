# Color Fields

The `FieldServiceMobileSettings` sObject has **14 color fields**, all hex strings (`#RRGGBB`). The org-default record has `IsDefault = true` and `DeveloperName = 'Field_Service_Mobile_Settings'`. There is one default record per org.

Color values are **light-mode** values. Dark mode inverts the contrast scale automatically — see [contrast-validation.md](contrast-validation.md).

## Brand & Navigation

| Field | Description | Salesforce default |
|---|---|---|
| `NavbarBackgroundColor` | The color of the top bar in the app | `#803ABE` |
| `NavbarInvertedColor` | The secondary color of the top bar in the app | `#FFFFFF` |
| `PrimaryBrandColor` | The color of **non-interactive** areas in the app | `#803ABE` |
| `SecondaryBrandColor` | The color of **interactive** areas in the app | `#2A7AB0` |
| `BrandInvertedColor` | The color of toasts and the contrast color for the floating action button | `#FFFFFF` |

## Contrast Scale

| Field | Description | Salesforce default |
|---|---|---|
| `ContrastPrimaryColor` | The color of primary text | `#000000` |
| `ContrastSecondaryColor` | The color of secondary text | `#444444` |
| `ContrastTertiaryColor` | The color of icons on the settings screen and primary lines delineating UI areas | `#9FAAB5` |
| `ContrastQuaternaryColor` | The color of some graphics and secondary lines delineating UI areas | `#E6E6EB` |
| `ContrastQuinaryColor` | The color of the background behind cards in the UI | `#EEEEEE` |
| `ContrastInvertedColor` | The color of card backgrounds in the UI | `#FFFFFF` |

## Feedback / Status Colors

| Field | Description | Salesforce default |
|---|---|---|
| `FeedbackPrimaryColor` | The color of error messages | `#C23934` |
| `FeedbackSecondaryColor` | The color of success messages or progress icons | `#13C4A3` |
| `FeedbackSelectedColor` | The color indicating the user's current selection | `#FFFFFF` |

## Key distinctions

- `PrimaryBrandColor` = non-interactive colored areas (schedule icon dot, section labels, decorative elements).
- `SecondaryBrandColor` = interactive elements (buttons, links, GET DIRECTIONS, floating action button background).
- `NavbarBackgroundColor` and `PrimaryBrandColor` are typically the same color.
- `ContrastInvertedColor` = card backgrounds (usually white), not just inverted text.

## JSON spec shape

The skill consumes a flat JSON object whose keys match the 14 field names exactly:

```json
{
  "NavbarBackgroundColor": "#0070D2",
  "NavbarInvertedColor": "#FFFFFF",
  "PrimaryBrandColor": "#0070D2",
  "SecondaryBrandColor": "#1589EE",
  "BrandInvertedColor": "#FFFFFF",
  "ContrastPrimaryColor": "#000000",
  "ContrastSecondaryColor": "#444444",
  "ContrastTertiaryColor": "#9FAAB5",
  "ContrastQuaternaryColor": "#E6E6EB",
  "ContrastQuinaryColor": "#EEEEEE",
  "ContrastInvertedColor": "#FFFFFF",
  "FeedbackPrimaryColor": "#C23934",
  "FeedbackSecondaryColor": "#13C4A3",
  "FeedbackSelectedColor": "#FFFFFF"
}
```

Hex must be 6 digits with the `#` prefix. 3-digit shorthand and missing `#` are invalid — the agent rejects them during the step-3 self-check before proposing or applying.