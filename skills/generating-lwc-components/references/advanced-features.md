<!-- Parent: generating-lwc-components/SKILL.md -->

# Flow Screen Integration & Advanced Features

## Flow Screen Integration

LWC components can be embedded in Flow Screens for custom UI experiences within guided processes.

### Key Concepts

| Mechanism | Direction | Purpose |
|-----------|-----------|---------|
| `@api` with `role="inputOnly"` | Flow → LWC | Pass context data |
| `FlowAttributeChangeEvent` | LWC → Flow | Return user selections |
| `FlowNavigationFinishEvent` | LWC → Flow | Programmatic Next/Back/Finish |
| `availableActions` | Flow → LWC | Check available navigation |

### Quick Example

```javascript
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

@api recordId;           // Input from Flow
@api selectedRecordId;   // Output to Flow
@api availableActions = [];

handleSelect(event) {
    this.selectedRecordId = event.detail.id;
    // CRITICAL: Notify Flow of the change
    this.dispatchEvent(new FlowAttributeChangeEvent(
        'selectedRecordId',
        this.selectedRecordId
    ));
}

handleNext() {
    if (this.availableActions.includes('NEXT')) {
        this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
    }
}
```

**For complete Flow integration patterns, see:**
- [references/flow-integration-guide.md](../references/flow-integration-guide.md)
- [references/triangle-pattern.md](../references/triangle-pattern.md)

---

## TypeScript Support (Spring '26 - GA in API 66.0)

Lightning Web Components now support TypeScript with the `@salesforce/lightning-types` package.

```typescript
interface AccountRecord {
    Id: string;
    Name: string;
    Industry?: string;
}

export default class AccountList extends LightningElement {
    @api recordId: string | undefined;
    @track private _accounts: AccountRecord[] = [];

    @wire(getAccounts, { maxRecords: '$maxRecords' })
    wiredAccounts(result: WireResult<AccountRecord[]>): void {
        // Typed wire handling...
    }
}
```

**Requirements**: TypeScript 5.4.5+, `@salesforce/lightning-types` package

---

## LWC in Dashboards (Beta - Spring '26)

Components can be embedded as custom dashboard widgets.

```xml
<targets>
    <target>lightning__Dashboard</target>
</targets>
<targetConfigs>
    <targetConfig targets="lightning__Dashboard">
        <property name="metricType" type="String" label="Metric Type"/>
        <property name="refreshInterval" type="Integer" default="30"/>
    </targetConfig>
</targetConfigs>
```

**Note**: Requires enablement via Salesforce Customer Support

---

## Agentforce Discoverability (Spring '26 - GA in API 66.0)

Make components discoverable by Agentforce agents:

```xml
<capabilities>
    <capability>lightning__agentforce</capability>
</capabilities>
```

**Best Practices**:
- Clear `masterLabel` and `description`
- Detailed property descriptions
- Semantic naming conventions
