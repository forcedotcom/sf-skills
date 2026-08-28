# ITSM Fulfiller Persona Permset Topology (Core-shipped)

This skill assigns Core-shipped **StandardPermissionSet** persona permsets — NOT a
managed-package namespaced permset. On a real org there is no
`svc_itsm_intelligence` namespaced `PermissionSet`; the Fulfiller agent's
`svc_itsm_intelligence__*` prompt-template invocable actions surface only once
the running user holds the correct **Fulfiller persona permset** shipped in
Core (namespace `force`).

**Employee agent is out of scope for this skill.** The Employee agent's access
model is separate (org-preferences + a different persona layer) and does not
map onto these three permsets.

## Fulfiller persona ↔ AddOn ↔ PSL ↔ PermSet

| Persona | AddOn (`.add.xml`) | PSL (`.psl.xml`) | **PermSet DeveloperName** (assign this) | Grants userPerm |
|---|---|---|---|---|
| Incident Fulfiller | `IncidentManagementAddOn-1` | `IncidentFulfillerPsl-1` | **`IncidentFulfiller`** | `IncidentFulfillerUser` |
| Problem Fulfiller | `ProblemManagementAddOn-1` | `ProblemFulfillerPsl-1` | **`ProblemFulfillerPermSet`** | `ProblemFulfillerUser` |
| Change Fulfiller | `ChangeManagementAddOn-1` | `ChangeRequestFulfillerPsl-1` | **`ChangeRequestFulfillerPermSet`** | `ChangeFulfillerPerm` |

### Key facts

- **Namespace is `force` on every permset** — the namespace-prefix filter used
  in the previous version of this skill (`svc_itsm_intelligence`) never
  returns any of these rows.
- **Naming inconsistency**: `IncidentFulfiller` has NO `PermSet` suffix; the
  other two DO. The classifier's fixed-name list reflects this exactly —
  do not "normalize" the Incident name to `IncidentFulfillerPermSet`, it does
  not exist on the org.
- **CMDB access is a separate concern** — the CMDB read/write permsets are
  handled by `service-itsm-agentic-setup-cmdb-access-assign` and are not
  gated by any `svc_itsm_intelligence__*` prompt-template invocable, so they
  are intentionally excluded from this skill's fixed-lookup set.

## Fixed-lookup discovery query (Phase 1)

```sql
SELECT Id, Name, Label, LicenseId
FROM PermissionSet
WHERE Name IN (
  'IncidentFulfiller',
  'ProblemFulfillerPermSet',
  'ChangeRequestFulfillerPermSet'
)
```

**Interpreting the result set:**

- **≥1 row present** ⇒ Branch A (assign). Ask the user which persona to
  assign — do NOT auto-select, since a Fulfiller commonly needs only one
  persona (e.g. Incident) even when others are provisioned.
- **Zero rows** ⇒ Branch B (hand-off). The ITSM AddOn(s) are not provisioned
  on this org. Route to `service-itsm-agentic-setup-agentforce-studio-validate`
  so the AddOn(s) can be enabled first.

## `needsPsl` per persona

Whether the PSL POST step in Phase 2 runs is a **per-permset** decision, read
from each row's `LicenseId`:

- `LicenseId != null` ⇒ `needsPsl:true` (license-gated permset — POST the PSL
  before the permset assign).
- `LicenseId == null` ⇒ `needsPsl:false` (standalone permset — skip the PSL
  POST entirely; assign the permset only).

The classifier emits `needsPsl` per candidate row, so the caller reads the
switch from the selected persona and does not need to re-derive it.

## Codesearch sources

Every row above was verified against the Core repo. When the AddOn / PSL /
PermSet metadata drifts on a future release, re-run codesearch on the AddOn
file (`*.add.xml`) — the AddOn's `<permissionSet>` reference is the source of
truth for the DeveloperName this skill must assign.
