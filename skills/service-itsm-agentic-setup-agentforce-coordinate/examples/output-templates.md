# Output Templates — service-itsm-agentic-setup-agentforce-coordinate

Emit one of these text blocks at the corresponding step in the workflow. Setup is presented as
**two sequential stages** — Stage 1 (enable platform features) must finish before Stage 2 (install
& activate agent templates). Only items with a working child skill appear — hide placeholder rows.

## Feature menu (Behavior step 3)

```text
Agentforce for ITSM Setup (via service-itsm-agentic-setup-agentforce-coordinate)

Here are the features available for Agentforce ITSM. Set them up in two stages —
Stage 1 (enable) must finish before Stage 2 (install & activate):

┌───┬─────────┬──────────────────────────────┬────────────────────────────────────────────────────────┬──────────┐
│ # │ Stage   │ Item                         │ Description                                            │ Status   │
├───┼─────────┼──────────────────────────────┼────────────────────────────────────────────────────────┼──────────┤
│ 1 │ Stage 1 │ Agentforce Studio enablement │ Turn on org-level Agentforce, Einstein GenAI, and IT   │ Not done │
│   │         │ (Foundation for all agents)  │ Service agent features                                 │          │
│ 2 │ Stage 2 │ IT Service Fulfiller Agent   │ Automate actions and simplify critical asks for IT     │ Not done │
│   │         │                              │ service fulfillers who work with incidents, problems,  │          │
│   │         │                              │ change requests and more to resolve issues and         │          │
│   │         │                              │ requests.                                              │          │
│   │         │                              │ Setup: creates the agent from this template and        │          │
│   │         │                              │ activates a version.                                   │          │
│ 3 │ Stage 2 │ IT Service Employee Agent    │ Help employees quickly troubleshoot IT issues, raise   │ Not done │
│   │         │                              │ service requests, and track their incidents with ease. │          │
│   │         │                              │ Setup: creates the agent from this template and        │          │
│   │         │                              │ activates a version.                                   │          │
│ 4 │ Stage 2 │ Specialized Agents           │ Use the specialized templates and build agents that    │ Not done │
│   │         │ for Employee                 │ power your employee agent. Refine the agent logic, as  │          │
│   │         │                              │ necessary, and then activate them.                     │          │
│   │         │                              │ Setup: pick one specialized template (e.g. Password    │          │
│   │         │                              │ Manager, Onboarding), then create and activate that    │          │
│   │         │                              │ standalone agent. Re-run this item to add more.        │          │
└───┴─────────┴──────────────────────────────┴────────────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the features you want to set up (one or more, e.g. `1` or `1, 2`).
If you pick a Stage 2 template without Stage 1, I'll enable the Stage 1 foundation first.
```

Stage 1 (Agentforce Studio enablement) is the **foundation** — it enables the org-level platform
features every agent is built on. Stage 2 items (the Fulfiller agent, the Employee agent, and
Specialized Agents for Employee) are **installed from a template and activated**; they can be set up
in any order once Stage 1 is done.

**Specialized Agents for Employee** is a third Stage 2 item, shown right after the IT Service
Employee Agent to keep the two employee options together. Both use the same child skill
(`service-itsm-agentic-setup-employee-agent-configure`): the IT Service Employee Agent installs the
broad, ready-to-go employee agent, while Specialized Agents for Employee starts from one of the
specialized employee templates (for example Password Manager, Certificate Management, Onboarding, or
Hardware Request). Ask which specialized template the user wants **before** delegating this item —
the child skill defaults to the broad agent when handed no name (which would just re-create the IT
Service Employee Agent), and once given a name it disambiguates a partial or ambiguous match. The
chosen template names the agent it creates. The specialized templates themselves are turned on in
Stage 1; this item is where you build and activate an agent from them.

## Post-feature progress (Behavior step 5)

Example after Stage 1 (Agentforce Studio enablement) completes:

```text
Agentforce Studio — enabled successfully
(via service-itsm-agentic-setup-agentforce-studio-configure)

┌───┬─────────┬──────────────────────────────┬─────────────┐
│ # │ Stage   │ Item                         │ Status      │
├───┼─────────┼──────────────────────────────┼─────────────┤
│ 1 │ Stage 1 │ Agentforce Studio enablement │ Done        │
│   │         │ (Foundation for all agents)  │             │
│ 2 │ Stage 2 │ IT Service Fulfiller Agent   │ Not done    │
│ 3 │ Stage 2 │ IT Service Employee Agent    │ Not done    │
│ 4 │ Stage 2 │ Specialized Agents           │ Not done    │
│   │         │ for Employee                 │             │
└───┴─────────┴──────────────────────────────┴─────────────┘

Stage 1 (foundation) is enabled. On to Stage 2 — install and activate the IT
Service Fulfiller agent, the IT Service Employee agent, and/or a specialized
employee agent from their templates. The Fulfiller agent gives IT technicians an
assistant for triage, case summaries, and record automations; the Employee agent
gives requesters self-service help with their own requests; and Specialized
Agents for Employee builds a focused employee agent (such as Password Manager or
Onboarding) from a specialized template you pick.
```

## Completion summary (Behavior step 6)

The completion summary fires either (a) after every item completes, or (b) when the user says they
are finished — even if some items are still `Not done`. When rendering:

- Substitute each row's actual tracked status: `Done`, `In progress`, or `Not done`. Do NOT
  hard-code `Done`.
- Choose the header line based on whether every item is `Done`:
  - All items `Done` → `Agentforce for ITSM Setup — Complete`
  - Any item still `Not done` or `In progress` → `Agentforce for ITSM Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your Agentforce for ITSM setup is complete.`
  - Otherwise → `You have finished the items you selected. The remaining items can be resumed later by re-invoking this orchestrator.`

Example — user finished after only enabling Agentforce Studio (the Stage 2 agents stayed `Not done`):

```text
Agentforce for ITSM Setup — Finished
(via service-itsm-agentic-setup-agentforce-coordinate)

┌───┬─────────┬──────────────────────────────┬─────────────┐
│ # │ Stage   │ Item                         │ Status      │
├───┼─────────┼──────────────────────────────┼─────────────┤
│ 1 │ Stage 1 │ Agentforce Studio enablement │ Done        │
│   │         │ (Foundation for all agents)  │             │
│ 2 │ Stage 2 │ IT Service Fulfiller Agent   │ Not done    │
│ 3 │ Stage 2 │ IT Service Employee Agent    │ Not done    │
│ 4 │ Stage 2 │ Specialized Agents           │ Not done    │
│   │         │ for Employee                 │             │
└───┴─────────┴──────────────────────────────┴─────────────┘

You have finished the items you selected. The remaining items can be
resumed later by re-invoking this orchestrator.
```
