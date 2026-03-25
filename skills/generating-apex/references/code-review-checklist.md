# Apex Code Review Checklist

Quick-reference checklist for reviewing Apex code. Each item links to the reference file with full examples and guidance.

---

## Critical Issues (Must Fix)

### Bulkification
*Full guide: [bulkification-guide.md](bulkification-guide.md)*

| Check | Status |
|-------|--------|
| No SOQL queries inside loops | ☐ |
| No DML statements inside loops | ☐ |
| Uses collections (List, Set, Map) properly | ☐ |
| Handles 200+ records per trigger batch | ☐ |

---

### Security
*Full guide: [security-guide.md](security-guide.md)*

| Check | Status |
|-------|--------|
| Uses `WITH USER_MODE` for SOQL | ☐ |
| Uses bind variables (no SOQL injection) | ☐ |
| Uses `with sharing` by default | ☐ |
| `without sharing` justified and documented | ☐ |
| No hardcoded credentials | ☐ |
| No hardcoded Record IDs | ☐ |
| Named Credentials used for callouts | ☐ |

---


## Important Issues (Should Fix)

### Architecture
*Full guide: [trigger-actions-framework.md](trigger-actions-framework.md), [design-patterns.md](design-patterns.md)*

| Check | Status |
|-------|--------|
| One trigger per object | ☐ |
| Uses Trigger Actions Framework (or similar) | ☐ |
| Logic-less triggers (delegates to handler) | ☐ |
| Service layer for business logic | ☐ |
| Selector pattern for queries | ☐ |
| Single responsibility per class | ☐ |

---

### Error Handling
*Full guide: [anti-patterns.md](anti-patterns.md)*

| Check | Status |
|-------|--------|
| Catches specific exceptions before generic | ☐ |
| No empty catch blocks | ☐ |
| Errors logged appropriately | ☐ |
| Uses `AuraHandledException` for LWC | ☐ |
| Custom exceptions for business logic | ☐ |
| Exception cause chains preserved | ☐ |

---

### Naming
*Full guide: [naming-conventions.md](naming-conventions.md)*

| Check | Status |
|-------|--------|
| Class names are PascalCase | ☐ |
| Method names are camelCase verbs | ☐ |
| Variable names are descriptive | ☐ |
| No abbreviations (tks, rec, acc) | ☐ |
| Constants are UPPER_SNAKE_CASE | ☐ |
| Collections indicate type (accountsById) | ☐ |

---

### Performance
*Full guide: [bulkification-guide.md](bulkification-guide.md)*

| Check | Status |
|-------|--------|
| Uses `Limits` class to monitor | ☐ |
| Caches expensive operations | ☐ |
| Heavy processing in async | ☐ |
| SOQL filters on indexed fields | ☐ |
| Variables go out of scope (heap) | ☐ |
| No class-level large collections | ☐ |

---

## Minor Issues (Nice to Fix)

### Clean Code
*Full guide: [anti-patterns.md](anti-patterns.md), [best-practices.md](best-practices.md)*

| Check | Status |
|-------|--------|
| No double negatives (`!= false`) | ☐ |
| Boolean conditions extracted to variables | ☐ |
| Methods do one thing | ☐ |
| No side effects in methods | ☐ |
| Consistent formatting | ☐ |
| ApexDoc comments on public methods | ☐ |

---

## Review Process

1. **Static Analysis**: Run PMD / Salesforce Code Analyzer
2. **Bulkification**: Verify no SOQL/DML in loops
3. **Security**: Check sharing, CRUD/FLS, injection
4. **Architecture**: Verify patterns and separation
5. **Naming**: Check conventions
6. **Performance**: Review limits awareness
7. **Documentation**: Verify ApexDoc comments

---