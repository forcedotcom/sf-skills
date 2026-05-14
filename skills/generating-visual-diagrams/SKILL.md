---
name: generating-visual-diagrams
description: "AI-powered image generation for Salesforce visuals via Nano Banana Pro.
  Use this skill when the user needs rendered PNG/SVG output such as visual ERDs (Entity
  Relationship Diagrams), UI mockups, wireframes, or architecture illustrations.
  TRIGGER when: user asks for PNG/SVG output, UI mockups, wireframes, visual ERDs,
  or says \"generate image\" / \"create mockup\".
  DO NOT TRIGGER when: text-based Mermaid diagrams (use generating-mermaid-diagrams),
  or non-visual documentation tasks."
license: MIT
metadata:
  version: "1.0"
---

# generating-visual-diagrams: Salesforce Visual AI Skill

Use this skill when the user needs **rendered visuals**, not text diagrams: ERDs, UI mockups, architecture illustrations, slide-ready images, or image edits using Nano Banana Pro.

## Scope

**In scope:**
- PNG / SVG-style rendered image output
- Visual ERDs and architecture diagrams
- LWC or Experience Cloud mockups / wireframes
- Image edits on previously generated visuals

**Out of scope — delegate instead:**
- Mermaid or text-only diagrams → [generating-mermaid-diagrams](../generating-mermaid-diagrams/SKILL.md)
- Object / field metadata discovery for ERDs → [generating-custom-object](../generating-custom-object/SKILL.md) or [generating-custom-field](../generating-custom-field/SKILL.md)
- LWC implementation after the mockup is approved → [generating-lwc-components](../generating-lwc-components/SKILL.md)
- Apex review / implementation → [generating-apex](../generating-apex/SKILL.md)

---

## Hard Gate: Prerequisites First

Run the prerequisites check before using the skill:

```bash
scripts/check-prerequisites.sh
```

If prerequisites fail, stop and route the user to setup guidance in:
- [references/gemini-cli-setup.md](references/gemini-cli-setup.md)

---

## Required Inputs

Ask for or infer before generating:

| Input | Default if not provided |
|---|---|
| Image type | ERD |
| Subject scope and key entities / systems | Ask the user |
| Target quality | Draft (1K) |
| Preferred style | architect.salesforce.com aesthetic |
| Aspect ratio | Default (no override) |
| Quick mode or interview mode | Interview mode |

---

## Interview-First Workflow

Unless the user asks for **quick / simple / just generate**, ask clarifying questions first using the question bank in [references/interview-questions.md](references/interview-questions.md).

| Request type | Ask about |
|---|---|
| ERD / schema | objects, visual style, purpose, extras |
| UI mockup | component type, object/context, device/layout, style |
| architecture image | systems, boundaries, protocols, emphasis |
| image edit | what to keep, what to change, output quality |

**Quick mode defaults** (triggered by "quick", "simple", "just generate", "fast"):
- professional style, 1K draft, legend included, one image first then iterate

---

## Recommended Workflow

### 1. Run prerequisites check
Run `scripts/check-prerequisites.sh` and confirm all required tools pass before proceeding.

### 2. Gather inputs
- object list / metadata (delegate to `generating-custom-object` / `generating-custom-field` if needed)
- purpose: draft vs presentation vs documentation
- desired aesthetic — read [references/architect-aesthetic-guide.md](references/architect-aesthetic-guide.md) for ERDs
- aspect ratio / resolution

### 3. Run interview or use quick-mode defaults
Load [references/interview-questions.md](references/interview-questions.md) for the matching question set (ERD, LWC, architecture, code review).

### 4. Build a concrete prompt
Good prompts specify subject, composition, color treatment, labels/legends, and output quality goal.

### 5. Generate a fast draft at 1K
```bash
gemini --yolo "/generate 'Your prompt here'"
```
Open the result and review layout before spending on higher resolution.

### 6. Iterate using edits
```bash
gemini --yolo "/edit 'Specific change instruction'"
```
Use `/edit` for small adjustments — cheaper than regenerating. See [references/iteration-workflow.md](references/iteration-workflow.md).

### 7. Generate final at 2K/4K using the Python script
Run `scripts/generate_image.py` when layout is confirmed:
```bash
uv run scripts/generate_image.py -p "Refined prompt" -f "output.png" -r 4K
```

### 8. Error recovery
- If `gemini --yolo` returns no image: re-run once; if it fails again, fall back to the Python script path.
- If the Python script fails with `GEMINI_API_KEY not found`: verify the key is exported in your shell profile (`~/.zshrc` on macOS/zsh, `~/.bashrc` on Linux) and the terminal session is refreshed.
- If the extension is missing: run `gemini extensions install nanobanana` and re-run the prerequisites check.

---

## Default Style Guidance

For ERDs, default to the **architect.salesforce.com** aesthetic unless the user asks otherwise:
- dark border + light fill cards
- cloud-specific accent colors
- clean labels and relationship lines
- presentation-ready whitespace and hierarchy

Full style specification: [references/architect-aesthetic-guide.md](references/architect-aesthetic-guide.md)

---

## Common Patterns

| Pattern | Default approach |
|---|---|
| visual ERD | get metadata if available, then render a draft first |
| LWC mockup | load [assets/lwc/data-table.md](assets/lwc/data-table.md), [assets/lwc/record-form.md](assets/lwc/record-form.md), or [assets/lwc/dashboard-card.md](assets/lwc/dashboard-card.md) for the matching template |
| architecture illustration | load [assets/architecture/integration-flow.md](assets/architecture/integration-flow.md); emphasize systems and flows |
| image refinement | use `/edit` for small changes before regenerating |
| final production asset | switch to script-driven 2K/4K generation via `scripts/generate_image.py` |
| Apex / LWC code review | load [assets/review/apex-review.md](assets/review/apex-review.md) or [assets/review/lwc-review.md](assets/review/lwc-review.md) for the review prompt template |

---

## Output Expectations

Deliverables produced by this skill:

- **Draft image** (`<name>.png`) — 1K resolution rendered via `gemini --yolo "/generate ..."` for layout review
- **Final image** (`<name>.png`) — 2K or 4K resolution rendered via `scripts/generate_image.py` once composition is approved
- **Edit iteration** (`<name>.png`) — incremental refinement via `gemini --yolo "/edit ..."` without full regeneration

After delivering each image:
- Open the file in Preview or attach it in the session for multimodal review
- Ask the user whether to iterate on layout, labeling, or color before finalizing
- Only proceed to high-res output after draft composition is confirmed

---

## Rules / Constraints

| Rule | Rationale |
|---|---|
| Always run prerequisites check before any generation | Missing tools produce silent failures |
| Always draft at 1K before generating at 4K | Cost and time savings; composition changes at high res are wasteful |
| Use `/edit` for incremental changes, not full regeneration | Cheaper and faster for small adjustments |
| Never commit `GEMINI_API_KEY` to version control | Key is personal and tied to billing |
| Delegate text diagrams to `generating-mermaid-diagrams` | This skill owns rendered images only |

---

## Gotchas

| Issue | Resolution |
|---|---|
| Edit not applying correctly | Be specific: reference existing elements by name; one change at a time |
| 4K output looks different from 1K draft | Use exact same prompt text; minor variations are normal model behavior |
| `gemini --yolo` fails silently | Check that the Nano Banana extension is installed: `gemini extensions list` |
| Image dimensions wrong | Set `--aspect-ratio` explicitly in `scripts/generate_image.py` using `-a "16:9"` |
| RGBA image causes errors in Python script | Script auto-converts RGBA→RGB; ensure Pillow is installed via `uv` |

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Mermaid first draft or text diagram | [generating-mermaid-diagrams](../generating-mermaid-diagrams/SKILL.md) | faster structural diagramming |
| Object / field discovery for ERD | [generating-custom-object](../generating-custom-object/SKILL.md) / [generating-custom-field](../generating-custom-field/SKILL.md) | accurate schema grounding |
| Turn mockup into real LWC component | [generating-lwc-components](../generating-lwc-components/SKILL.md) | implementation after design |
| Apex review / implementation | [generating-apex](../generating-apex/SKILL.md) | code-quality follow-up |

---

## Reference File Index

| File | When to read |
|---|---|
| [references/gemini-cli-setup.md](references/gemini-cli-setup.md) | Prerequisites fail — Gemini CLI / Nano Banana setup guidance |
| [references/interview-questions.md](references/interview-questions.md) | Step 3 — load question set matching the request type |
| [references/iteration-workflow.md](references/iteration-workflow.md) | Step 6 — draft-to-final iteration patterns and cost tips |
| [references/architect-aesthetic-guide.md](references/architect-aesthetic-guide.md) | Step 4 — ERD color palettes, box styles, prompt templates |
| [references/examples-index.md](references/examples-index.md) | Step 4 — example prompts for ERD, LWC, architecture, code review |
| [assets/erd/core-objects.md](assets/erd/core-objects.md) | Step 4 — prompt template for core CRM objects (Account, Contact, Opportunity, Case) |
| [assets/erd/custom-objects.md](assets/erd/custom-objects.md) | Step 4 — prompt template for custom object ERDs |
| [assets/lwc/data-table.md](assets/lwc/data-table.md) | Step 4 — prompt template for lightning-datatable mockups |
| [assets/lwc/record-form.md](assets/lwc/record-form.md) | Step 4 — prompt template for lightning-record-form mockups |
| [assets/lwc/dashboard-card.md](assets/lwc/dashboard-card.md) | Step 4 — prompt template for dashboard card / metric tile mockups |
| [assets/architecture/integration-flow.md](assets/architecture/integration-flow.md) | Step 4 — prompt template for integration architecture diagrams |
| [assets/review/apex-review.md](assets/review/apex-review.md) | Step 4 — Gemini review prompt template for Apex code |
| [assets/review/lwc-review.md](assets/review/lwc-review.md) | Step 4 — Gemini review prompt template for LWC components |
| [scripts/check-prerequisites.sh](scripts/check-prerequisites.sh) | Step 1 — run to verify all required tools are installed |
| [scripts/generate_image.py](scripts/generate_image.py) | Step 7 — run for 2K/4K resolution output and image editing with resolution control |
