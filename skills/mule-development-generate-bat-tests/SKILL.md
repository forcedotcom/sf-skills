---
name: generate-bat-tests
description: Workflow required before generating, writing, or updating BAT (Blackbox API Testing) tests for a Mule app. Call use_skill as your FIRST action — before reading or writing any .dwl file — whenever the user asks to create, generate, add, write, refresh, extend, or fix BAT tests, a BAT suite, BDD API tests, black-box API tests, or Anypoint API Functional Monitoring tests for a deployed Mule HTTP API. Do not read the app source, open the existing suite, or author any .dwl yourself and attempt the task in one turn — even a targeted single-test change like 'add a 401 test' or 'fix the orders happy-path test' requires loading this skill first. Covers generating a suite from app source (OpenAPI + Mule XML), extending an existing hand-written BAT baseline, and running the suite against the live endpoint. Not for MUnit (build-time, in-process, XML) — use the Mule developer workflow for that. When you call this skill, it must be the only tool call in that response.
license: Apache-2.0
compatibility: Requires the BAT CLI (Anypoint API Functional Monitoring, installed at $HOME/.bat/bat), Java 17+, jq, and a deployed/running Mule HTTP API reachable at the configured URL. Reads the app's OpenAPI contract and Mule flow XML as generation input.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
  cli: bat
  theme: professional
allowed-tools: Bash Read Write Edit AskUserQuestion
---

# Generate BAT Tests

Generate a runnable **BAT (Blackbox API Testing) BDD** suite — DataWeave `.dwl`
files plus a `bat.yaml` manifest — from a Mule app's source, organized by
quality dimensions, and validated by running it against the live endpoint.

## When to Use This Skill

**Use this skill when users request:**

- "Generate BAT tests for this API / app"
- "Write a BAT suite for the orders service"
- "Add black-box API tests / BDD tests against the deployed endpoint"
- "Create Anypoint API Functional Monitoring tests"
- "Extend the existing BAT tests to cover the new error cases"
- "Refresh / fix the BAT suite after the API changed"

**Trigger keywords:** BAT, BDD, `.dwl` test, black-box test, API functional
monitoring, functional API test, blackbox · generate / write / add / extend /
refresh tests · against the deployed / running / live endpoint.

**Do NOT use this skill for MUnit.** MUnit is build-time, in-process, XML, and
XSD-validated — a different tool with a different workflow. BAT runs against a
**deployed HTTP endpoint**, is DataWeave, and has **no XSD**: the only gate on
correctness is "it parses AND it passes against the running app". That gate is
this skill's Phase 2.

---

## What BAT is (read once before Phase 1)

BAT = **Blackbox API Testing**, MuleSoft's API Functional Monitoring framework.
A BAT test is a DataWeave `.dwl` BDD file that issues real HTTP requests against
a deployed API and asserts on the responses. It does **not** import or see the
Mule flows — it is out-of-process and black-box. A suite is a directory of
`tests/*.dwl` files, a `bat.yaml` manifest, a `config/` with environment
settings, and a `run-bat.sh` runner. The suite is executed with the `bat` CLI:
`bat --config=local`.

Because there is no XSD and no build-time validator, two things matter more than
in MUnit generation:

1. **Authoring discipline** — the DSL has exact, easy-to-miss rules (see
   `references/bat-authoring-rules.md`). The Phase-2 static validator catches the
   mechanical ones before you spend a round-trip against the endpoint.
2. **The run is the gate** — a suite is not "done" until `./run-bat.sh` has been
   executed against the live app and every test passes (or each failure is
   explained in the report). This replaces MUnit's XSD/compile gate.

---

## Bundled scripts

This skill ships scripts under `scripts/`. Invoke them with the `Bash` tool —
do not inline their contents. `<skill-dir>` is the absolute path you were given
in the "skill is now active" message (the directory containing this `SKILL.md`).
Use it for every invocation; do not construct relative `../scripts/...` paths.

| Script | Purpose | Output |
| --- | --- | --- |
| `scripts/validate_prerequisites.sh` | Step 1 — validate toolchain (jq, BAT CLI at `$HOME/.bat/bat`, Java 17+). Validation-ONLY. | `tmp/bat-gen-env.json` (`ok`, `errors[]`, `bat_cli`, `java_version`) |
| `scripts/extract_endpoints.sh <app-dir>` | Step 2 — grep the Mule source for `<http:listener>` paths and `<raise-error>` types; list API spec files. Anchors the inventory. | `tmp/bat-gen/source-digest.json` + stdout |
| `scripts/scaffold_suite.sh <suite-dir> [--url U] [--token T] [--force]` | Step 8 — create `config/{default,local}.dwl`, `run-bat.sh` (chmod +x, JDK-17 `JAVA_OPTS`), and `tests/`. Idempotent. | suite skeleton on disk |
| `scripts/validate_bat_suite.sh <suite-dir> [--allowlist F]` | Step 9 — static DSL checks (imports, `describe(...)`, no `mustNotBe`, no hardcoded URL/token, Number status codes, `bat.yaml` shape, files↔disk parity, optional path allowlist). Exits 1 on violations. | stderr diagnostics |

---

## Workflow shape (two phases)

This workflow has two phases separated by a hard user-approval gate.

- **Phase 1: Test Design (Steps 1–6).** Validate the toolchain, read the app's
  OpenAPI contract and Mule XML (and, if present, an existing BAT baseline),
  build a **test inventory** tagged by quality dimension, present an Inventory
  Summary, and wait for the user to approve. Phase 1 writes **nothing** into the
  suite directory — only the workspace-relative `tmp/bat-gen/` digest and the
  inventory JSON.
- **Phase 2: Generate & Run (Steps 7–11).** Scaffold the suite, write the
  `.dwl` files + `bat.yaml`, run the static validator, run the suite against the
  live endpoint, and declare completion only after a clean run.

Phase 2 MUST NOT start until Step 6's approval gate has been passed explicitly.
Generating `.dwl` files before the inventory is approved is the highest-impact
failure mode this structure prevents — a wrong dimension split or a fabricated
endpoint becomes N wrong test files.

## Workflow-wide discipline (read before Phase 1)

- **Black-box only.** Tests hit the deployed HTTP API. They never import Mule
  flows, read the Object Store directly, or assert on internal state. If the
  user wants in-process flow assertions, that is MUnit, not this skill.
- **Endpoints come ONLY from the source.** Every path + verb in a generated test
  must exist in the app's Mule `<http:listener>` configuration and OpenAPI
  contract. Never invent an endpoint from the API's name or from training-time
  intuition. Step 2's `extract_endpoints.sh` digest is the anchor; the Phase-2
  validator enforces it via `--allowlist`.
- **Config interpolation, never hardcoding.** Every test uses `$(config.url)`
  and `config.token`. A literal `http://localhost...` or `"Bearer ..."` in a
  `.dwl` file is a defect — the validator rejects it.
- **The run is the gate.** "Done" means `./run-bat.sh` ran against the live app
  and every test passed, OR every failure is documented in the report with
  reasoning. Never declare completion off an unrun suite.
- **Don't fix the app to make a test pass.** If a test reveals what looks like a
  real bug in the app, do NOT edit the app. Flag it in the report as a discovered
  discrepancy and make the assertion match what the code actually does, noting
  the discrepancy for human review.

---

# Phase 1: Test Design

## Step 1: Validate Prerequisites

Run the prerequisite validator. It only validates; it writes findings to
`tmp/bat-gen-env.json`.

```bash
bash <skill-dir>/scripts/validate_prerequisites.sh
```

If it exits non-zero, STOP and surface the `errors` array to the user
(most commonly: BAT CLI not installed, or Java < 17). Do not attempt to author
a suite you cannot run — the run is the gate, and an unrunnable suite cannot
pass it.

---

## Step 2: Read the Source and Build the Endpoint Anchor

Identify the Mule app directory under test, then run the digest helper to anchor
the inventory in the real source:

```bash
bash <skill-dir>/scripts/extract_endpoints.sh <app-dir>
```

This writes `tmp/bat-gen/source-digest.json` and echoes it: the
`<http:listener>` paths (the endpoint allowlist), the `<raise-error>` types
(the error-type coverage list), and the API spec file paths.

Then **read the actual source** — the digest anchors you but does not replace
reading:

- The **OpenAPI/RAML contract** (paths from `api_specs[]`) — request/response
  shapes, required fields, enums, status codes.
- The **Mule flow XML** (`src/main/mule/*.xml`) — verbs per listener path,
  `<choice>/<when>` branches, `raise-error` mappings to status codes, the state
  machine if there is one, and how `Authorization` is enforced.
- `mule-artifact.json` for the runtime context.

**[BLOCKER] Do not generate tests from the OpenAPI contract alone.** The
contract states intent; the flow XML states behavior. Where they disagree, the
flow XML is what the deployed endpoint actually does, and BAT tests the deployed
endpoint. Note any contract↔code disagreements for the report.

---

## Step 3: Read the Existing BAT Baseline (if one exists)

If the app already has a hand-written BAT suite (commonly under `<app>/bat/` or
a directory the user names), read it. It is **ground truth for how this team
writes BAT tests** — absorb its idioms so the generated suite is consistent:

- file/test naming style (kebab-case files; double-quoted `describe(...)`
  headers; single-quoted `it must '...'` scenarios)
- the state-seeding pattern (`var context = HashMap()`, `execute [ context.set(...) ]`,
  `$(context.get(...))` in the next URL)
- config layout and `bat.yaml` shape
- which matchers the team uses

When a baseline exists, the generated suite MUST be a **strict superset** of the
behaviors the baseline covers — no regressions. Re-emit baseline tests (so the
suite stands alone), mark them `existing` in the inventory, and do not change
their semantics (you may rename for consistency). If no baseline exists, skip
this step.

---

## Step 4: Draft the Test Inventory

Using the source (Step 2) and any baseline (Step 3), draft the inventory: one
entry per proposed test, tagged with a primary quality dimension. Use the
taxonomy in `references/quality-dimensions.md`.

Write the inventory to `tmp/bat-gen/test-inventory.json` — a JSON array of:

```json
{
  "name": "post-orders-happy-path",
  "file": "tests/post-orders-happy-path.dwl",
  "dimension": "Accuracy",
  "subdimension": "data-integrity",
  "endpoint": "POST /orders",
  "rationale": "one sentence — why this test is worth running",
  "expected_status": 201,
  "expected_error_code": null,
  "exercises_raise_error_type": null,
  "covers": ["Coverage:endpoint", "Accuracy:data-integrity"],
  "provenance": "new",
  "stateful": false
}
```

- `provenance` is `existing` | `new` | `refined` (when a baseline test is
  improved — add a one-line `refined_reason`). When there is no baseline,
  everything is `new`.
- `stateful: true` marks tests that need a seed call + `context` (multi-step).
- Cover **every** endpoint × method and **every** `raise-error` type from the
  Step-2 digest. Aim for ~12–20 tests for a small API; don't bloat with
  redundant variants.

Names are kebab-case and match the `.dwl` basename.

---

## Step 5: Derive the Endpoint Allowlist

Write the normalized endpoint allowlist the Phase-2 validator will check
generated paths against — one path per line, with id segments collapsed to `{}`:

```
/orders
/orders/{}
/orders/{}/confirm
/orders/{}/ship
/orders/{}/cancel
```

Save it to `tmp/bat-gen/endpoint-allowlist.txt`. Derive it from the Step-2
`listener_paths[]` (plus base path), NOT from the inventory — it is the
independent check on the inventory.

---

## Step 6: Present the Inventory Summary and Get Approval

**[BLOCKER] Present ONLY after Steps 1–5 are complete.** Every inventory entry
must have a dimension, an endpoint that exists in the allowlist, and an expected
status. If any is missing or an endpoint is not in the allowlist, fix it before
presenting — do not paper over with "TBD".

Present a concise summary:

```
**BAT Test Inventory Summary**

**App under test:** <app dir> · runtime URL <config.url>
**Source read:** <OpenAPI spec path>, <flow XML path(s)>
**Baseline:** <none | N existing tests at <path>>

**Coverage:**
- Endpoints: <M of N listener paths × methods covered>
- raise-error types: <list each type from the digest and the test that triggers it; flag any not covered>
- State transitions: <list, if the app has a state machine>

**Inventory (<count> tests):**
- By dimension: Accuracy <n> · Robustness <n> · Security <n>
- By provenance: existing <n> · new <n> · refined <n>   (omit if no baseline)

**Items flagged for human review:**
- <contract↔code disagreements, suspicious validation, dead branches — or "none">
```

Then ask for explicit approval:

> Review the inventory above. Proceed to generate and run the suite (Phase 2)?
> - Yes, generate and run the suite.
> - No, I want to change the inventory.
> - No, cancel.

**[BLOCKER] WAIT for explicit "Yes" before Step 7.** On "change the inventory",
ask what to change (coverage, dimensions, specific tests) and loop back. On
"cancel", stop politely.

---

# Phase 2: Generate & Run

## Step 7: (Re)confirm the Runtime URL and Token

The suite runs against a live endpoint. Confirm the URL and bearer token before
scaffolding:

- If the user gave a URL/token, use them.
- If the app is the local fixture, the defaults are
  `http://localhost:8082/api/v1` and `Bearer test-token`.
- If neither is known, ask via `AskUserQuestion` — a suite pointed at the wrong
  URL fails every test for the wrong reason.

---

## Step 8: Scaffold the Suite

Create the suite skeleton (config, runner, tests dir):

```bash
bash <skill-dir>/scripts/scaffold_suite.sh <suite-dir> --url "<config.url>" --token "<bearer>"
```

This writes `config/default.dwl`, `config/local.dwl` (url/token/env),
`run-bat.sh` (chmod +x, with the JDK-17 `--add-opens` `JAVA_OPTS`), and an empty
`tests/`. It will not overwrite an existing `config/local.dwl` unless you pass
`--force` — respect a url/token the user already edited.

Pick `<suite-dir>` per the user's project convention (e.g.
`<app>/bat-generated/` or a path the user names). Do not write into the
hand-written baseline directory.

---

## Step 9: Write the `.dwl` Files and `bat.yaml`, then Validate

For each entry in the inventory whose provenance is not `dropped`, write
`tests/<name>.dwl` following **every** rule in
`references/bat-authoring-rules.md`. The canonical shapes are in
`references/examples/` — read them and match the style:

- `single-call-happy-path.dwl` — one request, multiple asserts.
- `auth-401.dwl` — negative/error-code test.
- `multi-step-stateful.dwl` — seed call + `context` + dependent call (for
  `stateful: true` inventory entries).
- `json-body-and-headers.dwl` — asserting a parsed JSON body field and a
  `Content-Type` header that carries a charset (see rules 7b/7c).

Then write `bat.yaml` (schema in the authoring rules / `references/examples/bat.yaml`):
`suite.name`, a `files:` entry per `.dwl`, and `reporters:` (HTML + JSON). **No
top-level `config:` key.**

As the **first tool call after writing**, run the static validator against the
endpoint allowlist from Step 5:

```bash
bash <skill-dir>/scripts/validate_bat_suite.sh <suite-dir> --allowlist tmp/bat-gen/endpoint-allowlist.txt
```

If it exits non-zero, fix the reported files and re-run the validator. Only
proceed to Step 10 after it exits 0. Keep the validator and the run in separate
responses.

---

## Step 10: Run the Suite Against the Live Endpoint

This is the gate. As the **only** tool call in this response:

```bash
cd <suite-dir> && ./run-bat.sh
```

Read the output:

- **All tests pass** → proceed to Step 11.
- **A test fails** → diagnose the cause:
  - **BAT-DSL/syntax error** → fix the `.dwl`, re-run the validator (Step 9),
    then re-run the suite.
  - **Assertion you guessed wrong** (the app's real behavior differs from what
    the test asserted) → correct the assertion to match the deployed behavior,
    and note the correction in the report.
  - **What looks like a real app bug** → do NOT fix the app. Flag it in the
    report as a discovered discrepancy, set the assertion to match the actual
    behavior, and mark it for human review.
  - **Connection refused / every test 401/404** → the runtime is down or the
    URL/token is wrong. Fix Step 7's config (re-run `scaffold_suite.sh --force`
    or edit `config/local.dwl`) and re-run. This is not a test defect.

Iterate until all tests pass OR every remaining failure is documented. Do not
ship a suite with silent failures. Run only `./run-bat.sh` in this response — no
other tool calls alongside it.

---

## Step 11: Write the Report and Declare Completion

**Pre-condition:** the immediately preceding response ran `./run-bat.sh` and you
have its pass/fail output. If not, go back to Step 10.

Write a short `REPORT.md` next to the suite:

- Test count by dimension and by provenance.
- Coverage table: each `raise-error` type and whether a test covers it; each
  endpoint × method.
- Pass rate (X/Y) from the run.
- Discrepancies discovered (contract↔code, suspected app bugs) — for human review.
- Any tests still failing and why (only if you could not resolve them and chose
  to flag rather than silently drop).

Then declare completion in a tight message — the user can see the files and the
run log. Include exactly:

1. The suite directory path and test count.
2. One sentence on what the suite covers.
3. The pass rate from the live run.
4. Anything flagged for human review (or "none").

Do not pad with feature lists or next-steps.

---

## Quick Reference

```bash
# Step 1: validate toolchain (jq, BAT CLI, Java 17+) — validation-only
bash <skill-dir>/scripts/validate_prerequisites.sh

# Step 2: anchor the inventory in the real source
bash <skill-dir>/scripts/extract_endpoints.sh <app-dir>   # → tmp/bat-gen/source-digest.json

# Step 8: scaffold the runnable suite skeleton
bash <skill-dir>/scripts/scaffold_suite.sh <suite-dir> --url "<config.url>" --token "<bearer>"

# Step 9: static DSL validation before spending a live run
bash <skill-dir>/scripts/validate_bat_suite.sh <suite-dir> --allowlist tmp/bat-gen/endpoint-allowlist.txt

# Step 10: the gate — run against the deployed endpoint
cd <suite-dir> && ./run-bat.sh
```

## References

- `references/bat-authoring-rules.md` — the BAT DSL rules (R1–R10), `bat.yaml`
  schema, config files, and `run-bat.sh`. Read before writing any `.dwl`.
- `references/quality-dimensions.md` — the Accuracy / Robustness / Security /
  Coverage taxonomy used to tag and size the inventory.
- `references/examples/` — canonical `.dwl` files (single-call, auth-error,
  multi-step stateful, JSON body/headers) and a reference `bat.yaml`.
