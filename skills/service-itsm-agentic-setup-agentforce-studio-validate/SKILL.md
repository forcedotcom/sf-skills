---
name: service-itsm-agentic-setup-agentforce-studio-validate
description: "Validate the Agentforce for IT Service prerequisites for a Fulfiller or Employee agent, using the Salesforce CLI (sf). The READ-ONLY prerequisite check: it reads the Salesforce Go feature toggles behind the Agentforce for IT Service setup page (Agentforce Studio, the IT Service Fulfiller / IT Service Employee templates, Specialized Agent Templates for Employee) via one Connect API call, then a helper script classifies the chosen path into a READY / NOT-READY verdict. It never enables anything; when a toggle is off it hands off to the agentforce-studio-configure skill to turn it on. Use when asked to check Agentforce prerequisites, validate the org is ready for an ITSM agent, or verify Agentforce Studio is enabled. Triggers: check agentforce prerequisites, validate agentforce readiness, is my org ready for the fulfiller agent, verify agentforce studio enabled. DO NOT TRIGGER: enabling or turning on the toggles, creating the fulfiller agent (service-itsm-agentic-setup-fulfiller-agent-configure), or CMDB CRUD."
metadata:
  version: "2.1"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-configure"
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

# Validate Agentforce for IT Service Prerequisites

Readiness check for **Agentforce for IT Service**, for either the **Fulfiller** or the **Employee** agent path. Before an ITSM agent can be created, the org must have the right **Salesforce Go feature toggles** turned on (the ones on the *Agentforce for IT Service* setup page). This skill reads those toggles through the **Salesforce CLI (`sf`)** — a single authenticated Connect API call via `sf api request rest` — and a helper script classifies the chosen agent path into a **READY / NOT-READY** verdict.

This is the **read-only** step in a three-skill flow. It **never enables anything**; turning toggles on is a separate write-capable skill:

| Step | Skill | What it does |
|------|-------|--------------|
| 1. Validate (this skill) | `service-itsm-agentic-setup-agentforce-studio-validate` | Read the toggles → READY / NOT-READY (no writes) |
| 2. Configure | `service-itsm-agentic-setup-agentforce-studio-configure` | Turn the disabled toggles ON |
| 3. Create agent | `service-itsm-agentic-setup-fulfiller-agent-configure` | Create + activate the Fulfiller agent |

On NOT-READY this skill names each disabled toggle and **hands off** to `service-itsm-agentic-setup-agentforce-studio-configure` to enable them — it does not POST an enable itself.

The feature toggles and their real `featureApiName`s:

| Go-page toggle | featureApiName | Required for |
|----------------|----------------|--------------|
| Turn on Agentforce Studio | `sales-cloud-agent-studio` | both paths (shared) |
| Agentforce for IT Service (parent umbrella) | `service-cloud-agentforce-for-itsm` | both paths (shared) |
| IT Service Fulfiller | `service-cloud-it-fulfiller-agent` | **fulfiller** |
| IT Service Employee | `service-cloud-requestor-agent` | **employee** |
| Specialized Agent Templates for Employee | `service-cloud-it-service-employee-agent` | **employee** |

All are **Connect API** features (`/connect/setup/discovery/...`) — the read goes through `sf api request rest`, no Headless360 dispatcher required. The classification is **deterministic** and lives in `scripts/classify-readiness.mjs` (invoked via `Bash`), not in prose.

## Scope

- **In scope**: Reading the Agentforce-for-IT-Service Go feature toggles via `connect/setup/discovery/features/status`; classifying the **fulfiller** or **employee** path into a per-feature + overall READY / NOT-READY verdict via a helper script; on NOT-READY, naming each disabled toggle and handing off to `service-itsm-agentic-setup-agentforce-studio-configure` to enable it.
- **Out of scope**: **Enabling / turning on any toggle** — that write is owned by `service-itsm-agentic-setup-agentforce-studio-configure` (this skill is read-only and never POSTs an enable); creating, committing, or activating an agent (handled by `service-itsm-agentic-setup-fulfiller-agent-configure`); the org-wide multi-agent orchestration toggle (that is a Headless360-only pref, not an ITSM Connect feature, and is not one of the setup-page toggles); assigning permission sets; CMDB CRUD.

---

## Which path?

Determine whether the user is setting up the **fulfiller** agent (the IT-fulfiller-facing agent) or an **employee** agent (the employee-facing / NGA agent). If it is not clear from the request, ask (`AskUserQuestion`). The path selects which toggles are required:

- **fulfiller** → `sales-cloud-agent-studio` + `service-cloud-agentforce-for-itsm` + `service-cloud-it-fulfiller-agent`
- **employee** → `sales-cloud-agent-studio` + `service-cloud-agentforce-for-itsm` + `service-cloud-requestor-agent` + `service-cloud-it-service-employee-agent`

---

## Preconditions

Before the skill can read anything, the CLI and target org must be configured. If any of these are unmet, `sf` surfaces an auth error or a `401`/`403`/`404`; **do not fabricate state — surface the raw error and stop**.

1. **`sf` CLI installed and authenticated to the target org** (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract or pass the access token by hand.
2. **API v67.0+**: the `connect/setup/discovery` feature APIs are available at v67.0. The version is pinned in the URL path; do not hand-edit it below the minimum.
3. **`node` ≥ 18** on PATH (runs the classifier script).

If a precondition fails, `sf` returns one of:
- Auth error / `401 Unauthorized` → session expired or wrong alias; re-run `sf org login web`.
- `403 Forbidden` → the user/org lacks the required access (missing Agentforce license).
- `404 Not Found` → the feature-discovery surface is not wired on this org tier — the classifier maps a missing/error body to CANNOT-CONFIRM, not a hard failure.

---

## Operations at a glance

| Operation | Command | Returns |
|-----------|---------|---------|
| Read feature toggles | `sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" --method POST --body '{"featureApiNames":[...]}' --target-org <alias>` | `{items:[{apiName,status,enableBlockedReasons[],dependencyStatuses[]}]}` — `status` is `ENABLED` / `NOT_ENABLED` per toggle. |

This skill makes **only** the read above — it is read-only. Enabling a toggle (`.../feature/{apiName}/enable`) is out of scope: hand off to `service-itsm-agentic-setup-agentforce-studio-configure`. `sf api request rest` prints the raw response body (JSON) to stdout — capture it to a file and hand it to the classifier. Full command shapes and the error taxonomy live in `references/cli-invocation.md`.

> **Never extract the access token.** Use `sf api request rest` directly — it uses the CLI's stored session for the target org. Do **not** pull the `accessToken` out of `sf org display` and hand-build an HTTP request with it; that bypasses the CLI session and leaks a bearer token into shell context.

---

## Architecture — How the check works

| Step | What happens | Tool used |
|------|--------------|-----------|
| Pick path | Determine fulfiller vs employee (ask if unclear) | `AskUserQuestion` |
| Read toggles | POST the feature-status batch for all toggles the path needs, capture to a file | `Bash` (`sf api request rest`) |
| Classify | Run `scripts/classify-readiness.mjs <file> <agentType> [exitStatus]` → per-feature + overall verdict | `Bash` (`node`) |
| Report | Render the classifier's verdict into the Output Format | — |
| Hand off | On NOT-READY, name each disabled toggle and hand off to `service-itsm-agentic-setup-agentforce-studio-configure` to enable it | — |

The skill is read-only — it never enables a toggle.

---

## Workflow

Substitute `<alias>` with the target org alias (ask the user, or use the default org from `sf config`). `<agentType>` is `fulfiller` or `employee`.

### Phase 1 — Read the feature toggles

1. POST the feature-status batch for every toggle the chosen path needs (safe to always request all five — the classifier only judges the ones the path requires), capturing stdout to a file. Do **not** add `--json`:

   ```bash
   sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
     --method POST \
     --body '{"featureApiNames":["sales-cloud-agent-studio","service-cloud-agentforce-for-itsm","service-cloud-it-fulfiller-agent","service-cloud-requestor-agent","service-cloud-it-service-employee-agent"]}' \
     --target-org <alias> > /tmp/features-status.json 2>/tmp/features-status.err
   echo $? > /tmp/features-status.exit
   ```

   Capture the command's exit status (`$?`) so the classifier can tell a confirmed 404 (gate not wired) apart from an auth/permission/transport failure. Do not swallow the exit with `|| true` — pass it to the classifier in Phase 2.

### Phase 2 — Classify (helper script)

2. Run the classifier over the captured file, the chosen agent type, **and the captured exit status**. **Use the skill's absolute directory** for the script path:

   ```bash
   node "<skill_dir>/scripts/classify-readiness.mjs" /tmp/features-status.json <agentType> "$(cat /tmp/features-status.exit)"
   ```

   It prints `{ agentType, readState, features, verdict, notEnabled, enableable, reasons, rawError }` where each feature is `PASS | FAIL | CANNOT-CONFIRM | ERROR` and `verdict` is `READY | NOT-READY | CANNOT-CONFIRM | ERROR`. This is the authoritative verdict — do not re-derive it from the raw response in prose. `notEnabled` lists every disabled required toggle; `enableable` is the subset with **no** `enableBlockedReasons` — the ones the configure skill can turn on straight away (the rest are blocked by an unmet dependency or a purchase/licensing gate).

### Phase 3 — Report + hand off

3. Render the classifier output into the Output Format below.
   - **READY** → point the user at `service-itsm-agentic-setup-fulfiller-agent-configure` to create the agent (fulfiller path), or `service-itsm-agentic-setup-employee-agent-configure` (employee path).
   - **NOT-READY** → name each disabled toggle (from `notEnabled`). For the `enableable` subset, hand off to `service-itsm-agentic-setup-agentforce-studio-configure` to turn them on (offer via `AskUserQuestion`: _"N prerequisite toggle(s) are off. Run service-itsm-agentic-setup-agentforce-studio-configure to enable them?"_ → on Yes, delegate; on No, stop and report). For any disabled-but-blocked toggle (in `notEnabled` but not `enableable`), report its `enableBlockedReasons` verbatim — it cannot be enabled until the blocker clears. **This skill does not POST an enable itself.**
   - **CANNOT-CONFIRM** → state which toggle(s) had no status and that the feature-discovery surface may not be wired on this org tier.
   - **ERROR** → the read failed (auth / permission / transport, or an unexpected body — see `rawError`). Surface the raw response and **stop**; do not treat it as a mere wiring gap.

### Phase 4 — (After enable) re-validate

4. If the user ran `service-itsm-agentic-setup-agentforce-studio-configure` to enable the toggles, re-run Phase 1 + Phase 2 here to confirm the verdict flips to READY, then report. This skill's own role remains read-only throughout.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| **This skill is read-only** — it never POSTs a feature enable | Turning toggles on is a separate write-capable skill (`service-itsm-agentic-setup-agentforce-studio-configure`); keeping the two apart keeps the `validate` verb honest and avoids two skills owning the same write |
| On NOT-READY, **hand off** to `service-itsm-agentic-setup-agentforce-studio-configure` for enablement | That skill owns the `.../feature/{apiName}/enable` write path (idempotent, dependency-ordered); this skill only names what is off |
| The read goes through `sf api request rest`; **never extract the access token** or hand-build a raw HTTP request | `sf api request rest` uses the CLI's stored session for `--target-org`; extracting the token leaks a bearer token into shell context |
| Classification lives in `scripts/classify-readiness.mjs`, invoked via `Bash` — not in prose | The verdict is a deterministic decision table over fixed feature statuses; a script is reliable, prose interpretation is not (authoring standard A9) |
| The required-toggle set depends on the agent path | Fulfiller and Employee agents gate on different template toggles; the classifier encodes both paths |
| These are **Connect API** features — use SF CLI, not Headless360 | A Connect/Tooling equivalent exists, so SF CLI is preferred (avoids the Headless360HostedMcpServer org-perm gate) |
| `enableBlockedReasons` non-empty ⇒ toggle is not in `enableable` — report the blocker | A blocked toggle can't be turned on even by the configure skill until the unmet dependency / purchase gate clears |
| Do **not** pass `--json` to `sf api request rest` | It is unsupported on some Connect endpoints; the raw stdout body is already JSON |

---

## Verification Checklist

- [ ] The agent path (fulfiller / employee) was determined (asked if unclear).
- [ ] The feature-status POST was run via `sf api request rest` and its body captured to a file.
- [ ] `scripts/classify-readiness.mjs` was invoked with the file, the agent type, **and the captured exit status**, and its `{verdict, notEnabled, enableable, rawError}` output recorded.
- [ ] The verdict (READY / NOT-READY / CANNOT-CONFIRM / ERROR) was reported verbatim from the classifier; on NOT-READY each disabled toggle was named, with the enable route only for the `enableable` subset and `enableBlockedReasons` reported for the rest; on ERROR the raw response was surfaced and the skill stopped.
- [ ] No feature was enabled by this skill (it is read-only); on NOT-READY the disabled toggles were named and the hand-off to `service-itsm-agentic-setup-agentforce-studio-configure` was offered, and the access token was never extracted.

---

## Output Format

Present the readiness report as:

```text
Agentforce for IT Service — Prerequisite Check (via service-itsm-agentic-setup-agentforce-studio-validate)

Org:          <org-alias> (API v67.0)
Agent path:   fulfiller | employee

  [PASS|FAIL] Agentforce Studio ......................... ENABLED | NOT_ENABLED (sales-cloud-agent-studio)
  [PASS|FAIL] Agentforce for IT Service (parent) ........ ENABLED | NOT_ENABLED (service-cloud-agentforce-for-itsm)
  [PASS|FAIL] <path-specific toggle(s)> ................. ENABLED | NOT_ENABLED (<featureApiName>)

Verdict: READY  |  NOT-READY  |  CANNOT-CONFIRM  |  ERROR

Next steps:
  - <If READY: "Org satisfies the prerequisites for the <path> agent. Create it via service-itsm-agentic-setup-fulfiller-agent-configure (fulfiller) / the employee-agent skill.">
  - <If NOT-READY: list each disabled toggle; for the enableable ones, hand off to service-itsm-agentic-setup-agentforce-studio-configure to turn them on; for blocked ones, report the enableBlockedReasons.>
  - <If CANNOT-CONFIRM: state which toggle(s) returned no status and that the feature-discovery surface may not be wired on this org.>
```

This skill is **read-only** — no org state is written. The only file it produces is the temporary response capture handed to the classifier.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/cli-invocation.md` | Every phase — exact `sf api request rest` read call shape, the feature-status route, the read-only / hand-off rule, the never-extract-token rule, the classifier contract, and the error taxonomy |
