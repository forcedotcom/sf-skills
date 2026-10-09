# Delta Computation Reference — Update Mode (Step 5)

Full matching and cycle-rejection algorithm for reconciling the desired hierarchy against the org's current one.

## Traverse the current tree from the root

Starting at the supplied System Account Id, read children level-by-level via the SObject child-relationship resource:

- `GET /services/data/v68.0/sobjects/Account/[Account Id]/ChildAccounts` via `dispatch_readonly` (see `references/mcp-invocation.md`)
- This returns the direct child Accounts (`body.records[]`, each with `Id`, `Name`, `ParentId`). Recurse into each child's Id to build the full `existingTree`.
- If `ChildAccounts` is unavailable in the org, fall back to a SOQL `/query` with the query text passed as `queryParams.q` (never appended inline to the URL as `?q=` — that has 404'd on some orgs). If both fail, ask the user to paste the current structure (Name + Account Id per node) instead.

## Match desired vs. current

By Name within the same sibling group (names are unique per sibling group — see Rules). For each desired node, walking from the root down:

- **Match found** (same Name under the matched parent) → reuse its Account Id; recurse into its children. No write.
- **No match** (desired node absent under that parent) → mark **CREATE**; every desired descendant beneath it is also CREATE (parent Id resolves once the parent is created).

## Extra nodes

Present in the org but absent from the desired structure → mark **EXTRA**. Do NOT delete. List them for the user in the preview.

## Explicit renames / moves

Only when the user asks for them by name — a bare desired tree cannot distinguish a rename from a delete-plus-add:

- **Rename**: resolve the target node's Account Id from `existingTree` by its current name/path → mark **RENAME** (new Name).
- **Move**: resolve both the node's Id and the new parent's Id → mark **MOVE** (new ParentId). Reject a move that would place a node under its own descendant (cycle) — stop with an error before writing.

## Result

A delta list of CREATE / RENAME / MOVE actions plus an EXTRA report. If the delta is empty and no renames/moves were requested, tell the user the org already matches the desired structure and skip to Step 9 (verify).
