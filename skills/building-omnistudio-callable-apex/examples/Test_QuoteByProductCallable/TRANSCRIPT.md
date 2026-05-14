# Reasoning Transcript: Industries Quote-by-Product Callable

This document records the reasoning process and skills used to generate `Industries_QuoteByProductCallable.cls` and `Industries_QuoteByProductCallableTest.cls`.

---

## Task Summary

Create a callable Apex class that finds all Quotes on an Account that have at least one QuoteLineItem with a specified Product2.ProductCode, plus a supporting test class.

---

## Skills Applied

### 1. **building-omnistudio-callable-apex** (Primary)

**Path:** `~/.claude/skills/building-omnistudio-callable-apex/SKILL.md`  
**Trigger:** Callable implementations, OmniStudio, Vlocity, Industries Apex extensions

**Application:**

- **Phase 1 – Requirements Gathering:**  
  Entry point: Integration Procedure / OmniScript. Action: `findQuotesByProductCode`.  
  Inputs: `accountId` (String), `productCode` (String).  
  Data: Quote, QuoteLineItem, Product2. No side effects (read-only).

- **Phase 2 – Contract Definition:**  
  Response envelope: `{ success, data: { quotes }, errors }`.  
  Action dispatch via `switch on action` with typed exception for unsupported actions.

- **Phase 3 – Implementation Pattern:**  
  - `call()` kept thin; logic delegated to `findQuotesByProductCode(args)`  
  - Input validation for `accountId` and `productCode` (blank checks)  
  - `with sharing` on the callable class  
  - SOQL with `WITH USER_MODE` for CRUD/FLS  
  - No SOQL/DML in loops  
  - Consistent envelope shape

- **Phase 4 – Testing:**  
  Positive, negative, contract, and unsupported-action tests per skill requirements.

- **Exception Class:**  
  `IndustriesCallableException` used per skill pattern for unsupported actions.

---

### 2. **generating-apex** (Reference)

**Path:** `~/.claude/skills/generating-apex/SKILL.md`  
**Trigger:** Apex classes, code quality

**Application:**

- ApexDoc on the class and action method  
- Naming: `Industries_QuoteByProductCallable` (callable pattern)  
- Null-safe input handling  
- Clear separation of concerns

---

### 3. **running-apex-tests** (Reference)

**Path:** `~/.claude/skills/running-apex-tests/SKILL.md`  
**Trigger:** Apex tests

**Application:**

- `@TestSetup` for shared data (Account, Opportunity, Product2, PricebookEntry, Quote, QuoteLineItem)  
- Positive: success case and empty-result case  
- Contract: missing `accountId`, missing `productCode`, null args  
- Negative: unsupported action throws `IndustriesCallableException`  
- GIVEN/WHEN/THEN comments (adapted from basic-test template)

---

### 4. **querying-soql / handling-sf-data** (Reference)

**Paths:** `skills/handling-sf-data/assets/soql/`, `skills/generating-mermaid-diagrams/assets/datamodel/`  
**Trigger:** SOQL and data model

**Application:**

- Quote–Opportunity–Account: `Quote.Opportunity.AccountId`  
- QuoteLineItem–Product2: `QuoteLineItem.Product2.ProductCode`  
- Subquery: `Id IN (SELECT QuoteId FROM QuoteLineItem WHERE Product2.ProductCode = :productCode)`  
- Confirmation that Product2.ProductCode is queryable from QuoteLineItem

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Response envelope** | Aligns with Industries pattern: `success`, `data`, `errors` for consistent handling by Integration Procedures |
| **Error envelope for validation** | Return structured errors instead of throwing; callers can handle without try/catch |
| **Exception for unsupported action** | Follows skill pattern; `IndustriesCallableException` makes misuse explicit |
| **`IndustriesCallableException` in separate class** | Reusable across callable classes, matches skill examples |
| **`WITH USER_MODE` on SOQL** | Enforces CRUD/FLS; requires API 59+ |
| **Quote ↔ Account path** | Standard model: `Quote.Opportunity.AccountId` (no direct Quote → Account) |
| **Product code on Product2** | Standard `Product2.ProductCode` via `QuoteLineItem.Product2` relationship |

---

## Artifacts Produced

1. **IndustriesCallableException.cls** – Custom exception for unsupported actions  
2. **Industries_QuoteByProductCallable.cls** – Callable implementation  
3. **Industries_QuoteByProductCallableTest.cls** – Test class (6 methods)  
4. **TRANSCRIPT.md** – This reasoning transcript  

---

## Deployment Notes

Copy the `.cls` files into your Salesforce project under `force-app/main/default/classes/` and add the corresponding `-meta.xml` files with `apiVersion` 59.0 or higher (for `WITH USER_MODE`). If your org uses an older API, remove `WITH USER_MODE` from the SOQL query.
