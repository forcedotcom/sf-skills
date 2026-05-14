---
name: building-omnistudio-callable-apex
description: "Salesforce Industries Common Core (OmniStudio/Vlocity) Apex callable generation and review skill with 120-point scoring. Use when creating, reviewing, or migrating Industries callable Apex implementations. TRIGGER when: user creates or reviews System.Callable classes, migrates VlocityOpenInterface or VlocityOpenInterface2, or builds Industries callable extensions used by OmniStudio, Integration Procedures, or DataRaptors. DO NOT TRIGGER when: generic Apex classes or triggers (use generating-apex), building Integration Procedures (use building-omnistudio-integration-procedure), authoring OmniScripts (use building-omnistudio-omniscript), configuring Data Mappers (use building-omnistudio-datamapper), or analyzing namespace/dependency issues (use analyzing-omnistudio-dependencies)."
license: MIT
metadata:
  version: "1.0"
---

# building-omnistudio-callable-apex: Callable Apex for Salesforce Industries Common Core

Specialist for Salesforce Industries Common Core callable Apex implementations. Produce secure,
deterministic, and configurable Apex that cleanly integrates with OmniStudio and Industries
extension points.

## Scope

- **In scope**: Creating `System.Callable` classes for Industries extension points; reviewing callable implementations for correctness and risks; migrating `VlocityOpenInterface` / `VlocityOpenInterface2` to `System.Callable`; 120-point scoring and validation
- **Out of scope**: Generic Apex classes without callable interface (use `generating-apex`); building Integration Procedures (use `building-omnistudio-integration-procedure`); authoring OmniScripts (use `building-omnistudio-omniscript`); deploying Apex classes (use `deploying-metadata`)

---

## Core Responsibilities

1. **Callable Generation**: Build `System.Callable` classes with safe action dispatch
2. **Callable Review**: Audit existing callable implementations for correctness and risks
3. **Validation & Scoring**: Evaluate against the 120-point rubric
4. **Industries Fit**: Ensure compatibility with OmniStudio/Industries extension points

---

## Workflow (4-Phase Pattern)

### Phase 1: Requirements Gathering

Ask for:
- Entry point (OmniScript, Integration Procedure, DataRaptor, or other Industries hook)
- Action names (strings passed into `call`)
- Input/output contract (required keys, types, and response shape)
- Data access needs (objects/fields, CRUD/FLS (Create/Read/Update/Delete and Field-Level Security) rules)
- Side effects (DML, callouts, async requirements)

Then:
1. Scan for existing callable classes: `Glob: **/*Callable*.cls`
2. Identify shared utilities or base classes used for Industries extensions
3. Create a task list

---

### Phase 2: Design & Contract Definition

**Define the callable contract**:
- Action list (explicit, versioned strings)
- Input schema (required keys + types)
- Output schema (consistent response envelope)

**Recommended response envelope**:
```
{
  "success": true|false,
  "data": {...},
  "errors": [ { "code": "...", "message": "..." } ]
}
```

**Action dispatch rules**:
- Use `switch on action`
- Default case throws a typed exception
- No dynamic method invocation or reflection

**VlocityOpenInterface / VlocityOpenInterface2 contract mapping**:

When designing for legacy Open Interface extensions (or dual Callable + Open Interface support), map the signature:

```
invokeMethod(String methodName, Map<String, Object> inputMap, Map<String, Object> outputMap, Map<String, Object> options)
```

| Parameter | Role | Callable equivalent |
|-----------|------|---------------------|
| `methodName` | Action selector (same semantics as `action`) | `action` in `call(action, args)` |
| `inputMap` | Primary input data (required keys, types) | `args.get('inputMap')` |
| `outputMap` | Mutable map where results are written (out-by-reference) | Return value; Callable returns envelope instead |
| `options` | Additional context (parent DataRaptor/OmniScript context, invocation metadata) | `args.get('options')` |

Design rules for Open Interface contracts:
- Treat `inputMap` and `options` as the combined input schema
- Define what keys must be written to `outputMap` per action (success and error cases)
- Preserve `methodName` strings so they align with Callable `action` strings
- Document whether `options` is required, optional, or unused for each action

---

### Phase 3: Implementation Pattern

**Vanilla System.Callable** (flat args, no Open Interface coupling):

**Read `assets/pattern_callable_vanilla.cls`** before generating — use when callers pass flat args and no VlocityOpenInterface integration is required.

**Callable skeleton** (same inputs as VlocityOpenInterface):

**Read `assets/pattern_callable_openinterface.cls`** before generating — use `inputMap` and `options` keys in `args` when integrating with Open Interface or when callers pass that structure.

**Input format**: Callers pass `args` as `{ 'inputMap' => Map<String, Object>, 'options' => Map<String, Object> }`. For backward compatibility with flat callers, if `args` lacks `'inputMap'`, treat `args` itself as `inputMap` and use an empty map for `options`.

**Implementation rules**:
1. Keep `call()` thin; delegate to private methods or service classes
2. Validate and coerce input types early (null-safe)
3. Enforce CRUD/FLS (Create/Read/Update/Delete and Field-Level Security) and sharing (`with sharing`, `Security.stripInaccessible()`)
4. Bulkify when args include record collections
5. Use `WITH USER_MODE` for SOQL when appropriate
6. **Namespace handling**: `System.Callable` is a standard interface (no namespace prefix required); `omnistudio.VlocityOpenInterface2` uses the managed `omnistudio` package namespace — always qualify it. If the callable class will be deployed into a namespaced managed package, ask the user for the namespace prefix and apply it to custom class names (e.g., `myns__Industries_XxxCallable`)

**VlocityOpenInterface / VlocityOpenInterface2 implementation**:

When implementing `omnistudio.VlocityOpenInterface` or `omnistudio.VlocityOpenInterface2`, use the signature:

```apex
global Boolean invokeMethod(String methodName, Map<String, Object> inputMap,
                           Map<String, Object> outputMap, Map<String, Object> options)
```

**Read `assets/pattern_openinterface.cls`** before generating — complete `VlocityOpenInterface2` skeleton with `switch on` dispatch and `outputMap` contract.

Open Interface implementation rules:
- Write results into `outputMap` via `putAll()` or individual `put()` calls; do not return the envelope from `invokeMethod`
- Return `true` for success, `false` for unsupported or failed actions
- Use the same internal private methods as the Callable (same `inputMap` and `options` parameters); only the entry point differs
- Populate `outputMap` with the same envelope shape (`success`, `data`, `errors`) for consistency

Both Callable and Open Interface accept the same inputs (`inputMap`, `options`) and delegate to identical private method signatures for shared logic.

---

### Phase 4: Testing & Validation

Minimum tests:
- **Positive**: Supported action executes successfully
- **Negative**: Unsupported action throws expected exception
- **Contract**: Missing/invalid inputs return error envelope
- **Bulk**: Handles list inputs without hitting limits

**Read `assets/pattern_test_class.cls`** — complete test class skeleton (positive, negative, contract, bulk, and null-args cases) before generating tests.

---

## Migration: VlocityOpenInterface to System.Callable

When modernizing Industries extensions, move `VlocityOpenInterface` or
`VlocityOpenInterface2` implementations to `System.Callable` and keep the
action contract stable.

**Guidance**:
- Preserve action names (`methodName`) as `action` strings in `call()`
- Pass `inputMap` and `options` as keys in `args`: `{ 'inputMap' => inputMap, 'options' => options }`
- Return a consistent response envelope instead of mutating `outMap`
- Keep `call()` thin; delegate to the same internal methods with `(inputMap, options)` signature
- Add tests for each action and unsupported action

**Read `assets/pattern_migration.cls`** — annotated before/after migration example (VlocityOpenInterface2 → System.Callable) before starting migration work.

---

## Best Practices (120-Point Scoring)

| Category | Points | Key Rules |
|----------|--------|-----------|
| **Contract & Dispatch** | 20 | Explicit action list; `switch on`; versioned action strings |
| **Input Validation** | 20 | Required keys validated; types coerced safely; null guards |
| **Security** | 20 | `with sharing`; CRUD/FLS checks; `Security.stripInaccessible()` |
| **Error Handling** | 15 | Typed exceptions; consistent error envelope; no empty catch |
| **Bulkification & Limits** | 20 | No SOQL/DML in loops; supports list inputs |
| **Testing** | 15 | Positive/negative/contract/bulk tests |
| **Documentation** | 10 | ApexDoc (`/** ... */` block comments — Salesforce Apex documentation standard) for class and action methods |

**Thresholds**: ✅ 90+ (Ready) | ⚠️ 70-89 (Review) | ❌ <70 (Block)

---

## ⛔ Guardrails (Mandatory)

Stop and ask the user if any of these would be introduced:
- Dynamic method execution based on user input (no reflection)
- SOQL/DML inside loops
- `without sharing` on callable classes
- Silent failures (empty catch, swallowed exceptions)
- Inconsistent response shapes across actions

---

## Gotchas

| Issue | Resolution |
|-------|-----------|
| Caller passes flat args but code expects `inputMap` key | Guard defensively: if `args` lacks `'inputMap'` key, treat `args` itself as the input map |
| `call()` receives `null` for `args` | Always null-check `args` before accessing keys; initialize to empty map if null |
| Test class uses `(Map<String, Object>) svc.call(...)` but call returns a wrong type | Ensure every action returns the same envelope type (`Map<String, Object>`) — mixed return types break callers |
| VlocityOpenInterface2 migration breaks callers that read `outputMap` by reference | After migrating to Callable, callers must read the return value instead of reading `outputMap` — update all callers |
| `IndustriesCallableException` class missing in project | This custom exception must be deployed alongside the callable class — include it in every deployment package |
| Org has both legacy Open Interface and new Callable wired to same action | Only one entry point should be active at a time; disable the old interface after confirming the callable works |

---

## Common Anti-Patterns

- `call()` contains business logic instead of delegating
- Action names are unversioned or not documented
- Input maps assumed to have keys without checks
- Mixed response types (sometimes Map, sometimes String)
- No tests for unsupported actions

---

## Cross-Skill Integration

| Skill | When to Use | Example |
|-------|-------------|---------|
| generating-apex | General Apex work beyond callable implementations | "Create trigger for Account" |
| generating-custom-object / generating-custom-field | Verify object/field availability before coding | "Describe Product2 fields" |
| deploying-metadata | Validate/deploy callable classes | "Deploy to sandbox" |

---

## Reference Skill

Use the core Apex standards, testing patterns, and guardrails in:
- [skills/generating-apex/SKILL.md](../generating-apex/SKILL.md)

---

## Bundled Examples

- [examples/Test_QuoteByProductCallable/](examples/Test_QuoteByProductCallable/) — read-only query example with `WITH USER_MODE`
- [examples/Test_VlocityOpenInterfaceConversion/](examples/Test_VlocityOpenInterfaceConversion/) — migration from legacy `VlocityOpenInterface`
- [examples/Test_VlocityOpenInterface2Conversion/](examples/Test_VlocityOpenInterface2Conversion/) — migration from `VlocityOpenInterface2`

## Output Expectations

Deliverables produced by this skill:

- `<ClassName>.cls` — Callable class implementing `System.Callable` with `switch on action` dispatch
- `<ClassName>Test.cls` — Test class with positive, negative, contract, and bulk test methods
- `IndustriesCallableException.cls` — Custom exception class (if not already present in the project)

---

## Notes

- Prefer deterministic, side-effect-aware callable actions
- Keep action contracts stable; introduce new actions for breaking changes
- Avoid long-running work in synchronous callables; use async when needed

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/pattern_callable_vanilla.cls` | Phase 3 — vanilla `System.Callable` skeleton (flat args, no Open Interface coupling) |
| `assets/pattern_callable_openinterface.cls` | Phase 3 — `System.Callable` skeleton with `inputMap`/`options` args (Open Interface-compatible) |
| `assets/pattern_openinterface.cls` | Phase 3 — `VlocityOpenInterface2` skeleton with `switch on` dispatch and `outputMap` contract |
| `assets/pattern_test_class.cls` | Phase 4 — test class skeleton (positive, negative, contract, bulk, and null-args cases) |
| `assets/pattern_migration.cls` | Migration — annotated before/after migration pattern (VlocityOpenInterface2 → System.Callable) |
| `examples/Test_QuoteByProductCallable/Industries_QuoteByProductCallable.cls` | Phase 3 — complete callable implementation with `WITH USER_MODE` SOQL and error envelope |
| `examples/Test_QuoteByProductCallable/Industries_QuoteByProductCallableTest.cls` | Phase 4 — full test class covering positive, contract, and unsupported-action cases |
| `examples/Test_QuoteByProductCallable/IndustriesCallableException.cls` | Phase 3 — custom exception pattern for unsupported actions |
| `examples/Test_QuoteByProductCallable/TRANSCRIPT.md` | Reference — reasoning transcript for the Quote-by-Product callable example |
| `examples/Test_VlocityOpenInterfaceConversion/MyCustomCallable.cls` | Phase 3 — migration pattern from legacy `VlocityOpenInterface` |
| `examples/Test_VlocityOpenInterfaceConversion/MyCustomCallableTest.cls` | Phase 4 — test class for VlocityOpenInterface migration example |
| `examples/Test_VlocityOpenInterfaceConversion/IndustriesCallableException.cls` | Phase 3 — custom exception class deployed alongside VlocityOpenInterface conversion |
| `examples/Test_VlocityOpenInterfaceConversion/MyCustomVlocityOpenInterface2.cls` | Phase 3 — the original legacy VlocityOpenInterface2 class before migration |
| `examples/Test_VlocityOpenInterfaceConversion/TRANSCRIPT.md` | Reference — reasoning transcript for VlocityOpenInterface conversion |
| `examples/Test_VlocityOpenInterface2Conversion/MyCustomCallable.cls` | Phase 3 — migration pattern from `VlocityOpenInterface2` |
| `examples/Test_VlocityOpenInterface2Conversion/MyCustomCallableTest.cls` | Phase 4 — test class for VlocityOpenInterface2 migration example |
| `examples/Test_VlocityOpenInterface2Conversion/IndustriesCallableException.cls` | Phase 3 — custom exception class deployed alongside VlocityOpenInterface2 conversion |
| `examples/Test_VlocityOpenInterface2Conversion/MyCustomRemoteClass.cls` | Phase 3 — remote class used by the VlocityOpenInterface2 migration example |
| `examples/Test_VlocityOpenInterface2Conversion/TRANSCRIPT.md` | Reference — reasoning transcript for VlocityOpenInterface2 conversion |
