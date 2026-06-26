# Fix Application: Before & After

This example demonstrates engine-provided auto-fix behavior on a small codebase.

## Initial Scan Results

**Command:**
```bash
sf code-analyzer run --rule-selector Recommended --output-file ./results.json --include-fixes
```

**Summary:**
- Total violations: 248
- Fixable violations: 67 (27%)

### Fixable Rules

| Rule | Engine | Severity | Count |
|------|--------|----------|-------|
| no-var | eslint | 3 | 42 |
| prefer-const | eslint | 3 | 18 |
| @salesforce-ux/slds/no-hardcoded-values-slds2 | eslint | 4 | 5 |
| no-extra-boolean-cast | eslint | 3 | 2 |

---

## Before Fix: Sample Violations

### Violation 1: no-var
**File:** `force-app/main/default/lwc/accountCard/accountCard.js:12`

```javascript
export default class AccountCard extends LightningElement {
    handleClick() {
        var accountId = this.recordId;  // ← violation
        var data = this.fetchData(accountId);  // ← violation
        this.processData(data);
    }
}
```

### Violation 2: prefer-const
**File:** `force-app/main/default/lwc/utils/dataProcessor.js:8`

```javascript
export function processRecords(records) {
    let result = [];  // ← violation (never reassigned)
    records.forEach(r => result.push(transform(r)));
    return result;
}
```

### Violation 3: @salesforce-ux/slds/no-hardcoded-values-slds2
**File:** `force-app/main/default/lwc/accountCard/accountCard.css:4`

```css
.account-card {
    border-radius: 4px;  /* ← violation */
    padding: 16px;  /* ← violation */
}
```

---

## Apply Fixes

**Command:**
```bash
node <skill_dir>/scripts/apply-fixes.js ./results.json
```

**Output:**
```json
{
  "success": true,
  "filesModified": 15,
  "fixesApplied": 67,
  "fixesSkipped": 0
}
```

---

## After Fix: Corrected Code

### Fix 1: no-var → let
**File:** `force-app/main/default/lwc/accountCard/accountCard.js:12`

```javascript
export default class AccountCard extends LightningElement {
    handleClick() {
        let accountId = this.recordId;  // ✓ fixed
        let data = this.fetchData(accountId);  // ✓ fixed
        this.processData(data);
    }
}
```

### Fix 2: let → const
**File:** `force-app/main/default/lwc/utils/dataProcessor.js:8`

```javascript
export function processRecords(records) {
    const result = [];  // ✓ fixed
    records.forEach(r => result.push(transform(r)));
    return result;
}
```

### Fix 3: Hardcoded values → SLDS tokens
**File:** `force-app/main/default/lwc/accountCard/accountCard.css:4`

```css
.account-card {
    border-radius: var(--slds-c-card-radius-border);  /* ✓ fixed */
    padding: var(--slds-c-card-spacing-block);  /* ✓ fixed */
}
```

---

## Verification Scan

**Command:**
```bash
sf code-analyzer run --rule-selector Recommended --output-file ./results-after.json --include-fixes
```

**Summary:**
- Total violations: 181 (↓ 67 from 248)
- Fixable violations: 0

**Result:** All 67 fixable violations resolved. Remaining 181 violations require manual fixes (e.g., ApexDoc comments, CRUD checks).

---

## Key Takeaways

1. **Engine-provided fixes are safe**: They're deterministic transformations, not AI-generated code.
2. **Apply, then verify**: Always re-scan after applying fixes to confirm no regressions.
3. **Not all violations are fixable**: Security issues like CRUD violations require manual code review.
4. **Files modified count ≠ fixes count**: Multiple violations in one file count as one file modification.
