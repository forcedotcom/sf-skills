# Find the right SOR when a routing tool is in reach (discover → describe → dispatch)

**Detect by tool shape, not by host name.** Check the tools available to you this run for a generic
capability-routing tool exposing **`discover` / `describe` / `dispatch`** verbs. The name may carry a
host prefix (`mcp__<host>__discover`, a bare `discover`, etc.) — **match the verb shape**. Such tools
are provided by SOR-routing surfaces (project-codey / Headless 360, Vibes / `vibes-cli`, Tool Factory
today; treat these as examples — the names change, the verb shape is the stable signal).

When one is in reach, the entry move for any DsarPolicy task is to **locate the SOR that covers the
capability**, then let it route the call. You supply judgment (which SOR, which operation, is the
request bounded / consented / an export-not-erasure); the SOR supplies the plumbing.

## 1. Discover — find the SOR, don't guess its name

Search the **capability**, not a guessed identifier:

- "manage DSAR / data-subject portability policies"
- "execute a DSAR policy against a data subject"
- "DSAR policy run history"

The SOR that owns this steel thread is **`DsarPolicyManager`** (owning team **Privacy Center**,
complexity SIMPLE). Its `agent_description` names DSAR policies + Right-to-Portability and the full
lifecycle:

```text
getAccessInfo → list policies → save (create / full-tree update) → activate
  → execute against a dataSubjectId → deactivate → delete
```

`isActive` is the load-bearing gate: **execute** needs ACTIVE; **edit / delete** need INACTIVE.

If several SORs surface, pick the one whose `agent_description` names **DSAR + Right-to-Portability**.
**Reject look-alikes:** data mask, generic consent, or anything framed as subject *erasure* — RTP
is a portability export, it deletes nothing. If none matches, say so and stop; do not fabricate a
SOR.

## 2. Describe — the contract comes from describe, not memory

`describe` the specific operation before calling it. The exact inputs — `policyName` (must match
`[a-zA-Z]+[a-zA-Z0-9_]*`), `description`, `isActive`, `relatedTrees` (UI-serialized node keys), and
`dataSubjectId` for execute — come from the operation's schema, not recall.

## 3. Dispatch — the SOR routes to the backend

`dispatch` the operation. The SOR picks the backend (the DsarPolicy config tree, the RTP execute
endpoint, the `DsarPolicyLog` read); you never hand-assemble the route.

## No routing tool in reach?

If no discover/describe/dispatch tool is available this run, fall back to the metadata / Connect /
SOQL routes in the SKILL.md object-model table. The judgment in the skill is identical either way —
the skill never changes *what* is correct, only *which tool* executes it.

## Related

- `../SKILL.md` — the object-model table (the plain-`sf` equivalents) and the three workflows
- The routing tool's own `discover` verb — "which SORs cover `<capability>`?" is answered by the
  discover/describe verbs described at the top of this file (project-codey / Headless 360), not by a
  separate skill.
