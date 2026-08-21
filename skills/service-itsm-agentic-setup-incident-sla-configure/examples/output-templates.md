# Output Templates — Incident SLA Setup

Canonical result-report strings for the SLA setup skill. Fill in the placeholders — do **not** substitute Salesforce record IDs into the user-facing output.

## Failure

Display the error from the `dispatch` response (`{status_code, body}`) exactly as returned, name the step that failed, and refer to `references/mcp-invocation.md` for known workarounds.

## Success — single milestone

```text
Incident SLA Setup Complete (via service-itsm-agentic-setup-incident-sla-configure)

Artifacts created:
  Milestone Type: <name> (OneTime)
  SLA Policy:     <name> (Active, Incident)
  Milestone:      <time> min, criteria: <criteria summary>
  Entitlement:    <name> -> Account: <account name>

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
  Milestone Types: <name1>, <name2>, ... (OneTime)
  SLA Policy:      <name> (Active, Incident)
  Milestones:
    #1  <MilestoneType name>   <time> min   criteria: <summary>
    #2  <MilestoneType name>   <time> min   criteria: <summary>
    ...
  Entitlement:     <name> -> Account: <account name>

Verification:
  Incident:  <IncidentNumber> — "<Subject>" (Priority=<value>)
  SLA Start: <timestamp>
  EntityMilestones fired:
    - <MilestoneType name>   Target: <TargetDate>   (Start + <timeTrigger> min)
    - ...
  Status:    <N> EntityMilestone(s) auto-created — SLA is active

Chain: MilestoneTypes > SLA Policy > Milestones > Entitlement > Incident > EntityMilestones
```

No record IDs in user-facing output. No files are produced — the skill mutates org configuration in place through headless-360 MCP dispatch.
