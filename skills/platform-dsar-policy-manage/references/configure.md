# Configure a DsarPolicy — authoring reference

Deep detail for **Workflow A**. Read this when you actually author the policy tree. The judgment
(refuse-to-guess, cap-and-stop) lives in `SKILL.md`; this file is the mechanics.

## The object model you author

A `DsarPolicy` is a **tree** of paths rooted on the object(s) that identify the data subject.

```text
DsarPolicy                     (the shell: DeveloperName, MasterLabel, lifecycle state)
└── DsarPolicyPath  (root)     (a root object the subject is identified on, e.g. Contact)
    ├── DsarPolicyField        (a field collected at this path)
    ├── DsarPolicyField
    └── DsarPolicyPath (child) (a relationship FROM this object TO a related object)
        └── DsarPolicyField
```

- **`DsarPolicyPath`** is either a **root** (a top-level object the subject is identified on) or a
  **relationship edge** from a parent object to a related object. Multiple roots are allowed — a
  subject identified on both `Contact` and `Lead` gets one root path each.
- **`DsarPolicyField`** names a field to include in the export at its parent path.
- All three are **Metadata API** entities. `DsarPolicyLog` (run history) is **not** part of this
  tree — it is standard SOQL (see `export-and-history.md`).

## Hard caps (the validator enforces these)

| Cap | Value |
|-----|-------|
| Children per path | **10** |
| Tree depth | **10** |
| Total nodes (paths) | **200** |
| Developer name | must match `[a-zA-Z]+[a-zA-Z0-9_]*` |

An unbounded request ("everything reachable from Account", "follow every relationship") will
exceed one of these. **Name the specific cap and stop** — do not start walking the object graph to
prove it (that times the turn out). Offer a bounded alternative: split into multiple policies, or
prune to the branches that actually hold the subject's data.

## Resolve names — never assume

Before authoring, resolve the real relationship and field API names against the org schema:

```bash
sf sobject describe --sobject Contact --target-org <alias> --json      # fields + child relationships
sf sobject describe --sobject Account --target-org <alias> --json
```

Use the `relationshipName`/`field` values from the describe output verbatim. A path that names a
relationship the org does not have will fail deploy.

## The `<tree.json>` shape for the validator

`scripts/validate-policy-tree.py` takes a JSON file describing the tree you intend to author. It
checks the caps and name regex **before** you write metadata, so a bad tree fails fast and cheap.

```json
{
  "developerName": "CustomerPortability",
  "roots": [
    {
      "developerName": "ContactRoot",
      "object": "Contact",
      "fields": ["FirstName", "LastName", "Email"],
      "children": [
        {
          "developerName": "ContactCases",
          "relationship": "Cases",
          "object": "Case",
          "fields": ["Subject", "Description"],
          "children": []
        }
      ]
    }
  ]
}
```

- `developerName` on every node → checked against `[a-zA-Z]+[a-zA-Z0-9_]*`.
- `children` nesting → depth check (root = depth 1).
- child count per node → 10-per-path check.
- total node count (roots + all descendants) → 200-node check.

The script exits non-zero and prints the first violation. Fix the tree and re-run until it exits 0,
then author metadata that mirrors it exactly.

## Lifecycle

- A policy is authored **INACTIVE**. It must be **ACTIVE** to execute (Workflow B).
- **INACTIVE** to **edit or delete**; **ACTIVE** to **execute**.
- To change an ACTIVE policy: **deactivate → edit → stop.** Never edit in place while ACTIVE, and
  **never reactivate on your own** — report the edit and get **explicit user confirmation** before
  reactivating/publishing. Auto-republishing breaks the reviewable audit trail that
  portability/erasure disputes rely on.
- Authoring, editing, or deleting the *policy* **never** touches the data subject's records — it
  only changes the export map. This is the export-not-deletion guardrail restated for configure.

## Deploy

```bash
sf project deploy start --source-dir <outputDir> --target-org <alias> --json
```

Deploy can legitimately fail where `DsarPolicy`/sub-entities are not fully enabled on the org.
Surface the raw error and name the prerequisite; the classification strategy and validated tree are
still the deliverable and belong in the report regardless of deploy outcome.
