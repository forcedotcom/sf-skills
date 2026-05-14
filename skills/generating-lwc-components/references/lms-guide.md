<!-- Parent: generating-lwc-components/SKILL.md -->
# Lightning Message Service (LMS) Guide

Complete guide to cross-DOM component communication using Lightning Message Service.

---

## Table of Contents

1. [Overview](#overview)
2. [When to Use LMS](#when-to-use-lms)
3. [Message Channel Setup](#message-channel-setup)
4. [Publishing Messages](#publishing-messages)
5. [Subscribing to Messages](#subscribing-to-messages)
6. [Scopes](#scopes)
7. [Advanced Patterns](#advanced-patterns)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Lightning Message Service (LMS) enables communication between components across different DOM contexts:
- Lightning Web Components (LWC)
- Aura Components
- Visualforce pages (in Lightning Experience)

**Key Benefits**:
- Cross-DOM communication (Shadow DOM boundaries)
- Loosely coupled components
- Publish-subscribe pattern
- Type-safe messaging with message channels

---

## When to Use LMS

| Use Case | Recommended Pattern |
|----------|---------------------|
| Parent → Child | `@api` properties (simple, direct) |
| Child → Parent | Custom Events (simple, direct) |
| Sibling → Sibling (same hierarchy) | Parent mediator + Custom Events |
| **Cross-DOM communication** | **Lightning Message Service** |
| **App Builder page components** | **Lightning Message Service** |
| **Aura ↔ LWC communication** | **Lightning Message Service** |
| **Visualforce ↔ LWC (in LEX)** | **Lightning Message Service** |

**Rule of Thumb**: Use LMS when components cannot directly reference each other or cross DOM boundaries.

---

## Message Channel Setup

### 1. Create Message Channel Metadata

Lightning Message Channels are metadata files that define the message schema.

**File**: `force-app/main/default/messageChannels/AccountSelected__c.messageChannel-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningMessageChannel xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Message channel for account selection events</description>
    <isExposed>true</isExposed>
    <lightningMessageFields>
        <description>Account ID</description>
        <fieldName>accountId</fieldName>
    </lightningMessageFields>
    <lightningMessageFields>
        <description>Account Name</description>
        <fieldName>accountName</fieldName>
    </lightningMessageFields>
    <lightningMessageFields>
        <description>Source component identifier</description>
        <fieldName>source</fieldName>
    </lightningMessageFields>
    <masterLabel>Account Selected</masterLabel>
</LightningMessageChannel>
```

### 2. Deploy Message Channel

```bash
sf project deploy start -m LightningMessageChannel:AccountSelected__c
```

### 3. Import Message Channel in Component

```javascript
import ACCOUNT_SELECTED_CHANNEL from '@salesforce/messageChannel/AccountSelected__c';
```

---

## Publishing Messages

### Basic Publisher Pattern

```javascript
// accountPublisher.js
import { LightningElement, wire } from 'lwc';
import { publish, MessageContext } from 'lightning/messageService';
import ACCOUNT_SELECTED_CHANNEL from '@salesforce/messageChannel/AccountSelected__c';

export default class AccountPublisher extends LightningElement {
    @wire(MessageContext)
    messageContext;

    handleAccountClick(event) {
        const accountId = event.target.dataset.id;
        const accountName = event.target.dataset.name;

        // Create payload
        const payload = {
            accountId: accountId,
            accountName: accountName,
            source: 'accountPublisher'
        };

        // Publish message
        publish(this.messageContext, ACCOUNT_SELECTED_CHANNEL, payload);
    }
}
```

```html
<!-- accountPublisher.html -->
<template>
    <div class="slds-card">
        <div class="slds-card__header">
            <h2 class="slds-text-heading_medium">Account List</h2>
        </div>
        <div class="slds-card__body">
            <template for:each={accounts} for:item="account">
                <div key={account.Id}
                     class="slds-box slds-m-around_small"
                     data-id={account.Id}
                     data-name={account.Name}
                     onclick={handleAccountClick}>
                    {account.Name}
                </div>
            </template>
        </div>
    </div>
</template>
```

### Publisher with Conditional Logic

```javascript
handlePublish(accountData) {
    // Validate before publishing
    if (!this.messageContext) {
        console.error('MessageContext not initialized');
        return;
    }

    if (!accountData || !accountData.Id) {
        console.error('Invalid account data');
        return;
    }

    const payload = {
        accountId: accountData.Id,
        accountName: accountData.Name,
        source: this.componentName,
        timestamp: Date.now()
    };

    publish(this.messageContext, ACCOUNT_SELECTED_CHANNEL, payload);

    // Optional: Show toast confirmation
    this.dispatchEvent(new ShowToastEvent({
        title: 'Selection Published',
        message: `Account "${accountData.Name}" selected`,
        variant: 'success'
    }));
}
```

---

## Subscribing to Messages

### Basic Subscriber Pattern

```javascript
// accountSubscriber.js
import { LightningElement, wire } from 'lwc';
import { subscribe, unsubscribe, MessageContext, APPLICATION_SCOPE } from 'lightning/messageService';
import ACCOUNT_SELECTED_CHANNEL from '@salesforce/messageChannel/AccountSelected__c';

export default class AccountSubscriber extends LightningElement {
    subscription = null;
    selectedAccountId;
    selectedAccountName;

    @wire(MessageContext)
    messageContext;

    connectedCallback() {
        this.subscribeToChannel();
    }

    disconnectedCallback() {
        this.unsubscribeFromChannel();
    }

    subscribeToChannel() {
        if (!this.subscription) {
            this.subscription = subscribe(
                this.messageContext,
                ACCOUNT_SELECTED_CHANNEL,
                (message) => this.handleMessage(message),
                { scope: APPLICATION_SCOPE }
            );
        }
    }

    unsubscribeFromChannel() {
        unsubscribe(this.subscription);
        this.subscription = null;
    }

    handleMessage(message) {
        this.selectedAccountId = message.accountId;
        this.selectedAccountName = message.accountName;

        console.log('Message received from:', message.source);
        console.log('Account ID:', message.accountId);
    }
}
```

```html
<!-- accountSubscriber.html -->
<template>
    <div class="slds-card">
        <div class="slds-card__header">
            <h2 class="slds-text-heading_medium">Selected Account</h2>
        </div>
        <div class="slds-card__body">
            <template lwc:if={selectedAccountId}>
                <dl class="slds-dl_horizontal">
                    <dt class="slds-dl_horizontal__label">Account ID:</dt>
                    <dd class="slds-dl_horizontal__detail">{selectedAccountId}</dd>
                    <dt class="slds-dl_horizontal__label">Account Name:</dt>
                    <dd class="slds-dl_horizontal__detail">{selectedAccountName}</dd>
                </dl>
            </template>
            <template lwc:else>
                <p class="slds-text-color_weak">No account selected</p>
            </template>
        </div>
    </div>
</template>
```

### Subscriber with Filtering

```javascript
handleMessage(message) {
    // Ignore messages from this component (avoid self-updates)
    if (message.source === this.componentName) {
        return;
    }

    // Filter by specific conditions
    if (message.accountId && message.accountId.startsWith('001')) {
        this.selectedAccountId = message.accountId;
        this.selectedAccountName = message.accountName;

        // Fetch additional data if needed
        this.loadAccountDetails(message.accountId);
    }
}

async loadAccountDetails(accountId) {
    try {
        const data = await getAccountDetails({ accountId });
        this.accountDetails = data;
    } catch (error) {
        this.handleError(error);
    }
}
```

---

## Scopes

LMS supports two subscription scopes:

| Scope | Behavior | Use Case |
|-------|----------|----------|
| `APPLICATION_SCOPE` | Receive messages from entire app | Cross-page communication, global state |
| `undefined` (default) | Receive messages only within active tab | Tab-specific communication |

### Application Scope Example

```javascript
import { APPLICATION_SCOPE } from 'lightning/messageService';

subscribe(
    this.messageContext,
    ACCOUNT_SELECTED_CHANNEL,
    (message) => this.handleMessage(message),
    { scope: APPLICATION_SCOPE }
);
```

### Tab Scope Example

```javascript
// No scope specified = tab scope only
subscribe(
    this.messageContext,
    ACCOUNT_SELECTED_CHANNEL,
    (message) => this.handleMessage(message)
);
```

---

## Advanced Patterns

### 1. Multiple Subscriptions

```javascript
export default class MultiSubscriber extends LightningElement {
    accountSubscription = null;
    contactSubscription = null;

    @wire(MessageContext) messageContext;

    connectedCallback() {
        // Subscribe to account channel
        this.accountSubscription = subscribe(
            this.messageContext,
            ACCOUNT_SELECTED_CHANNEL,
            (message) => this.handleAccountMessage(message),
            { scope: APPLICATION_SCOPE }
        );

        // Subscribe to contact channel
        this.contactSubscription = subscribe(
            this.messageContext,
            CONTACT_SELECTED_CHANNEL,
            (message) => this.handleContactMessage(message),
            { scope: APPLICATION_SCOPE }
        );
    }

    disconnectedCallback() {
        unsubscribe(this.accountSubscription);
        unsubscribe(this.contactSubscription);
        this.accountSubscription = null;
        this.contactSubscription = null;
    }

    handleAccountMessage(message) {
        // Handle account-specific logic
    }

    handleContactMessage(message) {
        // Handle contact-specific logic
    }
}
```

### 2. Publish-Subscribe in Same Component

```javascript
export default class PublisherSubscriber extends LightningElement {
    subscription = null;
    @wire(MessageContext) messageContext;

    connectedCallback() {
        // Subscribe to messages from OTHER components
        this.subscription = subscribe(
            this.messageContext,
            ACCOUNT_SELECTED_CHANNEL,
            (message) => this.handleMessage(message),
            { scope: APPLICATION_SCOPE }
        );
    }

    disconnectedCallback() {
        unsubscribe(this.subscription);
    }

    handleMessage(message) {
        // Filter out own messages
        if (message.source === 'myComponent') {
            return;
        }
        // Process external messages
        this.selectedAccountId = message.accountId;
    }

    handleLocalSelection(event) {
        const accountId = event.detail.id;

        // Publish for other components
        publish(this.messageContext, ACCOUNT_SELECTED_CHANNEL, {
            accountId,
            source: 'myComponent'
        });

        // Update own state directly (don't rely on subscription)
        this.selectedAccountId = accountId;
    }
}
```

### 3. Conditional Subscription

```javascript
export default class ConditionalSubscriber extends LightningElement {
    @api enableLiveUpdates = false;
    subscription = null;
    @wire(MessageContext) messageContext;

    connectedCallback() {
        if (this.enableLiveUpdates) {
            this.subscribeToChannel();
        }
    }

    @api
    toggleLiveUpdates(enabled) {
        this.enableLiveUpdates = enabled;
        if (enabled) {
            this.subscribeToChannel();
        } else {
            this.unsubscribeFromChannel();
        }
    }

    subscribeToChannel() {
        if (!this.subscription) {
            this.subscription = subscribe(
                this.messageContext,
                ACCOUNT_SELECTED_CHANNEL,
                (message) => this.handleMessage(message),
                { scope: APPLICATION_SCOPE }
            );
        }
    }

    unsubscribeFromChannel() {
        if (this.subscription) {
            unsubscribe(this.subscription);
            this.subscription = null;
        }
    }
}
```

### 4. Message Buffering

```javascript
export default class MessageBuffer extends LightningElement {
    messageQueue = [];
    isProcessing = false;

    handleMessage(message) {
        this.messageQueue.push(message);
        this.processQueue();
    }

    async processQueue() {
        if (this.isProcessing || this.messageQueue.length === 0) {
            return;
        }

        this.isProcessing = true;

        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            await this.processMessage(message);
        }

        this.isProcessing = false;
    }

    async processMessage(message) {
        // Simulate async processing
        return new Promise(resolve => {
            setTimeout(() => {
                this.selectedAccountId = message.accountId;
                resolve();
            }, 100);
        });
    }
}
```

---

## Best Practices

### 1. Always Unsubscribe

```javascript
disconnectedCallback() {
    // CRITICAL: Prevent memory leaks
    if (this.subscription) {
        unsubscribe(this.subscription);
        this.subscription = null;
    }
}
```

### 2. Validate MessageContext

```javascript
handlePublish(data) {
    if (!this.messageContext) {
        console.warn('MessageContext not available');
        return;
    }
    publish(this.messageContext, CHANNEL, data);
}
```

### 3. Use Descriptive Payloads

```javascript
// BAD - Unclear payload
publish(this.messageContext, CHANNEL, { id: '001xxx' });

// GOOD - Clear, descriptive payload
publish(this.messageContext, CHANNEL, {
    accountId: '001xxx000003DGQ',
    accountName: 'Acme Corp',
    source: 'accountList',
    timestamp: Date.now(),
    metadata: {
        action: 'selected',
        view: 'list'
    }
});
```

### 4. Document Message Channels

```javascript
/**
 * Publishes account selection event to AccountSelected__c channel
 * @param {Object} payload
 * @param {String} payload.accountId - Salesforce Account ID
 * @param {String} payload.accountName - Account Name
 * @param {String} payload.source - Component identifier
 */
publishAccountSelection(payload) {
    publish(this.messageContext, ACCOUNT_SELECTED_CHANNEL, payload);
}
```

### 5. Error Handling

```javascript
handleMessage(message) {
    try {
        if (!message || !message.accountId) {
            throw new Error('Invalid message payload');
        }

        this.selectedAccountId = message.accountId;
        this.loadAccountDetails(message.accountId);
    } catch (error) {
        console.error('Error processing message:', error);
        this.dispatchEvent(new ShowToastEvent({
            title: 'Error',
            message: 'Failed to process message',
            variant: 'error'
        }));
    }
}
```

---

## Troubleshooting

### Issue: Messages Not Received

**Checklist**:
1. Is `MessageContext` wired correctly?
   ```javascript
   @wire(MessageContext) messageContext;
   ```

2. Is subscription active?
   ```javascript
   console.log('Subscription:', this.subscription); // Should not be null
   ```

3. Is the message channel deployed?
   ```bash
   sf project deploy start -m LightningMessageChannel
   ```

4. Are publisher and subscriber using the same channel?
   ```javascript
   // Both should import the same channel
   import CHANNEL from '@salesforce/messageChannel/AccountSelected__c';
   ```

5. Is the scope correct?
   ```javascript
   // For cross-page: APPLICATION_SCOPE
   // For same page: no scope (default)
   ```

### Issue: Memory Leaks

**Cause**: Not unsubscribing in `disconnectedCallback()`

**Fix**:
```javascript
disconnectedCallback() {
    unsubscribe(this.subscription);
    this.subscription = null;
}
```

### Issue: Self-Updates

**Cause**: Component receives its own published messages

**Fix**: Filter by source
```javascript
handleMessage(message) {
    if (message.source === this.componentName) {
        return; // Ignore own messages
    }
    // Process message
}
```

---

## Testing LMS Components

### Mock MessageContext

```javascript
// testUtils.js
export const createMessageContextMock = () => {
    return jest.fn();
};

export const mockPublish = jest.fn();
export const mockSubscribe = jest.fn();
export const mockUnsubscribe = jest.fn();

jest.mock('lightning/messageService', () => ({
    publish: mockPublish,
    subscribe: mockSubscribe,
    unsubscribe: mockUnsubscribe,
    MessageContext: Symbol('MessageContext'),
    APPLICATION_SCOPE: Symbol('APPLICATION_SCOPE')
}), { virtual: true });
```

### Test Publisher

```javascript
import { createElement } from 'lwc';
import AccountPublisher from 'c/accountPublisher';
import { publish } from 'lightning/messageService';
import ACCOUNT_SELECTED_CHANNEL from '@salesforce/messageChannel/AccountSelected__c';

jest.mock('lightning/messageService');

describe('c-account-publisher', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('publishes account selection', () => {
        const element = createElement('c-account-publisher', {
            is: AccountPublisher
        });
        document.body.appendChild(element);

        // Trigger selection
        const accountCard = element.shadowRoot.querySelector('[data-id="001xxx"]');
        accountCard.click();

        // Assert publish was called
        expect(publish).toHaveBeenCalledWith(
            expect.anything(),
            ACCOUNT_SELECTED_CHANNEL,
            expect.objectContaining({
                accountId: '001xxx'
            })
        );
    });
});
```

### Test Subscriber

```javascript
import { createElement } from 'lwc';
import AccountSubscriber from 'c/accountSubscriber';
import { subscribe } from 'lightning/messageService';

jest.mock('lightning/messageService');

describe('c-account-subscriber', () => {
    let messageHandler;

    beforeEach(() => {
        subscribe.mockImplementation((context, channel, handler, options) => {
            messageHandler = handler;
            return { subscription: 'mock-subscription' };
        });
    });

    it('subscribes on connected', () => {
        const element = createElement('c-account-subscriber', {
            is: AccountSubscriber
        });
        document.body.appendChild(element);

        expect(subscribe).toHaveBeenCalled();
    });

    it('handles incoming message', async () => {
        const element = createElement('c-account-subscriber', {
            is: AccountSubscriber
        });
        document.body.appendChild(element);

        // Simulate message
        messageHandler({
            accountId: '001xxx',
            accountName: 'Acme Corp'
        });

        await Promise.resolve();

        const accountName = element.shadowRoot.querySelector('.account-name');
        expect(accountName.textContent).toBe('Acme Corp');
    });
});
```

---

## Complete Example: Account-Contact Sync

### Message Channel

```xml
<!-- ContactSelected__c.messageChannel-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<LightningMessageChannel xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Contact selection messaging</description>
    <isExposed>true</isExposed>
    <lightningMessageFields>
        <fieldName>contactId</fieldName>
    </lightningMessageFields>
    <lightningMessageFields>
        <fieldName>contactName</fieldName>
    </lightningMessageFields>
    <lightningMessageFields>
        <fieldName>accountId</fieldName>
    </lightningMessageFields>
    <masterLabel>Contact Selected</masterLabel>
</LightningMessageChannel>
```

### Publisher Component

```javascript
// contactList.js
import { LightningElement, api, wire } from 'lwc';
import { publish, MessageContext } from 'lightning/messageService';
import CONTACT_SELECTED from '@salesforce/messageChannel/ContactSelected__c';
import getContacts from '@salesforce/apex/ContactController.getContacts';

export default class ContactList extends LightningElement {
    @api accountId;
    contacts;
    @wire(MessageContext) messageContext;

    @wire(getContacts, { accountId: '$accountId' })
    wiredContacts({ data, error }) {
        if (data) {
            this.contacts = data;
        }
    }

    handleContactSelect(event) {
        const contactId = event.currentTarget.dataset.id;
        const contact = this.contacts.find(c => c.Id === contactId);

        publish(this.messageContext, CONTACT_SELECTED, {
            contactId: contact.Id,
            contactName: contact.Name,
            accountId: this.accountId
        });
    }
}
```

### Subscriber Component

```javascript
// contactDetails.js
import { LightningElement, wire } from 'lwc';
import { subscribe, MessageContext, APPLICATION_SCOPE } from 'lightning/messageService';
import CONTACT_SELECTED from '@salesforce/messageChannel/ContactSelected__c';
import getContactDetails from '@salesforce/apex/ContactController.getContactDetails';

export default class ContactDetails extends LightningElement {
    subscription = null;
    contactId;
    contactDetails;
    @wire(MessageContext) messageContext;

    connectedCallback() {
        this.subscription = subscribe(
            this.messageContext,
            CONTACT_SELECTED,
            (message) => this.handleContactSelected(message),
            { scope: APPLICATION_SCOPE }
        );
    }

    disconnectedCallback() {
        unsubscribe(this.subscription);
    }

    async handleContactSelected(message) {
        this.contactId = message.contactId;
        try {
            this.contactDetails = await getContactDetails({
                contactId: message.contactId
            });
        } catch (error) {
            console.error('Error loading contact details:', error);
        }
    }
}
```

---

## Related Resources

- [component-patterns.md](component-patterns.md) - Parent-child communication
- [jest-testing.md](jest-testing.md) - Testing LMS components
- [Official LMS Documentation](https://developer.salesforce.com/docs/component-library/documentation/en/lwc/lwc.use_message_channel)
