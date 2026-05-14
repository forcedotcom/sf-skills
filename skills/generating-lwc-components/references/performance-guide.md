<!-- Parent: generating-lwc-components/SKILL.md -->
# Performance Optimization Guide for LWC

Comprehensive guide to optimizing Lightning Web Component performance, including dark mode implementation, lazy loading, and rendering optimization.

---

## Table of Contents

1. [Dark Mode Implementation](#dark-mode-implementation)
2. [Rendering Performance](#rendering-performance)
3. [Lazy Loading](#lazy-loading)
4. [Data Management](#data-management)
5. [Event Optimization](#event-optimization)
6. [Memory Management](#memory-management)
7. [Bundle Size Optimization](#bundle-size-optimization)
8. [Performance Testing](#performance-testing)
9. [Common Anti-Patterns](#common-anti-patterns)

---

## Dark Mode Implementation

Dark mode is exclusive to SLDS 2 themes. Components must use global styling hooks to support light/dark theme switching.

### Complete SLDS 2 Color Token Reference

#### Surface Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-surface-1` | `#FFFFFF` | `#0B0B0B` | Primary surface (body background) |
| `--slds-g-color-surface-2` | `#F3F3F3` | `#181818` | Secondary surface |
| `--slds-g-color-surface-3` | `#E5E5E5` | `#2B2B2B` | Tertiary surface |
| `--slds-g-color-surface-4` | `#C9C9C9` | `#3E3E3E` | Quaternary surface |

#### Container Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-surface-container-1` | `#FAFAFA` | `#1A1A1A` | Card backgrounds, panels |
| `--slds-g-color-surface-container-2` | `#F7F7F7` | `#232323` | Nested containers |
| `--slds-g-color-surface-container-3` | `#F3F3F3` | `#2E2E2E` | Deep nesting |

#### Text Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-on-surface` | `#181818` | `#FAFAFA` | Primary text |
| `--slds-g-color-on-surface-1` | `#444444` | `#C9C9C9` | Secondary text |
| `--slds-g-color-on-surface-2` | `#706E6B` | `#A0A0A0` | Muted/disabled text |
| `--slds-g-color-on-surface-inverse` | `#FFFFFF` | `#181818` | Inverse text (buttons, badges) |

#### Border Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-border-1` | `#C9C9C9` | `#444444` | Primary borders |
| `--slds-g-color-border-2` | `#E5E5E5` | `#3E3E3E` | Secondary borders (dividers) |

#### Brand Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-brand-1` | `#0176D3` | `#1B96FF` | Primary brand (buttons, links) |
| `--slds-g-color-brand-2` | `#014486` | `#0B5CAB` | Brand hover/active states |

#### Status Colors

| Token | Light Mode | Dark Mode | Purpose |
|-------|------------|-----------|---------|
| `--slds-g-color-success-1` | `#2E844A` | `#45C65A` | Success states |
| `--slds-g-color-error-1` | `#EA001E` | `#FE5C4C` | Error states |
| `--slds-g-color-warning-1` | `#FFB75D` | `#FFB75D` | Warning states |
| `--slds-g-color-info-1` | `#0176D3` | `#1B96FF` | Info states |

#### Spacing Tokens

| Token | Value (rem) | Value (px) |
|-------|-------------|------------|
| `--slds-g-spacing-0` | 0 | 0 |
| `--slds-g-spacing-1` | 0.125 | 2 |
| `--slds-g-spacing-2` | 0.25 | 4 |
| `--slds-g-spacing-3` | 0.5 | 8 |
| `--slds-g-spacing-4` | 0.75 | 12 |
| `--slds-g-spacing-5` | 1 | 16 |
| `--slds-g-spacing-6` | 1.5 | 24 |
| `--slds-g-spacing-7` | 2 | 32 |
| `--slds-g-spacing-8` | 3 | 48 |

### Migration Examples

#### Before: SLDS 1 (Hardcoded Colors)

```css
/* accountCard.css - SLDS 1 (Deprecated) */
.card {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #dddddd;
    border-radius: 4px;
    padding: 16px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
    color: #000000;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
}

.card-text {
    color: #666666;
    font-size: 14px;
}

.card-link {
    color: #0176d3;
}

.card-link:hover {
    color: #014486;
    text-decoration: underline;
}
```

#### After: SLDS 2 (Dark Mode Ready)

```css
/* accountCard.css - SLDS 2 */
.card {
    background-color: var(--slds-g-color-surface-container-1, #ffffff);
    color: var(--slds-g-color-on-surface, #181818);
    border: 1px solid var(--slds-g-color-border-2, #e5e5e5);
    border-radius: var(--slds-g-radius-border-2, 0.25rem);
    padding: var(--slds-g-spacing-5, 1rem);
    box-shadow: 0 2px 4px var(--slds-g-color-border-1, rgba(0, 0, 0, 0.1));
}

.card-header {
    color: var(--slds-g-color-on-surface, #181818);
    font-size: var(--slds-g-font-size-5, 1rem);
    font-weight: var(--slds-g-font-weight-bold, 700);
    margin-bottom: var(--slds-g-spacing-3, 0.5rem);
}

.card-text {
    color: var(--slds-g-color-on-surface-1, #444444);
    font-size: var(--slds-g-font-size-3, 0.875rem);
}

.card-link {
    color: var(--slds-g-color-brand-1, #0176d3);
}

.card-link:hover {
    color: var(--slds-g-color-brand-2, #014486);
    text-decoration: underline;
}
```

### Component-Level Example

```javascript
// darkModeCard.js
import { LightningElement } from 'lwc';

export default class DarkModeCard extends LightningElement {
    // No JavaScript changes needed for dark mode!
    // All theming is handled via CSS variables
}
```

```html
<!-- darkModeCard.html -->
<template>
    <div class="card">
        <div class="card-header">
            <h2 class="card-title">Account Details</h2>
        </div>
        <div class="card-body">
            <p class="card-text">This card automatically adapts to light/dark mode</p>
            <a href="#" class="card-link">Learn more</a>
        </div>
    </div>
</template>
```

```css
/* darkModeCard.css */
.card {
    background-color: var(--slds-g-color-surface-container-1, #ffffff);
    border: 1px solid var(--slds-g-color-border-2, #e5e5e5);
    border-radius: var(--slds-g-radius-border-2, 0.25rem);
    padding: var(--slds-g-spacing-5, 1rem);
}

.card-header {
    border-bottom: 1px solid var(--slds-g-color-border-2, #e5e5e5);
    margin-bottom: var(--slds-g-spacing-4, 0.75rem);
    padding-bottom: var(--slds-g-spacing-3, 0.5rem);
}

.card-title {
    color: var(--slds-g-color-on-surface, #181818);
    font-size: var(--slds-g-font-size-5, 1rem);
    font-weight: var(--slds-g-font-weight-bold, 700);
    margin: 0;
}

.card-body {
    color: var(--slds-g-color-on-surface-1, #444444);
}

.card-text {
    margin-bottom: var(--slds-g-spacing-4, 0.75rem);
}

.card-link {
    color: var(--slds-g-color-brand-1, #0176d3);
    text-decoration: none;
}

.card-link:hover {
    color: var(--slds-g-color-brand-2, #014486);
    text-decoration: underline;
}
```

### Validation Script

```bash
# Check for hardcoded colors in CSS
grep -r "#[0-9A-Fa-f]\{3,6\}" force-app/main/default/lwc/ --include="*.css"

# Check for rgb/rgba values
grep -r "rgb\|rgba" force-app/main/default/lwc/ --include="*.css"

# Install SLDS Linter
npm install -g @salesforce-ux/slds-linter

# Run validation
slds-linter lint force-app/main/default/lwc/
```

---

## Rendering Performance

### Conditional Rendering

```javascript
// BAD: Re-renders entire list
<template for:each={allItems} for:item="item">
    <div if:true={item.visible} key={item.id}>
        {item.name}
    </div>
</template>

// GOOD: Filter before rendering
get visibleItems() {
    return this.allItems.filter(item => item.visible);
}

<template for:each={visibleItems} for:item="item">
    <div key={item.id}>{item.name}</div>
</template>
```

### Use `lwc:if` for Large Blocks

```html
<!-- lwc:if removes from DOM (better for large blocks) -->
<template lwc:if={showDashboard}>
    <c-dashboard data={dashboardData}></c-dashboard>
</template>

<!-- if:true hides with CSS (better for frequent toggling) -->
<div if:true={showMessage} class="message">
    {message}
</div>
```

### Key Directive for Lists

```html
<!-- CRITICAL: Use unique, stable keys -->
<template for:each={accounts} for:item="account">
    <div key={account.Id}>  <!-- Use record ID, not index -->
        {account.Name}
    </div>
</template>
```

### Getter Caching

```javascript
// BAD: Recalculates on every render
get formattedValue() {
    return this.expensiveCalculation(this.data);
}

// GOOD: Cache the result
@track _cachedValue;
_cacheKey;

get formattedValue() {
    const currentKey = JSON.stringify(this.data);
    if (this._cacheKey !== currentKey) {
        this._cacheKey = currentKey;
        this._cachedValue = this.expensiveCalculation(this.data);
    }
    return this._cachedValue;
}
```

### Avoid renderedCallback Loops

```javascript
// BAD: Infinite loop
renderedCallback() {
    this.count++; // Triggers re-render
}

// GOOD: Guard against loops
renderedCallback() {
    if (!this._rendered) {
        this._rendered = true;
        this.initializeChart();
    }
}
```

---

## Lazy Loading

### Dynamic Imports

```javascript
// accountManager.js
export default class AccountManager extends LightningElement {
    @track showCharts = false;
    chartModule;

    async handleShowCharts() {
        if (!this.chartModule) {
            // Lazy load chart component
            this.chartModule = await import('c/accountChart');
        }
        this.showCharts = true;
    }
}
```

### Intersection Observer for Lazy Loading

```javascript
// lazyImageLoader.js
export default class LazyImageLoader extends LightningElement {
    @api src;
    @api alt;

    isVisible = false;
    observer;

    renderedCallback() {
        if (!this.observer) {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.isVisible = true;
                        this.observer.disconnect();
                    }
                });
            }, { rootMargin: '50px' });

            const img = this.template.querySelector('img');
            if (img) {
                this.observer.observe(img);
            }
        }
    }

    get imageSrc() {
        return this.isVisible ? this.src : 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
    }

    disconnectedCallback() {
        if (this.observer) {
            this.observer.disconnect();
        }
    }
}
```

```html
<!-- lazyImageLoader.html -->
<template>
    <img src={imageSrc} alt={alt} loading="lazy">
</template>
```

### Virtual Scrolling

```javascript
// virtualList.js
export default class VirtualList extends LightningElement {
    @api items = [];
    @track visibleItems = [];

    itemHeight = 50;
    containerHeight = 500;
    scrollTop = 0;

    get visibleCount() {
        return Math.ceil(this.containerHeight / this.itemHeight);
    }

    get startIndex() {
        return Math.floor(this.scrollTop / this.itemHeight);
    }

    get endIndex() {
        return Math.min(
            this.startIndex + this.visibleCount + 1,
            this.items.length
        );
    }

    get paddingTop() {
        return this.startIndex * this.itemHeight;
    }

    get paddingBottom() {
        return (this.items.length - this.endIndex) * this.itemHeight;
    }

    connectedCallback() {
        this.updateVisibleItems();
    }

    handleScroll(event) {
        this.scrollTop = event.target.scrollTop;
        this.updateVisibleItems();
    }

    updateVisibleItems() {
        this.visibleItems = this.items.slice(
            this.startIndex,
            this.endIndex
        );
    }
}
```

```html
<!-- virtualList.html -->
<template>
    <div class="container"
         style={containerStyle}
         onscroll={handleScroll}>
        <div style={paddingTopStyle}></div>
        <template for:each={visibleItems} for:item="item">
            <div key={item.id} class="item">
                {item.name}
            </div>
        </template>
        <div style={paddingBottomStyle}></div>
    </div>
</template>
```

---

## Data Management

### Debouncing

```javascript
// searchComponent.js
export default class SearchComponent extends LightningElement {
    searchTerm = '';
    delayTimeout;

    handleSearchChange(event) {
        const searchTerm = event.target.value;

        // Clear previous timeout
        clearTimeout(this.delayTimeout);

        // Set new timeout (300ms debounce)
        this.delayTimeout = setTimeout(() => {
            this.performSearch(searchTerm);
        }, 300);
    }

    async performSearch(term) {
        try {
            const results = await searchAccounts({ searchTerm: term });
            this.results = results;
        } catch (error) {
            this.handleError(error);
        }
    }

    disconnectedCallback() {
        clearTimeout(this.delayTimeout);
    }
}
```

### Throttling

```javascript
// scrollTracker.js
export default class ScrollTracker extends LightningElement {
    lastScrollTime = 0;
    throttleDelay = 100;

    handleScroll(event) {
        const now = Date.now();

        if (now - this.lastScrollTime >= this.throttleDelay) {
            this.lastScrollTime = now;
            this.processScroll(event);
        }
    }

    processScroll(event) {
        // Handle scroll logic
        console.log('Scroll position:', event.target.scrollTop);
    }
}
```

### Caching Wire Results

```javascript
// accountList.js
export default class AccountList extends LightningElement {
    @api recordId;
    wiredAccountsResult;

    @wire(getAccounts, { accountId: '$recordId' })
    wiredAccounts(result) {
        this.wiredAccountsResult = result; // Cache for refreshApex
        if (result.data) {
            this.accounts = result.data;
        } else if (result.error) {
            this.error = result.error;
        }
    }

    async handleRefresh() {
        // Refresh cached wire result
        await refreshApex(this.wiredAccountsResult);
    }
}
```

---

## Event Optimization

### Event Delegation

```javascript
// BAD: Multiple event listeners
<template for:each={items} for:item="item">
    <button key={item.id} onclick={handleClick} data-id={item.id}>
        {item.name}
    </button>
</template>

// GOOD: Single delegated listener
<div onclick={handleContainerClick}>
    <template for:each={items} for:item="item">
        <button key={item.id} data-id={item.id}>
            {item.name}
        </button>
    </template>
</div>

handleContainerClick(event) {
    if (event.target.tagName === 'BUTTON') {
        const itemId = event.target.dataset.id;
        this.processClick(itemId);
    }
}
```

### Prevent Event Bubbling

```javascript
handleClick(event) {
    event.stopPropagation(); // Stop bubbling
    event.preventDefault();   // Prevent default action

    // Process event
}
```

---

## Memory Management

### Cleanup in disconnectedCallback

```javascript
export default class ResourceManager extends LightningElement {
    subscription;
    intervalId;
    observer;

    connectedCallback() {
        // Subscribe to events
        this.subscription = subscribe(
            this.messageContext,
            CHANNEL,
            this.handleMessage
        );

        // Set interval
        this.intervalId = setInterval(() => {
            this.updateData();
        }, 5000);

        // Create observer
        this.observer = new IntersectionObserver(
            this.handleIntersection
        );
    }

    disconnectedCallback() {
        // CRITICAL: Clean up all resources
        if (this.subscription) {
            unsubscribe(this.subscription);
            this.subscription = null;
        }

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
    }
}
```

### Remove Event Listeners

```javascript
export default class EventManager extends LightningElement {
    boundHandler;

    connectedCallback() {
        this.boundHandler = this.handleResize.bind(this);
        window.addEventListener('resize', this.boundHandler);
    }

    disconnectedCallback() {
        window.removeEventListener('resize', this.boundHandler);
    }

    handleResize() {
        // Handle resize
    }
}
```

---

## Bundle Size Optimization

### Code Splitting

```javascript
// Import only what you need
import { getRecord } from 'lightning/uiRecordApi';
import NAME_FIELD from '@salesforce/schema/Account.Name';

// Don't import entire modules
// BAD: import * as uiRecordApi from 'lightning/uiRecordApi';
```

### Minimize Dependencies

```javascript
// BAD: Import heavy library for simple task
import moment from 'moment';

get formattedDate() {
    return moment(this.date).format('MM/DD/YYYY');
}

// GOOD: Use native APIs
get formattedDate() {
    return new Intl.DateTimeFormat('en-US').format(new Date(this.date));
}
```

---

## Performance Testing

### Chrome DevTools Performance Tab

```javascript
// Add performance marks
export default class PerformanceTracked extends LightningElement {
    connectedCallback() {
        performance.mark('component-start');
        this.initializeComponent();
        performance.mark('component-end');
        performance.measure(
            'component-initialization',
            'component-start',
            'component-end'
        );

        const measure = performance.getEntriesByName('component-initialization')[0];
        console.log('Initialization took:', measure.duration, 'ms');
    }
}
```

### Lighthouse Audit

```bash
lighthouse https://your-org.lightning.force.com --only-categories=performance
```

### Custom Performance Metrics

```javascript
export default class MetricsTracker extends LightningElement {
    connectedCallback() {
        // Track time to interactive
        const startTime = performance.now();

        this.loadData().then(() => {
            const endTime = performance.now();
            console.log('Time to interactive:', endTime - startTime, 'ms');
        });
    }
}
```

---

<a id="common-anti-patterns"></a>

## Common Anti-Patterns

### 1. Excessive Wire Calls

```javascript
// BAD: Multiple wire calls for related data
@wire(getAccount, { accountId: '$recordId' }) account;
@wire(getContacts, { accountId: '$recordId' }) contacts;
@wire(getOpportunities, { accountId: '$recordId' }) opportunities;

// GOOD: Single wire call with joined data
@wire(getAccountWithRelated, { accountId: '$recordId' })
wiredData({ data, error }) {
    if (data) {
        this.account = data.account;
        this.contacts = data.contacts;
        this.opportunities = data.opportunities;
    }
}
```

### 2. Updating Tracked Properties in Getters

```javascript
// BAD: Side effects in getter
@track count = 0;

get message() {
    this.count++; // Causes infinite re-render!
    return `Count: ${this.count}`;
}

// GOOD: Pure getter
get message() {
    return `Count: ${this.count}`;
}
```

### 3. Not Using @track Wisely

```javascript
// BAD: Over-using @track
@track simpleValue = 'hello';
@track anotherValue = 42;

// GOOD: Only track complex objects
simpleValue = 'hello'; // Primitives don't need @track
@track complexObject = { nested: { value: 42 } };
```

### 4. Heavy Operations in renderedCallback

```javascript
// BAD: Heavy calculation every render
renderedCallback() {
    this.calculateComplexMetrics(); // Expensive!
}

// GOOD: Calculate only when data changes
@track _dataVersion = 0;
_renderedVersion = -1;

renderedCallback() {
    if (this._renderedVersion !== this._dataVersion) {
        this._renderedVersion = this._dataVersion;
        this.calculateComplexMetrics();
    }
}

handleDataChange() {
    this._dataVersion++;
}
```

---

## Performance Checklist

- [ ] Use SLDS 2 color tokens (dark mode ready)
- [ ] Lazy load components with dynamic imports
- [ ] Implement virtual scrolling for long lists (100+ items)
- [ ] Debounce search inputs (300ms)
- [ ] Throttle scroll/resize handlers (100ms)
- [ ] Cache expensive getter calculations
- [ ] Use `lwc:if` for large conditional blocks
- [ ] Provide stable keys in `for:each` loops
- [ ] Clean up resources in `disconnectedCallback()`
- [ ] Avoid heavy operations in `renderedCallback()`
- [ ] Use event delegation for list items
- [ ] Minimize wire service calls
- [ ] Remove unused imports
- [ ] Test with Chrome DevTools Performance tab
- [ ] Run Lighthouse performance audit

---

## Related Resources

- [component-patterns.md](component-patterns.md) - Implementation patterns
- [accessibility-guide.md](accessibility-guide.md) - A11y compliance
- [jest-testing.md](jest-testing.md) - Testing strategies
- [SLDS 2 Transition Guide](https://www.lightningdesignsystem.com/2e1ef8501/p/8184ad-transition-to-slds-2)
- [LWC Developer Guide](https://developer.salesforce.com/docs/platform/lwc/guide)
