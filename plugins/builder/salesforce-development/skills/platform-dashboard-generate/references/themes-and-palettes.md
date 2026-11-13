# Themes, Palettes and Colours

## Dashboard level (write both members of each pair, with the same value)

```xml
<chartTheme>light</chartTheme>                   <!-- light | dark -->
<colorPalette>unity</colorPalette>
<dashboardChartTheme>light</dashboardChartTheme>
<dashboardColorPalette>unity</dashboardColorPalette>
```

- The editor writes both the current (`chartTheme`, `colorPalette`) and legacy (`dashboardChartTheme`,
  `dashboardColorPalette`) elements. **When the palettes differ, the legacy `dashboardColorPalette` is
  the one that renders.** Always set them identically.
- Palettes (enum, case-sensitive): `unity` (editor default), `accessible`, `colorSafe`, `branding`,
  `bluegrass`, `dusk`, `earth`, `fire`, `gray`, `heat`, `justice`, `nightfall`, `pond`, `sunrise`,
  `tropic`, `water`, `watermelon`, `Default`.
- `branding` uses the org's brand palette from Setup → Themes and Branding (greys when none is set).
- UI palette names do not always match the enum (there is no `mineral` value — "Error parsing file:
  'mineral' is not a valid value for the enum 'ChartColorPalettes'"). For accessibility choose
  `accessible` or `colorSafe`.
- `chartTheme` `dark` darkens every widget's background.

## Widget level

`<componentChartTheme>dark</componentChartTheme>` overrides the dashboard theme for one widget (the
builder's "Widget theme"). Omit to inherit.

## Required colours

`backgroundStartColor`, `backgroundEndColor` (normally both `#FFFFFF`), `backgroundFadeDirection`
(`Diagonal` | `TopToBottom` | `LeftToRight`), `textColor` (`#000000`), `titleColor` (`#000000`).
Hex `#RRGGBB` only: "Invalid color format 'black' in textColor".

## Metric / gauge / table colours

- Metric and gauge `indicatorLowColor` / `indicatorMiddleColor` / `indicatorHighColor`: hex strings.
- Lightning table highlighting `lowRangeColor` / `midRangeColor` / `highRangeColor`: **decimal integers**
  (`int("C23934", 16)` = `12728628`).
- SLDS defaults: red `#C23934`, amber `#FFB75D`, green `#00716B`.
