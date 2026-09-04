# Report templates

Read this reference before emitting the final report. Every coordinator run produces exactly one user-facing artifact: `report.md`. This file defines its structure so every run's report is consistent and easy to read.

**Rule:** report concrete outcomes only. No hedges ("will create", "to be resolved", "pending confirmation"), no padding — dense, declarative lines.

The coordinator runs a dependency-ordered setup of the child skills (see `SKILL.md` → *Skills this coordinates*). The report is a **Skill Outcomes** table. Each skill's status is one of `Done` (created/updated/deployed/configured/bound/assigned), `Reused`, `Skipped`, `Blocked`, or `Blocked (dependency)` — the last is emitted when a prerequisite skill went red and the dependent skill was intentionally not run.

**Credentials never appear in `report.md`.** Generated passwords are written once to a restricted `CREDENTIALS.json` (mode 0600) and redacted from every other artifact. The report points the operator at that file; it never prints a plaintext password.

---

## Template A — Full run (happy path)

Use when every skill completed successfully (or was correctly reused/skipped for idempotency).

```markdown
# Omni-Channel Setup Report (via service-omni-channel-setup-coordinate)

## Setup Summary
| Field | Value |
|---|---|
| Org | mytestorg (Sandbox) |
| Agents / Supervisors provisioned | 5 / 1 |
| Routing targets | Case, MessagingSession |
| Service Channel strategy | Reused standard: Cases, sfdc_livemessage |

## Skill Outcomes
| # | Skill | Target(s) | Status | Notes |
|---|---|---|---|---|
| 1 | base-settings-configure | — | Reused | All 5 OmniChannel toggles already enabled |
| 2 | agent-users-create | — | Done | 5 agent users created |
| 3 | service-channel-configure | Case, MessagingSession | Reused | Standard Cases + sfdc_livemessage channels |
| 4 | queue-routing-config-deploy | Case | Done | Case_Routing_Config upserted (MostAvailable, weight 5) |
| 5 | queue-deploy | Case, MessagingSession | Done | Case queue aligned to Case_Routing_Config; messaging queue reused |
| 6 | queue-members-assign | Case, MessagingSession | Done | 5 agents bound to each target queue |
| 7 | routing-flow-deploy | Case | Done | Case routing flow deployed and active |
| 8 | presence-status-deploy | Case, MessagingSession | Done | Available_Case + Available_Messaging bound; Busy universal (reused) |
| 9 | permission-set-assign | — | Done | Omni_Agent assigned to 5 agents |
| 10 | supervisor-users-create | — | Done | 1 supervisor user created |
| 11 | supervisor-permset-assign | — | Done | ContactCenterSupervisor assigned to 1 supervisor |
| 12 | supervisor-config-deploy | — | Done | Omni_SupervisorCfg bound 1 supervisor + 2 discovered queues |

## Manual Actions Required
- **Login-behavior radio** — open Setup → Omni-Channel Settings → "Define login behavior when an agent opens a new window/tab" → select the desired option → Save. The `enableOmniAutoLoginPrompt` boolean deploys but does not drive this radio on v66.

## Artifacts
- `CREDENTIALS.json` (mode 0600) — generated agent + supervisor passwords. Read once, distribute securely, then delete (`rm -f`). Passwords are redacted from all other artifacts.
- Per-skill JSON artifacts + `.stderr.log` under the run's artifacts directory.

## Blocking Issues
None.

## Next Action
Read `CREDENTIALS.json` for the agent login, then log in, open the Service Console, click the Omni-Channel widget, set status to Online, and create a Case with Priority=Medium to observe routing.
```

---

## Template B — Partial run (a skill went red; dependents skipped)

Use when a prerequisite skill failed and the coordinator correctly skipped its dependents as `Blocked (dependency)`. The overall run is `red`; the report names the single blocker.

```markdown
# Omni-Channel Setup Report (via service-omni-channel-setup-coordinate)

## Setup Summary
| Field | Value |
|---|---|
| Org | mytestorg (CDO) |
| Agents / Supervisors provisioned | 5 / 1 |
| Routing targets | Case |
| Service Channel strategy | Reused standard: Cases |

## Skill Outcomes
| # | Skill | Target(s) | Status | Notes |
|---|---|---|---|---|
| 1 | base-settings-configure | — | Blocked | Deploy returned SucceededPartial; OmniChannel toggle did not stick |
| 2 | agent-users-create | — | Done | 5 agent users created |
| 3 | service-channel-configure | Case | Blocked (dependency) | base-settings did not succeed |
| 4 | queue-routing-config-deploy | Case | Blocked (dependency) | base-settings did not succeed |
| 5 | queue-deploy | Case | Blocked (dependency) | base-settings did not succeed |
| 6 | queue-members-assign | Case | Blocked (dependency) | queue-deploy did not succeed |
| 7 | routing-flow-deploy | Case | Blocked (dependency) | queue-members did not succeed |
| 8 | presence-status-deploy | Case | Blocked (dependency) | base-settings did not succeed |
| 9 | permission-set-assign | — | Done | Omni_Agent assigned to 5 agents |
| 10 | supervisor-users-create | — | Done | 1 supervisor user created |
| 11 | supervisor-permset-assign | — | Done | ContactCenterSupervisor assigned to 1 supervisor |
| 12 | supervisor-config-deploy | — | Blocked (dependency) | base-settings did not succeed |

## Manual Actions Required
- **Login-behavior radio** — (as in Template A)

## Artifacts
- `CREDENTIALS.json` (mode 0600) — generated agent + supervisor passwords. Read once, distribute securely, then delete.
- Per-skill JSON artifacts + `.stderr.log` under the run's artifacts directory.

## Blocking Issues
base-settings-configure returned SucceededPartial and the OmniChannel toggle did not persist on re-verify — every skill that requires Omni enabled was skipped as a dependency block.

## Next Action
Inspect the base-settings deploy for the org, resolve the partial-deploy failure, then re-invoke the coordinator (idempotent — completed skills are reused).
```

---

## Template C — Hard-stop before setup

Use when the readiness check failed and no writes were made — e.g. license shortfall, missing entity, production org without acknowledgement.

Fill **only** Setup Summary and Blocking Issues. Mark every skill row `Not started`. Point Next Action at the one thing that unblocks the run.

```markdown
# Omni-Channel Setup Report (via service-omni-channel-setup-coordinate)

## Setup Summary
| Field | Value |
|---|---|
| Org | mytestorg (Production) |
| Agents / Supervisors requested | 5 / 1 |
| Routing targets | Case |

## Skill Outcomes
| # | Skill | Status |
|---|---|---|
| 1–12 | all skills | Not started — blocked at readiness check |

## Blocking Issues
Target org is Production (IsSandbox=false, no TrialExpirationDate, OrganizationType=Enterprise Edition). safe_to_write=false; the coordinator refuses writes against production customer orgs.

## Next Action
Switch to a sandbox, CDO (trial), or Developer Edition alias and re-invoke.
```

---

## Report-quality checklist

Before emitting, mentally verify:

- [ ] Header ends with `(via service-omni-channel-setup-coordinate)`
- [ ] Every skill row's `Status` reflects the tracked state — not a hard-coded default
- [ ] A dependent skill whose prerequisite went red is shown as `Blocked (dependency)`, never `Done`
- [ ] The login-behavior click-path is surfaced whenever setup ran (even if the operator declines to turn the radio)
- [ ] **No plaintext passwords appear in the report** — they live only in `CREDENTIALS.json` (mode 0600); the report points the operator there
- [ ] **No Salesforce record IDs appear in the user-facing report** — human-readable names only
- [ ] A production org (`IsSandbox=false`, no `TrialExpirationDate`, non-DE/Base) was refused before setup started
- [ ] `Blocking Issues` is either `None.` or exactly one blocker (the coordinator should not chain multiple issues)
- [ ] `Next Action` is exactly one line — the single next step

---

## Anti-patterns to avoid

- AVOID: "Will create Omni_Demo_Cases_Queue" — say `Done` and list what was created, not what you plan to do
- AVOID: "Attempting to configure supervisor..." — the report emits after the action; describe the outcome, not the attempt
- AVOID: A plaintext password in `Next Action` or anywhere else in the report — point at `CREDENTIALS.json` instead
- AVOID: Salesforce record IDs in Skill Outcomes notes — human-readable DeveloperNames only, never `0C5RZ0000001I1J0AU`
- AVOID: Multi-line Blocking Issues — collapse to one line; if multiple issues, the coordinator should have stopped after the first
- AVOID: Preamble ("Here is the report you requested...") — jump straight to `# Omni-Channel Setup Report`
- AVOID: Design-doc padding ("The coordinator orchestrates multiple skills...") — the report is a status log, not a spec
