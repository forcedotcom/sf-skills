# Helper Script Contracts — service-itsm-agentic-setup-itsm-agentforce-permset-assign

All four scripts are deterministic, side-effect-free JSON classifiers (A9). They read one or more `sf data query --json` / `sf api request rest` captures and emit a single JSON object to stdout. Exit is `0` on any parseable body; the verdict is carried in the payload. Exit `2` is a usage error (missing args); the scripts do **not** exit non-zero on a workflow-blocking condition — that is the caller's job based on the emitted `verdict`.

## `scripts/classify-permset-availability.mjs`

Decides Branch A vs Branch B (assign vs hand-off) AND emits per-persona `needsPsl` flags. Fulfiller-only — the three persona names are hard-coded.

### Input

One file path (positional):

1. `permsets.json` — `sf data query --json` capture of `PermissionSet` filtered to the three Fulfiller persona `Name` values (see `permset-topology.md`). Unrelated rows are filtered out by the classifier.

Must be the raw stdout capture (the `{status, result: {records: [...]}}` envelope). An unparseable / non-envelope body produces `verdict:"CANNOT-CONFIRM"` with the raw error in `reasons[]`.

### Output

```json
{
  "personasFound": ["IncidentFulfiller"],
  "personasMissing": ["ProblemFulfillerPermSet","ChangeRequestFulfillerPermSet"],
  "candidates": [
    { "Id": "0PS...", "Name": "IncidentFulfiller", "Label": "Incident Fulfiller", "LicenseId": "0PL...", "needsPsl": true }
  ],
  "verdict": "ASSIGN",
  "reasons": ["..."]
}
```

- `candidates[]` lists ONLY rows whose `Name` matches one of the three known Fulfiller personas. Unrelated rows in the query result are dropped.
- `needsPsl` is derived per-row from `LicenseId !== null` — read it from the SELECTED persona in the workflow.
- `personasFound` preserves the canonical order (Incident, Problem, Change) so the AskUserQuestion menu is stable across runs.

Verdict values:

| verdict | Meaning | Caller action |
|---|---|---|
| `ASSIGN` | ≥1 Fulfiller persona present on the org | Continue to Phase 2. AskUserQuestion which persona to assign; read `needsPsl` off that persona to gate PSL SOQL + POST |
| `HAND-OFF` | None of the three personas present | Skip Phase 2 entirely; go to Phase 3 (delegate to `service-itsm-agentic-setup-agentforce-studio-validate`) |
| `CANNOT-CONFIRM` | The query envelope was unparseable | Surface `reasons[]` verbatim and stop |

**Never auto-select** from `candidates[]` — a Fulfiller commonly needs only one persona (e.g. Incident) even when several are provisioned. Present the list and let the user pick.

## `scripts/resolve-target-user.mjs`

Extracts the running user's Id from the API-root `identity` URL. Replaces any prose "take the last path segment starting with `005` ..." step (A9).

### Input

One file path (positional):

1. `api-root.json` — capture of `sf api request rest "/services/data/v67.0/" --method GET` for the target org.

### Output

```json
{
  "userId": "005...",
  "identity": "https://<mydomain>.my.salesforce.com/id/00D.../005...",
  "verdict": "RESOLVED",
  "reasons": ["..."]
}
```

Validation: the trailing path segment of `identity` must match `^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$` (15 or 18 chars, `005` prefix). Any other shape produces `CANNOT-CONFIRM` with the raw identity URL in `reasons[]`.

| verdict | Meaning | Caller action |
|---|---|---|
| `RESOLVED` | `userId` is safe to use as the running-user Id | Use `userId` for Phase 2b/2d assignments |
| `CANNOT-CONFIRM` | No identity URL, or trailing segment does not match `005…` | Surface `reasons[]` verbatim and stop; do NOT fall back to prose parsing |

## `scripts/classify-assignment-state.mjs`

Decides whether the Phase 2d write is needed (idempotency). Handles both the license-backed persona flow and the standalone-persona flow.

### Input

Two positional arguments:

1. `psa-existing.json` — `sf data query --json` capture of `PermissionSetAssignment` for the target user + selected persona's `Id`.
2. `psla-existing.json` **OR** the literal sentinel `NO-PSL`:
   - If the selected persona's `needsPsl:true`, pass the PSLA capture path.
   - If the selected persona's `needsPsl:false`, pass the string `NO-PSL` — the classifier skips the PSLA envelope read and reports `licenseAssigned:null`.

### Output

```json
{
  "permsetAssigned": false,
  "licenseAssigned": true,
  "needsWrite": true,
  "verdict": "NEEDS-WRITE",
  "reasons": ["...", "..."]
}
```

`licenseAssigned` is `null` (not `false`) in the `NO-PSL` branch to make it distinguishable from a real "no PSL row found" case.

Verdict values:

| verdict | Meaning | Caller action |
|---|---|---|
| `NEEDS-WRITE` | `permsetAssigned` is `false` (or, when `needsPsl:true`, `licenseAssigned` is also `false`) | Confirm-to-write (Phase 2c), then Phase 2d (PSL first + permset if `needsPsl:true`; permset only if `needsPsl:false`) |
| `ALREADY-ASSIGNED` | All applicable rows present | Skip Phase 2d entirely; go to Phase 4 verify |
| `CANNOT-CONFIRM` | One of the query envelopes was unparseable | Surface `reasons[]` verbatim and stop |

## `scripts/classify-action-surface.mjs`

Decides whether the target `svc_itsm_intelligence__*` invocable actions are surfaced for the running user after the assign. Replaces prose "grep the response for ..." in Phase 4 (A9). Fulfiller-only — Employee actions (`svc_emp_intelligence__*`) are not tracked by this skill.

### Input

Positional arguments:

1. `generate-prompt-response.json` — capture of `sf api request rest "/services/data/v67.0/actions/custom/generatePromptResponse" --method GET`.
2. `expectedActions-csv` (optional) — comma-separated list of specific action names to check by exact match (e.g. `svc_itsm_intelligence__DraftMobileTaskSummary,svc_itsm_intelligence__FindContextualKA`). Callers upstream (Fulfiller agent-configure Phase 1b) hold this list; when invoked standalone, omit the CSV.

### Output

```json
{
  "present": ["svc_itsm_intelligence__ActionA"],
  "missing": ["svc_itsm_intelligence__ActionB"],
  "totalItsmActionsSeen": 7,
  "verdict": "PARTIAL",
  "reasons": ["..."]
}
```

Verdict values:

| verdict | Meaning | Caller action |
|---|---|---|
| `SURFACED` | With CSV: every expected action found. Without CSV: at least one `svc_itsm_intelligence__` action is present in the response | Proceed to Phase 5 → report `ASSIGNED` / `ALREADY-ASSIGNED` |
| `PARTIAL` | With CSV only: some expected actions found, others missing | Report `VERIFY-INCONCLUSIVE` — session refresh may resolve, or the wrong persona permset was assigned |
| `MISSING` | With CSV: none of the expected actions found. Without CSV: no `svc_itsm_intelligence__` actions in the response | Report `VERIFY-INCONCLUSIVE` — do not falsely report `ASSIGNED` |
| `CANNOT-CONFIRM` | Envelope missing/failed or `actions[]` array not found | Surface `reasons[]` verbatim and stop |

## Why deterministic classifiers?

All four classifiers replace prose interpretation of query / response bodies with fixed rules that always produce the same output for the same input. This is the A9 rule the sibling agent-configure skills follow: any decision that gates a write (or a success report) on the state of a JSON body lives in a script, never in prose. Model interpretation of `records[].length === 0` is a well-documented source of false-positive skips ("classifier said empty, so no permset exists — proceed") when the real cause was an auth-failure that returned an empty envelope.
