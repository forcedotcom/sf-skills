# Aura to LWC Migration Guidelines

## Core Principles

When migrating Aura components to Lightning Web Components, follow these key principles:

1. **Understand before converting** - Fully analyze the Aura component to understand its functionality, states, and dependencies before beginning the migration.

2. **Focus on functionality equivalence** - The primary goal is to recreate the same user functionality, not necessarily the same internal structure.

3. **Leverage native web standards** - LWC is built on web standards, so prefer native HTML, CSS, and JavaScript capabilities over framework-specific features.

4. **Migrate iteratively** - Break down complex components into smaller parts and migrate one piece at a time.

5. **Test thoroughly** - Comprehensive testing ensures the migrated component maintains the same functionality.

## Key Architectural Differences

| Feature         | Aura                           | LWC                                  |
| --------------- | ------------------------------ | ------------------------------------ |
| Language        | JavaScript (ES5)               | Modern JavaScript (ES6+)             |
| Templating      | Proprietary markup             | Standard HTML with custom directives |
| Component Model | Custom Aura model              | Web Components standard              |
| Data Binding    | Two-way binding                | One-way binding (reactive)           |
| Events          | Aura event system              | Standard DOM events                  |
| Lifecycle       | Aura-specific hooks            | Standard Web Component lifecycle     |
| DOM Access      | Global IDs with aura:id        | this.template.querySelector()        |
| Dependencies    | Can have circular dependencies | Requires strict one-way dependencies |

## Component Structure Migration

**Aura Structure**:

```text
myComponent/
  ├── myComponent.cmp       # Component markup
  ├── myComponentController.js  # Controller logic
  ├── myComponentHelper.js      # Helper functions
  ├── myComponent.css           # Styles
  └── myComponentRenderer.js    # Custom rendering
```

**LWC Structure**:

```text
myComponent/
  ├── myComponent.html      # Template
  ├── myComponent.js        # JavaScript
  ├── myComponent.css       # Styles
  └── myComponent.js-meta.xml  # Configuration
```

## Markup Translation

**Aura Markup**:

```html
<aura:component>
  <aura:attribute name="record" type="Object" />
  <aura:handler name="init" value="{!this}" action="{!c.doInit}" />

  <div class="container">
    <lightning:card title="{!v.record.Name}">
      <p class="slds-p-horizontal_small">{!v.record.Description}</p>
      <aura:set attribute="actions">
        <lightning:button label="Edit" onclick="{!c.handleEdit}" />
      </aura:set>
    </lightning:card>
  </div>
</aura:component>
```

**LWC Markup**:

```html
<template>
  <div class="container">
    <lightning-card title="{record.Name}">
      <p class="slds-p-horizontal_small">{record.Description}</p>
      <div slot="actions">
        <lightning-button label="Edit" onclick="{handleEdit}"></lightning-button>
      </div>
    </lightning-card>
  </div>
</template>
```

## JavaScript Migration

**Aura Controller**:

```javascript
({
  doInit: function (component, event, helper) {
    helper.loadRecord(component);
  },

  handleEdit: function (component, event, helper) {
    helper.editRecord(component.get('v.record'));
  },
});
```

**Aura Helper**:

```javascript
({
  loadRecord: function (component) {
    var action = component.get('c.getRecord');
    action.setParams({
      recordId: component.get('v.recordId'),
    });

    action.setCallback(this, function (response) {
      if (response.getState() === 'SUCCESS') {
        component.set('v.record', response.getReturnValue());
      }
    });

    $A.enqueueAction(action);
  },

  editRecord: function (record) {
    // Edit logic
  },
});
```

**LWC JavaScript**:

```javascript
import { LightningElement, api, wire } from 'lwc';
import getRecord from '@salesforce/apex/RecordController.getRecord';

export default class MyComponent extends LightningElement {
  @api recordId;
  record;

  @wire(getRecord, { recordId: '$recordId' })
  wiredRecord({ error, data }) {
    if (data) {
      this.record = data;
    } else if (error) {
      console.error('Error loading record', error);
    }
  }

  handleEdit() {
    // Edit logic
  }
}
```

## Event Handling Migration

**Aura Events**:

```javascript
// Component event definition
<aura:event type="COMPONENT" description="Record selected">
    <aura:attribute name="recordId" type="String" />
</aura:event>

// Registering a component event
<aura:registerEvent name="recordSelected" type="c:RecordSelectedEvent" />

// Firing a component event
var event = component.getEvent("recordSelected");
event.setParams({ recordId: recordId });
event.fire();

// Handling a component event
<aura:handler name="recordSelected" action="{!c.handleRecordSelected}" />
```

**LWC Events**:

```javascript
// Dispatching a custom event
const event = new CustomEvent('recordselected', {
    detail: { recordId: this.recordId },
    bubbles: true,
    composed: true
});
this.dispatchEvent(event);

// Handling a custom event in parent component's HTML
<c-child-component onrecordselected={handleRecordSelected}></c-child-component>

// In parent component JS
handleRecordSelected(event) {
    const recordId = event.detail.recordId;
    // Process the event
}
```

## Lifecycle Methods Migration

**Aura Lifecycle**:

```javascript
// Init handler
<aura:handler name="init" value="{!this}" action="{!c.doInit}" />

// Render lifecycle
render: function() { /* Custom render */ },
rerender: function() { /* Custom rerender */ },
afterRender: function() { /* After DOM insertion */ },
unrender: function() { /* Component removed */ }
```

**LWC Lifecycle**:

```javascript
// Constructor
constructor() {
    super();
    // Initialize properties
}

// Connected callback
connectedCallback() {
    // Component inserted into DOM
}

// Render callback
renderedCallback() {
    // After component rendering
}

// Disconnected callback
disconnectedCallback() {
    // Component removed from DOM
}

// Error callback
errorCallback(error, stack) {
    // Handle errors
}
```

## Common Migration Challenges

### 1. Component Containment

**Aura** uses facets with `<aura:set attribute="body">` to define slots, while **LWC** uses named slots with the `slot` attribute.

### 2. Global IDs and DOM Access

**Aura** allows direct DOM access through global IDs with `aura:id`, while **LWC** requires using template references with `this.template.querySelector()`.

### 3. Global Event Bus

**Aura** uses application events for cross-component communication, while **LWC** typically uses a combination of custom events and Lightning Message Service.

### 4. Two-way Data Binding

**Aura** supports two-way data binding, while **LWC** uses one-way data binding, requiring explicit event handlers to update values.

### 5. Apex Integration

**Aura** uses callbacks for Apex method calls, while **LWC** uses the `@wire` decorator or `importedApexMethod()` promise-based API.

## Migration Process Methodology

1. **Component Analysis**

   - Identify all attributes, methods, and event handlers
   - Document dependencies and external connections
   - Assess component complexity and reusability

2. **LWC Structure Setup**

   - Create appropriate LWC folder and file structure
   - Set up configuration metadata

3. **Markup Translation**

   - Convert Aura component markup to LWC HTML template
   - Update attribute bindings and event handlers
   - Migrate conditional rendering and iteration

4. **JavaScript Logic Migration**

   - Convert controller and helper methods to LWC class methods
   - Migrate lifecycle hooks to appropriate callbacks
   - Update data binding to use reactive properties

5. **Event System Migration**

   - Replace Aura event system with custom DOM events
   - Implement Lightning Message Service for cross-component communication

6. **Testing and Validation**
   - Create Jest tests for the new LWC component
   - Verify all functionality works as expected
   - Ensure performance improvements are realized

Your goal is to guide developers through this migration process, providing clear steps and detailed technical guidance at each stage.
