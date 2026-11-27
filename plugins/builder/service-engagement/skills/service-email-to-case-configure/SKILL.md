---
name: service-email-to-case-configure
description: "Use to configure Salesforce Email-to-Case headlessly via the Metadata API. Reads CaseSettings, applies the emailToCase config with a Metadata CRUD update, and verifies by re-reading. Use this instead of generic CaseSettings metadata CRUD for any Email-to-Case task. Also the entry point for attaching an Agentforce agent to Email-to-Case: configures the E2C base, then delegates agent creation and channel wiring. TRIGGER on set up/configure Email-to-Case, enable E2C routing addresses, add a routing address, turn HTML email, email drafts, word count or other Email-to-Case defaults on or off (opt out of the default toggles), or E2C with an Agentforce agent. DO NOT TRIGGER for the interactive Easy Setup wizard, On-Demand E2C only, general Case/web-to-case setup, or an agent with no E2C involved."
metadata:
  version: "1.1"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "service-agentforce-channel-configure"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.9"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck: "(OrgPermissions.HasEmailToCase) && (UserPermissions.CustomizeApplication)"
---

# Configure Email-to-Case (dispatch)

Configure Salesforce Email-to-Case entirely through the project-codey `dispatch` / `dispatch_readonly` tools (no Setup UI, no `sf` CLI for org calls, except the optional Agentforce probe, whose `sf` alias must point at the org the server is bound to). The skill builds a `CaseSettings` source file for the desired `emailToCase` state, applies it in **two phases** (the full `emailToCase` block + Support Settings, then routing addresses; a single write fails on a fresh org), and verifies by re-reading. `scripts/apply-casesettings.py` makes **no org calls**: it prints each request for you to dispatch, validates the response you save, and builds the next write (see Dispatch protocol).

**Entry modes.** A direct user and an orchestrator (`delegationFrom` set, with an `intent`) run the same Workflow; what the `intent` or first message already states is not asked again. Pre-scan, the single confirmation, wording by `discoveryMode`, and the hand-back are in `references/onboarding-delegated-run.md`: read it at step 1.

## How delegation is handled

<!-- BEGIN delegation-pointer (managed by stamp_delegation_boilerplate.py -- do not edit by hand) -->

### Service-Onboarding delegation

When `delegationFrom` is set to service-onboarding, fetch and follow
[the Service-Onboarding delegation guidelines](references/_vendored/service-onboarding-delegation-guidelines.md) before acting — it is the single
source of truth, identical across every service-onboarding delegate. When it is absent, ignore this
and run as a normal standalone conversation.

<!-- END delegation-pointer -->

---

## Scope

- **In scope**: Enabling Email-to-Case org-wide and setting its toggles; creating `EmailToCase`, `Outlook`, and `GmailOAuth` routing addresses; applying the change to the org the dispatch server is bound to; verifying by re-reading.
- **Out of scope**:
  - **`E2cEasy` routing addresses** — created only through the Service Easy Setup wizard, not the Metadata API; route the user there.
  - Choosing or authenticating the org: the skill touches only the org the project-codey MCP server is bound to and never handles passwords or tokens. To target another org the user reconfigures the server.
  - Case object schema, layouts, assignment rules, or Web-to-Case.
  - Creating a queue or an Org-Wide Email Address, verifying a mailbox, or forwarding mail: the user does these (see After setup).
  - Editing or deleting an existing routing address (new addresses are appended).

---

## Attaching an Agentforce service agent (delegation)

When the user wants an Agentforce Service Agent to answer these emails, configure the Email-to-Case base (the Workflow below), then delegate; this skill never creates or modifies agents. **Before delegating, run `scripts/check-agent-email-capability.sh <target-org-alias>`**. Exit **3** means the org is not entitled: **stop, tell the user, and configure the plain base only.** Any other non-zero means the org is unreachable. On exit **0**, delegate agent creation to `agentforce-generate` and wiring to `service-agentforce-channel-configure` Branch C. Details: `references/agent-delegation.md`.

---

## Dispatch protocol

Every org call is a project-codey tool call that **you** make; `scripts/apply-casesettings.py` never touches the org. The loop is always the same:

1. Run `python3 scripts/apply-casesettings.py requests <kind> ...` (or a `phase-a` / `phase-b` command). It prints `{"requests": [...]}` or `{"request": {...}}`. Each request names the `tool` (`dispatch_readonly` for GET, `dispatch` for the PUT), `method`, `path`, and `query_params` or `body`.
2. Make **exactly that call**: copy `path`, `query_params`, and `body` verbatim, never edit the `xmlRep`, and use `dispatch` only when the request says so.
3. Save the tool's result **verbatim** to a file (the `{status_code, body}` JSON, or the path the tool saved it to) and pass it to the next subcommand.
4. If a subcommand exits non-zero, relay its stderr to the user and stop or re-prompt as it says.

| Subcommand | Use |
|---|---|
| `requests org` → `gate --org F [--confirm-production]` | Production-org verdict; non-zero on production without confirmation and **always** when the org type is unreadable. |
| `requests settings` → `read --response F` | The current `CaseSettings`. |
| `requests lookups --input F --current F ...` | User/queue validation queries; pass the results on as `--users F` / `--queues F`. |
| `phase-a`, `phase-b` | Build the PUT request. `phase-b` may print `{"skip": true}` when there is nothing new to add. |
| `check-write --response F` | Validates a PUT result. Run it after **every** write. |
| `verify --initial F --after F` | Preservation guard + verified summary; pass the same flags and lookup files as `phase-a`. |
| `requests cases` / `messages` → `cases` | Act 3 proof. |

---

## Required Inputs

Gather or infer before applying. Ask only when a wrong assumption would produce a broken or incorrect result:

- **Target org** — none to collect: dispatch acts on the org the server is bound to. Only the optional Agentforce probe needs that org's `sf` CLI alias.
- **Routing address(es)** — for each: `routingName` (unique label), `addressType` (`EmailToCase` default, or `Outlook` / `GmailOAuth`), `caseOrigin`, and `casePriority`. The platform rejects the address if `caseOrigin` or `casePriority` is missing, so treat all four as required in the source file.
- **Customer-facing email address per routing address** — **take it from the `intent` or the user's message when stated, otherwise ask explicitly for each, in address order**; never guess, default, or reuse from earlier context. Not stored in the source file — passed at apply time via `--routing-email` (one per address that takes an email — **`Outlook` addresses take none**; the script fails closed on a count mismatch).
- **Support Settings — Default Case Owner & Automated Case User** — preserve-first, never assumed:
  - **Independent, preserved per field.** Each configured field is left untouched; change one only if the user asks (`--overwrite-support-settings`). Ask **only for the field(s) unset**.
  - **For each unset field, use the `intent` or ask** (never assume a default user): Default Case Owner **type** (`User`/`Queue`) + **value** (active Username or Queue DeveloperName) → `--owner-type`/`--owner-value`; Automated Case User **type** (`User`/`System`) — `User` needs a **username**, `System` needs no value → `--automated-type`/`--automated-value` (+ optional `--system-user-email` for System when the org's automated user doesn't exist yet).
  - **If a value is invalid**, the script fails: get a valid one and re-run; never guess. If the user says "use me", ask for their exact username.
- **Case defaults per address** (optional) — `createTask`, `saveEmailHeaders`, and the opt-in per-address Default Case Owner (`caseOwner` + `caseOwnerType`, both or neither; see step 6). Omitted by default so cases fall to the org Default Case Owner / assignment rules.
- **Org-level toggles** (optional) — set only if the user asks, beyond the defaults in step 4 (which apply to a fresh setup only). They live in the `emailToCase` section (`enableHtmlEmail`, `notifyOwnerOnNewCaseEmail`, `enableE2CDeduplicateAttachments`, `showWordCountInComposer`, `enableE2CSourceTracking`, `overEmailLimitAction`, `unauthorizedSenderAction`) or at the top level (`enableDraftEmails`).

Defaults: `enableEmailToCase` and `enableOnDemandEmailToCase` default to `true` (both required — On-Demand before routing addresses); `addressType` defaults to `EmailToCase`. Support Settings have **no default** — preserved if set, otherwise elicited (never assumed).

---

## Workflow

All steps are sequential.

1. **Confirm the org, pre-scan it, and confirm once** — run `requests org` and dispatch it (a failure usually means the server is not connected or bound to the intended org: tell the user and stop). Then run `gate --org <file>`; on production it exits non-zero until confirmed, so pre-scan anyway and re-run it with the flag after the yes. The gate **refuses to mutate a production org** (non-sandbox, non-trial) unless `--confirm-production` is passed, and refuses an org whose type it cannot read even with the flag — enabling Email-to-Case is permanent and org-wide. **Send no write before `gate` succeeds.** Pre-scan (read-only): `requests settings`, dispatch, save as the **initial read** (keep it unchanged until `verify`), `read --response <file>`, and classify it with `references/onboarding-delegated-run.md` §1 (nothing set up / no change / add / override / ask once). Before the first write, ask **one** confirmation for every org type, naming the org and its type, and adding that enabling is permanent only when Email-to-Case is not yet on (§2); on production the same yes covers `--confirm-production`, which you never add before it. No change needed: report, run `verify`, hand back, with no write.

2. **Elicit the routing email(s)** — take the exact customer-facing email for each routing address except `Outlook` ones from the `intent` or the user's message when stated, otherwise ask (never assume or reuse a value). Pass them to every `phase-a` / `phase-b` / `verify` command via `--routing-email`, in source-file order.

3. **Load the template** — read `assets/CaseSettings.settings-meta.xml` for structure and field placement. Its comments are guidance for you; never copy them. Emit only the elements you set, comment-free, as in `examples/CaseSettings-two-addresses.settings-meta.xml`.

4. **Enable the E2C switches, then confirm the optional toggles** — set both `enableEmailToCase` and `enableOnDemandEmailToCase` to `true` (both required; On-Demand must be on before routing addresses can be created — the script enables it in Phase A before Phase B). Then handle the **non-required convenience settings**, which the template turns on by default:

   Enable HTML email (`enableHtmlEmail`), Eliminate duplicate email attachments (`enableE2CDeduplicateAttachments`), Show word count in composer (`showWordCountInComposer`) and Notify case owners on new emails (`notifyOwnerOnNewCaseEmail`) all go inside `<emailToCase>`. Enable Email Drafts (`enableDraftEmails`) is a top-level Support Settings field at the `CaseSettings` root.

   **On a fresh setup, tell the user exactly which will be turned on (in the guided wording of `references/onboarding-delegated-run.md` §3 when `discoveryMode` is `"guided"`) and let them opt out;** an opt-out already in the `intent` is not asked again. Remove any they decline; keep the rest in place (four inside `<emailToCase>`, `enableDraftEmails` at the root). Never enable an optional flag the user didn't agree to. **On an org that already has Email-to-Case, do not apply these defaults:** include only the toggles the user chose to change. Confirmed toggles apply in Phase A.

5. **Pick the correct surface per routing address** — for each address, decide by `addressType` using `references/routing_address_reference.md`. If any requested address is `E2cEasy`, stop and route the user to the Service Easy Setup wizard instead of emitting Metadata for it.

6. **Populate routing-address fields** — for each `EmailToCase` / `Outlook` / `GmailOAuth` address, set `addressType`, `routingName`, `caseOrigin`, and `casePriority` (all required; the platform rejects the write without `caseOrigin` or `casePriority`), plus any optional case defaults. An `Outlook` address **must** also set `caseOwner` + `caseOwnerType` (the platform rejects it with "Missing caseOwner") and takes **no** email — the platform rejects `emailAddress` on it. Do **not** put `emailAddress` in the source file (it comes from `--routing-email`), and do **not** set the read-only `emailServicesAddress` or `isVerified`. See `examples/CaseSettings-two-addresses.settings-meta.xml` for a multi-address example.

   **Per-address Default Case Owner is opt-in.** Ask one address at a time whether its cases go to a specific owner or fall to the org Default Case Owner / assignment rules (the default). If the user declines, leave `caseOwner`/`caseOwnerType` out of the source file; if they opt in, set **both**.

7. **Determine Support Settings (Default Case Owner + Automated Case User)** — from the step 1 read, inspect `defaultCaseOwner` / `defaultCaseUser` / `useSystemUserAsDefaultCaseUser`. **When the user names a value, write it into the source file** (`defaultCaseOwner` + `defaultCaseOwnerType`; `defaultCaseUser`, or `useSystemUserAsDefaultCaseUser` + optional `systemUserEmail`); the script also accepts these as flags. **Leave each field the org already has as-is** (override only if the user asks, with `--overwrite-support-settings`). For a field unset **and** not named in the `intent` or by the user, ask; never assume a user.

8. **Validate the source file** — run `python3 scripts/validate-casesettings.py [--no-addresses-ok] <source-file>` (the flag for a toggle-only file) and fix any errors.

9. **Apply to the org** — with `<flags>` = `--input <source-file> --routing-email <email-1> [--routing-email <email-2> ...]` (exactly one per non-`Outlook` routing address, in document order) plus, **only when Support Settings are not already configured** (step 7), `[--owner-type User|Queue --owner-value <username-or-queue-devname>] [--automated-type User --automated-value <username> | --automated-type System [--system-user-email <email>]]` (add `--overwrite-support-settings` only if the user asked to change a configured field):
   1. `requests lookups --current <initial-read> <flags>`; dispatch each printed request (it is empty when there is nothing to validate) and keep the results as `--users` / `--queues`.
   2. `phase-a --current <initial-read> <flags> [--users F] [--queues F]` → dispatch its `request` (a PUT), then `check-write`. Keep its `summary`.
   3. `requests settings`, dispatch, save as the **fresh read** → `phase-b --current <fresh-read> <flags> [--users F] [--queues F]` → if it prints a `request`, dispatch it and `check-write`; if it prints `skip`, there is nothing to add. Keep its `phaseB` list.
   4. `requests settings`, dispatch, save as the **final read** → `verify --initial <initial-read> --after <final-read> <flags> [--users F] [--queues F]` (the same lookup files as `phase-a`; `verify` re-resolves Support Settings against them).

   If a script command rejects a value, relay it, get a valid one, and re-run from that command. Add `--confirm-production` only after the user's yes (step 1). A failed `check-write` stops the run: report the platform message verbatim (see `references/troubleshooting.md`) and do not re-send an edited payload.

10. **Confirm the result** — check the `verify` output and the kept summaries: `verified.enableEmailToCase` / `verified.enableOnDemandEmailToCase` are `true`, `verified.routingAddressCount` matches the expected count, each `phaseB` entry is `status: created` (or `already_exists`), and `supportSettings.action` is `preserved-existing` / `set-from-input` / `overwrote-existing`. Use `requests settings` + `read` to re-read without writing. When called by an orchestrator, report what was set, what was left as it was, and what remains for the user, then hand control back (`references/onboarding-delegated-run.md` §5).

---

## After setup — post-completion guidance

The items below are **not** workflow steps — present them to the user once setup is confirmed.

### Forwarding (required for real inbound mail)

Always give the user this guidance; it is how inbound mail actually reaches Salesforce:

> Your routing address now has a Salesforce-generated **email services address**. To receive inbound mail, forward mail sent to your customer-facing address (e.g. `support@company.com`) to that address.

### End-to-end proof (Act 3)

Offer once, on a direct run only, to prove that inbound email creates Cases (a live round-trip; skip it if declined); on a delegated run, only if asked. The skill never sends email: the user verifies the address and sends a test email, then a read-only check looks for the Case. Follow `references/end-to-end-proof.md`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Apply in two phases built by `apply-casesettings.py` (PUT to `/headless/metadata`), never a single combined write or a minimal `emailToCase` patch | A single write fails on a fresh org, and only the full `emailToCase` block provisions On-Demand before addresses bind. See `references/apply-mechanics.md`. |
| All org reads and writes go through `dispatch_readonly` / `dispatch`; the only `sf` use is the Agentforce capability probe | The MCP server owns auth and org binding. Do not fall back to the `sf` CLI, SOAP, or a hand-built token if dispatch is unavailable — stop and tell the user. |
| Make each dispatch call exactly as the script printed it, and send no write before `gate` succeeds | The payloads encode the validated two-phase mechanism and the production safety check; an edited `xmlRep` or a skipped gate defeats both. |
| Write only the top-level fields the skill owns; never echo the whole `CaseSettings` record | The platform re-validates every top-level field sent (e.g. Case Feed needs Chatter). Omitted fields keep their values. See `references/apply-mechanics.md`. |
| The customer-facing email must be explicit input (`--routing-email`, from the user or the `intent`), never in the source file and never assumed | Prevents a guessed or stale address from being provisioned. The script fails closed if `--routing-email` count ≠ address count. |
| Support Settings are preserved **per field** if configured; never assumed if not | Each configured field is left untouched (unless `--overwrite-support-settings`); an unset field needs an explicit, org-validated value, or the script fails closed. |
| Automated Case User "System" and a named `defaultCaseUser` are mutually exclusive | `--automated-type System` sets `useSystemUserAsDefaultCaseUser` and must not carry a user value; the platform rejects both. |
| The script reads → patches → updates (append-only for addresses) | Existing routing addresses are preserved; a duplicate `routingName`/`emailAddress` is reported as `already_exists`. New addresses are emitted before existing ones, and a runtime guard fails the run if any existing address is dropped. See `references/apply-mechanics.md`. |
| `EmailToCaseSettings` is never applied directly; `enableEmailToCase` cannot be turned off once on | It is written only as the `emailToCase` child of `CaseSettings`. The platform permanently enables the feature after the first `true` apply; never rely on setting it back to `false`. |
| Production orgs require explicit `--confirm-production`; never add the flag unprompted, and never before the single confirmation of step 1 | Enabling Email-to-Case is permanent and org-wide. The script fails closed on a non-sandbox, non-trial org (and one whose type it can't read) until the user confirms. Sandboxes and trials are exempt. |
| `E2cEasy` addresses must use the Service Easy Setup wizard | The prebuilt `service_case` queue binding and `isVerified` flip are not reproducible through the Metadata API. |

---

## Gotchas

For the full symptom → resolution table (Phase B errors, Case Feed/Chatter, owner half-fills, `GmailOAuth`, the cases proof, toggle placement), read `references/troubleshooting.md`.

---

## Output Expectations

A comment-free `CaseSettings` source file, the applied org state, and the script's JSON summaries.

---

## Reference File Index

| File | When to read / run |
|------|-------------|
| `references/onboarding-delegated-run.md` | Step 1 — pre-scan, single confirmation, guided wording, permission message, hand-back |
| `references/apply-mechanics.md` | Before changing how the script builds or sequences writes |
| `references/troubleshooting.md` | An apply or verify error, or a setting that doesn't behave |
| `references/agent-delegation.md` | Attaching an Agentforce service agent |
| `references/end-to-end-proof.md` | After setup, the optional inbound-email proof |
| `references/routing_address_reference.md` | Steps 5–6 — address fields and `addressType` surface |
| `assets/CaseSettings.settings-meta.xml` | Step 3 — the source-file template |
| `examples/CaseSettings-two-addresses.settings-meta.xml` | Step 6 — multi-address structure |
| `scripts/check-agent-email-capability.sh` | The pre-delegation capability gate |
| `scripts/validate-casesettings.py` | Step 8 |
| `scripts/apply-casesettings.py` | Steps 1, 7, 9, 10 |
