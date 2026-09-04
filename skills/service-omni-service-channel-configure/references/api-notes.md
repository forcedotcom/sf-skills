# ServiceChannel — API notes

Load this reference only when the deploy fails or Salesforce reports unexpected state. Under normal operation the skill's deploy-and-report script just runs and emits its JSON; this doc is for troubleshooting and extensions.

**Metadata type:** `ServiceChannel` (queryable via the Tooling API for basic fields; Metadata-only for `capacityModel` and other tuning fields). **API version:** v66.

---

## The six fields in the shipped Cases XML

| Field | Value | Semantics |
|---|---|---|
| `capacityModel` | `TAB_BASED` | Capacity accounting model. `TAB_BASED` = each open Console tab = 1 unit of an agent's total capacity. Alternative: `STATUS_BASED` (capacity varies by presence status) |
| `doesMinimizeWidgetOnAccept` | `false` | Whether the Omni widget minimizes when an agent accepts work. `false` = widget stays visible |
| `hasAutoAcceptEnabled` | `false` | Whether work is auto-accepted (no click). `false` = agent must manually accept |
| `isInterruptible` | `false` | Whether new work can interrupt an active work item. `false` = agents finish current work first |
| `label` | `Cases` | UI display name. Must be `Cases` for the standard Case channel |
| `relatedEntityType` | `Case` | The sObject type this channel routes. Must be `Case` for Case routing |

**Fields not in the shipped XML (Salesforce uses defaults):**
- `secondaryRoutingPriorityField` — set only when secondary priority sorting is needed.
- `customEventChannel` / `customEventPayloadField` — only for custom-event-driven channels.
- `dispatcherClass` — only for advanced routing customization.

Fork the skill's XML to set any of these.

## Capacity is not tunable at the channel level on v66

Per-item weighted capacity (`capacityWeight` on older API versions) is no longer a ServiceChannel field on v66; the schema exposes `capacityModel` (`TAB_BASED` | `STATUS_BASED`) instead. For per-agent totals use `PresenceUserConfig.Capacity` at the agent level, or switch `capacityModel` to `STATUS_BASED` for status-dependent behavior. Related renames on v66: `masterLabel` → `label`, `relatedEntity` → `relatedEntityType`; `isCustomerVisible` was removed (customer visibility is now inferred from channel type).

**Implication for this skill:** on a fresh v66 CDO the `Cases` channel already has all six fields at their defaults, so this skill's deploy usually returns `state: Unchanged` / `status: reused`. It is most useful for recovering a mis-configured `Cases` channel, migrating from an older API version's config, or documenting the canonical v66 state in a git-controlled asset. It cannot change per-Case weighted capacity, and enabling auto-accept or minimizing behavior requires forking the XML.

---

## Standard channels' DeveloperNames

Salesforce ships several standard ServiceChannels on Service Cloud orgs:

| DeveloperName | MasterLabel | RelatedEntity | Purpose |
|---|---|---|---|
| `Cases` | `Cases` | `Case` | Standard Case routing (**this skill's target**) |
| `sfdc_liveagent` | `Chat` | `LiveChatTranscript` | Live Agent chat |
| `sfdc_livemessage` | `Messaging` | `MessagingSession` | Messaging (WhatsApp, SMS, etc.) |
| `sfdc_phone` | `Phone` | `VoiceCall` | Voice/telephony |

The standard Case channel's DeveloperName is `Cases` (plural), not `Case` (singular). To configure a different standard channel, fork this skill's XML and package.xml so the file path and package member both match the target DeveloperName.

---

## ServiceChannel's Metadata field is not Tooling-SOQL queryable

`capacityModel` and the other tuning fields cannot be read via Tooling SOQL as a pre-check:

```text
SELECT Id, DeveloperName, MasterLabel, CapacityWeight FROM ServiceChannel WHERE DeveloperName='Cases'
-- INVALID_FIELD: No such column 'CapacityWeight' on entity 'ServiceChannel'.

SELECT Id, DeveloperName, MasterLabel, Metadata FROM ServiceChannel WHERE DeveloperName='Cases'
-- INVALID_FIELD: No such column 'Metadata' on entity 'ServiceChannel'.
```

`GET /services/data/vXX.0/tooling/sobjects/ServiceChannel/<id>` also returns `{Metadata: null}` even when the metadata exists. The workaround is a Metadata API retrieve (`sf project retrieve start --metadata "ServiceChannel:Cases"`) — slow (~90 sec) but reliable. This skill avoids the retrieve entirely by relying on the deploy's own `files[0].state` signal.

Behavior is entity-specific: `WorkSkillRouting` exposes a queryable `Metadata` field, `ServiceChannel` does not. Always describe first (or test with a small query) before assuming Tooling SOQL is a viable read path.

---

## Deploy failure modes

| Symptom | Root cause | Skill behavior |
|---|---|---|
| `INVALID_TYPE` for ServiceChannel | OmniChannelSettings not enabled (`enableOmniChannel=false`) | Translates to: "OmniChannelSettings is not enabled on this org. Run service-omni-base-settings-configure first." |
| `FIELD_INTEGRITY_EXCEPTION` for relatedEntity | Attempted to change `relatedEntity` (immutable on the standard Case channel) | Block; do not change relatedEntity via this skill — write a separate custom-channel-create skill |
| `DUPLICATE_DEVELOPER_NAME` | Tried to create a channel with an existing DeveloperName | Should not happen (this skill updates the existing `Cases`, not creates) — indicates a bug or org corruption |
| `state: Unchanged` | Payload matched existing state | Success — `status: reused` |
| `state: Changed, success: true` | Payload modified state | Success — `status: created` |

---

## Alternative approaches (evaluated, not chosen)

- **Tooling API PATCH on `Metadata`** — fails at the read step (see above), so a PATCH cannot be validated. The Metadata API is the reliable canonical path.
- **Retrieve → parse XML → decide → deploy** — rejected because the ~90-second retrieve latency is not justified when the deploy's own `state: Unchanged` signal is authoritative. If before-state visibility becomes important, add an optional `--with-detect` flag.
- **`sf api request rest` GET → PATCH** — the GET works but returns `Metadata: null` for ServiceChannel, so it is not a viable read path.
