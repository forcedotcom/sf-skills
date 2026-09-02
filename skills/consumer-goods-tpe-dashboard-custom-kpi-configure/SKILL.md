---
name: consumer-goods-tpe-dashboard-custom-kpi-configure
description: "Customize the Trade Promotion Effectiveness (TPE) Analytics dashboards' generic KPI slots (Promotion Measure 1-3, Tactic Measure 1-2) with customer-chosen KPI measure codes and display names, without touching the shipped base model. Use when a customer/admin wants to \"customize TPE dashboards\", \"change the KPIs on the Promotion/Tactic Analysis dashboard\", or \"swap in our own measure codes on the TPE dashboard\"."
metadata:
  version: "1.0"
  domains: ["Consumer Goods"]
  relatedSkills:
    - "consumer-goods-tpe-dashboard-configure"
  cliTools:
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Customize TPE Dashboard KPIs

Headlessly clones the base TPE Analytics semantic-model parameters, visualizations, and dashboards
under a customer-chosen suffix, so a customer's own KPI measure codes appear on the Promotion/Tactic
Analysis dashboards without ever mutating the shipped base model. Driven entirely by `sf` CLI +
REST against an already-authenticated org. Requires `consumer-goods-tpe-dashboard-configure` to
have already installed the TPE Analytics app and the Extended TPM Analytics SDM — this skill never
installs those, only customizes on top of them.

Persona: a **Salesforce TPM System Admin** customizing TPE dashboards for their org's own KPIs.

There is no native "clone" endpoint for any of the three artifact types this skill touches
(semantic-model parameters, visualizations, dashboards) — every clone is the same three-step
pattern: **GET** the base artifact, **deep-copy** its JSON and apply overrides, **POST** the copy as
a new artifact. Base-model artifacts are never mutated in place.

## The 5 KPI slots — two artifacts per slot, not one

The shipped Extended TPM Analytics SDM exposes 5 generic **List-type parameters** that the standard
dashboards bind to: Promotion Measure 1-3 (`Promotion_Measure_{1,2,3}_prm` / `_value`) and Tactic
Measure 1-2 (`Tactic_Measure_{1,2}_prm` / `_clc`). **Never assume Tactic mirrors Promotion's
`_value` naming** — resolve both slots' measurement apiNames from the live model per slot, never by
pattern. See `references/payload-shapes.md` for the confirmed apiNames and JSON shapes.

Each slot is **two SDM artifacts**: the **parameter** (`*_prm`, a `List` type with `allowedValues`
menu entries and a `defaultValue`) and the **calculated measurement** (what visualizations actually
query; its `expression` links back to the parameter by apiName). **Customizing a slot means cloning
both** — the parameter gets the customer's KPI as a new/selected `allowedValues` entry, and the
measurement's `expression` is rewritten to reference the cloned parameter's new apiName.

This skill always produces clones of **all 5 slots (10 artifacts)**, whether or not a given slot has
a requested override — an unmentioned slot is still cloned as an exact copy of the base artifacts
(only apiName/label suffixed).

Two override modes per slot (see `references/procedure.md` for exact `--overrides` shapes):

- **APPEND mode** (default): upserts one `{measureCode, displayName}` entry into the base menu by
  measure code — same code relabels in place, new code appends.
- **REPLACE mode**: a full `allowedValues` array supplied by the customer becomes the entire menu.

Either way this skill assumes the underlying measure data is already populated by prior
`setup-rtr-datacloud-export`/data-kit setup — it does not create that underlying data itself.

## Inputs to collect first

Ask before starting. Do not guess.

1. **TPM System Admin username** — verify connectivity via
   `node ./scripts/sf-rest.js org-status --target-org <username>` (never `sf org display --json`
   directly — that leaks a live `accessToken`). Non-`Connected` ⇒ stop, ask the user to log in.
2. **Dry-run?** — offer by default.
3. **Suffix** — distinguishes cloned metadata from the base model (e.g. `Cust`). Suggest `Cust` as a
   default. Applied to every new artifact's API name/label — never reuse a base-model API name.
4. **Per-measure overrides** — walk the customer through the 5 measures via `AskUserQuestion`,
   **batched by dashboard** (Promotion Measure 1-3 in one call, Tactic Measure 1-2 in a second call —
   never all 5 in one call, the tool caps at 4 questions per call), never using the internal term
   "slot" toward the user. **Never ask a separate plain free-text follow-up question to collect the
   list** — a plain-text message doesn't block the next tool call, so if you fire another
   `AskUserQuestion` for the next measure before the customer's reply lands, their answer races
   ahead and lands on the wrong question. Instead, collect the full list **inside the same blocking
   question**: every `AskUserQuestion` question automatically gets a "Type Something" free-text
   option appended after your listed options — no need to add your own placeholder option for it,
   and never rely on a bare canned option label (e.g. "Replace with custom list") to actually carry
   the list, since selecting it only returns that label text, not the customer's data. Word the
   question and its second option's description to point the customer at "Type Something"
   explicitly, e.g. option 2 = "Replace with custom list", description: "Select **Type Something**
   (last option, below) and type comma-separated `{measureCode}: {displayName}` pairs, plus which
   one should be default." **A menu can have more than one entry — always collect the full array,
   never just one pair** (a single-pair answer is still an array of length 1). This collected array
   maps directly to that slot's REPLACE-mode override (`{"allowedValues":[...], "defaultValue":
   "<first displayName unless the customer says otherwise>"}`) — see `references/procedure.md`'s
   override-mode shapes. Confirm the resolved list per measure back to the user before Phase 0.
5. **Which dashboards to produce** — Promotion Analysis, Tactic Analysis, or both. Default to both
   if any measure on either has an override; otherwise ask explicitly.

## How it works — phase list

1. **Namespace detection** — resolve `NS` via `sf package installed list` for consistency with
   sibling skills, but never apply it to any `/services/data/...` path (those are never namespaced).
2. **Phase 0 — Preflight & discovery**: verify connectivity, pin API version `v67.0`, resolve the
   installed app + asset ids (model, both dashboards, visualizations) by walking the app's asset
   list — never hardcode an id. Block with a pointer to `consumer-goods-tpe-dashboard-configure` if
   prerequisites are missing. Full detail: `references/procedure.md`.
3. **Phase 1 — Resolve the 5-slot plan**: deep-copy each base parameter/measurement with overrides
   applied, print the plan, get explicit user confirmation before any writes.
4. **Phases 2-4 — Clone parameters, measurements, visualizations, dashboards**: run
   `scripts/clone-tpe-dashboards.js` (preferred over hand-rolling individual REST calls) — see
   `references/procedure.md` for the full CLI usage, override-mode payload shapes, and every
   real-write gotcha the script encodes (label uniqueness, dataSource `.type` stripping rules,
   cloning every KPI-bound visualization not just one "designated" viz, cosmetic label-text
   replacement, upsert-by-measure-code).
5. **Phase 5 — Verify**: GET every created artifact back and confirm parameters, measurements,
   visualizations, and dashboards all correctly reference the new suffixed clones, never a base
   apiName. Full detail: `references/procedure.md`.

## Key rules (see `references/procedure.md` for the complete list)

- Never mutate a base-model artifact — every write is a new POST of a suffixed copy.
- Never create anything without explicit user go-ahead on the Phase 1 plan.
- Always produce all 5 slots' worth of clones, even with zero overrides.
- Never leave a cloned measurement's `expression` referencing a base parameter apiName.
- Never hardcode an artifact id, api-name, or namespace across orgs.
- Never assume only one visualization per dashboard needs cloning — clone every widget whose viz
  references a slot measurement.

## Reference map

| Topic | File |
|---|---|
| Full phase-by-phase procedure, script CLI usage, all real-write gotchas, complete Rules list | `references/procedure.md` |
| Confirmed live JSON shapes for parameters, calculated measurements, visualizations, dashboards, and POST body shapes for all 4 create endpoints | `references/payload-shapes.md` |
| Org REST helper (strips `accessToken`; `org-status` subcommand) | `scripts/sf-rest.js` |
| Deterministic driver for Phases 2-4 | `scripts/clone-tpe-dashboards.js` |

## Report

At the end of a run, give the user a structured status per phase (0-5): pass / blocked / pending,
with the specific blocking reason where applicable, and the final list of created artifacts (slot →
new parameter, base viz → new viz, base dashboard → new dashboard). Call out anything skipped due
to dry-run or a declined confirmation.

**When invoked via delegation** (the calling skill used the `Skill` tool to reach this file, rather
than the user directly — e.g. `consumer-goods-tpe-dashboard-configure`'s customization step): this
report is an intermediate result. Return it to the calling skill and let it continue with its own
report — do not present this as the final answer to the user unless this skill was invoked
standalone.
