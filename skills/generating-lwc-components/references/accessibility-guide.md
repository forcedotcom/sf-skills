<!-- Parent: generating-lwc-components/SKILL.md -->
# Accessibility Guide for LWC

Comprehensive guide to building WCAG 2.1 AA compliant Lightning Web Components.

---

## Table of Contents

1. [Accessibility Standards](#accessibility-standards)
2. [Semantic HTML](#semantic-html)
3. [ARIA Attributes](#aria-attributes)
4. [Keyboard Navigation](#keyboard-navigation)
5. [Focus Management](#focus-management)
6. [Color and Contrast](#color-and-contrast)
7. [Screen Reader Support](#screen-reader-support)
8. [Live Regions](#live-regions)
9. [Form Accessibility](#form-accessibility)
10. [Common Patterns](#common-patterns)
11. [Testing](#testing)
12. [Tools and Resources](#tools-and-resources)

---

## Accessibility Standards

### WCAG 2.1 AA Compliance

All Lightning Web Components should meet WCAG 2.1 Level AA standards.

| Principle | Description |
|-----------|-------------|
| **Perceivable** | Information must be presentable to users in ways they can perceive |
| **Operable** | UI components must be operable (keyboard, mouse, voice) |
| **Understandable** | Information and UI must be understandable |
| **Robust** | Content must work with assistive technologies |

### Key Requirements

| Requirement | Standard | Implementation |
|-------------|----------|----------------|
| **Color contrast** | 4.5:1 for normal text, 3:1 for large text | Use SLDS color tokens |
| **Keyboard navigation** | All interactive elements accessible via keyboard | Tab order, Enter/Space triggers |
| **Screen reader support** | ARIA labels, roles, live regions | Proper semantic HTML + ARIA |
| **Focus indicators** | Visible focus state | Use SLDS focus utilities |
| **Alternative text** | All images have alt text | `alt` attribute on images |

---

## Semantic HTML

### Use Proper HTML Elements

```html
<!-- BAD: Non-semantic markup -->
<div onclick={handleClick}>Click me</div>

<!-- GOOD: Semantic button -->
<button onclick={handleClick}>Click me</button>
```

### Headings Hierarchy

```html
<!-- BAD: Skipping heading levels -->
<h1>Page Title</h1>
<h3>Subsection</h3> <!-- Skipped h2 -->

<!-- GOOD: Logical heading structure -->
<h1>Page Title</h1>
<h2>Main Section</h2>
<h3>Subsection</h3>
```

### Landmarks

```html
<template>
    <header class="slds-page-header">
        <h1>Dashboard</h1>
    </header>

    <nav aria-label="Primary navigation">
        <ul>
            <li><a href="#home">Home</a></li>
            <li><a href="#accounts">Accounts</a></li>
        </ul>
    </nav>

    <main>
        <article>
            <h2>Account Details</h2>
            <!-- Content -->
        </article>
    </main>

    <aside aria-label="Related information">
        <!-- Sidebar content -->
    </aside>

    <footer>
        <p>Copyright 2025</p>
    </footer>
</template>
```

---

## ARIA Attributes

### ARIA Labels

```html
<!-- Icon button without visible text -->
<button aria-label="Delete record" onclick={handleDelete}>
    <lightning-icon icon-name="utility:delete" size="small"></lightning-icon>
</button>

<!-- Form field with additional context -->
<lightning-input
    label="Phone"
    aria-describedby="phone-help"
    value={phone}
    onchange={handlePhoneChange}>
</lightning-input>
<div id="phone-help" class="slds-text-color_weak">
    Enter phone number with country code
</div>
```

### ARIA Roles

```html
<!-- Custom list -->
<div role="list">
    <div role="listitem">Item 1</div>
    <div role="listitem">Item 2</div>
</div>

<!-- Alert message -->
<div role="alert" class="slds-notify slds-notify_alert">
    <span class="slds-assistive-text">Error</span>
    <p>Form validation failed</p>
</div>

<!-- Dialog/Modal -->
<div role="dialog"
     aria-modal="true"
     aria-labelledby="modal-heading"
     aria-describedby="modal-description">
    <h2 id="modal-heading">Confirm Action</h2>
    <p id="modal-description">Are you sure you want to delete this record?</p>
</div>
```

### ARIA States

```html
<!-- Expandable section -->
<button
    aria-expanded={isExpanded}
    aria-controls="details-section"
    onclick={toggleExpanded}>
    Show Details
</button>
<div id="details-section" class={sectionClass}>
    <!-- Details content -->
</div>

<!-- Loading state -->
<div aria-busy={isLoading}>
    <template lwc:if={isLoading}>
        <lightning-spinner alternative-text="Loading data"></lightning-spinner>
    </template>
    <template lwc:else>
        <!-- Content -->
    </template>
</div>

<!-- Required field -->
<lightning-input
    label="Name"
    required
    aria-required="true"
    value={name}>
</lightning-input>
```

---

## Keyboard Navigation

### Tab Order

```html
<!-- Natural tab order -->
<form>
    <lightning-input label="First Name" tabindex="0"></lightning-input>
    <lightning-input label="Last Name" tabindex="0"></lightning-input>
    <lightning-button label="Submit" tabindex="0"></lightning-button>
</form>

<!-- Skip to main content link -->
<a href="#main-content" class="slds-assistive-text slds-assistive-text_focus">
    Skip to main content
</a>
<main id="main-content">
    <!-- Content -->
</main>
```

### Keyboard Event Handlers

```javascript
// accountCard.js
export default class AccountCard extends LightningElement {
    handleKeyDown(event) {
        // Enter or Space activates
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this.handleSelect();
        }

        // Arrow navigation
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.focusNextItem();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.focusPreviousItem();
        }

        // Escape closes
        if (event.key === 'Escape') {
            this.handleClose();
        }
    }

    focusNextItem() {
        const items = this.template.querySelectorAll('[role="listitem"]');
        const currentIndex = Array.from(items).indexOf(document.activeElement);
        const nextIndex = (currentIndex + 1) % items.length;
        items[nextIndex].focus();
    }

    focusPreviousItem() {
        const items = this.template.querySelectorAll('[role="listitem"]');
        const currentIndex = Array.from(items).indexOf(document.activeElement);
        const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
        items[prevIndex].focus();
    }
}
```

```html
<!-- accountCard.html -->
<template>
    <div role="list">
        <template for:each={accounts} for:item="account">
            <div key={account.Id}
                 role="listitem"
                 tabindex="0"
                 onkeydown={handleKeyDown}
                 onclick={handleSelect}
                 data-id={account.Id}>
                {account.Name}
            </div>
        </template>
    </div>
</template>
```

---

## Focus Management

### Focus Trap in Modals

```javascript
// composableModal.js
export default class ComposableModal extends LightningElement {
    _focusableElements = [];
    _isOpen = false;

    @api
    toggleModal() {
        this._isOpen = !this._isOpen;

        if (this._isOpen) {
            // Capture focusable elements
            this._focusableElements = this.getFocusableElements();

            // Focus first element
            requestAnimationFrame(() => {
                this._focusableElements[0]?.focus();
            });

            // Add keyboard listener
            window.addEventListener('keydown', this._handleKeyDown);

            // Store previous focus
            this._previousFocus = document.activeElement;
        } else {
            // Remove keyboard listener
            window.removeEventListener('keydown', this._handleKeyDown);

            // Restore focus
            this._previousFocus?.focus();
        }
    }

    getFocusableElements() {
        const selector = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])'
        ].join(',');

        return Array.from(this.template.querySelectorAll(selector));
    }

    _handleKeyDown = (event) => {
        if (event.key === 'Tab') {
            this.trapFocus(event);
        } else if (event.key === 'Escape') {
            this.toggleModal();
        }
    }

    trapFocus(event) {
        const firstElement = this._focusableElements[0];
        const lastElement = this._focusableElements[this._focusableElements.length - 1];
        const activeElement = this.template.activeElement;

        if (event.shiftKey) {
            // Shift+Tab: Moving backward
            if (activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            }
        } else {
            // Tab: Moving forward
            if (activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    }

    disconnectedCallback() {
        window.removeEventListener('keydown', this._handleKeyDown);
    }
}
```

### Managing Focus After Actions

```javascript
handleDelete(event) {
    const itemId = event.target.dataset.id;
    const itemIndex = this.items.findIndex(item => item.Id === itemId);

    // Delete item
    this.items = this.items.filter(item => item.Id !== itemId);

    // Focus next item or previous if last item deleted
    requestAnimationFrame(() => {
        const focusIndex = itemIndex < this.items.length ? itemIndex : itemIndex - 1;
        if (focusIndex >= 0) {
            const nextItem = this.template.querySelector(`[data-id="${this.items[focusIndex].Id}"]`);
            nextItem?.focus();
        }
    });
}
```

---

## Color and Contrast

### Use SLDS Color Tokens

```css
/* BAD: Hardcoded colors */
.my-component {
    color: #333333;
    background-color: #ffffff;
    border-color: #dddddd;
}

/* GOOD: SLDS tokens with proper contrast */
.my-component {
    color: var(--slds-g-color-on-surface, #181818);
    background-color: var(--slds-g-color-surface-container-1, #ffffff);
    border-color: var(--slds-g-color-border-1, #c9c9c9);
}
```

### Testing Contrast

```html
<!-- Text: 4.5:1 minimum contrast ratio -->
<p class="slds-text-body_regular">Regular body text</p>

<!-- Large text (18pt+): 3:1 minimum -->
<h1 class="slds-text-heading_large">Large heading</h1>

<!-- Links: Must be distinguishable from surrounding text -->
<p>
    Visit our <a href="/help" class="slds-text-link">help center</a> for support.
</p>
```

### Color Independence

```html
<!-- BAD: Relies only on color to convey status -->
<span class="text-red">Error</span>

<!-- GOOD: Uses icon + text + color -->
<span class="slds-text-color_error">
    <lightning-icon icon-name="utility:error" size="x-small"></lightning-icon>
    Error
</span>

<!-- GOOD: Status indicators with patterns -->
<div class="slds-badge slds-theme_error">
    <lightning-icon icon-name="utility:close" size="xx-small"></lightning-icon>
    Failed
</div>
```

---

## Screen Reader Support

### Assistive Text

```html
<!-- Hidden text for screen readers -->
<span class="slds-assistive-text">Required field</span>
<lightning-input label="Email" required value={email}></lightning-input>

<!-- Button with icon only -->
<button aria-label="Edit record">
    <lightning-icon icon-name="utility:edit" size="small"></lightning-icon>
    <span class="slds-assistive-text">Edit</span>
</button>

<!-- Loading state announcement -->
<template lwc:if={isLoading}>
    <span class="slds-assistive-text">Loading data, please wait</span>
    <lightning-spinner size="small"></lightning-spinner>
</template>
```

### Image Alternative Text

```html
<!-- Decorative images (no alt needed, hide from screen readers) -->
<img src="decorative-icon.png" alt="" role="presentation">

<!-- Informative images (descriptive alt text) -->
<img src="chart.png" alt="Sales trend showing 15% increase over last quarter">

<!-- Functional images (describe action) -->
<a href="/profile">
    <img src="user-avatar.png" alt="View your profile">
</a>
```

---

## Live Regions

### ARIA Live Regions

```javascript
// notificationComponent.js
export default class NotificationComponent extends LightningElement {
    @track messages = [];

    addMessage(message, type = 'info') {
        const id = Date.now();
        this.messages = [...this.messages, { id, message, type }];

        // Auto-remove after 5 seconds
        setTimeout(() => {
            this.messages = this.messages.filter(m => m.id !== id);
        }, 5000);
    }
}
```

```html
<!-- notificationComponent.html -->
<template>
    <!-- Polite: Announced after current speech -->
    <div aria-live="polite" aria-atomic="true" class="slds-assistive-text">
        <template for:each={messages} for:item="msg">
            <p key={msg.id}>{msg.message}</p>
        </template>
    </div>

    <!-- Visual notifications -->
    <div class="slds-notify-container">
        <template for:each={messages} for:item="msg">
            <div key={msg.id} class={msg.type} role="status">
                <p>{msg.message}</p>
            </div>
        </template>
    </div>
</template>
```

### Assertive vs Polite

```html
<!-- Polite: Non-urgent updates (search results, status changes) -->
<div aria-live="polite" class="slds-assistive-text">
    {searchResultsCount} results found
</div>

<!-- Assertive: Urgent messages (errors, warnings) -->
<div aria-live="assertive" role="alert" class="slds-notify slds-notify_alert">
    <span class="slds-assistive-text">Error</span>
    Form submission failed. Please correct the errors and try again.
</div>
```

---

## Form Accessibility

### Accessible Form Fields

```html
<template>
    <form onsubmit={handleSubmit}>
        <!-- Required field with validation -->
        <lightning-input
            label="Email"
            type="email"
            name="email"
            required
            value={email}
            onchange={handleEmailChange}
            message-when-value-missing="Email is required"
            message-when-bad-input="Please enter a valid email">
        </lightning-input>

        <!-- Field with help text -->
        <lightning-input
            label="Phone"
            type="tel"
            value={phone}
            field-level-help="Enter phone number with country code"
            aria-describedby="phone-help"
            onchange={handlePhoneChange}>
        </lightning-input>
        <div id="phone-help" class="slds-text-color_weak slds-m-top_xx-small">
            Format: +1 (555) 555-5555
        </div>

        <!-- Error state -->
        <template lwc:if={errors.industry}>
            <lightning-input
                label="Industry"
                value={industry}
                variant="label-hidden"
                aria-invalid="true"
                aria-describedby="industry-error"
                class="slds-has-error">
            </lightning-input>
            <div id="industry-error" class="slds-form-element__help" role="alert">
                {errors.industry}
            </div>
        </template>

        <!-- Submit button -->
        <lightning-button
            type="submit"
            label="Save"
            variant="brand"
            disabled={isSubmitting}>
        </lightning-button>
    </form>
</template>
```

### Fieldset and Legend

```html
<!-- Radio button group -->
<fieldset class="slds-form-element">
    <legend class="slds-form-element__legend slds-form-element__label">
        Contact Method <abbr class="slds-required" title="required">*</abbr>
    </legend>
    <div class="slds-form-element__control">
        <lightning-radio-group
            name="contactMethod"
            label="Contact Method"
            options={contactOptions}
            value={selectedMethod}
            onchange={handleMethodChange}
            variant="label-hidden"
            required>
        </lightning-radio-group>
    </div>
</fieldset>
```

---

## Common Patterns

### Accessible Tabs

```javascript
// tabsComponent.js
export default class TabsComponent extends LightningElement {
    @track activeTab = 'tab1';

    handleTabKeyDown(event) {
        const tabs = Array.from(this.template.querySelectorAll('[role="tab"]'));
        const currentIndex = tabs.indexOf(event.target);

        let nextIndex;
        if (event.key === 'ArrowRight') {
            nextIndex = (currentIndex + 1) % tabs.length;
        } else if (event.key === 'ArrowLeft') {
            nextIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
        } else if (event.key === 'Home') {
            nextIndex = 0;
        } else if (event.key === 'End') {
            nextIndex = tabs.length - 1;
        }

        if (nextIndex !== undefined) {
            event.preventDefault();
            tabs[nextIndex].focus();
            this.activeTab = tabs[nextIndex].dataset.tab;
        }
    }

    handleTabClick(event) {
        this.activeTab = event.currentTarget.dataset.tab;
    }
}
```

```html
<!-- tabsComponent.html -->
<template>
    <div class="slds-tabs_default">
        <ul role="tablist" class="slds-tabs_default__nav">
            <li class="slds-tabs_default__item" role="presentation">
                <a role="tab"
                   tabindex={tab1Tabindex}
                   aria-selected={isTab1Active}
                   aria-controls="tab1-panel"
                   data-tab="tab1"
                   onclick={handleTabClick}
                   onkeydown={handleTabKeyDown}>
                    Tab 1
                </a>
            </li>
            <li class="slds-tabs_default__item" role="presentation">
                <a role="tab"
                   tabindex={tab2Tabindex}
                   aria-selected={isTab2Active}
                   aria-controls="tab2-panel"
                   data-tab="tab2"
                   onclick={handleTabClick}
                   onkeydown={handleTabKeyDown}>
                    Tab 2
                </a>
            </li>
        </ul>

        <div id="tab1-panel"
             role="tabpanel"
             aria-labelledby="tab1"
             class={tab1PanelClass}>
            <!-- Tab 1 content -->
        </div>

        <div id="tab2-panel"
             role="tabpanel"
             aria-labelledby="tab2"
             class={tab2PanelClass}>
            <!-- Tab 2 content -->
        </div>
    </div>
</template>
```

### Accessible Data Table

```html
<template>
    <table class="slds-table slds-table_bordered" role="grid">
        <thead>
            <tr>
                <th scope="col" role="columnheader">
                    <span class="slds-truncate">Account Name</span>
                </th>
                <th scope="col" role="columnheader">
                    <span class="slds-truncate">Industry</span>
                </th>
                <th scope="col" role="columnheader">
                    <span class="slds-truncate">Actions</span>
                </th>
            </tr>
        </thead>
        <tbody>
            <template for:each={accounts} for:item="account">
                <tr key={account.Id} role="row">
                    <th scope="row" role="gridcell">
                        <a href={account.link}>{account.Name}</a>
                    </th>
                    <td role="gridcell">
                        {account.Industry}
                    </td>
                    <td role="gridcell">
                        <button aria-label={account.editLabel}
                                data-id={account.Id}
                                onclick={handleEdit}>
                            <lightning-icon icon-name="utility:edit" size="x-small"></lightning-icon>
                        </button>
                    </td>
                </tr>
            </template>
        </tbody>
    </table>
</template>
```

---

## Testing

### Automated Testing

```javascript
// Jest accessibility tests
it('has proper ARIA labels', () => {
    const element = createElement('c-my-component', {
        is: MyComponent
    });
    document.body.appendChild(element);

    const button = element.shadowRoot.querySelector('button');
    expect(button.getAttribute('aria-label')).toBeTruthy();
});

it('manages focus when modal opens', async () => {
    const element = createElement('c-modal', { is: Modal });
    document.body.appendChild(element);

    element.openModal();
    await flushPromises();

    const firstFocusable = element.shadowRoot.querySelector('.focusable');
    expect(document.activeElement).toBe(firstFocusable);
});

it('announces status changes to screen readers', async () => {
    const element = createElement('c-notification', {
        is: Notification
    });
    document.body.appendChild(element);

    element.showMessage('Success');
    await flushPromises();

    const liveRegion = element.shadowRoot.querySelector('[aria-live]');
    expect(liveRegion.textContent).toContain('Success');
});
```

### Manual Testing Checklist

- [ ] Navigate entire component using only keyboard (Tab, Shift+Tab, Enter, Space, Arrows)
- [ ] Test with screen reader (NVDA, JAWS, VoiceOver)
- [ ] Verify color contrast ratios (4.5:1 minimum for text)
- [ ] Test at 200% zoom
- [ ] Verify focus indicators are visible
- [ ] Test with high contrast mode
- [ ] Verify all interactive elements have accessible names
- [ ] Test form validation announcements

---

## Tools and Resources

### Browser Extensions

| Tool | Purpose |
|------|---------|
| **axe DevTools** | Automated accessibility testing |
| **Lighthouse** | Built into Chrome DevTools, accessibility audit |
| **WAVE** | Visual accessibility evaluation |
| **Color Contrast Analyzer** | Check WCAG contrast compliance |

### Screen Readers

| Platform | Screen Reader |
|----------|---------------|
| Windows | NVDA (free), JAWS |
| macOS | VoiceOver (built-in) |
| iOS | VoiceOver (built-in) |
| Android | TalkBack (built-in) |

### Testing Commands

```bash
# Run axe accessibility tests
npm install --save-dev @axe-core/cli
axe https://your-app.lightning.force.com

# Lighthouse CLI
npm install -g lighthouse
lighthouse https://your-app.lightning.force.com --only-categories=accessibility
```

### Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [Salesforce Lightning Design System Accessibility](https://www.lightningdesignsystem.com/accessibility/overview/)
- [WebAIM Resources](https://webaim.org/resources/)

---

## Related Resources

- [component-patterns.md](component-patterns.md) - Implementation patterns
- [jest-testing.md](jest-testing.md) - Testing strategies
- [performance-guide.md](performance-guide.md) - Performance optimization
