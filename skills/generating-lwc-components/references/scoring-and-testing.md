<!-- Parent: generating-lwc-components/SKILL.md -->

# SLDS 2 Validation (165-Point Scoring) & Jest Testing

## SLDS 2 Scoring Categories

| Category | Points | Key Checks |
|----------|--------|------------|
| **SLDS Class Usage** | 25 | Valid class names, proper `slds-*` utilities |
| **Accessibility** | 25 | ARIA labels, roles, alt-text, keyboard navigation |
| **Dark Mode Readiness** | 25 | No hardcoded colors, CSS variables only |
| **SLDS Migration** | 20 | No deprecated SLDS 1 patterns/tokens |
| **Styling Hooks** | 20 | Proper `--slds-g-*` variable usage |
| **Component Structure** | 15 | Uses `lightning-*` base components |
| **Performance** | 10 | Efficient selectors, no `!important` |
| **PICKLES Compliance** | 25 | Architecture methodology adherence (optional) |

**Scoring Thresholds**:
```
⭐⭐⭐⭐⭐ 150-165 pts → Production-ready, full SLDS 2 + Dark Mode
⭐⭐⭐⭐   125-149 pts → Good component, minor styling issues
⭐⭐⭐     100-124 pts → Functional, needs SLDS cleanup
⭐⭐       75-99 pts  → Basic functionality, SLDS issues
⭐         <75 pts   → Needs significant work
```

---

## Dark Mode Readiness

Dark mode is exclusive to SLDS 2 themes. Components must use global styling hooks to support light/dark theme switching.

### Dark Mode Checklist

- [ ] **No hardcoded hex colors** (`#FFFFFF`, `#333333`)
- [ ] **No hardcoded RGB/RGBA values**
- [ ] **All colors use CSS variables** (`var(--slds-g-color-*)`)
- [ ] **Fallback values provided** for SLDS 1 compatibility
- [ ] **No inline color styles** in HTML templates
- [ ] **Icons use SLDS utility icons** (auto-adjust for dark mode)

### Global Styling Hooks (Common)

| Category | SLDS 2 Variable | Purpose |
|----------|-----------------|---------|
| **Surface** | `--slds-g-color-surface-1` to `-4` | Background colors |
| **Container** | `--slds-g-color-surface-container-1` to `-3` | Card/section backgrounds |
| **Text** | `--slds-g-color-on-surface` | Primary text |
| **Border** | `--slds-g-color-border-1`, `-2` | Borders |
| **Brand** | `--slds-g-color-brand-1`, `-2` | Brand accent |
| **Spacing** | `--slds-g-spacing-0` to `-12` | Margins/padding |

**Example Migration**:
```css
/* SLDS 1 (Deprecated) */
.my-card { background-color: #ffffff; color: #333333; }

/* SLDS 2 (Dark Mode Ready) */
.my-card {
    background-color: var(--slds-g-color-surface-container-1, #ffffff);
    color: var(--slds-g-color-on-surface, #181818);
}
```

---

## Jest Testing Patterns

### Essential Patterns

```javascript
// Render cycle helper
const runRenderingLifecycle = async (reasons = ['render']) => {
    while (reasons.length > 0) {
        await Promise.resolve(reasons.pop());
    }
};

// DOM cleanup
afterEach(() => {
    while (document.body.firstChild) {
        document.body.removeChild(document.body.firstChild);
    }
    jest.clearAllMocks();
});

// Proxy unboxing (LWS compatibility)
const unboxedData = JSON.parse(JSON.stringify(component.data));
expect(unboxedData).toEqual(expectedData);
```

### Test Template Structure

```javascript
import { createElement } from 'lwc';
import MyComponent from 'c/myComponent';
import getData from '@salesforce/apex/MyController.getData';

jest.mock('@salesforce/apex/MyController.getData', () => ({
    default: jest.fn()
}), { virtual: true });

describe('c-my-component', () => {
    afterEach(() => { /* DOM cleanup */ });

    it('displays data when loaded successfully', async () => {
        getData.mockResolvedValue(MOCK_DATA);
        const element = createElement('c-my-component', { is: MyComponent });
        document.body.appendChild(element);
        await runRenderingLifecycle();
        // Assertions...
    });
});
```

**For complete testing patterns (ResizeObserver polyfill, advanced mocks, event testing), see [references/jest-testing.md](../references/jest-testing.md)**
