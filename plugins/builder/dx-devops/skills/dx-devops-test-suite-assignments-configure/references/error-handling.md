# Error Handling — Suite Assignments (Modes B–D)

Never expose raw API error messages, stack traces, or JSON payloads to the user. Map response status codes to plain-language messages.

| Status | User-facing message |
|---|---|
| 400 | "The request was invalid. Check that all suite and stage IDs are correct and the event type is valid." |
| 403 | "You don't have permission to modify suite assignments on this pipeline." |
| 404 | "The pipeline or stage was not found." |
| 500 | "A server error occurred. Try again in a few minutes." |

## Mode A (recommendation) errors

Mode A makes only read queries. If a `sf data query` fails, report the problem in plain language and stop — do NOT fabricate suite names, recommendations, or coverage data. If no suites are assigned to the Review trigger, state that explicitly ("No test suites are currently assigned to the Review trigger for this pipeline").
