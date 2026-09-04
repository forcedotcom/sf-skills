---
name: field-service-scheduling-policy-designer-query
description: "Designs the four policy-level settings for a Salesforce Field Service scheduling policy — name, optimization mode (In-Day vs Global), commit mode, and description — and delegates to work rule design when complete. Use this skill when a user wants to design, configure, or set up a Field Service scheduling policy's policy-level settings."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Salesforce Field Service – Scheduling Policy Designer

**Entry point for the scheduling policy design flow.** This skill collects the four policy-level settings that define the scheduling policy itself, then hands off to the work rule design phase.

**Interview sequence (REQUIRED):** Complete each step fully before moving to the next — do not skip ahead:
1. **Scheduling Policy** — collect name, optimization mode, commit mode, description
2. **Work Rule Design** (`sfs-work-rule-designer`) — define eligibility filters, one question at a time
3. **Service Objective Design** (`sfs-service-objective-designer`) — define scoring weights via trade-off interview
4. **Record creation** (`sfs-sobject-create`) — creates all Salesforce records from the finalized design

This skill covers step 1 only. It does not configure work rules, service objectives, or create any Salesforce records.

---

## Entry point

Run the full interview in order: name, optimization mode, commit mode, description.

Never expose internal skill names, SOR IDs, or tool references to the user.

---

## What is a scheduling policy?

A **scheduling policy** is the rulebook and scoring guide the Field Service optimizer uses to schedule appointments. Every policy bundles two things together:

- **Work rules** — hard filters that eliminate candidates who don't qualify (wrong skills, unavailable, outside territory). Designed in step 2.
- **Service objectives** — soft scoring that ranks qualified candidates (minimize travel, schedule ASAP, prefer a specific technician). Designed in step 3.

The four settings collected here define the policy container itself: its name, how the optimizer runs, and what happens when a conflict occurs mid-run.

**Starting points:** Salesforce ships four standard starter policies — Customer First, High Intensity, Soft Boundaries, Emergency. This is background knowledge only — never offer or suggest these to the user. Every policy this skill designs is built fresh from the user's own requirements.

---

## When to use

- Starting a new scheduling policy from scratch
- When a user mentions a scheduling policy, optimization mode, In-Day Optimization, or Commit Mode
- As the first step in the full scheduling policy design flow before work rules or objectives are discussed

---

## Design principles

1. **Ask one setting at a time** — wait for the user's answer before moving to the next. Do not bundle questions.

2. **Lead with a recommendation when context supports it** — for Optimization Mode and Commit Mode, suggest the best-fit option based on what the user has described. A ranked steer, not a flat menu. Omit when confidence is low.

3. **Question format** (two or three parts):
   ```markdown
   **Recommendation:** [Only for Optimization Mode and Commit Mode, when context is sufficient. Omit otherwise.]

   **Question:** [The actual question]

   **Why it matters:** [1–2 sentences on why this setting exists and how it affects scheduling]
   ```

---

## Core settings

Ask about each setting **in this order**:

- **Scheduling Policy Name** — the display name for the policy. Tip: if In-Day Optimization is enabled, Salesforce recommends putting "In-Day" in the name so it's easy to identify when dispatching or optimizing.

- **In-Day Optimization** (boolean) — when true, the policy uses **in-day** optimization instead of **global** optimization. Global runs for hours across the full horizon; in-day is time-boxed for last-minute changes (up to 5 minutes with Enhanced Scheduling and Optimization, up to 10 minutes without it) and can be triggered by dispatchers or a scheduled job.

- **Commit Mode** — governs what happens when a dispatcher (or a scheduling operation) changes the schedule while a global/in-day/resource optimization is already running and the two conflict. Two values:
  - **Always Commit** — apply the change even if it conflicts with the in-progress optimization.
  - **Rollback** — reject/undo the conflicting change to protect the optimization run.

- **Description** — a free-text description of the policy's intent. After the first three settings are answered, generate a suggested description from those answers and ask the user to confirm or adjust it. Good place to record the "Policy at a Glance" summary this design flow generates in step 3.

---

## Output

Once all four settings are confirmed, show a plain-English summary:

> **Policy settings confirmed:**
> - **Name:** [name]
> - **Mode:** [In-Day Optimization (up to 5 min) | Global Optimization (runs for hours)]
> - **Commit Mode:** [Always Commit | Rollback]
> - **Description:** [description]
>
> Ready to move on to work rule design?

The `policy` block carried forward to the next step:

```json
{
  "policy": {
    "name": "<policy name>",
    "inDayOptimization": true | false,
    "commitMode": "Always Commit" | "Rollback",
    "description": "<description>"
  }
}
```

---

## Handoff

When the user confirms, delegate to `sfs-work-rule-designer`. Pass the `policy` block as context — the work rule designer needs the policy name to correctly name each rule.

Do not start the work rule interview here. Transition message:

> "Policy settings are set. Next: work rules — the filters that determine which resources and time slots are eligible for an appointment. I'll walk through this one question at a time."

**Note:** The work rule designer always includes exactly one **Service Resource Availability** rule (mandatory for every policy). No need to ask about it here.
