# Custom Labels Reference (Web and Mobile deployments)

Custom labels replace the widget's built-in text (for example the "Today" date divider) per deployment, with optional translations. They are **Tooling API records, not part of `EmbeddedServiceConfig` XML**: never add them to the generated file. Supported on Web (v1 and v2) and Mobile deployments; **API deployments have no custom labels**. They are written in Phase 2C after the deployment exists, and go live only when the deployment is published (SKILL.md step 17c).

---

## Inputs to Gather

- **Deployment** (API name, resolved to its `EmbeddedServiceConfig` Id)
- **Label key** — one `LabelKey` per label. Prefer `EM_*` (embedded messaging). Do not guess keys; list candidates from the describe (see Validating the Key)
- **Text** in the base language (`en_US`)
- **Translations** (optional) — pairs of language code and text

Delegated: read the key, text and translations from `intent`; ask only for what it leaves open, and never invent a key. Deployment-level labels only. You may propose candidate keys from the user's description (for example "Today divider" → `EM_Container_Base_StartBookendText`), but never pick one silently: the user names the key or confirms one from the list you show.

---

## Prerequisites (check in order; stop at the first failure, except an inactive translation language, see 2)

All checks are read-only. Enabling Translation Workbench or a language is an org setting: give the user the Setup step and let them apply it (delegated: `failed`, naming the unmet prerequisite). Do not change org settings here.

1. **Translation Workbench is enabled** — required for *any* custom label to show, English-only included.
   `GET /services/data/vXX.0/tooling/query?q=SELECT IsTranslationWorkbenchEnabled FROM LanguageSettings` → must be `true`. A missing row or `false` means off.
2. **Every language the label appears in is enabled** — the base language and each translation.
   `GET /services/data/vXX.0/query?q=SELECT Language, IsActive FROM Translation` (standard data API, not Tooling) → each needed code must have `IsActive = true`. The API accepts any of 224 language codes for a translation, but Setup lists only enabled ones, so a translation for a language that is not enabled is stored and cannot be seen or edited in Setup. **Do not write a `LocalizedValue` for a language that is not active**, even when told not to ask questions: write the base text only if that is valid, skip the translation, and report the Setup step to enable the language (delegated: `failed` for that translation, naming the language).
3. **The deployment exists and its type supports labels** (contract §3 pre-scan). Read `deploymentType` from the deployment before any write, so no `ExternalString` is created and left orphaned:
   - **API:** not supported. Stop and say so; write nothing (delegated: `failed`, naming the type).
   - **Mobile:** only `EM_PreChat_TermsAndConditions` and `EM_Fallback_FallbackMessage` are accepted (core rule in `EmbeddedServiceCustomLabelObject`, checked on create). Any other key fails with `INVALID_INPUT: Object is not supported for this deployment type`; refuse it up front and offer those two.
   - **Web (v1 and v2):** any key from the describe is accepted. See the v1/v2 warning below.

---

## Validating the Key

`LabelKey` on `EmbeddedServiceCustomLabel` is a restricted picklist (about 440 values). Read the valid keys from `GET /services/data/vXX.0/tooling/sobjects/EmbeddedServiceCustomLabel/describe` (field `LabelKey`, `picklistValues`); never hardcode the list. An unknown key fails the create.

| Prefix | Meaning |
|---|---|
| `EM_` | Embedded Messaging widget text. Use these |
| `LA_`, `FS_`, `CM_` | Legacy chat and other products. The API accepts them on a Web deployment, but they do not map to MIAW text. Warn before using one |

**Web v1/v2 warning.** Web v1 and v2 show different label sets in Setup. The API stores a key that belongs to the other version, but it never appears in Setup or the widget, and the org cannot be asked which keys fit which version. Do not read the client version. Before writing, tell the user once: "Setup lists different labels for Web v1 and v2. If the row does not appear under Custom Labels for this deployment, the key may belong to the other version." Do not hardcode or filter by a key list. Delegated: no question; add a one-line "verify in Setup (v1 and v2 list different labels)" note to the result and keep the status `success`.

The label sets the widget text only. Turning Terms and Conditions on or off is `isTermsAndConditionsEnabled` / `isTermsAndConditionsRequired` in the XML (SKILL.md step 15); on Mobile, `EM_PreChat_TermsAndConditions` is the text of that line.

Where a key appears in Setup: Setup → the deployment → Custom Labels, filtered by Language / Chat Group / Label Group / Label Type. For example `EM_Container_Base_StartBookendText` is the default "Today" row, Chat Group "Chat in Progress", Label Type "System Messages".

---

## Record Model

| Record (Tooling) | Purpose |
|---|---|
| `ExternalString` | The text: `Name`, `MasterLabel`, `Value`, `Language`, `Category` |
| `EmbeddedServiceCustomLabel` | Binds the string to the deployment: `EmbeddedServiceConfigId`, `LabelKey`, `CustomLabelId` |
| `LocalizedValue` | One translation: `ParentId` (the `ExternalString` Id), `Language`, `Value` |

**`ExternalString` shape (required).** `Category` must be `EmbeddedMessaging`; any other value, or none, makes the later publish fail. Use the shape Setup writes:

- `Name` = `MasterLabel` = `<LabelKey>_<15-char EmbeddedServiceConfigId>_<7 digits>`
- `Language` = `en_US`, `Category` = `EmbeddedMessaging`, `Value` = the text

---

## Create (idempotent)

1. **Detect.** `GET /services/data/vXX.0/tooling/query?q=SELECT Id, LabelKey, CustomLabelId FROM EmbeddedServiceCustomLabel WHERE EmbeddedServiceConfigId = '<id>'`. A row for the key means **update**, not create: a second binding for the same key on a deployment fails with `DUPLICATE_VALUE`. For an existing row, read the `ExternalString` `Value` and its `LocalizedValue` rows and compare with the request; if all match, write nothing (delegated: `already-configured`, contract §3).
2. **Create the string.** `POST /services/data/vXX.0/tooling/sobjects/ExternalString` with the shape above. Keep the returned `id`.
3. **Bind it.** `POST /services/data/vXX.0/tooling/sobjects/EmbeddedServiceCustomLabel` with `{EmbeddedServiceConfigId, LabelKey, CustomLabelId}`. If the bind is rejected, `DELETE` the `ExternalString` from step 2 (it is left orphaned) and report the error.
4. **Translations** (if any). `POST /services/data/vXX.0/tooling/sobjects/LocalizedValue` per language with `{ParentId, Language, Value}`.
5. **Read back.** Query the `ExternalString` (`Value`, `Category`) and re-query the bindings to confirm what landed.

Build JSON bodies with `jq -n --arg` on the CLI path; never splice user text into a body.

## Update

- Change the base text: `PATCH .../tooling/sobjects/ExternalString/<id>` with `{Value}`. (`sf data update record` and `dispatch` take a plain update; `sf api request rest` returns 405 on a plain `PATCH`, so avoid it.)
- Change or add a translation: `PATCH` the existing `LocalizedValue`, or `POST` one for a new language.

## Remove

`DELETE .../tooling/sobjects/EmbeddedServiceCustomLabel/<junction id>` (no body). Deleting the binding also deletes the `ExternalString` and its translations; do not delete those separately.

---

## Transport

Tooling calls go through `dispatch` / `dispatch_readonly` on the raw route (`/services/data/vXX.0/tooling/...`); every call above, including `PATCH` and `DELETE`, was verified that way on the test gateway. Fall back to the `sf` CLI only on the named signals in contract §2. The CLI path was verified end to end on the test org; use `sf data ... record --use-tooling-api`, not `sf api request rest`:

| Step | Command |
|---|---|
| Read | `sf data query --use-tooling-api -q "<SOQL>"` |
| Create | `sf data create record --use-tooling-api -s <ExternalString\|EmbeddedServiceCustomLabel\|LocalizedValue> -v "Field='value' ..."` |
| Update | `sf data update record --use-tooling-api -s <sObject> -i <id> -v "Value='...'"` (plain update, no `_HttpMethod` override) |
| Remove | `sf data delete record --use-tooling-api -s EmbeddedServiceCustomLabel -i <junction id>` (cascades as above) |

With `--json`, the output can carry control characters and a CLI update warning on stdout. Strip control characters (`tr -d '\000-\010\013-\037'`) before `jq`, and read each new record's `result.id` before the next step. A duplicate bind returns "duplicate value found: EmbeddedServiceConfigId duplicates value on record with id ...". The CLI fails the same way `dispatch` does on `DUPLICATE_VALUE`, so detect first.

---

## Publish

Writing labels changes the draft only. Follow SKILL.md step 17c: stop, give the review link, and publish only on an explicit yes in that turn. Delegated: never publish, and always end with the contract section 5 result (`status`, `errorMessage`, `outputs` with `published: false`) as the final reply, naming what was written or which prerequisite failed. Do not end with prose only.

---

## Gotchas

| Issue | Resolution |
|---|---|
| Label saved but missing from the Setup language dropdown | The language is not enabled in Translation Workbench; give the Setup step |
| Label does not show at all | Translation Workbench is off, or the deployment was not republished |
| Publish fails after adding a label | `ExternalString.Category` is not `EmbeddedMessaging` |
| `DUPLICATE_VALUE` on bind | The key is already bound to this deployment; update it instead |
| `INVALID_INPUT: Object is not supported for this deployment type` | Mobile accepts only the T&C and Fallback keys; API accepts none. Delete the orphan `ExternalString` |
| Label saved but missing from the Setup Custom Labels list or the widget | The key may belong to the other Web version (v1 vs v2). Remove it and pick a key Setup shows for this deployment |
| Label shows in Setup but not the widget | Not yet republished, or the key maps to different text than expected. Check the Chat Group and Label Type rows in Setup |

## Verification Checklist

- [ ] Translation Workbench is enabled and every needed language is `IsActive`
- [ ] Deployment type supports labels (not API; Mobile only the two keys); `LabelKey` is in the describe's picklist (prefer `EM_*`)
- [ ] Web: the v1/v2 warning was given and the Setup review link asks the user to confirm the row
- [ ] `ExternalString` has `Category = EmbeddedMessaging` and the Setup-shaped `Name` (confirmed by read-back, not assumed)
- [ ] Exactly one `EmbeddedServiceCustomLabel` per key for the deployment (re-query after the writes)
- [ ] Labels were not added to `EmbeddedServiceConfig` XML
- [ ] Publish waited for an explicit yes; the Setup review link was given
