# Coverage gap analysis — mechanics (Workflow D)

The mechanics for **Workflow D**. The judgment (read-only, candidates-not-verdicts, depth-1,
disposition-to-admin) and the user-facing script live in `references/gap-analysis-guide.md`; this
file is the *how*. Everything here is **read-only** — Workflow D never writes metadata.

> **This entire file is INTERNAL — never narrated to the user.** The describe commands, the ~5-object
> bound, and every note about truncation / event-message limits / token cost / "scored 0" steer *how
> you work*; they are not status updates. Do the work quietly and present only the four user-facing
> blocks from `gap-analysis-guide.md`. See its *Internal vs. user-facing* section.

## Contents

- [1. Read current coverage](#1-read-current-coverage)
- [2. Enumerate one-hop candidate objects](#2-enumerate-one-hop-candidate-objects)
- [3. Flag candidate fields (the rubric)](#3-flag-candidate-fields-the-rubric)
- [4. Diff against the current tree](#4-diff-against-the-current-tree)
- [5. The depth gate](#5-the-depth-gate)
- [6. The transparency report shape](#6-the-transparency-report-shape)

## 1. Read current coverage

Load the policy's existing roots and paths so gaps are reported *relative to* them. On a plain `sf`
surface the tree is Metadata API:

```bash
sf project retrieve start --metadata DsarPolicy:<PolicyDeveloperName> --target-org <alias>
```

On an MCP / SOR surface, read it with the `DsarPolicyManager` `list`/`describe` operation instead.
Record the set of `{object → [fields]}` already covered — that set is subtracted in step 4.

## 2. Enumerate one-hop candidate objects

For **each root** object in the policy, describe it once and read two things from the result:

```bash
# A full object describe is ~100KB+ of JSON. Do NOT read it raw into the turn — the accumulated
# describe payloads overflow the agent's event-message size limit and the run TRUNCATES before it
# writes the report. Always project to just the fields you reason over, so only a few KB enters context:
sf sobject describe --sobject <RootObject> --target-org <alias> --json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["result"]; \
print(json.dumps({"fields":[{"name":f["name"],"type":f["type"],"label":f["label"]} for f in d["fields"]], \
"children":[c["childSObject"] for c in d["childRelationships"]][:40]}, indent=1))'
```

- **`fields[]`** — the root's own fields (candidate personal-data fields live here).
- **one relationship hop out** — the objects directly related to the root:
  - `childRelationships[]` → child objects (e.g. Contact → Cases, Contact → ContactPointEmails);
  - reference/lookup `fields[]` (`type: "reference"`) → parent objects the root points to.

**Never read a raw `--json` describe into the turn.** Project every describe (root and one-hop)
through the field-name/type/label filter above. This is the single most important guard against the
`Truncated event message received` failure — the describe JSON, not the number of objects, is what
overruns the stream.

Describe each one-hop object once to read *its* `fields[]`. **Stop there.** Do not describe the
objects *those* relate to — that is level 2, gated behind explicit confirmation (step 5). The
one-hop rule is what keeps the scan bounded and cheap; it is also the tree-cap discipline (skill
call #3) applied to discovery.

**Hard bound — describe at most ~5 one-hop objects, then stop and report.** A standard root such as
`Contact` exposes dozens of `childRelationships[]`; describing all of them floods the context and
the run can truncate before it ever writes the report (a failed audit, not a thorough one). Pick the
**most privacy-relevant** related objects (contact points, cases/activities carrying supplied
contact data, the parent account) — describe those few, and **name in the report the related objects
you did *not* describe** so the omission is transparent, offering them under the depth gate (step 5).
The root's own describe plus a couple of one-hop objects is enough for a correct, complete audit;
**describing more than ~5 objects adds no value and risks truncation.**

**Policy/type unreadable (the accepted environment path) → stop at the root describe.** If
`DsarPolicy` can't be read (Metadata/Tooling/Connect all 404 — the feature isn't enabled on this
org), do **not** fan out to one-hop objects at all: a single **projected** `Contact` describe is
enough to demonstrate the depth-1 candidate reasoning. Flag the candidate fields on the root, state
that the policy/type couldn't be read and that you therefore reasoned from the root alone, name the
one-hop objects you *would* scan next (without describing them), and write the report. Casting wider
here only adds truncation risk for no benefit — the gap-analysis *method* is what matters, not breadth.

**Write incrementally; never let discovery starve the report.** The report file is the deliverable —
an audit that describes many objects but never writes is a failed, incomplete audit — strictly worse
than one that scans fewer objects and writes. Create `${outputDir}` and draft the report early, fill it in
as you describe, and once you have the root + a couple of one-hop objects **write it** — then offer
more depth, rather than gathering everything first and writing last.

## 3. Flag candidate fields (the rubric)

On the root and each one-hop object, mark fields that **may** hold the subject's personal data.
Every flag carries a **reason**; use the strongest available signal and name it:

| Signal (strongest first) | How to read it | Reason string |
|--------------------------|----------------|---------------|
| Field compliance metadata | describe field's `complianceGroup` / `securityClassification` (when populated) | `marked <value> in field metadata` |
| Field type | `type` = `email` / `phone` / `address`; `date` used as birthdate | `<type> field, common personal data` |
| Name / label semantics | tokens: Name, First/Last, Email, Phone, Mobile, SSN, Passport, DOB/Birth, Address/Street/City/Postal, IP, DeviceId, TaxId | `name/label suggests <category>` |
| Duplicate of a covered value | same value already mapped on another object | `duplicate of a covered field; admin picks canonical source` |

**These are candidates, not classifications.** A field the rubric misses can still be personal
data; a flagged field may not be. The admin confirms (skill call #2). When `complianceGroup` /
`securityClassification` come back empty on the org, say so — the scan then rests on type and name
semantics only, which is weaker; state that limitation in the report.

## 4. Diff against the current tree

Candidate = flagged in step 3 **and not** in the covered set from step 1. Group the result by
object. Also list, per scanned object, the fields **already** covered — the report shows covered vs
newly-surfaced side by side so the admin sees what the policy already handles.

## 5. The depth gate

After presenting the one-hop findings, offer to go deeper — but only expand on **explicit
confirmation**, and warn first:

> Going beyond one level produces a large volume of output and uses considerably more tokens.

If the admin confirms, repeat steps 2–4 for exactly the depth they approved (usually one more hop),
then stop and re-offer. Never recurse unprompted; never "just keep going down the tree."

## 6. The transparency report shape

The report must make the method and its limits visible (skill call: transparency). Include:

- **Objects scanned** — the roots and the one-hop objects, by name (so the admin sees the actual
  surface examined, not just conclusions).
- **Candidate fields** — a table of `object | field | reason | already in policy?`.
- **Covered vs surfaced** — what the policy already maps, alongside the new candidates.
- **Search limit** — an explicit line that only one level was scanned, and the offer to go deeper.
- **Disposition prompt** — which candidates to add; adding routes to Workflow A (authored INACTIVE,
  no auto-reactivation). Report even when nothing new was found ("no uncovered candidates at one
  level").
