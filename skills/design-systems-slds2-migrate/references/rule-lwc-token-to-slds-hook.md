# Rule: LWC Token to SLDS Hook

**Rule ID:** `slds/lwc-token-to-slds-hook`
**Severity:** Error
**Scope:** Replaces deprecated `--lwc-*` design tokens with SLDS 2 styling hooks.

---

## What the Linter Does

The linter detects deprecated `--lwc-*` tokens and reports them as **errors**. When there is only one suggestion, `--fix` auto-applies it. When there are multiple suggestions, manual selection is required. Here's real linter output for a multiple-suggestion case:

```
  2:14  error  The '--lwc-colorBackground' design token is deprecated. Replace it with
               the SLDS 2 styling hook and set the fallback to '--lwc-colorBackground'.
               1. --slds-g-color-surface-2
               2. --slds-g-color-surface-container-2                    slds/lwc-token-to-slds-hook

✖ 1 SLDS Violation (1 error, 0 warnings)
```

---

## CRITICAL: Two-Step Workflow

### Step 1: Read Linter Suggestions First (Mandatory)

Before doing anything else, extract the numbered suggestions from the linter output.

**ABSOLUTE RULE: You can ONLY use hooks from the linter's numbered list. You CANNOT use any other hooks.**

- If linter suggests `1. --slds-g-color-surface-2` and `2. --slds-g-color-surface-container-2`
- You can ONLY choose between those two
- Using `--slds-g-color-surface-1` is FORBIDDEN (not in the list)

### Step 2: Apply Context-Based Decision (Only After Step 1)

Now that you have the linter's suggestions, use context to choose the best option FROM THE LIST.

---

## Decision Process

### Single Suggestion

If the linter gives ONE option, `--fix` auto-applies it. The result looks like:

```css
color: var(--slds-g-color-on-surface-2, var(--lwc-colorTextDefault));
```

### Multiple Suggestions

If the linter gives MULTIPLE options, apply pattern matching to choose.

**Surface vs Container — Core Concept:**

**SURFACE** = The overlay itself — the element that creates a new stacking context (pages, modals, popovers, dialogs)
- The modal/popover/dialog body background (e.g., `.slds-modal`, `.slds-popover`)
- Main component backgrounds like `.main-body`, `.page-wrapper`, `.THIS`

**CONTAINER** = Elements that sit on top of a surface (cards, tiles, headers, footers, list items)
- Parts within an overlay like `.slds-modal__header`, `.slds-modal__footer`
- Card components like `.card-header`, `.card-footer`, `.tile-body`
- Repeating items like `.list-item`, `.table-row`

### Pattern Matching

When the linter gives surface vs container options:

**Choose SURFACE when:**
- `.slds-modal`, `.slds-popover`, `.slds-dialog` — the overlay itself (creates new stacking context)
- `main-*`, `*-body`, `*-page`, `*-root`, `*-wrapper`, `*-background` — primary/root elements
- `.THIS` — component root

**Choose CONTAINER when:**
- `.slds-modal__*`, `.slds-popover__*`, `.slds-dialog__*` — parts within an overlay (header, footer, content)
- `*-card-*`, `*-tile-*`, `*-item*`, `*-row*` — nested elements within surfaces
- Sections/panels nested within a card, tile, or item

### Step-by-Step Decision Process

1. **READ LINTER SUGGESTIONS** — Extract the numbered list of hooks
2. **IDENTIFY CLASS NAME** — Look at the CSS selector being styled
3. **PATTERN MATCH** — Check surface patterns first, then container patterns
4. **SELECT FROM LINTER OPTIONS** — Choose the corresponding option
5. **NEVER INVENT HOOKS** — Only use hooks explicitly listed by the linter

For deeper context investigation (class usage in HTML/JS, component structure), see [color-hooks-decision-guide.md](color-hooks-decision-guide.md).

---

## Replacement Pattern

Always include the original LWC token as fallback:

```css
property: var(--slds-g-[hook], var(--lwc-[originalToken]));
```

The nested `var()` fallback ensures compatibility during migration.

---

## Mandatory Rules

**Rule 1: ONLY USE LINTER-SUGGESTED HOOKS**
- Read the linter output first
- Only use hooks that appear in the linter's numbered list
- Cannot invent or use hooks not suggested by the linter

**Rule 2: USE PATTERN RECOGNITION TO CHOOSE FROM LINTER OPTIONS**
- One option → use that exact option
- Multiple options → apply pattern matching:
  - Surface: `.slds-modal`, `.slds-popover`, `.slds-dialog`, `main-*`, `*-body`, `*-page`, `*-root`, `.THIS`
  - Container: `.slds-modal__*`, `.slds-popover__*`, `.slds-dialog__*`, `*-card-*`, `*-tile-*`, `*-item*`, `*-row*`
- Apply patterns generically — don't memorize specific examples

**Rule 3: ALWAYS INCLUDE FALLBACK**
- Format: `var(--slds-g-[hook], var(--lwc-[originalToken]))`

**Rule 4: MINIMAL CHANGES**
- Only fix actual `slds/lwc-token-to-slds-hook` violations
- Do not remove any other code or styles
- Reference line numbers for all modifications
- If no violations found, return empty list

---

## Validation Checklist

- [ ] All `var(--lwc-*)` tokens have SLDS 2 replacements
- [ ] Replacements are from the linter's suggested list (not invented)
- [ ] Original token included as fallback: `var(--slds-g-*, var(--lwc-*))`
- [ ] Context-appropriate choice when multiple options given
