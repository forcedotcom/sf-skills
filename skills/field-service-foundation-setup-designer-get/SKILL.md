---
name: field-service-foundation-setup-designer-get
description: "Creates Field Service foundation data — Work Types, Skills, Service Territories, and Operating Hours. Accepts existing data in any format or designs from scratch, and confirms the design with the user. Use this skill when a user wants to create, design, or set up Field Service foundation data."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Field Service Foundation Setup Designer

**Design or refine Field Service foundation data — Work Types, Skills, Service Territories, Operating Hours, and other associated Field Service objects — through structured interviews. Starting from scratch or from existing recommendations.**

This skill runs a design conversation — it does not call Salesforce APIs directly. It collects the design through a structured conversation, whether starting from scratch or working from existing data, and confirms the final design with the user. This skill covers two design workflows in sequence (or independently):

1. **Work Types & Skills** — 6-question interview
2. **Service Territories & Operating Hours** — 3-question interview

## Entry point

- **Starting from scratch** → run the full interview phases below to build the design.
- **Have existing data** — this includes scraped/read source output, JSON or text provided by the user, or any other external source brought into context. Show a plain-English summary of the proposed configuration as a starting reference, then immediately ask: "Would you like to go through a guided design interview to refine this, or proceed directly with this configuration?" Wait for the answer before doing anything else.
- **Ready to create** → show a plain-English summary of the records to be created (not raw JSON or skill names), ask for explicit confirmation, then proceed only after the user confirms.

Never expose internal skill names, SOR IDs, or tool references to the user.

## When to use

- Starting Field Service setup from scratch — no existing Work Types or Territories yet
- When initial recommendations need adjustment for either work types or territories (or both)
- To explore different granularity levels (Work Types) or territory models (Territories)
- When customer provides additional context about their business or coverage areas
- During discovery sessions to design or iterate on the foundation data model

## Design principles

1. **Structured questions with consistent intent**
   - Questions based on Work Type Implementation Guide and Service Territory Design Guide
   - Adapt examples to customer's business context
   - Intent stays consistent, wording adapts intelligently

2. **Brief answers must work**
   - "No", "Yes", "No we don't" are complete answers
   - Progress to next question immediately
   - No explanations required

3. **Smart question adaptation**
   - Check if topic already covered
   - If covered: brief confirmatory question
   - If not covered + business context: customize examples
   - If not covered + no context: exact structured question

4. **Question format** (three or four parts):
   ```markdown
   **Recommendation:** [Only include when context is sufficient. Lead with the best-fit option given what's known, then briefly note alternatives with the condition under which they'd apply instead — not a flat menu of equal choices, but a ranked steer. Omit entirely when confidence is low.]

   **Question:** [The actual question — or a lighter "does this fit?" when a Recommendation is present]

   **Why I'm asking:** [1-2 sentences: why this matters]

   **Impact:** [1-2 sentences: how their answer affects the design]
   ```

## How it works

### Pre-phase: Source ingestion (if provided)

If no source has been provided, creatively ask the user whether they have a website or document that describes their business or Field Service operation — framing it as something that would help build a more accurate and tailored starting recommendation rather than a generic one.

If the user provides a URL, fetch it. Extract Field Service-relevant signals: industry, service types, geographic coverage, team and skill structure. Use these to generate an initial recommendation covering Work Types, Skills, Service Territories, and Operating Hours — which feeds into the refinement interview rather than starting from nothing.

### Phase 1: Work Types & Skills

1. **Accept input**: Takes existing data in any format (JSON, CSV, free-form text), or starts fresh if nothing is provided.
2. **Interview**: Cover these topics — service line granularity, equipment size/type variations, brand/model specificity, service tiers and site types, parts tracking, duration accuracy.
3. **Output**: Designed Work Types and Skills as JSON + change log.

### Phase 2: Service Territories & Operating Hours

1. **Accept input**: Same as Phase 1.
2. **Interview**: Cover these topics — territory structure (geographic/functional/hybrid), geographic boundaries (if applicable), functional team geographic constraints (if applicable).
3. **Output**: Designed Service Territories and Operating Hours as JSON + change log.


## Inputs

- **Source material** (optional): A URL the agent will fetch to extract business context and generate an initial recommendation. Takes precedence over manually pasted data when both are provided.
- **Existing data** (optional): Work Types/Skills and/or Service Territories/Operating Hours in any format — JSON, CSV, free-form text, or pasted output from a prior session. If nothing is provided, recommendations are built entirely through the interview.
- **Business context** (optional): Additional context to tailor interview questions to the customer's industry or service model.

## Outputs

- Designed or refined Work Types with metadata
- Skills inventory organized by category
- Designed or refined Service Territories with structure
- Operating Hours organized by timezone
- Combined JSON export (Salesforce API-ready, for deployment via `sfs-sobject-create`)
- Markdown summary with change log
- Before/after comparison (when refining existing data)

## Granularity Levels Reference (Work Types)

From Work Type Implementation Guide:

| Level | When to Use | Example |
|-------|-------------|---------|
| **High-Level** | Simple service models, quick setup | "Installation", "Repair", "Maintenance" |
| **Mid-Level** | Equipment-specific service | "HVAC Installation", "HVAC Repair" |
| **Detailed** | Brand-specific service needs | "HVAC Installation (Carrier)", "HVAC Installation (Trane)" |
| **Hyper-Specific** | SLA/site variations | "HVAC Repair (Carrier) - Hospital" |

**Best practice:** Start with simplest model possible, increase granularity only when necessary.

## Territory Models Reference (Service Territories)

From Service Territory Design Guide:

| Model | When to Use | Example |
|-------|-------------|---------|
| **Geographic** | Location-based coverage, reduce travel time | "Northern California", "Southwest Region" |
| **Functional** | Specialized service types, skill-based assignment | "Fire Safety Team", "Commercial HVAC Team" |
| **Hybrid** | Combined benefits, specialized teams with regional boundaries | "Northern CA - Fire Safety", "Southwest - Commercial HVAC" |

**Best practice:** Start with simplest model possible, increase complexity only when necessary.

---

## Output format

Generate the output JSON payload from interview answers using this mapping:

- `WorkType` → `SkillRequirement` (junction → `Skill`)
- `WorkType` → `ProductRequired` (junction → `Product2`)
- `OperatingHours` → `TimeSlot` (parent-child)
- `ServiceTerritory` → `OperatingHours` (lookup)
