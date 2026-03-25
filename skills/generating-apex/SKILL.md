---
name: generating-apex
description: Primary Apex authoring skill for class generation, refactoring, and review. ALWAYS ACTIVATE when the user mentions Apex, .cls, triggers, or asks to create/refactor a class (service, selector, domain, batch, queueable, schedulable, invocable, DTO, utility, interface, abstract, exception, REST resource). Use this skill for requests involving SObject CRUD, mapping collections, fetching related records, scheduled jobs, batch jobs, trigger design, @AuraEnabled controllers, @RestResource endpoints, custom REST APIs, or code review of existing Apex.
---

# Generating Apex

Use this skill for production-grade Apex: new classes, selectors, services, async jobs,
invocable methods, and triggers; and for evidence-based review of existing `.cls`.

## When This Skill Owns the Task

- Any Apex class generation or refactor (service, selector, domain, DTO/wrapper, utility, interface, abstract, exception)
- Trigger design and trigger-framework decisions
- Async or orchestration: Batch, Queueable (incl. Finalizer), Schedulable, CursorStep, `@InvocableMethod`
- `@AuraEnabled` controllers for LWC/Aura
- `@RestResource` endpoints for custom REST APIs
- Review of bulkification, sharing, security, or maintainability


---

## Required Inputs

Gather or infer before authoring:

- Class type (service, selector, domain, batch, queueable, schedulable, invocable, trigger, trigger action, DTO, utility, interface, abstract, exception, REST resource)
- Target object(s) and business goal
- Class name (derive using the naming table below)
- Net-new vs refactor/fix; any org/API constraints
- Deployment targets

Defaults unless specified:
- Sharing: `with sharing` (see sharing rules per type below)
- Access: `public` (use `global` only when required by managed packages or `@InvocableMethod`)
- API version: `66.0` (minimum version)
- ApexDoc comments: yes

---

## Workflow
All steps in this workflow are MANDATORY and must be executed in order. Execute every step without skipping, merging, or reordering. If a step is blocked or seemingly not applicable, STOP and request the missing context, or explicitly mark it as "N/A" with a one-sentence justification in the final report before proceeding. Continue only when the gate for the current step is satisfied.

1. [MANDATORY] **Discover project conventions**
   - Service–Selector–Domain layering, logging utilities
   - Existing classes/triggers and current trigger framework or handler pattern
   - Whether Trigger Actions Framework (TAF) is already in use

2. [MANDATORY] **Choose the smallest correct pattern** (see Type-Specific Guidance below)

3. [MANDATORY] **Review templates and assets**
   - Check this skill’s `templates/` and `assets/`
   - For any test class work, always read and use `generating-apex-test` skill

4. [MANDATORY] **Author with guardrails** — apply every rule in the Rules section below
   - Generate `{ClassName}.cls` with ApexDoc
   - Generate `{ClassName}.cls-meta.xml`

5. [MANDATORY] **Generate test classes** — Use the skill `generating-apex-test` and follow its complete workflow to generate `{ClassName}Test.cls` and `{ClassName}Test.cls-meta.xml`. You MUST use that skill now and execute its instructions before proceeding to Step 6. After the test skill workflow completes, return here and continue with Step 6 — do NOT end the task.

6. [MANDATORY] **Static analysis — DO NOT SKIP**
   - Execute the MCP tool `run_code_analyzer` on the newly generated/updated files
   - Remediate all violations with severity levels `sev0`, `sev1`, and `sev2`
   - Re-run `run_code_analyzer` until no `sev0–sev2` issues remain

7. [MANDATORY] **Execute Apex tests**
   - Run the org’s Apex test suite including `{ClassName}Test`
   - All test authoring, failure remediation, and coverage improvements MUST be performed by reading and following `skills/generating-apex-test/SKILL.md`; iterate until green

8. [MANDATORY] **Report** using the output format at the bottom of this file

9. [MANDATORY] **Enforce cross-skill boundaries**
   - Test class creation, updates, refactors, data setup, and advanced fixtures: ALWAYS delegate by reading and following `skills/generating-apex-test/SKILL.md`
   - NEVER write test code directly in this skill; all test work flows through the test skill

---

## Rules

### Hard-Stop Constraints (Must Enforce)

If any constraint would be violated in generated code, **stop and explain the problem** before proceeding:

| Constraint | Rationale |
|---|---|
| Place all SOQL outside loops | Avoid query governor limits (100 queries) |
| Place all DML outside loops | Avoid DML governor limits (150 statements) |
| Declare a sharing keyword on every class | Prevent unintended `without sharing` defaults and data exposure |
| Use Custom Metadata/Labels/describe calls instead of hardcoded IDs | Ensure portability across orgs |
| Always handle exceptions (log, rethrow, or recover) | Prevent silent failures |
| Use bind variables for all dynamic SOQL with user input | Prevent SOQL injection |
| Use Apex-native collections (`List`, `Map`, `Set`) rather than Java types | Prevent compile errors |
| Verify methods exist in Apex before use | Prevent reliance on non-existent APIs |
| Use `Assert` class instead of `System.assert*` in test classes | Legacy `System.assert`, `System.assertEquals`, `System.assertNotEquals` are deprecated; use `Assert.areEqual`, `Assert.isTrue`, `Assert.fail`, etc. |
| Avoid `System.debug()` in main code paths | Debug statements that concatenate variables into the string consume CPU regardless of logging being enabled; use a logging framework or Custom Metadata–controlled logger instead if required on main code paths |
| Never use `@future` methods | Use Queueable with `System.Finalizer` for all async work; `@future` cannot be called from Batch, cannot chain, and cannot accept non-primitive types |

### Bulkification & Governor Limits

- Collect all SOQL and DML outside of loops; operate on `List`, `Set`, `Map`
- All public APIs accept and process collections; single-record overloads delegate to the bulk method
- In batch/bulk flows, prefer partial-success DML (`Database.update(records, false)`) and process `SaveResult` for errors
- Use `Map<Id, SObject>` constructor for efficient ID-based lookups from query results
- Use `Set<Id>` for deduplication and membership checks; prefer `Set.contains()` over `List.contains()`

### SOQL Optimization

- Use selective queries with proper `WHERE` clauses; use indexed fields (`Id`, `Name`, `OwnerId`, lookup/master-detail fields, `ExternalId` fields, custom indexes) in filters when possible
- `SELECT *` does not exist in SOQL — always specify the exact fields needed
- Apply `LIMIT` clauses to bound result sets; use `ORDER BY` for deterministic results
- When querying Custom Metadata Types (objects ending with `__mdt`), do NOT use SOQL — use the built-in methods (`{CustomMdt__mdt}.getAll().values()`, `getInstance()`, etc.)

### Security

- Default to `with sharing`; document the justification when `without sharing` or `inherited sharing` is chosen
- Use `WITH USER_MODE` in SOQL queries for automatic CRUD/FLS enforcement
- Use bind variables (`:variableName`) for all dynamic SOQL; sanitize queries by binding variables rather than concatenating user input
- For dynamic field/operator names in SOQL, validate against an allowlist or `Schema.describe` before use
- Use `Security.stripInaccessible()` when `WITH USER_MODE` is not available (pre-API 62.0)
- Store credentials and API keys in Named Credentials and reference them in code
- Use `AuraHandledException` for user-facing errors in `@AuraEnabled` methods; ensure messages are user-safe and exclude internal details
- When using `without sharing`, add a Custom Permission check to restrict access

### Error Handling

- Catch specific exceptions before generic `Exception`; include context in messages
- Only wrap code in `try/catch` when the enclosed statements can realistically throw — never add defensive try/catch around simple field assignments, collection additions, or arithmetic; place error handling around DML, callouts, JSON parsing, and type casting where failures are expected
- Preserve exception cause chains: use `new CustomException('message', causedException)` — preserve the original stack trace by passing the cause rather than concatenating `e.getMessage()` into a new exception
- Provide a custom exception class per service domain when meaningful
- In `@AuraEnabled` methods, catch exceptions and rethrow as `AuraHandledException`

### Null Safety

- Add guard clauses for null/empty inputs at the top of every public method
- Return empty collections instead of `null`
- Use safe navigation (`?.`) for chained property access
- Use null coalescing (`??`) for default values
- Prefer `String.isBlank(value)` over manual checks like `value == null || value.trim().isEmpty()`

### Constants & Literals

- Use enums over string constants whenever possible; enum values follow `UPPER_SNAKE_CASE`
- Extract all literal strings and numbers into `private static final` constants or a dedicated constants class
- Use `Label.` custom labels for user-facing strings
- Use Custom Metadata for configurable values (thresholds, mappings, feature flags)
- Never output HTML-escaped entities in code (e.g., `&#39;`); use literal single quotes `'` in Apex string literals

### Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Service | `{SObject}Service` | `AccountService` |
| Selector | `{SObject}Selector` | `AccountSelector` |
| Domain | `{SObject}Domain` | `OpportunityDomain` |
| Batch | `{Descriptive}Batch` | `AccountDeduplicationBatch` |
| Queueable | `{Descriptive}Queueable` | `ExternalSyncQueueable` |
| Schedulable | `{Descriptive}Schedulable` | `DailyCleanupSchedulable` |
| DTO | `{Descriptive}DTO` | `AccountMergeRequestDTO` |
| Wrapper | `{Descriptive}Wrapper` | `OpportunityLineWrapper` |
| Utility | `{Descriptive}Util` | `StringUtil` |
| Interface | `I{Descriptive}` | `INotificationService` |
| Abstract | `Abstract{Descriptive}` | `AbstractIntegrationService` |
| Exception | `{Descriptive}Exception` | `AccountServiceException` |
| REST Resource | `{SObject}RestResource` | `AccountRestResource` |
| Trigger | `{SObject}Trigger` | `AccountTrigger` |
| Trigger Action | `TA_{SObject}_{Action}` | `TA_Account_SetDefaults` |

Additional naming rules:
- Classes: `PascalCase`
- Methods: `camelCase`, start with a verb (`get`, `create`, `process`, `validate`, `is`, `has`)
- Variables: `camelCase`, descriptive nouns; Maps as `{value}By{key}` (e.g., `accountsById`); Sets as `{noun}Ids`
- Constants: `UPPER_SNAKE_CASE`
- Use full descriptive names instead of abbreviations (`acc`, `tks`, `rec`)

### ApexDoc

- Required on the class header and every `public`/`global` method
- Include: brief description, `@param`, `@return`, `@throws`, `@example` where helpful

### Modern Apex Idioms

Prefer current language features:
- Safe navigation: `obj?.Field__c`
- Null coalescing: `value ?? fallback`
- `WITH USER_MODE` over manual CRUD/FLS checks
- `Database.Cursor` (CursorStep) over Batch Apex for new high-throughput jobs
- `Assert` class (`Assert.areEqual`, `Assert.isTrue`, `Assert.fail`, etc.) over legacy `System.assert`, `System.assertEquals`, `System.assertNotEquals` in all test classes

### Code Structure

- Keep each class focused on a single responsibility
- Limit class size to 500 lines of code maximum; split into collaborating classes when exceeded
- Use the Return Early pattern — validate preconditions at the top of methods and return/throw immediately to reduce nesting
- Extract private helpers for methods longer than ~40 lines
- Prefer interfaces for cross-class contracts to keep coupling loose
- Use Dependency Injection (constructor or method parameters) to decouple collaborators and improve testability
- Group related classes in packages/folders when possible (e.g., all Account-related classes together)
- Maintain consistent abstraction levels within a method — keep orchestration separate from low-level implementation

---

## Async Decision Matrix

| Scenario | Default | Key Traits |
|---|---|---|
| Standard async work | **Queueable** | Job ID, chaining, non-primitive types, configurable delay (up to 10 min via `AsyncOptions`), dedup signatures |
| Very large datasets | **Batch Apex** | Chunked processing, max 5 concurrent; use `QueryLocator` for large scopes |
| Modern batch alternative | **CursorStep** (`Database.Cursor`) | 2000-record chunks, higher throughput, no 5-job limit |
| Recurring schedule | **Scheduled Flow** (preferred) or **Schedulable** | Schedulable has 100-job limit; use only when chaining to Batch or needing complex Apex logic |
| Post-job cleanup | **Finalizer** (`System.Finalizer`) | Runs regardless of Queueable success/failure |
| Long-running callouts | **Continuation** | Up to 3 per transaction, 3 parallel |
| Legacy fire-and-forget | `@future` | **Do not use** — replace with Queueable + Finalizer in all new development |
| Delays > 10 minutes | `System.scheduleBatch()` | Schedule a Batch job at a specific future time |

---

## Type-Specific Guidance

### Service
- `with sharing`; stateless; keep public APIs focused and `static` where reasonable
- Delegate all SOQL to Selectors and SObject behavior to Domains
- Wrap business errors in a custom exception (e.g., `AccountServiceException`)

### Selector
- `inherited sharing` (inherits from caller — allows reuse from both `with` and `without sharing` contexts)
- One Selector per SObject or query domain
- Return `List<SObject>` or `Map<Id, SObject>`; maintain a DRY base field list constant and reference it in all SOQL queries — never duplicate the field list inline across methods constant and reference it in all SOQL queries — never duplicate the field list inline across methods
- Accept filter criteria as parameters; always include `WITH USER_MODE`

### Domain
- `with sharing`; encapsulate SObject field defaults, derivations, and validations
- Operate only on in-memory lists; perform SOQL and DML in Services/Selectors
- Designed to be invoked from services, triggers, and orchestration layers

### Batch
- `with sharing`; implement `Database.Batchable<SObject>` (add `Database.Stateful` when tracking results across chunks)
- Keep `start()` focused on query definition; place business logic in `execute()`
- Use `QueryLocator` for large datasets; handle partial failures via `Database.SaveResult`
- Provide a meaningful `finish()` — at minimum logging; consider notifications
- Accept filter parameters via constructor to make the batch reusable

### Queueable
- `with sharing`; accept data via constructor
- Add chain-depth guards to prevent infinite chains
- Optionally implement `Finalizer` for recovery/cleanup
- Use `AsyncOptions` for configurable delay (up to 10 min) and dedup signatures

### Schedulable
- `with sharing`; keep `execute()` lightweight — delegate to a Queueable or Batch
- Provide CRON expression constants; document schedule intent
- Provide a convenience `scheduleDaily()` or similar static helper

### DTO / Wrapper
- No sharing keyword needed (pure data containers; SOQL and DML are handled elsewhere)
- Prefer simple public properties; provide no-arg and parameterized constructors
- Serialization-friendly (`JSON.serialize`/`deserialize`); implement `Comparable` when ordering matters

### Utility
- No sharing keyword needed (utility classes are pure functions; SOQL/DML belong in Services/Selectors)
- All methods `public static`; provide a `private` constructor to prevent instantiation
- Keep all methods pure and side-effect-free; perform SOQL and DML in dedicated layers

### Interface
- Define clear contracts with ApexDoc on each method signature

### Abstract
- `with sharing`; offer default behavior via `virtual` methods
- Mark extension points `protected virtual` or `protected abstract`

### Custom Exception
- No sharing keyword needed
- Extend `Exception`; keep simple with descriptive names
- Apex exceptions support: `new MyException()`, `new MyException('msg')`, `new MyException(cause)`, `new MyException('msg', cause)`

### Trigger
- One trigger per object; delegate all logic to handler or TAF action classes
- Include all relevant DML contexts (`before insert, after insert, before update, after update, before delete, after delete, after undelete`)
- If TAF is installed, the trigger body is a single line: `new MetadataTriggerHandler().run();`

### Trigger Action (TAF)
- One class per concern per context; implement `TriggerAction.{Context}` (e.g., `TriggerAction.BeforeInsert`)
- Register via `Trigger_Action__mdt` custom metadata records (actions do nothing without registration)
- Name: `TA_{SObject}_{ActionName}`
- For recursion prevention, prefer field-value comparison over static boolean flags

### Invocable Method (`@InvocableMethod`)
- `with sharing`; use inner `Request`/`Response` classes with `@InvocableVariable`
- Accept `List<Request>`, return `List<Response>`; bulkify — query and DML outside loops
- Always include `isSuccess` (Boolean) and `errorMessage` (String) in Response
- Return errors in Response rather than throwing exceptions (exceptions trigger Flow fault path)
- Limit supported `@InvocableVariable` types to primitives, `Id`, `SObject`, and `List<T>` (types such as `Map`, `Set`, and `Blob` are not supported)

### REST Resource (`@RestResource`)
- `global with sharing`; `global` is required for Apex REST endpoints — both the class and annotated methods must be `global`
- Use versioned URL mapping: `@RestResource(urlMapping='/{resource}/v1/*')` for future API evolution
- Parse `RestContext.request` directly in methods for flexibility; use `void` methods with `RestContext.response` when fine-grained status code control is needed, or return a response DTO for automatic serialization
- Return appropriate HTTP status codes per logic branch: `200` success, `201` created, `400` bad request, `404` not found, `422` validation failure, `500` internal error — never default to `500` for all errors
- Validate incoming parameters; use `Pattern.matches('[a-zA-Z0-9]{15,18}', value)` for Id format validation; escape/bind all user input in SOQL
- Always include `LIMIT` and `ORDER BY` in SOQL queries; implement pagination via `pageSize`/`offset` query parameters with a reasonable max page size
- Use `WITH USER_MODE` in all SOQL for CRUD/FLS enforcement; combine with `with sharing` for record-level security
- Design endpoints to handle bulk operations efficiently — accept and return collections where appropriate
- Provide a standardized `ApiResponse` wrapper with `success`, `message`, and `data`/`records` fields for consistent client parsing
- Include inner request/response DTO classes to define the API contract clearly
- Delegate business logic to Service classes; keep the REST resource as a thin controller layer

### `@AuraEnabled` Controller
- `with sharing`; use `WITH USER_MODE` in all SOQL
- Use `@AuraEnabled(cacheable=true)` only for read-only queries; leave `cacheable` unset for DML operations
- Catch exceptions and rethrow as `AuraHandledException` with user-friendly messages

---

## Output Expectations

Deliverables per class:
- `{ClassName}.cls`
- `{ClassName}.cls-meta.xml` (default API version `66.0` or higher unless specified)
- `{ClassName}Test.cls` (generated via `skills/generating-apex-test/SKILL.md`)
- `{ClassName}Test.cls-meta.xml` (generated via `skills/generating-apex-test/SKILL.md`)

Meta XML template:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>{API_VERSION}</apiVersion>
    <status>Active</status>
</ApexClass>
```

Report in this order:

```text
Apex work: <summary>
Files: <paths>
Design: <pattern / framework choices>
Workflow: all mandatory steps completed (1–9); any N/A justified
Risks: <security, bulkification, async, dependency notes>
Analyzer: run_code_analyzer clean (sev0–sev2 remediated)
Testing: Apex tests executed; failures fixed or delegated via skills/generating-apex-test
Deploy: <dry-run or next step>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Describe objects / fields first | metadata skill | Ensure alignment with the correct schema |
| Seed bulk or edge-case data | data skill | Create realistic datasets |
| Run Apex tests / fix failing tests | Read and follow `skills/generating-apex-test/SKILL.md` | Execute and iterate on failures |
| Deploy to org | deploy skill | Validation and deployment orchestration |
| Build Flow that calls Apex | Flow skill | Declarative orchestration via `@InvocableMethod` |
| Build LWC that calls Apex | LWC skill | UI/controller integration via `@AuraEnabled` |

---

## LSP Validation

This skill supports an LSP-assisted authoring loop for `.cls` and `.trigger` files:
- Syntax issues detected immediately after write/edit
- Auto-fix common syntax errors in a short loop (max 3 attempts)
- Semantic quality validated via the code review checklist

Full guide: [troubleshooting](references/troubleshooting.md)

---

## Optional Enhancers

- Run additional PMD rulesets beyond the default `run_code_analyzer` configuration for deeper style analysis

---

## Reference Map

### Core guides
- [security guide](references/security-guide.md) — CRUD/FLS, sharing, SOQL injection, Named Credentials
- [bulkification guide](references/bulkification-guide.md) — governor limits, collection patterns, performance monitoring

### Checklists & catalogs
- [anti-patterns](references/anti-patterns.md) — critical anti-patterns, code smells, and refactoring strategies
- [naming conventions](references/naming-conventions.md) — class, method, variable, collection naming
- [llm anti-patterns](references/llm-anti-patterns.md) — hallucinated methods, Java types, null safety pitfalls

### Specialized patterns
- [trigger-actions-framework](references/trigger-actions-framework.md) — TAF setup, action classes, bypass, recursion
- [automation-density guide](references/automation-density-guide.md) — Flow vs Apex vs hybrid decision framework
- [flow integration](references/flow-integration.md) — `@InvocableMethod` / `@InvocableVariable` patterns
- [triangle pattern](references/triangle-pattern.md) — Flow-LWC-Apex integration (Apex perspective)
- [design patterns](references/design-patterns.md) — Factory, Strategy, Singleton, Builder, Decorator, Observer, Command, Facade, Domain, UoW
- [solid principles](references/solid-principles.md) — SRP, OCP, LSP, ISP, DIP in Apex

### Additional references
- [best practices](references/best-practices.md) — platform cache, static caching, guard clauses, comment guidelines
- [troubleshooting](references/troubleshooting.md) — LSP validation, deployment errors, debug logs, governor limit debugging
