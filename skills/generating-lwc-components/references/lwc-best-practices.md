<!-- Parent: generating-lwc-components/SKILL.md -->
# Lightning Web Components Best Practices

This guide provides comprehensive best practices for building production-ready LWC components, organized around the **PICKLES Framework** and incorporating advanced patterns from industry experts.

---

## PICKLES Framework Overview

The PICKLES Framework provides a structured approach to LWC architecture. Use it as a checklist during component design and implementation.

```
🥒 P - Prototype    → Validate ideas with wireframes & mock data
🥒 I - Integrate    → Choose data source (LDS, Apex, GraphQL)
🥒 C - Composition  → Structure component hierarchy & communication
🥒 K - Kinetics     → Handle user interactions & event flow
🥒 L - Libraries    → Leverage platform APIs & base components
🥒 E - Execution    → Optimize performance & lifecycle hooks
🥒 S - Security     → Enforce permissions & data protection
```

**Reference**: [PICKLES Framework](https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/) — David Picksley, Third Eye Consulting

---

## Component Design Principles

### Single Responsibility (PICKLES: Composition)

Each component should do one thing well.

```
✅ GOOD: accountCard, accountList, accountForm (separate components)
❌ BAD: accountManager (does display, list, and form in one)
```

### Composition Over Inheritance

Build complex UIs by composing simple components.

```html
<!-- Compose components -->
<template>
    <c-page-header title="Accounts"></c-page-header>
    <c-account-filters onfilter={handleFilter}></c-account-filters>
    <c-account-list accounts={filteredAccounts}></c-account-list>
    <c-pagination total={totalCount} onpage={handlePage}></c-pagination>
</template>
```

### Unidirectional Data Flow

Data flows down (props), events bubble up.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA FLOW PATTERN                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Parent Component                                               │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  state: accounts = [...]                                │   │
│   │                                                          │   │
│   │  ┌──────────┐     ┌──────────┐     ┌──────────┐        │   │
│   │  │ Child A  │ ←── │ Child B  │ ←── │ Child C  │        │   │
│   │  │          │     │          │     │          │        │   │
│   │  │ @api     │     │ @api     │     │ @api     │        │   │
│   │  │ accounts │     │ selected │     │ details  │        │   │
│   │  └────┬─────┘     └────┬─────┘     └────┬─────┘        │   │
│   │       │                │                │               │   │
│   │       │   Events       │   Events       │   Events      │   │
│   │       └────────────────┴────────────────┘               │   │
│   │              ↑ bubbles to parent                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Naming & Decorator Conventions

### Property & Attribute Naming

| Context | Convention | Example |
|---------|-----------|---------|
| JavaScript properties | camelCase | `itemName`, `maxValue` |
| HTML attributes | kebab-case, lowercase | `item-name`, `max-value` |
| Dispatched event names | Lowercase, no `on` prefix | `'recordchange'`, `'save'` |
| HTML event listeners | `on` + event name | `onrecordchange`, `onsave` |

Reserved prefixes in JS property names: `on`, `aria`, `data`. Reserved words: `slot`, `part`, `is`.

### @api Decorator Rules

- Only one decorator per field/method — do not combine `@api` with `@track` or `@wire`
- For getter/setter pairs: decorate only the getter, and always define both getter and setter
- Never mutate `@api` properties internally — use a private reactive copy instead
- Only use `@api` on properties/methods that are part of the component's public API

```javascript
// ✅ GOOD: getter/setter with @api on getter only
_recordId;

@api
get recordId() { return this._recordId; }
set recordId(value) {
    this._recordId = value;
    this.loadRecord();
}
```

### @track Decorator Rules

Since Spring '20, primitive properties are reactive by default. `@track` is only needed when **mutating nested properties** of objects or arrays.

| Scenario | @track Needed? |
|----------|----------------|
| Primitive value (`string`, `number`, `boolean`) | No |
| Object/array that is **reassigned** entirely | No |
| Object with **nested property mutation** (`this.obj.nested.value++`) | Yes |

```javascript
// ❌ Unnecessary: primitives are reactive by default
@track searchTerm = '';

// ✅ Correct: remove @track for primitives
searchTerm = '';

// ✅ Correct: @track needed for nested mutation
@track formData = { billing: { city: '' } };
// later: this.formData.billing.city = 'San Francisco';
```

---

## Data Integration (PICKLES: Integrate)

### Data Source Decision Tree

| Scenario | Recommended Approach |
|----------|---------------------|
| Single record by ID | Lightning Data Service (`getRecord`) |
| Simple record CRUD | `lightning-record-form` / `lightning-record-edit-form` |
| Complex queries | Apex with `@AuraEnabled(cacheable=true)` |
| Related records, filtering | GraphQL wire adapter |
| Real-time updates | Platform Events / Streaming API |
| External data | Named Credentials + Apex callout |

### GraphQL vs Apex Decision

| Use GraphQL When | Use Apex When |
|------------------|---------------|
| Fetching related objects | Complex business logic |
| Client-side filtering | Aggregate queries (COUNT, SUM) |
| Cursor-based pagination | Bulk DML operations |
| Reducing over-fetching | Callouts to external systems |

### Wire Service Best Practices

```javascript
// Store wire result for refreshApex
wiredAccountsResult;

@wire(getAccounts, { searchTerm: '$searchTerm' })
wiredAccounts(result) {
    this.wiredAccountsResult = result;  // Store for refresh
    const { data, error } = result;
    if (data) {
        this.accounts = data;
        this.error = undefined;
    } else if (error) {
        this.error = this.reduceErrors(error);
        this.accounts = [];
    }
}

// Refresh when needed
async handleRefresh() {
    await refreshApex(this.wiredAccountsResult);
}
```

### Error Handling Pattern

```javascript
// Centralized error reducer
reduceErrors(errors) {
    if (!Array.isArray(errors)) {
        errors = [errors];
    }

    return errors
        .filter(error => !!error)
        .map(error => {
            // UI API errors
            if (error.body?.message) return error.body.message;
            // JS errors
            if (error.message) return error.message;
            // GraphQL errors
            if (error.graphQLErrors) {
                return error.graphQLErrors.map(e => e.message).join(', ');
            }
            return JSON.stringify(error);
        })
        .join('; ');
}
```
---

## Event Patterns (PICKLES: Kinetics)

### Custom Events

```javascript
// Child dispatches event
this.dispatchEvent(new CustomEvent('select', {
    detail: { recordId: this.recordId },
    bubbles: true,    // Bubbles through DOM
    composed: true    // Crosses shadow boundary
}));

// Parent handles event
handleSelect(event) {
    const recordId = event.detail.recordId;
}
```

### Event Bubbling Configuration

Choose the minimum propagation scope needed:

| Configuration | Encapsulation | Use Case |
|---------------|---------------|----------|
| `{ bubbles: false, composed: false }` | **Maximum** (Preferred) | Direct parent-child communication |
| `{ bubbles: true, composed: false }` | Acceptable | Internal shadow DOM communication |
| `{ bubbles: false, composed: true }` | Acceptable | Cross shadow boundary without full bubbling |
| `{ bubbles: true, composed: true }` | **Discouraged** | Only when grandparent+ must handle event |

```javascript
// ✅ Preferred: Maximum encapsulation
this.dispatchEvent(new CustomEvent('select', {
    detail: { recordId: this.recordId }
    // bubbles and composed default to false
}));

// ⚠️ Use only when necessary
this.dispatchEvent(new CustomEvent('globalnotify', {
    detail: { message: 'Record saved' },
    bubbles: true,
    composed: true
}));
```

### Event Data Passing

```javascript
// Primitives: pass directly in detail
this.dispatchEvent(new CustomEvent('update', {
    detail: this.recordId  // string — no wrapping needed
}));

// Non-primitives: always pass a copy to prevent mutation
this.dispatchEvent(new CustomEvent('change', {
    detail: { ...this.formData }  // shallow copy
}));
```

### Event Naming Conventions

```
✅ GOOD                    ❌ BAD
────────────────────────   ────────────────────────
onselect                   onSelectItem
onrecordchange             on-record-change
onsave                     onSaveClicked
onerror                    onErrorOccurred
```

### When to Use LMS vs Events

| Scenario | Use |
|----------|-----|
| Parent-child communication | Custom events |
| Sibling components (same parent) | Events via parent |
| Components on different parts of page | Lightning Message Service |
| LWC to Aura communication | LMS |
| LWC to Visualforce | LMS |

### Debouncing Pattern

```javascript
delayTimeout;

handleSearch(event) {
    const searchTerm = event.target.value;
    clearTimeout(this.delayTimeout);

    this.delayTimeout = setTimeout(() => {
        this.searchTerm = searchTerm;
    }, 300);  // 300ms debounce
}
```

---

## Spread Patterns & Destructuring

### lwc:spread Directive

The `lwc:spread` directive dynamically spreads object properties as component attributes. Useful for reducing boilerplate and enabling dynamic attribute binding.

**Reference**: [Saurabh Samir - lwc:spread Directive](https://medium.com/@saurabh.samirs)

#### Basic Usage

```html
<!-- Without lwc:spread (verbose) -->
<lightning-button
    label={buttonLabel}
    variant={buttonVariant}
    disabled={isDisabled}
    onclick={handleClick}>
</lightning-button>

<!-- With lwc:spread (dynamic) -->
<lightning-button lwc:spread={buttonAttributes} onclick={handleClick}></lightning-button>
```

```javascript
get buttonAttributes() {
    return {
        label: this.buttonLabel,
        variant: this.isImportant ? 'brand' : 'neutral',
        disabled: this.isProcessing
    };
}
```

#### lwc:spread vs @api Object Binding

| Approach | Use When | Reactivity |
|----------|----------|------------|
| `lwc:spread={obj}` | Passing multiple attributes dynamically | Re-renders on object change |
| `@api config` | Passing structured data to custom component | Must spread in child |
| Individual `@api` props | Simple, known properties | Each prop triggers render |

#### Conditional Attribute Spreading

```javascript
get inputAttributes() {
    const attrs = {
        label: 'Search',
        type: 'text',
        value: this.searchTerm
    };

    // Conditionally add attributes
    if (this.isRequired) {
        attrs.required = true;
    }

    if (this.maxLength) {
        attrs['max-length'] = this.maxLength;
    }

    return attrs;
}
```

```html
<lightning-input lwc:spread={inputAttributes} onchange={handleChange}></lightning-input>
```

#### Event Handlers with lwc:spread

**Important**: Event handlers must be bound separately, not spread:

```html
<!-- ✅ CORRECT: Event handler separate from spread -->
<lightning-button lwc:spread={buttonProps} onclick={handleClick}></lightning-button>

<!-- ❌ INCORRECT: onclick in spread object won't work -->
<!-- buttonProps = { label: 'Save', onclick: this.handleClick } -->
```

### lwc:on Directive (Spring '26 - API 66.0)

The `lwc:on` directive solves the limitation above by enabling **dynamic event binding** directly from JavaScript. It allows you to bind multiple event handlers at runtime.

**Requires**: API 66.0+ (Spring '26)

#### Basic Usage

```javascript
// component.js
export default class DynamicEventComponent extends LightningElement {
    // Define event handlers as object properties
    eventHandlers = {
        click: this.handleClick.bind(this),
        mouseover: this.handleMouseOver.bind(this),
        focus: this.handleFocus.bind(this)
    };

    handleClick() {
        console.log('Element clicked!');
    }

    handleMouseOver() {
        console.log('Mouse over!');
    }

    handleFocus() {
        console.log('Element focused!');
    }
}
```

```html
<!-- template.html -->
<template>
    <!-- Bind multiple event handlers dynamically -->
    <button lwc:on={eventHandlers}>Click Me</button>
</template>
```

#### Combining lwc:spread and lwc:on

For fully dynamic components, combine both directives:

```javascript
// component.js
export default class FullyDynamicButton extends LightningElement {
    // Properties via lwc:spread
    buttonAttributes = {
        label: 'Save',
        variant: 'brand',
        disabled: false
    };

    // Events via lwc:on
    buttonEvents = {
        click: this.handleClick.bind(this),
        focus: this.handleFocus.bind(this)
    };

    handleClick() {
        this.dispatchEvent(new CustomEvent('save'));
    }

    handleFocus() {
        console.log('Button focused');
    }
}
```

```html
<!-- template.html -->
<template>
    <!-- Best of both worlds: dynamic props AND dynamic events -->
    <lightning-button
        lwc:spread={buttonAttributes}
        lwc:on={buttonEvents}>
    </lightning-button>
</template>
```

#### Dynamic Event Handlers from @api

Pass event handler configurations from parent components:

```javascript
// childComponent.js
export default class ChildComponent extends LightningElement {
    @api eventConfig; // { click: handler, change: handler }

    get resolvedHandlers() {
        // Ensure handlers are properly bound
        const handlers = {};
        if (this.eventConfig) {
            Object.entries(this.eventConfig).forEach(([event, handler]) => {
                handlers[event] = typeof handler === 'function' ? handler : () => {};
            });
        }
        return handlers;
    }
}
```

```html
<!-- childComponent.html -->
<template>
    <div lwc:on={resolvedHandlers}>
        <slot></slot>
    </div>
</template>
```

#### Removing Event Listeners

Remove specific event listeners by omitting them from the object:

```javascript
// Toggle mouseover handler on/off
toggleHoverHandler() {
    if (this._hoverEnabled) {
        // Remove mouseover by omitting it
        this.eventHandlers = {
            click: this.handleClick.bind(this)
        };
    } else {
        // Add mouseover back
        this.eventHandlers = {
            click: this.handleClick.bind(this),
            mouseover: this.handleMouseOver.bind(this)
        };
    }
    this._hoverEnabled = !this._hoverEnabled;
}
```

#### lwc:spread vs lwc:on Comparison

| Directive | Purpose | Use Case |
|-----------|---------|----------|
| `lwc:spread` | Dynamic **properties/attributes** | Pass label, variant, disabled dynamically |
| `lwc:on` | Dynamic **event handlers** | Bind click, change, custom events dynamically |
| Both together | Fully dynamic configuration | Reusable wrapper components, dynamic UIs |

**Important Notes**:
- Do NOT mutate the object passed to `lwc:on` - create a new object to update handlers
- Event type names should be lowercase without the `on` prefix (use `click` not `onclick`)
- Always use `.bind(this)` or arrow functions to preserve context

### Object Spread & Destructuring

Modern JavaScript patterns for cleaner data handling in LWC.

#### Object Spread for Config Merging

```javascript
// Default + user config pattern
const defaultConfig = {
    pageSize: 10,
    sortField: 'Name',
    sortDirection: 'ASC'
};

get tableConfig() {
    return {
        ...defaultConfig,
        ...this.userConfig  // User config overrides defaults
    };
}
```

#### Destructuring with Defaults

```javascript
// Extract values with fallbacks
handleRecordLoad(record) {
    const {
        Name = 'Unknown',
        Industry = 'Not Specified',
        AnnualRevenue = 0
    } = record.fields;

    this.accountName = Name.value;
    this.industry = Industry.value;
    this.revenue = AnnualRevenue.value;
}
```

#### Nested Destructuring

```javascript
// Deep extraction in single statement
processResult(result) {
    const {
        data: {
            record: {
                fields: { Name, BillingCity }
            }
        },
        error
    } = result;

    if (error) {
        this.handleError(error);
        return;
    }

    this.name = Name.value;
    this.city = BillingCity.value;
}
```

#### Array Spread Patterns

```javascript
// Immutable array updates (required for LWC reactivity)
addItem(newItem) {
    this.items = [...this.items, newItem];  // Append
}

removeItem(index) {
    this.items = [
        ...this.items.slice(0, index),
        ...this.items.slice(index + 1)
    ];  // Remove at index
}

updateItem(index, updates) {
    this.items = this.items.map((item, i) =>
        i === index ? { ...item, ...updates } : item
    );  // Update at index
}
```

#### Parameter Spreading in Apex Calls

```javascript
async handleSubmit() {
    const result = await createRecord({
        ...this.recordData,
        CreatedBy__c: this.currentUserId,
        Status__c: 'Pending'
    });
}
```

### When to Use Each Pattern

| Pattern | Best For | Avoid When |
|---------|----------|------------|
| `lwc:spread` | Many dynamic attributes, base component wrappers | Need event binding, simple static props |
| Object spread | Config merging, immutable updates | Deep objects (consider structuredClone) |
| Destructuring | Extracting multiple values, API responses | Simple single-property access |
| Array spread | Adding/removing items immutably | Large arrays (performance concern) |

---

## Complex Template Expressions (Spring '26 Beta - API 66.0)

Spring '26 introduces **complex template expressions**, enabling JavaScript expressions directly in templates. This was previously limited to simple property and getter bindings.

> ⚠️ **Beta Feature**: Use getters in production until this becomes GA. Document any complex expressions for future migration.

### Before vs After

```html
<!-- BEFORE Spring '26: Required getters for any logic -->
<template>
    <!-- Simple property binding only -->
    <template lwc:if={isValid}>...</template>

    <!-- Complex conditions needed a getter -->
    <template lwc:if={showLoadingState}>...</template>
</template>
```

```javascript
// Required getter in JS
get showLoadingState() {
    return this.isLoading && this.items.length === 0;
}
```

```html
<!-- AFTER Spring '26 (Beta): Complex expressions in template -->
<template>
    <!-- Logical operators -->
    <template lwc:if={!isLoading && items.length > 0}>
        <c-item-list items={items}></c-item-list>
    </template>

    <!-- Optional chaining -->
    <template lwc:if={user?.permissions?.canEdit}>
        <lightning-button label="Edit"></lightning-button>
    </template>

    <!-- Arithmetic expressions -->
    <span class="slds-text-body_small">
        Total: ${total * taxRate}
    </span>

    <!-- Comparison operators -->
    <template lwc:if={items.length >= minItems}>
        <c-pagination></c-pagination>
    </template>
</template>
```

### Supported Expression Types

| Expression Type | Example | Notes |
|-----------------|---------|-------|
| **Logical NOT** | `{!isLoading}` | Negation |
| **Logical AND** | `{a && b}` | Short-circuit evaluation |
| **Logical OR** | `{a \|\| b}` | Short-circuit evaluation |
| **Comparison** | `{count > 0}`, `{status === 'active'}` | `==`, `===`, `!=`, `!==`, `<`, `>`, `<=`, `>=` |
| **Arithmetic** | `{price * quantity}` | `+`, `-`, `*`, `/`, `%` |
| **Optional Chaining** | `{user?.profile?.name}` | Safe property access |
| **Nullish Coalescing** | `{value ?? 'default'}` | Default for null/undefined |
| **Ternary** | `{isActive ? 'Yes' : 'No'}` | Conditional value |
| **Array Access** | `{items[0]}` | Index-based access |
| **String Concatenation** | `{firstName + ' ' + lastName}` | String joining |

### Best Practices for Complex Expressions

```html
<!-- ✅ GOOD: Simple inline logic -->
<template lwc:if={!isLoading && hasData}>
    ...
</template>

<!-- ✅ GOOD: Optional chaining for safety -->
<span>{account?.Owner?.Name}</span>

<!-- ⚠️ CAUTION: Keep expressions readable -->
<!-- If expression is long, consider a getter for maintainability -->
<template lwc:if={isEditable && hasPermission && !isLocked && status === 'draft'}>
    <!-- Consider: get canEdit() { return ...; } -->
</template>

<!-- ❌ AVOID: Side effects in expressions -->
<!-- Don't call methods that modify state -->
```

### Migration Strategy

1. **New code**: Use complex expressions for simple conditions
2. **Existing code**: Keep getters that have unit tests
3. **Complex logic**: Continue using getters for maintainability
4. **Document**: Mark complex expressions in templates for review when GA

### Limitations (Beta)

- No function calls in expressions (use getters)
- No template literals with `${}` interpolation
- Cannot reference `this` directly
- No destructuring in expressions

---

## Template Directives

### Conditional Rendering: Legacy → Modern

Always use `lwc:if`, `lwc:elseif`, `lwc:else` instead of the deprecated `if:true` / `if:false` directives.

```html
<!-- ❌ Legacy (deprecated) -->
<template if:true={isLoading}>
    <lightning-spinner></lightning-spinner>
</template>
<template if:false={isLoading}>
    <c-data-view data={records}></c-data-view>
</template>

<!-- ✅ Modern -->
<template lwc:if={isLoading}>
    <lightning-spinner></lightning-spinner>
</template>
<template lwc:elseif={error}>
    <c-error-panel errors={error}></c-error-panel>
</template>
<template lwc:else>
    <c-data-view data={records}></c-data-view>
</template>
```

**Rules**: Conditional directives are valid on `<template>`, standard HTML tags, custom components, and base components. All elements in a conditional group must be siblings at the same DOM level.

### List Rendering

#### for:each

Every `for:each` must be paired with `for:item`. The `key` attribute must use a stable unique identifier — always `key={item.id}`, never an index.

```html
<!-- ✅ GOOD -->
<template for:each={accounts} for:item="account">
    <c-account-card key={account.Id} account={account}></c-account-card>
</template>

<!-- ❌ BAD: key={index} or key={account.Name} -->
```

#### iterator Directive

Use `iterator` when you need access to `.first` or `.last` metadata for conditional styling.

```html
<template iterator:it={contacts}>
    <div key={it.value.Id}>
        {it.value.Name}
    </div>
</template>
```

**Iterator name must be lowercase**. Access item data via `{iteratorname}.value.property` and metadata via `.index`, `.first`, `.last`.

#### Nested Loop Rules

Use distinct `for:item` or `iterator` names in nested loops to avoid variable shadowing:

```html
<!-- ✅ Distinct names -->
<template for:each={departments} for:item="dept">
    <div key={dept.Id}>
        <template for:each={dept.Employees} for:item="emp">
            <span key={emp.Id}>{emp.Name}</span>
        </template>
    </div>
</template>
```

### Multiple Template Rendering

When a component needs to switch between entirely different layouts, import multiple HTML templates and return the appropriate one from `render()`.

```javascript
import defaultTemplate from './myComponent.html';
import editTemplate from './myComponentEdit.html';

export default class MyComponent extends LightningElement {
    isEditing = false;

    render() {
        return this.isEditing ? editTemplate : defaultTemplate;
    }
}
```

---

## Performance Optimization (PICKLES: Execution)

### Lifecycle Hook Guidance

| Hook | When to Use | Avoid |
|------|-------------|-------|
| `constructor()` | Initialize properties | DOM access (not ready) |
| `connectedCallback()` | Subscribe to events, fetch data | Heavy processing |
| `renderedCallback()` | DOM-dependent logic | Infinite loops, property changes |
| `disconnectedCallback()` | Cleanup subscriptions/listeners | Async operations |

### Lazy Loading

```html
<!-- Only render when needed -->
<template lwc:if={showDetails}>
    <c-expensive-component record-id={recordId}></c-expensive-component>
</template>
```

### Efficient Rendering

```javascript
// Bad: Creates new array every render
get filteredItems() {
    return this.items.filter(item => item.active);
}

// Good: Cache the result
_filteredItems;
_itemsHash;

get filteredItems() {
    const currentHash = JSON.stringify(this.items);
    if (currentHash !== this._itemsHash) {
        this._filteredItems = this.items.filter(item => item.active);
        this._itemsHash = currentHash;
    }
    return this._filteredItems;
}
```

### Virtual Scrolling

Use `lightning-datatable` with `enable-infinite-loading` for large datasets instead of rendering all items.

**For comprehensive performance patterns** (DOM optimization, event delegation, memory management, bundle size): see `references/performance-guide.md`

---

## Advanced Jest Testing Patterns

Based on [James Simone's advanced testing patterns](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/).

### Render Cycle Helper

LWC re-rendering is asynchronous. Use this helper to document and await render cycles:

```javascript
// testUtils.js
export const runRenderingLifecycle = async (reasons = ['render']) => {
    while (reasons.length > 0) {
        await Promise.resolve(reasons.pop());
    }
};

// Usage in tests
it('updates after property change', async () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    element.greeting = 'new value';
    await runRenderingLifecycle(['property change', 'render']);

    expect(element.shadowRoot.querySelector('div').textContent).toBe('new value');
});
```

### Proxy Unboxing (Lightning Web Security)

Lightning Web Security proxifies objects. Unbox them for assertions:

```javascript
// LWS proxifies complex objects - unbox for comparison
const unboxedData = JSON.parse(JSON.stringify(component.data));
expect(unboxedData).toEqual(expectedData);
```

### DOM Cleanup Pattern

Clean up after each test to prevent state bleed:

```javascript
describe('c-my-component', () => {
    afterEach(() => {
        // Clean up DOM
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });
});
```

### ResizeObserver Polyfill

Some components use ResizeObserver. Add polyfill in jest.setup.js:

```javascript
// jest.setup.js
if (!window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserver {
        constructor(callback) {
            this.callback = callback;
        }
        observe() {}
        unobserve() {}
        disconnect() {}
    };
}
```

### Mocking Apex Methods

```javascript
jest.mock('@salesforce/apex/MyController.getData', () => ({
    default: jest.fn()
}), { virtual: true });

// In test
import getData from '@salesforce/apex/MyController.getData';

it('displays data', async () => {
    getData.mockResolvedValue(MOCK_DATA);
    // ... test code
});
```

---

## Security Best Practices (PICKLES: Security)

### FLS Enforcement

```apex
// Always use SECURITY_ENFORCED or stripInaccessible
@AuraEnabled(cacheable=true)
public static List<Account> getAccounts() {
    return [SELECT Id, Name FROM Account WITH SECURITY_ENFORCED];
}

// For DML operations
SObjectAccessDecision decision = Security.stripInaccessible(
    AccessType.CREATABLE,
    records
);
insert decision.getRecords();
```

### Input Sanitization

```apex
// Apex should escape user input
String searchKey = '%' + String.escapeSingleQuotes(searchTerm) + '%';
```

### XSS Prevention

LWC automatically escapes content in templates. Never bypass this.

```html
<!-- Safe: LWC auto-escapes -->
<p>{userInput}</p>
```

### Input Validation Patterns

#### Lightning Base Component Validation Attributes

Use built-in validation attributes on Lightning input components to enforce constraints declaratively:

```html
<lightning-input
    label="Email"
    type="email"
    required
    max-length="255"
    message-when-value-missing="Email is required"
    message-when-pattern-mismatch="Enter a valid email address"
    onchange={handleEmailChange}>
</lightning-input>
```

#### Form Submission Validation

Always validate all inputs before processing a form submission:

```javascript
handleSubmit() {
    const allValid = [...this.template.querySelectorAll('lightning-input')]
        .reduce((valid, input) => {
            input.reportValidity();
            return valid && input.checkValidity();
        }, true);

    if (!allValid) {
        return;  // Stop — validation errors displayed to user
    }

    this.saveRecord();
}
```

#### Custom Validation with setCustomValidity

```javascript
handleBlur(event) {
    const input = event.target;
    if (input.value && !this.isUniqueName(input.value)) {
        input.setCustomValidity('This name is already in use');
    } else {
        input.setCustomValidity('');  // Always clear when valid
    }
    input.reportValidity();
}
```

### Scoped Module Imports

Always use static `@salesforce/` scoped imports instead of legacy Global Value Providers (`$Label`, `$Resource`, etc.)

---

## Accessibility (a11y)

### Required Practices

| Element | Requirement |
|---------|-------------|
| Buttons | `label` or `aria-label` |
| Icons | `alternative-text` |
| Form inputs | Associated `<label>` |
| Dynamic content | `aria-live` region |
| Loading states | `aria-busy="true"` |

### Keyboard Navigation

```javascript
handleKeyDown(event) {
    switch (event.key) {
        case 'Enter':
        case ' ':
            this.handleSelect(event);
            break;
        case 'Escape':
            this.handleClose();
            break;
        case 'ArrowDown':
            this.focusNext();
            event.preventDefault();
            break;
    }
}
```

### Focus Trap Pattern (for Modals)

Based on [James Simone's modal pattern](https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/):

```javascript
_focusableElements = [];

_onOpen() {
    // Collect focusable elements
    this._focusableElements = [
        ...this.querySelectorAll('.focusable'),
        ...this.template.querySelectorAll('lightning-button, button, [tabindex="0"]')
    ].filter(el => !el.disabled);

    // Focus first element
    this._focusableElements[0]?.focus();

    // Add ESC handler
    window.addEventListener('keyup', this._handleKeyUp);
}

_handleKeyUp = (event) => {
    if (event.code === 'Escape') {
        this.close();
    }
}

disconnectedCallback() {
    window.removeEventListener('keyup', this._handleKeyUp);
}
```

---

## SLDS 2 & Dark Mode

### Dark Mode Checklist

- [ ] No hardcoded hex colors (`#FFFFFF`, `#333333`)
- [ ] No hardcoded RGB/RGBA values
- [ ] All colors use CSS variables (`var(--slds-g-color-*)`)
- [ ] Fallback values provided for SLDS 1 compatibility
- [ ] Icons use SLDS utility icons (auto-adjust for dark mode)

### SLDS 1 → SLDS 2 Migration

```css
/* BEFORE (SLDS 1 - Deprecated) */
.my-card {
    background-color: #ffffff;
    color: #333333;
}

/* AFTER (SLDS 2 - Dark Mode Ready) */
.my-card {
    background-color: var(--slds-g-color-surface-container-1, #ffffff);
    color: var(--slds-g-color-on-surface, #181818);
}
```

### Key Global Styling Hooks

| Category | SLDS 2 Variable |
|----------|-----------------|
| Surface | `--slds-g-color-surface-1` to `-4` |
| Text | `--slds-g-color-on-surface` |
| Border | `--slds-g-color-border-1`, `-2` |
| Spacing | `--slds-g-spacing-0` to `-12` |

**Important**: `--slds-c-*` (component-level hooks) are NOT supported in SLDS 2 yet.

---

## CSS Isolation & Scoping

LWC uses Shadow DOM for style encapsulation. Follow these rules to prevent style leakage and collisions.

### CSS Selector Rules

| Pattern | Status | Reason |
|---------|--------|--------|
| `:host` | ✅ Use | Targets the component's root element |
| `:host(.modifier)` | ✅ Use | Conditional styling based on host class |
| `.my-class` | ✅ Use | Class selectors scoped automatically |
| `*` (universal) | ❌ Avoid | Can leak outside component scope |
| `#my-id` | ❌ Avoid | LWC transforms IDs to globally unique values |
| `c-my-component` | ❌ Avoid | Use `:host` instead of component name |
| `:host-context()` | ❌ Not supported | Use `:host` instead |
| `lightning-button` | ❌ Avoid | Cannot override base component internals |
| `.slds-button` | ❌ Avoid | Cannot replace or override SLDS classes |

```css
/* ❌ BAD: Universal selector leaks */
* { font-family: Arial, sans-serif; }

/* ✅ GOOD: Scoped universal */
:host * { font-family: Arial, sans-serif; }

/* ❌ BAD: Component name as selector */
c-my-component { display: flex; }

/* ✅ GOOD: :host for component-level styles */
:host { display: flex; }

/* ❌ BAD: Overriding base component or SLDS */
lightning-button { background-color: red; }
.slds-button { background-color: purple; }

/* ✅ GOOD: Use styling hooks */
:host {
    --slds-c-button-brand-color-background: red;
}
```

### Avoid `!important` Overuse

Rely on proper specificity rather than `!important` declarations. Excessive `!important` interferes with parent component styling and makes future maintenance difficult.

### Never Rely on Compiler-Generated Scope Tokens

```css
/* ❌ BAD: Brittle — token changes across builds */
c-child[lwc-2j48dfhd928c-host] { padding: 1rem; }

/* ✅ GOOD */
:host { padding: 1rem; }
```

---

## Testing Checklist

### Unit Test Coverage

- [ ] Component renders without errors
- [ ] Data displays correctly when loaded
- [ ] Error state displays when fetch fails
- [ ] Empty state displays when no data
- [ ] Events dispatch with correct payload
- [ ] User interactions work correctly
- [ ] Loading states are shown/hidden appropriately

### Manual Testing

- [ ] Works in Lightning Experience
- [ ] Works in Salesforce Mobile
- [ ] Works in Experience Cloud (if targeted)
- [ ] Works in Dark Mode (SLDS 2)
- [ ] Keyboard navigation works
- [ ] Screen reader announces properly
- [ ] No console errors
- [ ] Performance acceptable with real data

---

## Common Mistakes

### 1. Modifying @api Properties

```javascript
// ❌ BAD
@api items;
handleClick() {
    this.items.push(newItem);  // Mutation!
}

// ✅ GOOD
handleClick() {
    this.items = [...this.items, newItem];
}
```

### 2. Forgetting to Clean Up

```javascript
// ❌ BAD: Memory leak
connectedCallback() {
    this.subscription = subscribe(...);
}

// ✅ GOOD
disconnectedCallback() {
    unsubscribe(this.subscription);
}
```

### 3. Wire with Non-Reactive Parameters

```javascript
// ❌ BAD
let recordId = '001xxx';
@wire(getRecord, { recordId: recordId })

// ✅ GOOD
@api recordId;
@wire(getRecord, { recordId: '$recordId' })
```

---

## Resources

- [PICKLES Framework](https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/) — David Picksley, Third Eye Consulting
- [LWC Recipes (GitHub)](https://github.com/trailheadapps/lwc-recipes)
- [SLDS 2 Transition Guide](https://www.lightningdesignsystem.com/2e1ef8501/p/8184ad-transition-to-slds-2)
- [James Simone - Advanced Jest Testing](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/)
- [James Simone - Composable Modal](https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/)
- [SLDS Styling Hooks](https://developer.salesforce.com/docs/platform/lwc/guide/create-components-css-custom-properties.html)
