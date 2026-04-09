# Examples

Worked examples showing the SLDS authoring workflow: from intent to artifact selection.

Each example follows the 5-phase workflow from SKILL.md and shows which files were consulted and why.


## Example 1: Build a Confirmation Dialog

### Phase 1: Understand the Need

- **Pattern:** Confirmation dialog before a destructive action
- **Framework:** LWC
- **States:** Open, confirming (loading), closed

### Phase 2: Select the Artifact

**Check LBC:** `LightningModal` exists in the [Lightning Component Library](https://developer.salesforce.com/docs/component-library/overview/components). Use it.

**Also search blueprints** (for class reference):

```bash
node scripts/search-blueprints.cjs --search "modal"
# Found: Modals (category: Overlay, root: slds-modal)
```

**Read blueprint YAML** for class details: `metadata/blueprints/components/modals.yaml`

Key takeaway: `LightningModal` handles the `slds-modal`, `slds-backdrop`, and ARIA attributes automatically. No need to apply blueprint classes manually in LWC.

### Phase 3: Apply Styling

**Read:** `references/styling-decision-guide.md`

The destructive action button needs error color to signal danger:

```bash
node scripts/search-hooks.cjs --prefix "--slds-g-color-error-"
# Found: --slds-g-color-error-1 (#ea001e), --slds-g-color-on-error-1 (#ffffff)
```

**Result:** Use `variant="destructive"` on `lightning-button` inside the modal footer. The LBC handles the correct SLDS color hooks internally.

For the modal body spacing, use utility classes:

```html
<div class="slds-p-around_medium slds-text-align_center">
  <p>Are you sure you want to delete this record?</p>
</div>
```

### Phase 4: Add Icons

**Search:** `node scripts/search-icons.cjs --query "warning"`

```
Found: utility:warning (score: 100, match: exact)
```

```html
<lightning-icon
    icon-name="utility:warning"
    alternative-text="Warning"
    variant="error"
    size="small"
    class="slds-m-right_x-small">
</lightning-icon>
```

### Phase 5: Validate (checklists.md)

- No hardcoded colors (using LBC variants + hooks)
- Icon has `alternative-text`
- Spacing uses utility classes (`slds-p-around_medium`, `slds-m-right_x-small`)
- No `.slds-*` overrides

---

## Example 2: Styled Card with Status Badge (Non-LWC)

### Phase 1: Understand the Need

- **Pattern:** A card showing a record with a colored status badge
- **Framework:** React (not LWC -- no LBCs available)
- **States:** Active, inactive, pending

### Phase 2: Select the Artifact

**LBC check:** Not applicable (React).

**Search blueprints:**

```bash
node scripts/search-blueprints.cjs --search "card"
# Found: Cards (category: Layout, root: slds-card)

node scripts/search-blueprints.cjs --search "badge"
# Found: Badges (category: Feedback, root: slds-badge)
```

**Read YAMLs:**
- `metadata/blueprints/components/cards.yaml` -- classes: `slds-card`, `slds-card__header`, `slds-card__body`, `slds-card__footer`
- `metadata/blueprints/components/badges.yaml` -- classes: `slds-badge`, modifiers: `slds-badge_lightest`, `slds-badge_inverse`

### Phase 3: Apply Styling

**Read:** `references/styling-decision-guide.md`

Card background and text use surface hooks. The status is conveyed by badge text plus a custom status accent on the card, rather than invented badge modifiers.

```html
<article class="slds-card my-status-card">
  <div class="slds-card__header slds-grid">
    <header class="slds-media slds-media_center slds-has-flexi-truncate">
      <div class="slds-media__body">
        <h2 class="slds-card__header-title slds-truncate">Account Name</h2>
      </div>
      <div class="slds-no-flex">
        <span class="slds-badge slds-badge_lightest">Active</span>
      </div>
    </header>
  </div>
  <div class="slds-card__body slds-card__body_inner">
    <p>Record details here</p>
  </div>
</article>
```

Custom styling for a subtle card border:

```css
.my-status-card {
  border-left: 3px solid var(--slds-g-color-accent-1, #0176d3);
}
```

Note: custom class uses `my-*` prefix, hook with fallback, no `.slds-*` overrides.

### Phase 4: Add Icons

**Search for a standard object icon:**

```bash
node scripts/search-icons.cjs --query "account" --category "standard"
# Found: standard:account (score: 100, match: exact)
```

In React (non-LWC), use the SVG blueprint pattern:

```html
<span class="slds-icon_container slds-icon-standard-account" title="Account">
  <svg class="slds-icon slds-icon_small" aria-hidden="true">
    <use xlinkHref="/assets/icons/standard-sprite/svg/symbols.svg#account"></use>
  </svg>
  <span class="slds-assistive-text">Account</span>
</span>
```

### Phase 5: Validate

- Card uses exact blueprint classes (`slds-card`, `slds-card__header`, etc.)
- Badge uses a real blueprint modifier (`slds-badge_lightest`), not an invented status variant
- Custom border uses `my-*` prefix and hook with fallback
- Icon uses `slds-assistive-text` for accessibility
- No hardcoded colors

---

## Example 3: Responsive Data Layout with Hooks

### Phase 1: Understand the Need

- **Pattern:** A responsive grid of metric cards
- **Framework:** LWC
- **States:** Loading (spinner), populated, empty (illustration)

### Phase 2: Select the Artifact

**LBC:** `lightning-card` for each metric card. `lightning-spinner` for loading.

**Search for empty state:**

```bash
node scripts/search-blueprints.cjs --search "illustration"
# Found: Illustration (category: Media, root: slds-illustration)
```

### Phase 3: Apply Styling

**Verify grid and spacing utilities** before using them:

```bash
node scripts/search-utilities.cjs --search "slds-grid"
# Found: slds-grid (category: grid, css: display: flex)

node scripts/search-utilities.cjs --search "slds-text-heading_large"
# Found: slds-text-heading_large (category: typography)

node scripts/search-utilities.cjs --search "slds-text-body_small"
# Found: slds-text-body_small (category: typography)
```

**Grid layout** uses utility classes (see `references/utilities-quick-ref.md`):

```html
<div class="slds-grid slds-wrap slds-gutters">
  <template for:each={metrics} for:item="metric">
    <div key={metric.id} class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
      <lightning-card title={metric.label}>
        <div class="slds-p-horizontal_small">
          <p class="slds-text-heading_large">{metric.value}</p>
          <p class="slds-text-body_small slds-text-color_weak">{metric.subtitle}</p>
        </div>
      </lightning-card>
    </div>
  </template>
</div>
```

**Custom metric styling** with hooks:

```css
.my-metric-value {
  font-size: var(--slds-g-font-scale-6, 2rem);
  font-weight: var(--slds-g-font-weight-7, 700);
  color: var(--slds-g-color-on-surface-3, #181818);
}

.my-metric-trend-up {
  color: var(--slds-g-color-success-1, #2e844a);
}

.my-metric-trend-down {
  color: var(--slds-g-color-error-1, #ea001e);
}
```

Note: trend colors use semantic feedback hooks (success/error), not hardcoded green/red.

**Empty state** uses the SLDS illustration blueprint:

```html
<template if:false={hasData}>
  <div class="slds-illustration slds-illustration_small">
    <img src="/img/chatter/Desert.svg" class="slds-illustration__svg" alt="" />
    <div class="slds-text-longform">
      <h3 class="slds-text-heading_medium">No metrics available</h3>
      <p class="slds-text-body_regular">Check back when data is loaded.</p>
    </div>
  </div>
</template>
```

### Phase 4: Add Icons

Trend indicators need icons:

```bash
node scripts/search-icons.cjs --query "arrow up"
# Found: utility:arrowup (score: 100)

node scripts/search-icons.cjs --query "arrow down"
# Found: utility:arrowdown (score: 100)
```

```html
<lightning-icon
    icon-name={metric.trendIcon}
    alternative-text={metric.trendLabel}
    size="xx-small"
    class="slds-m-left_xx-small">
</lightning-icon>
```

### Phase 5: Validate

- Grid uses `slds-grid` + `slds-col` + responsive `slds-*-size_*` classes
- Spacing uses utilities (`slds-p-horizontal_small`, `slds-m-left_xx-small`)
- Typography uses utilities (`slds-text-heading_large`, `slds-text-body_small`)
- Custom CSS uses `my-*` prefix and hooks with fallbacks
- Trend colors use semantic hooks (success/error), not hardcoded values
- Empty state uses SLDS illustration blueprint
- Icons have `alternative-text`
