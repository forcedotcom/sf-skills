# Data Cloud Feature Readiness

Use this guide when a Data Cloud command fails and you need to decide whether the issue is:
- runtime / plugin setup
- org authentication
- product provisioning
- feature gating
- empty-but-enabled configuration
- a bad table name or wrong probe

The goal is to **detect first, classify second, and guide third** instead of blindly executing a command and surfacing a raw error.

## Core principle

Do **not** treat one failing command as proof that all of Data Cloud is unavailable.

Different command families hit different backend surfaces. A failure in one area can coexist with successful read-only access in another.

Examples:
- `sf data360 doctor` checks the **search-index** endpoint only.
- `sf data360 query describe` checks the **query** plane and requires a real DMO/DLO table name.
- `sf data360 dmo list` checks a **catalog/listing** endpoint.
- `sf data360 activation platforms` checks the **activation destination** surface.

## Recommended first step

Run the shared readiness classifier before mutation-heavy work:

```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o myorg --json
```

For retrieve/query work, only add a table probe when you already know the table name is real:

```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o myorg --phase retrieve --describe-table MyDMO__dlm --json
```

## Signal matrix

| Signal | What it usually means | What to do next | What **not** to assume |
|---|---|---|---|
| `sf data360 man` fails | Runtime/plugin missing | Install or relink the community runtime | Do not debug org features yet |
| `sf org display -o <org>` fails | Org auth missing | Re-authenticate the org | Do not blame Data Cloud |
| `No results.` | Feature is reachable but currently empty | Continue with create/setup flow | Do not say the feature is disabled |
| `This feature is not currently enabled for this user type or org: [CdpXxx]` | Specific module is gated for the current org/user | Guide the user to setup/provisioning/permission review for that module | Do not say the entire product is disabled |
| `Couldn't find CDP tenant ID. Please enable CDP first.` | The **query** plane could not resolve a CDP tenant for that request | Re-check broader readiness with `data-space list`, `dmo list`, and `doctor`; then retry with a known table if appropriate | Do not treat this as universal proof that all Data Cloud endpoints are off |
| `NOT_FOUND: DataModelEntity ... is not found` | The table name is not queryable in that org | Pick a real DMO/DLO from `dmo list`, `dlo list`, or `dmo get` | Do not say the whole query feature is unavailable |
| `Request failed` | Generic endpoint failure or inconclusive response | Fall back to neighboring read-only probes | Do not stop after one generic failure |

## High-signal feature gates

### `CdpDataStreams`
Typical impact:
- `sf data360 data-stream list`
- prepare / ingestion workflows

Suggested guidance:
- review Data Cloud Setup provisioning
- review source connector readiness
- confirm the user has the right Data Cloud permissions
- for Salesforce CRM ingestion, confirm the connector/integration user has object + field read access in the source org

### `CdpIdentityResolution`
Typical impact:
- `sf data360 identity-resolution list`
- harmonize / unified profile workflows

Suggested guidance:
- review harmonization and identity-resolution entitlements
- verify Data Cloud permission sets for the acting user
- confirm upstream DLO/DMO work is already healthy before retrying IR

### `CdpActivationTarget`
Typical impact:
- `sf data360 activation-target list`
- downstream audience delivery setup

Suggested guidance:
- review Data Cloud activation permissions
- review target/destination setup in Data Cloud Setup
- confirm the org/edition actually exposes activation-target management for that user

### `CdpActivationExternalPlatform`
Typical impact:
- `sf data360 activation platforms`
- platform catalog for destinations such as ads or storage targets

Suggested guidance:
- review Activation Targets setup
- review destination-specific authentication/configuration
- check whether the org exposes additional toggles in **Data Cloud Setup → Feature Manager**

### `CdpDataSpace`
Typical impact:
- `sf data360 data-space list`
- core multi-space administration

Suggested guidance:
- review core Data Cloud provisioning and user access
- confirm the user is intended to administer/view data spaces

## What is usually **not** fully programmatic

Do not promise a pure CLI flow for:
- initial Data Cloud tenant provisioning
- license assignment
- every org-wide Data Cloud enablement step

These commonly require Setup UI, provisioning, licensing, or account-level activation.

## What is often programmatic **after** provisioning

Once the org is properly provisioned, many workflows are programmatic through `sf data360`, including:
- data-space listing / get / create / update
- DMO catalog inspection and some DMO mutations
- segment and calculated insight lifecycle operations
- activation target and data action target operations
- search-index lifecycle operations
- hybrid search and related retrieve-plane workflows on newer runtime versions

Exact coverage still depends on org entitlements and the user's permissions.

## Known partial-automation gap

Some external database connectors can be created via API while the corresponding data-stream creation flow still requires UI steps or org-specific browser automation.

Practical guidance:
- treat connection creation and stream creation as separate capability checks
- do not assume a successful external connection create call means `data-stream create` will work for that connector
- if the org relies on that path, guide the user toward manual UI creation or a locally validated Playwright/browser automation helper rather than promising a generic CLI-only workflow

## User-facing guidance model

When blocked, respond in this order:
1. **Classify the failing surface** — runtime, auth, provisioning, feature gate, empty state, or bad table
2. **Show the evidence** — the specific command + high-signal error text
3. **Give the next setup step** — Data Cloud Setup, permissions, Feature Manager, source-object permissions, destination auth, etc.
4. **Avoid false claims** — don't say "Data Cloud is off" unless multiple core probes support that conclusion

## Setup guidance to point users toward

Depending on the failing feature, guide users to review:
- **Setup → Data Cloud Setup** for core provisioning / Get Started flow
- **Standard Data Cloud permission sets** appropriate to the task (for example Architect/Admin vs activation-focused roles)
- **Data Cloud Setup → Feature Manager** for org-specific toggles or beta features that are actually exposed there
- **Source org permissions** for CRM ingestion users when streams/connectors depend on object/field access
- **Activation target and destination authentication** when activation features are partially enabled but not usable yet

## Skill author checklist

Before telling the user a feature is unavailable:
- [ ] Did I run a targeted probe for this phase?
- [ ] Did I check at least one neighboring read-only probe?
- [ ] Did I avoid treating `doctor` as a full product readiness check?
- [ ] Did I avoid treating `query describe` as a universal tenant probe?
- [ ] Did I tell the user exactly what setup area to review next?
