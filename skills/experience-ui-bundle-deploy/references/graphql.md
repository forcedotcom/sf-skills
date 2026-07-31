# GraphQL schema fetch + codegen

Detail for the **graphql** step. Source of truth: reference `org-setup.mjs` graphql
step (1770-1792).

Runs from the **UI bundle directory** (`uiBundles/<bundle>/`), not the project
root. This step reflects org state, so it MUST run **after** deploy and permission
assignment — custom objects/fields and the caller's FLS only appear in the
introspected schema once they exist in the org and the user can see them.

## Sequence (in the UI bundle dir)

1. `npm install`
2. `npm run graphql:schema` — GraphQL introspection; writes the schema locally.
   Pass the target org via env:
   ```bash
   SF_TARGET_ORG=<org> npm run graphql:schema
   ```
3. `npm run graphql:codegen` — generates types from the local schema.
4. `npm run build` — rebuild the bundle against the freshly generated types.

## When to run

- Schema is missing, OR
- Metadata / permissions changed since the last fetch (any deploy that adds or
  changes objects, fields, or permission sets).

Re-run schema fetch + codegen **after every metadata deployment** that changes
objects, fields, or permissions — stale types otherwise drift from org state.
