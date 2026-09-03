<!--
  OWNER: Service Cloud (see catalog/test-drives.json → owner).
  STATUS: v0.2 — spike-validated (feasibility spike 2026-08-24). The build runs end-to-end via the
  agentforce-generate skill: author an AiAuthoringBundle agent (AgentforceServiceAgent) with FAQ,
  case lookup/create/update, and escalation, back the case actions with invocable Apex, then
  validate + deploy. Actions were verified against real org data.
  The framework seeded this; the Service Cloud team owns making it sing and keeping it current.
  This file is INJECTED AND RUN VERBATIM by the engine as if the user typed it — keep it in a
  natural, user's-voice style. Authoring guidance (what to pre-answer vs. leave live, how to mark
  manual Setup checkpoints) lives in ../AUTHORING.md, not here. Do not add engine/meta commentary
  to the runnable prompt below.

  MANUAL SETUP CHECKPOINTS the runtime must narrate (spike findings — no CLI/skill automates these):
    1. Website chat widget: wiring the agent to a Messaging for Web / Embedded Service channel is a
       Setup task (there is no channel-configure skill). Narrate it as a "⏸ In Setup, go to …" pause.
    2. Email-to-case: also Setup-only; narrate, don't choreograph.
    3. Service-agent escalation (@utils.escalate) needs a messaging connection configured for a live
       handoff; without it, escalation degrades to offering to log a case (the agent handles this).
    4. Try-it-out is interactive: `sf agent preview` is a TTY UI (no headless/scriptable mode), so the
       engine hands off to the user to run it — it does not auto-verify the conversation.
-->

I want to add a help agent to my Salesforce org so customers can get answers to common questions,
manage their support cases, and reach a human agent when they need one. I'd like it available as a
chat widget on our customer website.

Build the whole thing end to end against my connected org: create the agent, give it the topics and
actions it needs to answer FAQs, look up and update cases, and escalate to a human, then deploy it and
wire it up as a website chat channel so I can try it out. Walk me through the choices that shape how
the agent behaves — its persona, the topics it should cover, and when it should hand off — and handle
the setup plumbing yourself. When a step has to happen in Setup that you can't do for me, tell me
exactly what to click and I'll do it, then we keep going.
