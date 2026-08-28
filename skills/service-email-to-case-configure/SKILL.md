---
name: service-email-to-case-configure
description: "Use to configure Salesforce Email-to-Case in a headless flow via the Metadata API. Reads the current CaseSettings, applies the desired emailToCase configuration with the updateMetadata CRUD call, and verifies by re-reading. Also the entry point when the user wants an Agentforce service agent on Email-to-Case: this skill configures the E2C base, then delegates agent creation and channel wiring. Start here even when no agent exists yet. TRIGGER when the user says set up Email-to-Case, configure email to case, enable Email-to-Case routing addresses, add an email routing address, Email-to-Case Metadata API, or set up Email-to-Case with an Agentforce service agent (attach an agent to an email routing address). DO NOT TRIGGER when the user needs the interactive Service Easy Setup wizard for E2cEasy addresses, when configuring On-Demand Email-to-Case only, for general Case object or web-to-case setup, or when only creating an Agentforce agent with no Email-to-Case involved."
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
  accessCheck:
    - type: "orgPerm"
      value: "OrgPermissions.HasEmailToCase"
    - type: "userPerm"
      value: "UserPermissions.CustomizeApplication"
---

# Configure Email-to-Case (Metadata API)

Configure Salesforce Email-to-Case entirely through the Metadata API (no Setup UI), for headless org configuration. The skill builds a `CaseSettings` source file for the desired `emailToCase` state, then applies it with `scripts/apply-casesettings.py`, which runs `updateMetadata` in **two phases** — the full `emailToCase` block + Support Settings (Phase A), then routing addresses (Phase B) — and verifies by re-reading. Two phases because a single deploy **fails on a fresh org**: On-Demand must be live before an address binds (see Rules / Constraints).

## Scope

- **In scope**: Enabling Email-to-Case org-wide and setting its toggles (full field lists in Required Inputs and step 4); creating `EmailToCase`, `Outlook`, and `GmailOAuth` routing addresses; applying the change to an sf-CLI-authenticated org via `apply-casesettings.py`; verifying by re-reading.
- **Out of scope**:
  - **`E2cEasy` routing addresses** — created only through the Service Easy Setup wizard, not the Metadata API; route the user there.
  - Authenticating the org — the user authenticates out-of-band (e.g. `sf org login web`); the script reuses that session and never handles passwords or tokens.
  - Case object schema, layouts, assignment rules, or Web-to-Case.

---

## Attaching an Agentforce service agent (delegation)

When the user wants an Agentforce Service Agent to answer these emails, configure the Email-to-Case base (the Workflow below), then delegate — this skill never creates or modifies agents.

**Gate on org capability first.** Attaching an agent needs the org entitled for Agentforce Email-to-Case; that entitlement surfaces as the `BotEmailDefinition` metadata type, so probe read-only **before delegating**:

```bash
scripts/check-agent-email-capability.sh <target-org-alias>   # pins describe to the org's API version
```

Exit **3** → not entitled: **stop, tell the user, and configure the plain Email-to-Case base only — make no Agentforce agent or channel-wiring changes.** Any other non-zero is an unreachable org, not "not entitled" — fix auth and re-run. On exit **0**, delegate:

1. **Agent creation → `agentforce-generate`,** omitting the **Service Customer Verification topic** (unsupported on the email channel) and including an **Escalation subagent** so the agent can hand off to a human — on email, escalation transfers the case to a service rep, and without the subagent the agent can't escalate.
2. **Wiring → `service-agentforce-channel-configure` Branch C.**

---

## Required Inputs

Gather or infer before applying. Ask only when a wrong assumption would produce a broken or incorrect result:

- **Target org alias** — the sf CLI alias/username of an already-authenticated org. The script obtains the session with `sf org display` and `sf org auth show-access-token`; it does not log in for you.
- **Routing address(es)** — for each: `routingName` (unique label), `addressType` (`EmailToCase` default, or `Outlook` / `GmailOAuth`), `caseOrigin`, and `casePriority`. The platform rejects the address if `caseOrigin` or `casePriority` is missing, so treat all four as required in the source file.
- **Customer-facing email address per routing address** — **ask explicitly for each, in address order**; never guess, default, or reuse from earlier context. Not stored in the source file — passed at apply time via `--routing-email` (one per address; the script fails closed on a count mismatch).
- **Support Settings — Default Case Owner & Automated Case User** — preserve-first, never assumed:
  - **Independent, preserved per field.** Each configured field is left untouched; change one only if the user asks (`--overwrite-support-settings`). Ask **only for the field(s) unset**.
  - **For each unset field, ask** (never default to the authenticated user): Default Case Owner **type** (`User`/`Queue`) + **value** (active Username or Queue DeveloperName) → `--owner-type`/`--owner-value`; Automated Case User **type** (`User`/`System`) — `User` needs a **username**, `System` needs no value → `--automated-type`/`--automated-value` (+ optional `--system-user-email` for System when the org's automated user doesn't exist yet).
  - **If any value is invalid**, the script fails — get a valid value and re-run; never substitute or guess.
  - Pass `--use-authenticated-user` **only** if the user explicitly asks.
- **Case defaults per address** (optional) — `createTask`, `saveEmailHeaders`, and an optional **per-address Default Case Owner** (`caseOwner` + `caseOwnerType`), **opt-in per address** (see step 6): omitted by default so cases fall to the org Default Case Owner / assignment rules. When set, `caseOwner` (active Username or Queue DeveloperName) must be paired with `caseOwnerType` (`User`/`Queue`); the script validates it against the org, failing closed if absent.
- **Org-level toggles** (optional) — set only if the user asks. Two containers: the **`emailToCase` section** (`enableHtmlEmail`, `notifyOwnerOnNewCaseEmail`, `enableE2CDeduplicateAttachments`, `showWordCountInComposer`, plus `enableE2CSourceTracking`, `overEmailLimitAction`, `unauthorizedSenderAction`), and **top-level Support Settings** (`enableDraftEmails` — plural element name, a sibling of `emailToCase`). See step 4's table for container/UI-label mapping; top-level scalar toggles apply in Phase A.

Defaults: `enableEmailToCase` and `enableOnDemandEmailToCase` default to `true` (both required — On-Demand before routing addresses); `addressType` defaults to `EmailToCase`. Support Settings have **no default** — preserved if set, otherwise elicited (never the authenticated user).

---

## Workflow

All steps are sequential.

1. **Confirm the org (and its type)** — confirm the target org alias is authenticated (`sf org display --target-org <alias>`). The apply script checks the `Organization` row and **refuses to mutate a production org** (non-sandbox, non-trial) unless `--confirm-production` is passed — enabling Email-to-Case is permanent and org-wide. If production, tell the user and confirm before re-running with `--confirm-production`. Sandboxes, scratch orgs, and trials deploy without the flag.

2. **Elicit the routing email(s)** — ask the user for the exact customer-facing email address for each routing address (never assume, default, or carry a value over from earlier). Pass them to the script via `--routing-email` in the order the addresses appear in the source file.

3. **Load the template** — read `assets/CaseSettings.settings-meta.xml` for structure and field placement. Its comments are authoring guidance **for you** — never copy them into the output. Emit only the elements you set; the output must be comment-free, matching `examples/CaseSettings-two-addresses.settings-meta.xml`.

4. **Enable the E2C switches, then confirm the optional toggles** — set both `enableEmailToCase` and `enableOnDemandEmailToCase` to `true` (both required; On-Demand must be on before routing addresses can be created — the script enables it in Phase A before Phase B). Then handle the **non-required convenience settings**, which the template turns on by default:

   | UI label | Field | Container |
   |----------|-------|-----------|
   | Enable HTML email | `enableHtmlEmail` | `emailToCase` |
   | Eliminate duplicate email attachments | `enableE2CDeduplicateAttachments` | `emailToCase` |
   | Show word count in composer | `showWordCountInComposer` | `emailToCase` |
   | Notify case owners on new emails | `notifyOwnerOnNewCaseEmail` | `emailToCase` |
   | Enable Email Drafts | `enableDraftEmails` (top-level `CaseSettings`) | Support Settings |

   **Before enabling these, tell the user exactly which will be turned on and let them opt out** (e.g. "I'll also enable these optional settings: … — let me know if you'd like to skip any."). Remove any the user opts out of; keep the rest in their correct container (four inside `<emailToCase>`, `enableDraftEmails` at the root). Never silently enable these or any other optional flag the user didn't agree to. Confirmed toggles apply in Phase A.

5. **Pick the correct surface per routing address** — for each address, decide by `addressType` using `references/routing_address_reference.md`. If any requested address is `E2cEasy`, stop and route the user to the Service Easy Setup wizard instead of emitting Metadata for it.

6. **Populate routing-address fields** — for each `EmailToCase` / `Outlook` / `GmailOAuth` address, set `addressType`, `routingName`, `caseOrigin`, and `casePriority` (all required — the platform rejects the operation with "Missing caseOrigin"/"Missing casePriority" if either is absent), plus any optional case defaults. Do **not** put `emailAddress` in the source file — it is supplied at apply time via `--routing-email`. Do **not** set the read-only fields `emailServicesAddress` or `isVerified` — the platform manages them. See `examples/CaseSettings-two-addresses.settings-meta.xml` for a complete multi-address example.

   **Per-address Default Case Owner (opt-in).** Ask one address at a time whether cases from *this* address go to a specific owner or fall to the org Default Case Owner / assignment rules (the default) — different addresses can route to different owners. If the user **declines**, leave `caseOwner`/`caseOwnerType` out of the source file entirely (the template ships them commented out). If the user **opts in**, ask for the **type** (`User`/`Queue`) and **value** (active Username or Queue DeveloperName) and set **both** `<caseOwnerType>` and `<caseOwner>` — the platform rejects `caseOwner` without its type. `apply-casesettings.py` validates it against the org and fails closed if absent. Do not guess or reuse the top-level Default Case Owner.

7. **Determine Support Settings (Default Case Owner + Automated Case User)** — run `python3 scripts/apply-casesettings.py --target-org <alias> --input <source-file> --verify-only` and inspect `defaultCaseOwner` / `defaultCaseUser` / `useSystemUserAsDefaultCaseUser`. **When the user names a value, write it into the source file** (`defaultCaseOwner` + `defaultCaseOwnerType`; `defaultCaseUser`, or `useSystemUserAsDefaultCaseUser` + optional `systemUserEmail`) — the scored, versionable artifact; the script also accepts these as flags. **Leave each field the org already has as-is** — omit it and it is preserved (override only if the user asks — then `--overwrite-support-settings`). For a field unset **and** unnamed, ask; never assume the authenticated user (`--use-authenticated-user` only if explicitly asked).

8. **Validate the source file** — run `python3 scripts/validate-casesettings.py <path-to-source-file>` and resolve any reported errors before applying.

9. **Apply to the org** — run:
   ```bash
   python3 scripts/apply-casesettings.py --target-org <alias> --input <source-file> \
       --routing-email <email-for-address-1> [--routing-email <email-for-address-2> ...] \
       [--owner-type User|Queue --owner-value <username-or-queue-devname>] \
       [--automated-type User --automated-value <username> | --automated-type System [--system-user-email <email>]] \
       [--confirm-production]
   ```
   Provide exactly one `--routing-email` per routing address, in document order. Supply the owner/automated flags **only when the org's Support Settings are not already configured** (step 7); if configured, omit them and they are preserved. If the script rejects a value as invalid, relay it, get a valid value, and re-run — never fall back to the authenticated user. **If the script reports production and exits, do not add `--confirm-production` yourself** — confirm with the user first (step 1). The script applies Phase A (support settings + toggles), then Phase B (routing addresses), re-reads to verify, and exits non-zero on any fault.

10. **Confirm the result** — check the JSON summary: `verified.enableEmailToCase` / `verified.enableOnDemandEmailToCase` are `true`, `verified.routingAddressCount` matches the address count, each `phaseB` entry is `status: created` (or `already_exists`), and `supportSettings.action` is `preserved-existing` / `set-from-input` / `set-from-authenticated-user`. Use `--verify-only` to re-read without writing.

Configuration is complete after step 10.

---

## After setup — post-completion guidance

The items below are **not** workflow steps — present them to the user once setup is confirmed.

### Forwarding (required for real inbound mail)

Always give the user this guidance — it is how inbound mail to the customer-facing address actually reaches Salesforce:

> Your routing address now has a Salesforce-generated **email services address**. To receive inbound mail, configure your email system to forward mail sent to your customer-facing address (e.g. `support@company.com`) to that generated services address.

### End-to-end proof (Act 3)

Offer to prove inbound email creates Cases — a live round-trip; skip it if the user declines. The skill never sends email — it orchestrates two human actions, then verifies with SOQL: (1) **Address ownership** — Salesforce emails a confirmation link; `isVerified` flips only when the human clicks it. Tell the user to click it and **wait**. (2) **Send a test email** — ask the user to send one real email from an external mailbox to the routing address's Salesforce-generated **email services address** (not the customer-facing address, which only receives mail once forwarding is configured), report the sender, and **wait**. (3) **Verify with evidence** — then run:

```bash
python3 scripts/apply-casesettings.py --target-org <alias> --verify-cases \
    [--supplied-email <external-sender-address>]
```

Read-only: it queries `Case` where `Origin='Email'` (last 3 days, optionally narrowed by sender) plus the linked incoming `EmailMessage` rows (`Incoming=true`, `ParentId` = the new Case), and exits **non-zero if no matching Case has a linked incoming email** (mail not processed yet — wait and re-run — or address not verified). On success it prints the `Case` + `EmailMessage` evidence with `proven: true`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Apply via `apply-casesettings.py` (two-phase `updateMetadata`), never a plain deploy or a minimal `emailToCase` patch | A single deploy fails on a fresh org; the full `emailToCase` block (not a field-level flip) is what provisions On-Demand before addresses bind. See `references/apply-mechanics.md`. |
| Write only the top-level fields the skill owns; never echo the whole `CaseSettings` record | The platform re-validates every top-level field in the payload (e.g. Case Feed → Chatter); sending only `emailToCase` + `enableDraftEmails` + Support Settings avoids unrelated failures and needs no Chatter prerequisite. Omitted fields keep their values via field-level merge. |
| The customer-facing email must be explicit user input (`--routing-email`), never in the source file and never assumed | Prevents a guessed or stale address from being provisioned. The script fails closed if `--routing-email` count ≠ address count. |
| `CaseSettings` `fullName` is always `Case` | It is an org singleton settings type; the script targets `Case` automatically. |
| Support Settings are preserved **per field** if configured; never assumed if not | Default Case Owner and Automated Case User are independent — each configured field is left untouched (unless `--overwrite-support-settings`), and only an unset field requires an explicit, org-validated value (fails closed otherwise). The authenticated user is used only with `--use-authenticated-user`. |
| Automated Case User "System" and a named `defaultCaseUser` are mutually exclusive | `--automated-type System` sets `useSystemUserAsDefaultCaseUser` and must not carry a user value; the platform rejects both. |
| The script reads → patches → updates (append-only for addresses) | It merges onto current settings, so existing routing addresses are preserved; a duplicate `routingName`/`emailAddress` is reported as `already_exists`. New addresses are emitted **before** existing ones (`updateMetadata` replaces the collection wholesale and would drop an existing address that a new one follows; a runtime guard fails the run if any existing address is dropped). See `references/apply-mechanics.md`. |
| `EmailToCaseSettings` is never applied directly; `enableEmailToCase` cannot be turned off once on | It is written only as the `emailToCase` child of `CaseSettings`. The platform permanently enables the feature after the first `true` apply; never rely on setting it back to `false`. |
| Production orgs require explicit `--confirm-production`; never add the flag unprompted | Enabling Email-to-Case is permanent and org-wide. The script fails closed on a non-sandbox, non-trial org (and one whose type it can't read) until the user confirms. Sandboxes and trials are exempt. |
| Proving inbound Cases is a read-only step the user triggers; the skill never sends email | `--verify-cases` only queries `Case`/`EmailMessage` after the human verified the address and sent a test email. Fails closed until a Case with a linked incoming email exists. |
| `E2cEasy` addresses must use the Service Easy Setup wizard | The prebuilt `service_case` queue binding and `isVerified` flip are not reproducible through the Metadata API. |
| Never write `emailServicesAddress` or `isVerified` | Both are read-only, platform-generated; the script strips them if present. |
| The generated source file contains only the elements being set — **no XML comments** | Template/example comments are authoring guidance, not output. Copying them bloats the file (gold is comment-free) and CLI-example comments with `<placeholder>` tokens can fail XML validation. Put explanation in your chat reply, never in the `.settings-meta.xml`. |

---

## Gotchas

For the full symptom → resolution table (Phase B provisioning errors, Case Feed/Chatter, per-address owner half-fills, `GmailOAuth` conflicts, `--verify-cases` failures, and every toggle-placement pitfall), read `references/troubleshooting.md`.

---

## Output Expectations

Deliverables:
- A `CaseSettings` source file (e.g. `Case.settings-meta.xml`) for the desired `emailToCase` state — toggles and routing-address fields, **without** `emailAddress` (supplied at apply time), read-only fields, or XML comments. Structure follows `assets/CaseSettings.settings-meta.xml`.
- The applied org state from `apply-casesettings.py`, plus its JSON summary (resolved owner, per-address status, verification read).

---

## Reference File Index

| File | When to read / run |
|------|-------------|
| `assets/CaseSettings.settings-meta.xml` | Step 3 — the starting template for the source file |
| `references/apply-mechanics.md` | Read before touching how the script builds or sequences its `updateMetadata` payloads |
| `references/troubleshooting.md` | When the apply or verify step reports an error, or a configured setting doesn't behave — full symptom → resolution table |
| `references/routing_address_reference.md` | Steps 5–6 — routing-address field semantics and the `addressType` surface-selection rule |
| `examples/CaseSettings-two-addresses.settings-meta.xml` | Step 6 — to verify the source-file structure for multiple routing addresses |
| `scripts/check-agent-email-capability.sh` | Attaching an Agentforce service agent — the pre-delegation capability gate (probes for `BotEmailDefinition`) |
| `scripts/validate-casesettings.py` | Step 8 — deterministic structural validation before applying |
| `scripts/apply-casesettings.py` | Step 9 — applies the settings via two-phase `updateMetadata` and verifies |
| `scripts/tests/test_get_session.py` | Run when changing session-token acquisition (`get_session` / `_usable_access_token`) — the unit suite guarding token extraction and API-version resolution |
