<!-- Parent: generating-lwc-components/SKILL.md -->
# LWC Template Anti-Patterns

This guide documents systematic errors in Lightning Web Component templates, with special focus on patterns that LLMs commonly generate incorrectly. LWC templates have strict limitations compared to frameworks like React or Vue.

> **Source**: [LLM Mistakes in Apex & LWC - Salesforce Diaries](https://salesforcediaries.com/2026/01/16/llm-mistakes-in-apex-lwc-salesforce-code-generation-rules/)

---

## Table of Contents

1. [Inline JavaScript Expressions](#1-inline-javascript-expressions)
2. [Ternary Operators in Templates](#2-ternary-operators-in-templates)
3. [Object Literals in Attributes](#3-object-literals-in-attributes)
4. [Complex Expressions](#4-complex-expressions)
5. [Event Handler Mistakes](#5-event-handler-mistakes)
6. [Iteration Anti-Patterns](#6-iteration-anti-patterns)
7. [Conditional Rendering Issues](#7-conditional-rendering-issues)
8. [Slot and Composition Errors](#8-slot-and-composition-errors)
9. [Data Binding Mistakes](#9-data-binding-mistakes)
10. [Style and Class Binding](#10-style-and-class-binding)

---

## 1. Inline JavaScript Expressions

**Critical Rule**: LWC templates do NOT support JavaScript expressions. Only property references are allowed.

### ❌ BAD: Arithmetic in Template

```html
<!-- LLM generates this - DOES NOT WORK -->
<template>
    <p>Total: {price * quantity}</p>
    <p>Tax: {price * 0.1}</p>
    <p>Discount: {price - discount}</p>
</template>
```

### ✅ GOOD: Use Getters

```javascript
// component.js
export default class PriceCalculator extends LightningElement {
    price = 100;
    quantity = 2;
    discount = 10;

    get total() {
        return this.price * this.quantity;
    }

    get tax() {
        return this.price * 0.1;
    }

    get discountedPrice() {
        return this.price - this.discount;
    }
}
```

```html
<!-- component.html -->
<template>
    <p>Total: {total}</p>
    <p>Tax: {tax}</p>
    <p>Discount: {discountedPrice}</p>
</template>
```

### ❌ BAD: String Concatenation in Template

```html
<!-- DOES NOT WORK -->
<template>
    <p>Hello, {firstName + ' ' + lastName}!</p>
    <a href={'/account/' + accountId}>View Account</a>
</template>
```

### ✅ GOOD: Computed Properties

```javascript
// component.js
export default class Greeting extends LightningElement {
    firstName = 'John';
    lastName = 'Doe';
    accountId = '001xx000003DGbY';

    get fullName() {
        return `${this.firstName} ${this.lastName}`;
    }

    get accountUrl() {
        return `/account/${this.accountId}`;
    }
}
```

```html
<!-- component.html -->
<template>
    <p>Hello, {fullName}!</p>
    <a href={accountUrl}>View Account</a>
</template>
```

---

## 2. Ternary Operators in Templates

**Critical Rule**: Ternary operators (`condition ? a : b`) are NOT allowed in LWC templates.

### ❌ BAD: Ternary in Template

```html
<!-- LLM generates this - DOES NOT WORK -->
<template>
    <p class={isActive ? 'active' : 'inactive'}>Status</p>
    <span>{count > 0 ? count : 'None'}</span>
    <button disabled={isLoading ? true : false}>Submit</button>
</template>
```

### ✅ GOOD: Use Getters for Conditional Values

```javascript
// component.js
export default class StatusDisplay extends LightningElement {
    isActive = true;
    count = 0;
    isLoading = false;

    get statusClass() {
        return this.isActive ? 'active' : 'inactive';
    }

    get displayCount() {
        return this.count > 0 ? this.count : 'None';
    }

    get isButtonDisabled() {
        return this.isLoading;
    }
}
```

```html
<!-- component.html -->
<template>
    <p class={statusClass}>Status</p>
    <span>{displayCount}</span>
    <button disabled={isButtonDisabled}>Submit</button>
</template>
```

### ✅ GOOD: Use if:true/if:false for Conditional Rendering

```html
<!-- component.html -->
<template>
    <template if:true={isActive}>
        <p class="active">Active</p>
    </template>
    <template if:false={isActive}>
        <p class="inactive">Inactive</p>
    </template>

    <template if:true={hasCount}>
        <span>{count}</span>
    </template>
    <template if:false={hasCount}>
        <span>None</span>
    </template>
</template>
```

```javascript
// component.js
get hasCount() {
    return this.count > 0;
}
```

---

## 3. Object Literals in Attributes

**Critical Rule**: Object literals (`{}`) cannot be passed directly as attribute values.

### ❌ BAD: Inline Object Literals

```html
<!-- LLM generates this - DOES NOT WORK -->
<template>
    <c-child-component
        config={{ showHeader: true, theme: 'dark' }}
        style={{ color: 'red', fontSize: '14px' }}>
    </c-child-component>

    <lightning-datatable
        columns={[{ label: 'Name', fieldName: 'name' }]}
        data={records}>
    </lightning-datatable>
</template>
```

### ✅ GOOD: Define Objects in JavaScript

```javascript
// component.js
export default class ParentComponent extends LightningElement {
    config = {
        showHeader: true,
        theme: 'dark'
    };

    columns = [
        { label: 'Name', fieldName: 'name' },
        { label: 'Email', fieldName: 'email' }
    ];

    records = [];
}
```

```html
<!-- component.html -->
<template>
    <c-child-component config={config}></c-child-component>

    <lightning-datatable
        columns={columns}
        data={records}>
    </lightning-datatable>
</template>
```

### ❌ BAD: Inline Array Literals

```html
<!-- DOES NOT WORK -->
<template>
    <c-multi-select options={['Red', 'Green', 'Blue']}></c-multi-select>
</template>
```

### ✅ GOOD: Define Arrays in JavaScript

```javascript
// component.js
export default class ColorPicker extends LightningElement {
    colorOptions = [
        { label: 'Red', value: 'red' },
        { label: 'Green', value: 'green' },
        { label: 'Blue', value: 'blue' }
    ];
}
```

```html
<!-- component.html -->
<template>
    <c-multi-select options={colorOptions}></c-multi-select>
</template>
```

---

## 4. Complex Expressions

**Critical Rule**: No method calls, comparisons, or logical operators in templates.

### ❌ BAD: Method Calls in Template

```html
<!-- LLM generates this - DOES NOT WORK -->
<template>
    <p>{name.toUpperCase()}</p>
    <p>{items.length}</p>
    <p>{formatDate(createdDate)}</p>
    <p>{JSON.stringify(data)}</p>
</template>
```

### ✅ GOOD: Use Getters for Transformations

```javascript
// component.js
export default class DataDisplay extends LightningElement {
    name = 'john doe';
    items = ['a', 'b', 'c'];
    createdDate = new Date();
    data = { key: 'value' };

    get upperName() {
        return this.name.toUpperCase();
    }

    get itemCount() {
        return this.items.length;
    }

    get formattedDate() {
        return new Intl.DateTimeFormat('en-US').format(this.createdDate);
    }

    get dataJson() {
        return JSON.stringify(this.data);
    }
}
```

```html
<!-- component.html -->
<template>
    <p>{upperName}</p>
    <p>{itemCount}</p>
    <p>{formattedDate}</p>
    <p>{dataJson}</p>
</template>
```

### ❌ BAD: Comparisons in Template

```html
<!-- DOES NOT WORK -->
<template>
    <template if:true={count > 5}>
        <p>Many items</p>
    </template>

    <template if:true={status === 'active'}>
        <p>Active</p>
    </template>
</template>
```

### ✅ GOOD: Getter-Based Comparisons

```javascript
// component.js
get hasManyItems() {
    return this.count > 5;
}

get isActive() {
    return this.status === 'active';
}
```

```html
<!-- component.html -->
<template>
    <template if:true={hasManyItems}>
        <p>Many items</p>
    </template>

    <template if:true={isActive}>
        <p>Active</p>
    </template>
</template>
```

### ❌ BAD: Logical Operators in Template

```html
<!-- DOES NOT WORK -->
<template>
    <template if:true={isAdmin && hasPermission}>
        <button>Delete</button>
    </template>

    <template if:true={!isLoading}>
        <p>Content</p>
    </template>
</template>
```

### ✅ GOOD: Computed Boolean Properties

```javascript
// component.js
get canDelete() {
    return this.isAdmin && this.hasPermission;
}

get isNotLoading() {
    return !this.isLoading;
}
```

```html
<!-- component.html -->
<template>
    <template if:true={canDelete}>
        <button>Delete</button>
    </template>

    <template if:true={isNotLoading}>
        <p>Content</p>
    </template>
</template>
```

---

## 5. Event Handler Mistakes

### ❌ BAD: Inline Event Handlers with Arguments

```html
<!-- LLM generates this - DOES NOT WORK -->
<template>
    <button onclick={handleClick(item.id)}>Click</button>
    <button onclick={() => this.handleDelete(record)}>Delete</button>
    <input onchange={e => this.handleChange(e.target.value)}>
</template>
```

### ✅ GOOD: Handler Functions with Data Attributes

```html
<!-- component.html -->
<template>
    <template for:each={items} for:item="item">
        <button
            key={item.id}
            data-id={item.id}
            onclick={handleClick}>
            Click {item.name}
        </button>
    </template>
</template>
```

```javascript
// component.js
handleClick(event) {
    const itemId = event.target.dataset.id;
    // or use event.currentTarget.dataset.id for delegated events
    console.log('Clicked item:', itemId);
}

handleChange(event) {
    const value = event.target.value;
    this.inputValue = value;
}
```

### ❌ BAD: Event Binding with bind()

```html
<!-- DOES NOT WORK -->
<template>
    <button onclick={handleClick.bind(this, item)}>Click</button>
</template>
```

### ✅ GOOD: Use Data Attributes for Context

```html
<!-- component.html -->
<template>
    <template for:each={items} for:item="item">
        <button
            key={item.id}
            data-id={item.id}
            data-name={item.name}
            data-index={item.index}
            onclick={handleItemClick}>
            {item.name}
        </button>
    </template>
</template>
```

```javascript
// component.js
handleItemClick(event) {
    const { id, name, index } = event.currentTarget.dataset;
    // dataset values are always strings
    const indexNum = parseInt(index, 10);
}
```

---

<a id="6-iteration-anti-patterns"></a>

## 6. Iteration Anti-Patterns

### ❌ BAD: Missing Key in Iteration

```html
<!-- LLM forgets key - causes rendering issues -->
<template>
    <template for:each={items} for:item="item">
        <div>{item.name}</div>  <!-- Missing key! -->
    </template>
</template>
```

### ✅ GOOD: Always Include Key

```html
<!-- component.html -->
<template>
    <template for:each={items} for:item="item">
        <div key={item.id}>{item.name}</div>
    </template>
</template>
```

### ❌ BAD: Using Index as Key

```html
<!-- Anti-pattern: index can cause issues with reordering -->
<template>
    <template for:each={items} for:item="item" for:index="index">
        <div key={index}>{item.name}</div>
    </template>
</template>
```

### ✅ GOOD: Use Unique Identifier as Key

```javascript
// If items don't have unique IDs, generate them
connectedCallback() {
    this.items = this.rawItems.map((item, index) => ({
        ...item,
        uniqueKey: `item-${item.name}-${index}`
    }));
}
```

```html
<!-- component.html -->
<template>
    <template for:each={items} for:item="item">
        <div key={item.uniqueKey}>{item.name}</div>
    </template>
</template>
```

### ❌ BAD: Nested Iteration Without Proper Keys

```html
<!-- PROBLEMATIC -->
<template>
    <template for:each={categories} for:item="category">
        <div key={category.id}>
            <h3>{category.name}</h3>
            <template for:each={category.items} for:item="item">
                <!-- Key might conflict with other categories -->
                <p key={item.id}>{item.name}</p>
            </template>
        </div>
    </template>
</template>
```

### ✅ GOOD: Compound Keys for Nested Iteration

```javascript
// component.js
get processedCategories() {
    return this.categories.map(category => ({
        ...category,
        items: category.items.map(item => ({
            ...item,
            compositeKey: `${category.id}-${item.id}`
        }))
    }));
}
```

```html
<!-- component.html -->
<template>
    <template for:each={processedCategories} for:item="category">
        <div key={category.id}>
            <h3>{category.name}</h3>
            <template for:each={category.items} for:item="item">
                <p key={item.compositeKey}>{item.name}</p>
            </template>
        </div>
    </template>
</template>
```

---

## 7. Conditional Rendering Issues

### ❌ BAD: if:true on Non-Boolean Values

```html
<!-- LLM assumes truthy/falsy works like JS - it doesn't always -->
<template>
    <!-- String 'false' is truthy! -->
    <template if:true={stringValue}>
        <p>Shown even for 'false' string!</p>
    </template>

    <!-- 0 might not behave as expected -->
    <template if:true={count}>
        <p>Count: {count}</p>
    </template>
</template>
```

### ✅ GOOD: Explicit Boolean Conversion

```javascript
// component.js
get hasStringValue() {
    return Boolean(this.stringValue) && this.stringValue !== 'false';
}

get hasCount() {
    return this.count !== null && this.count !== undefined && this.count !== 0;
}
```

```html
<!-- component.html -->
<template>
    <template if:true={hasStringValue}>
        <p>Has value</p>
    </template>

    <template if:true={hasCount}>
        <p>Count: {count}</p>
    </template>
</template>
```

### ❌ BAD: Multiple Conditions Without Else

```html
<!-- Verbose and error-prone -->
<template>
    <template if:true={isLoading}>
        <lightning-spinner></lightning-spinner>
    </template>
    <template if:true={hasError}>
        <p>Error occurred</p>
    </template>
    <template if:true={hasData}>
        <p>Data loaded</p>
    </template>
</template>
```

### ✅ GOOD: Use a State Getter

```javascript
// component.js
get viewState() {
    if (this.isLoading) return 'loading';
    if (this.error) return 'error';
    if (this.data) return 'success';
    return 'empty';
}

get isLoadingState() { return this.viewState === 'loading'; }
get isErrorState() { return this.viewState === 'error'; }
get isSuccessState() { return this.viewState === 'success'; }
get isEmptyState() { return this.viewState === 'empty'; }
```

```html
<!-- component.html -->
<template>
    <template if:true={isLoadingState}>
        <lightning-spinner></lightning-spinner>
    </template>
    <template if:true={isErrorState}>
        <c-error-display error={error}></c-error-display>
    </template>
    <template if:true={isSuccessState}>
        <c-data-display data={data}></c-data-display>
    </template>
    <template if:true={isEmptyState}>
        <c-empty-state></c-empty-state>
    </template>
</template>
```

---

## 8. Slot and Composition Errors

### ❌ BAD: Named Slot with Wrong Syntax

```html
<!-- LLM uses Vue/React slot syntax -->
<template>
    <!-- Wrong: Vue syntax -->
    <c-card>
        <template v-slot:header>Header</template>
    </c-card>

    <!-- Wrong: React children syntax -->
    <c-card header="Header Content">
        Body Content
    </c-card>
</template>
```

### ✅ GOOD: LWC Slot Syntax

```html
<!-- Parent component using slots -->
<template>
    <c-card>
        <span slot="header">Card Header</span>
        <p slot="body">Card body content</p>
        <button slot="footer">Action</button>
    </c-card>
</template>
```

```html
<!-- c-card component template -->
<template>
    <article class="slds-card">
        <header class="slds-card__header">
            <slot name="header"></slot>
        </header>
        <div class="slds-card__body">
            <slot name="body"></slot>
            <slot></slot> <!-- Default slot -->
        </div>
        <footer class="slds-card__footer">
            <slot name="footer"></slot>
        </footer>
    </article>
</template>
```

---

## 9. Data Binding Mistakes

### ❌ BAD: Two-Way Binding Syntax

```html
<!-- LLM uses Angular/Vue two-way binding - doesn't exist in LWC -->
<template>
    <input [(ngModel)]="name">  <!-- Angular -->
    <input v-model="name">       <!-- Vue -->
    <input bind:value={name}>    <!-- Svelte-ish -->
</template>
```

### ✅ GOOD: One-Way Binding with Event Handler

```html
<!-- component.html -->
<template>
    <lightning-input
        label="Name"
        value={name}
        onchange={handleNameChange}>
    </lightning-input>

    <!-- Or standard HTML input -->
    <input
        type="text"
        value={name}
        onchange={handleInputChange}
        oninput={handleInputChange}>
</template>
```

```javascript
// component.js
name = '';

handleNameChange(event) {
    this.name = event.detail.value;  // lightning-input uses detail.value
}

handleInputChange(event) {
    this.name = event.target.value;  // standard input uses target.value
}
```

### ❌ BAD: Direct Property Mutation in Template

```html
<!-- Cannot mutate in template -->
<template>
    <button onclick={count++}>Increment</button>
</template>
```

### ✅ GOOD: Mutate in Handler

```javascript
// component.js
count = 0;

handleIncrement() {
    this.count++;
}
```

```html
<!-- component.html -->
<template>
    <button onclick={handleIncrement}>Increment ({count})</button>
</template>
```

---

## 10. Style and Class Binding

### ❌ BAD: Dynamic Styles in Template

```html
<!-- LLM uses React/Vue style binding - doesn't work in LWC -->
<template>
    <div style="color: {textColor}; font-size: {fontSize}px">
        Content
    </div>

    <div style={{ color: textColor, fontSize: fontSize + 'px' }}>
        Content
    </div>
</template>
```

### ✅ GOOD: CSS Custom Properties (Recommended)

```javascript
// component.js
@api textColor = 'blue';
@api fontSize = 14;

renderedCallback() {
    this.template.host.style.setProperty('--text-color', this.textColor);
    this.template.host.style.setProperty('--font-size', `${this.fontSize}px`);
}
```

```css
/* component.css */
.dynamic-text {
    color: var(--text-color, black);
    font-size: var(--font-size, 14px);
}
```

```html
<!-- component.html -->
<template>
    <div class="dynamic-text">Content</div>
</template>
```

### ✅ GOOD: Computed Style String (When Necessary)

```javascript
// component.js
get dynamicStyle() {
    return `color: ${this.textColor}; font-size: ${this.fontSize}px;`;
}
```

```html
<!-- component.html -->
<template>
    <div style={dynamicStyle}>Content</div>
</template>
```

### ❌ BAD: Dynamic Class with Expression

```html
<!-- DOES NOT WORK -->
<template>
    <div class="base {isActive ? 'active' : ''}">Content</div>
    <div class={`base ${isActive ? 'active' : ''}`}>Content</div>
</template>
```

### ✅ GOOD: Computed Class String

```javascript
// component.js
get containerClass() {
    return `base ${this.isActive ? 'active' : ''} ${this.isHighlighted ? 'highlighted' : ''}`.trim();
}
```

```html
<!-- component.html -->
<template>
    <div class={containerClass}>Content</div>
</template>
```

---

## Quick Reference: Template Rules

| What You Want | Wrong (Other Frameworks) | Right (LWC) |
|---------------|-------------------------|-------------|
| Arithmetic | `{a + b}` | Getter: `get sum() { return a + b; }` |
| String concat | `{a + ' ' + b}` | Getter with template literal |
| Ternary | `{x ? a : b}` | Getter or if:true/if:false |
| Method call | `{items.length}` | Getter: `get count() { return items.length; }` |
| Comparison | `if:true={x > 5}` | Getter: `get isBig() { return x > 5; }` |
| Logical AND | `if:true={a && b}` | Getter: `get both() { return a && b; }` |
| Negation | `if:true={!x}` | `if:false={x}` or getter |
| Object literal | `config={{ key: val }}` | Class property |
| Event args | `onclick={fn(x)}` | Use data attributes |
| Two-way bind | `value={name}` auto-update | `value={name}` + `onchange` |

---

## Validation Checklist

Before deploying LWC templates, verify:

- [ ] No arithmetic operations (`+`, `-`, `*`, `/`)
- [ ] No ternary operators (`? :`)
- [ ] No object/array literals (`{}`, `[]`)
- [ ] No method calls (`.length`, `.toUpperCase()`)
- [ ] No comparisons (`>`, `<`, `===`, `!==`)
- [ ] No logical operators (`&&`, `||`, `!`)
- [ ] All iterations have unique `key` attributes
- [ ] Event handlers don't have inline arguments
- [ ] Dynamic styles use CSS custom properties or computed strings

---

## Reference

- **LWC Best Practices**: See `references/lwc-best-practices.md`
- **Component Patterns**: See `references/component-patterns.md`
- **Source**: [Salesforce Diaries - LLM Mistakes](https://salesforcediaries.com/2026/01/16/llm-mistakes-in-apex-lwc-salesforce-code-generation-rules/)
