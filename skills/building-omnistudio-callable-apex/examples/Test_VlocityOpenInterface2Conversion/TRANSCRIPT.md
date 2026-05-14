# Reasoning Transcript: VlocityOpenInterface2 → Callable Conversion (MyCustomRemoteClass)

This document records the reasoning process and skills used to convert `MyCustomRemoteClass.cls` (VlocityOpenInterface2) to `MyCustomCallable.cls` and create `MyCustomCallableTest.cls`.

---

## Task Summary

Convert a VlocityOpenInterface2 implementation (`MyCustomRemoteClass`) to `System.Callable`, add a test class, and document reasoning and skills used.

---

## Source Analysis

**Original class:** `MyCustomRemoteClass.cls`

- **Implements:** `omnistudio.VlocityOpenInterface2`
- **Action:** `calculateTotal`
- **Input contract:** `inputMap` with keys `price` (Decimal), `quantity` (Decimal)
- **Output contract:** `outputMap.put('total', price * qty)`
- **Behavior:** Single action; returns `true` on success, `false` for unsupported methods

---

## Skills Applied

### 1. **building-omnistudio-callable-apex** (Primary)

**Path:** `skills/building-omnistudio-callable-apex/SKILL.md`  
**Trigger:** Callable implementations, VlocityOpenInterface, migration to System.Callable

**Application:**

- **Migration guidance (SKILL § Migration: VlocityOpenInterface to System.Callable):**
  - Preserved action name: `calculateTotal` → `action` in `call()`
  - Pass `inputMap` and `options` as keys in `args`: `{ 'inputMap' => inputMap, 'options' => options }`
  - Return response envelope instead of mutating `outputMap`
  - Keep `call()` thin; delegate to `calculateTotal(inputMap, options)`
  - Backward compatibility: if `args` lacks `inputMap`, treat `args` as `inputMap`

- **Callable skeleton (SKILL § Phase 3 – Callable skeleton):**
  - Extracted `inputMap` and `options` from `args` with null guards
  - `switch on action` with `when else` throwing `IndustriesCallableException`

- **Response envelope:**
  ```
  { success, data: { total }, errors }
  ```

- **Input validation:** Added `toDecimal()` and `toInteger()` type coercion (OmniScript often passes strings); return error envelope when `price` or `quantity` is null or invalid.

- **Contract & Dispatch:** Explicit action list; typed exception for unsupported actions.

---

### 2. **generating-apex** (Reference)

**Path:** `~/.claude/skills/generating-apex/SKILL.md`  
**Trigger:** Apex classes, code quality

**Application:**

- ApexDoc on class and key methods
- `with sharing` on the callable class
- Null-safe input handling; no direct casts without validation
- Naming: `MyCustomCallable` (callable pattern; preserves "MyCustom" from source)

---

### 3. **running-apex-tests** (Reference)

**Path:** `~/.claude/skills/running-apex-tests/SKILL.md`  
**Trigger:** Apex tests

**Application:**

- **Positive:** Success with `inputMap`/`options`, flat args, and string inputs (type coercion)
- **Contract:** Missing `price`, missing `quantity`, null args → error envelope
- **Negative:** Unsupported action throws `IndustriesCallableException`
- GIVEN/WHEN/THEN implied via clear assertions and method names

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Preserve lowercase keys** (`price`, `quantity`, `total`) | Original `MyCustomRemoteClass` used lowercase; maintains contract for existing Integration Procedures / OmniScripts |
| **Response envelope** | Aligns with Industries pattern; callers get consistent `success`, `data`, `errors` shape |
| **Error envelope for validation** | Return structured errors instead of throwing; callers can handle without try/catch |
| **Exception for unsupported action** | Skill pattern; `IndustriesCallableException` makes misuse explicit |
| **Type coercion helpers** | OmniScript/Integration Procedures often pass strings; `toDecimal`/`toInteger` allow `'25.00'`, `'4'` etc. |
| **Flat args fallback** | When `args` lacks `inputMap`, treat `args` as `inputMap` for backward compatibility |

---

## Artifacts Produced

1. **IndustriesCallableException.cls** – Custom exception for unsupported actions  
2. **MyCustomCallable.cls** – Callable implementation (converted from MyCustomRemoteClass)  
3. **MyCustomCallableTest.cls** – Test class (7 methods)  
4. **TRANSCRIPT.md** – This reasoning transcript  

---

## Contract Mapping (Before → After)

| VlocityOpenInterface2 | System.Callable |
|----------------------|-----------------|
| `methodName` = `'calculateTotal'` | `action` = `'calculateTotal'` |
| `inputMap.get('price')`, `inputMap.get('quantity')` | Same keys in `args.inputMap` or flat `args` |
| `outputMap.put('total', ...)` | `return { success => true, data => { total => ... } }` |
| `return false` for unsupported | `throw IndustriesCallableException` |
| `options` (unused in original) | Passed through for future use |

---

## Deployment Notes

Copy the `.cls` files into your Salesforce project under `force-app/main/default/classes/` and add the corresponding `-meta.xml` files. No SOQL/DML; no special API version requirements.
