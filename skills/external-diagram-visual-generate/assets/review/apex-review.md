# Apex Code Review Template

## Gemini Review Prompt

```
Review this Apex code for best practices and issues:

CODE:
[paste code here]

REVIEW CATEGORIES:

1. BULKIFICATION
   - SOQL queries in loops
   - DML operations in loops
   - Governor limit risks
   - Collection usage

2. SECURITY
   - CRUD permissions check
   - FLS enforcement
   - Sharing model compliance
   - Injection vulnerabilities

3. BEST PRACTICES
   - Trigger handler pattern
   - One trigger per object
   - Separation of concerns
   - Proper exception handling

4. PERFORMANCE
   - Selective SOQL queries
   - Index usage
   - Unnecessary computation

5. MAINTAINABILITY
   - Code comments
   - Method length
   - Test coverage considerations

OUTPUT FORMAT:
JSON with summary, issues array, bestPractices array, and score
```

## Usage

```bash
gemini "Review this Apex trigger for issues: [paste code]" -o json
```

## Severity Guidelines

| Severity | Criteria |
|----------|----------|
| High | Security, governor limits, data integrity |
| Medium | Performance, best practices |
| Low | Style, minor improvements |
