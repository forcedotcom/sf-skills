---
name: service-itsm-agentic-setup-agentforce-studio-configure
description: "Enable the Agentforce for IT Service Salesforce Go feature toggles (Agentforce Studio, Einstein Generative AI, the parent umbrella, and the Fulfiller/Employee agent templates) using the Salesforce CLI (sf). Turns ON org prefs via the Setup Discovery feature/{apiName}/enable Connect API route. Write-capable, idempotent, dependency-ordered, confirm-to-write required. Use when asked to enable Agentforce Studio, turn on Agentforce for IT Service, enable Einstein generative AI, or configure the org-level Agentforce for IT Service prerequisites. Triggers: enable agentforce studio, turn on agentforce for it service, enable einstein generative ai, configure agentforce org prefs. DO NOT TRIGGER: read-only prerequisite check (service-itsm-agentic-setup-agentforce-studio-validate), create/activate an agent (service-itsm-agentic-setup-fulfiller-agent-configure), or assigning permission sets."
metadata:
  version: "1.3"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-validate"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
allowed-tools: |
  Bash
  Read
  AskUserQuestion
---

# Enable Agentforce for IT Service Prerequisites

Enable the **Agentforce for IT Service** Salesforce Go feature toggles — **Einstein Generative AI**, **Agentforce Studio**, the **parent umbrella**, and the path-specific agent template (**Fulfiller** or **Employee**) — entirely through the **Salesforce CLI (`sf`)**. These toggles are the **prerequisites for creating the Fulfiller/Employee agent**; this **write-capable** step turns them on via the Setup Discovery `POST /connect/setup/discovery/feature/{apiName}/enable` Connect API route. Each toggle is enabled **idempotently** (skipped if already `ENABLED`), dependencies are enabled first, and explicit confirmation is required before any write.

| Step | Skill | What it does |
|------|-------|--------------|
| 1. Validate | `service-itsm-agentic-setup-agentforce-studio-validate` | Read the toggles → READY / NOT-READY (no writes) |
| 2. Configure (this skill) | `service-itsm-agentic-setup-agentforce-studio-configure` | Turn the disabled toggles ON |
| 3. Create agent | `service-itsm-agentic-setup-fulfiller-agent-configure` | Create + activate the Fulfiller agent |

This skill is typically reached via hand-off from the validate skill's NOT-READY report, but can also be run directly.

A helper script — `scripts/classify-enable-plan.mjs` — reads the batched `/features/status` response and deterministically computes the dependency-ordered enable plan (before writing) and the final per-feature verdict (after writing). This mirrors the validate skill's `classify-readiness.mjs` contract (authoring standard A9): the decision logic lives in a script, not in prose.

## Scope

- **In scope**: Enabling Einstein Generative AI (`sales-cloud-einstein-generative-ai`), Agentforce Studio (`sales-cloud-agent-studio`), the parent umbrella (`service-cloud-agentforce-for-itsm`), and the path-specific template (`service-cloud-it-fulfiller-agent` for fulfiller; `service-cloud-requestor-agent` + `service-cloud-it-service-employee-agent` for employee) via `POST .../feature/{apiName}/enable`; reading live per-org state from `/features/status` before and after each write; enabling dependencies first; confirming enablement stuck via re-query; surfacing an ENABLED / ALREADY-ENABLED / FAILED verdict per feature. Writes are idempotent — skip if already `ENABLED`.
- **Out of scope**: Provisioning Agentforce licenses (Setup > Company Information > Permission Set Licenses); assigning permission sets to users; creating, configuring, or activating an agent (`service-itsm-agentic-setup-fulfiller-agent-configure`); read-only prerequisite validation without writes (`service-itsm-agentic-setup-agentforce-studio-validate`); the org-wide multi-agent orchestration toggle (a Headless360-only pref, not a Connect feature).

---

## Which path?

Determine whether the user is enabling prerequisites for the **fulfiller** agent or an **employee** agent. If unclear, ask (`AskUserQuestion`) — same path selection the validate skill uses:

- **fulfiller** → `sales-cloud-einstein-generative-ai` → `sales-cloud-agent-studio` → `service-cloud-agentforce-for-itsm` → `service-cloud-it-fulfiller-agent`
- **employee** → `sales-cloud-einstein-generative-ai` → `sales-cloud-agent-studio` → `service-cloud-agentforce-for-itsm` → `service-cloud-requestor-agent` → `service-cloud-it-service-employee-agent`

Einstein Generative AI is a dependency of Agentforce Studio and is not one of the toggles the validate skill reports on directly, but it must be enabled first if it is off — the classifier includes it in the enable plan for both paths.

---

## Preconditions

Same as the validate skill (they share the target org and API surface). If unmet, `sf` surfaces an auth error or a `401`/`403`/`404`; **do not fabricate state — surface the raw error and stop**.

1. **`sf` CLI installed and authenticated to the target org** (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract or pass the access token by hand.
2. **API v67.0+**: the `connect/setup/discovery` feature APIs are available at v67.0. The version is pinned in the URL path; do not hand-edit it below the minimum.
3. **`node` ≥ 18** on PATH (runs the classifier script).
4. **Agentforce license** on the org (`accessCheck`) — a missing license surfaces as `403` or as `enableBlockedReasons` on the read.

---

## Operations at a glance

| Operation | Command | Returns |
|-----------|---------|---------|
| Read feature toggles | `sf api request rest ".../connect/setup/discovery/features/status" --method POST --body '{"featureApiNames":[...]}' --target-org <alias>` | `{items:[{apiName,status,enableBlockedReasons[],dependencyStatuses[]}]}` |
| Enable one toggle | `sf api request rest ".../connect/setup/discovery/feature/{apiName}/enable" --method POST --body '{}' --target-org <alias>` | `{success:boolean}` — endpoint takes no meaningful body, but `--body '{}'` must be passed explicitly (see gotchas) |

Both are Connect API routes reachable via `sf api request rest` — no Headless360 dispatcher required. Full command shapes, the response envelope, and the error taxonomy live in `references/cli-invocation.md`.

> **Never extract the access token.** Use `sf api request rest` directly — it uses the CLI's stored session for the target org. Do **not** pull the `accessToken` out of `sf org display` and hand-build an HTTP request with it.

> **CRITICAL: DO NOT use IPCManagement `updateOrgPref` to flip agent prefs.** That controller's write allow-list **rejects** the agent prefNames (`Invalid prefName`, 500). The Setup Discovery `POST /feature/{apiName}/enable` endpoint is the **only** correct write path for these toggles.

---

## Architecture — How enablement works

| Step | What happens | Tool used |
|------|--------------|-----------|
| Pick path | Determine fulfiller vs employee (ask if unclear) | `AskUserQuestion` |
| Read current state | POST the feature-status batch for the path's toggles, capture to a file | `Bash` (`sf api request rest`) |
| Plan | Run `scripts/classify-enable-plan.mjs <file> <agentType> [exitStatus]` → dependency-ordered `pending` list | `Bash` (`node`) |
| Confirm-to-write | Present the exact `pending` list and require explicit "yes" | `AskUserQuestion` |
| Enable | Re-read + reclassify before each `apiName` in `order`, POST `.../feature/{apiName}/enable` when unblocked, record the result | `Bash` (`sf api request rest` + `node scripts/record-enable-result.mjs`) |
| Verify | Re-read `/features/status`, re-run the classifier | `Bash` (`sf` + `node`) |
| Report | Run `scripts/classify-final-report.mjs` over the before/results/after files → final verdict | `Bash` (`node`) |

---

## Workflow

Substitute `<alias>` with the target org alias. `<agentType>` is `fulfiller` or `employee`.

### Phase 1 — Read Current State

1. POST the feature-status batch for every toggle the chosen path needs, capturing stdout to a file. Do **not** add `--json`. Write the request body **once** to a temp file and reuse it verbatim in Phases 1, 4, and 5 via `--body "$(cat ...)"` — never retype it, substitute a placeholder like `[...]`, or rely on a shell variable, since each Bash invocation may run in a fresh shell where a plain variable would be unset:

   ```bash
   cat > /tmp/feature-status-body.json <<'EOF'
   {"featureApiNames":["sales-cloud-einstein-generative-ai","sales-cloud-agent-studio","service-cloud-agentforce-for-itsm","service-cloud-it-fulfiller-agent","service-cloud-requestor-agent","service-cloud-it-service-employee-agent"]}
   EOF

   sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
     --method POST \
     --body "$(cat /tmp/feature-status-body.json)" \
     --target-org <alias> > /tmp/enable-status-before.json 2>/tmp/enable-status-before.err
   echo $? > /tmp/enable-status-before.exit
   ```

   Capture the exit status — do not swallow it with `|| true`.

### Phase 2 — Plan (helper script)

2. Run the classifier over the captured file to compute the dependency-ordered enable plan, saving its output — Phase 6 consumes this file, not the raw `/features/status` response:

   ```bash
   node "<skill_dir>/scripts/classify-enable-plan.mjs" /tmp/enable-status-before.json <agentType> "$(cat /tmp/enable-status-before.exit)" > /tmp/enable-plan-before.json
   ```

   It prints `{ agentType, readState, features, order, alreadyEnabled, pending, blocked, unconfirmed, verdict, reasons, rawError }`. `verdict: "ALL-ENABLED"` means nothing to do — skip to Phase 6. `verdict: "NEEDS-ENABLE"` means `pending` (in `order`) lists what to enable. `blocked` lists any `pending` toggle whose `enableBlockedReasons` is non-empty **as of this read** — a toggle blocked only on an earlier dependency in `order` becomes enable-able once that dependency is on, so Phase 4 re-checks each toggle immediately before attempting it rather than trusting this snapshot for the whole loop. `unconfirmed` lists any required toggle missing from the response or carrying a status this classifier doesn't recognize — `verdict: "CANNOT-CONFIRM"` (not `"ALL-ENABLED"`) when `unconfirmed` is non-empty and `pending` is empty. `readState: "error"` ⇒ surface `rawError` and stop; `readState: "not-wired"` ⇒ report CANNOT-CONFIRM and stop.

### Phase 3 — Confirm-to-Write Checkpoint (REQUIRED)

3. **Present the exact `pending` list** (excluding anything in `blocked`) and require an explicit "yes" from the user via `AskUserQuestion` before proceeding. Enabling org prefs mutates org state. **Proceed to Phase 4 ONLY on an explicit "yes".** On "no", stop and report the current state without any writes.

### Phase 4 — Enable (Dependencies First, Re-Checked Before Each Toggle)

4. Iterate `order` **in sequence** (Einstein GenAI → Studio → parent → child template(s)). Before attempting to enable each `<apiName>`, re-read and reclassify — this is what lets a child that was `blocked` in Phase 2 (only because Studio/parent was still off) become enable-able once that dependency's own enable has landed, instead of being permanently written off from the Phase-2 snapshot:

   ```bash
   sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
     --method POST \
     --body "$(cat /tmp/feature-status-body.json)" \
     --target-org <alias> > /tmp/enable-status-loop.json 2>/tmp/enable-status-loop.err
   echo $? > /tmp/enable-status-loop.exit
   node "<skill_dir>/scripts/classify-enable-plan.mjs" /tmp/enable-status-loop.json <agentType> "$(cat /tmp/enable-status-loop.exit)"
   ```

   Inspect `features["<apiName>"].signal` from that output:
   - `PASS` → already `ENABLED`; nothing to do, move to the next `apiName` in `order`.
   - `FAIL` with an empty `enableBlockedReasons` → enable it now:

     ```bash
     sf api request rest "/services/data/v67.0/connect/setup/discovery/feature/<apiName>/enable" \
       --method POST \
       --body '{}' \
       --target-org <alias> > /tmp/enable-<apiName>.json 2>/tmp/enable-<apiName>.err
     node "<skill_dir>/scripts/record-enable-result.mjs" /tmp/enable-<apiName>.json <apiName> /tmp/enable-results.json
     ```

     The `/enable` endpoint itself takes no meaningful body, but `sf api request rest --method POST` with no `--body` flag at all fails with `Error (SfError): No 'mode' found in 'body' entry` — always pass `--body '{}'` explicitly. `record-enable-result.mjs` reads the response, classifies it ENABLED/FAILED, and accumulates it into `/tmp/enable-results.json` keyed by `apiName` — the deterministic per-toggle bookkeeping Phase 6 consumes.
   - `FAIL` with a **non-empty** `enableBlockedReasons` → still blocked even after this iteration's re-check (a real, not merely-sequential, blocker — e.g. unlicensed) — do not POST; move to the next `apiName` in `order` and let Phase 6 report the blocker verbatim.
   - `CANNOT-CONFIRM` / `ERROR` on this specific `apiName`'s read → stop the loop and surface the read failure; do not guess at remaining toggles.

   One failed toggle does not block the rest of the plan — continue the loop.

### Phase 5 — Verify Enablement

5. Re-run the Phase 1 read (same `/tmp/feature-status-body.json`) into a fresh file, and re-run the classifier over it, saving its output for Phase 6:

   ```bash
   sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
     --method POST \
     --body "$(cat /tmp/feature-status-body.json)" \
     --target-org <alias> > /tmp/enable-status-after.json 2>/tmp/enable-status-after.err
   echo $? > /tmp/enable-status-after.exit
   node "<skill_dir>/scripts/classify-enable-plan.mjs" /tmp/enable-status-after.json <agentType> "$(cat /tmp/enable-status-after.exit)" > /tmp/enable-plan-after.json
   ```

   `verdict: "ALL-ENABLED"` ⇒ every toggle in `order` is confirmed `ENABLED` — success. Anything still in `pending`/`blocked`/`unconfirmed` needs Phase 6 to classify it precisely (FAILED vs CANNOT-CONFIRM).

### Phase 6 — Aggregate Verdict (helper script)

6. Run the final aggregator over the Phase-2 classifier output (`/tmp/enable-plan-before.json`, not the raw `/features/status` response), the Phase-4 accumulated results (or `-` if Phase 2 was already `ALL-ENABLED`/`CANNOT-CONFIRM`/`ERROR` and Phase 4 never ran), and the Phase-5 classifier output (`/tmp/enable-plan-after.json`):

   ```bash
   node "<skill_dir>/scripts/classify-final-report.mjs" /tmp/enable-plan-before.json /tmp/enable-results.json /tmp/enable-plan-after.json
   ```

   It prints `{ features: { <apiName>: { finalStatus, reason } }, order, overall, reasons }` where `finalStatus` is `ALREADY-ENABLED | ENABLED | FAILED | CANNOT-CONFIRM | ERROR` and `overall` is `SUCCESS | PARTIAL | FAILED | CANNOT-CONFIRM | ERROR`. Render this directly into the Output Format — do not re-derive the per-feature verdict or the overall summary in prose (authoring standard A9). On `overall: "SUCCESS"`, point the user at `service-itsm-agentic-setup-fulfiller-agent-configure` (fulfiller) or `service-itsm-agentic-setup-employee-agent-configure` (employee) to proceed.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Enable via `POST /connect/setup/discovery/feature/{apiName}/enable` only | The IPCManagement `updateOrgPref` write allow-list rejects the agent prefNames (`Invalid prefName`) — this is the **only** correct write path |
| Read live per-feature state from `POST /features/status`, never a flat catalog list | Only `/status` carries per-org `ENABLED`/`NOT_ENABLED` + `enableBlockedReasons[]` + `dependencyStatuses[]` |
| Enable dependencies before children, in the classifier's `order` | Enabling a child before Einstein GenAI / Studio surfaces unmet-dependency blockers |
| Re-read and reclassify immediately before each toggle in the Phase-4 loop, not once at the top of the loop | A child `blocked` only because an earlier dependency was still off becomes enable-able the instant that dependency's own `/enable` lands — a single Phase-2 snapshot would report it FAILED even though it was never really blocked |
| Idempotent: skip `/enable` for anything already `ENABLED` | The classifier's `alreadyEnabled` list is authoritative; enabling an already-enabled feature returns `{success:true}` but is redundant |
| **REQUIRED confirm-to-write checkpoint** before any `/enable` POST | Enabling org prefs mutates org state; the user must explicitly approve the exact `pending` list |
| Never attempt to enable a toggle whose **current** (re-checked) `enableBlockedReasons` is non-empty | Non-empty `enableBlockedReasons` means the write would fail — report the blocker instead of a doomed POST |
| `verdict: "CANNOT-CONFIRM"` when `unconfirmed` is non-empty, even if `pending` is empty | A required toggle missing from the response, or with an unrecognized status, must not be reported as ALL-ENABLED just because nothing is left in `pending` |
| Classification and per-toggle result recording live in `scripts/classify-enable-plan.mjs`, `scripts/record-enable-result.mjs`, and `scripts/classify-final-report.mjs`, invoked via `Bash` — not in prose | Deterministic decision tables and aggregation over fixed feature statuses (authoring standard A9) |
| The read/write goes through `sf api request rest`; **never extract the access token** | `sf api request rest` uses the CLI's stored session for `--target-org` |
| Do **not** pass `--json` to `sf api request rest` | Unsupported on some Connect endpoints; the raw stdout body is already JSON |
| These are **Connect API** features — use SF CLI, not Headless360 | A Connect/Tooling equivalent exists, so SF CLI is preferred (avoids the Headless360HostedMcpServer org-perm gate) |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf api request rest --method POST` with no `--body` flag errors `No 'mode' found in 'body' entry` | The `/enable` endpoint itself takes no meaningful body, but the CLI still requires the flag — always pass `--body '{}'` explicitly (verified on CLI 2.140.6 and 2.145.6) |
| Feature API name unavailable / unlicensed on the org | No catalog endpoint enumerates valid names — the Phase-1 `/features/status` read surfaces an unavailable/unlicensed feature via `enableBlockedReasons[]` before any enable attempt |
| `/features/status` shows `NOT_ENABLED` with `dependencyStatuses[]` unmet | Enable the listed dependency first (Einstein GenAI before Studio, Studio before the parent/child toggles) |
| `updateOrgPref` → 500 `Invalid prefName` for an agent pref | Wrong write path — use the Setup Discovery `feature/{apiName}/enable` endpoint instead |
| Auth error from `sf api request rest` | The target org's session needs re-authentication (`sf org login web`) |
| Treating an auth/permission/empty-body read failure as "not wired" | Pass the captured `$?` as the classifier's 3rd arg — only a confirmed 404 is CANNOT-CONFIRM; anything else is ERROR (surface `rawError`, stop) |
| Reporting `ALL-ENABLED` because `pending` is empty | Also check `unconfirmed` — a required toggle missing from the response or with an unrecognized status is neither confirmed ENABLED nor NOT_ENABLED |
| Re-deriving the per-feature / overall verdict in prose from the before/after JSON | Run `scripts/classify-final-report.mjs` — the aggregation is fixed comparison logic (authoring standard A9), not a judgment call |
| Setting the feature-status request body in a shell variable in Phase 1 and expecting it in Phase 4/5 | Each `Bash` invocation may run in a fresh shell where the variable is unset, silently sending an empty body — persist it to `/tmp/feature-status-body.json` once and read it back with `--body "$(cat /tmp/feature-status-body.json)"` in every phase |

---

## Verification Checklist

- [ ] The agent path (fulfiller / employee) was determined (asked if unclear).
- [ ] Phase 1 read `/features/status` via `sf api request rest`, captured to a file, with its exit status captured.
- [ ] `scripts/classify-enable-plan.mjs` computed the `pending` (dependency-ordered), `blocked`, and `unconfirmed` lists before any write.
- [ ] The user explicitly confirmed the exact `pending` list at the Phase-3 checkpoint before any `/enable` POST.
- [ ] Phase 4 re-read and reclassified **before each toggle**, not once for the whole loop — so a child unblocked by an earlier dependency's enable was still attempted.
- [ ] Each attempted `/enable` POST's response was recorded via `scripts/record-enable-result.mjs`, accumulated across the loop.
- [ ] `/features/status` was re-read after enablement and the classifier re-run to confirm the final per-feature verdict.
- [ ] `scripts/classify-final-report.mjs` (not prose) computed the final per-feature status and overall summary from the before/results/after files; the access token was never extracted.

---

## Output Format

Present the enablement report as a **table** — this is **Stage 1 (Foundation)**, the platform
enablement that Stage 2 (install & activate the agent) is built on. Each Status is one of
ENABLED / ALREADY-ENABLED / FAILED / CANNOT-CONFIRM:

```text
Agentforce for IT Service — Stage 1: Enable Platform Features (via service-itsm-agentic-setup-agentforce-studio-configure)

Org:          <org-alias> (API v67.0)
Agent path:   fulfiller | employee

| # | Platform feature | Status |
| --- | --- | --- |
| 1 | Einstein Generative AI | <status> |
| 2 | Agentforce Studio | <status> |
| 3 | Agentforce for IT Service | <status> |
| 4 | <path-specific toggle(s)> | <status> |

Verdict: SUCCESS | PARTIAL | FAILED | CANNOT-CONFIRM | ERROR

Next steps:
  - <If SUCCESS: "Stage 1 (foundation) complete — proceed to Stage 2: install + activate the <path> agent via service-itsm-agentic-setup-fulfiller-agent-configure (fulfiller) / the employee-agent skill.">
  - <If PARTIAL/FAILED/CANNOT-CONFIRM/ERROR: list the affected toggle(s) + reason (enableBlockedReasons, unconfirmed status, or read error) + remediation steps>
```

Render `overall` and each feature's `finalStatus` from `scripts/classify-final-report.mjs` verbatim (substitute into each `<status>` cell) — do not recompute them. No files are produced beyond the temporary response captures used by the classifiers.

Label rows exactly as the classifier emits them — never add `Requestor`, `Specialized`, or `parent`.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/cli-invocation.md` | Every phase — exact `sf api request rest` read/write call shapes, response envelope, feature API names, the classifier contract, and the error taxonomy |
