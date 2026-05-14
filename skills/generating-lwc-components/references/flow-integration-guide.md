<!-- Parent: generating-lwc-components/SKILL.md -->
# LWC Flow Integration Guide

This guide covers building Lightning Web Components for use in Salesforce Flow Screens.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FLOW ↔ LWC COMMUNICATION                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────┐                    ┌─────────────────┐        │
│   │      FLOW       │                    │       LWC       │        │
│   │    Variables    │                    │   Component     │        │
│   └────────┬────────┘                    └────────┬────────┘        │
│            │                                      │                  │
│            │ @api (inputOnly)                     │                  │
│            ├─────────────────────────────────────▶│                  │
│            │                                      │                  │
│            │ FlowAttributeChangeEvent (outputOnly)│                  │
│            │◀─────────────────────────────────────┤                  │
│            │                                      │                  │
│            │ FlowNavigationFinishEvent            │                  │
│            │◀─────────────────────────────────────┤                  │
│            │  (NEXT, BACK, FINISH, PAUSE)         │                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

| Direction | Mechanism | Use Case |
|-----------|-----------|----------|
| Flow → LWC | `@api` with `role="inputOnly"` | Pass context data to component |
| LWC → Flow | `FlowAttributeChangeEvent` | Return user selections/data |
| LWC → Navigation | `FlowNavigationFinishEvent` | Trigger Next/Back/Finish |

---

## Meta.xml Configuration

### Target Configuration

```xml
<targets>
    <target>lightning__FlowScreen</target>
</targets>
```

### Property Roles

```xml
<targetConfig targets="lightning__FlowScreen">
    <!-- INPUT: Flow → Component -->
    <property
        name="recordId"
        type="String"
        label="Record ID"
        description="ID from Flow"
        role="inputOnly"/>

    <!-- OUTPUT: Component → Flow -->
    <property
        name="selectedValue"
        type="String"
        label="Selected Value"
        description="User's selection"
        role="outputOnly"/>
</targetConfig>
```

### Supported Property Types

| Type | Description | Example |
|------|-------------|---------|
| `String` | Text values | Record IDs, names |
| `Boolean` | True/false | Flags, completion status |
| `Integer` | Whole numbers | Counts, indexes |
| `Date` | Date values | Due dates |
| `DateTime` | Date and time | Timestamps |
| `@salesforce/schema/*` | SObject references | Record types |

---

## FlowAttributeChangeEvent

This is the **critical** mechanism for sending data back to Flow.

### Import

```javascript
import { FlowAttributeChangeEvent } from 'lightning/flowSupport';
```

### Usage

```javascript
// Dispatch event to update Flow variable
// First param: @api property name (must match meta.xml exactly)
// Second param: new value
this.dispatchEvent(new FlowAttributeChangeEvent(
    'selectedRecordId',  // Property name
    this.recordId        // Value
));
```

### Example: Selection Handler

```javascript
@api selectedRecordId;
@api selectedRecordName;

handleSelect(event) {
    const id = event.target.dataset.id;
    const name = event.target.dataset.name;

    // Update local properties
    this.selectedRecordId = id;
    this.selectedRecordName = name;

    // Notify Flow of BOTH changes
    this.dispatchEvent(new FlowAttributeChangeEvent('selectedRecordId', id));
    this.dispatchEvent(new FlowAttributeChangeEvent('selectedRecordName', name));
}
```

### Common Mistake

```javascript
// ❌ WRONG: Only updating local property
this.selectedRecordId = id;

// ✅ CORRECT: Update AND dispatch event
this.selectedRecordId = id;
this.dispatchEvent(new FlowAttributeChangeEvent('selectedRecordId', id));
```

---

## FlowNavigationFinishEvent

Programmatically trigger Flow navigation from your component.

### Import

```javascript
import { FlowNavigationFinishEvent } from 'lightning/flowSupport';
```

### Navigation Actions

| Action | Description | When Available |
|--------|-------------|----------------|
| `'NEXT'` | Go to next screen | Mid-flow screens |
| `'BACK'` | Go to previous screen | After first screen |
| `'FINISH'` | Complete the flow | Final screens |
| `'PAUSE'` | Pause flow (if enabled) | Pausable flows |

### Usage

```javascript
// Navigate to next screen
this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));

// Navigate back
this.dispatchEvent(new FlowNavigationFinishEvent('BACK'));

// Finish the flow
this.dispatchEvent(new FlowNavigationFinishEvent('FINISH'));
```

### Check Available Actions

Flow provides available actions via a special `@api` property:

```javascript
// Automatically populated by Flow runtime
@api availableActions = [];

get canGoNext() {
    return this.availableActions.includes('NEXT');
}

get canGoBack() {
    return this.availableActions.includes('BACK');
}

handleNext() {
    if (this.canGoNext) {
        this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
    }
}
```

### Conditional Navigation Buttons

```html
<template lwc:if={canGoBack}>
    <lightning-button label="Back" onclick={handleBack}></lightning-button>
</template>

<template lwc:if={canGoNext}>
    <lightning-button label="Next" variant="brand" onclick={handleNext}></lightning-button>
</template>
```

---

## Validation Before Navigation

Always validate before allowing navigation:

```javascript
handleNext() {
    // Validate
    if (!this.selectedRecordId) {
        this.errorMessage = 'Please select a record.';
        this.dispatchEvent(new FlowAttributeChangeEvent('errorMessage', this.errorMessage));
        return;
    }

    // Clear error
    this.errorMessage = null;
    this.dispatchEvent(new FlowAttributeChangeEvent('errorMessage', null));

    // Mark complete and navigate
    this.isComplete = true;
    this.dispatchEvent(new FlowAttributeChangeEvent('isComplete', true));
    this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
}
```

---

## Apex Integration in Flow Context

### Wire Service

```javascript
import { wire } from 'lwc';
import getRecords from '@salesforce/apex/MyController.getRecords';

@api recordId; // From Flow

@wire(getRecords, { parentId: '$recordId' })
wiredRecords({ error, data }) {
    if (data) {
        this.records = data;
    } else if (error) {
        this.error = this.reduceErrors(error);
    }
}
```

### Imperative Calls

```javascript
import processRecord from '@salesforce/apex/MyController.processRecord';

async handleProcess() {
    this.isLoading = true;
    try {
        const result = await processRecord({
            recordId: this.selectedRecordId
        });

        if (result.success) {
            this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
        } else {
            this.errorMessage = result.message;
            this.dispatchEvent(new FlowAttributeChangeEvent('errorMessage', result.message));
        }
    } catch (error) {
        this.errorMessage = this.reduceErrors(error);
    } finally {
        this.isLoading = false;
    }
}
```

---

## Flow Context Variables

Flow provides special context via reserved variable names:

```xml
<!-- In Flow Builder, map these to your component -->
<property name="recordId" value="{!$Record.Id}"/>
<property name="objectApiName" value="{!$Record.Object}"/>
```

---

## Testing LWC in Flows

### Jest Testing

```javascript
import { createElement } from 'lwc';
import FlowScreenComponent from 'c/flowScreenComponent';
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

// Mock the flow support module
jest.mock('lightning/flowSupport', () => ({
    FlowAttributeChangeEvent: jest.fn(),
    FlowNavigationFinishEvent: jest.fn()
}), { virtual: true });

describe('c-flow-screen-component', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('dispatches FlowAttributeChangeEvent on selection', async () => {
        const element = createElement('c-flow-screen-component', {
            is: FlowScreenComponent
        });
        element.availableActions = ['NEXT', 'BACK'];
        document.body.appendChild(element);

        // Simulate selection
        const tile = element.shadowRoot.querySelector('.record-tile');
        tile.click();

        // Verify event dispatched
        expect(FlowAttributeChangeEvent).toHaveBeenCalled();
    });

    it('dispatches FlowNavigationFinishEvent on next', async () => {
        const element = createElement('c-flow-screen-component', {
            is: FlowScreenComponent
        });
        element.availableActions = ['NEXT'];
        element.selectedRecordId = '001xx000000001';
        document.body.appendChild(element);

        // Click next button
        const nextButton = element.shadowRoot.querySelector('lightning-button[label="Next"]');
        nextButton.click();

        // Verify navigation event
        expect(FlowNavigationFinishEvent).toHaveBeenCalledWith('NEXT');
    });
});
```

### Manual Testing

1. Create a Screen Flow in Setup
2. Add your LWC component to a screen
3. Map input/output variables
4. Test in Flow debug mode
5. Verify variable values in debug panel

---

## Common Patterns

### Selection with Confirmation

```javascript
handleSelect(event) {
    this.selectedId = event.target.dataset.id;
    // Don't navigate yet - wait for explicit confirmation
}

handleConfirm() {
    if (!this.selectedId) {
        this.showError('Please select an item');
        return;
    }

    this.dispatchEvent(new FlowAttributeChangeEvent('selectedId', this.selectedId));
    this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
}
```

### Multi-Select to Collection

```javascript
@api selectedIds = [];

handleToggle(event) {
    const id = event.target.dataset.id;

    if (this.selectedIds.includes(id)) {
        this.selectedIds = this.selectedIds.filter(i => i !== id);
    } else {
        this.selectedIds = [...this.selectedIds, id];
    }

    // Send collection back to Flow
    this.dispatchEvent(new FlowAttributeChangeEvent('selectedIds', this.selectedIds));
}
```

### Conditional Screen (Skip Logic)

```javascript
connectedCallback() {
    // Auto-skip if condition met
    if (this.shouldSkip) {
        this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
    }
}
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Output not updating in Flow | Missing FlowAttributeChangeEvent | Always dispatch event after updating @api property |
| Navigation buttons not showing | Wrong availableActions | Check Flow provides availableActions correctly |
| Component not appearing | Missing `isExposed: true` | Set in meta.xml |
| Properties not mapping | Role mismatch | Use `inputOnly` for inputs, `outputOnly` for outputs |
| Values reset on navigation | Local state not persisted | Use @api properties for all persisted data |

---

## Template

Use the template at `assets/flow-screen-component/` as a starting point.

---

## Passing sObjects and Wrapper Classes to Flow

### Overview

Flow can receive complex Apex types through `apex://` type bindings. This enables:
- Passing sObjects directly (not just IDs)
- Passing wrapper/DTO classes with multiple fields
- Two-way data binding for record editing

### apex:// Type Syntax

In your meta.xml, reference Apex classes using the `apex://` prefix:

```xml
<targetConfig targets="lightning__FlowScreen">
    <!-- Pass entire Account record -->
    <property
        name="accountRecord"
        type="apex://Account"
        label="Account Record"
        role="inputOnly"/>

    <!-- Pass custom wrapper class -->
    <property
        name="orderSummary"
        type="apex://OrderController.OrderSummaryWrapper"
        label="Order Summary"
        role="inputOnly"/>

    <!-- Output a modified record -->
    <property
        name="updatedAccount"
        type="apex://Account"
        label="Updated Account"
        role="outputOnly"/>
</targetConfig>
```

### Wrapper Class Requirements

Apex wrapper classes must be **public** and have **public properties**:

```apex
public class OrderController {

    // Wrapper class for Flow
    public class OrderSummaryWrapper {
        @AuraEnabled public String orderId;
        @AuraEnabled public String orderName;
        @AuraEnabled public Decimal totalAmount;
        @AuraEnabled public List<LineItemWrapper> lineItems;
        @AuraEnabled public Account customer;
    }

    public class LineItemWrapper {
        @AuraEnabled public String productName;
        @AuraEnabled public Integer quantity;
        @AuraEnabled public Decimal unitPrice;
    }

    // Invocable method to create the wrapper
    @InvocableMethod(label='Get Order Summary')
    public static List<OrderSummaryWrapper> getOrderSummary(List<Id> orderIds) {
        // Query and build wrapper...
    }
}
```

### Using sObjects in LWC

```javascript
import { api, LightningElement } from 'lwc';
import { FlowAttributeChangeEvent } from 'lightning/flowSupport';

export default class AccountEditor extends LightningElement {
    // Receive sObject from Flow
    @api accountRecord;

    // Track local modifications
    _modifiedAccount;

    connectedCallback() {
        // Create a working copy
        this._modifiedAccount = { ...this.accountRecord };
    }

    handleNameChange(event) {
        this._modifiedAccount.Name = event.target.value;
    }

    handleSave() {
        // Send modified record back to Flow
        this.dispatchEvent(
            new FlowAttributeChangeEvent('updatedAccount', this._modifiedAccount)
        );
    }
}
```

### Using Wrapper Classes in LWC

```javascript
import { api, LightningElement } from 'lwc';

export default class OrderSummaryViewer extends LightningElement {
    @api orderSummary; // apex://OrderController.OrderSummaryWrapper

    get formattedTotal() {
        return this.orderSummary?.totalAmount?.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        });
    }

    get lineItems() {
        return this.orderSummary?.lineItems || [];
    }

    get customerName() {
        // Access nested sObject
        return this.orderSummary?.customer?.Name || 'Unknown';
    }
}
```

### Flow Configuration for apex:// Types

1. **Create an Invocable Action** that returns your wrapper:
   ```apex
   @InvocableMethod
   public static List<MyWrapper> getData(List<String> inputs) { ... }
   ```

2. **In Flow Builder**, call the Invocable Action before the screen

3. **Store result** in an Apex-Defined Variable

4. **Pass to LWC** via the screen component input mapping

### Common Patterns

#### Pattern 1: Record Edit with Validation

```javascript
// LWC that receives, edits, and returns an sObject
@api inputRecord;      // apex://Contact (inputOnly)
@api outputRecord;     // apex://Contact (outputOnly)
@api isValid = false;  // Boolean (outputOnly)

handleFieldChange(event) {
    const field = event.target.dataset.field;
    this.workingRecord[field] = event.target.value;

    // Validate and update outputs
    this.isValid = this.validateRecord();
    this.dispatchEvent(new FlowAttributeChangeEvent('outputRecord', this.workingRecord));
    this.dispatchEvent(new FlowAttributeChangeEvent('isValid', this.isValid));
}
```

#### Pattern 2: Multi-Record Selection

```javascript
// Select from a list, output selected items
@api availableRecords;  // apex://Account[] (inputOnly)
@api selectedRecords = []; // apex://Account[] (outputOnly)

handleSelect(event) {
    const id = event.target.dataset.id;
    const record = this.availableRecords.find(r => r.Id === id);

    if (record && !this.selectedRecords.find(r => r.Id === id)) {
        this.selectedRecords = [...this.selectedRecords, record];
        this.dispatchEvent(
            new FlowAttributeChangeEvent('selectedRecords', this.selectedRecords)
        );
    }
}
```

#### Pattern 3: Master-Detail Editing

```javascript
// Edit parent with nested child records
@api orderWrapper;  // apex://OrderController.OrderWithLines (inputOnly)
@api updatedOrder;  // apex://OrderController.OrderWithLines (outputOnly)

handleLineItemChange(event) {
    const index = event.target.dataset.index;
    const field = event.target.dataset.field;
    const value = event.target.value;

    // Update nested structure
    const updated = JSON.parse(JSON.stringify(this.orderWrapper));
    updated.lineItems[index][field] = value;

    // Recalculate totals
    updated.totalAmount = updated.lineItems.reduce(
        (sum, item) => sum + (item.quantity * item.unitPrice), 0
    );

    this.updatedOrder = updated;
    this.dispatchEvent(new FlowAttributeChangeEvent('updatedOrder', updated));
}
```

### Limitations

| Limitation | Workaround |
|------------|------------|
| No `@JsonAccess` support | Ensure wrapper classes don't require JSON annotation |
| 1000 record limit per collection | Paginate or filter in Apex before passing |
| No generic types | Create specific wrapper classes |
| Complex nesting depth | Flatten deep hierarchies |

### Debugging Tips

1. **Console log received data** to verify structure:
   ```javascript
   connectedCallback() {
       console.log('Received from Flow:', JSON.stringify(this.inputWrapper));
   }
   ```

2. **Check Apex class visibility** - inner classes need `public` modifier

3. **Verify @AuraEnabled** on all properties you need to access

---

## Cross-Skill Integration

| Integration | See Also |
|-------------|----------|
| Flow → Apex → LWC | [triangle-pattern.md](triangle-pattern.md) |
| Apex @AuraEnabled | [sf-apex/references/best-practices.md](../../sf-apex/references/best-practices.md) |
| Flow Templates | [sf-flow/assets/](../../sf-flow/assets/) |
| Async Notifications | [async-notification-patterns.md](async-notification-patterns.md) |
| State Management | [state-management.md](state-management.md) |
