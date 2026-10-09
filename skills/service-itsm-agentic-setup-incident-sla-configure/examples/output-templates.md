# Output Templates — Incident SLA Setup

Canonical result-report strings for the SLA setup skill. Fill in the placeholders — do **not** substitute Salesforce record IDs into the user-facing output.

## Failure

Display the error from the `dispatch` response (`{status_code, body}`) exactly as returned, name the step that failed, and refer to `references/mcp-invocation.md` for known workarounds.

## Success — single milestone

```text
Incident SLA Setup Complete (via service-itsm-agentic-setup-incident-sla-configure)

Artifacts created:
  Milestone Type: <name> (No Recurrence)
  SLA Policy:     <name> (Active, Incident)
  Milestone:      <time> min, criteria: <criteria summary>
  Entitlement:    <name> (auto-provisioned; no Account — Incident engages per-Incident via EntitlementId)

Verification:
  Incident:  <IncidentNumber> — "<Subject>"
  SLA Start: <timestamp>
  Milestone: <MilestoneType name>
  Target:    <TargetDate> (Start + <timeTrigger> min)
  Status:    EntityMilestone auto-created — SLA is active

Chain: MilestoneType > SLA Policy > Milestone > Entitlement > Incident > EntityMilestone
```

## Success — multi-milestone (list every attached milestone)

```text
Incident SLA Setup Complete (via service-itsm-agentic-setup-incident-sla-configure)

Strategy: <Response + Resolution | Priority-tiered | Escalation ladder | Custom>

Artifacts created:
  Milestone Types: <name1>, <name2>, ... (No Recurrence)
  SLA Policy:      <name> (Active, Incident)
  Milestones:
    #1  <MilestoneType name>   <time> min   criteria: <summary>
    #2  <MilestoneType name>   <time> min   criteria: <summary>
    ...
  Entitlement:     <name> (auto-provisioned; no Account — Incident engages per-Incident via EntitlementId)

Verification:
  Incident:  <IncidentNumber> — "<Subject>" (Priority=<value>)
  SLA Start: <timestamp>
  EntityMilestones fired:
    - <MilestoneType name>   Target: <TargetDate>   (Start + <timeTrigger> min)
    - ...
  Status:    <N> EntityMilestone(s) auto-created — SLA is active

Chain: MilestoneTypes > SLA Policy > Milestones > Entitlement > Incident > EntityMilestones
```

If a test Incident was not created (verification partial), replace the Verification block with:

```text
Verification:
  SLA Policy confirmed active (Incident) with all <N> milestones attached.
  No test Incident was created, so EntityMilestone firing was not exercised in this run.
```

## Success — milestone actions (Phase 5, when Warn/Escalate was requested)

Append this **Milestone Actions** block to the multi-milestone success report above — do not emit it
alone. The report must still carry the policy, both milestones (name, time, criteria), the
Entitlement, the Verification section, and the scope line below.

```text
Milestone Actions attached:
  <MilestoneType name>:
    - Warning:   fires <X> min before target  ->  <action summary, e.g. raise Urgency = High>
    - Violation: fires at breach               ->  <action summary, e.g. raise Impact = High>
  <MilestoneType name>:
    - Warning:   fires <Y> min before target  ->  <action summary>
    - Violation: fires at breach               ->  <action summary>

  Warn offsets are computed per milestone (offset = round(target * (1 - warn%))); each milestone
  keeps its own offset. Escalate-on-breach is a Violation at the target (offset 0).

Confirmation: each action was confirmed from its create response (success + action mapping
returned). The attached warning/escalation settings can't be independently queried after creation,
so that create-response confirmation is the verification.

Scope: only the Incident SLA setup was configured — no other Setup preference was changed.
```

No record Ids in user-facing text — **every interim progress/narration message too**, not just these final templates (this enforces the SKILL.md **Output contract**): refer to the test Incident by its **`IncidentNumber`** and to milestones by their **`MilestoneType` name**, never the 15/18-char record Id.

**No implementation/MCP jargon in user-facing text.** Terms like "headless", "read-back", "dispatch", "Connect API", or operation ids are internal — never surface them in the report or narration. Say "the settings can't be independently queried after creation", **not** "no headless read-back". No files are produced — the skill mutates org configuration in place through headless-360 MCP dispatch.
