---
name: experience-lwc-base-components-integrate
description: "Pick the right Lightning Base Component (`lightning-*`) for a given UI task, retrieve its full API (props, methods, events, slots) from the bundled per-component reference, and wire it into an LWC (LWC `.html`, `.js`, and `.css` files) without breaking SLDS. Use this skill when users say \"I need a Lightning modal / datatable / combobox / record form\", ask which `lightning-*` component fits a use case, want a shortlist of LBC candidates, are about to hand-roll a UI that a base component already provides, or are editing an LWC bundle's `.html` / `.js` / `.css` and need to select or wire a base component. Also triggers on \"Lightning base component\", \"LBC\", \"lightning-combobox\", \"lightning-datatable\", \"use `lightning-` tag\". DO NOT TRIGGER for applying SLDS design tokens, blueprints, or styling guidance in general — that is `design-systems-slds-apply`; this skill only selects and wires `lightning-*` base components."
metadata:
  version: "1.0"
  relatedSkills:
    - design-systems-slds-apply
---
<!-- adk-managed-skill -->

# Using Lightning Base Components

Lightning Base Components (LBC) are the `lightning-*` web components shipped
by Salesforce. This skill routes an agent through the right decision sequence
so the final component choice is **as specific as possible** and backed by
real API docs — not a hand-rolled reimplementation of something that already
exists.

## When to Use This Skill

- User describes a UI need ("searchable dropdown", "record edit form",
  "modal with footer") and asks which `lightning-*` component fits.
- User is about to build a primitive (button group, combobox, toast) and
  should be using LBC instead.
- User asks you to review LWC markup for LBC-related issues — specifically
  overriding SLDS classes or restyling LBC internals.
- User needs the authoritative props/events/slots for a specific
  `lightning-*` tag.

## Prerequisites

- Knowledge of which LBC namespace your org uses (`lightning` is the default
  public namespace; some platforms expose `lightning-community` or others —
  the user's meta files will clarify).
- The skill ships authoritative API docs for every Lightning Base Component
  in [references/lightning-components.md](references/lightning-components.md).
  Each component is a `# Component API Structure` block; grep for
  `**Name:** <camelCaseName>` (e.g. `**Name:** datatable`) to jump to its
  Properties / Methods / Events / Slots. Read this rather than relying on
  cached knowledge — LBC evolves and the reference is the source of truth.


## Workflow

### Step 1 — Read the **entire** component index first

Open [lightning-component-index.md](references/lightning-component-index.md)
and scan **all** entries before making any selection. This is non-negotiable:
LBC's value comes from picking the most specialized component, and skipping
the scan leads to reinventing compound widgets out of primitives.

As you scan, compile a **candidate list** — every component whose description
touches any aspect of the use case. Do not filter or rank yet.

### Step 2 — Narrow to the most specific fit per feature

Once the scan is complete:

- For each feature in the use case, select the **most specific** component
  that covers it. Prefer a specialized compound (`lightning-record-form`,
  `lightning-tabset`, `lightning-datatable`) over a generic primitive
  (`lightning-input`, `lightning-button`) when the specialized one covers
  the scenario end-to-end.
- Avoid duplication: if `lightning-record-form` already renders fields for a
  record, do not pair it with `lightning-input-field` unless you're
  explicitly overriding behavior.

### Step 3 — Share the shortlist and confirm

Present the final shortlist to the developer with a one-line rationale per
component. Wait for explicit confirmation before pulling full API docs. This
prevents the agent from burning context on components the developer has
already mentally ruled out.

### Step 4 — Retrieve full API docs

Once confirmed, use the bundled helper to pull the exact API blocks — this
avoids ad-hoc grepping across a large reference:

```bash
scripts/extract-component-docs.sh <camelCaseName> [<camelCaseName>...]
```

Convert `lightning-<foo>` tags to camelCase (no `lightning-` prefix):

- `lightning-datatable` → `datatable`
- `lightning-record-edit-form` → `recordEditForm`
- `lightning-button-icon` → `buttonIcon`

Each returned block has the same shape: **Basic Information** (tag, namespace,
type), **Properties** (name, type, default, description), **Methods**,
**Events**, **Slots**, and (where applicable) usage notes. This skill is about
**picking** the components; the bundled reference is about **wiring** them.

### Step 5 — Produce integration guidance

Using the per-component reference, walk the developer through:

- The exact `<lightning-...>` tag and required attributes.
- Which events to bind (`onchange`, `oncommit`, `onsuccess`, …) and what
  the event payload contains.
- Any slots to fill (headers, footers, custom content).
- Known constraints from the component docs (e.g. `lightning-record-form`
  requires `object-api-name` and `record-id` for edit/view modes).

### Step 6 — Respect LBC styling rules

Do not override SLDS classes on LBC internals. See
[lbc-expert-guidance.md](references/lbc-expert-guidance.md) for specifics.
Common issues:

- Targeting `.slds-button` or `.slds-input` in the host component's CSS to
  restyle an LBC — LBC ships inside a shadow root, so these selectors
  either leak into sibling components or get stripped entirely. Use the
  component's documented styling hooks (`--sds-c-button-*`, etc.) instead.
- Wrapping an LBC just to mutate its internal markup. You can't — the
  markup is hidden behind the shadow root. If the component doesn't expose
  the slot/prop you need, that's a platform-level gap, not a restyling job.


## Examples

### Example — "I need a multi-select combobox with typeahead"

1. Scan the component index end-to-end.
2. Candidate list includes: `lightning-combobox`, `lightning-dual-listbox`,
   `lightning-record-picker`.
3. Shortlist: `lightning-dual-listbox` (the documented multi-select base
   component). Rule out `lightning-combobox` — its documented API is
   single-select; it has no `type="multi"` and no multi-select mode.
   Flag that `lightning-record-picker` only fits if the values are record IDs.
4. Developer confirms `lightning-dual-listbox`.
5. Run `scripts/extract-component-docs.sh dualListbox`.
6. Return the `options`, `value`, `onchange` payload, and required label
   props from the block's Properties / Events sections.

### Example — "I'm going to write my own modal"

1. Scan finds `lightning-modal`, `lightning-modal-body`,
   `lightning-modal-footer`, `lightning-modal-header`.
2. Shortlist is the 4 modal components.
3. Confirm.
4. Run `scripts/extract-component-docs.sh modal modalHeader modalBody modalFooter`
   → full modal API (how to extend `LightningModal`, the static `.open()`
   pattern, slotting the header/body/footer).
5. Steer the developer away from rolling their own dialog.


## Verification Checklist

- [ ] The full component index was scanned before any selection (no
      keyword-search shortcutting).
- [ ] Candidate list included every component that touches the use case.
- [ ] Final shortlist selects the **most specific** component per feature.
- [ ] Developer confirmed the shortlist before the bundled component
      reference was opened.
- [ ] Integration guidance cites props / events / slots from the real API
      docs (not inferred).
- [ ] No suggestions to restyle LBC by overriding SLDS classes.


## Troubleshooting

- **Grep for `**Name:** <name>` returns no match** — name is wrong, or the
  reference uses a different camelCase. Double-check against the component
  index (`lightning-record-form` → `recordForm`,
  `lightning-record-view-form` → `recordViewForm`,
  `lightning-button-icon` → `buttonIcon`).
- **Proposed component doesn't have the prop you expected** — trust the
  real API doc over memory. LBC evolves; cached knowledge lies.
- **Developer resists the shortlist** — don't skip Step 4. Still retrieve
  the docs for the developer's preferred choice so they see the actual
  trade-offs.
- **Developer wants to restyle LBC internals** — redirect to styling hooks
  (see the LBC Expert reference). Refusing shadow DOM penetration is the
  correct answer.
