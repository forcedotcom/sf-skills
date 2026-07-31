# Voice Latency Heuristics

Voice agents live and die on latency. Under ~2 seconds between "caller stops
speaking" and "agent starts speaking" feels natural; every additional second
erodes the illusion of talking to a person. Text agents can hide a slow tool
behind a spinner — voice agents can't. This reference encodes the latency
anti-patterns worth catching at **authoring** time (`/agentforce-generate`) and
diagnosing from **traces** (`/agentforce-observe`).

Each pattern has three parts: **detection** (how to spot it in the `.agent`
bundle or a trace), **impact** (typical cost), and **fix** (instructional patch,
action/tool change, or flag-for-human).

> **Fix classification.** Only *purely instructional* fixes (adding an ack
> phrase, tightening turn length, adding a spoken-form rule) are safe to apply
> automatically. Anything that changes an action's implementation, its
> synchronicity, or an org/channel-level setting is **flag-only** — surface it
> with the specific object/action named and let a human decide.

---

## 1. Synchronous writes on the live-call critical path

The single biggest latency killer in the field. Any write (DML, external
callout, trigger cascade) that runs *inside* the turn between caller-speaks and
agent-speaks adds directly to perceived response time.

**Detection**
- An action's target performs a write and runs synchronously in the reasoning turn.
- The action name/description implies mutation: `update`, `insert`, `log`, `commit`, `save`, `record`, `create`, `submit`.
- A trigger fires on the target object (custom or managed-package).

**Impact**
- Simple insert with a normal trigger: ~300–800ms.
- Managed-package trigger cascade on a heavy object: multiple seconds.
- Chained callout inside the trigger: add ~1–3s per hop.

**Fix**
- **Preferred:** move the write to post-call via a Platform Event or async queue.
- **Interim:** wrap the write in a Queueable and return immediately from the action.
- **Instructional (auto):** add an ack phrase before the action ("One moment while I get that on file.").
- **Flag for human:** if the write MUST happen mid-turn (authentication, payment authorization), don't rewrite — flag with the specific object and trigger names.

## 2. Large result sets returned raw to the reasoning LLM

Retrieval that returns the full body of every matching record is a hidden
latency *and* accuracy tax — the model has to filter needles from a hayfield
every turn, on a bloated context.

**Detection**
- Action description mentions `search`, `retrieve`, `knowledge`, `articles`, `documents`.
- Action returns more than ~5 items or ~2KB of text per call by default.
- No `limit` / `top_k` / `max_chars` parameter surfaced to the planner.
- Return type is the raw object (article, record), not a summarized shape.

**Impact**
- Seconds per call, plus downstream reasoning slowdown on the bloated context.
- Degraded answer accuracy.

**Fix**
- **Action change:** summarize first (title + 1–2 sentence excerpt), page the rest behind a follow-up action.
- **Action change:** add a `limit` parameter with a low default (3–5); name the allowed range in its `description` (Agent Script has no `enum` input attribute — see `actions-reference.md` "Voice-Safe Action Authoring" rule "Enumerate small value sets in the description").
- **Instructional:** if the action stays bulky, add an ack phrase ("This can take a few seconds — hang with me.").
- **Flag for human:** if the customer intentionally wants wide-net RAG over their whole KB, surface the tradeoff instead of rewriting.

## 3. Chained external callouts

Every external HTTP hop is a chance for tail latency. Two hops brings the p95 of
both to the caller.

**Detection**
- An action's implementation makes 2+ external HTTP calls per invocation.
- A trigger on the target object hits a webhook or external system.

**Impact**
- Per hop: ~200–800ms typical, seconds at p95.
- Two chained hops: p95 easily crosses several seconds.

**Fix**
- **Flag for human** with the specific hops named — the topology matters.
- Where feasible, propose consolidating hops server-side or pre-fetching in parallel.

## 4. Over-decomposed multi-subagent routing

A monolithic agent is often faster *and* more accurate than a deep tree of
subagents fronted by a classifier. Each planner turn costs ~1–2s; each subagent
handoff can add another. This is the voice cost of the "dead hub" and
"over-routing" anti-patterns already tracked in `known-issues.md`.

**Detection**
- The bundle has several subagents whose only job is to route to one other subagent.
- A classifier/guardrail subagent intercepts every utterance before the primary agent.

**Impact**
- Extra planner round-trips per turn; unexpected orchestrator calls when subagents chain.

**Fix**
- **Flag for human:** collapsing multi-subagent → flatter routing is a design decision.
- Where the structure must stay, ensure each hop has an ack phrase.
- Consider whether a guardrail subagent can become instruction-level rules in `system:`.

## 5. Long agent turns trip the silence/nudge timer

On long agent turns, the platform's "are you still there?" nudge (Speak-Up) can
fire before the caller has had a chance to respond, producing an awkward overlap
or dead air. This is the same root cause as the response-verbosity check in
`/agentforce-observe`.

**Detection**
- Response templates or instructions that produce turns over ~30 words / ~10s of speech.
- Welcome/greeting message longer than one or two sentences.

**Impact**
- Dead air, overlap, or a spurious "still there?" prompt on the first or a long turn.

**Fix**
- **Instructional (auto):** enforce ≤2-sentence turns everywhere (the "Keep responses concise" rule in `voice-modality-reference.md`); keep the greeting to one sentence.
- **Flag for human:** if long turns are legally required (disclaimers), the silent/nudge timing is an **org-level** setting, not an agent-bundle change.

## 6. TTS number / currency / ID garble

TTS engines read `$172,576.81` or `+14155551212` as garble unless the model
pre-formats them into spoken form.

**Detection**
- Instructions or action outputs surface prices, phone numbers, IDs, dates, or account numbers.
- No rule telling the model to render numbers in spoken form.

**Impact**
- Callers hear unintelligible strings; erodes trust and forces repeats.

**Fix**
- **Instructional (auto):** add the spoken-form number rule (the "Render numbers, prices, and IDs in spoken form" rule in `voice-modality-reference.md`).
- **Flag for human:** if the deployment language has weak TTS number-normalization coverage, note the gap so the instruction rule carries the load.

## 7. Premature end-of-turn under noise (STT endpointing)

Callers in noisy environments (drive-throughs, call centers, home appliances)
get cut off before they finish because the STT endpointer signals end-of-turn
too aggressively.

**Detection**
- Deployment is telephony (PSTN/SIP) rather than a web client.
- Customer domain suggests a noisy environment (auto, retail, home services).
- Endpointing silence threshold left at the default.

**Impact**
- Truncated caller utterances, repeated turns, frustration.

**Fix**
- **Flag for human (org-level):** raise the endpointing silence threshold for noisy environments (typical safe range ~300–900ms; lean higher when noisy). This is a channel/STT setting, not an agent-bundle change.
- **Instructional (auto):** add an ASR repair prompt (Rule for misheard input in `voice-modality-reference.md`) so a truncated utterance recovers gracefully.

## 8. Telephony transport hops (SIP / multi-region)

Every trunk hop and region crossing on the SIP path adds latency. Largely
outside the agent bundle's control, but worth flagging.

**Detection**
- Deployment metadata mentions multiple trunks, a non-local region, or a third-party telephony proxy.

**Fix**
- **Flag for human only.** Not an agent-bundle-level fix.

---

## Automatable checks

Grep the `.agent` bundle (and, for `/agentforce-observe`, cross-reference the
trace) for these:

| Pattern | Meaning | Severity | Fix class |
|---|---|---|---|
| Mutating action (name/description implies write) runs synchronously in the turn | Sync write on critical path | high | flag (+ ack phrase auto) |
| Retrieval action returns > ~5 items / > ~2KB with no `limit` parameter | Bulky retrieval | high | flag |
| Action implementation makes 2+ external HTTP calls | Chained callout | medium | flag |
| Several subagents that only route to one other subagent | Over-routing / dead hub | medium | flag |
| Response templates > ~30 words, or greeting > 1–2 sentences | Nudge/long-turn risk | medium | instructional (auto) |
| Prices / phone / IDs referenced with no spoken-form rule | TTS garble | medium | instructional (auto) |
| Slow action (SOQL, external HTTP, retrieval) with no ack phrase in instructions | Missing filler | high | instructional (auto) |

## What NOT to change automatically

- Synchronous writes required to happen mid-turn (payment auth, identity verification) — flag with the reason.
- Retrieval where the customer explicitly wants wide-net RAG — flag with the tradeoff.
- Endpointing / silence / nudge thresholds — these are **channel/org-level** settings, not agent-bundle.
- SIP topology — a platform/telephony decision.

## Related

- `voice-modality-reference.md` — instruction rules (ack phrases, spoken-form numbers, repair prompts, turn length).
- `actions-reference.md` — voice-safe action authoring (descriptions, parameter names, error shapes).
- `known-issues.md` — dead-hub / over-routing anti-patterns.
- `/agentforce-observe` — trace-driven latency diagnosis (Phase 1 voice checks).
