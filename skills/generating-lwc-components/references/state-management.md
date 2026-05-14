<!-- Parent: generating-lwc-components/SKILL.md -->
<!-- TIER: 3 | DETAILED REFERENCE -->
<!-- Read after: SKILL.md -->
<!-- Purpose: Modern state management patterns using @lwc/state -->

# LWC State Management

> Modern state management patterns for Lightning Web Components using @lwc/state and Platform State Managers

## Overview

LWC state management has evolved beyond simple reactive properties. This guide covers modern patterns for managing complex state across components, including the `@lwc/state` library and Salesforce Platform State Managers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATE MANAGEMENT SPECTRUM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SIMPLE ◄────────────────────────────────────────────────────────► COMPLEX │
│                                                                             │
│  @track/@api      Singleton Store      @lwc/state       Platform State     │
│  (Component)      (Cross-Component)    (Full Library)   (Record/Layout)    │
│                                                                             │
│  ┌─────────┐      ┌─────────────┐      ┌────────────┐   ┌───────────────┐  │
│  │ Single  │      │ Shared      │      │ Atoms +    │   │ Record Data + │  │
│  │ Component│      │ Across      │      │ Computed + │   │ Layout State │  │
│  │ State   │      │ Components  │      │ Actions    │   │ (Platform)   │  │
│  └─────────┘      └─────────────┘      └────────────┘   └───────────────┘  │
│                                                                             │
│  Use when:         Use when:            Use when:        Use when:          │
│  - Local state     - Shared cart        - Complex UI     - Record pages     │
│  - Form fields     - User prefs         - Async state    - Flexipages       │
│  - UI toggles      - Cached data        - Derived data   - Tab persistence  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## When to Use Each Pattern

| Pattern | Complexity | Scope | Use Case |
|---------|------------|-------|----------|
| **@track / reactive properties** | Low | Component | Form inputs, toggles, local UI state |
| **Singleton Store** | Medium | Cross-component | Shopping cart, filters, user preferences |
| **@lwc/state** | Medium-High | Cross-component | Complex forms, async state, computed values |
| **Platform State Managers** | High | Page/Record | Record pages, layout-aware components |

---

## Pattern 1: Reactive Properties (Component-Level)

### Standard Reactivity

```javascript
import { LightningElement } from 'lwc';

export default class SimpleState extends LightningElement {
    // Reactive by default (primitive types and objects)
    counter = 0;
    isActive = false;
    user = { name: 'John', email: 'john@example.com' };

    // Object reassignment triggers reactivity
    updateUser() {
        // ✅ Works - new object reference
        this.user = { ...this.user, name: 'Jane' };

        // ❌ Won't trigger rerender - same reference
        // this.user.name = 'Jane';
    }

    increment() {
        this.counter++; // ✅ Primitive assignment is reactive
    }
}
```

### Getters (Computed Properties)

```javascript
export default class ComputedExample extends LightningElement {
    firstName = '';
    lastName = '';
    items = [];

    // Computed property - recalculates when dependencies change
    get fullName() {
        return `${this.firstName} ${this.lastName}`.trim();
    }

    get hasItems() {
        return this.items.length > 0;
    }

    get totalPrice() {
        return this.items.reduce((sum, item) => sum + item.price, 0);
    }

    get formattedPrice() {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(this.totalPrice);
    }
}
```

---

## Pattern 2: Singleton Store (Cross-Component State)

For sharing state across components without platform dependencies.

### Store Module (`store.js`)

```javascript
/**
 * Singleton store for cross-component state management.
 *
 * Usage:
 * import store from 'c/store';
 *
 * // Read state
 * const cart = store.getState('cart');
 *
 * // Update state
 * store.setState('cart', { items: [...cart.items, newItem] });
 *
 * // Subscribe to changes
 * store.subscribe('cart', (newCart) => { this.cart = newCart; });
 */

// Private state container
const state = new Map();

// Subscribers by key
const subscribers = new Map();

// Get current state for a key
function getState(key) {
    return state.get(key);
}

// Set state and notify subscribers
function setState(key, value) {
    const oldValue = state.get(key);
    state.set(key, value);

    // Notify all subscribers for this key
    const keySubscribers = subscribers.get(key) || [];
    keySubscribers.forEach(callback => {
        try {
            callback(value, oldValue);
        } catch (e) {
            console.error('Store subscriber error:', e);
        }
    });
}

// Subscribe to state changes
function subscribe(key, callback) {
    if (!subscribers.has(key)) {
        subscribers.set(key, []);
    }
    subscribers.get(key).push(callback);

    // Return unsubscribe function
    return () => {
        const keySubscribers = subscribers.get(key) || [];
        const index = keySubscribers.indexOf(callback);
        if (index > -1) {
            keySubscribers.splice(index, 1);
        }
    };
}

// Initialize state with default values
function initState(key, defaultValue) {
    if (!state.has(key)) {
        state.set(key, defaultValue);
    }
    return state.get(key);
}

// Clear state (useful for testing)
function clearState() {
    state.clear();
    subscribers.clear();
}

export default {
    getState,
    setState,
    subscribe,
    initState,
    clearState
};
```

### Using the Store

```javascript
// cartManager.js
import { LightningElement } from 'lwc';
import store from 'c/store';

export default class CartManager extends LightningElement {
    cart = { items: [], total: 0 };
    unsubscribe;

    connectedCallback() {
        // Initialize cart state
        this.cart = store.initState('cart', { items: [], total: 0 });

        // Subscribe to cart changes from other components
        this.unsubscribe = store.subscribe('cart', (newCart) => {
            this.cart = newCart;
        });
    }

    disconnectedCallback() {
        // Clean up subscription
        if (this.unsubscribe) {
            this.unsubscribe();
        }
    }

    addItem(event) {
        const item = event.detail;
        const currentCart = store.getState('cart');

        const newCart = {
            items: [...currentCart.items, item],
            total: currentCart.total + item.price
        };

        store.setState('cart', newCart);
    }
}
```

---

## Pattern 3: @lwc/state Library

The `@lwc/state` library provides reactive state primitives with automatic dependency tracking.

### Installation

```bash
# If using npm in LWC project
npm install @lwc/state
```

### Core Concepts

#### Atoms (Primitive State)

```javascript
import { atom, computed } from '@lwc/state';

// Create atoms for primitive state
const countAtom = atom(0);
const nameAtom = atom('');
const itemsAtom = atom([]);

// Read value
console.log(countAtom.value); // 0

// Write value - triggers reactivity
countAtom.value = 5;

// Reset to initial value
countAtom.reset();
```

#### Computed (Derived State)

```javascript
import { atom, computed } from '@lwc/state';

const priceAtom = atom(100);
const quantityAtom = atom(2);
const taxRateAtom = atom(0.08);

// Computed automatically recalculates when dependencies change
const subtotal = computed(() => priceAtom.value * quantityAtom.value);
const tax = computed(() => subtotal.value * taxRateAtom.value);
const total = computed(() => subtotal.value + tax.value);

console.log(total.value); // 216 (100 * 2 * 1.08)

// Update a dependency - all computed values update
priceAtom.value = 150;
console.log(total.value); // 324 (150 * 2 * 1.08)
```

#### Actions (State Mutations)

```javascript
import { atom, action } from '@lwc/state';

const cartAtom = atom({ items: [], total: 0 });

// Actions encapsulate state mutations
const addToCart = action((item) => {
    const cart = cartAtom.value;
    cartAtom.value = {
        items: [...cart.items, item],
        total: cart.total + item.price
    };
});

const removeFromCart = action((itemId) => {
    const cart = cartAtom.value;
    const item = cart.items.find(i => i.id === itemId);
    cartAtom.value = {
        items: cart.items.filter(i => i.id !== itemId),
        total: cart.total - (item?.price || 0)
    };
});

const clearCart = action(() => {
    cartAtom.reset();
});
```

### LWC Integration

```javascript
import { LightningElement } from 'lwc';
import { atom, computed } from '@lwc/state';

// Define atoms outside component (singleton)
const searchTermAtom = atom('');
const resultsAtom = atom([]);
const isLoadingAtom = atom(false);

// Computed values
const hasResults = computed(() => resultsAtom.value.length > 0);
const resultCount = computed(() => resultsAtom.value.length);

export default class SearchComponent extends LightningElement {
    // Bind atoms to component for reactivity
    get searchTerm() {
        return searchTermAtom.value;
    }

    get results() {
        return resultsAtom.value;
    }

    get isLoading() {
        return isLoadingAtom.value;
    }

    get hasResults() {
        return hasResults.value;
    }

    handleSearchChange(event) {
        searchTermAtom.value = event.target.value;
        this.performSearch();
    }

    async performSearch() {
        if (searchTermAtom.value.length < 2) {
            resultsAtom.value = [];
            return;
        }

        isLoadingAtom.value = true;
        try {
            const results = await searchRecords({ term: searchTermAtom.value });
            resultsAtom.value = results;
        } finally {
            isLoadingAtom.value = false;
        }
    }
}
```

---

## Pattern 4: Platform State Managers

Salesforce provides built-in state managers for record pages and layouts.

### stateManagerRecord

Manages record data with automatic refresh and caching.

```javascript
import { LightningElement, wire } from 'lwc';
import { stateManagerRecord } from 'lightning/stateManagerRecord';
import { getRecord } from 'lightning/uiRecordApi';

export default class RecordStateExample extends LightningElement {
    @api recordId;

    // Wire with state manager for enhanced caching
    @wire(stateManagerRecord, {
        recordId: '$recordId',
        fields: ['Account.Name', 'Account.Industry']
    })
    recordState;

    get accountName() {
        return this.recordState?.data?.fields?.Name?.value;
    }

    get industry() {
        return this.recordState?.data?.fields?.Industry?.value;
    }

    // State manager provides loading/error states
    get isLoading() {
        return this.recordState?.loading;
    }

    get hasError() {
        return !!this.recordState?.error;
    }
}
```

### stateManagerLayout

Manages layout-aware state for flexipage components.

```javascript
import { LightningElement, wire } from 'lwc';
import { stateManagerLayout } from 'lightning/stateManagerLayout';

export default class LayoutAwareComponent extends LightningElement {
    @api recordId;
    @api objectApiName;

    // Wire layout state manager
    @wire(stateManagerLayout, {
        recordId: '$recordId',
        objectApiName: '$objectApiName'
    })
    layoutState;

    get isCompact() {
        return this.layoutState?.density === 'compact';
    }

    get visibleFields() {
        return this.layoutState?.fields || [];
    }
}
```

### Composing State Managers

```javascript
import { LightningElement, wire } from 'lwc';
import { stateManagerRecord } from 'lightning/stateManagerRecord';
import { atom, computed } from '@lwc/state';

// Custom state atoms
const selectedTabAtom = atom('details');
const expandedSectionsAtom = atom(new Set(['overview']));

export default class ComposedStateComponent extends LightningElement {
    @api recordId;

    // Platform state for record data
    @wire(stateManagerRecord, {
        recordId: '$recordId',
        fields: ['Account.Name', 'Account.Type', 'Account.Industry']
    })
    recordState;

    // Custom state for UI
    get selectedTab() {
        return selectedTabAtom.value;
    }

    get expandedSections() {
        return expandedSectionsAtom.value;
    }

    isSectionExpanded(sectionId) {
        return expandedSectionsAtom.value.has(sectionId);
    }

    handleTabChange(event) {
        selectedTabAtom.value = event.detail.value;
    }

    handleSectionToggle(event) {
        const sectionId = event.target.dataset.section;
        const sections = new Set(expandedSectionsAtom.value);

        if (sections.has(sectionId)) {
            sections.delete(sectionId);
        } else {
            sections.add(sectionId);
        }

        expandedSectionsAtom.value = sections;
    }
}
```

---

## Anti-Patterns to Avoid

### ❌ BAD: Mutating Objects In Place

```javascript
// DON'T - won't trigger reactivity
this.user.name = 'New Name';
this.items.push(newItem);
```

### ✅ GOOD: Create New References

```javascript
// DO - triggers reactivity
this.user = { ...this.user, name: 'New Name' };
this.items = [...this.items, newItem];
```

### ❌ BAD: Heavy Computation in Getters

```javascript
// DON'T - runs every render cycle
get expensiveComputation() {
    return this.items
        .map(item => complexTransform(item))
        .filter(item => complexFilter(item))
        .sort((a, b) => complexSort(a, b));
}
```

### ✅ GOOD: Cache Computed Values

```javascript
_cachedResult;
_lastItemsHash;

get optimizedComputation() {
    const currentHash = JSON.stringify(this.items);
    if (this._lastItemsHash !== currentHash) {
        this._cachedResult = this.items
            .map(item => complexTransform(item))
            .filter(item => complexFilter(item))
            .sort((a, b) => complexSort(a, b));
        this._lastItemsHash = currentHash;
    }
    return this._cachedResult;
}
```

### ❌ BAD: Forgetting to Unsubscribe

```javascript
// DON'T - memory leak
connectedCallback() {
    store.subscribe('data', (data) => this.data = data);
}
```

### ✅ GOOD: Clean Up Subscriptions

```javascript
// DO - proper cleanup
_unsubscribe;

connectedCallback() {
    this._unsubscribe = store.subscribe('data', (data) => this.data = data);
}

disconnectedCallback() {
    if (this._unsubscribe) {
        this._unsubscribe();
    }
}
```

---

## Best Practices Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATE MANAGEMENT BEST PRACTICES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CHOOSE THE RIGHT PATTERN                                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ✅ Start with simple reactive properties                                   │
│  ✅ Use singleton store for shared non-record state                         │
│  ✅ Use @lwc/state for complex derived state                                │
│  ✅ Use Platform State Managers on record pages                             │
│  ❌ Don't over-engineer simple components                                   │
│                                                                             │
│  REACTIVITY                                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ✅ Create new object/array references for updates                          │
│  ✅ Use spread operator: { ...obj, newProp }                                │
│  ✅ Use getters for computed values                                         │
│  ❌ Don't mutate objects/arrays in place                                    │
│                                                                             │
│  PERFORMANCE                                                                │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ✅ Cache expensive computations                                            │
│  ✅ Debounce rapid state updates                                            │
│  ✅ Clean up subscriptions in disconnectedCallback                          │
│  ❌ Don't do heavy computation in getters                                   │
│                                                                             │
│  TESTING                                                                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ✅ Test state transitions explicitly                                       │
│  ✅ Verify subscription cleanup                                             │
│  ✅ Mock store for unit tests                                               │
│  ❌ Don't test implementation details                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [SKILL.md](../SKILL.md) - PICKLES Framework overview
- [lwc-best-practices.md](lwc-best-practices.md) - General LWC patterns
- [triangle-pattern.md](triangle-pattern.md) - Component composition

---

## Source

> **References**:
> - [Mastering State Management in LWC using @lwc/state](https://salesforcediaries.com/2025/11/26/mastering-state-management-in-lwc-using-lwc-state/) - Salesforce Diaries
> - [Platform State Managers in LWC](https://salesforcediaries.com/2025/11/26/platform-state-managers-in-lwc/) - Salesforce Diaries
