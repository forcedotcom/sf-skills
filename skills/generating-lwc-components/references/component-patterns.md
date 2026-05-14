<!-- Parent: generating-lwc-components/SKILL.md -->
# LWC Component Patterns

Comprehensive code examples for common Lightning Web Component patterns.

---

## Table of Contents

1. [PICKLES Framework Details](#pickles-framework-details)
2. [Wire Service Patterns](#wire-service-patterns)
   - [Wire vs Imperative Apex Calls](#wire-vs-imperative-apex-calls)
3. [GraphQL Patterns](#graphql-patterns)
4. [Modal Component Pattern](#modal-component-pattern)
5. [Record Picker Pattern](#record-picker-pattern)
6. [Workspace API Pattern](#workspace-api-pattern)
7. [Parent-Child Communication](#parent-child-communication)
8. [Sibling Communication (via Parent)](#sibling-communication-via-parent)
9. [Navigation Patterns](#navigation-patterns)
10. [TypeScript Patterns](#typescript-patterns)
11. [Apex Controller Patterns](#apex-controller-patterns)

---

## PICKLES Framework Details

### P - Prototype

**Purpose**: Validate ideas early before full implementation.

| Action | Description |
|--------|-------------|
| Wireframe | Create high-level component sketches |
| Mock Data | Use sample data to test functionality |
| Stakeholder Review | Gather feedback before development |
| Separation of Concerns | Break into smaller functional pieces |

```javascript
// Mock data pattern for prototyping
const MOCK_ACCOUNTS = [
    { Id: '001MOCK001', Name: 'Acme Corp', Industry: 'Technology' },
    { Id: '001MOCK002', Name: 'Global Inc', Industry: 'Finance' }
];

export default class AccountPrototype extends LightningElement {
    accounts = MOCK_ACCOUNTS; // Replace with wire/Apex later
}
```

### I - Integrate

**Purpose**: Determine how components interact with data systems.

**Integration Checklist**:
- [ ] Implement error handling with clear user notifications
- [ ] Add loading spinners to prevent duplicate requests
- [ ] Use LDS for single-object operations (minimizes DML)
- [ ] Respect FLS and CRUD in Apex implementations
- [ ] Store `wiredResult` for `refreshApex()` support

### C - Composition

**Purpose**: Structure how LWCs nest and communicate.

**Best Practices**:
- Maintain shallow component hierarchies (max 3-4 levels)
- Single responsibility per component
- Clean up subscriptions in `disconnectedCallback()`
- Use custom events purposefully, not for every interaction

```javascript
// Parent-managed composition pattern
// parent.js
handleChildEvent(event) {
    this.selectedId = event.detail.id;
    // Update child via @api
    this.template.querySelector('c-child').selectedId = this.selectedId;
}
```

### K - Kinetics

**Purpose**: Manage user interaction and event responsiveness.

```javascript
// Debounce pattern for search
delayTimeout;

handleSearchChange(event) {
    const searchTerm = event.target.value;
    clearTimeout(this.delayTimeout);
    this.delayTimeout = setTimeout(() => {
        this.dispatchEvent(new CustomEvent('search', {
            detail: { searchTerm }
        }));
    }, 300);
}
```

### L - Libraries

**Purpose**: Leverage Salesforce-provided and platform tools.

**Recommended Platform Features**:

| API/Module | Use Case |
|------------|----------|
| `lightning/navigation` | Page/record navigation |
| `lightning/uiRecordApi` | LDS operations (getRecord, updateRecord) |
| `lightning/platformShowToastEvent` | User notifications |
| `lightning/modal` | Native modal dialogs |
| Base Components | Pre-built UI (button, input, datatable) |
| `lightning/refresh` | Dispatch refresh events |

**Avoid reinventing** what base components already provide!

### E - Execution

**Purpose**: Optimize performance and resource efficiency.

**Performance Checklist**:
- [ ] Lazy load with `if:true` / `lwc:if`
- [ ] Use `key` directive in iterations
- [ ] Cache computed values in getters
- [ ] Avoid property updates that trigger re-renders
- [ ] Use browser DevTools Performance tab

### S - Security

**Purpose**: Enforce access control and data protection.

```apex
// Secure Apex pattern
@AuraEnabled(cacheable=true)
public static List<Account> getAccounts(String searchTerm) {
    String searchKey = '%' + String.escapeSingleQuotes(searchTerm) + '%';
    return [
        SELECT Id, Name, Industry
        FROM Account
        WHERE Name LIKE :searchKey
        WITH SECURITY_ENFORCED
        LIMIT 50
    ];
}
```

---

## Wire Service Patterns

### Wire vs Imperative Apex Calls

LWC can interact with Apex in two ways: **@wire** (reactive/declarative) and **imperative calls** (manual/programmatic). Understanding when to use each is critical for building performant, maintainable components.

#### Quick Comparison

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    WIRE vs IMPERATIVE APEX CALLS                                     │
├──────────────────┬──────────────────────────────┬────────────────────────────────────┤
│    Aspect        │      Wire (@wire)            │      Imperative Calls              │
├──────────────────┼──────────────────────────────┼────────────────────────────────────┤
│ Execution        │ Automatic / Reactive         │ Manual / Programmatic              │
│ DML Operations   │ ❌ Read-Only                 │ ✅ Insert / Update / Delete        │
│ Data Updates     │ ✅ Auto on Parameter Change  │ ❌ Manual Refresh Required         │
│ Control          │ ⚠️ Low (framework decides)   │ ✅ Full (you decide when/how)      │
│ Error Handling   │ ✅ Framework Managed         │ ⚠️ Developer Managed               │
│ Supported Objects│ ⚠️ UI API Only               │ ✅ All Objects                     │
│ Caching          │ ✅ Built-in (cacheable=true) │ ❌ No automatic caching            │
└──────────────────┴──────────────────────────────┴────────────────────────────────────┘
```

#### Pros & Cons

| Wire (@wire) | Imperative Calls |
|--------------|------------------|
| ✅ Auto UI sync & caching | ✅ Supports DML & all objects |
| ✅ Less boilerplate code | ✅ Full control over timing |
| ✅ Reactive to parameter changes | ✅ Can handle complex logic |
| ❌ Read-only, limited objects | ❌ Manual handling, no auto refresh |
| ❌ Can't control execution timing | ❌ More error handling code needed |

#### When to Use Each

**Use Wire (@wire) when:**
- 📌 Read-only data display
- 📌 Auto-refresh UI when parameters change
- 📌 Stable parameters (recordId, filter values)
- 📌 Working with UI API supported objects

**Use Imperative Calls when:**
- 📌 User actions (clicks, form submissions)
- 📌 DML operations (Insert, Update, Delete)
- 📌 Dynamic parameters determined at runtime
- 📌 Custom objects or complex queries
- 📌 Need control over execution timing

#### Side-by-Side Code Examples

**Wire Example** - Data loads automatically when `selectedIndustry` changes:

```javascript
import { LightningElement, wire } from 'lwc';
import fetchAccounts from '@salesforce/apex/AccountController.fetchAccounts';

export default class WireExample extends LightningElement {
    selectedIndustry = 'Technology';
    accounts;
    error;

    // Automatically re-fetches when selectedIndustry changes
    @wire(fetchAccounts, { industry: '$selectedIndustry' })
    wiredAccounts({ data, error }) {
        if (data) {
            this.accounts = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.accounts = undefined;
        }
    }
}
```

**Imperative Example** - Data loads only when user triggers action:

```javascript
import { LightningElement } from 'lwc';
import fetchAccounts from '@salesforce/apex/AccountController.fetchAccounts';

export default class ImperativeExample extends LightningElement {
    selectedIndustry = 'Technology';
    accounts;
    error;
    isLoading = false;

    // Called explicitly when user clicks button or submits form
    async fetchAccounts() {
        this.isLoading = true;
        try {
            this.accounts = await fetchAccounts({
                industry: this.selectedIndustry
            });
            this.error = undefined;
        } catch (error) {
            this.error = error;
            this.accounts = undefined;
        } finally {
            this.isLoading = false;
        }
    }
}
```

#### Decision Tree

```
                    ┌─────────────────────────────┐
                    │   Need to modify data?      │
                    │   (Insert/Update/Delete)    │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────┴───────────────┐
                    │                             │
                   YES                            NO
                    │                             │
                    ▼                             ▼
         ┌─────────────────┐        ┌─────────────────────────┐
         │   IMPERATIVE    │        │  Should data auto-      │
         │   (Use await)   │        │  refresh on param       │
         └─────────────────┘        │  change?                │
                                    └───────────┬─────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    │                       │
                                   YES                      NO
                                    │                       │
                                    ▼                       ▼
                         ┌─────────────────┐     ┌─────────────────┐
                         │   @WIRE         │     │   IMPERATIVE    │
                         │   (Reactive)    │     │   (On-demand)   │
                         └─────────────────┘     └─────────────────┘
```

---

### 1. Basic Data Display (Wire Service)

```javascript
// accountCard.js
import { LightningElement, api, wire } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';

const FIELDS = [NAME_FIELD, INDUSTRY_FIELD];

export default class AccountCard extends LightningElement {
    @api recordId;

    @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
    account;

    get name() {
        return getFieldValue(this.account.data, NAME_FIELD);
    }

    get industry() {
        return getFieldValue(this.account.data, INDUSTRY_FIELD);
    }

    get isLoading() {
        return !this.account.data && !this.account.error;
    }
}
```

```html
<!-- accountCard.html -->
<template>
    <template lwc:if={isLoading}>
        <lightning-spinner alternative-text="Loading"></lightning-spinner>
    </template>
    <template lwc:if={account.data}>
        <div class="slds-box slds-theme_default">
            <h2 class="slds-text-heading_medium">{name}</h2>
            <p class="slds-text-color_weak">{industry}</p>
        </div>
    </template>
    <template lwc:if={account.error}>
        <p class="slds-text-color_error">{account.error.body.message}</p>
    </template>
</template>
```

### 2. Wire Service with Apex

```javascript
// contactList.js
import { LightningElement, api, wire } from 'lwc';
import getContacts from '@salesforce/apex/ContactController.getContacts';
import { refreshApex } from '@salesforce/apex';

export default class ContactList extends LightningElement {
    @api recordId;
    contacts;
    error;
    wiredContactsResult;

    @wire(getContacts, { accountId: '$recordId' })
    wiredContacts(result) {
        this.wiredContactsResult = result; // Store for refreshApex
        const { error, data } = result;
        if (data) {
            this.contacts = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.contacts = undefined;
        }
    }

    async handleRefresh() {
        await refreshApex(this.wiredContactsResult);
    }
}
```

---

## GraphQL Patterns

> **Module Note**: `lightning/graphql` supersedes `lightning/uiGraphQLApi` and provides newer features like mutations, optional fields, and dynamic query construction.

### GraphQL Query (Wire Adapter)

```javascript
// graphqlContacts.js
import { LightningElement, wire } from 'lwc';
import { gql, graphql } from 'lightning/graphql';

const CONTACTS_QUERY = gql`
    query ContactsQuery($first: Int, $after: String) {
        uiapi {
            query {
                Contact(first: $first, after: $after) {
                    edges {
                        node {
                            Id
                            Name { value }
                            Email { value }
                            Account {
                                Name { value }
                            }
                        }
                        cursor
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
    }
`;

export default class GraphqlContacts extends LightningElement {
    contacts;
    pageInfo;
    error;
    _cursor;

    @wire(graphql, {
        query: CONTACTS_QUERY,
        variables: '$queryVariables'
    })
    wiredContacts({ data, error }) {
        if (data) {
            const result = data.uiapi.query.Contact;
            this.contacts = result.edges.map(edge => ({
                id: edge.node.Id,
                name: edge.node.Name.value,
                email: edge.node.Email?.value,
                accountName: edge.node.Account?.Name?.value
            }));
            this.pageInfo = result.pageInfo;
        } else if (error) {
            this.error = error;
        }
    }

    get queryVariables() {
        return { first: 10, after: this._cursor };
    }

    loadMore() {
        if (this.pageInfo?.hasNextPage) {
            this._cursor = this.pageInfo.endCursor;
        }
    }
}
```

### GraphQL Mutations (Spring '26 - GA in API 66.0)

Mutations allow create, update, and delete operations via GraphQL. Use `executeMutation` for imperative operations.

```javascript
// graphqlAccountMutation.js
import { LightningElement, track } from 'lwc';
import { gql, executeMutation } from 'lightning/graphql';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

// Create mutation
const CREATE_ACCOUNT = gql`
    mutation CreateAccount($name: String!, $industry: String) {
        uiapi {
            AccountCreate(input: {
                Account: {
                    Name: $name
                    Industry: $industry
                }
            }) {
                Record {
                    Id
                    Name { value }
                    Industry { value }
                }
            }
        }
    }
`;

// Update mutation
const UPDATE_ACCOUNT = gql`
    mutation UpdateAccount($id: ID!, $name: String!) {
        uiapi {
            AccountUpdate(input: {
                Account: {
                    Id: $id
                    Name: $name
                }
            }) {
                Record {
                    Id
                    Name { value }
                }
            }
        }
    }
`;

// Delete mutation
const DELETE_ACCOUNT = gql`
    mutation DeleteAccount($id: ID!) {
        uiapi {
            AccountDelete(input: { Account: { Id: $id } }) {
                Id
            }
        }
    }
`;

export default class GraphqlAccountMutation extends LightningElement {
    @track accountName = '';
    @track industry = '';
    isLoading = false;

    handleNameChange(event) {
        this.accountName = event.target.value;
    }

    handleIndustryChange(event) {
        this.industry = event.target.value;
    }

    async handleCreate() {
        if (!this.accountName) return;

        this.isLoading = true;
        try {
            const result = await executeMutation(CREATE_ACCOUNT, {
                variables: {
                    name: this.accountName,
                    industry: this.industry || null
                }
            });

            const newRecord = result.data.uiapi.AccountCreate.Record;
            this.showToast('Success', `Account "${newRecord.Name.value}" created`, 'success');
            this.resetForm();
        } catch (error) {
            this.handleError(error);
        } finally {
            this.isLoading = false;
        }
    }

    async handleUpdate(accountId, newName) {
        try {
            const result = await executeMutation(UPDATE_ACCOUNT, {
                variables: { id: accountId, name: newName }
            });
            this.showToast('Success', 'Account updated', 'success');
            return result.data.uiapi.AccountUpdate.Record;
        } catch (error) {
            this.handleError(error);
        }
    }

    async handleDelete(accountId) {
        try {
            await executeMutation(DELETE_ACCOUNT, {
                variables: { id: accountId }
            });
            this.showToast('Success', 'Account deleted', 'success');
        } catch (error) {
            this.handleError(error);
        }
    }

    handleError(error) {
        const message = error.graphQLErrors
            ? error.graphQLErrors.map(e => e.message).join(', ')
            : error.message || 'Unknown error';
        this.showToast('Error', message, 'error');
    }

    showToast(title, message, variant) {
        this.dispatchEvent(new ShowToastEvent({ title, message, variant }));
    }

    resetForm() {
        this.accountName = '';
        this.industry = '';
    }
}
```

### GraphQL Mutation Operations

| Operation | Mutation Type | Notes |
|-----------|---------------|-------|
| **Create** | `{Object}Create` | Can request fields from newly created record |
| **Update** | `{Object}Update` | Cannot query fields in same request |
| **Delete** | `{Object}Delete` | Cannot query fields in same request |

### allOrNone Parameter

Control transaction behavior with `allOrNone` (default: `true`):

```javascript
const BATCH_CREATE = gql`
    mutation BatchCreate($allOrNone: Boolean = true) {
        uiapi(allOrNone: $allOrNone) {
            acc1: AccountCreate(input: { Account: { Name: "Account 1" } }) {
                Record { Id }
            }
            acc2: AccountCreate(input: { Account: { Name: "Account 2" } }) {
                Record { Id }
            }
        }
    }
`;

// If allOrNone=true: All rollback if any fails
// If allOrNone=false: Only failed operations rollback
```

---

## Modal Component Pattern

Based on [James Simone's composable modal pattern](https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/).

```javascript
// composableModal.js
import { LightningElement, api } from 'lwc';

const OUTER_MODAL_CLASS = 'outerModalContent';

export default class ComposableModal extends LightningElement {
    @api modalHeader;
    @api modalTagline;
    @api modalSaveHandler;

    _isOpen = false;
    _focusableElements = [];

    @api
    toggleModal() {
        this._isOpen = !this._isOpen;
        if (this._isOpen) {
            this._focusableElements = [...this.querySelectorAll('.focusable')];
            this._focusFirstElement();
            window.addEventListener('keyup', this._handleKeyUp);
        } else {
            window.removeEventListener('keyup', this._handleKeyUp);
        }
    }

    get modalAriaHidden() {
        return !this._isOpen;
    }

    get modalClass() {
        return this._isOpen
            ? 'slds-modal slds-visible slds-fade-in-open'
            : 'slds-modal slds-hidden';
    }

    get backdropClass() {
        return this._isOpen ? 'slds-backdrop slds-backdrop_open' : 'slds-backdrop';
    }

    _handleKeyUp = (event) => {
        if (event.code === 'Escape') {
            this.toggleModal();
        } else if (event.code === 'Tab') {
            this._handleTabNavigation(event);
        }
    }

    _handleTabNavigation(event) {
        // Focus trap logic - keep focus within modal
        const activeEl = this.template.activeElement;
        const lastIndex = this._focusableElements.length - 1;
        const currentIndex = this._focusableElements.indexOf(activeEl);

        if (event.shiftKey && currentIndex === 0) {
            this._focusableElements[lastIndex]?.focus();
        } else if (!event.shiftKey && currentIndex === lastIndex) {
            this._focusFirstElement();
        }
    }

    _focusFirstElement() {
        if (this._focusableElements.length > 0) {
            this._focusableElements[0].focus();
        }
    }

    handleBackdropClick(event) {
        if (event.target.classList.contains(OUTER_MODAL_CLASS)) {
            this.toggleModal();
        }
    }

    handleSave() {
        if (this.modalSaveHandler) {
            this.modalSaveHandler();
        }
        this.toggleModal();
    }

    disconnectedCallback() {
        window.removeEventListener('keyup', this._handleKeyUp);
    }
}
```

```html
<!-- composableModal.html -->
<template>
    <!-- Backdrop -->
    <div class={backdropClass}></div>

    <!-- Modal -->
    <div class={modalClass}
         role="dialog"
         aria-modal="true"
         aria-hidden={modalAriaHidden}
         aria-labelledby="modal-heading">

        <div class="slds-modal__container outerModalContent"
             onclick={handleBackdropClick}>

            <div class="slds-modal__content slds-p-around_medium">
                <!-- Header -->
                <template lwc:if={modalHeader}>
                    <h2 id="modal-heading" class="slds-text-heading_medium">
                        {modalHeader}
                    </h2>
                </template>
                <template lwc:if={modalTagline}>
                    <p class="slds-m-top_x-small slds-text-color_weak">
                        {modalTagline}
                    </p>
                </template>

                <!-- Slotted Content -->
                <div class="slds-m-top_medium">
                    <slot name="modalContent"></slot>
                </div>

                <!-- Footer -->
                <div class="slds-m-top_medium slds-text-align_right">
                    <lightning-button
                        label="Cancel"
                        onclick={toggleModal}
                        class="slds-m-right_x-small focusable">
                    </lightning-button>
                    <lightning-button
                        variant="brand"
                        label="Save"
                        onclick={handleSave}
                        class="focusable">
                    </lightning-button>
                </div>
            </div>
        </div>
    </div>

    <!-- Hidden background content -->
    <div aria-hidden={_isOpen}>
        <slot name="body"></slot>
    </div>
</template>
```

---

## Record Picker Pattern

```javascript
// recordPicker.js
import { LightningElement, api } from 'lwc';

export default class RecordPicker extends LightningElement {
    @api label = 'Select Record';
    @api objectApiName = 'Account';
    @api placeholder = 'Search...';
    @api required = false;
    @api multiSelect = false;

    _selectedIds = [];

    @api
    get value() {
        return this.multiSelect ? this._selectedIds : this._selectedIds[0];
    }

    set value(val) {
        this._selectedIds = Array.isArray(val) ? val : val ? [val] : [];
    }

    handleChange(event) {
        const recordId = event.detail.recordId;
        if (this.multiSelect) {
            if (!this._selectedIds.includes(recordId)) {
                this._selectedIds = [...this._selectedIds, recordId];
            }
        } else {
            this._selectedIds = recordId ? [recordId] : [];
        }

        this.dispatchEvent(new CustomEvent('select', {
            detail: {
                recordId: this.value,
                recordIds: this._selectedIds
            }
        }));
    }

    handleRemove(event) {
        const idToRemove = event.target.dataset.id;
        this._selectedIds = this._selectedIds.filter(id => id !== idToRemove);
        this.dispatchEvent(new CustomEvent('select', {
            detail: { recordIds: this._selectedIds }
        }));
    }
}
```

```html
<!-- recordPicker.html -->
<template>
    <lightning-record-picker
        label={label}
        placeholder={placeholder}
        object-api-name={objectApiName}
        onchange={handleChange}
        required={required}>
    </lightning-record-picker>

    <template lwc:if={multiSelect}>
        <div class="slds-m-top_x-small">
            <template for:each={_selectedIds} for:item="id">
                <lightning-pill
                    key={id}
                    label={id}
                    data-id={id}
                    onremove={handleRemove}>
                </lightning-pill>
            </template>
        </div>
    </template>
</template>
```

---

## Workspace API Pattern

```javascript
// workspaceTabManager.js
import { LightningElement, wire } from 'lwc';
import { IsConsoleNavigation, getFocusedTabInfo, openTab, closeTab,
         setTabLabel, setTabIcon, refreshTab } from 'lightning/platformWorkspaceApi';

export default class WorkspaceTabManager extends LightningElement {
    @wire(IsConsoleNavigation) isConsole;

    async openRecordTab(recordId, objectApiName) {
        if (!this.isConsole) return;

        await openTab({
            recordId,
            focus: true,
            icon: `standard:${objectApiName.toLowerCase()}`,
            label: 'Loading...'
        });
    }

    async openSubtab(parentTabId, recordId) {
        if (!this.isConsole) return;

        await openTab({
            parentTabId,
            recordId,
            focus: true
        });
    }

    async getCurrentTabInfo() {
        if (!this.isConsole) return null;
        return await getFocusedTabInfo();
    }

    async updateTabLabel(tabId, label) {
        if (!this.isConsole) return;
        await setTabLabel(tabId, label);
    }

    async updateTabIcon(tabId, iconName) {
        if (!this.isConsole) return;
        await setTabIcon(tabId, iconName);
    }

    async refreshCurrentTab() {
        if (!this.isConsole) return;
        const tabInfo = await getFocusedTabInfo();
        await refreshTab(tabInfo.tabId);
    }

    async closeCurrentTab() {
        if (!this.isConsole) return;
        const tabInfo = await getFocusedTabInfo();
        await closeTab(tabInfo.tabId);
    }
}
```

---

<a id="parent-child-communication"></a>

## Parent-Child Communication

```javascript
// parent.js
import { LightningElement } from 'lwc';

export default class Parent extends LightningElement {
    selectedAccountId;

    handleAccountSelected(event) {
        this.selectedAccountId = event.detail.accountId;
    }
}
```

```html
<!-- parent.html -->
<template>
    <c-account-list onaccountselected={handleAccountSelected}></c-account-list>
    <template lwc:if={selectedAccountId}>
        <c-account-detail account-id={selectedAccountId}></c-account-detail>
    </template>
</template>
```

```javascript
// child.js (accountList)
import { LightningElement } from 'lwc';

export default class AccountList extends LightningElement {
    handleRowAction(event) {
        const accountId = event.detail.row.Id;

        // Dispatch event to parent
        this.dispatchEvent(new CustomEvent('accountselected', {
            detail: { accountId },
            bubbles: true,
            composed: false // Don't cross shadow DOM boundaries
        }));
    }
}
```

---

## Sibling Communication (via Parent)

When two child components need to communicate but share the same parent, use the **parent as middleware**. This is the recommended pattern for master-detail UIs.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SIBLING COMMUNICATION FLOW                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                         ┌──────────┐                                │
│                         │  Parent  │  ← Manages state               │
│                         └────┬─────┘                                │
│                    ┌─────────┴─────────┐                            │
│                    │                   │                            │
│              CustomEvent          @api property                     │
│                (up)                 (down)                          │
│                    │                   │                            │
│              ┌─────┴─────┐       ┌─────┴─────┐                      │
│              │  Child A  │       │  Child B  │                      │
│              │  (List)   │       │  (Detail) │                      │
│              └───────────┘       └───────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**The flow**:
1. **Child A** dispatches a custom event (e.g., user selects an account)
2. **Parent** catches the event and updates its state
3. **Parent** passes data to **Child B** via `@api` property

### Complete Example: Account List → Account Detail

```javascript
// accountContainer.js - Parent orchestrates communication between siblings
import { LightningElement } from 'lwc';

export default class AccountContainer extends LightningElement {
    // State managed at parent level
    selectedAccountId;
    selectedAccountName;

    // Child A (accountList) fires this event
    handleAccountSelect(event) {
        this.selectedAccountId = event.detail.accountId;
        this.selectedAccountName = event.detail.accountName;
    }

    // Clear selection (triggered by Child B)
    handleClearSelection() {
        this.selectedAccountId = null;
        this.selectedAccountName = null;
    }

    get hasSelection() {
        return !!this.selectedAccountId;
    }
}
```

```html
<!-- accountContainer.html -->
<template>
    <div class="slds-grid slds-gutters">
        <!-- Child A: Account List -->
        <div class="slds-col slds-size_1-of-2">
            <c-account-list
                onaccountselect={handleAccountSelect}
                selected-id={selectedAccountId}>
            </c-account-list>
        </div>

        <!-- Child B: Account Detail (receives data via @api) -->
        <div class="slds-col slds-size_1-of-2">
            <template lwc:if={hasSelection}>
                <c-account-detail
                    account-id={selectedAccountId}
                    account-name={selectedAccountName}
                    onclearselection={handleClearSelection}>
                </c-account-detail>
            </template>
            <template lwc:else>
                <div class="slds-box slds-theme_shade">
                    Select an account to view details
                </div>
            </template>
        </div>
    </div>
</template>
```

```javascript
// accountList.js - Child A: Dispatches events UP to parent
import { LightningElement, api, wire } from 'lwc';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

export default class AccountList extends LightningElement {
    @api selectedId; // Highlight selected row (from parent)
    accounts;
    error;

    @wire(getAccounts)
    wiredAccounts({ data, error }) {
        if (data) {
            this.accounts = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.accounts = undefined;
        }
    }

    handleRowClick(event) {
        const accountId = event.currentTarget.dataset.id;
        const accountName = event.currentTarget.dataset.name;

        // Dispatch event to parent (not bubbles - parent listens directly)
        this.dispatchEvent(new CustomEvent('accountselect', {
            detail: { accountId, accountName }
        }));
    }

    // Computed: Check if row should be highlighted
    getRowClass(accountId) {
        return accountId === this.selectedId
            ? 'slds-item slds-is-selected'
            : 'slds-item';
    }
}
```

```javascript
// accountDetail.js - Child B: Receives data via @api from parent
import { LightningElement, api, wire } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';
import REVENUE_FIELD from '@salesforce/schema/Account.AnnualRevenue';

const FIELDS = [INDUSTRY_FIELD, REVENUE_FIELD];

export default class AccountDetail extends LightningElement {
    @api accountId;      // Received from parent
    @api accountName;    // Received from parent

    @wire(getRecord, { recordId: '$accountId', fields: FIELDS })
    account;

    get industry() {
        return getFieldValue(this.account.data, INDUSTRY_FIELD);
    }

    get revenue() {
        return getFieldValue(this.account.data, REVENUE_FIELD);
    }

    get isLoading() {
        return !this.account.data && !this.account.error;
    }

    handleClose() {
        // Dispatch event back to parent to clear selection
        this.dispatchEvent(new CustomEvent('clearselection'));
    }
}
```

### When to Use Sibling Pattern vs LMS

| Scenario | Sibling Pattern | LMS |
|----------|-----------------|-----|
| Components share same parent | ✅ Recommended | ❌ Overkill |
| State is simple (1-2 values) | ✅ | ❌ |
| Need bidirectional updates | ✅ | ✅ |
| Components in different DOM trees | ❌ | ✅ Required |
| Cross-framework (LWC ↔ Aura) | ❌ | ✅ Required |
| Many consumers need same data | ❌ Consider LMS | ✅ |
| Component hierarchy is deep (4+ levels) | ❌ Consider LMS | ✅ |

**Rule of thumb**: If components share a parent and data flow is simple, use sibling pattern. If components are "far apart" in the DOM or you need pub/sub semantics, use LMS.

---

## Navigation Patterns

```javascript
// navigator.js
import { LightningElement } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';

export default class Navigator extends NavigationMixin(LightningElement) {

    navigateToRecord(recordId, objectApiName = 'Account') {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId,
                objectApiName,
                actionName: 'view'
            }
        });
    }

    navigateToList(objectApiName, filterName = 'Recent') {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName,
                actionName: 'list'
            },
            state: { filterName }
        });
    }

    navigateToNewRecord(objectApiName, defaultValues = {}) {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName,
                actionName: 'new'
            },
            state: {
                defaultFieldValues: Object.entries(defaultValues)
                    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
                    .join(',')
            }
        });
    }

    navigateToRelatedList(recordId, relationshipApiName) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordRelationshipPage',
            attributes: {
                recordId,
                relationshipApiName,
                actionName: 'view'
            }
        });
    }

    navigateToNamedPage(pageName, params = {}) {
        this[NavigationMixin.Navigate]({
            type: 'standard__namedPage',
            attributes: {
                pageName
            },
            state: params
        });
    }
}
```

---

## TypeScript Patterns

### TypeScript Component Pattern

```typescript
// accountList.ts
import { LightningElement, api, wire, track } from 'lwc';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';
import ACCOUNT_NAME_FIELD from '@salesforce/schema/Account.Name';

// Define interfaces for type safety
interface AccountRecord {
    Id: string;
    Name: string;
    Industry?: string;
    AnnualRevenue?: number;
}

interface WireResult<T> {
    data?: T;
    error?: Error;
}

export default class AccountList extends LightningElement {
    // Typed @api properties
    @api recordId: string | undefined;

    @api
    get maxRecords(): number {
        return this._maxRecords;
    }
    set maxRecords(value: number) {
        this._maxRecords = value;
    }

    // Typed @track properties
    @track private _accounts: AccountRecord[] = [];
    @track private _error: string | null = null;

    private _maxRecords: number = 10;
    private _wiredResult: WireResult<AccountRecord[]> | undefined;

    // Typed wire service
    @wire(getAccounts, { maxRecords: '$maxRecords' })
    wiredAccounts(result: WireResult<AccountRecord[]>): void {
        this._wiredResult = result;
        const { data, error } = result;

        if (data) {
            this._accounts = data;
            this._error = null;
        } else if (error) {
            this._error = this.reduceErrors(error);
            this._accounts = [];
        }
    }

    // Typed getters
    get accounts(): AccountRecord[] {
        return this._accounts;
    }

    get hasAccounts(): boolean {
        return this._accounts.length > 0;
    }

    // Typed event handlers
    handleSelect(event: CustomEvent<{ accountId: string }>): void {
        const { accountId } = event.detail;
        this.dispatchEvent(new CustomEvent('accountselected', {
            detail: { accountId },
            bubbles: true,
            composed: true
        }));
    }

    // Typed utility methods
    private reduceErrors(error: Error | Error[]): string {
        const errors = Array.isArray(error) ? error : [error];
        return errors
            .filter((e): e is Error => e !== null)
            .map(e => e.message || 'Unknown error')
            .join('; ');
    }
}
```

### TypeScript Jest Test Pattern

```typescript
// accountList.test.ts
import { createElement, LightningElement } from 'lwc';
import AccountList from 'c/accountList';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

// Type definitions for tests
interface AccountRecord {
    Id: string;
    Name: string;
    Industry?: string;
}

// Mock Apex
jest.mock(
    '@salesforce/apex/AccountController.getAccounts',
    () => ({ default: jest.fn() }),
    { virtual: true }
);

const MOCK_ACCOUNTS: AccountRecord[] = [
    { Id: '001xx000003DGQ', Name: 'Acme Corp', Industry: 'Technology' }
];

describe('c-account-list', () => {
    let element: LightningElement & { maxRecords?: number };

    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('displays accounts after data loads', async () => {
        (getAccounts as jest.Mock).mockResolvedValue(MOCK_ACCOUNTS);

        element = createElement('c-account-list', { is: AccountList });
        document.body.appendChild(element);

        await Promise.resolve();

        const items = element.shadowRoot?.querySelectorAll('.slds-item');
        expect(items?.length).toBe(MOCK_ACCOUNTS.length);
    });
});
```

### TypeScript Features for LWC

| Feature | LWC Support | Notes |
|---------|-------------|-------|
| **Interface definitions** | ✅ | Define shapes for records, events, props |
| **Typed @api properties** | ✅ | Getter/setter patterns with types |
| **Typed @wire results** | ✅ | Generic `WireResult<T>` pattern |
| **Typed event handlers** | ✅ | `CustomEvent<T>` for event detail typing |
| **Private class fields** | ✅ | Use `private` keyword |
| **Strict null checking** | ✅ | Optional chaining `?.` and nullish coalescing `??` |

---

## Apex Controller Patterns

### Cacheable Methods (for @wire)

```apex
public with sharing class LwcController {

    @AuraEnabled(cacheable=true)
    public static List<Account> getAccounts(String searchTerm) {
        String searchKey = '%' + String.escapeSingleQuotes(searchTerm) + '%';
        return [
            SELECT Id, Name, Industry, AnnualRevenue
            FROM Account
            WHERE Name LIKE :searchKey
            WITH SECURITY_ENFORCED
            ORDER BY Name
            LIMIT 50
        ];
    }

    @AuraEnabled(cacheable=true)
    public static List<PicklistOption> getIndustryOptions() {
        List<PicklistOption> options = new List<PicklistOption>();
        Schema.DescribeFieldResult fieldResult =
            Account.Industry.getDescribe();
        for (Schema.PicklistEntry entry : fieldResult.getPicklistValues()) {
            if (entry.isActive()) {
                options.add(new PicklistOption(entry.getLabel(), entry.getValue()));
            }
        }
        return options;
    }

    public class PicklistOption {
        @AuraEnabled public String label;
        @AuraEnabled public String value;

        public PicklistOption(String label, String value) {
            this.label = label;
            this.value = value;
        }
    }
}
```

### Non-Cacheable Methods (for DML)

```apex
@AuraEnabled
public static Account createAccount(String accountJson) {
    Account acc = (Account) JSON.deserialize(accountJson, Account.class);

    // FLS check
    SObjectAccessDecision decision = Security.stripInaccessible(
        AccessType.CREATABLE,
        new List<Account>{ acc }
    );

    insert decision.getRecords();
    return (Account) decision.getRecords()[0];
}

@AuraEnabled
public static void deleteAccounts(List<Id> accountIds) {
    if (accountIds == null || accountIds.isEmpty()) {
        throw new AuraHandledException('No accounts to delete');
    }

    List<Account> toDelete = [
        SELECT Id FROM Account
        WHERE Id IN :accountIds
        WITH SECURITY_ENFORCED
    ];

    delete toDelete;
}
```

### Error Handling Pattern

```apex
@AuraEnabled
public static List<Contact> getContactsWithErrorHandling(Id accountId) {
    try {
        if (accountId == null) {
            throw new AuraHandledException('Account ID is required');
        }

        List<Contact> contacts = [
            SELECT Id, Name, Email, Phone
            FROM Contact
            WHERE AccountId = :accountId
            WITH SECURITY_ENFORCED
            ORDER BY Name
            LIMIT 100
        ];

        return contacts;
    } catch (Exception e) {
        throw new AuraHandledException('Error fetching contacts: ' + e.getMessage());
    }
}
```

---

## Related Resources

- [lms-guide.md](lms-guide.md) - Lightning Message Service deep dive
- [jest-testing.md](jest-testing.md) - Advanced testing patterns
- [accessibility-guide.md](accessibility-guide.md) - WCAG compliance
- [performance-guide.md](performance-guide.md) - Optimization techniques

---

## External References

- [PICKLES Framework](https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/) — David Picksley, Third Eye Consulting
- [LWC Recipes (GitHub)](https://github.com/trailheadapps/lwc-recipes)
- [James Simone - Composable Modal](https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/)
