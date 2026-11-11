---
name: building-flow-approval-process
description: "Build Salesforce Flow Approval Processes (processType: ApprovalWorkflow). Use when the user wants to 'create a flow approval process', 'build an ApprovalWorkflow', 'set up multi-level approval with flows', 'configure approval orchestration', 'add approval stages to a flow', or encounters errors such as 'Submit for Approval doesn\\'t work with Flow Approval Processes' or 'Outputs reference doesn\\'t exist'. Not for Classic Approval Processes (Setup > Approval Processes)."
metadata:
  version: "1.0"
---

## Goal

Design, implement, and deploy Salesforce Flow Approval Processes (`processType: ApprovalWorkflow`), covering the full stack: orchestration flow, background steps, approval steps, screen flows, WebLink triggers, and required Lightning page components.

## When to Use This Skill

Activate this skill for:
- Creating a new multi-level approval process using Flows (not Classic Approval Processes)
- Configuring `orchestratedStages`, Background Steps, and Approval Steps in an `ApprovalWorkflow` flow
- Setting up the WebLink button that launches the orchestration
- Debugging errors specific to Flow Approval Processes (`Submit for Approval not supported`, output reference syntax failures, subflow restrictions)
- Adding `Flow Orchestration Work Guide` and `Approval Trace` components to a record page

**Delegate elsewhere** for Classic Approval Processes (Setup > Approval Processes), record-triggered flows, or Apex-based approval routing.

## Classic vs. Flow Approval Process — Critical Distinction

| | Classic Approval Process | Flow Approval Process |
|---|---|---|
| Setup location | Setup > Approval Processes | Setup > Flows (`processType: ApprovalWorkflow`) |
| Trigger | `Submit for Approval` action | WebLink URL button → `/flow/FlowApiName?params` |
| Entry conditions | Record criteria | Background Step + Evaluation Flow |
| Steps | Linear steps | `orchestratedStages` containing `stageSteps` |

**Never use the "Submit for Approval" Flow action with an ApprovalWorkflow.** Salesforce documentation states explicitly: *"This action doesn't submit a record for approval using Flow Approval Processes."*

## Flow Generation — Mandatory Delegation

An ApprovalWorkflow solution involves multiple flows. Apply this rule for each:

| Flow type | How to generate |
|---|---|
| AutoLaunched flows (calculation, evaluation, status update) | **Use `generating-flow` skill** — 3-step MCP pipeline (`fetchGroundedObjectMetadata` → `flowElementSelection` → `flowElementGeneration`). Never write XML manually. |
| Screen Flow (approver review UI) | **Use `generating-flow` skill** — same 3-step MCP pipeline. |
| ApprovalWorkflow orchestration (`processType: ApprovalWorkflow`) | **Write XML manually** — the MCP pipeline does not support this processType. Use the XML patterns in `references/xml-patterns.md`. |

Generate all component flows **before** the orchestration. The orchestration references them by API name in `actionName` attributes.

## Core Workflow

1. **Define entry variables** — declare the 4 mandatory input variables on the orchestration
2. **Generate supporting flows** — use the `generating-flow` skill to create each AutoLaunched flow and the Screen Flow via the MCP pipeline
3. **Design orchestration stages** — model each approval level as an `orchestratedStage` with Background Steps and Approval Steps
4. **Wire decision routing** — use Decision elements between stages, referencing Background Step outputs via `{!StepName.Outputs.variableName}` syntax
5. **Write the ApprovalWorkflow orchestration XML** — using patterns from `references/xml-patterns.md`
6. **Create the WebLink trigger** — build the URL button on the object; add to the page layout
7. **Add Lightning components** — place Flow Orchestration Work Guide and Approval Trace on the record page
8. **Deploy in order** — follow the required deployment sequence to avoid dependency failures
9. **Validate** — submit a test record and verify each stage transitions correctly

## Architecture Pattern

```
WebLink Button
  └── /flow/ApprovalOrchestration?recordId=...&submitter={!$User.Id}&retURL=...
        └── ApprovalWorkflow (processType: ApprovalWorkflow)
              ├── Background Step → AutoLaunched Flow (calculate level / init status)
              ├── Decision (route by level output)
              ├── Stage N1
              │     ├── Approval Step (Screen Flow — approver UI)
              │     └── Background Step (update status)
              ├── Decision (Approve / Reject)
              ├── Stage N2 — same pattern
              └── Stage N3 — same pattern
```

## Required Orchestration Variables

Declare these 4 input variables on every ApprovalWorkflow orchestration:

| Variable | dataType | isInput |
|---|---|---|
| `recordId` | String | true |
| `submitter` | String | true |
| `submissionComments` | String | true |
| `firstApprover` | String | true |

Missing any of these causes runtime errors even if the variable is not used in the flow logic.

## Step Types Reference

### Background Step
- `actionType: stepBackground` / `stepSubtype: BackgroundStep`
- Calls an AutoLaunched flow (`TriggerType: None`)
- `requiresAsyncProcessing: false`, `runAsUser: false`, `shouldLock: false`
- Inputs accept variable references or string literals only — no calculated expressions

### Approval Step
- `actionType: stepApproval` / `stepSubtype: ApprovalStep`
- Calls a Screen Flow for the approver UI
- `requiresAsyncProcessing: true`, `runAsUser: true`, `shouldLock: true`
- `assigneeType`: `Queue`, `User`, or `Group`
- Output `approvalDecision` must be exactly `"Approve"` or `"Reject"` (case-sensitive)

## Output Reference Syntax

Reference Background Step outputs in downstream elements:

```
{!StepName.Outputs.variableName}
```

- In a Decision element: `<leftValueReference>CalcLevel.Outputs.approvalLevel</leftValueReference>`
- In a subsequent Background Step input: `<elementReference>CalcLevel.Outputs.approvalLevel</elementReference>`
- Approval decision: `<leftValueReference>Approbation_N1.Outputs.approvalDecision</leftValueReference>`

## Screen Flow — Required Variables

The approver Screen Flow must declare these variables with exact names:

**Inputs:** `approvalInformation` (String), `recordId` (String)

**Outputs:** `approvalDecision` (String) — value must be exactly `"Approve"` or `"Reject"`; `approvalComments` (String)

Add a `faultConnector` on every `recordLookups` element displaying `{!$Flow.FaultMessage}`.

## Hard-Stop Constraints

These cause deployment or runtime failures:

- **No `<subflows>` element** in an ApprovalWorkflow — use Background Steps instead
- **No Custom Error elements** in AutoLaunched flows called by Background Steps (`TriggerType: None`)
- **No calculated expressions** as Background Step inputs — variable references and string literals only
- **No `Submit for Approval` action** to trigger an ApprovalWorkflow — WebLink URL only
- **No** `hasMenubar`, `height`, `position`, `isResizable` on a WebLink with `openType: replace`
- **Deletion via Metadata API fails** when the flow has execution history — delete from Setup UI

## Required Lightning Page Components

Add both components to the record page via Lightning App Builder:

1. **Flow Orchestration Work Guide** — shows pending work items to approvers
2. **Approval Trace** — shows approval history

Without these, approvers have no interface to process their work items.

## Deployment Order

Deploy in this sequence to avoid dependency errors:

1. Custom objects and fields
2. AutoLaunched flows (calculation, evaluation, status update)
3. Screen Flow (approver review UI)
4. ApprovalWorkflow orchestration
5. WebLink + page layout

```bash
SF_LOG_FILE=/dev/null sf project deploy start -m "Flow:MyFlowName" --ignore-conflicts -o my-org
```

## Common Errors Quick Reference

| Error | Cause | Fix |
|---|---|---|
| `This action doesn't submit a record for approval using Flow Approval Processes` | Classic "Submit for Approval" action used | Replace with WebLink URL button |
| `CalcLevel.approvalLevel doesn't exist` | Missing `Outputs.` in reference syntax | Use `CalcLevel.Outputs.approvalLevel` |
| `firstApprover / submissionComments received nothing` | Required orchestration variables missing | Declare all 4 mandatory input variables |
| `Flows of type ApprovalWorkflow can't include Subflow elements` | Subflow element used | Replace with Background Step |
| `Can't include Custom Error elements when TriggerType is None` | Custom Error in AutoLaunched flow | Remove Custom Error; let fault propagate |
| `insufficient access rights on cross-reference id` on delete | Flow has execution history | Delete from Setup UI, not Metadata API |
| WebLink deployment failure with `openType: replace` | Forbidden properties included | Remove `hasMenubar`, `hasScrollbars`, `height`, `position`, `isResizable` |

## Additional Resources

### Reference Files

For complete XML patterns and templates, consult:
- **`references/xml-patterns.md`** — Full XML for orchestration variables, WebLink, Background Step, Approval Step, and Screen Flow variables
