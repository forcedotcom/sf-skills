---
name: integration-eventing-subscription-configure
description: "Create, read, update, and delete ManagedEventSubscription metadata in Salesforce. Use this skill for any work involving managed event subscriptions, platform event subscriptions, event channel subscribers, or .managedEventSubscription-meta.xml files. TRIGGER when: user asks to subscribe to a platform event, create a managed subscription, set up event replay, configure an event channel subscriber, update replay preset, activate or deactivate a subscription, delete a subscription, or manage ManagedEventSubscription metadata. SKIP when: user needs to create the platform event channel itself (use platform-custom-object-generate skill) or needs Flow-based event subscriptions (use automation-flow-generate skill)."
metadata:
  version: "1.0"
---

# Managing ManagedEventSubscription

Create, read, update, and delete `ManagedEventSubscription` metadata — the Salesforce construct for durably subscribing to platform event channels with managed replay tracking.

## Scope

- **In scope**: Generating and modifying `.managedEventSubscription-meta.xml` files for create, read, update, and delete operations
- **Out of scope**: Creating the underlying platform event (`__e`) channel itself; Flow-based or Apex-based event subscriptions; deploying metadata to an org
- **Only generate one file** — the `.managedEventSubscription-meta.xml` file. Do NOT generate the referenced platform event object or any other metadata type.

---

## Clarifying Questions

Before generating, confirm if not already clear:

- What is the **topic name**? (see format table in `references/topic-name-formats.md`)
- What is the **developer name**? (required for Create — alphanumeric and underscores only, no spaces; optional for Read/Update/Delete if `Id` is known)
- What is the **label** (human-readable name)?
- What **default replay** preset — `LATEST` (default) or `EARLIEST`?
- What **error recovery replay** preset — `LATEST` (default) or `EARLIEST`?
- What should the initial **state** be — `RUN` (active) or `STOP` (inactive)? (default: `RUN`)

---

## Required Inputs

Gather or infer before proceeding:

- **Operation**: create, read, update, or delete
- **DeveloperName**: required for Create (becomes the filename); optional for Read/Update/Delete if `Id` is provided instead
- **Id**: Tooling API record Id — can be used to identify the subscription for Read/Update/Delete instead of DeveloperName
- **label**: human-readable label (can include spaces)
- **topicName**: event channel path — read `references/topic-name-formats.md` for valid formats (platform events, change events, custom channels)
- **defaultReplay**: `LATEST` or `EARLIEST` (default: `LATEST`)
- **errorRecoveryReplay**: `LATEST` or `EARLIEST` (default: `LATEST`)
- **state**: `RUN` or `STOP` (default: `RUN`) — `PAUSE` is reserved for internal platform use and will be rejected with `INVALID_INPUT`
- **version**: Metadata API version (default: match org API version, e.g. `67.0`)

---

## Workflow

### Create

1. **Gather inputs** — confirm DeveloperName, label, topicName, defaultReplay, errorRecoveryReplay, state, version. Apply defaults for any omitted fields. If DeveloperName is not provided, ask the user — do not derive it from the label.
2. **Confirm the topic exists** — ask the user to confirm the event channel already exists in the org before proceeding. Do NOT generate the platform event object yourself — that is out of scope for this skill. If the user says it doesn't exist yet, stop and direct them to create it first using the `platform-custom-object-generate` skill, then return here.
3. **Read the template** — load `assets/managed-event-subscription-template.xml` as the starting structure.
4. **Generate the file** — produce `managedEventSubscriptions/<DeveloperName>.managedEventSubscription-meta.xml` filled with user-provided values.
5. **Verify** — run the checklist below before presenting output.
6. **Guide the user on subscribing** — after deployment, the subscription can be identified for Pub/Sub API `ManagedSubscribe` RPC calls using either the `DeveloperName` or the record `Id`. To retrieve the `Id`, run: `SELECT Id, DeveloperName FROM ManagedEventSubscription WHERE DeveloperName='<DeveloperName>'` via the Tooling API.

### Read

1. **Identify the subscription** — accept either `Id` or `DeveloperName`; prefer `Id` if provided.
2. **Show the file path** — `managedEventSubscriptions/<DeveloperName>.managedEventSubscription-meta.xml` (if DeveloperName known).
3. **Retrieve and display** — read and present the current XML content.

### Update

1. **Identify the subscription** — accept either `Id` or `DeveloperName`; prefer `Id` if provided.
2. **Read the existing file** — load current content before modifying.
3. **Apply changes** — update only the specified fields; preserve all others.
4. **Read `references/update-constraints.md`** for fields that cannot be changed after creation.
5. **Verify** — run the checklist below before presenting output.

### Delete

1. **Identify the subscription** — accept either `Id` or `DeveloperName`; confirm with the user before proceeding.
2. **Warn** — deleting a ManagedEventSubscription permanently removes replay tracking state.
3. **Produce deletion instructions** — explain how to remove the file and deploy the destructive change using `destructiveChanges.xml`.
4. **Read `references/delete-guide.md`** for the destructive deployment procedure.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| `<topicName>` must use a valid path prefix | Platform events use `/event/Name__e`; change events use `/data/Name`; see `references/topic-name-formats.md` for all formats |
| `<defaultReplay>` and `<errorRecoveryReplay>` must be `LATEST` or `EARLIEST` | These are the only valid enum values; any other value fails metadata validation |
| `<state>` must be `RUN` or `STOP` | `PAUSE` is reserved for internal platform use — the API rejects it with `INVALID_INPUT: You can create a managed event subscription state field only to RUN or STOP` |
| All six required elements must be present | `topicName`, `defaultReplay`, `errorRecoveryReplay`, `label`, `state`, `version` are all required; omitting any causes a deploy error |
| DeveloperName must be unique within the org | Duplicate names cause `DUPLICATE_DEVELOPER_NAME` errors |
| Do not include `<namespacePrefix>`, `<id>`, or `<createdDate>` | Read-only platform fields; including them causes deployment failures in unpackaged orgs |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `The topicName field is invalid` on deploy | Wrong format or the event doesn't exist in the org — read `references/topic-name-formats.md` for correct path |
| Replay state lost after delete + recreate | Deleting discards stored replay position; recreating starts from `defaultReplay` — avoid reusing the same DeveloperName after delete |
| `INVALID_TYPE` on SOQL query | ManagedEventSubscription is only queryable via Tooling API, not standard SOQL |
| `EARLIEST` replay on high-volume channels | Can trigger up to 72 hours of backlog replay on activation; always confirm with the user |
| Metadata not supported in older orgs | ManagedEventSubscription requires API v60.0+; check org API version |
| `eventChannel` or `isActive` in generated XML | These are wrong field names — use `topicName` and `state` (`RUN`/`STOP`) instead |
| `PAUSE` state in generated XML | `PAUSE` is reserved for internal platform use and will be rejected with `INVALID_INPUT` — only use `RUN` or `STOP` |
| User unsure how to identify subscription for Pub/Sub API | Both `DeveloperName` and record `Id` can be used with `ManagedSubscribe` RPC — retrieve the `Id` via Tooling API if needed: `SELECT Id FROM ManagedEventSubscription WHERE DeveloperName='<name>'` |
| Changes not reflected immediately in Pub/Sub API | After create/update/delete, the Pub/Sub API can take up to ~2 minutes to reflect the new config; if ManagedSubscribe returns NOT_FOUND, wait and retry |

---

## Verification Checklist

Before presenting any generated XML:

- [ ] Does `<topicName>` follow a valid path format per `references/topic-name-formats.md`? (`/event/Name__e`, `/data/NameChangeEvent`, `/data/ChangeEvents`, `/event/Name__chn`, `/data/Name__chn`)
- [ ] Is `<defaultReplay>` exactly `LATEST` or `EARLIEST`?
- [ ] Is `<errorRecoveryReplay>` exactly `LATEST` or `EARLIEST`?
- [ ] Is `<state>` exactly `RUN` or `STOP`? (`PAUSE` is invalid for user-created subscriptions)
- [ ] Is `<label>` populated?
- [ ] Is `<version>` present (e.g. `67.0`)?
- [ ] Are read-only fields (`<id>`, `<createdDate>`, `<namespacePrefix>`) absent?
- [ ] Does the filename match the DeveloperName exactly?

---

## Output Expectations

- **Create / Update**: `managedEventSubscriptions/<DeveloperName>.managedEventSubscription-meta.xml` — this is the only file to generate
- **Delete**: instructions to remove the file and deploy via `destructiveChanges.xml`
- **Read**: display of existing file contents

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create the platform event channel (`__e`) being subscribed to | `platform-custom-object-generate` skill |
| Subscribe via Flow (Process Automation) | `automation-flow-generate` skill |
| Deploy metadata to org | `platform-metadata-deploy` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/managed-event-subscription-template.xml` | Before generating any new subscription — use as starting structure |
| `references/topic-name-formats.md` | When setting `<topicName>` — covers platform events, change events, and custom channels |
| `references/update-constraints.md` | During Update workflow — to check which fields are immutable post-creation |
| `references/delete-guide.md` | During Delete workflow — for destructive change deployment procedure |
