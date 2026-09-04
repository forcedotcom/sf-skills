---
name: field-service-data-capture-form-designer-configure
description: "Design a Field Service Mobile Data Capture Flow from either a natural-language description OR a PDF/image of an existing paper form. Extracts field labels, types, required-state, and section structure into an intermediate JSON spec, confirms the plan with the user, then hands off to fs-data-capture-form-deployer for compile + deploy. Handles both input modes in one skill — prose ('build a Field Service form for asset inspection', 'make a DataCaptureFlow that asks the technician to…', 'create an inventory transfer form') and visual sources ('convert this PDF to a Data Capture Flow', 'make a Field Service form from this image', 'turn this paper form into a DataCaptureFlow'). Detects the input mode automatically from a .pdf/.png/.jpg/.jpeg path, else extracts from the prose. Do NOT use this skill to patch an already-deployed flow — that's fs-data-capture-form-editor."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Design a Data Capture Form (from prose or from an image / PDF)

This skill produces an intermediate JSON spec from the user's input — a
natural-language description **or** a PDF/image of an existing form — gets the
user's approval on the plan, and then invokes `fs-data-capture-form-deployer` to
compile and deploy.

## When this skill fires

The user asks for a Data Capture Flow / Field Service Mobile form. The input
arrives in one of two modes:

- **Prose mode** — the user describes the form in plain text with no attached file. Examples:
  - "Create a data capture form for asset inspection that asks for asset id, condition rating, photos, and remarks."
  - "Build a Field Service form for inventory transfer with parts repeater, source location, and destination dropdown."
  - "Generate a DataCaptureFlow that captures three things: site name, contact info, and a notes field."
- **Image / PDF mode** — the user supplies a path to a `.pdf`, `.png`, `.jpg`, or `.jpeg` file. Examples:
  - "Convert /tmp/inspection.pdf to a Data Capture Flow"
  - "Build a Field Service form from this image: ~/Downloads/site-visit.png"
  - "Turn this paper form into a DataCaptureFlow" (with attached image)

Detect the mode from the input: **if the user supplied a `.pdf` / `.png` / `.jpg` / `.jpeg` path, use image/PDF mode; otherwise use prose mode.** Everything after extraction (steps 2-6) is identical for both.

## Workflow

### 1. Read the source (mode-dependent)

**Prose mode — read the description carefully; don't fabricate fields.**
Extract only the fields the user actually mentioned. Don't invent extra fields based on what "usually goes on" an inspection form. If the user says "asks for asset id, condition rating, photos, and remarks", emit four fields, not eight.

If the user's description is too vague to produce a usable form ("build a form that captures stuff about a service appointment"), ask one or two targeted questions before extracting — what fields they want, whether there's a parent record, what should happen on submit. Don't guess.

Then apply the prose-evidence rules in [reference/extraction-from-prompt.md](reference/extraction-from-prompt.md).

**Image / PDF mode — read the file.**
Use the `Read` tool on the path the user gave you. PDFs and images are natively supported. If the PDF is more than 10 pages, ask the user which pages contain the form (the `Read` tool requires a `pages` parameter for large PDFs).

Then apply the control-evidence rules in [reference/extraction-from-image.md](reference/extraction-from-image.md).

### 2. Extract the intermediate JSON

Apply every rule in the mode-appropriate extraction reference (from step 1). The output schema is defined by the **input contract of the build skill**:
- [field-types.md](../fs-data-capture-form-deployer/reference/field-types.md) — field type → component mapping, required Flow boilerplate, choice/repeater shapes, visibility rules.
- [post-screen-automation.md](../fs-data-capture-form-deployer/reference/post-screen-automation.md) — schema for the optional `postScreen` block.

Write the JSON to `/tmp/data-capture-spec.json`.

### 3. Determine the desired outcome

A data capture form is a means, not an end. Before asking for approval, decide what should happen in Salesforce when the user submits the form:

- If the user explicitly says what to create/update ("create a ProductTransfer for each part"), OR the source/filename strongly implies an outcome (Inventory Transfer → ProductTransfer; Asset Inspection → WorkOrderLineItem) — emit a `postScreen` block with the named (or best-guess) object and field API names. When it's a best guess, list every `valueRef` / `field` in the confirmation step so the user can correct names.
- If the outcome is ambiguous AND the user gave no hint — surface the question in the confirmation step ("What should happen when this form is submitted?") with concrete options drawn from the form's domain.
- A screens-only flow with no `postScreen` is valid, but you must say so explicitly in the confirmation step.

See the mode-appropriate extraction reference for the full outcome-elicitation rules.

### 4. Confirm with the user (mandatory gate)

Show the user what you plan to build before deploying. Use `AskUserQuestion` to gate the handoff to Build.

In the question body or surrounding text, plainly state:

1. **The desired outcome.** What the flow does after the last screen — e.g. "Submitting the form will create a ProductTransfer per row in the Parts repeater" or "This flow only captures data — admin will wire up automation in Flow Builder." If a `postScreen` block was generated, list every Salesforce object name and every `field` API name it references. Object/field API names are the most common source of post-deploy errors.
2. The `formTitle` and the proposed `<FlowApiName>` (PascalCase, no spaces).
3. The number of screens and total fields (count repeater children too).
4. Any visibility rules generated and the choice values they key off of.
5. **Every field type, especially specialized ones, and the evidence it's based on.** For each `Signature`, `UploadFile`, `UploadImage`, `Images`, `Matrix`, `Address`, `Lookup`, `FileView`, or `Repeater` in the spec, name the field and the evidence — in prose mode the prose evidence ("user said 'parts repeater'", "user described a sign-here pad"); in image mode the visual evidence ("`damagePhoto` → UploadImage because the source has a camera-icon button"). These deploy as **real functional components** (`dcSignature`, `dcUpImage`, etc.) — so emitting them when the user only meant a text field (prose) or when you can only point to the field's *label* (image) is the most common extraction bug. If the matching control vocabulary / visual control isn't present, downgrade to `ShortText`/`LongText`/`Numeric` and call it out.
6. **Lookup objects and FileView filenames.** For every `Lookup`, list the `lookupObject` (Salesforce object API name) and `lookupSearchFields` you chose. For every `FileView`, list the `fileName`. These names are common sources of post-deploy errors — surface them so the user can correct.
7. Any fields that fell back to a labeled `dcTextInput` placeholder (only happens for `Lookup` with no `lookupObject` and `FileView` with no `fileName`).

Offer the user clear options:
- **Approve and deploy** — proceed to step 5.
- **Edit the spec first** — let them edit `/tmp/data-capture-spec.json` directly, then re-run from step 4.
- **Cancel** — stop without deploying.

Do not proceed to step 5 without explicit approval.

### 5. Hand off to Build

Once approved, hand the approved spec to `fs-data-capture-form-deployer`. Pick a `<FlowApiName>` matching `^[A-Z][A-Za-z0-9_]*$` (default: PascalCase of `formTitle`), then follow that skill's workflow — it runs entirely over REST through the Codey runtime, with **no `sf` CLI, no scripts, and no `.flow-meta.xml`**:

1. **Verify org auth** — [fs-data-capture-form-deployer/SKILL.md](../fs-data-capture-form-deployer/SKILL.md) §1 (a cheap `SELECT Id FROM Organization LIMIT 1` REST probe; the runtime resolves the connected org — this family does not manage aliases).
2. **Build the Flow Metadata JSON inline** from the approved spec — deployer §3 + [reference/flow-metadata-json.md](../fs-data-capture-form-deployer/reference/flow-metadata-json.md). The agent assembles the `Metadata` object directly; there is no XML compile step.
3. **Deploy** with a single `POST /services/data/vXX.0/tooling/sobjects/Flow` carrying `{ "FullName": "<FlowApiName>", "Metadata": { ... } }` — deployer §4.

After deploy, follow the reporting + error-handling steps in [fs-data-capture-form-deployer/SKILL.md](../fs-data-capture-form-deployer/SKILL.md) §5.

### 6. Offer to attach the form to a parent record

After a successful deploy, the flow exists but is invisible from the Forms tab on any Service Appointment / Work Order. Ask the user whether they want it attached to a specific parent (the canonical "pending form" pattern). If yes, follow the attach steps in [fs-data-capture-form-deployer/SKILL.md](../fs-data-capture-form-deployer/SKILL.md) §6 — a single `POST /services/data/vXX.0/sobjects/DynamicDataCapture` (no scripts). For SA-context testing, attach to the SA's parent Work Order, not the SA itself — FSL Mobile reads Forms from the parent Work Order.

## Out of scope

- Patching an already-deployed flow → `fs-data-capture-form-editor`.
- Hand-authoring patterns the converter doesn't generate (visual polish HTML, real `dcSignature`/`dcUpImage`, master-detail child records, supporting CustomObjects) → `fs-data-capture-reference` library skill.

## Files in this skill

- `reference/extraction-from-prompt.md` — prose-evidence rules for picking field types from user descriptions, screen grouping, visibility rules, outcome-elicitation, validation checklist. Used in **prose mode**.
- `reference/extraction-from-image.md` — control-evidence rules for picking field types from rendered widgets, repeater extraction rules, screen grouping, visibility rules, outcome-elicitation, validation checklist. Used in **image / PDF mode**.
