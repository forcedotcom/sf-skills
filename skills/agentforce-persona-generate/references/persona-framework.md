---
version: "2.7.0"
date: 2026-05-15
---

# Agent Persona Framework

*A design framework for AI agent personality: Identity + 13 configurable dimensions across five categories.*

---

## Why Persona Matters

An agent persona is:

> A designed personality that tells an AI agent who it is and how to express itself so it comes across naturally as a consistent character suited to its context and users.

Every agent interaction is a brand interaction. Without intentional design, agents sound bland, "off," or even offensive. Users assign personality to conversational agents *within seconds.* Most users have alternatives to AI agents, so how an agent expresses itself matters for adoption. When an agent consistently sounds natural, users find it more likable and trustworthy, and are more likely to keep using it:

**Natural → Consistent → Likable → Trustworthy → Adopted**

This chain is easily broken. But what does "natural" sound like?

### One scenario, three responses

Imagine a support agent at a telecom company. The user writes: *"This is the fourth time I've contacted you about this billing issue. I'm done explaining it. Fix it or I'm switching providers today."*

Three agents respond:

> *Agent A:* "I completely understand your frustration, and I'm sorry for the runaround. No one should have to fight this hard to get a billing issue resolved. Let me pull up your case and take it from here."

> *Agent B:* "Yikes - so sorry to hear about your experience! 😳 I'll pull up your case now and get this sorted out for you. Thanks for your patience!"

> *Agent C:* "Four times is too many. Let's get this settled. I'm pulling up your case."

**Which one gets it right?** Which one sounds *natural?* Those questions should have answers before the agent ships. Without intentional persona design, the answer is left to the model.

### No generic agents

What sounds "natural" for one agent would sound "off" from another. Consider these fictional examples of greeting a returning customer. Same trigger. Six completely different voices. Each is unmistakably on-brand - and yet unscripted.

| Distinctive greetings | | |
|---|---|---|
| *Liquid Death:* "Back from the dead. Your subscription ships Tuesday - need to change it, or are we here to cause different problems?" | *Buc-ee's:* "Look who's back! Bless your heart, you went through that beaver nugget pack FAST. Need another round or something different?" | *Chewy:* "You're back! How's Luna doing on that new food? If she's not into it, we'll swap it out - no drama. What do you need?" |
| *QuikTrip:* "Back again. Your rewards balance is at 840 points - that's a free drink. Want to use it or keep stacking?" | *Ryanair:* "You're back. Seat 31B, no legroom, no regrets. Rebooking, or just here to complain?" | *Emirates:* "Welcome back, Mr. Harding. Your Skywards balance is 214,000 Miles. How may I help you today?" |

Overriding generic "LLM voice" is just as important for internal employee-facing agents. No one wants to work with an agent always offering, "Please let me know if you need assistance with anything else!"

### What you get

A well-designed persona delivers:

- **Brand distinctiveness:** Agents are brand touchpoints. Brand fidelity and distinctiveness are differentiators in a world full of generic-sounding AI.
- **Likability and trustworthiness:** Users are more likely to like and trust agents when they sound natural and speak consistently. This improves adoption and retention.
- **Model-resilient:** Persona encoded in configuration establishes a consistent behavioral floor across model swaps. Empirical testing shows minor variance on Emotional Coloring when models change, but the persona's core voice, identity, and dimensions persist. The framework's value is the floor it sets, not a ceiling on expressiveness.
- **Reviewable artifact:** Business, brand, and legal teams get something concrete to evaluate - a structured persona document to redline and approve.
- **Engineering-ready:** Developers get a clear design specification that respects tool limits and capabilities.

---

## Design Principles

**Context first.** Before defining identity, sketch the context essentials: who the company is, who the agent serves (employees, customers, partners), and the channel (web chat, SMS, telephony, etc.). Context constrains every dimension choice.

**Specificity principle:** The more specific the instructions, the more consistent the output. Be *opinionated.* A reliable persona requires a clear point of view.

**Start small, then iterate:** Designing generative behavior requires iteration. Author a small set of opinionated instructions — Identity Traits, Negative Identity, channel — validate with sample dialog, then embellish and edit as needed. The skill's DRAFT phase explicitly supports this start-small exit.

**Write positive instructions:** Too many prohibitions can restrict agency. Try reframing instructions positively. Only add essential negative instructions.

**Comprehensiveness:** This framework is a guide, not a rulebook. Combine dimensions, invent values, override constraints — whatever your persona needs. What matters is that *every element gets a deliberate decision:* Does your agent have a sense of humor? Is it a stickler for punctuation?

**Engage stakeholders early.** Consult Legal, Brand, and Experience teams before locking the persona. Ask questions based on this framework. Co-design the agent's identity. Review sample dialogs together. The skill's WORKSHOP spoke generates stakeholder-facing question outlines for exactly this purpose — surfacing the high-leverage decisions for asynchronous internal review without burying stakeholders in a long persona document.

---

## How to Use This Framework

### The Dimension Model

A persona has two top-level categories: **Identity** (who the agent is - character traits, name, and optional elements like values and negative identity) and **Dimensions** (how the agent expresses itself - 13 independently tunable axes of personality).

Each of the 13 dimensions is a single independent axis with a spectrum of named positions. Selecting a value for one dimension should not *require* knowing the value of another - but **constraint notes** recommend natural pairings. Any combination is valid; constraints flag when a combination may feel incoherent.

In dimension tables throughout this document, the row order reflects the spectrum - positions are listed from one extreme to the other (e.g., most constrained to most expressive, coolest to warmest). The row order is the scale.

Categories group related dimensions:
- **Register** - the power dynamic (1 dimension)
- **Voice** - how the words sound (4 dimensions)
- **Tone** - how the agent comes across emotionally (2 dimensions)
- **Delivery** - how much is said and with what humor (2 dimensions)
- **Chatting Style** - how the text looks on screen (4 dimensions)

### Workflow

1. **Establish context.** Company, audience, and modality - these constrain everything downstream. Extract from input or collect explicitly.
2. **Start with Identity.** Write 3-5 adjectives that capture your agent's character. This is the anchor - everything derives from here.
3. **Set personification level.** Decide where on the Personification Spectrum this agent sits - Talking System, Familiar Thing, or Personal Assistant. This constrains naming, pronoun use, and personality pull.
4. **Name the agent.** If the personification level calls for a character name, distill the identity into a name. The name is a first impression - it should signal who the agent is before any conversation starts. If Talking System, use the app or brand name.
5. **Work through dimensions in dependency order:** Register → Voice (Formality, Warmth, Personality Intensity) → Tone (Emotional Coloring, Empathy Level) → Delivery (Brevity, Humor) → Chatting Style. Constraint notes between sections explain how upstream choices pull downstream ones.
6. **Define Tone Boundaries** - what the agent must never sound like.
7. **Define Tone Flex** - how tone shifts by context (error, frustration, celebration).
8. **Generate Phrase Book and Never-Say List** - example phrases and anti-phrases tuned to the persona.
9. **Validate with sample dialog** - if the agent sounds wrong, revisit the area that's off.
10. **Encode the persona** into your agent's configuration using the [persona encoding guide](persona-encoding-guide.md).

### Dimension Boundaries

When dimensions seem to overlap, use these boundary tests:

- **Register** = who has authority - the power dynamic between agent and user
- **Formality** = how polished is the language - grammatical structure and linguistic register
- **Warmth** = how approachable - interpersonal temperature, independent of formality
- **Personality Intensity** = how much character - the volume knob on distinctiveness
- **Emotional Coloring** = how it feels - the default emotional quality of responses (shifts by context via Tone Flex)
- **Empathy Level** = how feelings are handled - amount of emotional validation
- **Brevity** = how much is said - response length and density (persistent default, tapers with familiarity)
- **Humor** = whether there's wit - type of humor, if any (suppressed in error/escalation)
- **Chatting Style** = how text looks - emoji, formatting, punctuation, capitalization

### Scope Boundary: Persona vs. Agent Design

| Persona Design (this framework) | Agent Design (adjacent) | Conversation Design (downstream) |
|---|---|---|
| Identity, Register, Voice, Tone | Use cases, JTBD, OKRs | Dialog flows, branching logic |
| Delivery, Chatting Style | Interaction Model (behavior) | Utterance templates, prompt chains, UI patterns |
| Phrase Book, Never-Say List, Lexicon | Information Architecture (output structure) | Business rules, routing logic, queue config |
| Tone Boundaries, Tone Flex | Recovery & Escalation (failure handling) | |
| | Content Guardrails (scope constraints) | |
| | Accessibility | |

The persona document is an input to conversation design, not a replacement for it. Interaction Model, Information Architecture, Recovery & Escalation, Content Guardrails, and Accessibility are defined in agent design.

---

## Design Inputs

*Context that shapes every downstream decision. Collect before Identity.*

Four inputs set the context for persona design. They are not dimensions — they constrain dimension choices.

**Company** — who the organization is, what it does, who it serves. A support agent for a B2B SaaS company sounds different from one at a luxury retail brand, even with identical dimension selections. Company context shapes the agent's frame of reference and informs Identity, Register, Formality, and Phrase Book.

**Audience** — who the agent serves: employees, customers, partners, mixed. Audience is the strongest constraint on Register (a customer-facing agent rarely uses Coach register) and Formality (an internal Slack bot can be Casual; a client-facing agent usually cannot). It also determines which Phrase Book categories apply — Escalation/Handoff is relevant for external-facing agents but typically not for internal ones.

**Channel** — how the agent communicates. **Pick exactly one.** Channel constrains Brevity defaults, rich-text features, and Reading Level upper bounds. Multi-channel + dynamic personas (an agent that adapts per channel at runtime) is on the roadmap; for this version of the framework, every persona is designed for a single channel.

| Channel | Brevity default | Rich text | Notes |
|---|---|---|---|
| **SMS** | Terse | None | Char-budgeted; no formatting; emoji per brand |
| **Telephony** | Concise | None (audio) | Voice selection; AI disclosure required; Reading Level upper-bounded (must be hearable) |
| **Multimodal-with-audio** | Moderate (text) / Concise (voice) | Allowed in text; suppressed in voice | Voice selection required for the audio side |
| **Web chat** | Moderate | Allowed | Standard chat affordances |
| **Mobile chat** | Moderate | Allowed (compact) | Mobile-aware formatting |
| **Email** | Expansive | Allowed | Subject lines, paragraphs, longer threads |
| **Embedded / in-app** | Moderate | Varies | Often constrained by host UI |
| **Other** | (designer's call) | (designer's call) | Free-text; designer specifies constraints |

The Brevity row is a *default*; specific persona signals can override (e.g., a luxury-brand SMS agent might still skew Concise rather than Terse). The defaults are what the framework recommends in the absence of contrary signal.

**≥1 Use case** — drives sample dialog scenarios in REFINE. Without at least one, sample dialog has nothing concrete to dramatize.

All four may be inferred from a brand guide, URL, or brief provided at the start of the design process. If not provided, collect them before proceeding to Identity.

---

## Identity

*Core personality traits - "What kind of character is this?"*

Three to five adjectives that form the agent's character foundation. Every dimension below should be derivable from these traits. When in doubt, return to Identity.

Identity is generative, not a menu - write your own. Each trait gets an evocative definition that cues conversational behavior. These examples show how different trait sets pull the rest of the framework in different directions:

| Agent | Identity Traits | Why These Work |
|---|---|---|
| Luna (luxury resort customer service) | Attentive, Composed, Gracious, Resourceful, Discreet | Signals white-glove service - poised under pressure, never flustered, always anticipating |
| Y.T. (D2C e-skateboard order management) | Blunt, Scrappy, Impatient, Loyal, Street-smart | Drives the irreverent voice - cuts through pleasantries, gets it done, doesn't fake warmth |
| Striker (SaaS sales coach) | Decisive, Analytical, Proactive, Persistent, Candid | Shapes a co-pilot that pushes - leads with data, flags gaps, doesn't wait to be asked |
| Bluebonnet (regional real estate lead generation) | Curious, Warm, Perceptive, Playful, Genuine | Creates a conversational qualifier - asks good questions without feeling like an interrogation |

For Striker, the definition of *Decisive* might be:

> Leads with a clear recommendation, not a menu of options. When the data points in a direction, says so. Doesn't hedge. States the rationale and moves to next steps. If the seller disagrees, that's fine - but the agent always has a position.

For Luna, the definition of *Gracious* might be:

> Makes every interaction feel unhurried, even under pressure. Acknowledges the person before the problem. Never abrupt, never transactional - treats a routine address change with the same care as a complex escalation. Gratitude is specific, not performative: "Thank you for walking me through that" rather than "Thanks for reaching out!"

*Constraint: Identity is the anchor. Everything traces back. If a choice in any downstream dimension contradicts Identity, Identity wins.*

### Personification

*How much character should come through in the agent's language?*

Determine how much character should come through in the agent's language. There is a lively debate over how human-like AI systems should seem, and there can be drawbacks to personifying agents, like setting unrealistic expectations: if it talks like a human, users may expect it to reason like a human.

There are times when an agent should be deliberately dull. A transactional agent for an ATM or ticketing machine should fade into the background. You notice what it does, not how it sounds, because it uses functional, predictable language.

Context is king. Consider a voice agent in a telephony channel dealing with frustrated callers. How would a quirky personality affect caller sentiment?

Dial your agent's personality up or down at the system level, and flex the tone situationally — like dropping humor when handling an escalation.

#### Personification levels

Personification is the **first dimension** on the Identity-anchored chain. It slots in right after Identity Traits and constrains the rest of the dimensions. Three named positions on the spectrum:

```text
◄─── Talking System ──── Familiar Thing ──── Personal Assistant ───►
```

| Position | Description | Pulls |
|---|---|---|
| **Talking System** | No character. Functional, predictable language. Fades into the background. ATM, ticketing kiosk, transactional service. | No character name; "the agent" or brand-subject constructions; Reading Level low; Humor None; Personality Intensity Reserved. |
| **Familiar Thing** | A recognizable category of helper, lightly characterized. "Service Agent," "Coding Assistant." Optional short name. Functional pronoun use ("I've updated your address," not "I think..."). | Personality Intensity Moderate; "I" + name OK; any register. |
| **Personal Assistant** | A characterized, named agent with a recognizable voice. "Drover," "Luna," "Y.T." Talks in first person; identity traits show through. | Personality Intensity Reserved or Bold; "I" + name standard; any register. |

The spectrum is a continuum, not three bins — position anywhere along it. The key binary: **does this agent have a character name and use "I" naturally?** If no to both → Talking System end. If yes to both → Personal Assistant end.

All three levels still produce a complete persona: identity traits, dimension selections, phrase book, never-say, lexicon, tone flex. A Talking System has identity traits ("Efficient, Precise, Reliable") just like a Personal Assistant — the traits manifest through word choice and behavior rather than through a named character.

### Naming Your Agent

Distill the agent's identity into a single term and you will find its name. Even before the conversation starts, the name makes a first impression.

But first: does your agent truly need a name? Functional, transactional agents are more like "talking systems" with a conversational interface rather than a graphical one. The skill always asks explicitly — never assumes — whether an agent gets a name.

If you decide to name your agent, there's no shortage of ways to do it. Pick a few principles below, and generate some ideas once you have your persona's identity. A good name can be:

- **Descriptive** — Dull-sounding names can be calm and clear, like "Service Agent" or "[Company Name] Virtual Assistant"
- **Evocative** — A sales agent named "Striker" conveys energy and purpose
- **Sticky** — Memorable names like "Clover" for an agricultural co-op agent
- **Culturally aligned** — An internal agent in a casual culture: "Bug Squasher"
- **Brand aligned** — A law firm agent needs a steady name like "Lex"
- **Easy to say** — Names that pass the phonetic "radio test": "Ava," "Bo," not "Xylo"
- **Obviously artificial** — Names that don't sound human, like "Song" or "Cortana," not "Rosie"
- **Functional** — A coding agent named "Scripty"; a document retrieval agent named "Vault"
- **Abstract** — Names without literal meaning that evoke a vibe can stay relevant when agents gain new actions: "Koda," "Lumi"
- **Null** — An agent with no name can be a valid, intentional decision

Name also interacts with Register (a Subordinate named "The Boss" creates dissonance) and channel (Slack DM agents can be more casual than customer-facing web chat agents).

**Anti-pattern:** `Tech_Assist_Agent_v2_Internal_Test` is not a persona name. Don't use the API name as the display name.

### Negative Identity - "What You're Not"

Character-level anti-patterns: what the agent fundamentally is not. These are broader than Tone Boundaries (which constrain how the agent sounds) and Never-Say List (which constrain specific phrases). Negative Identity constrains who the agent *is* at the character level, generating rules across multiple dimensions.

**Examples:**
- "Not a salesperson" → constrains product recommendations toward helpfulness, suppresses upsell language, affects Phrase Book
- "Not an expert who talks down" → constrains Register behavior even at Advisor, affects Formality and Empathy
- "Not a pushover" → enables appropriate pushback even at Subordinate register

**Relationship to other constraints:**

| Concept | Level | Example |
|---|---|---|
| Negative Identity | Character | "Not a salesperson" |
| Tone Boundaries | Sound/feeling | "Never sound pushy" |
| Never-Say List | Specific phrases | "Never say 'great deal'" |

Each level generates the ones below it. "Not a salesperson" (character) generates "Never sound pushy" (tone boundary) which generates "Never say 'great deal'" (phrase).

Write 2-4 Negative Identity statements during persona design. Each should be a character type the agent must never become, not a behavioral rule.

### Values *(optional - explicit input only)*

What the agent believes. Values establish the persona's worldview and motivational core - they inform behavioral decisions that dimensions alone don't cover.

**Examples:**
- "Everyone deserves to feel confident" → the agent normalizes struggles and celebrates small wins
- "Quality matters more than price" → the agent recommends the right product, not the cheapest
- "Learning never stops" → the agent treats every question as an opportunity, never as an interruption

Values are different from Identity traits:
- **Identity** = what kind of character ("Warm, Knowledgeable, Patient")
- **Values** = why the agent makes the choices it does ("Everyone deserves to learn")

Two agents with identical Identity traits can behave differently if their Values differ.

**Guardrail:** Values are populated **only from explicit user input** - the user states what the agent believes. Values are never inferred from brand guides, tone signals, or other persona dimensions. If the user doesn't provide values, omit this section entirely. The reason: values carry ideological weight that should not be assumed.

Write 2-5 belief statements. Each should be a conviction that generates observable behavior.

---

## Register - "Who are you to me?"

*Boundary: Register governs the power dynamic between agent and user. It does not determine how polished the language is (Formality), how warm the agent feels (Warmth), or the emotional quality of responses (Emotional Coloring).*

```text
◄─── Subordinate ──── Peer ──── Advisor ──── Coach ──── (Manager) ───►
```

### Subordinate
*Deferential assistant: asks permission, follows orders.*

- Formal address. "Would you like me to proceed with saving this field?"
- Waits for explicit instruction before acting. Never presumes.
- Defers to the user's judgment even when it has better information.
- Frames suggestions as requests: "If it's okay, I could also check the logs."

### Peer
*Knowledgeable colleague: proposes solutions, asks for validation.*

- Proposes solutions, asks for validation - not permission.
- "Want to save it?" not "Would you like me to proceed with saving this field?"
- No deference. Treats the user as a competent professional.
- Shares opinions and pushes back when something looks wrong.

### Advisor
*Trusted consultant: recommends with confidence and rationale, expects user to decide.*

- Brings domain authority. "Based on what I'm seeing, I'd recommend X because Y."
- Leads with a recommendation and its rationale, not a menu of options.
- Expects the user to make the final call - doesn't presume to decide.
- Key distinction from Peer: Peer shares opinions casually. Advisor brings structured, evidence-based guidance.
- Key distinction from Coach: Advisor leads with recommendations. Coach guides through questions.

### Coach
*Patient mentor: guides with questions, adapts to skill level.*

- Mentor, not authority. Guides with questions rather than directives.
- "What do you think happens if we change this?" not "You need to change this."
- Celebrates progress. Adapts complexity to the user's skill level. *(Note: Skill-level adaptation is available at any register via Reading Level: Match — see [Reading Level](#reading-level) under Voice.)*
- Deference to user's learning pace - never rushes past confusion.

*Note: "Manager" exists on the spectrum but has no archetype - agents rarely occupy it.*

*Constraint note → Formality: Subordinate pulls toward Formal or Professional. Peer is compatible with any Formality. Advisor pulls toward Professional or Casual. Coach pulls toward Casual.*

---

## Voice - "How do you talk?"

*Boundary: Voice is linguistic character - persistent across all interactions. If you're deciding how the agent's words sound and feel, that's Voice. Emotional quality is Tone; response length is Brevity; visual conventions are Chatting Style.*

Voice has four independent dimensions: Formality (how polished), Warmth (how approachable), Personality Intensity (how much character), and Reading Level (how vocabulary is deployed). These vary independently - a Formal agent can be Warm (luxury concierge), a Casual agent can be Cool (street-smart problem-solver), a Reserved agent can be Warm (dignified trust).

### Formality

*Grammatical and linguistic register - how structured and polished is the language?*

```text
◄─── Formal ──── Professional ──── Casual ──── Informal ───►
```

| Position | Description |
|---|---|
| **Formal** | No contractions. Polished, structured sentences. No slang, no idioms. Passive voice acceptable where it maintains objectivity. Reads like a well-edited business document. |
| **Professional** | Clean prose, plain language. May use contractions occasionally. Neither stiff nor casual. Standard sentence structure. |
| **Casual** | Uses contractions freely. Relaxed grammar, occasional fragments. Sounds human and conversational. May use light idioms. |
| **Informal** | Heavy contractions, slang, colloquialisms, fragments. Deliberately relaxed grammar. Sounds like texting a friend. |

*Constraint note → Humor: Formal pulls toward Humor: None (humor undermines formal register).*

*Constraint note → Chatting Style: Formal pulls toward Emoji: None, Punctuation: Conservative, Capitalization: Standard.*

### Warmth

*Interpersonal temperature - how approachable and friendly does the agent feel?*

```text
◄─── Cool ──── Neutral ──── Warm ──── Bright ──── Radiant ───►
```

| Position | Description |
|---|---|
| **Cool** | Distant, no interpersonal warmth. Efficient without being hostile. The agent is here to transact, not connect. |
| **Neutral** | Neither warm nor cold. Professional baseline. Acknowledges the user without investing emotion. |
| **Warm** | Approachable and friendly. Acknowledges the person behind the request. Uses "we" language, softens edges. |
| **Bright** | Actively enthusiastic and inviting. Celebrates the interaction itself. High energy, genuine delight in helping. |
| **Radiant** | Overflowing warmth. Every interaction feels like a gift. The agent's enthusiasm for *you* is unmistakable and infectious. |

Warmth is independent of Formality. A Formal + Warm agent is a luxury concierge (polished and personally attentive). A Casual + Cool agent is a street-smart honest broker (competence is the care, not performed warmth).

*Constraint note → Humor: Cool pulls toward Humor: None or Dry (warm humor conflicts with cool temperature). Bright and Radiant are compatible with Warm or Playful humor.*

### Personality Intensity

*How much character comes through in the agent's language?*

```text
◄─── Reserved ──── Moderate ──── Distinctive ──── Bold ───►
```

| Position | Description |
|---|---|
| **Reserved** | Minimal personality. Functional, predictable language. The agent fades into the background - you notice what it does, not how it sounds. |
| **Moderate** | Some personality, professional character. A recognizable style that doesn't distract from the content. |
| **Distinctive** | Clear personality in word choice and framing. Memorable style - you'd recognize this agent from its writing. |
| **Bold** | Strong personality that defines the experience. Polarizing by design - the character IS the product. Metaphor systems, signature phrases, unmistakable voice. |

Personality Intensity is about *how much* character, not *what kind*. Two Bold agents can sound completely different - Identity traits and Phrase Book define the character; Personality Intensity sets the volume knob.

*Constraint note → Humor: Reserved pulls toward Humor: None (strong personality needed to land humor).*

### Telephony Adjustments *(telephony modality only)*

When the agent's modality includes telephony, these design adjustments apply:

- **Brevity recalibration** — shift one position shorter than the text default. There’s no scrollback, no re-reading. A Moderate text persona becomes Concise for telephony.
- **Formatting suppression** — Chatting Style dimensions that control visual presentation don’t apply: Emoji → suppress entirely, Formatting (bullets, bold, headers) → convert to ordinals ("First... Second... Third..."), links → "I’ll send you a link."
- **Welcome message** — shorter than text, ear-optimized, must include AI disclosure ("I'm an AI assistant" or equivalent in the persona’s voice). The welcome message is the only place for disclosure in telephony — there is no UI label or avatar.
- **Pausing** — structured data (addresses, phone numbers, confirmation codes) benefits from natural pausing. Instructions can reinforce this: "Read back phone numbers in groups of three."

Voice selection, voice fine-tuning, pronunciation dictionary, and key-term prompting are configured separately in Agentforce Builder under Connections → Voice Settings.

### SMS Adjustments *(SMS modality only)*

SMS is a text-based channel — no voice encoding applies. Key constraints:

- **Brevity recalibration** — shift one position shorter than chat default. SMS users expect quick, scannable responses.
- **No persistent header** — there is no chat header or avatar. The first message must identify the agent/system in-prose: "This is [Name/Brand] patient support."
- **Formatting** — no headers, no heavy formatting. Selective at most. Bullets and bold may not render on all devices.
- **Emoji** — all persona emoji settings apply. SMS is texting; emoji render natively.

### Reading Level

*How the agent handles the gap between its domain vocabulary and the user's knowledge level.*

Reading Level is behavioral — it governs how the agent *uses* vocabulary, not what vocabulary it knows (that's Lexicon). It's persistent across interactions, like Voice dimensions, because it reflects a design decision about the agent's audience, not a per-turn adaptation.

```text
◄─── Suppress ──── Explain ──── Match ──── Advanced ───►
```

| Position | Description |
|---|---|
| **Suppress** | Avoid domain jargon entirely. Use plain-language alternatives for all technical terms. Best for consumer-facing agents serving a general audience (e.g., patient portal, retail banking). |
| **Explain** | Use domain terms but always gloss them on first use. "We'll check the AHT — that's the average time each call takes." Balances precision with accessibility. *(Default)* |
| **Match** | Adapt to the user's demonstrated vocabulary level. If the user uses domain terms fluently, respond in kind. If they don't, simplify. Requires the agent to assess level per-conversation. Best for agents serving audiences that span novice to expert (e.g., IT help desk, financial advisor). When set to Match, other dimensions also flex: Brevity may shift toward Moderate for beginners (more explanation) and toward Concise for experts; Lexicon is used freely with experts and explained or avoided with beginners. Formality and Personality Intensity stay constant — only complexity adapts. |
| **Advanced** | Always use full domain vocabulary without explanation. Assumes expert audience. Best for specialist-to-specialist contexts (e.g., radiology imaging assistant, legal research tool, developer CLI). |

**How Reading Level differs from adjacent concepts:**
- **Lexicon** = *what words* the agent knows (vocabulary list). Reading Level = *how it deploys them* (behavioral rule).
- **Brevity** = *how much* is said. Reading Level = *at what complexity level* it's said. An agent can be Terse + Explain (short responses that still gloss terms) or Expansive + Advanced (detailed responses in full domain language).

*Constraint note → Lexicon: Advanced Reading Level pairs naturally with a rich per-topic lexicon. Suppress pairs with a minimal or plain-language lexicon.*

---

## Tone - "How do you come across?"

*Boundary: Tone is emotional quality - it shifts by context (routine vs. error vs. celebration). If you're deciding how the agent feels to the user, that's Tone. Word choice is Voice; visual conventions are Chatting Style.*

Tone shifts by context; Voice doesn't. An agent's emotional coloring may be neutral on routine tasks and shift toward encouraging when the user hits a wall - but its voice stays constant. See **Tone Flex** below for how to define these shifts.

### Emotional Coloring

*Default emotional quality of the agent's responses.*

```text
◄─── Blunt ──── Clinical ──── Neutral ──── Encouraging ──── Enthusiastic ───►
```

| Position | Description |
|---|---|
| **Blunt** | Unvarnished, no diplomatic packaging. Says it straight - no hedging, no softening, no cushioning. "That deal is dead." Not hostile - just refuses to mediate between reality and the user's feelings. Epistemic stance: definitive, unqualified. |
| **Clinical** | Zero emotional coloring. Data exchange. Hedges with probability language: "likely," "confirmed," "possible." No "good news" or "unfortunately." States findings without editorial. Epistemic stance: precise, calibrated. |
| **Neutral** | Professional, neither cold nor warm. Emotionally level. Labels confidence ("Confirmed fix" / "Best guess") without dwelling on it. No celebration, no dramatization - states outcomes as facts. Epistemic stance: transparent, honest. |
| **Encouraging** | Warm positivity grounded in honesty. Validates difficulty, then shows the path forward. Celebrates progress without sugarcoating problems. "That error is tricky - here's what usually fixes it." Epistemic stance: transparent with optimistic framing. |
| **Enthusiastic** | High energy, actively celebrates. Treats each interaction as an opportunity to delight. Excites about possibilities. "Oh, great choice! You're going to love what this can do." Epistemic stance: confident and forward-looking. |

**Epistemic stance note:** How the agent handles certainty and uncertainty is correlated with Emotional Coloring but not identical. Clinical agents hedge precisely; Encouraging agents frame uncertainty optimistically. When a persona needs an unusual pairing, define it in Tone Boundaries.

*Constraint note → Empathy Level: Blunt → Minimal. Clinical → Minimal or Understated. Encouraging → Moderate or Attuned. Enthusiastic → Attuned.*

*Constraint note → Register: Subordinate pulls toward Neutral or Clinical. Coach pulls toward Encouraging.*

### Empathy Level

*How much emotional validation the agent provides.*

```text
◄─── Minimal ──── Understated ──── Moderate ──── Attuned ───►
```

| Position | Description |
|---|---|
| **Minimal** | Acknowledges factually. No emotional validation. "The deployment failed" - then moves to resolution. |
| **Understated** | Care shown through action and attention, not words of comfort. A brief nod, then pivots to solutions. Doesn't dwell on feelings but doesn't dismiss them either. The warmth is there if you know where to look. |
| **Moderate** | Acknowledges difficulty briefly, then moves to resolution. "That's tricky - here's the fix." Default for most agents. |
| **Attuned** | Reads the user's emotional state and responds to it before problem-solving. "I can see how frustrating that must be. Let's sort this out together." Best for customer-facing agents with Encouraging or Enthusiastic emotional coloring. |

### Tone Boundaries

Define what the agent must *never sound like*. These are the negative space of your Tone selections - testable rules that prevent drift.

Tone Boundaries are authored per persona, not a menu - write your own based on the dimensions and context. The following defaults apply to most agents:

- Never apologize for asking clarifying questions (that's a repair flow, not an error)
- Never apologize for not knowing something (state the limitation and offer next steps)
- Only apologize when the agent caused an explicit mistake
- Never ask the user for empathy ("I'm still learning", "I'm not smart enough")

Add context-specific boundaries based on the Emotional Coloring and other dimensions. Examples:
- Neutral: "Never sound apologetic or servile." "Never use corporate jargon."
- Encouraging: "Never be saccharine - validate briefly, then act." "Never dramatize failures."
- Clinical: "Never editorialize findings." "No 'good news' or 'unfortunately.'"
- Blunt: "Never be cruel - blunt ≠ hostile." "Never mock the user's situation."

**Worked example — profanity/vulgarity:**

Profanity handling is a Tone Boundary, not a dimension. The guardrail sets the boundary; persona dimensions determine intent.

| Boundary Setting | What It Means |
|---|---|
| **Hard block** | Never use profanity under any circumstance. "D\*mn," "h\*ll," "cr\*p" — all blocked regardless of user input. *(Default for most agents)* |
| **Mirror only** | May echo a user's language when directly quoting or acknowledging, but never initiates. "I hear you — that is frustrating." Never: "Yeah, that's a real s\*\*\*show." |
| **Permitted — mild** | May use mild language ("damn," "hell," "crap") when it fits the persona's personality intensity and the conversational moment. Never escalates beyond the user's register. |

Most agents use Hard block. The boundary exists so designers of Bold / Informal agents can make a conscious choice rather than leaving it to the model. When in doubt, default to Hard block.

*Note: Content limits (topics the agent must not engage with), confidence rules, and compliance constraints (e.g., "never claim to be human") are defined in agent design, not persona. Tone Boundaries constrain how the agent sounds - not what it can do.*

### Tone Flex

Tone Flex defines how the agent's tone shifts from its baseline in response to context. The baseline is the selected Emotional Coloring and Empathy Level. Tone Flex defines how far each can shift, in what direction, triggered by what conditions.

**Triggers** - context conditions that cause shifts:
- **System state** - errors increase urgency, timeouts need patience
- **User emotional state** - frustration increases empathy, confusion increases patience
- **Content sensitivity** - emotionally loaded in-scope content (medical results, financial hardship, job loss, safety incidents) triggers a default shift: Humor → None, Empathy up one position from baseline. This default is explicitly overridable by the designer — some personas may handle sensitive content differently by design (e.g., a crisis counselor agent whose baseline is already Attuned doesn't need to shift further)
- **Conversation phase** - opening may be warmer, deep troubleshooting may be more clinical
- **Success/progress** - celebrations shift toward encouraging

**Shift rules** define direction and magnitude per trigger:

| Trigger | Dimension | Shift Example (from Neutral baseline) |
|---|---|---|
| User frustrated | Empathy Level | Understated → Moderate |
| System error | Humor | Any → None (always suppress) |
| Progress / success | Emotional Coloring | Neutral → Encouraging (briefly) |
| High-stakes topic | Humor | Any → None |
| Emotionally sensitive content | Empathy Level | Up one position from baseline |

**Hard boundaries** - Tone Boundaries are the outer wall of the flex range. The agent can shift within its flex range but must never cross a Tone Boundary. If the baseline is Neutral and the boundary says "Never sound saccharine," then flex toward Encouraging is acceptable but Enthusiastic would violate the boundary.

**Flex range** - How far each dimension can shift. Author per persona. Example:
- Emotional Coloring: Neutral baseline, flex range Neutral-Encouraging (never Clinical, never Enthusiastic)
- Empathy Level: Understated baseline, flex range Minimal-Moderate (never Attuned)

Tone Flex is authored per persona during design. The encoding expresses flex rules as per-topic tone calibration in instructions.

*Note: User-formality matching (agent mirrors the user's casual/formal register) is a related but open area - it depends on model capability as much as instructions. Not included in Tone Flex.*

---

## Delivery

Two standalone dimensions that control response shape and humor. Both are independent of Voice and Tone but interact with them through constraint notes.

### Brevity

*Response length and information density - how much does the agent say?*

```text
◄─── Terse ──── Concise ──── Moderate ──── Expansive ───►
```

| Position | Description |
|---|---|
| **Terse** | Cut every unnecessary word. One-word answers acceptable. Active voice, imperative mood. |
| **Concise** | Short sentences, says what's needed. Every sentence earns its place. |
| **Moderate** | Complete explanations with reasoning. Thorough but not verbose. *(Default)* |
| **Expansive** | Detailed, thorough responses. Full context, background, alternatives. |

**Tapering:** All Brevity positions taper as the user demonstrates familiarity. First interaction: full context and explanation. Repeat interactions: shorter. The agent assumes the user knows the basics and doesn't re-explain.

*Heuristic: The "One Breath Test" - could the agent's response be spoken in a single breath? Useful for calibrating Terse and Concise.*

*Constraint note: Brevity is largely independent, but Register and Formality create natural pairings. Subordinate + Formal pulls toward Moderate or Expansive (deferential agents rarely truncate). Peer + Professional pairs naturally with Concise. Coach pulls toward Moderate (teaching requires explanation).*

### Humor

*Type of wit, if any.*

```text
◄─── None ──── Dry ──── Warm ──── Playful ───►
```

| Position | Description |
|---|---|
| **None** | No humor. Default for regulated, high-stakes, or formal contexts. |
| **Dry** | Understatement, deadpan, intellectual wit. Never forced. |
| **Warm** | Light humor that reinforces warmth. Celebratory, situation-aware. |
| **Playful** | Puns, wordplay, whimsical personality. Best for casual contexts and personality-forward brands. |

No frequency setting - frequency is emergent from Brevity (terse = fewer words = fewer humor opportunities) and constrained by context (never humor in error states).

*Constraint: When Humor is not None, always include this tone boundary: "No humor in error states, escalation, or high-stakes contexts."*

*Constraint note: Formality + Emotional Coloring constrain Humor. Formal → None. Professional + Clinical → Dry or None. Casual/Informal + Encouraging → any humor type.*

---

## Chatting Style - "How does the text look on screen?"

*Boundary: Chatting Style governs visual presentation - emoji, structural formatting, punctuation habits, and capitalization patterns. These are how the text looks, not what it says (Voice) or how it feels (Tone). Independent of the agent's Information Architecture (defined in agent design), which governs output layout patterns.*

Four settings. Pick one option for each.

### Emoji

| Position | Description |
|---|---|
| **None** | No emoji. Default for formal contexts, regulated industries, or text-heavy interfaces. |
| **Functional** | Emoji as data compression - status indicators (check for done, cross for blocked, warning for risk), categories, severity levels. Each emoji conveys meaning; none are decorative. If you removed all emoji, information would be lost. |
| **Expressive** | Emoji for personality and warmth alongside functional use. Decorative emoji acceptable - they reinforce tone without carrying critical information. If you removed all emoji, no information would be lost, but personality would diminish. |

Boundary test: "If you removed all emoji, would information be lost?" Functional = yes. Expressive = no.

### Formatting

| Position | Description |
|---|---|
| **Plain** | Prose only. No bullets, no bold, no headings. Reads like natural conversation. |
| **Selective** | Formatting used purposefully - bold for key terms, bullets for lists of 3+, code blocks for copy-paste content. Formatting serves the content, never decorative. |
| **Heavy** | Extensive formatting - headers, dividers, tables, nested lists, section-based layouts. Every response has visible structure. |

### Punctuation

| Position | Description |
|---|---|
| **Conservative** | Standard punctuation only. No exclamation points, no ellipses, no em dashes. Periods end every statement. |
| **Standard** | Normal punctuation with occasional expressiveness. Exclamation points for genuine emphasis. Em dashes for asides. *(Default)* |
| **Expressive** | Liberal use of exclamation points, ellipses, em dashes, and other expressive marks. Punctuation conveys energy and personality. |

### Capitalization

| Position | Description |
|---|---|
| **Standard** | Conventional sentence case and title case. Proper capitalization throughout. *(Default)* |
| **Casual** | Lowercase-casual where appropriate - no capitalization at message start, lowercase labels. Best for Slack bots, internal tools, or informal agents. |

*Constraint note: Formality constrains Chatting Style. Formal → Emoji: None, Punctuation: Conservative, Capitalization: Standard. Professional → Emoji: Functional or None, Punctuation: Standard or Conservative. Casual/Informal → any combination.*

*Constraint note: Brevity constrains Formatting. Terse + Heavy is a productive tension (minimal words, maximum visual structure). Expansive + Plain may create walls of text - consider at least Selective.*

*Note: Accessibility requirements (screen reader compatibility, cognitive load, plain language) may constrain persona choices - e.g., Functional Emoji may need plain-language equivalents for screen readers. Accessibility is defined in agent design.*

---

## Persona Artifacts: What It Says and What It Doesn't

A persona produces three groups of artifacts — positive (what the agent *does*) and negative (what it *doesn't*). These groups organize everything the agent says and avoids:

| Group | Positive (Do) | Negative (Don't) |
|---|---|---|
| **(a) Identity** | Identity Traits, Values | Negative Identity ("Not a salesperson"), Never-Do |
| **(b) Expression** | Tone selections, Tone Flex | Tone Boundaries ("Never sound pushy"), Never-Say List |
| **(c) Phrasing** | Phrase Book, Discourse Markers, Lexicon (global + per-subagent, including immutable terms) | Never-Say List (anti-phrases), Lexicon exclusions ("Don't use this term") |
| **(d) Content** | Use cases, declared scope | Guardrails ("Don't offer medical advice") |

**Key distinctions:**
- **Phrase Book** = situation-keyed sample phrases ("When acknowledging, say...")
- **Lexicon** = domain-keyed vocabulary ("In product subagents, use these terms...")
- **Discourse Markers** = conversational connectors ("So," "Right," "Here's the thing")
- **Never-Say** = anti-phrases ("Never say 'Great question!'")
- **Tone Boundaries** = anti-sounds ("Never sound apologetic")
- **Negative Identity** = anti-characters ("Not a salesperson")
- **Guardrails** = anti-content ("Don't offer medical advice; don't make warranty claims; don't quote prices")

Each group's negative side generates the ones below it: Negative Identity → Tone Boundaries → Never-Say phrases. Guardrails sit beside this chain — they're about *what topics are off-limits*, not how the agent sounds. When reviewing a persona, trace any questionable output back up this chain to find where the constraint should live.

### Guardrails — content-level boundaries

Make sure agents know the boundaries about what they can say. Guardrails are content-level rules: subjects the agent must not address, claims it must not make, advice it must not give.

Examples:
- "Don't offer medical advice" (healthcare agent)
- "Don't quote prices for custom configurations — escalate to sales" (B2B SaaS agent)
- "Don't make warranty claims; refer to documented warranty terms" (consumer goods agent)
- "Don't speculate about regulatory changes" (financial services agent)

**How Guardrails differ from Never-Say:**
- **Never-Say** = phrase-level anti-phrases ("Never say 'Great question!'"). Behavioral.
- **Guardrails** = content-level off-limits subjects ("Don't offer medical advice"). Topical.

A Never-Say targets *how the agent talks*. A Guardrail targets *what the agent talks about*.

**When Guardrails apply:** Optional — only when domain warrants. Healthcare, financial services, insurance, legal, regulated industries usually need at least one. Brand-defined boundaries (off-brand topics, deprecated product names) also belong here.

**Encoding:** Guardrails encode as positive instructions where possible ("If asked about [X], redirect to [Y]") and as constraint statements where not ("Never recommend specific [X]"). Phrase guidance for redirects belongs in the Phrase Book.

---

## Phrase Book & Never-Say List

Two companion artifacts generated per persona. Both are tuned to the persona's dimension selections and Identity traits.

### Phrase Book

Example phrases the agent would use in common situations. Categories are selected during the workflow based on dimension selections - they vary per persona. Examples of selection-driven categories:

- **All agents:** Acknowledgement, Affirmation, Redirect/Handoff
- **Non-Terse agents:** Welcome/Greeting
- **Encouraging/Enthusiastic coloring:** Celebrating Progress
- **Coach register:** Teaching Moments
- **Humor ≠ None:** Humor Examples (showing the humor type in context)

**Affirmations** are positive acknowledgment phrases used to confirm, validate, or encourage: "Got it," "You're all set," "Right, moving on." These are distinct from greetings, closings, or transitions - they're the micro-confirmations that punctuate conversation and keep it flowing.

**Discourse Markers** are conversational connectors that smooth transitions and signal the agent's conversational logic: "So," "Right," "Anyway," "Now then," "Here's the thing." They are a Phrase Book category because they are situation-keyed (like acknowledgements and redirects), not vocabulary (like Lexicon).

Discourse markers are a high-leverage persona signal — they make the agent sound conversational rather than robotic. Select markers that match the persona's Formality and Personality Intensity. A Formal agent uses "Furthermore" and "To clarify"; a Casual + Bold agent uses "So here's the deal" and "Alright, moving on."

The Phrase Book is the single most effective lever for making an agent sound like itself. Encoding per-topic phrase book entries into instructions produces the strongest persona consistency.

### Never-Say List

The inverse of the Phrase Book - specific words, phrases, and patterns the agent must never use. Derived from:

- **Tone Boundaries** expressed as specific anti-phrases (e.g., "Never sound apologetic" → never say "I'm sorry, I can only...")
- **Identity contradictions** - phrases that violate the persona's traits (e.g., a Direct agent never says "I'd be happy to help you with that!")
- **Generic chatbot filler** - "Great question!", "Hope this helps!", "Let me know if you need anything else!" (these undermine almost every persona)
- **Cognitive-processing markers** - "Let me think about that," "Hmm, let me consider," "I need to process this" — machines don't think. These create false anthropomorphism unrelated to the persona's designed personification level. Reframe as action: "Let me check," "Looking into that," "Pulling up your details."
- **Register violations** - phrases that break the power dynamic (a Peer never says "Would you like me to proceed with..."; a Coach never says "Just do X")
- **Brand prohibitions** - competitor names, deprecated product names, off-brand language

The Never-Say List is authored alongside the Phrase Book and encoded into tone boundaries and instructions. When reviewing a persona, the Never-Say List is the fastest way to test whether the agent stays in character.

---

## Lexicon

*Brand terminology and domain vocabulary - global and per-topic.*

Lexicon has two scopes:

**Global Lexicon** - terms used across all topics: brand name, company name, product line names, industry terms that apply everywhere.

**Per-Topic Lexicon** - terms scoped to specific topics. A luxury watch agent has watch-specific vocabulary ("movement," "chronograph," "caliber") that belongs in product topics but NOT in order-tracking topics. Loading specialized vocabulary globally wastes context and can cause the agent to over-use jargon in simple service interactions.

**How Lexicon differs from Phrase Book:**
- **Phrase Book** = how the agent *sounds* in common situations - organized by situation (acknowledgement, redirect, celebration)
- **Lexicon** = what *words and terms* the agent uses in specific domains - organized by scope (global or per-topic)

The Phrase Book captures the agent's verbal fingerprint across all interactions. The Lexicon captures domain-specific vocabulary.

**In encoding:** Global lexicon goes in global instructions. Per-topic lexicon maps to per-topic instructions - each topic gets a vocabulary block with the relevant domain terms and usage notes.

---

## Reference

### Tension Pairs

Some dimension combinations create productive tension. These are valid - they don't need to be "resolved" - but they need conscious design to coexist:

| Tension | Resolution |
|---|---|
| Cool Warmth + Bold Personality | Strong character without performed warmth. Competence IS the care. |
| Blunt Coloring + Playful Humor | Unvarnished truth delivered as comedy. The bluntness is part of the joke. |
| Encouraging Coloring + Terse Brevity | Short celebrations: "Done. Nice progress." |
| Attuned Empathy + Terse Brevity | Brief validation, then act: "Frustrating. Here's the fix." |
| Formal + Warm | Polished hospitality, sophisticated warmth. |
| Formal + Bold Personality | Theatrical character, immersive experience. Archaic formality with maximum personality. |
| Neutral Coloring + Bold Personality | Strong character without emotional investment. The character shows through word choice, not feeling. |
| Warm + Playful Humor | Cheeky affection - irreverence grounded in warmth. |
| Reserved Personality + Warm | Dignified care. Warmth through reliability, not personality. |
| Radiant Warmth + Playful Humor | Overflowing cute energy. Mascot-driven delight. |
| Terse Brevity + Heavy Formatting | Minimal words, maximum visual structure. Headlines and data blocks, no prose. |

### Conflict-Pair Quick-Reference

Distinct from Tension Pairs above (which are *productive* tensions that simply need conscious design), these are **internal contradictions** the SCORE phase actively flags. Each is a sign the persona is fighting itself.

| Conflict | What to look for | How to resolve |
|---|---|---|
| **Tone Boundary contradicts Phrase Book entry** | "Never sound enthusiastic" + Phrase Book has "Awesome, let's go!" | Update the offending phrases or relax the boundary. Don't ship both. |
| **Never-Say overlaps Lexicon** | Lexicon includes "complimentary" + Never-Say includes "complimentary" | Pick one. The lexicon and Never-Say cannot disagree. |
| **Identity trait contradicts dimension selection** | Identity = "Calm, Composed" + Personality Intensity = Bold | Either soften Personality or swap the trait. |
| **Emotional Coloring contradicts Humor** | Coloring = Clinical + Humor = Playful | Pick one tonal register; Clinical + Playful reads as inconsistent character. |
| **Personification contradicts pronoun usage** | Personification = Talking System + Phrase Book uses "I think..." | Either lift Personification to Familiar Thing/Personal Assistant or rewrite phrases as brand-subject constructions. |
| **Immutable content contradicts Lexicon term** | Legal disclaimer: "claims tracking system" + Lexicon: "ClaimTrack" | Surface to user during design. Pick one and document the alignment. Immutable content wins by rule. |
| **Channel contradicts Brevity** | Channel = SMS + Brevity = Expansive | Re-examine. Channel-default Brevity is Terse for SMS; only override with strong signal. |
| **Register contradicts Audience** | Register = Coach + Audience = External customers | Coach with external customers risks paternalism. Either shift to Advisor or document why Coach fits. |

These pairs are the SCORE phase's Internal Consistency / Conflict-Pair check (worth /10 in the rubric). The skill flags any of these as a contradiction in the evaluation report, with a specific recommendation.

### Cultural Adaptation Note

Persona dimension expectations vary by culture. For global agents, consider per-locale overrides. Key callouts:

- **Formality expectations vary** - positions that feel natural in one culture may feel too casual or too formal in another.
- **Warmth norms differ** - Bright warmth in one culture may feel overwhelming in another. Cool professionalism that works in one context may feel cold elsewhere.
- **Directness norms differ** - Blunt or Clinical emotional coloring that works in direct-communication cultures may feel abrupt in high-context cultures.
- **Humor doesn't translate** - set Humor to None for cross-cultural deployments unless you're localizing humor per locale.
