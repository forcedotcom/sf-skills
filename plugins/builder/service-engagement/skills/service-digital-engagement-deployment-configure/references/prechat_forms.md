# Pre-Chat Forms Reference (`<embeddedServiceForms>`)

Complete reference for configuring pre-chat forms on an `EmbeddedServiceConfig`. Read this whenever the user asks to add, change, deactivate, or remove pre-chat fields, or to set `displayNameFormat`.

Collects information from users before conversation starts. Applicable to all deployment types.

---

## Inputs to Gather

For each field:
- `formField`: a standard `_`-prefixed name, or the name of an existing channel `customParameter`.
- `formFieldType`.
- Whether it's required.
- Whether it's visible or hidden/pre-populated.

Also gather:
- **ChoiceList fields:** the DeveloperName of an existing `ChoiceList` (see [ChoiceList (Dropdown) Fields](#choicelist-dropdown-fields)).
- **`displayNameFormat`** (optional): see [displayNameFormat Rules](#displaynameformat-rules).
- **Omni-Flow routing details:** needed only if `isActive=true`, the channel isn't already Flow-routed, and the user accepts the offer to switch it (see [Runtime Dependency](#runtime-dependency-active-pre-chat-requires-omni-flow-routing)). Get the **Omni-Channel routing Flow API name** and the **fallback queue** DeveloperName. Both are needed to switch the channel to Flow routing, which is handed off to `service-digital-engagement-channel-configure`. Don't assume them.
- **Field → flow-variable mappings** (optional, and only meaningful with Omni-Flow routing): if the user wants the collected values delivered into the routing Flow, capture each pair (pre-chat field → flow input variable name). This skill does **not** write the mapping, because it lives on the channel. Pass the pairs to `service-digital-engagement-channel-configure`, which owns `actionParameterMappings`.

---

## Defaults: Pre-Chat Is OFF Out of the Box

The Setup UI ships pre-chat **disabled**. A brand-new deployment has **no active form and no fields**. Match that baseline when the user gives no pre-chat instruction:

- **Do not generate an `<embeddedServiceForms>` block at all** unless the user explicitly asks for pre-chat data collection. Omitting it is the correct default.
- **Never auto-inject** `_FirstName` / `_LastName` / `_Email` / `_Subject` as "the default form." A starter set of standard fields is a common *admin* pattern, not a Salesforce-shipped default.
- When the user *does* ask for a form but omits per-field detail, mirror the Setup UI's unchecked checkboxes: `isRequired` → `false`, `isHidden` → `false`.
- `displayContext` has **no platform default** and is a required element. If the user doesn't specify, default to `Conversation`. This is a skill convention: the UI forces an explicit pick and there is no factory value.

## Form Structure

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `displayContext` | Enum | Yes | — (no platform default; skill uses `Conversation`) | `Conversation` (form shown every conversation) or `Session` (shown once per session) |
| `isActive` | Boolean | Yes | `false` | Whether the form is active. Platform default is `false`; set `true` to make the form live |
| `embeddedServiceFormFields` | Repeatable | Yes | — | Individual form fields (see below) |

## Form Field Structure (`<embeddedServiceFormFields>`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `displayOrder` | Integer | Yes | — | Display position. Visible fields use `0`-based ascending order; **hidden fields conventionally use `-1`** (see hidden-field pattern below) |
| `formField` | String | Yes | — | Parameter name. Use the `_` prefix for standard fields (e.g., `_FirstName`) and the exact `name` for custom fields. **Must resolve to a standard parameter or an existing `customParameter` on the associated channel** (see coupling note) |
| `formFieldType` | Enum | Yes | — | One of `Text`, `Email`, `Phone`, `Number`, `Checkbox`, `ChoiceList`. Setup UI "Field Type" labels match these, except `Dropdown` → `ChoiceList`. See the Custom Pre-Chat Fields section for the full UI mapping |
| `choiceList` | String | ChoiceList only | — | DeveloperName of an existing `ChoiceList` record. **Required when `formFieldType` is `ChoiceList`**; omit otherwise. The record must already exist in the org (not deployable — see ChoiceList section) |
| `isHidden` | Boolean | Yes | `false` | Whether field is hidden from the user (value still captured/pre-populated) |
| `isRequired` | Boolean | Yes | `false` | Whether field must be filled |
| `messagingChannelParameterType` | Enum | Yes | — | `Standard` or `Custom` |

Every attribute above is mandatory on each `<embeddedServiceFormFields>`, except `choiceList`. A missing attribute fails the deploy with "required field missing" or "upsert failed null".

## Hidden / Pre-Populated Fields

Hidden fields capture context without prompting the user, such as marketing attribution, campaign IDs, or tracking params. The value is passed through from the host page but never shown.

The Setup UI has no per-field "hidden" checkbox. Instead, a field is hidden by placing it under the **Hidden Pre-Chat Fields** accordion (rather than **Visible Pre-Chat Fields**) on the pre-chat panel. In metadata, that maps to:

- `isHidden` → `true`
- `displayOrder` → `-1`. Visible fields get sequential `0`-based order; hidden fields keep `-1` because they aren't ordered on-screen.
- `isRequired` → `false`
- `messagingChannelParameterType` → almost always `Custom` (must exist as a `customParameter` on the channel first)

```xml
<embeddedServiceFormFields>
    <displayOrder>-1</displayOrder>
    <formField>utm_campaign</formField>
    <formFieldType>Text</formFieldType>
    <isHidden>true</isHidden>
    <isRequired>false</isRequired>
    <messagingChannelParameterType>Custom</messagingChannelParameterType>
</embeddedServiceFormFields>
```

## Field ↔ Channel Coupling (Required)

`formField` is validated against the associated messaging channel at deploy time:

- **Standard fields** (`_FirstName`, `_LastName`, `_Email`, `_Subject`) resolve to built-in standard parameters, so they have no channel prerequisite. The channel should still expose the matching `standardParameters` for routing.
- **Custom fields**, including every `ChoiceList` field, must match by name a `customParameter` already defined on the channel. Create those via `service-digital-engagement-channel-configure` **before** referencing them here, or the deploy fails.

## Runtime Dependency: Active Pre-Chat Requires Omni-Flow Routing

An **active** pre-chat form (`isActive=true`) only works on the client if the associated messaging channel's **routing type is Omni-Channel Flow ("Omni Flow")**:

- The routing Flow is what consumes the collected pre-chat parameters. With **queue-based routing the pre-chat form will not function**.
- Routing type is a channel-side setting owned by `service-digital-engagement-channel-configure`, not part of `EmbeddedServiceConfig`. It must still be true for the form to work.

The platform does not enforce this: Setup and the Metadata API both accept an active form on a queue-routed channel. How to handle it: gap 3 in [Validating and Remediating Prerequisites](#validating-and-remediating-prerequisites).

## Parameter → Flow-Variable Mapping (channel-side)

When the channel uses Omni-Flow routing, each pre-chat parameter can be bound to a routing-flow input variable so the collected value is delivered into the Flow.

**This binding lives on the `MessagingChannel`, not on the `EmbeddedServiceConfig`.** It is owned entirely by `service-digital-engagement-channel-configure`, which authors, documents, and validates it (see that skill's `channel_settings.md` for the `actionParameterMappings` shape). This skill never emits it.

This skill only captures the pairs (see Inputs to Gather) and passes them on in the hand-off below.

## Validating and Remediating Prerequisites

**Before generating the form**, validate it against the *retrieved* channel state. The gaps to check:

1. A custom `formField` with no matching channel `customParameter`: **blocks the deploy**.
2. A missing `ChoiceList` record: **blocks the deploy**.
3. `isActive=true` on a queue-routed channel: deploys, but the form won't work in the widget. **Warn only.**

For gaps 1 and 3, offer to fix them by **invoking `service-digital-engagement-channel-configure`**. Pass it the retrieved channel as context, plus any field → flow-variable pairs the user gave. This skill must never edit the `MessagingChannel` metadata itself.

A missing `ChoiceList` can only be created in Setup, so report it and don't create it. If gap 1 or 2 remains unfixed, stop and report the unmet prerequisite instead of emitting the form. For gap 3, emit the form either way and repeat the warning in the final summary.

Two cautions for the hand-off:

- **Hand off, don't hand-edit, and pass the existing channel as context.** `service-digital-engagement-channel-configure` builds a full channel document. Give it the retrieved channel so it *augments* the existing configuration; that's how existing `customParameters`, `actionParameterMappings`, consent, keywords, and settings avoid being clobbered. Do not merge channel XML by hand from within this skill.
- **The routing switch has prerequisites.** Moving a channel from Queue to Omni-Flow requires a fallback queue and an **already-existing** Omni-Channel routing Flow (create one via `automation-flow-generate` if none exists). It is a channel-wide change, so confirm the user intends it before handing off.

## Deactivating vs. Removing Pre-Chat Fields

Turning pre-chat off, or trimming fields, is not one operation, and the Metadata API update path does **not** behave like the Setup UI. The `<embeddedServiceFormFields>` collection follows a replace-if-present / no-op-if-empty rule. Pick the operation that matches the intent:

| Goal | How | Result |
|------|-----|--------|
| **Deactivate** (turn pre-chat off, keep fields) | Set `<isActive>false</isActive>`, deploy, **publish** | Form stops rendering; all fields are retained and can be reactivated. This is the off switch the Metadata API supports. |
| **Delete specific fields** | Deploy the block with **only the fields to KEEP** (min 1), then publish | A non-empty field collection is a full **replace**, so omitted fields are deleted. |
| **Delete ALL fields / delete the form** | **Not possible via Metadata API** | An empty collection (or omitting the block) is a silent **no-op**: the deploy reports "Succeeded" but every field is preserved. Removal is Setup-UI only (pre-chat editor link: ChoiceList rule 4). Even then a retrieve can still show an **inactive form with 1 field** (observed after a Setup delete), so don't promise the form is gone: offer to retrieve and report what remains. Deactivate instead. |

Key points:

- **Empty ≠ subset.** An *empty* `<embeddedServiceFormFields>` collection preserves everything (no-op), while a *non-empty* subset replaces the collection and drops the omitted fields. Through metadata you can shrink a form to 1 field, but never to 0.
- **Every case is a draft until published**, and publishing needs the user's approval (SKILL.md step 17c).
- **Order matters when a field maps to a custom channel param.** To remove a field bound to a channel `customParameter`:
  1. Strip the field from the form and **republish**. This publish is required before the param can go, so ask the user to approve it; if they decline, stop before step 2.
  2. Hand off to `service-digital-engagement-channel-configure` to delete the param. Other deployments can share the channel; any whose form still uses the param block the delete, so the channel skill checks them first.

  Deleting a param that a live pre-chat field still references fails ("can't be deleted as it is referenced elsewhere"). The param's `actionParameterMapping` must also be removed first, which is a separate two-step change on the channel side.
- **Scalar footnote:** omitting the scalar `<displayNameFormat>` on a deploy *does* drop it. Scalars clear on omission, unlike the field collection.

## Example

See `examples/esd_web_prechat_fields.xml` for the full `<embeddedServiceForms>` + `<displayNameFormat>` delta (standard, custom, Checkbox, ChoiceList, and hidden fields). It is kept there as the single canonical copy rather than duplicated here. Graft it onto a base deployment such as `examples/esd_web_full.xml`.

## Standard Pre-Chat Fields

Standard fields use a `_` prefix in the `formField` value:

| `formField` Value | Maps to `parameterType` | Typical Usage |
|-------------------|------------------------|---------------|
| `_FirstName` | `FirstName` | User identification |
| `_LastName` | `LastName` | User identification |
| `_Email` | `Email` | Follow-up and case creation |
| `_Subject` | `Subject` | Routing context |

## Custom Pre-Chat Fields

Custom fields use the exact `name` value from the channel's `customParameters`, with no prefix (see Field ↔ Channel Coupling).

**Where the data type lives:** the channel `customParameter` is **always** `parameterDataType=String`; the channel accepts no other value. The field's actual data type (Text, Number, Checkbox, Dropdown) is set here at the deployment level, via `formFieldType`.

So a Checkbox pre-chat field is `formFieldType=Checkbox` on this ESD form field plus a plain `String` `customParameter` on the channel. Do **not** ask the channel skill for a `Boolean`/`Number` parameter; it fails with "bad value for restricted picklist field".

### How custom fields are created in the Setup UI

Admins add a custom field through **Setup → the pre-chat editor → Add Field**, which opens the **New Custom Field** dialog. This one dialog handles *all* custom field types. What it captures maps to metadata as follows:

| Setup UI field | Maps to | Notes |
|----------------|---------|-------|
| **Field Type** | `formFieldType` | Options → enum value: `Text`→`Text`, `Email`→`Email`, `Phone`→`Phone`, `Number`→`Number`, `Checkbox`→`Checkbox`, `Dropdown`→`ChoiceList` |
| **Channel Variable Name** | `formField` | A **lookup that selects an existing channel `customParameter`** (`MessagingChannelParameter`). It is *not* free text and does *not* create a parameter. If none exist, the dialog shows "Create one in Messaging Settings"; create it first via `service-digital-engagement-channel-configure` |
| Dropdown-only fields | see ChoiceList section | **Dropdown Name / Dropdown API Name / Dropdown API Values** appear only when Field Type is `Dropdown` |

Visible vs. hidden is **not** set in this dialog. It's determined by which accordion (Visible / Hidden Pre-Chat Fields) the field sits under on the main panel; see Hidden / Pre-Populated Fields above.

## ChoiceList (Dropdown) Fields

A ChoiceList renders the field as a dropdown of predefined options.

**Critical: a `ChoiceList` is NOT deployable metadata**; create it in Setup. There is no `.choiceList-meta.xml` file to author or `sf project deploy`. The `EmbeddedServiceConfig` only ever **references** a ChoiceList by its DeveloperName.

The dropdown (ChoiceList) is created **inline in the "New Custom Field" dialog** when Field Type is `Dropdown`. Saving that dialog creates the `ChoiceList` and `ChoiceListValue` records in the org; they are not part of the deployable `EmbeddedServiceConfig` artifact. The extra dialog fields map as:

| Setup UI field (Dropdown only) | Maps to | In `EmbeddedServiceConfig` XML? |
|--------------------------------|---------|-------------------------------|
| **Dropdown Name** | `ChoiceList.masterLabel` | No (org-side record) |
| **Dropdown API Name** | `ChoiceList.developerName` → the `<choiceList>` reference | Yes — `<choiceList>` value |
| **Dropdown API Values** | `ChoiceListValue` records | No (org-side records) |

Consequences for this skill:

1. **The ChoiceList must already exist in the target org**, created via the Dropdown dialog above. It is not part of the artifact this skill produces.
2. In the form field, set `formFieldType` to `ChoiceList` and add a `<choiceList>` element with the existing record's DeveloperName (= the Dropdown API Name).
3. The same field must also satisfy the **field ↔ channel coupling**: its `formField` must match an existing channel `customParameter` (the Channel Variable Name), and `messagingChannelParameterType` is `Custom`. Its channel param is `String`, like any custom field.
4. Before generating, confirm the ChoiceList exists. ChoiceList can't be queried through the data API or Tooling API, so don't run a query for it. Ask the user to confirm the dropdown exists in the Setup pre-chat editor (New Custom Field → Dropdown) and to give you its **Dropdown API Name**. If it doesn't exist **or the user isn't sure**, treat it as missing: leave the ChoiceList field out of every deploy (never deploy it to find out) and tell the user to create it in Setup first; do **not** attempt to generate or deploy a ChoiceList file. Give them a full, clickable link to the deployment's pre-chat editor: `<instanceUrl>/lightning/setup/EmbeddedServiceDeployments/<EmbeddedServiceConfigId>/EmbeddedMessaging/prechat`, where `instanceUrl` comes from `sf org display --target-org '<org-alias>' --json | jq -r .result.instanceUrl` (always pipe through `jq`; the raw output contains the access token) and the Id from Tooling `SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='<name>'`. Hand back only this plain URL; the user's own browser login opens it. Never paste `sf org open --url-only` output, because its frontdoor URL carries a login token. There they choose New Custom Field → Field Type `Dropdown`.

```xml
<embeddedServiceFormFields>
    <choiceList>Customer_Inquiry_Type</choiceList>
    <displayOrder>0</displayOrder>
    <formField>InquiryType</formField>
    <formFieldType>ChoiceList</formFieldType>
    <isHidden>false</isHidden>
    <isRequired>true</isRequired>
    <messagingChannelParameterType>Custom</messagingChannelParameterType>
</embeddedServiceFormFields>
```

---

## displayNameFormat Rules

`displayNameFormat` is a scalar on `<embeddedServiceMessagingChannel>`. It sets the display name shown when pre-chat is enabled. Deploy and runtime both read the same field.

1. **Exactly 3 brace tokens:** `{a}{b}{c}`. Fewer fails structure validation (*"DisplayNameFormat field must match format {firstvalue}{secondvalue}{thirdvalue}"*). Leave unused slots **empty**, e.g. `{_firstName}{_lastName}{}`.
2. **Each non-empty token = the referenced pre-chat field's `externalParameterName`** (the "Channel Variable Name"), for *both* standard and custom fields. This is **not** the `<formField>` value:
   - **Standard**: `_firstName`, `_lastName`, `_email`, `_subject` (lowercase-first). The `formField` apiValue spelling `{_FirstName}` is **rejected** (*"includes a field name that doesn't match any configured…pre-chat fields"*), because deploy validation and runtime both look up by `externalParameterName`.
   - **Custom**: the channel `customParameter`'s `externalParameterName` (usually equal to its `name`, e.g. `CompanyName`).
3. At runtime each token is replaced by the value the user entered for that field, rendered space-separated (e.g. `Jane Doe`). Referenced parameters must be fields present (visible or hidden) in the form.
4. If you can't supply valid tokens, **omit** `displayNameFormat` (platform default).
5. **On a deployment that already has a form, tokens are checked against the *saved* fields, not the fields in the same deploy.** Adding a field and referencing it in `displayNameFormat` in one deploy fails with *"doesn't match any configured…pre-chat fields"*, even when the token is valid. Use two deploys: (1) the new field set, keeping the current `displayNameFormat`; (2) the same document with the new `displayNameFormat`. A deployment with no prior form accepts both in one deploy, but the two-step order is always safe.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Pre-chat ChoiceList not showing / missing | Created in Setup only; follow [ChoiceList rule 4](#choicelist-dropdown-fields) |
| Pre-chat form configured but not appearing / not working in the widget | Confirm `isActive=true` AND the channel uses Omni-Channel Flow routing (not queue-based). Active pre-chat only works with Omni-Flow routing. Also confirm the deployment was published after the deploy |
| Standard pre-chat field not found | Use `_` prefix for standard fields in `formField`: `_FirstName`, `_LastName`, `_Email`, `_Subject` |
| Custom pre-chat field fails to deploy | The `formField` must match an existing channel `customParameter` by name; add it via `service-digital-engagement-channel-configure` first |
| `displayNameFormat` rejected (bad format, or "field name doesn't match…pre-chat fields") | See [displayNameFormat Rules](#displaynameformat-rules): exactly 3 tokens, each a field's `externalParameterName` (`_firstName`, not `_FirstName`). If the token is correct but its field is new in the same deploy, deploy the field first, then the format (rule 5) |
| Deploy "Succeeded" but the pre-chat fields are all still there | An empty field collection is a no-op. Deactivate with `isActive=false`, or keep at least 1 field; removal is Setup-UI only (see the table above) |

---

## Verification Checklist

- [ ] Is `<embeddedServiceForms>` present only because the user asked for pre-chat?
- [ ] Does every `formField` resolve to a standard parameter (`_`-prefixed) or an **existing** channel `customParameter`?
- [ ] Do all `ChoiceList` fields reference a `<choiceList>` DeveloperName that already exists in the org?
- [ ] Do hidden/pre-populated fields use `displayOrder=-1` and `isHidden=true`?
- [ ] Does each `<embeddedServiceFormFields>` include all required attributes (`displayOrder`, `formField`, `formFieldType`, `isHidden`, `isRequired`, `messagingChannelParameterType`)?
- [ ] If `isActive=true` and the associated channel is not Omni-Channel Flow (Omni-Flow) routed, was the user warned that the form won't work in the widget until the routing is switched?
- [ ] If `displayNameFormat` is set, does it have **exactly 3** brace tokens (empties allowed)? Is each non-empty token a field's `externalParameterName` (lowercase-first `_firstName` etc., NOT `_FirstName`)?
