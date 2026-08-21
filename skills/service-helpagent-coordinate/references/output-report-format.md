# Output Report Format — Help Agent Setup

> **When to read this file.** Load it right before you write the final `report.md` for a run. This file is the full specification for the two report shapes (settled-facts and guided-decision), the templates, and the failure modes to avoid. `SKILL.md` links here from its Output Expectations section.

## The one deliverable

A single `report.md`: a **status report of what was decided and done**, not a design doc, plan, or architecture write-up. Two rules govern quality:

1. **Report concrete outcomes, never intentions.** Write what *is* — the decided value, the created resource, the resolved ID — not what you *would* or *plan to* do. If a step could not run to completion because this is a non-interactive run, **decide the sensible default, state it as the decision, and report it as such** — do not stall on "awaiting confirmation," "to be resolved," "pending user input," or "please provide…". Hedging language ("will create", "to be executed", "once confirmed") reads as an unfinished plan and is scored as incomplete. Name the agent, the locale, the grounding source, `authMode`, the ADL name, the `rag_feature_config_id`, the site `UrlPathPrefix`, the ESD publish state — as settled facts.
2. **No padding, no scaffolding prose.** No preamble, no design-doc sections, no restating the prompt. Dense, declarative lines only.

**Density bar (web-chat / portal flows are the usual offenders).** The whole report is the two tables plus the two short sections — target well under ~40 lines total. A table cell is a **value or a short clause, never a sentence with a subject and verb**: `UnAuth` not "The authMode was set to UnAuth"; `Help_Agent_Knowledge (indexing COMPLETED)` not "A dedicated Agentforce Data Library named Help_Agent_Knowledge was created and its indexing completed". Do not restate a decided value across multiple cells, do not narrate the mechanics of how a resource was created (which API, which CLI call, which retrieve/deploy sequence) — that belongs in the skill, not the report — and do not append explanatory prose after a table. State the reasoning callout (readiness ordering, `authMode`) only when the request centers on that one decision; otherwise the value alone suffices.

## Choosing a report shape

**Before writing, choose the report shape by what the run actually did. There are two:**

- **A settled-facts report** — the flow *executed a step*: the user directed a concrete action ("set up the grounding", "put it on <named site>") and every input was supplied or has a sensible skill-owned default. Report what was decided and done.
- **A guided-decision report** — the flow is at a *decision the user owns*: an opening request with no agent details yet ("set up a help agent", "add a chat widget"), **or** a checkpoint surfacing multiple real alternatives the skill must not invent (e.g. several Live LWR sites). Presenting the checkpoint's questions/options *is* the deliverable; stay draft-first.

Use the settled-facts report, not the guided-decision one, when the missing value is a mechanical default the skill can just pick (data category → org default) — decide it and report it done. Use the guided-decision report only when the choice genuinely belongs to the user (identity at an opener; which of several existing sites). The guided-decision report is **not** an escape hatch for hedging on an execute request.

## Settled-facts report

**Settled-facts report — the flow ran (completed, or blocked mid-execution).** Start with the exact H1 `# Help Agent Setup Report`, then the two tables and two short sections below, in order. Every cell is a **concrete, decided value** — a bare value, not a sentence. Keep prose out.

**Report DECISIONS as settled facts, never placeholders or intentions.** This is a non-interactive run: you do not get to defer. Do NOT emit "to be captured", "not yet reached", "flow is paused", "awaiting", "once confirmed", or "will create". For a value the flow **decides** (agent name, locale, tone, ADL name, `authMode`, data category), state the concrete decision as done — a cell with nothing decided gets `None`. For an **opaque ID the run generates** (the `rag_feature_config_id`, a Salesforce record Id, a site's URL path prefix), report the **actual value produced this run** — never invent a plausible-looking one and never copy an ID from this template; if the run genuinely did not produce it, name that in Blocking Issues rather than fabricating. Hedging is scored as incomplete; fabricated IDs are scored as inaccurate. Include every value below and nothing else.

**Scope the report to the checkpoint(s) the request targeted — do not narrate checkpoints the run never entered.** When the user directs a single checkpoint ("set up the grounding", "ground it on Knowledge" → Checkpoint 2 only), the report centers on that checkpoint. Fill its row with settled facts; give each checkpoint the run did **not** reach a bare `Not started` in its Decision cell — no plan, no "pending", no "not yet reached", no downstream detail. Do **not** manufacture a `Blocking Issues` entry or a `Next Action` about a later checkpoint you were never asked to run: if the targeted checkpoint completed, `Blocking Issues` is `None` and `Next Action` is the single next checkpoint by name (e.g. "Checkpoint 3 (channel) when you're ready"). A report that sprawls into unrequested checkpoints and hedges there is scored as incomplete even when the targeted checkpoint is perfect.

**When the request centers on one decision, carry that decision's reasoning — not a bare value.** Some requests are about a single load-bearing choice: *why the readiness steps run in a specific order*, or *which `authMode` to pick and why*. For these, the targeted cell (or a short `## <Topic>` section right after the tables) must state the **decision, its rationale, and the concrete failure it avoids** — because that reasoning is the deliverable, not scaffolding:

- **Readiness ordering** — give the ordered sequence (licenses / Einstein Agent User → **enable Data Cloud** → **assign Data Cloud permission sets**), say *why* the order is load-bearing (the permission sets do not exist until Data Cloud is enabled — assigning first fails with `PermissionSet not found: GenieUserEnhancedSecurity`), and warn that skipping the assignment yields empty runtime grounding even when ADL indexing reports SUCCESS. Do not compress this to "perm sets assigned". If Data Cloud is not yet enabled on this org, the Readiness row must say so — never assert "Data Cloud enabled; perm sets assigned" while `Blocking Issues` says it isn't; that contradiction is scored as inaccurate.
- **`authMode` choice** — name the value (`UnAuth` for an anonymous-or-mixed audience), state the rationale (`UnAuth` allows **both** guests and authenticated upgrades via `identityToken`; `Auth` is authenticated-only and silently breaks the guest widget and the Setup "Test Enhanced Web Chat" page), confirm the audience it was chosen for, and state the assertion as a settled part of the flow — "the deployed MessagingChannel is re-fetched and `embeddedConfig.authMode = UnAuth` is asserted" — **present tense, not "will be re-fetched"**. Do not compress this to "authMode UnAuth". The `authMode` decision is complete once chosen: do **not** frame it as pending ("to be confirmed"), and do **not** manufacture a `Blocking Issues` entry or `Next Action` about the *adjacent* site-resolution step — a scoped `authMode` request is not blocked on the LWR site. If nothing stopped the scoped decision, `Blocking Issues` is `None`.

The `‹…›` slots below mark where **this run's** real values go — replace each slot, never emit the slot text itself:

```markdown
# Help Agent Setup Report

## Setup Summary
| Field | Value |
|---|---|
| Readiness | Data Cloud enabled; perm sets assigned (GenieUserEnhancedSecurity, GenieAnalytics, DataSpacePermSet); Einstein Agent User assigned |
| Failure mode guarded | Stock NOT_SCHEDULED ADL → empty knowledgeSummary; guarded via dedicated ADL, indexing gated to COMPLETED |
| Delegation | agentforce-generate → agent + ADL; dx-org-permission-set-assign → Data Cloud perms; service-digital-engagement-* → channel + ESD |

## Checkpoint Outcomes
| # | Checkpoint | Decision |
|---|---|---|
| 1 | Identity | ‹agent name› (‹DeveloperName›), ‹locale›, ‹tone› |
| 2 | Grounding | Salesforce Knowledge via agentforce-generate; dedicated ADL ‹library name› (stock All_Records_and_Fields_Default not wired); indexing gated to COMPLETED before wiring; rag_feature_config_id ‹ARFPC_ id from this run's adl publish› captured |
| 3 | Channel | Web Chat; authMode ‹UnAuth or Auth›; site ‹target site UrlPathPrefix›; ESD HelpChat WebV2 — *or* `Not started` if the run never entered this checkpoint |
| 4 | Go-live | ESD Published; channel Active; escalation flow wired — *or* `Not started` |

## Blocking Issues
‹the one thing that actually stopped the flow — one line — or `None`›

## Next Action
One line — the single next step for the user.
```

Non-slot values above (Data Cloud, perm-set names, `HelpChat WebV2`, delegation targets) are the skill's canonical defaults — reproduce them as-is. Fill the `‹…›` slots from this run (including `authMode`, which is decided per run from the Step B choice — do not default it in the report). **Any checkpoint the run did not reach gets a bare `Not started` — not a plan, forecast, or "pending" note.** For a request scoped to one checkpoint (e.g. Checkpoint 2 grounding), only that row carries settled facts; rows 3 and 4 read `Not started`, `Blocking Issues` is `None`, and `Next Action` names the next checkpoint (e.g. "Checkpoint 3 (channel) when you're ready").

**Blocked run?** `Blocking Issues` is the one sanctioned place to state a real blocker — one honest line there (e.g. "multiple Live LWR sites — asked user to choose"; "Knowledge data category not specified — chose the org's default group") is **required and is not hedging**. It records what stopped a checkpoint the run *actually entered* — never a checkpoint the request never targeted (a scoped Checkpoint-2 run is not "blocked" on Checkpoint 3). Keep the checkpoint cells decisive for what *was* settled; put the single unresolved thing here. What is scored as incomplete is hedging *inside the decision cells* ("to be captured", "not yet", "pending") — not a clear one-line blocker in this section.

### Multi-channel run — trace the loop, don't report one channel

When the request names **two or more channels** ("web chat first, then Voice — add both"), the settled-facts report must show every named channel was wired. One `Not started` in the Channel row, or a Channel cell that names only the first channel with the second framed as "next step" / "to be added", is scored as an incomplete loop. The up-front request authorizes all the named channels, so the flow wires them in order **without** a between-branch `AskUserQuestion` — report that prompt-level authorization, never a user reply that did not occur. Expand the Channel row into a short trace right after the `## Checkpoint Outcomes` table — one row per named channel:

```markdown
## Channel Loop
| Step | Outcome |
|---|---|
| Channel 1 — ‹type› | ‹settled facts: authMode for Web Chat, resolved site/UrlPathPrefix or phone number, ESD/routing state› |
| Advance | ‹next named type› named up front in the request → wired next without a between-branch prompt |
| Channel 2 — ‹type› | re-entered Checkpoint 3; ‹settled facts for this branch› |
| Go-live | all named channels wired; proceed to go-live |
```

Only when the prompt did **not** name a channel does the between-branch `AskUserQuestion` run — in that case report the options offered and the actual selection. Every named channel gets a settled outcome (or a one-line blocker in `Blocking Issues` if a branch genuinely could not complete). Do not stop the trace after Channel 1.

## Guided-decision report

**Guided-decision report — a decision the user owns.** Here the deliverable is *the decision point itself*, presented cleanly. This is not hedging: at an opener or a genuine fork, asking with sensible defaults is the correct, complete response. Do **not** provision, deploy, or fabricate the value the user still owns. Orient, present the current checkpoint's choices with defaults, sketch what the remaining checkpoints will cover, and confirm nothing is live yet. Use exactly these sections:

```markdown
# Help Agent Setup Report

## Guided Setup
Help Agent setup runs as four checkpoints: identity → grounding → channel → go-live. Nothing is created, deployed, or published until you confirm at each step.

## Current Checkpoint
Checkpoint ‹n — name›. This agent will ‹map the user's stated needs to the design in one line: knowledge-grounded Q&A from Salesforce Knowledge, support-case create/update, and escalation to a live human when needed›, delivered as ‹the channel the user named, e.g. a Web Chat widget on their site›.

## Decisions Needed
- ‹Question 1 — offered default› (e.g. Agent name — `Help Agent`, API name `Help_Agent`)
- ‹Question 2 — offered default› (e.g. Language — `en_US`)
- ‹Question 3 — offered default› (e.g. Greeting, Tone)
- ‹…the real choices for THIS checkpoint only; for a multi-option fork, list the actual alternatives found (e.g. each Live LWR site by Name + UrlPathPrefix) and never pick for the user›

## Checkpoint Roadmap
- Readiness (silent, before provisioning): confirm licenses / Einstein Agent User → enable Data Cloud → assign the Data Cloud permission sets, in that order.
- 2 Grounding: connect Salesforce Knowledge via a dedicated Agentforce Data Library, indexing gated to COMPLETED.
- 3 Channel: deploy the chosen channel + Embedded Service Deployment; confirm `authMode` from who will be chatting.
- 4 Go-live: embed, publish, and verify with a live round-trip — only after you confirm.

## Next Action
Reply with your choices (or accept the defaults) and I'll proceed to the next checkpoint. Nothing is created, grounded, embedded, or published until you confirm at each step.
```

Fill every `‹…›` from this run's context. Keep to these five sections — the Roadmap names what later checkpoints will do (it is not a settled-fact table and must not claim any of it is done); no provisioning tables, no settled-fact cells for steps not yet reached.

## Never include

Each of the following is a scored failure:

- A preamble restating the prompt or the request
- The skills-inventory pre-flight roll call (the eight `OK:` / `resolve-at-runtime:` dependency lines). That check is silent and for your own awareness — it is **not** part of the deliverable. Only name a sibling skill in the report if a delegation step actually reached it and it could not be resolved, and then only that one skill, as a one-line `Blocking Issues` entry.
- "End of report." trailers
- Decorative `---` / `===` rules
- `Scope`, `Assumptions`, `Out-of-Scope`, `Architecture`, `Options Considered`, `Next Steps`, `Steps:`, or `Outcome Gate:` sections
- The checkpoints re-listed as questions
- The agent script or reference-file contents pasted inline
- Emoji
- Marketing adjectives ("seamless", "robust", "powerful", "comprehensive")
