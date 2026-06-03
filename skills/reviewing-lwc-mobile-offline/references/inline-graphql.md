# Inline GraphQL Wire Configuration

## Framework for the analysis

The Komaci offline static analysis engine requires GraphQL queries to be **extracted from `@wire` adapter configurations into separate getter methods** for proper offline data priming. Inline GraphQL query strings within `@wire` adapter calls prevent the static analysis engine from understanding and optimizing data dependencies for offline scenarios.

**FOCUS:** Only report improper usage of GraphQL queries and variables accessed outside of a component getter function. Do not provide feedback on any other adapter use.

Key points to consider:

- GraphQL queries and variables MUST be accessed from a getter function within the component class.
- GraphQL queries MUST NOT be inlined in the wire adapter configuration object.
- GraphQL variables MUST NOT be inlined in the wire adapter configuration object.
- GraphQL queries MUST NOT be defined as top-level constants.
- GraphQL variables MUST NOT be defined as top-level constants.
- If the query is already in a getter function, do not provide feedback.
- If the component does not use GraphQL, does not import GraphQL, does not use `@wire`, or does not contain a query in a `gql` template literal, do not provide feedback or analyze further.

## Request

Review the JavaScript files for `@wire` decorators with inline GraphQL queries:

1. Identify `@wire` decorators that use GraphQL wire adapters.
2. Look for literal GraphQL query strings within the wire configuration objects.
3. Check for template literals or string literals containing GraphQL syntax.
4. Analyze the complexity and reusability of the inline queries.
5. Determine appropriate getter method names for extracted queries.
6. Validate that extraction will not break existing functionality.
7. Report each violation with specific refactoring guidance.

For each violation, provide a strong suggested action that names a concrete getter — e.g. _"The query MUST be extracted into a getter function called `fooQuery` and accessed by the config `@wire(graphql, { query: '$fooQuery' })`."_

Rules to follow:

- If no action is required, return an empty list. Do not return null or any other value — return an empty array.
- Keep issues concise; avoid duplicated issues or unnecessary analysis for things that are not real violations.
- Stick to the instructions for the specific reviewer in scope. Issues outside that scope will be analyzed by other reviewers.
- For each violation, provide:
  - The exact violation type as defined by the reviewer in scope.
  - A description of why it is a problem in the context of mobile offline priming.
  - An intent analysis explaining what the developer likely intended.
  - A suggested action with concrete code-level remediation.
- Do not make assumptions about other components that may be referenced.
