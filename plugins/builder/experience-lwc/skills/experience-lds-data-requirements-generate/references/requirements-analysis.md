# Requirements Analysis for LDS Data Requirements

## My Job

Analyze Lightning Web Component code to identify and clarify data requirements that need to be resolved before implementing LDS solutions. Focus on parsing natural language requirements, extracting operation types, identifying objects and fields, and determining scope and context.

## What I Look For

- **Ambiguous data requirements**: Comments or TODOs that mention data operations but lack specificity about objects, fields, or operation types.
- **Unclear operation types**: References to data operations without a clear indication of whether it's read, create, update, or delete.
- **Vague object references**: Mentions of data entities that could refer to multiple Salesforce objects or custom objects.
- **Incomplete field specifications**: Generic references like "contact info", "address", or "phone" that could map to multiple API names.
- **Missing scope context**: Data requirements without a clear indication of single vs. multiple records, user-triggered vs. automatic operations.

## What I Ignore

- Code that already has clear, specific LDS implementations.
- Standard Lightning components with proper data binding.
- Non-data-related TODOs and comments.
- Performance optimizations that don't affect requirement clarity.
- TODOs/comments that already acknowledge the need for clarification — these show proper requirement awareness.

## Analysis Framework (Requirements Analysis Mode)

**Operation type analysis**

- Read verbs: "get", "retrieve", "show", "list", "display".
- Create verbs: "create", "add", "new", "insert".
- Update verbs: "update", "edit", "modify", "change".
- Delete verbs: "delete", "remove".
- Flag ambiguous references that could indicate multiple operation types and require explicit confirmation.

**Data entity identification**

- Distinguish between standard Salesforce objects (high confidence) and potential custom objects (requires clarification).
- Detect custom-object patterns through industry-specific terminology or non-standard naming.
- Never assume a custom object API name without explicit confirmation.

**Field specification analysis**

- Map generic field references to specific API names where possible.
- Identify field ambiguity patterns that require clarification (e.g., "phone" → `Phone` vs `MobilePhone` vs `HomePhone`).
- Flag potential custom fields that need org-specific verification.

**Scope and context assessment**

- Determine data access patterns: single record vs. multiple records vs. query-based.
- Assess implementation context: user-triggered actions vs. automatic operations vs. real-time display.
- Consider performance implications and user experience requirements.
