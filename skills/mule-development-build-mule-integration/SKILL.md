---
name: build-mule-integration
description: Workflow required before any Mule flow and integration work. Call use_skill as your FIRST action — before reading project files — whenever the user asks to create, generate, update, fix, modify, change, edit, tweak, adjust, or rework any Mule flow, sub-flow, or component. Do not read project files and attempt the change yourself — even targeted single-component changes like 'modify the choice router', 'fix the until-successful', or 'update the catch block' require this workflow. Covers all change types, new integrations and targeted changes to error handlers, catch blocks, choice routers, DataWeave transforms, HTTP listeners, foreach loops, retry policies, scatter-gathers, connectors, and variable assignments. Prompts beginning with 'This code defines...' or 'This flow...' are generation requests, not analysis. When you call this skill, it must be the only tool call in that response.
license: Apache-2.0
compatibility: Requires Anypoint CLI v4 with the `@salesforce/anypoint-cli-dx-mule-plugin` DX plugin, Java 11+, Maven 3.6+, Mule Runtime (for `dx mule describe-connector` metadata commands)
metadata:
  author: mule-dx-tooling
  version: "1.3.0"
  cli: anypoint-cli-v4
  theme: professional
allowed-tools: Bash Read Write Edit AskUserQuestion
---

# Mule Developer

Build professional Mule integrations with intelligent connector discovery and data-driven XML generation.

## When to Use This Skill

**Use this skill when users request:**

- "Create a Mule app/integration/flow"
- "Build integration between X and Y"
- "Sync data from X to Y" (e.g., "Salesforce to Slack", "MySQL to Salesforce")
- "Query Salesforce", "Send Slack notifications"
- "Schedule jobs", "Poll data every N minutes"
- "Create webhooks", "Build event-driven flows"

**Trigger keywords:** create, build, integrate, sync, connect · mule, integration, flow, app, project · salesforce, slack, servicenow, jira, netsuite · mysql, postgresql, database · api, http endpoint, rest api · schedule, poll, every N minutes · alert, notify, webhook.

Always search Exchange for system-specific connectors first. Most SaaS applications have dedicated connectors.

---

## Prerequisites

```bash
anypoint-cli-v4 --version
anypoint-cli-v4 dx --help
echo $JAVA_HOME && java -version   # Java 11+
anypoint-cli-v4 conf
```

If tools are missing:

```bash
npm install -g @mulesoft/anypoint-cli-v4
npm install -g @salesforce/anypoint-cli-dx-mule-plugin
anypoint-cli-v4 conf username <username>
anypoint-cli-v4 conf password <password>
```

---

## Bundled scripts

This skill ships small bash scripts under `scripts/`. Invoke them with the `Bash` tool — do not inline their contents into a response. The scripts persist their output to disk so later steps can consume it mechanically and are not at the mercy of shell variables that vanish when a Bash tool call returns:

| Script | Purpose | Output location |
| --- | --- | --- |
| `scripts/validate_prerequisites.sh` | Step 1 — validate toolchain (CLI, DX plugin, Java 11+, JAVA_HOME, Mule runtime presence). Validation-ONLY | `tmp/mule-dev-env.json` (workspace-relative; contains `mule_version`, `runtime_path`, `errors[]`, ...) |
| `scripts/get_latest_connector.sh <search> [nickname]` | Step 3 — search Exchange and print ranked connector candidates (`groupId:assetId:version`, one per line, no score, no winner cue). Writes nothing. | stdout only |
| `scripts/pick_connector.sh <nickname> <gav>` | Step 3 — record the agent's chosen GAV (after reasoning or an `AskUserQuestion`) as a draft | `tmp/connector-choices/<nickname>.json` (`{groupId, assetId, version}`) |
| `scripts/commit_connectors.sh` | Step 8 (post-TDD-approval) — promote every draft under `tmp/connector-choices/` to the pinned `tmp/connector-versions/` directory that Phase 2 reads | `tmp/connector-versions/*.json` |
| `scripts/build_gav.sh <json>` | Turn a saved connector JSON into its `groupId:assetId:version` string | stdout |
| `scripts/build_deps.sh [versions-dir]` | Step 8 — read every connector pin in `tmp/connector-versions/` and emit a comma-joined GAV string, ready for `dx mule project create --dependencies`. Skips `db-driver.json` and any non-pin file. | stdout |
| `scripts/describe_connector.sh <nickname> [--type operation\|source --name <name>]` | Step 4 (no flags) / Step 13 (with flags) — run `dx mule describe-connector` for the drafted GAV, save full JSON, echo digest to stdout, AND cache `.errorTypes` to `tmp/connector-errors/` for the Step 16 validator | `tmp/connector-metadata/<nick>[-<name>].json` + `tmp/connector-errors/<nick>[.<name>].json` + digest on stdout |
| `scripts/validate_before_build.sh <project-dir>` | Step 16 pre-mvn — error-type whitelist (Cluster D), namespace↔dependency parity (Cluster A2–A5), canonical XSD URL shape | stderr + non-zero exit on first violation |
| `scripts/maybe_add_http_connector.sh --project <dir> <providers...>` | Phase 2 — defensive check that HTTP connector is present when OAuth providers were chosen; edits `<dir>/pom.xml` | `<dir>/pom.xml` |
| `scripts/search_templates.sh <search-term>` | Step 1b (template path) — search Anypoint Exchange for `type == "template"` assets via parallel calls (unscoped + org-scoped), dedup, rank by token overlap, enrich top 10 with `description`, `minMuleVersion`, and `sourceLocation`. | Single JSON array on stdout (max 10 rows, private-first). Exits 1 on no match. |

Invoke scripts by the absolute path you were given in the "skill is now active" message (it is the directory containing this `SKILL.md`). Do **not** construct relative paths like `../scripts/...` — Cline's working directory shifts across turns and relative paths have produced "No such file or directory" errors in real runs. The inline step examples below write `scripts/...` as shorthand; substitute `<skill-dir>/scripts/...` when you actually execute them.

**Why scripts instead of inline bash:** in earlier iterations connector search was a shell *function* defined inside a single `Bash` tool call. When the call returned the subshell died and the resolved GAV went with it. By the time a later step assembled `dx mule project create`, the only trace of the version was in scrolled-past tool output — and the agent frequently pasted a fictional version from training-time memory instead. Persisting to a file on disk makes the version something we can `jq` at the command site, which removes that failure mode entirely.

---

## Workflow shape (two phases)

This workflow has two phases separated by a hard user-approval gate.

- **Phase 1: Technical Design (Steps 1–7).** Identify systems, search Exchange, describe connectors, pick trigger and providers, present a Technical Design Summary, wait for the user to approve. Phase 1 writes **nothing** to the user's project directory — all artifacts live under workspace-relative paths: `tmp/mule-dev-env.json` (env cache owned by `validate_prerequisites.sh`), `tmp/connector-choices/*.json` (draft connector picks), and `tmp/connector-metadata/*.json`. The pinned `tmp/connector-versions/*.json` directory that Phase 2 reads is only populated after Step 7's approval, by `commit_connectors.sh`.
- **Phase 2: Build (Steps 8–17).** Create the real project, generate config and flow XML, run the build, declare completion. Phase 2 is the only phase that touches the user's project directory.

Phase 2 MUST NOT start until Step 7's approval gate has been passed explicitly. Skipping Phase 1 — or collapsing it into a single "I'll just use HTTP" decision — is the single highest-impact failure mode of this skill and is what the two-phase structure exists to prevent.

## Workflow-wide discipline (read before Phase 1)

- **Build → cleanup → completion separation (Step 16 → Step 17 → Step 18).** Three responses, in order, each with a single tool call: `mvn clean package`, then `rm -r tmp/`, then the completion signal. Do not bundle them. Wait for each result before moving on.
- **One mvn invocation per response.** When re-running a build after a fix, emit only the `mvn` command in that response. Do not bundle it with further edits, follow-up shell commands, or the completion signal.
- **"Completion" means the build already passed.** You may only declare completion after a response that ran `mvn clean package` came back with `BUILD SUCCESS`.
- **Connector versions come ONLY from the Step 3 flow.** Never paste a version from `references/connector-catalog.md`, from training-time memory, or from extrapolation. Step 3 is a three-script dance: `get_latest_connector.sh` lists ranked candidates (stdout only, no pin file), `pick_connector.sh <nickname> <gav>` records the chosen row as a draft in `tmp/connector-choices/`, and `commit_connectors.sh` (Step 8, first action after TDD approval) promotes every draft to `tmp/connector-versions/`. Every GAV that reaches `dx mule project create --dependencies` or `pom.xml` must be pulled from a `tmp/connector-versions/*.json` file via `scripts/build_deps.sh` (for the full `--dependencies` string at Step 8) or `scripts/build_gav.sh` (for a single connector's GAV elsewhere in Phase 2). The catalog's versions are snapshots that drift — treat it only as a connector-identity reference, not as a version source.
- **The agent does the picking, not the script.** `get_latest_connector.sh` deliberately emits a plain ranked list with no score, no emoji, and no "winner" signal. When the list has one row the choice is obvious. When it has several rows the agent must decide which one matches the user's stated system — and if the rows represent real variants of the same family (Slack `mule4-slack-connector` vs `mule-slack-connector`; FTP vs FTPS; Dynamics 365 vs Dynamics GP/NAV/BC; IBM MQ vs Solace vs JMS), the decision belongs to the user via `AskUserQuestion`, not to the agent's guess. The cost of one extra prompt is one turn; the cost of a silent wrong variant is a full Phase-2 rewrite.
- **No HTTP fallback without evidence.** You may only classify a system as "no dedicated connector exists, use HTTP" AFTER `scripts/get_latest_connector.sh <system>` has run AND returned zero matches (exit 1) OR every row in the ranked list is obviously a different product (no assetId shares tokens with the system name beyond noise words like `mule`/`connector`). Declaring HTTP as the answer before the search has run is forbidden. Exchange carries dedicated connectors for hundreds of SaaS products that are easy to miss when reasoning from training-time knowledge alone — the helper script is the authoritative check. A dedicated connector gives metadata discovery, typed operations, and correct authentication; HTTP gives raw request plumbing the user would then have to wire up by hand, so quietly falling back to HTTP is a real loss, not a neutral choice. Note that any ranked row whose `groupId` is a UUID (e.g. `a50e4364-a38c-4340-b05a-c1f8ebed0748:…`) is a connector the user's organization has published privately to Exchange — treat these as first-class candidates, not noise. An org that took the trouble to publish a private connector usually wants it used, often because it wraps internal endpoints, custom auth, or a golden-path the public connector can't cover.

---

# Phase 1: Technical Design

## Step 1: Validate Prerequisites

Run the prerequisite validation script. It only handles validation. It writes the prereq validation findings to `tmp/mule-dev-env.json` in the current workspace; Step 8 reads `mule_version` from there.

```bash
bash scripts/validate_prerequisites.sh
```

If the script exits non-zero, STOP progressing any further in the skill and inform the user to act on the `errors` array in `tmp/mule-dev-env.json`. Do not invent a fallback Mule version — `mule_version` is empty when no runtime is detected.

What `validate_prerequisites.sh` checks: Anypoint CLI v4 installed · DX plugin available · `JAVA_HOME` set · Java 11+ · Mule runtime detected at `~/.mule-dx/config.json:.runtimePath` or under `~/AnypointCodeBuilder/runtime/mule-*`. If runtime or other tools are missing, the script reports the error and informs the user to run the necessary commands for proper installation.

---

## Step 1b: Project Source Decision

**Always ask this when creating a new project.** After prerequisites pass, determine how the user wants to create the project:

```xml
<ask_followup_question>
<question>I can create this project in one of three ways. Which would you prefer?</question>
<options>["I want to generate from scratch without a template.", "I want to use organizational templates from Anypoint Exchange.", "I have a local template file (.jar or .zip) I want to use."]</options>
</ask_followup_question>
```

**Based on the answer:**

1. **Exchange or Local template** → Read `references/template-project-creation.md` and follow the appropriate flow (Exchange E1–E4, or Local L1–L4). The sub-skill ends with an explicit **continue-or-stop** prompt (Steps E5 / L5) — if the user picks "stop", declare completion via `<attempt_completion>`; if they pick "continue", return here and proceed to Step 2.
2. **Scratch** → Continue to Step 2. Project creation will happen at Step 8 (after connector discovery provides the `--dependencies`).

**When to skip this step entirely:**
- User is working on an existing project (modifying/updating flows, not creating a new one)

---

## Step 2: Identify Systems and Trigger Hints

**[BLOCKER] Step 2 MUST NOT prompt the user.** Do not emit an `<ask_followup_question>` or `<AskUserQuestion>` here. The trigger decision happens in Step 5 after connector metadata is on disk — prompting now would force generic options (HTTP Listener / Scheduler) instead of real connector sources, which is the single highest-impact anti-pattern this workflow exists to prevent.

Produce two records in your response text. These are plain prose — not a thinking block, not a tool call — so later steps (and the user) can read them.

**1. Systems list.** Identify **EXACT system names**: source systems (where data comes from), target systems (where data goes to). Use specific names (Slack, Jira, ServiceNow, Stripe, Shopify), NOT generic terms (chat, ticketing, payments, commerce). Every name on this list will be searched in Step 3; every search must result in a `tmp/connector-choices/<nick>.json` draft on disk (the agent picks from the ranked list and calls `pick_connector.sh`).

**Anti-pattern — inferring a backend from a destination name.** When the prompt mentions a queue, topic, bus, or similar messaging destination, the string that names the destination (e.g. `foo.queue`, `orders.topic`, `events-stream`) is a *label*, not a technology. It does NOT identify which broker is behind it. Do NOT add a specific broker (Anypoint MQ, Kafka, IBM MQ, Solace, SQS, etc.) to the Systems list unless the prompt names it explicitly. If the prompt only says "queue" / "topic" / names a bare destination, list the system as `messaging broker (backend unspecified)` and plan to escalate in Step 3 — the user picks the backend, not the agent. Why this matters: a silently-chosen broker anchors Phase 2 against the wrong connector family, which is a full Phase-2 rewrite to correct.

**2. Trigger hints.** In one or two sentences, note the **verbatim phrases** from the user prompt that describe what starts the flow or names a cadence — e.g. *"every 3 seconds"* or *"listens for new Stripe charges"* or *"makes a GET request to retrieve customers"*. Do NOT classify yet. No class label, no decision tree, no "so the trigger is…". Step 5 does the trigger decision from connector metadata that does not exist yet; committing to a trigger now — even implicitly via a class — tends to anchor the agent against the real `sources[]` that Step 4 will produce.

If the prompt mentions no trigger or only describes outbound work ("makes a request", "fetches", "calls"), say so explicitly: "No explicit trigger phrase — outbound-only description." Step 5's metadata-first ladder handles this.

**Connector strategy per system:**

- **Major SaaS platforms** (Salesforce, ServiceNow, NetSuite, Workday) → search for dedicated connector in Step 3.
- **Standard protocols** (Database, JMS, FTPS, SFTP) → search for protocol-specific connector in Step 3.
- **Mid-market SaaS** (Stripe, Shopify, HubSpot, Twilio, Plaid, etc.) → search for dedicated connector in Step 3. Do NOT assume these have no connector — Exchange has dedicated connectors for many of them. Training-data intuition that "Stripe/Shopify/etc. is a REST-API-only system" is unreliable; the search is the authority.
- **Queue or Pub/Sub with a named backend** ("Kafka topic", "IBM MQ", "SQS", "Solace") → search for that specific connector in Step 3.
- **Queue or Pub/Sub without a named backend** (the prompt uses "queue", "topic", or a bare destination name without naming the broker technology) → per the Step-2 anti-pattern above, the destination name is not the backend. In Step 3, escalate via `AskUserQuestion` to let the user pick the backend (JMS via any broker provider, Kafka, IBM MQ, Solace, SQS, etc.). Only if the user declines to choose should you default to `mule-jms-connector` — JMS is the generic protocol layer that fits any broker, with the broker selected in Step 6 via the connection provider (active-mq, active-mq-nct, generic).
- **Unknown/Unclear / custom internal APIs** → still search Exchange first in Step 3; HTTP is the fallback only when Step 3's search returns nothing plausibly related.

Your next tool call after Step 2 MUST be `get_latest_connector.sh` for a system from your Systems list — NOT an `ask_followup_question`, NOT a describe-connector, NOT anything else. Step 3 is the non-negotiable next step.

---

## Step 3: Search Exchange for Connectors, Decide, Draft the Choice

Step 3 is a three-move loop run **once per named system** from Step 2:

1. **List** candidates with `get_latest_connector.sh`.
2. **Decide** which row is the right fit — inline rationale if the choice is obvious, `AskUserQuestion` if the rows are real variants of the same system family.
3. **Draft** the chosen GAV with `pick_connector.sh`. The draft lands in `tmp/connector-choices/<nick>.json` and stays there through Phase 1.

The script does not pin a winner. There is no emoji, no score, no "Picked" line in its output. When the list has one row the shape of the output is "one row"; when it has several the shape is "several rows" and that is the cue to read the names and reason about intent — or to escalate.

**Mandatory search rule.** Run `get_latest_connector.sh` for EVERY named system from Step 2 — including systems whose prominence in your training data leads you to assume they have no dedicated connector. Declaring "system X has no dedicated connector" without the script having run is forbidden. This is the rule that prevents silent HTTP fallback — see "No HTTP fallback without evidence" in the workflow-wide discipline.

**Term breadth.** Always prefer the broader system name (`databricks`, `aws-storage`, `snowflake`, `database`, `salesforce`) over a narrow suffix-pinned term like `mule-amazon-s3-connector` or `mule-db-connector`. Narrow terms can miss org-private connectors whose assetId shares no tokens with the public connector's name — e.g. searching `mule-amazon-s3-connector` won't surface a private `mule-plugin-aws-storage-api`, and `mule-db-connector` won't surface a private `<uuid>:mule-plugin-customer-warehouse-database`. The "Common search terms" table further down is a starting hint for well-known systems, not a constraint — if the broader term is noisy, you can always re-run with a narrower one.

**Version source-of-truth rule (MANDATORY):**

- The **only** acceptable source for a connector's version number is `get_latest_connector.sh` run against live Exchange in the current session, recorded via `pick_connector.sh`, and later promoted to `tmp/connector-versions/` by `commit_connectors.sh`. This applies equally to `dx mule project create --dependencies`, `pom.xml` `<dependency>` blocks, and every other place a version appears.
- **Do not** paste a version from `references/connector-catalog.md`. The catalog exists to help identify *which* connector to use (asset ID, purpose); its version numbers are best-effort snapshots that drift.
- **Do not** invent a version from memory or by extrapolating. Version numbers on Exchange are not predictable.
- **Do not** write a version before the corresponding `tmp/connector-choices/<name>.json` draft exists on disk.

### Move 1 — list

One invocation per named system. The nickname is how the draft and later pin will be named, so pick something short and use it consistently:

```bash
bash scripts/get_latest_connector.sh mule-salesforce-connector sfdc
```

Stdout shape, one GAV per line, ranked best-guess-first:

```
com.mulesoft.connectors:mule-salesforce-connector:11.1.0
com.mulesoft.connectors:mule-salesforce-analytics-connector:4.1.0
com.mulesoft.connectors:mule-salesforce-composite-connector:2.5.2
com.mulesoft.connectors:mule-salesforce-marketing-cloud-connector:5.0.0
```

Exit 0 means at least one row was returned; exit 1 means no Mule 4 extension matched and you need to treat this system as HTTP-fallback territory (see the workflow-wide discipline).

### Move 2 — decide & confirm

Read the list. Two cases, in order:

**Case A — one row.** Only one Mule 4 extension matches. Acknowledge the choice inline in one sentence ("Only match for HTTP: `org.mule.connectors:mule-http-connector:1.11.1`") and go to Move 3.

**Case B — multiple rows that are real variants of the same system family.** Rows whose assetId does not plausibly name the user's system are noise — filter them out logically. If more than one row/choice remains after the logical filtering for the user's system (e.g., Salesforce query returned `mule-salesforce-connector` plus three Salesforce sub-products for Analytics / Composite / Marketing Cloud etc.), always escalate via `AskUserQuestion`. Some common variant families that requires user confirmation:

- `slack` → `mule-slack-connector` (community, v4.x) **vs** `mule4-slack-connector` (premium MuleSoft, v2.x). Different OAuth shapes, different operations — neither is a "newer version" of the other.
- `ftp` → `mule-ftp-connector` (plain) **vs** `mule-ftps-connector` (TLS). Always confirm and suggest FTPS for best security practices.
- `ibm-mq` vs `solace` vs `kafka` vs `jms` — a destination name in the prompt (e.g. `foo.queue`, `bar.topic`) does NOT identify the backend. Unless the prompt explicitly names the broker technology, escalate with these as options; `mule-jms-connector` is the generic-protocol fallback when the user declines to pick.
- `microsoft-dynamics-*` — 365, GP, NAV, 365-Business-Central, CRM are different products the user may have meant interchangeably.
- `oracle-ebs` vs `oracle-ebs-122` — alternate EBS major versions.
- Any pair whose assetIds share the target system's name and differ only in a variant suffix, protocol marker, major-version marker, or the `mule4-` vs `mule-` prefix.
- A public connector + a private (UUID-groupId) connector for the same system family — e.g. `com.mulesoft.connectors:mule4-snowflake-connector` and `<uuid>:mule-plugin-snowflake-sys-api-json` both showing up in a `snowflake` search. The org-published asset usually exists for a reason (custom auth, internal endpoints, a wrapper around the public connector), so NEVER silently pick the public one when a private alternative is in the same ranked list — surface both with `AskUserQuestion` and let the user choose.

Prompt shape when you escalate:

```xml
<ask_followup_question>
<question>Two Mule 4 Slack connectors exist on Exchange. Which should this integration use?</question>
<options>[
  "org.mule.connectors:mule-slack-connector:4.3.2 — community Slack connector",
  "com.mulesoft.connectors:mule4-slack-connector:2.0.1 — MuleSoft premium Slack connector",
  "Other — describe which Slack variant you need"
]</options>
</ask_followup_question>
```

When more than one choice exists, confirm with user; a silent wrong variant costs a Phase-2 rewrite.

If the user's prompt explicitly names one variant ("use the Dynamics 365 connector, not BC", "the premium Slack connector only"), that pins the choice and you proceed without asking.

### Move 3 — draft

Record the chosen GAV as a draft. Idempotent — you can re-run with a different GAV if Step 4 or Step 5 metadata reveals a better fit:

```bash
bash scripts/pick_connector.sh sfdc   com.mulesoft.connectors:mule-salesforce-connector:11.1.0
bash scripts/pick_connector.sh slack  com.mulesoft.connectors:mule4-slack-connector:2.0.1
bash scripts/pick_connector.sh jms    org.mule.connectors:mule-jms-connector:1.10.3
# → tmp/connector-choices/{sfdc,slack,jms}.json now each contain {groupId, assetId, version}
```

If you realize after Step 4's metadata digest that the draft is wrong, re-run `pick_connector.sh` with the corrected GAV. Drafts remain mutable until Step 8's `commit_connectors.sh` promotes them.

**Why drafts instead of pins during Phase 1.** If a connector choice bakes into `tmp/connector-versions/` before the user has seen the Technical Design Summary, the agent — and every downstream check — treats it as settled. Holding the choice as a draft until TDD approval keeps the whole design reversible, and lets the approval gate be the real commitment point.

### Selection rules the script applies internally

(Reference only — you don't need to reimplement them. The list is ordered best-guess-first; treat ordering as a soft hint, not a directive.)

- Only `"type": "extension"` (Mule 4 compatible) — Mule 3 `type=connector` assets, templates, examples, and rest-apis are filtered out.
- Any groupId whose asset is `type="extension"` is admissible; ranking keeps first-party connectors on top via a 3-tier preference (`com.mulesoft.connectors` > `org.mule.connectors` > other).
- Latest semantic version within each `(groupId, assetId)` group.
- Token-overlap scoring with the search term; the premium groupId and shorter assetId break ties. Scores are used for ordering only and are never emitted.
- Two pages fetched in parallel (offsets 0 and 200) so broad searches like `salesforce` don't drop candidates off a single page.

### Common search terms

These are starting hints for well-known systems. For anything else — and especially for any system you suspect the user's org may have a private connector for — search by system name first.

| System | Search term |
| --- | --- |
| Salesforce | `salesforce` |
| Database | `database` |
| HTTP | `http` |
| NetSuite | `netsuite` |
| ServiceNow | `servicenow` |
| Amazon S3 | `amazon` |
| JMS | `jms` |
| Slack | `slack` (returns both Slack variants — this is the ambiguous case above) |

For any system not in the list, search dynamically with the system name (e.g. `stripe`, `shopify`, `hubspot`, `databricks`, `snowflake`) — don't assume naming patterns and don't assume the system has no connector. Broader system-name terms also surface any private (UUID-groupId) connectors the user's organization has published in the same domain, which a narrow `mule-<name>-connector` term tends to miss.

---

## Step 4: Describe Connectors

For each connector resolved in Step 3, retrieve its full metadata and **read the digest** that the wrapper script prints. Use `describe_connector.sh` rather than writing the `describe-connector` pipeline by hand — the wrapper resolves the probe path, saves the full JSON to disk for later steps, AND echoes `sources[]` and `configs[]` to stdout so you see what Step 5 will need:

```bash
bash scripts/describe_connector.sh sfdc       # nickname from Step 3
bash scripts/describe_connector.sh stripe
bash scripts/describe_connector.sh http
```

Each invocation writes `tmp/connector-metadata/<nickname>.json` (full response, consumed again by Phase 2) and prints a digest shaped like this:

```json
{
  "namespace_prefix": "stripe",
  "sources": [
    "on-canceled-subscription-listener",
    "on-new-charge-listener",
    ...
  ],
  "configs": [
    { "name": "config", "providers": ["api-key"] }
  ],
  "operations_count": 335,
  "operations_sample": ["createV13dSecure", "..."]
}
```

**Read the `sources[]` array that comes back.** That list is the set of real native triggers the connector supports; it is what Step 5 branches on. Do not skip past the digest straight to the next `describe_connector.sh` call — Step 5's trigger decision depends on you knowing which sources each connector exposes, and the digest is the cheapest place to get that information.

The script also writes `tmp/connector-errors/<nickname>.json` with the connector-wide error-type whitelist. The Step 16 validator reads this directory; you don't need to invoke it manually.

If you ever need the full response (e.g. to introspect `childElements[]` for `oauth-callback-config`), read `tmp/connector-metadata/<nickname>.json` directly.

**Manual fallback** — if for some reason the wrapper is unavailable, you can reproduce it by hand. In Phase 1 the draft file is authoritative; `build_gav.sh` accepts either location:

```bash
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule describe-connector \
  --connector "$(bash scripts/build_gav.sh tmp/connector-choices/sfdc.json)" \
  --output json > tmp/connector-metadata/sfdc.json
jq '{namespace: .namespace.prefix, sources, configs: [.configs[] | {name, providers: [.connectionProviders[]?]}]}' tmp/connector-metadata/sfdc.json
```

But in the common case prefer the wrapper — it is one line instead of three and it makes the sources list visible in your turn's tool output without a follow-up call.

---

## Step 5: Select Trigger

Every top-level flow (that is not a sub-flow or a `<flow-ref>` target) needs exactly ONE trigger. Step 5 decides *which* trigger by letting connector metadata drive the choice — not prompt-text intuition.

**[BLOCKER] Explore-before-decide gate.** Before committing to a trigger — whether inline or via `AskUserQuestion` — both of the following must be true for EVERY named system from Step 2's Systems list:

1. `tmp/connector-choices/<nick>.json` exists on disk (Step 3, via `pick_connector.sh`).
2. `tmp/connector-metadata/<nick>.json` exists on disk (Step 4).

AND you must have the `sources[]` content in view. Run:

```bash
for f in tmp/connector-metadata/*.json; do
  echo "--- $f ---"
  jq '{namespace: .namespace.prefix, sources}' "$f"
done
```

in the response that begins Step 5, and read the output. This is the same data the `describe_connector.sh` digest already showed per connector in Step 4, but re-echoing it here puts every connector's sources side-by-side in one place right before the decision. Do not commit to a trigger without having those lists in the current tool output — past turns scroll out of context quickly.

Why this gate exists: if the agent commits to a trigger before reading `sources[]`, the usual failure mode is to default to `http:listener` (treating the prompt as a webhook) and silently ignore a real connector source that Step 4 just fetched. A connector's `sources[]` array is the authoritative list of triggers it supports; Step 5 must branch from that list, not from prompt-text intuition.

### Decision ladder (evaluate in order)

Work through the rungs below in order. Each rung is one of the possible *paths* — there is no "fallback" ranking; the first path whose preconditions all match is the one you take.

#### Rung 1 — Connector-source path

For each connector in scope, examine `sources[]` from the digest. For any source whose **name** plausibly relates to the user's stated need (noun match: "product", "order", "charge", "customer"; AND verb-prefix consistency: `on-new-*`, `on-updated-*`, `on-modified-*`, `on-*-arrived`, `poll-*`, `*-listener`, `*-trigger`), inspect its shape via the unified `describe-connector` command with `--type source`:

```bash
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule describe-connector \
  --connector "$(bash scripts/build_gav.sh tmp/connector-choices/<nick>.json)" \
  --type source \
  --name <source-name> \
  --output json
```

Do **not** call `source-detail` on every source — only on those whose name plausibly fits the user's intent per the noun+verb-prefix check above. On rich connectors this is the difference between 1–2 CLI calls and 7+ (Shopify, Salesforce, etc.).

Compare the returned **shapes** — not the names alone — to the user's intent:

- If the source's `childElements[]` includes a `scheduling-strategy` element, this is a **polling source** — the connector itself handles the cadence natively. When the user's prompt names a cadence ("every N", "daily", "hourly") AND the matched source is a polling source, the cadence goes inside the source's `<scheduling-strategy>` child. **Do NOT introduce a separate top-level `<scheduler>` alongside it.** Example correct shape:
  ```xml
  <shopify:on-updated-product-trigger config-ref="shopifyConfig">
      <scheduling-strategy>
          <fixed-frequency frequency="3000" startDelay="5000"/>
      </scheduling-strategy>
  </shopify:on-updated-product-trigger>
  ```
- If the source has no `scheduling-strategy` child and exposes an event (`on-new-*`, `on-modified-*`), it's an **event source** — use it directly; no top-level scheduler needed.
- If the source's shape includes `listenerConfig` references, it's a **webhook receiver** — suitable for "receive callback at endpoint" prompts.

**Commit inline** to a connector source when exactly one source's shape fits the user's intent and the match is explainable in one sentence. State the choice with a one-line rationale citing the source name.

**Prompt via `AskUserQuestion`** when two or more sources both pass the shape check against the user's intent, OR when the user's language is genuinely ambiguous about which source semantics they want. Options list the real source names, not generic placeholders:

```xml
<ask_followup_question>
<question>Which Salesforce event should trigger this flow?</question>
<options>[
  "salesforce:replay-topic-listener — subscribe to a Salesforce streaming topic",
  "salesforce:modified-object-listener — fire when a record of a given sObject is modified",
  "Other — pick a different source"
]</options>
</ask_followup_question>
```

If no source passes the shape check against any connector in scope, move to Rung 2.

#### Rung 2 — Generic scheduler path

Take this path when:

- No connector source fits the user's intent (Rung 1 examined the candidates and none matched), AND
- The prompt names a cadence ("every N", "daily", "hourly", "poll every…"), AND
- The flow body will call connector operations (not event-driven).

Use `<scheduler>` with `<fixed-frequency>` or `<cron>`. State the choice inline.

**Record the rejection.** When taking this path, note in one sentence why Rung 1's sources were rejected — e.g. "Shopify's `on-updated-product-trigger` matches 'every 3 seconds' but the user wants to pull by custom date range not 'updated since last poll', so a generic `<scheduler>` + `shopify:product-list` is more appropriate." Step 7's TDD requires this list; capture it now while the reasoning is fresh.

#### Rung 3 — HTTP Listener path

Take this path when:

- The prompt explicitly says "expose endpoint", "receive HTTP request", "provide REST API", "webhook at /path", AND
- No connector source in scope is a webhook-style receiver.

Use `<http:listener>`. State the choice inline. Record which connector sources were considered and why they were rejected (see Step 7).

#### Rung 4 — Ask the user

Take this path when none of Rungs 1–3 clearly apply — e.g. the prompt is outbound-only ("makes a request", "fetches", "retrieves") with no cadence and no endpoint language. `AskUserQuestion` with options derived from the actual `sources[]` of connectors in scope PLUS Scheduler and HTTP Listener:

```xml
<ask_followup_question>
<question>The prompt describes outbound calls but does not name a trigger. What should start this flow?</question>
<options>[
  "Scheduler — run on a time-based schedule",
  "HTTP Listener — receive an inbound HTTP request",
  "<connector>:<source-name> — native event from one of the connectors in scope (list any that apply based on sources[])",
  "Other — please describe"
]</options>
</ask_followup_question>
```

### After the decision

Record the selected trigger, its owning connector (if any), and — if the path is Rung 2 or Rung 3 — the list of connector sources that were considered and one-line reasons each was dismissed. Step 7's TDD surfaces this list; if it is missing, the TDD is incomplete and Phase 2 cannot start.

**[BLOCKER] WAIT for the user's response before moving to Step 6 when this step prompts.**

---

## Step 6: Select Connection Providers

**Ask the user only when there is an actual choice to make.** For each connector, look at the `configs[]` metadata captured in Step 4 — specifically the `connectionProviders` list of the config that owns the operation you intend to call in Phase 2.

**Decision rule:**

- **Multiple configs or multiple providers** → **MUST** use `AskUserQuestion`. The user's choice determines both which `config-name` and which `--connection-provider` you pass to Step 11's `config-detail` call, and which XML structure you write in Step 12.
- **Exactly one config and exactly one provider** → **DO NOT** prompt. State the choice inline in one line ("Using `s3:config[connection]` — the only option provided by the connector") and proceed. Prompts that offer a single "option" look like pointless ceremony and waste a conversation turn.

**Worked examples from live Exchange metadata:**

| Connector | `configs` × providers | Action |
| --- | --- | --- |
| S3 connector | `config[connection]` | Announce, do NOT prompt |
| VM connector | `config[connection]` | Announce, do NOT prompt |
| HTTP connector | `listener-config[listener-connection]`, `request-config[request-connection]` | Configs map 1:1 to listener vs request — determined by the flow shape (trigger vs outbound call), not a user preference. Announce, do NOT prompt. |
| A multi-config connector with stream vs. non-stream configs | `config[basic, role]`, `streams-config[streams]` | **Prompt** — pick the config whose operations match the use case, and if that config has >1 provider, pick a provider. |
| A connector offering basic / OAuth / JWT / client-credentials | `config[basic, oauth-user-pass, jwt, oauth-client-credentials]` | **Prompt** — real alternatives with different credential models. |
| Database connector | `config[my-sql-connection, oracle-connection, data-source-connection, generic-connection, ...]` | **Prompt** for the provider, then resolve the JDBC driver GAV in the same step (see "Step 6b — JDBC driver resolution" below). Step 9 is a mechanical `pom.xml` edit. |

**When you do prompt,** present only the real alternatives (don't pad with "if unsure..." copy). Example:

> This connector offers four connection providers. Which should this integration use?
> - `basic` — username + password + security token
> - `oauth-user-pass` — OAuth with user credentials
> - `jwt` — JWT bearer token (server-to-server)
> - `oauth-client-credentials` — OAuth client credentials

**Do not offer a "recommendation" as one of the options** if it's really the only option. If there is only one choice, do not ask.

Store the selected `(config-name, connection-provider)` pair for each connector, and **persist the `describe-connector` connection-provider output** for Phase 2 so it doesn't have to re-invoke the CLI. **Flag semantics note:** `--name` carries the **connection provider** name, `--config-name` carries the **config** name — easy to get backwards:

```bash
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule describe-connector \
  --connector "$(bash scripts/build_gav.sh tmp/connector-choices/sfdc.json)" \
  --type connection-provider \
  --name basic-connection \
  --config-name sfdc-config \
  --output json > tmp/connector-metadata/sfdc-config.json
```

### Step 6b — JDBC driver resolution (only if `mule-db-connector` is in scope)

`mule-db-connector` is the one case where the Step-6 provider choice needs more clarification. The provider choice only handles the XML connection element (`<db:my-sql-connection>`, `<db:generic-connection>`, etc.), but the **JDBC driver JAR** is a separate Maven artifact that must ship alongside the connector via `<sharedLibrary>`. Resolve both in Step 6 so Step 7's design summary can show a full `groupId:artifactId:version` for the driver and Step 9 becomes a mechanical `pom.xml` edit with no further prompting.

**Branch on the Step-6 provider answer:**

| Provider picked | Driver auto-pin from the canonical table (Step 9) | Prompt? |
| --- | --- | --- |
| `my-sql` | `com.mysql:mysql-connector-j:8.4.0` (8.4 LTS; 9.x requires JDK 21) | No — announce inline |
| `oracle` | `com.oracle.database.jdbc:ojdbc11:23.9.0.25.07` (Java 17+) | No — announce inline |
| `mssql` | `com.microsoft.sqlserver:mssql-jdbc:13.4.0.jre11` (Java 17+) | No — announce inline |
| `generic` **and the target database is identifiable as PostgreSQL** (user prompt names Postgres, a prior turn named Postgres, or a JDBC URL placeholder shows `jdbc:postgresql://`) | `org.postgresql:postgresql:42.7.11` — the canonical `generic` pairing | No — announce inline |
| `generic` **and the target is something else or unspecified** (H2, Snowflake, SAP HANA, Vertica, unknown, or the user didn't name a database) | **Cannot auto-pin** — `generic-connection` accepts any JDBC URL and only the target database identifies the driver. IF user select generic, see `references/jdbc-drivers.md` for canonical options, then prompt with Postgres listed first (most common `generic` target). | **Yes** |
| `data-source` | **Cannot auto-pin** — driver is supplied by the container, or by an explicit `<sharedLibrary>` declaration. Prompt. | **Yes** |
| `derby` | **Multi-artifact + JDK-dependent** — If selected, see `references/jdbc-drivers.md` for the embedded vs network-client split and the Java 17 vs Java 8 version matrix. Prompt on `embedded` vs `client`. | **Yes** |

The rule: **if the target database is one of the first rows above (my-sql, oracle, mssql or generic with postgres) do not prompt — auto-pin and announce inline.** Reserve the prompt for non-canonical `generic` targets and for the inherently multi-choice providers (`data-source`, `derby`).

The always-prompt branches all use the same prompt shape:

```xml
<ask_followup_question>
<question>You picked <provider> for <database>; which JDBC driver should ship as a sharedLibrary?</question>
<options>[
  "<canonical-option-1 from the reference file> — <one-line purpose>",
  "<canonical-option-2> — ...",
  "Other — I will provide a groupId:artifactId:version"
]</options>
</ask_followup_question>
```

**What Step 6 must record for Step 9:**

One or more `{groupId, artifactId, version}` tuples, plus the driver class, persisted so Step 9 can emit the `<dependency>` + `<sharedLibrary>` pairs without re-asking. Use a sidecar file next to the connector choice:

```bash
# example: after Step 6 picks my-sql
cat > tmp/connector-choices/db-driver.json <<'JSON'
{
  "dependencies": [
    { "groupId": "com.mysql", "artifactId": "mysql-connector-j", "version": "8.4.0" }
  ],
  "driverClass": "com.mysql.cj.jdbc.Driver"
}
JSON
```

For `derby:embedded` that file contains three entries; for `generic` with PostgreSQL it contains one. The Step-9 applier reads this file and applies every entry in it to `pom.xml`.

The driver choice will be part of the technical design. Step 7 shows it under "Build-time additions"; the user's approval at Step 7 is what authorizes Step 9 to edit `pom.xml`.
---

## Step 7: Present Technical Design Summary

**[BLOCKER] Present ONLY after Steps 1–6 are complete.** Every connector must have a drafted GAV (from `tmp/connector-choices/*.json`), every connector must have captured metadata (from `tmp/connector-metadata/*.json`), and every config must have a selected provider. If any of those is missing, go back to the relevant step — do not paper over with "TBD" in the summary.

```
**Technical Design Summary**

**User Requirement:** "<original user prompt, verbatim>"

**Project Context:**
- Project directory: <absolute path where Phase 2 will create the project>
- Work type: <New / Modification / Post-scaffolding>
- Mule runtime: <mule_version from tmp/mule-dev-env.json>
- Java: <java_version>

**Trigger:**
- Selected: <element name> from <connector or built-in source>
  (e.g., "shopify:on-updated-product-trigger with fixed-frequency 3000ms" or "salesforce:replay-topic-listener from mule-salesforce-connector:10.15.7" or "Built-in Scheduler, every 5 minutes")
- Sources considered: list the `sources[]` entries that were examined via `source-detail` (if any), with one line each
  stating why the source was chosen OR dismissed. If the selected trigger is `<scheduler>` or `<http:listener>` and any
  in-scope connector has a `sources[]` entry, at least one rejection line is required — a TDD whose "Sources considered"
  is empty while a connector source exists is incomplete, and Phase 2 cannot start.
  Example:
  - `shopify:on-updated-product-trigger` — SELECTED: polling source with `scheduling-strategy` child, matches "every 3 seconds" intent.
  - `shopify:on-new-product-trigger` — dismissed: fires only on creation, user wants updates too.
  - `shopify:on-updated-customer-trigger` — dismissed: wrong object (product, not customer).

**Required Connectors:**
1. <System Name>: <GAV> [com.mulesoft.connectors | org.mule.connectors | third-party]
   - Purpose: <one line>
   - Config: <config-name> | Provider: <provider-name>
2. ...

**Build-time additions (auto):**
- `mule-http-connector` — included if the trigger is HTTP Listener OR any Step 6 provider is OAuth-family (callback listener)
- JDBC driver(s) — included if `mule-db-connector` is in scope. List **every** `groupId:artifactId:version` recorded in `tmp/connector-choices/db-driver.json` from Step 6b, plus the driver class. Vague phrasing like "PostgreSQL JDBC driver included" is not acceptable here — the user is approving an explicit build edit and needs the exact coordinates.
  Example:
  - `org.postgresql:postgresql:42.7.11` (driver class `org.postgresql.Driver`) — added as `<dependency>` and `<sharedLibrary>` in `pom.xml`.

**Built-in processors anticipated (if applicable):**
- DataWeave, Logger, error handlers
```

Then ask for explicit approval:

```xml
<ask_followup_question>
<question>Please review the technical design above. Proceed to build (Phase 2)?</question>
<options>[
  "Yes, proceed to build.",
  "No, I want to change the plan.",
  "No, cancel generation."
]</options>
</ask_followup_question>
```

**[BLOCKER] WAIT for explicit "Yes, proceed to build." before Step 8.** On "No, I want to change the plan.", ask which part (trigger, connectors, providers) and loop back to the relevant step. On "No, cancel generation.", stop the workflow politely.

Why this gate matters: Phase 1 is the last chance to catch a silent HTTP fallback, a wrong connector variant, a wrong trigger, or a missing clarifying question. Once Phase 2 begins the project skeleton is on disk and rewinding is more expensive for everyone. The summary is the user's chance to correct course; respect "No, I want to change the plan." as a first-class outcome, not an exception.

**After approval, the very first action of Step 8 is `commit_connectors.sh` — that is the script that promotes every Phase-1 draft in `tmp/connector-choices/` to the pinned `tmp/connector-versions/` directory that `dx mule project create` and `pom.xml` will read from. Do not skip it; `build_deps.sh` / `build_gav.sh` calls later in Phase 2 will fail if the pin files aren't there.**

**Output:** User approval to proceed.

---

# Phase 2: Build

## Step 8: Create Project

**First action — promote Phase 1 drafts to pinned versions.** The user just approved the TDD, so every connector choice in `tmp/connector-choices/` is now official. Promote them in one shot:

```bash
bash scripts/commit_connectors.sh
# → copies every tmp/connector-choices/*.json → tmp/connector-versions/*.json
# → exits 1 if no drafts exist (means Step 3 was skipped for some system)
```

Then read `tmp/mule-dev-env.json` for the Mule version and use `build_deps.sh` to emit the full `--dependencies` string from the pins on disk — do not retype GAVs from previous tool output, and do not inline `$(build_gav.sh ...)` once per connector:

```bash
MULE_VERSION=$(jq -r '.mule_version' tmp/mule-dev-env.json)

NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule project create <project-name> \
  --group-id com.example \
  --mule-version "$MULE_VERSION" \
  --dependencies "$(bash scripts/build_deps.sh)" \
  --skip-environment
```

`build_deps.sh` reads every `tmp/connector-versions/*.json` pin, filters out the Step 6b JDBC driver sidecar (`db-driver.json`), and prints a comma-joined GAV string. Any pin file in that directory is included automatically — including `http.json` if you added it via the rule below.

**Why one wrapper instead of N inlined `$(build_gav.sh …)` substitutions:** with absolute script paths (per the invocation rule above) each inlined `$(…)` is ~165 characters, so a 4-connector project produces a 1000+ character `dx mule project create` command. The Dev Agent terminal harness loses its completion marker on very long commands and stalls the whole turn until the 2-minute timeout fires. `build_deps.sh` keeps the command under ~250 characters regardless of how many connectors are in scope.

**Every connector that appears in the approved Technical Design Summary must have a pin in `tmp/connector-versions/` before `build_deps.sh` runs** — `commit_connectors.sh` already put them there. Two cases add an extra connector beyond the systems explicitly named in the TDD:

| Condition | Added connector |
| --- | --- |
| Step 5 selected trigger is HTTP Listener (flow contains `<http:listener>`) | `mule-http-connector` |
| Step 6 selected any OAuth-family provider (OAuth, JWT, auth-code) | `mule-http-connector` (for OAuth callbacks) |
| Any event-listener source trigger (e.g., `<s3:new-object-listener>`, `<salesforce:replay-topic-listener>`) | None beyond the connector that owns the source — it is already in the TDD |

If either HTTP-trigger condition applies and you have not already picked HTTP in Step 3, run `get_latest_connector.sh mule-http-connector http` + `pick_connector.sh http <gav>` + `commit_connectors.sh` **before** `dx mule project create` so `tmp/connector-versions/http.json` exists when `build_deps.sh` scans the directory. Missing it causes a first-build failure like `Can't resolve http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd` — self-healable, but it costs a turn.

**Version source-of-truth (from Step 3):** every GAV in `--dependencies` must come from a `tmp/connector-versions/*.json` file. **Do not** inline a literal version like `com.mulesoft.connectors:mule-amazon-s3-connector:6.6.0` in the `--dependencies` string — if you bypass `build_deps.sh` and the literal version differs from what the helper would have returned, `mvn clean package` will fail with a "not found" error, and the failure is often not self-healable because the version is fictional.

**Project structure created:**

- `pom.xml` (Maven configuration with dependencies)
- `mule-artifact.json` (artifact metadata with correct Java version)
- `src/main/mule/<project-name>.xml` (flow definition)
- `src/main/resources/` (configuration files)

---

## Step 9: Apply JDBC Driver to pom.xml

The driver GAVs were already chosen in Step 6b and approved by the user at Step 7. Step 9 reads `tmp/connector-choices/db-driver.json` and applies every entry to `<project-name>/pom.xml` — one entry produces one `<dependency>` block AND one `<sharedLibrary>` block. Skip this step entirely if `mule-db-connector` is not in scope.

If `tmp/connector-choices/db-driver.json` is missing but `mule-db-connector` is in scope, return to Step 6b — do NOT invent a driver here or assume prematurely.

**For every entry in `db-driver.json`'s `dependencies[]` array, add both:**

1. **`<dependency>` inside `<dependencies>`**, verbatim from the sidecar:

```xml
<dependency>
    <groupId>{groupId}</groupId>
    <artifactId>{artifactId}</artifactId>
    <version>{version}</version>
</dependency>
```

2. **`<sharedLibrary>` inside the `mule-maven-plugin` `<configuration><sharedLibraries>`** — `groupId`/`artifactId` copied verbatim from the `<dependency>` above (no version here). 

```xml
<configuration>
    <sharedLibraries>
        <sharedLibrary>
            <groupId>{groupId}</groupId>
            <artifactId>{artifactId}</artifactId>
        </sharedLibrary>
        <!-- repeat for every entry in db-driver.json -->
    </sharedLibraries>
</configuration>
```
---

## Step 10: Verify HTTP Connector (OAuth/HTTP-Listener defensive check)

In v7, Step 8's `--dependencies` already includes `mule-http-connector` when Step 5 chose HTTP Listener or Step 6 chose an OAuth-family provider — because Phase 1's approved TDD made that visible. This step is a **defensive no-op check** in the common case: run the helper in case the TDD missed the HTTP addition for some reason.

**Skip this step entirely** when none of the selected providers match `oauth|jwt|auth-code|authorization-code` AND the trigger is not HTTP Listener. Running it as a "just to be safe" consumes a turn.

For the OAuth / HTTP-Listener case, run the idempotent helper:

```bash
bash <skill-dir>/scripts/maybe_add_http_connector.sh \
  --project ./<project-name> \
  "oauth-user-pass"    # one argument per Step-6 provider
```

`<skill-dir>` is the absolute path you were given in the "skill is now active" message (the directory containing this `SKILL.md`). Using the absolute path avoids the "No such file or directory" errors that come from relative invocation.

If *any* provider argument matches `oauth`, `jwt`, `auth-code`, or `authorization-code` (case-insensitive), the script:

1. Reuses `<project-name>/tmp/connector-choices/http.json` if the agent already picked HTTP in Step 3, otherwise runs `get_latest_connector.sh mule-http-connector http` and drafts the top row via `pick_connector.sh http <gav>` — HTTP is an unambiguous search, so no user prompt is needed.
2. Inserts a `<dependency>` block before `</dependencies>` in `<project-name>/pom.xml` (with `<classifier>mule-plugin</classifier>`).
3. Is a no-op if the HTTP connector is already present.

**Manual fallback** — also add HTTP connector if: the connector documentation mentions "callback URL" or "redirect URI", or Step 11 `config-detail` shows an `oauth-callback-config` child element. Without HTTP connector the build fails with: `The content of element '<connector>:<connection-provider>' is not complete`.

---

## Step 11: Get Configuration Details

Phase 1 Step 6 already persisted `config-detail` output to `tmp/connector-metadata/<nickname>-config.json`. Read it from there:

```bash
cat tmp/connector-metadata/sfdc-config.json
```

Only re-invoke the CLI if the cache file is missing (which should not happen if Phase 1 ran correctly). **Flag semantics note:** `--name` is the connection provider, `--config-name` is the config:

```bash
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule describe-connector \
  --connector "$(bash scripts/build_gav.sh tmp/connector-versions/sfdc.json)" \
  --type connection-provider \
  --name basic-connection \
  --config-name sfdc-config \
  --output json
```

**Response shape** (same `attributes` + `childElements` pattern):

```json
{
  "name": "sfdc-config",
  "prefix": "salesforce",
  "elementName": "sfdc-config",
  "attributes": [ { "attributeName": "name", "required": true } ],
  "childElements": [
    { "paramName": "expirationPolicy", "prefix": "salesforce", "elementName": "expiration-policy" }
  ],
  "connectionProviders": [
    {
      "name": "basic-connection",
      "prefix": "salesforce",
      "elementName": "basic-connection",
      "attributes": [
        { "attributeName": "username", "required": true },
        { "attributeName": "password", "required": true },
        { "attributeName": "securityToken", "required": true }
      ],
      "childElements": [
        { "paramName": "reconnection", "prefix": "mule", "elementName": "reconnection" }
      ]
    }
  ]
}
```

**Check BOTH attributes AND childElements** of the selected connection provider:

```bash
jq '.connectionProviders[0].childElements[] | select(.paramName == "oauthCallbackConfig")' tmp/connector-metadata/sfdc-config.json
```

**Connection providers use one of two patterns:**

1. **Attributes pattern** (e.g., Salesforce basic-connection):

   ```xml
   <salesforce:basic-connection
       username="${salesforce.username}"
       password="${salesforce.password}"
       securityToken="${salesforce.securityToken}" />
   ```

2. **Child elements pattern** (e.g., Slack OAuth):

   ```xml
   <slack:slack-auth-connection>
       <slack:oauth-authorization-code
           consumerKey="${slack.consumerKey}"
           consumerSecret="${slack.consumerSecret}" />
   </slack:slack-auth-connection>
   ```

**When generating XML:** if `attributes` has items, use attributes on the connection element; if `attributes` is empty but `childElements` has items, use nested child elements. Never hardcode structure — always use the metadata.

---

## Step 12: Create Configuration Files

Based on Step 11 metadata, create configuration files.

**`src/main/resources/config.yaml`** — extract required attributes and child-element parameters; emit placeholders:

```yaml
salesforce:
  username: "user@example.com"
  password: "password"
  securityToken: "token"

slack:
  consumerKey: "your-consumer-key"
  consumerSecret: "your-consumer-secret"
```

**Configuration XML** — structure driven entirely by metadata:

```xml
<configuration-properties file="config.yaml" />

<salesforce:sfdc-config name="salesforceConfig">
    <salesforce:basic-connection
        username="${salesforce.username}"
        password="${salesforce.password}"
        securityToken="${salesforce.securityToken}" />
</salesforce:sfdc-config>

<slack:config name="slackConfig">
    <slack:slack-auth-connection>
        <slack:oauth-authorization-code
            consumerKey="${slack.consumerKey}"
            consumerSecret="${slack.consumerSecret}" />
        <slack:oauth-callback-config
            listenerConfig="HTTP_Listener_config"
            callbackPath="/slack/callback"
            authorizePath="/slack/authorize" />
    </slack:slack-auth-connection>
</slack:config>

<http:listener-config name="HTTP_Listener_config">
    <http:listener-connection host="0.0.0.0" port="8081" />
</http:listener-config>
```

**Generate ALL `childElements[]` entries from metadata** — the connection provider's `elementName`, the `attributes[]` array, and **every** `childElements[]` entry. For OAuth connectors, `oauth-callback-config` requires a `listenerConfig` attribute referencing an `http:listener-config`. **Missing required childElements = build failure.**

---

## Step 13: Get Operation / Source Details

For each operation the flow will call, retrieve metadata:

```bash
bash scripts/describe_connector.sh sfdc --type operation --name query
```

**Response shape** (same `attributes` + `childElements` pattern as `config-detail`):

```json
{
  "name": "query",
  "prefix": "salesforce",
  "elementName": "query",
  "attributes": [
    { "attributeName": "config-ref", "required": true },
    { "attributeName": "target" },
    { "attributeName": "targetValue", "defaultValue": "#[payload]", "expressionRequired": true }
  ],
  "childElements": [
    { "paramName": "salesforceQuery", "prefix": "salesforce", "elementName": "salesforce-query", "required": true }
  ]
}
```

**For event-driven triggers** (the Step 5 selected trigger is a connector source, not built-in Scheduler or generic HTTP Listener), also retrieve source details:

```bash
bash scripts/describe_connector.sh sfdc --type source --name replay-topic-listener
```

Same `attributes` + `childElements` structure. Always include ALL `required: true` attributes and child elements.

The script also writes `tmp/connector-errors/<nick>.<op>.json` (per-op error subset) and the Step 4 invocation populated `tmp/connector-errors/<nick>.json` (connector-wide union). The error types in those files are the ONLY `NS:ID` strings allowed in `<on-error-propagate type="...">` and `<on-error-continue type="...">` at Step 14. Do NOT invent identifiers from connector vocabulary — `SFTP:FILE_NOT_FOUND` is not real; the actual name is `SFTP:FILE_DOESNT_EXIST`.

**`<raise-error>` has a stricter rule:** it can only throw `MULE:*` errors or custom namespaces like `APP:*` — never connector namespaces (e.g. `EC2:*`, `SFTP:*`, `SALESFORCE:*`). Connector error types can be *caught* in `<on-error-*>` handlers but not *raised*. If you need to raise a retry-exhausted error, use `<raise-error type="MULE:RETRY_EXHAUSTED">`, not `<raise-error type="EC2:RETRY_EXHAUSTED">`. The Step 16 validator enforces both rules mechanically.

**Generate operation XML (example):**

```xml
<salesforce:query config-ref="salesforceConfig">
    <salesforce:salesforce-query>
        SELECT Id, Name, Amount, StageName
        FROM Opportunity
        WHERE StageName = 'Closed Won' AND CloseDate = TODAY
    </salesforce:salesforce-query>
</salesforce:query>
```

---

## Step 14: Generate Complete Flow

Generate the complete flow in `src/main/mule/<project-name>.xml` using metadata from Steps 10, 12. Do NOT use hardcoded structures.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
        http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
        http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd
        http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">
    <!-- One namespace URI + XSD URL pair per <dependency> in pom.xml. Do not include doc or xsi. -->

    <configuration-properties file="config.yaml" />

    <salesforce:sfdc-config name="salesforceConfig">
        <salesforce:basic-connection
            username="${salesforce.username}"
            password="${salesforce.password}"
            securityToken="${salesforce.securityToken}" />
    </salesforce:sfdc-config>

    <flow name="integration-flow">
        <scheduler>
            <scheduling-strategy>
                <fixed-frequency frequency="300000"/>
            </scheduling-strategy>
        </scheduler>

        <salesforce:query config-ref="salesforceConfig">
            <salesforce:salesforce-query>
                SELECT Id, Name, Amount FROM Opportunity WHERE StageName = 'Closed Won'
            </salesforce:salesforce-query>
        </salesforce:query>

        <ee:transform>
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
payload]]></ee:set-payload>
            </ee:message>
        </ee:transform>
    </flow>
</mule>
```

**`xsi:schemaLocation` construction rule:**

Include in `xsi:schemaLocation` exactly one entry for each **module or connector namespace that has a matching `<dependency>` in `pom.xml`** (core, ee/core, and each connector — `http`, `salesforce`, `db`, `anypoint-mq`, etc.). Each entry is the namespace URI followed by the URL of its XSD, separated by whitespace.

**Namespaces that must NOT appear in `xsi:schemaLocation` (closed list):**

| Namespace | `xmlns:*` declaration | Why it's excluded from `schemaLocation` |
|---|---|---|
| `doc` (`http://www.mulesoft.org/schema/mule/documentation`) | Required when any `doc:name` / `doc:description` is used (Step 15) | No XSD exists at that URL. `doc:*` attributes are accepted by `mule-core` via `anyAttribute`. Adding a schemaLocation entry makes `mvn clean package` fail at `process-classes` with `Can't resolve …/mule-documentation.xsd`. |
| `xsi` (`http://www.w3.org/2001/XMLSchema-instance`) | Required to use the `xsi:schemaLocation` attribute itself | `xsi` is a W3C standard namespace, not a Mule schema. |

**Namespace ↔ dependency parity:** if a namespace is declared via `xmlns:X` but has no matching `<dependency>` in `pom.xml`, the correct fix is to **add the dependency or remove the namespace** — not to add a schemaLocation entry that points at a non-existent XSD. Same failure mode as `mule-documentation.xsd` above, different root cause; applies to `mule-scripting`, `mule-objectstore`, `mule-validation`, `mule-http` when those namespaces are declared without their connector dep.

**Generation rules:**

- Use exact `elementName` from metadata for all tags
- Use exact `attributeName` from metadata for all attributes
- Include every `required: true` attribute and child element
- Use the correct namespace prefix from metadata
- Reference `config-ref` names from Step 12
- **Generate child elements in the exact order of the `childElements[]` array** — XSD schemas enforce strict sequencing
- **Do not add wrapper elements that are not in metadata** (e.g., use `<reconnect>` not `<reconnection-strategy><reconnect>`)
- Place reconnection at the config connection level, not operation level (unless metadata explicitly includes it there)
- Build `xsi:schemaLocation` from the module/connector `<dependency>` list in `pom.xml`; never include `doc` or `xsi`. See the rule block above.

---

## Step 15: Add `doc:name` and `doc:description` to Canvas-Visible Elements

Every XML element that appears as a visible node on the flow canvas MUST have `doc:name` and `doc:description` attributes. `doc:description` is displayed as the label text on the canvas node (overriding `doc:name` when present), so keep it concise and meaningful.

**Prerequisite — namespace declaration:**

Any use of a `doc:*` attribute requires `xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"` on the `<mule>` root (see Step 14). If it is missing, every `doc:name` triggers `The prefix "doc" for attribute "doc:name" associated with an element type "..." is not bound`. The fix is to add the `xmlns:doc` attribute — and, per Step 14's `xsi:schemaLocation` construction rule, **not** to add `mule-documentation` to `xsi:schemaLocation`.

Infer descriptions from the `description` field returned by `config-detail`, `operation-detail`, and `source-detail` metadata, the XML structure and element purpose, flow comments, and the overall integration context.

**Rules:**

- Human-readable sentences that explain the element's purpose in *this* integration, not generic documentation
- **Max 125 characters** — keeps labels readable on the canvas
- Active voice; be specific about what the element does
- Include relevant details: endpoints, object types, field names, scheduling intervals
- Add `doc:name` as a short label alongside `doc:description`

**Add `doc:name` and `doc:description` to these canvas-visible element types:**

| Element Type | Examples |
| --- | --- |
| **Flows/sub-flows** | `<flow>`, `<sub-flow>` |
| **Sources/triggers** | `<http:listener>`, `<scheduler>`, `<salesforce:modified-object-listener>` |
| **Operations/processors** | `<logger>`, `<set-variable>`, `<set-payload>`, `<ee:transform>`, `<http:request>`, `<salesforce:query>`, `<flow-ref>`, any connector operation |
| **Scopes/containers** | `<choice>`, `<scatter-gather>`, `<round-robin>`, `<first-successful>`, `<foreach>`, `<until-successful>`, `<parallel-foreach>`, `<try>` |
| **Branches/routes** | `<when>`, `<otherwise>`, `<route>` |
| **Global configs** | `<salesforce:sfdc-config>`, `<http:listener-config>`, `<configuration-properties>` |

**Do NOT add `doc:description` to inner property elements** — these aren't rendered on the canvas:

- `<scheduling-strategy>`, `<fixed-frequency>`, `<cron>`
- `<http:body>`, `<http:headers>`, `<http:query-params>`
- `<reconnection>`, `<reconnect>`
- `<non-repeatable-stream>`, `<repeatable-in-memory-stream>`
- Operation-specific child content elements (e.g., `<salesforce:salesforce-query>`, `<slack:chatpost-message-content>`)
- Transform inner elements (`<ee:message>`, `<ee:set-payload>`, `<ee:variables>`, `<ee:set-variable>`)

**Example — after (with doc:name and doc:description):**

```xml
<flow name="contact-sync-flow"
    doc:name="Contact Sync Flow"
    doc:description="Receives HTTP requests and syncs modified Salesforce contacts to Slack">

    <http:listener config-ref="httpConfig" path="/contacts" allowedMethods="GET"
        doc:name="HTTP GET /contacts"
        doc:description="Receives incoming HTTP GET requests on the /contacts endpoint" />

    <salesforce:query config-ref="salesforceConfig"
        doc:name="Query modified contacts"
        doc:description="Queries Salesforce for Contact records modified since the last sync">
        <salesforce:salesforce-query>
            SELECT Id, Name, Email FROM Contact WHERE LastModifiedDate > :lastSync
        </salesforce:salesforce-query>
    </salesforce:query>

    <choice
        doc:name="Contacts found?"
        doc:description="Routes processing based on whether any modified contacts were returned">
        <when expression="#[sizeOf(payload) > 0]"
            doc:name="Has contacts"
            doc:description="Processes each contact when results are not empty">
            <foreach
                doc:name="For each contact"
                doc:description="Iterates through each modified contact to send to Slack">
                <ee:transform
                    doc:name="Map to JSON"
                    doc:description="Transforms Salesforce Contact into a simplified JSON structure with id, name, and email">
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
payload map { id: $.Id, name: $.Name, email: $.Email }]]></ee:set-payload>
                    </ee:message>
                </ee:transform>

                <slack:create-chatpost-message config-ref="slackConfig"
                    doc:name="Post to Slack"
                    doc:description="Sends the transformed contact data as a message to the configured Slack channel">
                    <slack:chatpost-message-content>#[payload]</slack:chatpost-message-content>
                </slack:create-chatpost-message>
            </foreach>
        </when>
        <otherwise
            doc:name="No contacts"
            doc:description="Handles the case when no modified contacts are found">
            <logger level="INFO" message="No contacts found"
                doc:name="Log no contacts"
                doc:description="Logs that no modified contacts were found in this request" />
        </otherwise>
    </choice>
</flow>
```

---

## Step 16: Build and Verify

### Pre-build validation

As the FIRST tool call of the build response, run:

```bash
bash <skill-dir>/scripts/validate_before_build.sh ./<project-name>
```

The validator runs three static checks (error-type whitelist, namespace↔dependency parity, canonical XSD URL shape) and exits 1 on any violation. If it fails, fix the reported issue (revisit Step 14), re-run the validator, and only proceed to `mvn clean package` after it exits 0. This preserves the one-command-per-response discipline — validator and mvn stay in separate responses.

```bash
cd <project-name>
mvn clean package
```

Success: `target/<project-name>-1.0.0-SNAPSHOT-mule-application.jar`.

**Build-then-verify protocol (do NOT skip steps):**

1. Emit `mvn clean package` as the **only** tool call in this response. Do not include a completion signal, a follow-up `ls`, or any other tool call alongside it. Stop and wait for the build output.
2. You MUST wait until the mvn clean package succeeds. Do NOT make any assumptions about build completion. The terminal output is the ONLY source of truth.
2. Read the output:
    - If the last line block contains `BUILD SUCCESS`, proceed to Step 17 (cleanup) **in a new response**.
    - If the last line block contains `BUILD FAILURE`, find the `[ERROR]` line beginning `Failed to execute goal ...`, diagnose the root cause, edit the offending file (revisiting the relevant earlier Step — e.g. Step 14 for XML structure, Step 15 for documentation attributes and namespaces), and return to step 1 of this protocol. MUST follow the "Best Practices" section for diagnosing the issue and applying the correct fix. Never assume a solution. ALWAYS reference the connector metadata sources and operations under tmp/ folder as your source of truth.

**After any `<write_to_file>` or `<replace_in_file>` on `pom.xml`, on flow XML, or on config XML, you MUST re-run `mvn clean package` before declaring completion.** Editing without re-verifying silently ships a broken build.

---

## Step 17: Clean Up Workspace `tmp/`

**Pre-condition:** The immediately preceding response must be a build response (per Step 16) whose returned output contains `BUILD SUCCESS`. If this is not true, do NOT enter Step 17 — go back to Step 16.

The workspace-relative `tmp/` directory carries Phase 1 → Phase 2 coordination state — `tmp/mule-dev-env.json`, `tmp/connector-choices/`, `tmp/connector-versions/`, `tmp/connector-metadata/`, `tmp/connector-errors/`, plus the `tmp/mule-dev-*-XXXXXX` scratch files written by `get_latest_connector.sh` and `describe_connector.sh`. Once the build passes those files have served their purpose — they exist only so steps can hand state to each other, not as artifacts the user needs.

Remove the directory in its own response, as the only tool call:

```bash
rm -r tmp/
```

**Discipline:**

- Delete only `tmp/` at the workspace root.

---

## Step 18: Declare Completion

**Pre-condition:** The two preceding responses must be (a) a build response (per Step 16) returning `BUILD SUCCESS`, immediately followed by (b) a cleanup response (per Step 17) that ran `rm -r tmp/`. If either is missing, do NOT enter Step 18 — go back to whichever step is missing. You HAVE to clean up the tmp/ folder no matter the attemps succeed or fail at the end.

**Discipline:**

- **The completion signal is the ONLY tool call in this response.** Do not run `mvn` here. Do not add follow-up shell commands. The build was already executed and verified in the previous response.
- **Do not declare completion after a `BUILD FAILURE`, even if you believe the subsequent edit fixes it.** Re-run `mvn clean package` in its own response (Step 16), observe `BUILD SUCCESS`, then declare completion in the next response.
- **Do not declare completion if the most recent build was never actually executed** (e.g., the command was shown but no result came back). Re-run it in its own response and wait.

**Completion message content — keep it tight.** The user can see the files and the build log. The completion message is evidence that the build passed, not a marketing document. Include exactly these, and nothing else:

1. The successful build artifact path: `target/<project-name>-1.0.0-SNAPSHOT-mule-application.jar`
2. One sentence naming the integration (what it does, e.g. "Polls S3 every 5s and publishes new-object events to a JMS queue").
3. The `config.yaml` keys the user still needs to fill in (credentials, bucket names, queue names) — as a short bullet list. This is the only information that is not already visible on disk.

Do **not** include: lengthy "Features Implemented" sections, redacted JSON payload examples, "Next Steps" (the user will deploy when they're ready), or recap tables.

---

## Best Practices

**1. Dynamic connector versions.** See Step 3's "Version source-of-truth rule" for the full mandate.

- ✅ Phase 1: `get_latest_connector.sh mule-salesforce-connector sfdc` → list → `pick_connector.sh sfdc <gav>` → draft at `tmp/connector-choices/sfdc.json`
- ✅ Phase 2: `commit_connectors.sh` (first action of Step 8) → `build_deps.sh` for the `dx mule project create --dependencies` string, or `build_gav.sh tmp/connector-versions/<name>.json` for a single GAV elsewhere
- ❌ Hardcoded literal: `com.mulesoft.connectors:mule-salesforce-connector:10.20.0`
- ❌ Pasted from `references/connector-catalog.md` (snapshot only — drifts)
- ❌ Search term alone as the GAV: `salesforce`

**2. Metadata-driven XML generation.** Never manually write XML. Always use metadata from `operation-detail`, `config-detail`, `source-detail`:

- `attributes` → XML attributes on the tag (use `attributeName` verbatim)
- `childElements` → nested XML elements (use `prefix:elementName` as the tag)
- Always include every `required: true` attribute and child element
- Optional entries may be omitted unless specifically needed
- `description` → understand what the parameter does
- `allowedValues` → constrain values
- `defaultValue` → skip if acceptable

**3. System-specific connectors first, every time.** Always search Exchange for a dedicated connector before falling back to HTTP — and "before" means literally before, not "before I type my decision". The skill's discipline is that a Phase-1 draft in `tmp/connector-choices/` (or the post-commit pin in `tmp/connector-versions/`) is the only evidence that allows declaring "system X is covered"; the helper script having exited 1 is the only evidence that allows declaring "no dedicated connector, falling back to HTTP".

**4. Validate metadata before generation.** Use `describe-connector` for features, `config-detail` / `operation-detail` / `source-detail` for exact specs.

---

## Common Integration Patterns

**#1 HTTP API → Query → Response:** http:listener → salesforce:query → ee:transform → response (Components: HTTP + Salesforce/Database)

**#2 Scheduled Sync → Query → Transform → Notification:** scheduler → salesforce:query → ee:transform → slack:post-message (Components: Scheduler + Salesforce + Slack)

**#3 Scheduled Sync → Query → Transform → Batch Insert:** scheduler → query → ee:transform → foreach → db:insert (Components: Scheduler + Source System + Database)

**#4 Event listener → Transform → Downstream system:** `<connector>:<event-source>` → ee:transform → target-connector operation (Components: Source System with native listener + Target System). This pattern shines when the source connector exposes a real event source in `sources[]` — use that instead of polling via Scheduler.

---

## Troubleshooting

**JAVA_HOME not set:** `export JAVA_HOME=$(/usr/libexec/java_home -v 11)`

**anypoint-cli-v4 not found:** `npm install -g @mulesoft/anypoint-cli-v4`

**DX plugin not found:** `npm install -g @salesforce/anypoint-cli-dx-mule-plugin`

**Connector not found:** check spelling · try `mule-<name>-connector` and `mule4-<name>-connector` · verify Mule 4 compatibility.

**Wrong connector selected:** use specific search terms (`mule-http-connector`, not `http`). `scripts/get_latest_connector.sh` scores by token overlap and requires at least one token match — a bogus search will exit 1 rather than return a random result.

**Runtime path required:** first use of `dx mule describe-connector` or related commands prompts for runtime location. The path is saved to `~/.mule-dx/config.json`.

**Database driver missing:** if Step 6b didn't record `tmp/connector-choices/db-driver.json`, return to Step 6b to make the choice (with prompts where the provider is `generic`/`data-source`/`derby`). If the sidecar exists but `pom.xml` is missing the entries, return to Step 9 — it reads that file and applies every entry as a `<dependency>` + `<sharedLibrary>` pair. Do not invent a driver GAV at Step 9.

**`The mule application does not contain the following shared libraries: [<artifactId>:<groupId>]`:** the `<dependency>` block is present but the matching `<sharedLibrary>` block inside `mule-maven-plugin` is either missing or has a mismatched `groupId`/`artifactId`. Every driver dependency needs both; see Step 9.

**Derby driver layout:** see `references/jdbc-drivers.md`. Derby 10.15+ split into multiple artifacts (`derby` + `derbyshared` + `derbytools` for embedded; `derbyclient` + `derbyshared` for network client), so the `<sharedLibrary>` list has multiple entries, not one.

---

## Quick Reference

`<skill-dir>` below is the absolute path you were given in the "skill is now active" message. Use it consistently — do not construct relative `../scripts/...` paths.

```bash
# Step 1: validate toolchain (CLI, DX plugin, Java 11+, Mule runtime presence) - Validation-only
bash <skill-dir>/scripts/validate_prerequisites.sh

# Step 3: connector search — list, decide, draft (one loop per system; search
# EVERY named system including mid-market SaaS; don't pre-judge as "no connector")
bash <skill-dir>/scripts/get_latest_connector.sh <search-term> [<nickname>]   # prints ranked GAVs to stdout
# ... agent reads list, decides (or AskUserQuestion for real variant ambiguity), then:
bash <skill-dir>/scripts/pick_connector.sh <nickname> <groupId:assetId:version>   # drafts to tmp/connector-choices/

# Step 4: describe connectors (Phase 1 — wrapper saves JSON + echoes sources[] digest)
bash <skill-dir>/scripts/describe_connector.sh <nickname>   # one per connector

# Step 6: connection-provider detail (Phase 1 — also cached for Phase 2).
# Flag semantics: --name = connection provider, --config-name = config name.
GAV_A="$(bash <skill-dir>/scripts/build_gav.sh tmp/connector-choices/a.json)"
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule describe-connector --connector "$GAV_A" \
  --type connection-provider --name <prov> --config-name <name> --output json \
  > tmp/connector-metadata/a-config.json

# Step 8: promote drafts to pinned versions, then create the real project (Phase 2)
bash <skill-dir>/scripts/commit_connectors.sh   # tmp/connector-choices/ → tmp/connector-versions/
MULE_VERSION=$(jq -r '.mule_version' tmp/mule-dev-env.json)
NODE_NO_WARNINGS=1 anypoint-cli-v4 dx mule project create <name> \
  --group-id com.example \
  --mule-version "$MULE_VERSION" \
  --dependencies "$(bash <skill-dir>/scripts/build_deps.sh)" \   # reads every tmp/connector-versions/*.json pin
  --skip-environment   # scratch projects don't need environment resolution

# Step 10: OAuth → HTTP defensive check (only when Step 6 chose OAuth/JWT/auth-code
# or the trigger is HTTP Listener)
bash <skill-dir>/scripts/maybe_add_http_connector.sh --project ./<name> "<provider1>" "<provider2>"

# Step 13: operation / source details (Phase 2 — wrapper saves JSON + caches errorTypes)
bash <skill-dir>/scripts/describe_connector.sh <nickname> --type operation --name <op>
bash <skill-dir>/scripts/describe_connector.sh <nickname> --type source    --name <src>

# Step 16: pre-mvn validation — error-type whitelist + namespace↔dep parity + XSD shape
bash <skill-dir>/scripts/validate_before_build.sh ./<project>
```

| Pre-mvn validation | `bash <skill-dir>/scripts/validate_before_build.sh ./<project>` |

---
