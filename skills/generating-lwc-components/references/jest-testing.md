<!-- Parent: generating-lwc-components/SKILL.md -->
# Advanced Jest Testing for LWC

Comprehensive guide to testing Lightning Web Components using Jest, based on [James Simone's advanced testing patterns](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/).

---

## Table of Contents

1. [Setup](#setup)
2. [Core Testing Patterns](#core-testing-patterns)
3. [Render Cycle Management](#render-cycle-management)
4. [Mocking Strategies](#mocking-strategies)
5. [Testing Wire Services](#testing-wire-services)
6. [Testing Events](#testing-events)
7. [Testing Navigation](#testing-navigation)
8. [Testing LMS](#testing-lms)
9. [Testing GraphQL](#testing-graphql)
10. [Polyfills and Utilities](#polyfills-and-utilities)
11. [Best Practices](#best-practices)

---

## Setup

### Install Dependencies

```bash
# Install Jest and LWC testing tools
npm install --save-dev @salesforce/sfdx-lwc-jest jest

# Install additional utilities
npm install --save-dev @testing-library/jest-dom
```

### Jest Configuration

**File**: `jest.config.js`

```javascript
const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    roots: ['<rootDir>/force-app'],
    moduleNameMapper: {
        '^@salesforce/apex$': '<rootDir>/force-app/test/jest-mocks/apex',
        '^@salesforce/schema$': '<rootDir>/force-app/test/jest-mocks/schema',
        '^lightning/navigation$': '<rootDir>/force-app/test/jest-mocks/lightning/navigation',
        '^lightning/messageService$': '<rootDir>/force-app/test/jest-mocks/lightning/messageService'
    },
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
        '<rootDir>/.sfdx/',
        '<rootDir>/.agents/',
        '<rootDir>/.cursor/',
        '<rootDir>/.claude/',
        '<rootDir>/.pi/'
    ],
    coverageThreshold: {
        global: {
            branches: 80,
            functions: 80,
            lines: 80,
            statements: 80
        }
    }
};
```

`roots: ['<rootDir>/force-app']` keeps Jest focused on real Salesforce source. The ignore list adds defense-in-depth for agent/tool folders that may contain copied examples or generated artifacts.

Example test assets in `generating-lwc-components/assets/` ship with a `.example` suffix. Copy them into `force-app/main/default/lwc/<component>/__tests__/` and rename them to `*.test.js` or `*.test.ts` before running Jest.

### Setup File

**File**: `jest.setup.js`

```javascript
// ResizeObserver polyfill
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

// IntersectionObserver polyfill
if (!window.IntersectionObserver) {
    window.IntersectionObserver = class IntersectionObserver {
        constructor(callback) {
            this.callback = callback;
        }
        observe() {}
        unobserve() {}
        disconnect() {}
    };
}

// Custom matchers
expect.extend({
    toHaveClass(element, className) {
        const pass = element.classList.contains(className);
        return {
            pass,
            message: () => pass
                ? `Expected element NOT to have class "${className}"`
                : `Expected element to have class "${className}"`
        };
    }
});
```

---

## Core Testing Patterns

### Basic Test Structure

```javascript
import { createElement } from 'lwc';
import MyComponent from 'c/myComponent';

describe('c-my-component', () => {
    afterEach(() => {
        // Clean up DOM
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        // Clear all mocks
        jest.clearAllMocks();
    });

    it('renders correctly', () => {
        const element = createElement('c-my-component', {
            is: MyComponent
        });
        document.body.appendChild(element);

        expect(element.shadowRoot.querySelector('h1')).not.toBeNull();
    });
});
```

### DOM Cleanup Pattern

```javascript
describe('c-my-component', () => {
    let element;

    beforeEach(() => {
        element = createElement('c-my-component', { is: MyComponent });
        document.body.appendChild(element);
    });

    afterEach(() => {
        // CRITICAL: Prevent state bleed between tests
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('test case 1', () => {
        // Element is fresh for each test
    });

    it('test case 2', () => {
        // Element is fresh for each test
    });
});
```

---

## Render Cycle Management

### Render Cycle Helper

Based on [James Simone's pattern](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/).

```javascript
// testUtils.js
export const runRenderingLifecycle = async (reasons = ['render']) => {
    while (reasons.length > 0) {
        await Promise.resolve(reasons.pop());
    }
};

// Alias for brevity
export const flushPromises = () => runRenderingLifecycle();
```

### Usage in Tests

```javascript
import { runRenderingLifecycle, flushPromises } from './testUtils';

it('updates after property change', async () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    // Change property
    element.greeting = 'new value';

    // Wait for render cycle
    await runRenderingLifecycle(['property change', 'render']);

    // Assert
    const div = element.shadowRoot.querySelector('div');
    expect(div.textContent).toBe('new value');
});

it('handles async operation', async () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    // Trigger async action
    const button = element.shadowRoot.querySelector('button');
    button.click();

    // Flush all promises
    await flushPromises();

    // Assert
    expect(element.shadowRoot.querySelector('.result')).not.toBeNull();
});
```

---

## Mocking Strategies

### Mock Apex Imports

```javascript
// __mocks__/apex.js
export default function createApexTestWireAdapter() {
    return jest.fn();
}

// Component test
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

jest.mock(
    '@salesforce/apex/AccountController.getAccounts',
    () => ({ default: jest.fn() }),
    { virtual: true }
);

describe('c-account-list', () => {
    it('displays accounts', async () => {
        const MOCK_DATA = [
            { Id: '001xxx', Name: 'Acme' }
        ];

        getAccounts.mockResolvedValue(MOCK_DATA);

        const element = createElement('c-account-list', {
            is: AccountList
        });
        document.body.appendChild(element);

        await flushPromises();

        const items = element.shadowRoot.querySelectorAll('.account-item');
        expect(items.length).toBe(1);
    });
});
```

### Mock Schema Imports

```javascript
// __mocks__/schema.js
export default {
    'Account.Name': 'Name',
    'Account.Industry': 'Industry',
    'Contact.FirstName': 'FirstName'
};

// Component test
jest.mock('@salesforce/schema/Account.Name', () => 'Name', { virtual: true });
jest.mock('@salesforce/schema/Account.Industry', () => 'Industry', { virtual: true });
```

### Mock Platform Events

```javascript
// Mock ShowToastEvent
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

jest.mock('lightning/platformShowToastEvent', () => ({
    ShowToastEvent: jest.fn()
}), { virtual: true });

it('shows toast on success', () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    const handler = jest.fn();
    element.addEventListener('showtoast', handler);

    // Trigger action
    const button = element.shadowRoot.querySelector('button');
    button.click();

    // Assert toast was dispatched
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.title).toBe('Success');
});
```

---

## Testing Wire Services

### Test Wire Adapter

```javascript
import { createElement } from 'lwc';
import AccountCard from 'c/accountCard';
import { getRecord } from 'lightning/uiRecordApi';

// Emit data from wire
const mockGetRecord = require('lightning/uiRecordApi');

describe('c-account-card', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('displays account data', async () => {
        const element = createElement('c-account-card', {
            is: AccountCard
        });
        element.recordId = '001xxx000003DGQ';
        document.body.appendChild(element);

        // Emit mock data to wire
        mockGetRecord.emit({
            Id: '001xxx000003DGQ',
            fields: {
                Name: { value: 'Acme Corp' },
                Industry: { value: 'Technology' }
            }
        });

        await flushPromises();

        const name = element.shadowRoot.querySelector('.account-name');
        expect(name.textContent).toBe('Acme Corp');
    });

    it('displays error', async () => {
        const element = createElement('c-account-card', {
            is: AccountCard
        });
        element.recordId = '001xxx000003DGQ';
        document.body.appendChild(element);

        // Emit error to wire
        mockGetRecord.error();

        await flushPromises();

        const error = element.shadowRoot.querySelector('.error-message');
        expect(error).not.toBeNull();
    });
});
```

### Test Imperative Apex

```javascript
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

jest.mock(
    '@salesforce/apex/AccountController.getAccounts',
    () => ({ default: jest.fn() }),
    { virtual: true }
);

it('loads accounts imperatively', async () => {
    const MOCK_ACCOUNTS = [
        { Id: '001xxx', Name: 'Acme' }
    ];

    getAccounts.mockResolvedValue(MOCK_ACCOUNTS);

    const element = createElement('c-account-search', {
        is: AccountSearch
    });
    document.body.appendChild(element);

    // Trigger search
    const input = element.shadowRoot.querySelector('input');
    input.value = 'Acme';
    input.dispatchEvent(new Event('change'));

    await flushPromises();

    expect(getAccounts).toHaveBeenCalledWith({ searchTerm: 'Acme' });

    const results = element.shadowRoot.querySelectorAll('.account-item');
    expect(results.length).toBe(1);
});

it('handles apex error', async () => {
    getAccounts.mockRejectedValue(new Error('Network error'));

    const element = createElement('c-account-search', {
        is: AccountSearch
    });
    document.body.appendChild(element);

    const input = element.shadowRoot.querySelector('input');
    input.value = 'Test';
    input.dispatchEvent(new Event('change'));

    await flushPromises();

    const errorMsg = element.shadowRoot.querySelector('.error');
    expect(errorMsg.textContent).toContain('Network error');
});
```

---

## Testing Events

### Test Custom Events

```javascript
it('dispatches custom event', () => {
    const element = createElement('c-event-emitter', {
        is: EventEmitter
    });
    document.body.appendChild(element);

    const handler = jest.fn();
    element.addEventListener('itemselected', handler);

    // Trigger event
    const button = element.shadowRoot.querySelector('button');
    button.click();

    // Assert
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.id).toBe('001xxx');
});
```

### Test Event Bubbling

```javascript
it('bubbles event to parent', () => {
    const parent = createElement('c-parent', { is: Parent });
    document.body.appendChild(parent);

    const handler = jest.fn();
    parent.addEventListener('itemselected', handler);

    // Get child component
    const child = parent.shadowRoot.querySelector('c-child');
    const button = child.shadowRoot.querySelector('button');
    button.click();

    expect(handler).toHaveBeenCalled();
});
```

### Test Event Composition

```javascript
it('composes event across shadow DOM', () => {
    const element = createElement('c-composer', {
        is: Composer
    });
    document.body.appendChild(element);

    const handler = jest.fn();
    document.addEventListener('customevent', handler);

    // Trigger composed event
    const button = element.shadowRoot.querySelector('button');
    button.click();

    expect(handler).toHaveBeenCalled();
});
```

---

## Testing Navigation

### Mock Navigation Mixin

```javascript
// __mocks__/lightning/navigation.js
export const NavigationMixin = (Base) => {
    return class extends Base {
        [NavigationMixin.Navigate](pageReference, replace) {
            this._navigate = { pageReference, replace };
        }
    };
};

NavigationMixin.Navigate = Symbol('Navigate');

// Component test
import { NavigationMixin } from 'lightning/navigation';

it('navigates to record page', async () => {
    const element = createElement('c-navigator', {
        is: Navigator
    });
    document.body.appendChild(element);

    const button = element.shadowRoot.querySelector('button');
    button.click();

    await flushPromises();

    expect(element._navigate.pageReference.type).toBe('standard__recordPage');
    expect(element._navigate.pageReference.attributes.recordId).toBe('001xxx');
});
```

---

## Testing LMS

### Mock Message Service

```javascript
// __mocks__/lightning/messageService.js
export const publish = jest.fn();
export const subscribe = jest.fn();
export const unsubscribe = jest.fn();
export const MessageContext = Symbol('MessageContext');
export const APPLICATION_SCOPE = Symbol('APPLICATION_SCOPE');
```

### Test Publisher

```javascript
import { publish, MessageContext } from 'lightning/messageService';
import ACCOUNT_CHANNEL from '@salesforce/messageChannel/AccountSelected__c';

jest.mock('lightning/messageService');

it('publishes message on selection', () => {
    const element = createElement('c-publisher', {
        is: Publisher
    });
    document.body.appendChild(element);

    const button = element.shadowRoot.querySelector('button');
    button.click();

    expect(publish).toHaveBeenCalledWith(
        expect.anything(),
        ACCOUNT_CHANNEL,
        expect.objectContaining({ accountId: '001xxx' })
    );
});
```

### Test Subscriber

```javascript
import { subscribe, unsubscribe } from 'lightning/messageService';

jest.mock('lightning/messageService');

it('subscribes on connected', () => {
    const element = createElement('c-subscriber', {
        is: Subscriber
    });
    document.body.appendChild(element);

    expect(subscribe).toHaveBeenCalled();
});

it('unsubscribes on disconnected', () => {
    const element = createElement('c-subscriber', {
        is: Subscriber
    });
    document.body.appendChild(element);
    document.body.removeChild(element);

    expect(unsubscribe).toHaveBeenCalled();
});

it('handles incoming message', async () => {
    let messageHandler;
    subscribe.mockImplementation((context, channel, handler) => {
        messageHandler = handler;
        return { subscription: 'mock' };
    });

    const element = createElement('c-subscriber', {
        is: Subscriber
    });
    document.body.appendChild(element);

    // Simulate message
    messageHandler({ accountId: '001xxx', accountName: 'Acme' });

    await flushPromises();

    const name = element.shadowRoot.querySelector('.account-name');
    expect(name.textContent).toBe('Acme');
});
```

---

## Testing GraphQL

### Mock GraphQL Adapter

```javascript
import { graphql } from 'lightning/graphql';

// Mock graphql wire adapter
jest.mock('lightning/graphql', () => ({
    gql: jest.fn(query => query),
    graphql: jest.fn()
}), { virtual: true });

it('displays graphql query results', async () => {
    const element = createElement('c-graphql-component', {
        is: GraphqlComponent
    });
    document.body.appendChild(element);

    // Emit mock data
    const mockData = {
        uiapi: {
            query: {
                Contact: {
                    edges: [
                        { node: { Id: '003xxx', Name: { value: 'John Doe' } } }
                    ]
                }
            }
        }
    };

    graphql.emit({ data: mockData });

    await flushPromises();

    const contacts = element.shadowRoot.querySelectorAll('.contact-item');
    expect(contacts.length).toBe(1);
});
```

---

## Polyfills and Utilities

### ResizeObserver Polyfill

```javascript
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

### Proxy Unboxing (LWS Compatibility)

```javascript
// Lightning Web Security proxifies objects
// Unbox them for deep equality assertions

it('compares complex objects', () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    // Unbox proxied data
    const unboxedData = JSON.parse(JSON.stringify(element.data));

    expect(unboxedData).toEqual({
        accounts: [
            { Id: '001xxx', Name: 'Acme' }
        ]
    });
});
```

### Test Utilities Module

```javascript
// testUtils.js
export const runRenderingLifecycle = async (reasons = ['render']) => {
    while (reasons.length > 0) {
        await Promise.resolve(reasons.pop());
    }
};

export const flushPromises = () => runRenderingLifecycle();

export const queryAll = (element, selector) => {
    return Array.from(element.shadowRoot.querySelectorAll(selector));
};

export const query = (element, selector) => {
    return element.shadowRoot.querySelector(selector);
};

export const waitFor = async (condition, timeout = 3000) => {
    const start = Date.now();
    while (!condition()) {
        if (Date.now() - start > timeout) {
            throw new Error('waitFor timeout');
        }
        await flushPromises();
    }
};

// Usage
import { query, queryAll, waitFor } from './testUtils';

it('uses test utils', async () => {
    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    const button = query(element, 'button');
    button.click();

    await waitFor(() => query(element, '.result') !== null);

    const items = queryAll(element, '.item');
    expect(items.length).toBeGreaterThan(0);
});
```

---

## Best Practices

### 1. Always Clean Up DOM

```javascript
afterEach(() => {
    while (document.body.firstChild) {
        document.body.removeChild(document.body.firstChild);
    }
    jest.clearAllMocks();
});
```

### 2. Use Descriptive Test Names

```javascript
// BAD
it('works', () => { /* ... */ });

// GOOD
it('displays error message when apex call fails', () => { /* ... */ });
```

### 3. Test User Interactions

```javascript
it('filters list when search input changes', async () => {
    const element = createElement('c-searchable-list', {
        is: SearchableList
    });
    document.body.appendChild(element);

    const input = element.shadowRoot.querySelector('input');
    input.value = 'test';
    input.dispatchEvent(new Event('input'));

    await flushPromises();

    const items = element.shadowRoot.querySelectorAll('.list-item');
    expect(items.length).toBeLessThan(10); // Filtered results
});
```

### 4. Test Error States

```javascript
it('displays error when wire service fails', async () => {
    mockGetRecord.error({ message: 'Network error' });

    const element = createElement('c-example', { is: Example });
    document.body.appendChild(element);

    await flushPromises();

    const error = element.shadowRoot.querySelector('.error-message');
    expect(error.textContent).toContain('Network error');
});
```

### 5. Test Loading States

```javascript
it('shows spinner during data load', async () => {
    const element = createElement('c-async-component', {
        is: AsyncComponent
    });
    document.body.appendChild(element);

    // Before data loads
    let spinner = element.shadowRoot.querySelector('lightning-spinner');
    expect(spinner).not.toBeNull();

    // Emit data
    mockGetData.emit([{ Id: '001xxx' }]);
    await flushPromises();

    // After data loads
    spinner = element.shadowRoot.querySelector('lightning-spinner');
    expect(spinner).toBeNull();
});
```

### 6. Test Accessibility

```javascript
it('has proper ARIA labels', () => {
    const element = createElement('c-accessible', {
        is: Accessible
    });
    document.body.appendChild(element);

    const button = element.shadowRoot.querySelector('button');
    expect(button.getAttribute('aria-label')).toBe('Delete record');
});

it('manages focus correctly', async () => {
    const element = createElement('c-modal', { is: Modal });
    document.body.appendChild(element);

    element.openModal();
    await flushPromises();

    const firstFocusable = element.shadowRoot.querySelector('.focusable');
    expect(document.activeElement).toBe(firstFocusable);
});
```

### 7. Organize Tests by Feature

```javascript
describe('c-account-list', () => {
    describe('data loading', () => {
        it('displays accounts when data loads successfully');
        it('shows error when data load fails');
        it('shows spinner during loading');
    });

    describe('filtering', () => {
        it('filters by search term');
        it('filters by industry');
        it('clears filters');
    });

    describe('selection', () => {
        it('selects account on click');
        it('dispatches selection event');
        it('highlights selected account');
    });
});
```

---

## Complete Test Example

```javascript
import { createElement } from 'lwc';
import AccountList from 'c/accountList';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';
import { publish } from 'lightning/messageService';
import ACCOUNT_SELECTED from '@salesforce/messageChannel/AccountSelected__c';

// Mocks
jest.mock('@salesforce/apex/AccountController.getAccounts', () => ({
    default: jest.fn()
}), { virtual: true });

jest.mock('lightning/messageService');

const MOCK_ACCOUNTS = [
    { Id: '001xxx001', Name: 'Acme Corp', Industry: 'Technology' },
    { Id: '001xxx002', Name: 'Global Inc', Industry: 'Finance' }
];

const flushPromises = () => new Promise(resolve => setImmediate(resolve));

describe('c-account-list', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    describe('data loading', () => {
        it('displays accounts when loaded successfully', async () => {
            getAccounts.mockResolvedValue(MOCK_ACCOUNTS);

            const element = createElement('c-account-list', {
                is: AccountList
            });
            document.body.appendChild(element);

            await flushPromises();

            const items = element.shadowRoot.querySelectorAll('.account-item');
            expect(items.length).toBe(2);
            expect(items[0].textContent).toContain('Acme Corp');
        });

        it('displays error when fetch fails', async () => {
            getAccounts.mockRejectedValue(new Error('Network error'));

            const element = createElement('c-account-list', {
                is: AccountList
            });
            document.body.appendChild(element);

            await flushPromises();

            const error = element.shadowRoot.querySelector('.error-message');
            expect(error).not.toBeNull();
            expect(error.textContent).toContain('Network error');
        });
    });

    describe('selection', () => {
        it('publishes message when account selected', async () => {
            getAccounts.mockResolvedValue(MOCK_ACCOUNTS);

            const element = createElement('c-account-list', {
                is: AccountList
            });
            document.body.appendChild(element);

            await flushPromises();

            const firstAccount = element.shadowRoot.querySelector('.account-item');
            firstAccount.click();

            expect(publish).toHaveBeenCalledWith(
                expect.anything(),
                ACCOUNT_SELECTED,
                expect.objectContaining({
                    accountId: '001xxx001',
                    accountName: 'Acme Corp'
                })
            );
        });
    });

    describe('filtering', () => {
        it('filters accounts by search term', async () => {
            getAccounts.mockResolvedValue(MOCK_ACCOUNTS);

            const element = createElement('c-account-list', {
                is: AccountList
            });
            document.body.appendChild(element);

            await flushPromises();

            const searchInput = element.shadowRoot.querySelector('input');
            searchInput.value = 'Acme';
            searchInput.dispatchEvent(new Event('input'));

            await flushPromises();

            const visibleItems = element.shadowRoot.querySelectorAll('.account-item:not(.hidden)');
            expect(visibleItems.length).toBe(1);
            expect(visibleItems[0].textContent).toContain('Acme Corp');
        });
    });
});
```

---

## Related Resources

- [component-patterns.md](component-patterns.md) - Component implementation patterns
- [lms-guide.md](lms-guide.md) - Lightning Message Service
- [James Simone - Advanced LWC Jest Testing](https://www.jamessimone.net/blog/joys-of-apex/advanced-lwc-jest-testing/)
- [LWC Recipes](https://github.com/trailheadapps/lwc-recipes) - See component-level `__tests__` folders for Jest examples
