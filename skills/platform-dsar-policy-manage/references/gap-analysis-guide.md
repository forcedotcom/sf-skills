# Gap-analysis guide prompt — coverage audit for a DsarPolicy

> This is the guidance the agent follows when an admin asks *"what personal data are we missing
> from this policy?"*. It is the script for **Workflow D — Coverage gap analysis**: a **read-only**
> audit that surfaces **candidate** objects/fields for the admin to disposition — it never
> classifies data authoritatively, never adds a path on its own, and never activates a policy.

## Contents

- [What this is and is not](#what-this-is-and-is-not)
- [The deterministic steps](#the-deterministic-steps)
- [How fields are flagged as candidate personal data (and why)](#how-fields-are-flagged-as-candidate-personal-data-and-why)
- [User-facing output (canonical)](#user-facing-output-canonical--use-verbatim-structure)
- [Guardrails](#guardrails)

## What this is and is not

The gap analysis answers **"which objects/fields that may hold this subject's personal data are
not yet covered by the policy?"** It is deliberately **structured and deterministic** — the same
request produces the same steps and the same transparency, not an open-ended graph walk that
varies run to run.

- **It is:** a read-only audit that (1) states its own method up front, (2) shows exactly which
  objects it looked at, (3) flags **candidate** personal-data fields **with a reason for each**,
  (4) states its search limit, and (5) hands the admin a disposition choice.
- **It is not:** an authoritative classification of what counts as personal data (that decision is
  the **admin's** — load-bearing call #2), an automatic edit to the policy, or an activation. The
  agent proposes; the admin disposes.

## Internal vs. user-facing (read before running)

This is the Workflow-D-specific application of **SKILL.md load-bearing call #8 (work silently — never
narrate the skill's internals)**. Workflow D has two layers; keep them apart in what you *say*:

- **Internal — never narrated to the user:** the step numbers and step names below, the `sf`/describe
  mechanics in `gap-scan.md`, and every author-facing note about truncation, event-message limits,
  token cost, or how the audit is "scored." These steer *how you work*; they are not status updates.
  Do not say "running Workflow D, step 2", "describing the root to avoid truncation", or "this keeps
  the run from scoring 0." Just do the work and present the result.
- **User-facing — the ONLY things the user sees:** the four blocks in
  [User-facing output (canonical — use verbatim structure)](#user-facing-output-canonical--use-verbatim-structure)
  — method preamble, findings, depth offer, disposition. Nothing else.

If the environment blocks the scan (feature off / policy unreadable), say so in one plain sentence
inside the findings block — not by narrating the mechanics that failed.

## The deterministic steps

Run these in order. Do not skip the method preamble (step 0) — transparency is the point. **These
step numbers/names are internal scaffolding — do the work, don't announce the scaffolding** (see
[Internal vs. user-facing](#internal-vs-user-facing-read-before-running)).

0. **Open with the plain-language method line.** Before scanning, tell the admin in **plain words**
   how you'll answer and its limits (see the script). This is the one allowed "here's how I'll do
   this" sentence — it must **not** name the workflow ("Workflow D", "coverage-gap audit"), announce
   that you're about to read the guide/mechanics, or cite a rule/tool (call #8). State the approach,
   then start.
1. **Read current coverage.** Load the policy's existing roots and paths (read-only). These are
   already-covered objects — the audit reports gaps *relative to* this set.
2. **Enumerate candidate objects — one level only.** For each policy **root** object, describe it
   and list its **immediately related** objects (exactly **one relationship hop** away). This
   depth-1 default is a hard limit that keeps performance and token cost bounded — do **not**
   recurse further without explicit confirmation (step 5).
3. **Flag candidate fields with reasoning.** On the root and each one-hop object, mark the fields
   that **may** hold the subject's personal data, and record **why** for each (see the flagging
   rubric). Candidates only — never "this *is* PII."
4. **Report transparently.** Present: the objects you scanned, the candidate fields with the
   per-field reason, the fields already covered vs newly surfaced, and an explicit statement of the
   **one-level search limit**.
5. **Offer to go deeper — only on explicit confirmation.** Ask whether the admin wants to look
   beyond one level. Warn plainly that going deeper produces **a large volume of output and burns
   significantly more tokens**. Expand only if they say yes, and only by the depth they approve.
6. **Disposition, don't mutate.** Ask which candidates the admin wants to add. Nothing is added
   automatically. Adding routes to **Workflow A (Configure)**, which authors the change INACTIVE
   and — per the activation rule — **stops for explicit user confirmation before reactivating**.

## How fields are flagged as candidate personal data (and why)

The reason string is mandatory — every flagged field says *why*. Use these signals, strongest
first, and name the signal you used:

- **Compliance metadata on the field** (e.g. a field's data-sensitivity / compliance-group /
  PII classification from the describe). Reason: *"marked <classification> in field metadata."*
  This is the strongest signal and the least subjective.
- **Field type semantics** — `email`, `phone`, `address` compound components, `date` used for
  birthdate. Reason: *"<type> field, commonly personal contact/identity data."*
- **Name/label semantics** — tokens like Name, First/Last, Email, Phone, Mobile, SSN, Passport,
  DOB/Birth, Address/Street/City/Postal, IP, DeviceId, TaxId. Reason: *"name/label suggests
  <category>."*
- **Already-covered elsewhere** — the same value appears on an already-mapped object. Reason:
  *"duplicate of a field already in the policy; flagged for the admin to decide canonical source."*

State the rubric's limits honestly: this is a **heuristic**, not a legal determination. A field
the rubric misses can still be personal data, and a flagged field may not be — the admin confirms.
When compliance metadata is absent on the org, say so (the audit leans on name/type semantics only).

## User-facing output (canonical — use verbatim structure)

**This is the output contract for Workflow D — the four blocks below are the only thing the user
sees, and their structure is fixed.** Use these four blocks, in this order, with this formatting
(the blockquote framing and the `Object | Field | Why I flagged it | In policy?` table columns);
do not improvise a different layout run to run. The *prose wording* may be adapted to the specific
policy/org, but the **blocks, their order, and the table columns are not optional** — stable
structure is what keeps the presentation clean instead of randomly formatted. Do not surface any of
the internal step numbers, mechanics, or scoring/truncation notes here (see
[Internal vs. user-facing](#internal-vs-user-facing-read-before-running)).

**Method preamble (step 0):**

> Here's how I can answer this. I'll start from your policy's root objects, look **one level out**
> at the objects directly related to them, and flag the fields that *might* contain this person's
> data — and I'll tell you **why** I flagged each one. I won't decide what counts as personal data
> for you, and I won't change the policy: you'll pick what to add. I stop at one level by default;
> I can go deeper if you ask, but that gets large and token-heavy, so I'll check with you first.

**Findings (step 4):**

> **Objects I looked at:** `<root objects>` and their immediately-related objects: `<one-hop list>`.
> **Already covered by the policy:** `<covered fields>`.
> **Candidate fields that may hold personal data (not yet covered):**
> | Object | Field | Why I flagged it | In policy? |
> |--------|-------|------------------|------------|
> | Contact | Email | email field, common contact PII | no |
> | Contact | Birthdate | date used as date of birth (name/type) | no |
> **Search limit:** I only looked **one level** out from your roots. Deeper relationships are not
> in this list.

**Depth gate (step 5):**

> Want me to look **beyond one level**? Heads up: it produces a lot more output and uses
> considerably more tokens. If yes, tell me how deep (e.g. one more level) and I'll continue.

**Disposition (step 6):**

> Which of these do you want added to the policy? I'll author the change and leave it **inactive**
> for your review — I won't reactivate or publish until you confirm.

## Guardrails

- **Candidates, never verdicts.** Every flag is a suggestion pending the admin's disposition.
- **Depth 1 by default.** Never recurse past one level without explicit, warned confirmation.
- **Read-only.** The audit changes nothing; adding is a separate, admin-driven Workflow A step.
- **No auto-activation.** Any resulting edit stops for explicit user confirmation before
  reactivation/publish (the activation rule).
- **Transparency is mandatory.** Always report what was scanned, why each field was flagged, and
  the search limit — even when the list is short or empty.
- **Transparency ≠ narrating internals.** Show *what* you scanned and *why* each field is flagged
  (the findings block). Do **not** narrate *how* — step numbers, describe mechanics, truncation /
  token / scoring notes stay internal. Transparency is about the audit's coverage and reasoning, not
  the skill's plumbing.
