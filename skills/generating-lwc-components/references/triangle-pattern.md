<!-- Parent: generating-lwc-components/SKILL.md -->
# Flow-LWC-Apex Triangle: LWC Perspective

The **Triangle Architecture** is a foundational Salesforce pattern where Flow, LWC, and Apex work together. This guide focuses on the **LWC role** in this architecture.

---

## Architecture Overview

```
                         ┌─────────────────────────────────────┐
                         │              FLOW                   │
                         │         (Orchestrator)              │
                         └───────────────┬─────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              │ screens                  │ actionCalls              │
              │ <componentInstance>      │ actionType="apex"        │
              │                          │                          │
              ▼                          ▼                          ▲
┌─────────────────────────┐    ┌─────────────────────────┐         │
│          LWC            │    │         APEX            │         │
│     (UI Component)      │───▶│   (Business Logic)      │─────────┘
│                         │    │                         │
│ • Rich UI/UX        ◀── YOU ARE HERE                   │
│ • User Interaction      │    │ • @InvocableMethod      │
│ • FlowAttribute         │    │ • @AuraEnabled          │
│   ChangeEvent           │    │ • Complex Logic         │
│ • FlowNavigation        │    │ • DML Operations        │
│   FinishEvent           │    │                         │
└─────────────────────────┘    └─────────────────────────┘
              │                          ▲
              │      @AuraEnabled        │
              │      wire / imperative   │
              └──────────────────────────┘
```

---

## LWC's Role in the Triangle

| Communication Path | Mechanism | Direction |
|-------------------|-----------|-----------|
| Flow → LWC | `inputParameters` → `@api` | One-way input |
| LWC → Flow | `FlowAttributeChangeEvent` | Event-based output |
| LWC → Flow Nav | `FlowNavigationFinishEvent` | Navigation command |
| LWC → Apex | `@wire` or `imperative` | Async call |
| Apex → LWC | Return value / wire refresh | Response |

---

## Pattern 1: Flow Screen Component

**Use Case**: Custom UI component for user selection within a guided Flow.

```
┌─────────┐     @api (in)      ┌─────────┐
│  FLOW   │ ────────────────▶  │   LWC   │
│ Screen  │                    │  Screen │
│         │ ◀────────────────  │Component│
│         │  FlowAttribute     │         │
└─────────┘   ChangeEvent      └─────────┘
```

### LWC JavaScript

```javascript
import { LightningElement, api } from 'lwc';
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

export default class RecordSelector extends LightningElement {
    // Input from Flow (read-only in component)
    @api recordId;
    @api availableActions = [];

    // Output to Flow (must dispatch event to update)
    @api selectedRecordId;

    handleSelect(event) {
        // Update local property
        this.selectedRecordId = event.detail.id;

        // CRITICAL: Dispatch event to update Flow variable
        this.dispatchEvent(new FlowAttributeChangeEvent(
            'selectedRecordId',  // Must match @api property name
            this.selectedRecordId
        ));
    }

    handleFinish() {
        // Navigate Flow to next screen
        if (this.availableActions.find(action => action === 'NEXT')) {
            this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
        }
    }
}
```

### LWC meta.xml (Flow Target)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>Record Selector</masterLabel>
    <description>Custom record selection component for Flow screens</description>
    <targets>
        <target>lightning__FlowScreen</target>
    </targets>
    <targetConfigs>
        <targetConfig targets="lightning__FlowScreen">
            <property name="recordId" type="String" label="Record ID" description="Parent record ID"/>
            <property name="selectedRecordId" type="String" label="Selected Record ID" role="outputOnly"/>
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

### Property Roles

| Role | Description | Flow Behavior |
|------|-------------|---------------|
| (none) | Input/Output | Editable in Flow builder |
| `role="inputOnly"` | Input only | Cannot be used as output |
| `role="outputOnly"` | Output only | Read-only in Flow builder |

---

## Pattern 2: LWC Calling Apex

**Use Case**: LWC needs data or operations beyond Flow context.

### Wire Pattern (Reactive, Cached)

```javascript
import { LightningElement, api, wire } from 'lwc';
import getRecords from '@salesforce/apex/RecordController.getRecords';

export default class RecordList extends LightningElement {
    @api recordId;
    records;
    error;

    @wire(getRecords, { parentId: '$recordId' })
    wiredRecords({ error, data }) {
        if (data) {
            this.records = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.records = undefined;
        }
    }
}
```

### Imperative Pattern (On-Demand, Fresh)

```javascript
import { LightningElement, api } from 'lwc';
import { FlowNavigationFinishEvent } from 'lightning/flowSupport';
import processRecord from '@salesforce/apex/RecordController.processRecord';

export default class RecordProcessor extends LightningElement {
    @api recordId;
    @api availableActions = [];
    isProcessing = false;

    async handleSubmit() {
        this.isProcessing = true;
        try {
            const result = await processRecord({ recordId: this.recordId });
            if (result.isSuccess) {
                // Navigate Flow forward
                this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
            }
        } catch (error) {
            // Handle error (show toast, etc.)
            console.error('Processing failed:', error.body.message);
        } finally {
            this.isProcessing = false;
        }
    }
}
```

### When to Use Each Pattern

| Pattern | Use When | Caching |
|---------|----------|---------|
| `@wire` | Data should refresh when inputs change | Yes (cacheable=true) |
| Imperative | User-triggered action, DML needed | No |

---

## Pattern 3: Full Triangle Integration

**Use Case**: LWC in Flow screen that calls Apex for complex operations.

```javascript
import { LightningElement, api, wire } from 'lwc';
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';
import getProducts from '@salesforce/apex/ProductController.getProducts';
import calculatePricing from '@salesforce/apex/PricingService.calculate';

export default class ProductSelector extends LightningElement {
    @api accountId;           // Input from Flow
    @api selectedProducts;    // Output to Flow
    @api totalPrice;          // Output to Flow
    @api availableActions = [];

    products;
    selectedIds = new Set();

    // Wire: Fetch products reactively
    @wire(getProducts, { accountId: '$accountId' })
    wiredProducts({ data, error }) {
        if (data) this.products = data;
    }

    handleProductSelect(event) {
        const productId = event.target.dataset.id;
        if (this.selectedIds.has(productId)) {
            this.selectedIds.delete(productId);
        } else {
            this.selectedIds.add(productId);
        }
        this.updateFlowOutputs();
    }

    async updateFlowOutputs() {
        // Update selected products output
        this.selectedProducts = Array.from(this.selectedIds);
        this.dispatchEvent(new FlowAttributeChangeEvent(
            'selectedProducts',
            this.selectedProducts
        ));

        // Imperative: Calculate pricing
        const result = await calculatePricing({
            productIds: this.selectedProducts
        });
        this.totalPrice = result.total;
        this.dispatchEvent(new FlowAttributeChangeEvent(
            'totalPrice',
            this.totalPrice
        ));
    }

    handleNext() {
        this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
    }
}
```

---

## Jest Testing (Flow Integration)

```javascript
import { createElement } from 'lwc';
import RecordSelector from 'c/recordSelector';
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

// Mock lightning/flowSupport
jest.mock('lightning/flowSupport', () => ({
    FlowAttributeChangeEvent: jest.fn(),
    FlowNavigationFinishEvent: jest.fn()
}), { virtual: true });

describe('c-record-selector', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('dispatches FlowAttributeChangeEvent on selection', async () => {
        const element = createElement('c-record-selector', {
            is: RecordSelector
        });
        element.recordId = '001xx000003GYHAA2';
        document.body.appendChild(element);

        // Simulate user selection
        const handler = jest.fn();
        element.addEventListener('flowattributechange', handler);

        const tile = element.shadowRoot.querySelector('[data-id]');
        tile.click();

        // Verify FlowAttributeChangeEvent was constructed
        expect(FlowAttributeChangeEvent).toHaveBeenCalledWith(
            'selectedRecordId',
            expect.any(String)
        );
    });

    it('dispatches FlowNavigationFinishEvent on finish', async () => {
        const element = createElement('c-record-selector', {
            is: RecordSelector
        });
        element.availableActions = ['NEXT', 'FINISH'];
        document.body.appendChild(element);

        const finishButton = element.shadowRoot.querySelector('.finish-button');
        finishButton.click();

        expect(FlowNavigationFinishEvent).toHaveBeenCalledWith('NEXT');
    });
});
```

---

## Deployment Order

When deploying integrated triangle solutions:

```
1. APEX CLASSES
   └── @AuraEnabled controllers (LWC depends on these)

2. LWC COMPONENTS      ← Deploy SECOND
   └── meta.xml with lightning__FlowScreen target
   └── JavaScript with Flow imports

3. FLOWS
   └── Reference deployed LWC components
```

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Missing FlowAttributeChangeEvent | Output never updates in Flow | Always dispatch event when output changes |
| Direct @api property mutation for outputs | Flow doesn't see changes | Use FlowAttributeChangeEvent |
| Mixing @wire and imperative for same data | Cache/freshness conflicts | Choose one pattern per data need |
| Calling Apex for Flow-available data | Unnecessary callouts | Pass via inputParameters |
| Hardcoded navigation actions | Breaks in different contexts | Check availableActions first |

---

## Flow Events Reference

| Event | Purpose | Parameters |
|-------|---------|------------|
| `FlowAttributeChangeEvent` | Update output property | (propertyName, value) |
| `FlowNavigationFinishEvent` | Navigate Flow | 'NEXT', 'BACK', 'PAUSE', 'FINISH' |

---

## Related Documentation

| Topic | Location |
|-------|----------|
| Flow screen component template | `generating-lwc-components/assets/flow-screen-component/` |
| LWC best practices | `generating-lwc-components/references/lwc-best-practices.md` |
| Apex triangle perspective | `sf-apex/references/triangle-pattern.md` |
| Flow triangle perspective | `sf-flow/references/triangle-pattern.md` |
