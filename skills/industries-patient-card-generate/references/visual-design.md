## 10. Visual design

Match these values exactly. In the tables, each value is written as "hook (value)", for example "spacing-5 (1.5rem)". **Use only the value in parentheses, as a plain CSS value** (`padding: 1.5rem`). Don't write `var(--slds-g-...)`: the org's theme overrides global hooks, so the card would look different from org to org. The hook name only says which SLDS design token the value comes from.

The component-level hooks written out in full (`--slds-c-icon-color-foreground-default` and `--slds-c-button-text-color`) are the exception. Set them as shown, with the fixed value, because they're the supported way to color `lightning-icon` and `lightning-button`.

Where the same token appears with different values in different rows, use each row's value: the rows describe the design, not the token.

### 10.1 Card

| Element | Values |
| --- | --- |
| Card (`<article>`) | padding spacing-5 (1.5rem); radius radius-border-4 (1.25rem); background color-surface-container-1 (#ffffff); shadow shadow-1 (0 2px 2px 0 rgba(0, 0, 0, 0.1)) |
| Divider between the header and the plan section | on the plan section host: `display: block`; margin-top and padding-top spacing-5 (1.5rem); border-top 1px solid color-border-1 (#e5e5e5) |

### 10.2 Header

| Element | Values |
| --- | --- |
| Header host | `display: block; position: relative; min-height: 3rem` (room for the spinner) |
| Layout | flex row; gap spacing-4 (1rem); `align-items: flex-start`. Avatar on the left, text column on the right (`min-width: 0`). |
| Avatar ring | 4.5rem × 4.5rem; padding 0.25rem; border 1px solid color-brand-base-90 (#d8e6fe); circle; `flex-shrink: 0` |
| Initials | fills the ring; circle; background color-brand-base-95 (#eef4ff); text color-brand-base-50 (#0176d3); font-scale-4 (1.5rem); weight 700; centered |
| Role | color-brand-base-50 (#0176d3); font-scale-neg-1 (0.875rem); weight 700 |
| Name (`<h2>`) | color-brand-base-10 (#001639); font-scale-6 (1.75rem); weight 800; line-height 1.2; `overflow-wrap: anywhere` |
| Demographics and contact lines | color-on-surface-1 (#5c5c5c); font-scale-1 (1rem); line-height 1.5; `overflow-wrap: anywhere`. One line per contact value; no icons and no visible labels. |

### 10.3 Member plan section

| Element | Values |
| --- | --- |
| Section host | `display: block; position: relative; min-height: 3rem` |
| Plan header | flex row; gap spacing-3 (0.75rem); `align-items: center`; `position: relative` (anchors the list) |
| Icon chip | 2.5rem × 2.5rem; radius radius-border-3 (0.5rem); background color-brand-base-95 (#eef4ff); holds `utility:shield` at `size="x-small"`, colored with `--slds-c-icon-color-foreground-default: #444444` |
| Text column | `flex: 1; min-width: 0`. Three lines: label, plan name, subtitle. |
| "Member Plan" label and subtitle | color-on-surface-1 (#5c5c5c); font-scale-neg-1 (0.875rem) |
| Plan name | color-on-surface-3 (#181818); font-scale-2 (1.25rem); weight 700; `overflow-wrap: anywhere` |
| Picker toggle | 1.75rem × 1.75rem circle; padding 0; border 1px solid color-on-surface-2 (#2e2e2e); background color-surface-container-1 (#ffffff); `utility:down` at `size="xx-small"`, colored with `--slds-c-icon-color-foreground-default: #0b5cab`; at the far right (`flex-shrink: 0`) |
| Focus ring (toggle) | outline 2px solid color-brand-base-50 (#0176d3); offset 2px |
| Plan list | absolute; top `calc(100% + spacing-2)`; left 0 and right 0 (full header width); z-index 10; border 1px solid color-border-1 (#e5e5e5); radius radius-border-3 (0.75rem); background color-surface-container-1; shadow shadow-2 (0 2px 8px rgba(0, 0, 0, 0.16)); `overflow: hidden`; no list bullets |
| Plan option | full-width button; column layout; padding spacing-3 (0.75rem); no border; transparent background; `text-align: start` |
| Option hover, focus or selected | background color-brand-base-95 (#eef4ff); focus outline 2px solid color-brand-base-50, offset -2px |
| Option name and subtitle | name color-on-surface-3, weight 600; subtitle color-on-surface-1, font-scale-neg-1 (0.875rem) |
| Content below the plan header | flex column; gap spacing-4 (1rem); margin-top spacing-4 (1rem). It holds the pills, then the plan details. |

### 10.4 Pills

| Element | Values |
| --- | --- |
| Pills host | flex column; gap spacing-2 (0.5rem) between the two rows |
| Row (`<ul>`) | flex, wrapping; gap spacing-2 (0.5rem); no bullets |
| Pill | inline-flex, centered; gap spacing-1 (0.25rem); padding spacing-1 spacing-3 (0.25rem 0.75rem); border 1px solid; radius radius-border-pill (15rem); font-scale-neg-1 (0.75rem); weight 600 |
| Dot | 0.375rem circle; background `currentColor` |
| Danger | text color-error-base-30 (#8e030f); background color-error-base-95 (#fef1ee); border color-error-base-90 (#feded8) |
| Success | text color-success-base-30 (#22683e); background color-success-base-95 (#ebf7e6); border color-success-base-90 (#cdefc4) |
| Neutral | text color-neutral-base-30 (#444444); background color-neutral-base-95 (#f3f3f3); border color-neutral-base-80 (#c9c9c9) |

### 10.5 Info row, toggle and tile grid

| Element | Values |
| --- | --- |
| Info row (`<dl>`) | flex row, no wrapping, left-aligned (items don't stretch) |
| Info item | flex column, value above label (`column-reverse` with the `dt` first in the DOM); `flex: 0 1 auto; min-width: 0`; padding-inline spacing-3 (0.75rem) at the start and spacing-5 (1.5rem) at the end; border-inline-start 1px solid color-border-1 (#e5e5e5). The first item has no start padding and no border. |
| Info label | color-on-surface-1 (#5c5c5c); font-scale-neg-1 (0.875rem) |
| Info value | color-on-surface-3 (#181818); font-scale-1 (1rem); weight 700 |
| Show More / Show Less | wrapper: margin-top spacing-4 (1rem); padding-top spacing-2 (0.5rem); border-top 1px solid color-border-1; `text-align: center`. A `lightning-button variant="base"` without an icon, with text color `--slds-c-button-text-color: #5c5c5c` and hover color `--slds-c-button-text-color-hover: #2e2e2e`. |
| Tile grid | CSS grid with `repeat(2, minmax(0, 1fr))`; gap spacing-3 (0.75rem); margin-top spacing-2 (0.5rem) |

### 10.6 Tile

| Element | Values |
| --- | --- |
| Tile (`<article>`) | flex column; gap spacing-1 (0.25rem); `height: 100%`; padding spacing-3 (0.75rem); border 1px solid color-border-1 (#e5e5e5); radius radius-border-4 (0.75rem); background color-surface-container-1 (#ffffff) |
| Tile header | flex row; gap spacing-2 (0.5rem); `align-items: flex-start`; margin-bottom spacing-2 (0.5rem) |
| Icon chip | 1.75rem × 1.75rem; radius radius-border-2 (0.5rem); background color-brand-base-95 (#eef4ff); the icon at `size="x-small"`, colored with `--slds-c-icon-color-foreground-default: #5c5c5c` |
| Icon chip, warning | background color-warning-base-95 (#fbf3e0) |
| Title (`<h3>`) | color-on-surface-1 (#5c5c5c); font-scale-neg-1 (0.875rem); weight 600; vertically centered with the chip |
| Value | color-on-surface-3 (#2e2e2e); font-scale-3 (1.25rem); weight 700; line-height 1.25 |
| Value, warning | color-warning-base-50 (#dd7a01) |
| Subtitle and empty text | color-on-surface-1 (#747474); font-scale-neg-1 (0.8125rem) |

### 10.7 General

- Reset the default margins on `p`, `h2`, `h3`, `dl`, `dd` and `ul` (SLDS already does this on Lightning pages). Don't add margins other than the ones listed above.
- Spinners: `lightning-spinner size="small"` with the "Loading" alternative text, inside the host that's loading.
- Wrap long values instead of truncating them; never use ellipsis.
- Don't use `lightning-card`, `lightning-avatar`, `lightning-pill` or `lightning-badge`. Their built-in styles don't match this design. Build the card, avatar, pills and tiles from plain elements.

---
