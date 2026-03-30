# Query Testing

## Load This Reference When

Load this file before testing GraphQL queries or triaging GraphQL errors returned by `sf api request rest`, including retries and status classification (`SUCCESS`, `FAILED`, `PARTIAL`).

## Testing Method

Use `sf api request rest` to POST the query to the GraphQL endpoint. Run from the **SFDX project root** (where `sfdx-project.json` lives).

```bash
sf api request rest /services/data/v66.0/graphql \
  --method POST \
  --body '{"query":"query GetData { uiapi { query { EntityName { edges { node { Id } } } } } }"}'
```

- Use the API version of the target org (v66.0+ for mutation support, v65.0+ for `@optional`)
- Replace the `query` value with the generated query string
- If the query uses variables, include them in the JSON body as a `variables` key

## Critical: HTTP 200 Does Not Mean Success

Salesforce returns HTTP 200 even when the GraphQL operation has errors (e.g., invalid fields, permission failures, invalid IDs). **Always parse the `errors` array in the response body regardless of HTTP status code.** Do not treat HTTP 200 as confirmation that the query succeeded.

## Testing Workflow

This workflow applies to both read and mutation queries:

1. **Report method** — State the exact method: `sf api request rest` POST to `/services/data/vXX.0/graphql` from the project root
2. **Ask user** — Ask the user whether they want to test the query. For mutations, also ask for input argument values — mutations modify real data, so explicit consent is essential. Wait for the user's answer before proceeding. Do not fabricate test data.
3. **Execute test** — Only if the user explicitly agrees. Run `sf api request rest` with the query, variables, and correct API version
4. **Report result** — Classify the result using the status definitions below. Always check the `errors` array in the response, even on HTTP 200.

## Result Status Definitions

| Status    | Condition                                       | Meaning                                       |
| --------- | ----------------------------------------------- | --------------------------------------------- |
| `SUCCESS` | `errors` is absent or empty                     | Query is valid (even if no data is returned)  |
| `FAILED`  | `data` is empty or null                         | Query is invalid                              |
| `PARTIAL` | `data` is present **and** `errors` is not empty | Some fields are inaccessible (mutations only) |

## FAILED Status Handling

The query is invalid. Follow this sequence:

### 1. Error Analysis

Parse the `errors` array and check `errors[].extensions.ErrorType` for Salesforce-specific error classification. Categorize into:

| Category        | ErrorType / Message Contains                                     | Resolution                                                                         |
| --------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Syntax**      | `InvalidSyntax`                                                  | Fix syntax errors using the error message details                                  |
| **Validation**  | `ValidationError`                                                | Field name is likely invalid — re-run the schema search script, ask user if still unclear |
| **Type**        | `VariableTypeMismatch` or `UnknownType`                          | Use error details and schema to correct the argument type; adjust variables        |
| **Execution**   | `DataFetchingException`, `invalid cross reference id`            | Entity is unknown/deleted — create entity first if possible, or ask for a valid Id |
| **Navigation**  | `is not currently available in mutation results`                 | Field cannot be in mutation output — apply PARTIAL status handling                 |
| **Unsupported** | `OperationNotSupported`                                          | The operation is not supported — check object availability and API version         |
| **API Version** | `Cannot invoke JsonElement.isJsonObject()` (on update mutations) | `Record` selection requires API version 64+ — report and retry with version 64     |

### 2. Targeted Resolution

Apply the resolution from the table above based on the error category. Update the query accordingly.

### 3. Test Again

Re-run the testing workflow with the updated query. Increment and track the attempt counter.

## PARTIAL Status Handling

The query executed but some fields are inaccessible (mutations only):

1. Report the fields listed in the `errors` attribute
2. Explain that these fields cannot be queried as part of a mutation
3. Explain that the query will report errors if these fields remain
4. Offer to remove the offending fields
5. **STOP and WAIT** for the user's answer. Do NOT remove fields without explicit consent.
6. If the user agrees, restart the mutation generation workflow with the updated field list

## Retry and Escalation

- **Maximum 2 test attempts** per generated query
- If targeted resolution fails after 2 attempts, ask the user for additional details and **restart the entire workflow from Step 1 (Acquire Schema)** to re-validate entity and field information
