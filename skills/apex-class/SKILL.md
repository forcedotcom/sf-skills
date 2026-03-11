---
name: apex-class
description: Generate production-ready Apex classes for Salesforce following enterprise best practices. Covers service classes, selectors, domain classes, batch/queueable/schedulable, DTOs, utilities, interfaces, abstract classes, and custom exceptions. Not for triggers or unit tests. Use this skill whenever the user asks to create, write, build, generate, or scaffold any Apex class — including when they describe functionality that would require an Apex class without explicitly saying "Apex class." Trigger on phrases like "build a service for," "create a handler," "I need a class that," "write Apex to," "scaffold a batch job," "create a queueable," or any request involving Salesforce server-side logic. Also use when the user asks to refactor, improve, or restructure existing Apex classes. Even if the request is vague like "I need something that processes Opportunities nightly," use this skill if the solution would involve an Apex class.
---

# Apex Class

Generate well-structured, production-ready Apex classes for Salesforce development.

## Scope

**Generates:**
- Service classes (business logic layer)
- Selector / query classes (SOQL encapsulation)
- Domain classes (SObject-specific logic)
- Batch Apex classes (`Database.Batchable`)
- Queueable Apex classes (`Queueable`, optionally `Finalizer`)
- Schedulable Apex classes (`Schedulable`)
- DTO / wrapper / request-response classes
- Utility / helper classes
- Custom exception classes
- Interfaces and abstract classes

**Does NOT generate:**
- Triggers (use a trigger framework skill)
- Unit tests (use a test writer skill)
- Aura controllers
- LWC JavaScript controllers

---

## Gathering Requirements

Before generating code, gather these inputs from the user (ask if not provided):

1. **Class type** — Service, Selector, Batch, Queueable, Schedulable, Domain, DTO, Utility, Interface, Abstract, Exception
2. **Class name** — or enough context to derive a meaningful name
3. **SObject(s) involved** — if applicable
4. **Business requirements** — plain-language description of what the class should do
5. **Optional preferences:**
   - Sharing model (`with sharing`, `without sharing`, `inherited sharing`)
   - Access modifier (`public` or `global`)
   - API version (default: `62.0`)
   - Whether to include ApexDoc comments (default: yes)

If the user provides a clear, complete request, generate immediately without unnecessary back-and-forth.

---

## Code Standards — ALWAYS Follow These

### Separation of Concerns
- **Service classes** contain business logic. They call Selectors for data and may call Domain classes for SObject-specific behavior.
- **Selector classes** encapsulate all SOQL queries. Services never contain inline SOQL.
- **Domain classes** encapsulate SObject-specific logic (field defaults, validation, transformation).
- Keep classes focused on a single responsibility.

### Bulkification
- All methods must operate on collections (`List`, `Set`, `Map`) by default.
- Never accept a single SObject when a `List<SObject>` is appropriate.
- Provide convenience overloads for single-record callers only when it makes the API cleaner, and have them delegate to the bulk method.

### Governor Limit Safety
- **No SOQL or DML inside loops.** Ever.
- Collect IDs/records first, query/DML once outside the loop.
- Use `Limits` class checks in batch/bulk operations where appropriate.
- Prefer `Database.insert(records, false)` with error handling in batch contexts.

### Sharing Model
- Default to `with sharing` unless the user specifies otherwise.
- If `without sharing` or `inherited sharing` is used, add an ApexDoc `@description` comment explaining WHY.

### Naming Conventions

| Class Type   | Pattern                        | Example                        |
|-------------|-------------------------------|-------------------------------|
| Service      | `{SObject}Service`            | `AccountService`              |
| Selector     | `{SObject}Selector`           | `AccountSelector`             |
| Domain       | `{SObject}Domain`             | `OpportunityDomain`           |
| Batch        | `{Descriptive}Batch`          | `AccountDeduplicationBatch`   |
| Queueable    | `{Descriptive}Queueable`      | `ExternalSyncQueueable`       |
| Schedulable  | `{Descriptive}Schedulable`    | `DailyCleanupSchedulable`     |
| DTO          | `{Descriptive}DTO`            | `AccountMergeRequestDTO`      |
| Wrapper      | `{Descriptive}Wrapper`        | `OpportunityLineWrapper`      |
| Utility      | `{Descriptive}Util`           | `StringUtil`, `DateUtil`      |
| Interface    | `I{Descriptive}`              | `INotificationService`        |
| Abstract     | `Abstract{Descriptive}`       | `AbstractIntegrationService`  |
| Exception    | `{Descriptive}Exception`      | `AccountServiceException`     |

### ApexDoc Comments
Include ApexDoc on every `public` and `global` method and on the class itself:

```apex
/**
 * @description Brief description of what the class does
 * @author Generated by Apex Class Writer Skill
 */
```

```apex
/**
 * @description Brief description of what the method does
 * @param paramName Description of the parameter
 * @return Description of the return value
 * @example
 * List<Account> results = AccountService.deduplicateAccounts(accountIds);
 */
```

### Null Safety
- Use guard clauses at the top of methods for null/empty inputs.
- Use safe navigation (`?.`) where appropriate.
- Return empty collections rather than `null`.

### Constants
- No magic strings or numbers in logic.
- Use `private static final` constants or a dedicated constants class.
- Use `Label.` custom labels for user-facing strings when appropriate.

### Custom Exceptions
- Each service class should define or reference a corresponding custom exception.
- Inner exception classes are preferred for simple cases: `public class AccountServiceException extends Exception {}`
- Include meaningful error messages with context.

### Error Handling
- Catch specific exceptions, not generic `Exception` unless re-throwing.
- Log errors meaningfully (assume a logging utility exists or stub one).
- In batch contexts, use `Database.SaveResult` / `Database.UpsertResult` with partial success.

---

## Output Format

For every class, produce TWO files:

1. **`{ClassName}.cls`** — The Apex class source code
2. **`{ClassName}.cls-meta.xml`** — The metadata file

### Meta XML Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>{API_VERSION}</apiVersion>
    <status>Active</status>
</ApexClass>
```

Default `apiVersion` is `62.0` unless the user specifies otherwise.

---

## Class Type–Specific Instructions

### Service Classes
- Read and follow: `templates/service.cls`
- Stateless — no instance variables holding mutable state
- All public methods should be `static` unless there's a compelling reason for instance methods
- Delegate queries to a Selector class
- Wrap business logic errors in a custom exception

### Selector Classes
- Read and follow: `templates/selector.cls`
- One Selector per SObject (or per logical query domain)
- Return `List<SObject>` or `Map<Id, SObject>`
- Accept filter criteria as method parameters, not hardcoded
- Include a private method that returns the base field list to keep DRY

### Domain Classes
- Read and follow: `templates/domain.cls`
- Encapsulate field-level defaults, derivations, and validations
- Operate on `List<SObject>` — designed to be called from triggers or services
- No SOQL or DML — only in-memory SObject manipulation

### Batch Classes
- Read and follow: `templates/batch.cls`
- Implement `Database.Batchable<SObject>` and optionally `Database.Stateful`
- Use `Database.QueryLocator` in `start()` for large datasets
- Handle partial failures in `execute()` using `Database.SaveResult`
- Implement meaningful `finish()` — at minimum, log completion

### Queueable Classes
- Read and follow: `templates/queueable.cls`
- Implement `Queueable` and optionally `Database.AllowsCallouts`
- Accept data through the constructor — queueables are stateful
- For chaining, include guard logic to prevent infinite chains
- Optionally implement `Finalizer` for error recovery

### Schedulable Classes
- Read and follow: `templates/schedulable.cls`
- Implement `Schedulable`
- Keep `execute()` lightweight — delegate to a Batch or Queueable
- Include a static method that returns a CRON expression for convenience
- Document the expected schedule in ApexDoc

### DTO / Wrapper Classes
- Read and follow: `templates/dto.cls`
- Use `public` properties — no getters/setters unless validation is needed
- Include a no-arg constructor and optionally a parameterized constructor
- Implement `Comparable` if sorting is needed
- Keep them serialization-friendly (no transient state unless intentional)

### Utility Classes
- Read and follow: `templates/utility.cls`
- All methods `public static`
- Class should be `public with sharing` with a `private` constructor to prevent instantiation
- Group related utilities (e.g., `StringUtil`, `DateUtil`, `CollectionUtil`)
- Every method must be side-effect-free (no DML, no SOQL)

### Interfaces
- Read and follow: `templates/interface.cls`
- Define the contract clearly with ApexDoc on every method signature
- Use meaningful names that describe the capability: `INotificationService`, `IRetryable`

### Abstract Classes
- Read and follow: `templates/abstract.cls`
- Provide default implementations for common behavior
- Mark extension points as `protected virtual` or `protected abstract`
- Include a concrete example in the ApexDoc showing how to extend

### Custom Exceptions
- Read and follow: `templates/exception.cls`
- Extend `Exception`
- Keep them simple — Apex exceptions don't support custom constructors well
- Name them descriptively: `AccountServiceException`, `IntegrationTimeoutException`

---

## Generation Workflow

1. Determine the class type from the user's request
2. Read the corresponding template from `templates/`
3. Read relevant examples from `examples/` if the class type has one
4. Apply the user's requirements to the template pattern
5. Generate the `.cls` file with full ApexDoc
6. Generate the `.cls-meta.xml` file
7. Present both files to the user
8. Include a brief note on design decisions if any non-obvious choices were made

---

## Anti-Patterns to Avoid

- ❌ SOQL or DML inside loops
- ❌ Hardcoded IDs or record type names (use `Schema.SObjectType` or Custom Metadata)
- ❌ God classes that mix query + logic + DML
- ❌ `public` fields on service classes
- ❌ Returning `null` from methods that should return collections
- ❌ Generic `catch (Exception e)` without re-throwing or meaningful handling
- ❌ Business logic in Batch `start()` methods
- ❌ Tight coupling between classes — use interfaces for extensibility
- ❌ Magic strings or numbers
- ❌ Methods longer than ~40 lines — break them into private helpers
