# API notes — ServicePresenceStatus (v66)

## Schema

`ServicePresenceStatus` is a Metadata-only sObject. It has an sObject shell for SOQL discovery, but the interesting state (channels, decline-reason references) lives only in the XML metadata.

**v66 XML skeleton:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ServicePresenceStatus xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Available for Cases</label>
    <channels>
        <channel>Cases</channel>
    </channels>
</ServicePresenceStatus>
```text

**Two elements only:**

| Element | Required | Type | Notes |
|---|---|---|---|
| `<label>` | yes | string ≤ 80 chars | Display label. On v66 this is `<label>` (older API versions used `<masterLabel>`). |
| `<channels>` | no | 0..N of `<channel>` | If present, agent is online for those channels. If absent, agent is busy/away (no work received). Each `<channel>` references a `ServiceChannel.DeveloperName`. |

**Fields not present in v66 XML:**

- `<statusType>` — on v66 this is inferred from the presence of `<channels>`; adding `<statusType>` to the deploy XML causes `Element {statusType} not defined`.
- `<masterLabel>` — renamed to `<label>`.

## The StatusType concept is not settable or queryable on v66

The `StatusType` concept still exists in the Salesforce runtime (query it via `PresenceUserConfigProfile` joins or the presence-status-selector UI) but is not:

- Directly settable in metadata XML (v66) — inferred from `<channels>`
- Directly queryable in SOQL (see below)
- Directly readable via `sf project retrieve start` — the XML you retrieve is the canonical representation

**Runtime implication:** to give an agent a "Busy" status, deploy a `ServicePresenceStatus` with no `<channels>` element. To give an "Online for Cases" status, deploy one with `<channels><channel>Cases</channel></channels>`. Multiple busy statuses are allowed (e.g. `Omni_OnBreak`, `Busy` — both no channels, distinguishable only by label).

**Caveat — busy/online status option is UI-only:** the Omni-Channel "Status Options: Online / Busy" toggle is NOT part of the `ServicePresenceStatus` metadata type or a queryable field (confirmed via community + developer.salesforce.com — the type carries only `label` + `channels`). A no-channels status is treated as busy at runtime, but you cannot *set* the toggle headlessly. Because of this, our skill does not mint a custom `Omni_Busy`; it reuses the conventional `Busy` status if it exists (`SELECT Id FROM ServicePresenceStatus WHERE DeveloperName='Busy'`) and only deploys a bundled `Busy` when the org has none — never redeploying (and thus never risking) an existing, correctly-toggled `Busy`.

## StatusType is not SOQL-queryable on v66

`ServicePresenceStatus.StatusType` is not SOQL-queryable on v66:

```
SELECT Id, DeveloperName, StatusType FROM ServicePresenceStatus
                                ^
ERROR at Row:1:Column:40
No such column 'StatusType' on entity 'ServicePresenceStatus'
```text

**Queryable fields:** `Id`, `DeveloperName`, `MasterLabel`.

**Fields that describe as existing on the sObject but fail in SOQL:** `StatusType`, `Channels` (relationship), various audit fields.

**Implication for the audit-log skill:** to enumerate the set of presence statuses on an org, use `SELECT Id, DeveloperName, MasterLabel FROM ServicePresenceStatus`, then optionally `sf project retrieve start` with a `ServicePresenceStatus:*` package to get the per-status XML for channel details.

## Deploy semantics

Metadata API deploy of `ServicePresenceStatus:Available_Case` returns per-file state:

- `Created` — new status record
- `Changed` — status existed, XML differed, record updated
- `Unchanged` — status existed, XML matched (byte-for-byte, after normalization)

For our skill's `Available_Case` XML:

```xml
<ServicePresenceStatus xmlns="http://soap.sforce.com/2006/04/metadata">
    <channels>
        <channel>Cases</channel>
    </channels>
    <label>Available for Cases</label>
</ServicePresenceStatus>
```

If the org has an existing `Available_Case` with a different label OR different channels OR extra child elements, deploy will report `Changed` and overwrite. This is intentional for our skill's "canonicalize state" semantics.

**XML element ordering does NOT affect Unchanged detection** — Salesforce normalizes before comparing. `<channels>` before `<label>` or after produces the same hash.

**Whitespace/indentation does NOT affect Unchanged detection** — Salesforce normalizes whitespace before comparing.

## Common deploy failures + translations

| Salesforce error | Skill translation | Prerequisite skill |
|---|---|---|
| `INVALID_TYPE: ServicePresenceStatus` | "OmniChannelSettings not enabled — run service-omni-base-settings-configure first" | `service-omni-base-settings-configure` |
| `INVALID_TYPE: OmniChannel` | Same as above | Same |
| `INVALID_FIELD_VALUE: 'Cases' is not valid` on `<channel>` reference | "Cases ServiceChannel does not exist — run service-omni-service-channel-configure first" | `service-omni-service-channel-configure` |
| `Element {statusType} not defined` | "Deploy XML contains `<statusType>` element — remove it; v66 infers status from `<channels>`" | (fix XML) |
| `INSUFFICIENT_ACCESS_OR_READONLY` | "Executing user lacks Metadata API permissions — re-authenticate as System Administrator" | (re-auth) |
| `UNKNOWN_EXCEPTION` (transient) | Retry once; if persists, escalate to Salesforce support | (retry) |

## Retrieve semantics

`sf project retrieve start --metadata "ServicePresenceStatus:*"` returns one XML file per status but can take several minutes for a handful of statuses (network + Salesforce packaging overhead), which is why this skill does not retrieve — it trusts `sf project deploy start`'s per-component `state` signal instead.

## Latency resilience (deploy async+poll; verify bounded-retry)

`deploy-and-report.sh` deploys **async** (`sf project deploy start --async`) then polls `sf project deploy report --job-id <id>` to a terminal state (~20 min budget = 80 × 15s), mirroring the sibling supervisor-config-deploy skill. A synchronous watched deploy raises `ClientTimeoutError` under org load and exits non-zero even when the server-side deploy Succeeds — a false red.

The post-deploy binding **verification** retrieve uses **bounded retry with backoff** (5 attempts, 10→40s increasing sleeps) so a single latency-induced *empty* retrieve does not immediately flip an otherwise-successful deploy to blocked. A retrieve that returns XML is authoritative and stops the loop at once (channel present → verified; channel absent → definitively unbound → blocked). The verify still fails closed: after the retry budget is exhausted with no XML, `BINDING_VERIFIED` stays `unverified` and the skill blocks — retries convert transient emptiness into a definitive read, they never assume success.

## Standard vs custom statuses

Salesforce ships several standard presence statuses out of the box on orgs with OmniChannel enabled:

- `availableForMessaging` (channels: sfdc_livemessage)
- `availableForMiaw` (channels: sfdc_livemessage)

These are shipped by Salesforce and always exist. Our skill's `Available_Case` is a custom addition — deploying it is idempotent (won't collide with the standard ones) but it does occupy the org's DeveloperName namespace. For the busy status we reuse the conventional `Busy` rather than adding a custom one.

**Naming convention rule:** never use a DeveloperName that looks like a standard status (e.g. `available*`, `busy*` without a prefix). Our skill uses `Available_Case` (with underscore + object suffix) and `Omni_*` (with `Omni_` prefix) to stay clear of the standard namespace.
