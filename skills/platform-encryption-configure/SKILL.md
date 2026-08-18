---
name: platform-encryption-configure
description: "Configure Salesforce Shield Platform Encryption — generate deployable encryption settings and encrypted-field metadata, and answer key-model and lifecycle questions. TRIGGER when: user wants to turn on deterministic encryption, encrypt a field, set up Cache-Only Keys, External Key Management, or replay detection, or mentions Shield Platform Encryption, encryption at rest, deterministic vs probabilistic encryption, encryptionScheme, PlatformEncryptionSettings, EncryptionKeySettings, BYOK, BYOKMS, tenant secrets, key rotation, or .settings-meta.xml / .field-meta.xml for encryption — even when they don't say 'Shield'. SKIP when: user needs a generic custom field with no encryption (use platform-custom-field-generate), needs the raw Metadata API type reference (use platform-metadata-api-context-get), or asks about Classic Encryption (encrypted text fields), which is a different feature. Use this skill for any Platform Encryption configuration, field-encryption, or key-model question."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "62.0"
  relatedSkills:
    - "platform-custom-field-generate"
    - "platform-metadata-api-context-get"
---

# Configure Platform Encryption

Configures Salesforce Shield Platform Encryption by generating the metadata that turns it on and choosing the right settings: which encryption scheme a field should use, which key-management model fits a requirement, and how the tenant-secret lifecycle works. This is a **hybrid** skill — it emits deployable `*.settings-meta.xml` / `*.field-meta.xml` where Platform Encryption exposes a real Metadata API surface, and returns grounded guidance where the operation is UI/REST-only.

## Scope

- **In scope**: choosing and applying `encryptionScheme` on a field; enabling deterministic encryption, Cache-Only Keys, External Key Management, and replay detection via `PlatformEncryptionSettings` / `EncryptionKeySettings`; explaining BYOK / BYOKMS / EKM / Cache-Only key models; tenant-secret rotation and destruction semantics; the query behavior of encrypted fields.
- **Out of scope**: a plain custom field with no encryption (use `platform-custom-field-generate`); the raw Metadata API field reference (use `platform-metadata-api-context-get`); Classic Encryption (`EncryptedText` fields) — that is a separate, legacy feature; deploying/pushing metadata to an org (that belongs to a deploy lifecycle skill).

---

## Required Inputs

Gather or infer before proceeding:

- **Question type**: is the user asking for a *deployable artifact* (a settings file, an encrypted field) or *guidance* (which model, what happens when I rotate a key)? Deployable → generate XML from `assets/`. Guidance → answer from `references/`. **A question is guidance whenever the ask is to explain, confirm, or compare** — "is that right?", "what's the relationship?", "can we…?", "is there an ordering requirement?", **"explain the difference between X and Y", "which key model should we use?"** — **even if the user also says they are about to write, deploy, or author settings themselves.** The user writing settings is *their* action; it does not make the skill's deliverable a file. Only an explicit "generate / create / give me the file / here is my field, encrypt it" is an artifact request.
- **Key-model choice questions are guidance, not deployable metadata.** "Explain BYOK vs external key management / BYOKMS / EKM / Cache-Only", "which one keeps key material out of Salesforce?", "should we use BYOK or EKM?" → answer them in a **single markdown answer file** (the guidance write-up), not a deployable `*.settings-meta.xml`. **Naming the enabling setting in that answer (e.g. `canExternalKeyManagement`, `enableCacheOnlyKeys`) does NOT turn it into a settings artifact** — cite the field name inline in the answer file; do **not** emit an `EncryptionKey.settings-meta.xml` unless the user explicitly says "generate/create the settings file."
- **Field encryption target** (for field work): the object and field API name, and whether the user needs to *filter, sort, or group* on the field (drives deterministic vs probabilistic).
- **Key model** (for key work): whether keys are Salesforce-derived (default), customer-supplied (BYOK), stored in an external KMS (BYOKMS/EKM), or fetched on demand (Cache-Only).

If the request is clear, generate or answer immediately — do not interrogate the user.

---

## Workflow

1. **Classify the request** — deployable artifact vs guidance, using the Required Inputs above. Then **scope the output to exactly what was asked**:
   - A **guidance** question produces **exactly one markdown answer file** — a single file (e.g. `answer.md`) containing the full written diagnosis/explanation — and **nothing else**. Do not also emit a `*.settings-meta.xml`, a `*.field-meta.xml`, or a second helper doc. This covers every "what happens when…?", "how do I…?", "which model…?", "is X right…?", "can we…?", "what's the relationship / ordering…?" question, including query-behavior and Cache-Only/replay questions. **A clause like "before I write our settings" or "before I author the file" describes the *user's* next step and does NOT turn the question into a deployable-metadata request — write the answer file, not a settings file.**
   - **Naming a metadata change in a guidance answer does NOT mean emitting the deployable file for it.** A remediation or diagnosis question — *"how do I make the field queryable?"*, *"why did my query fail and how do I fix it?"*, *"which key model keeps material out of Salesforce?"* — is answered **inside the one markdown answer file**, naming the relevant element/scheme inline (e.g. "switch to a `Deterministic*` scheme and enable `enableDeterministicEncryption`", or "use External Key Management — `canExternalKeyManagement`"). Do **not** additionally materialize a `*.field-meta.xml` or `*.settings-meta.xml` to *demonstrate* that change — mentioning the element in the answer is the complete deliverable. Produce a deployable metadata file **only** when the user explicitly says generate/create/give me the field or settings file.
   - An **artifact** request gets **only** the specific metadata file(s) named — do not add a `DEPLOYMENT_GUIDE.md`, `README.md`, an `EXPLANATION.md`, an org-`settings` file, or any companion artifact the user did not ask for.
   - If a deploy step or org setting is a prerequisite, state it **inside the one answer file** (for guidance) or **in a code comment inside the one artifact** (for an artifact request) — never as an extra file.

2. **For field encryption** — read `references/encryption-schemes.md` to choose the scheme, then load `assets/encrypted-field.field-meta.xml` as the starting template. Set `encryptionScheme` to exactly one of the four valid enum values (see the reference). Only `Deterministic*` schemes are filterable.

   > **Write the field file at the SFDX source path, not the root.** A `*.field-meta.xml` **must** live at `objects/<ObjectApiName>/fields/<FieldApiName>__c.field-meta.xml` (e.g. `objects/Patient__c/fields/Diagnosis_Notes__c.field-meta.xml`) — the object folder uses the object's API name (`Patient__c` for a custom object, `Contact` for a standard one) and the file is named after the field API name. Emitting the file at the repo root, in a flat directory, or under any other folder is a structural miss even when the XML itself is correct.

3. **For org-level encryption settings** — load `assets/PlatformEncryption.settings-meta.xml` (deterministic encryption, field-history encryption, MEK permission) or `assets/EncryptionKey.settings-meta.xml` (Cache-Only, EKM, Data 360, transactional DB, replay detection). Read `references/key-models.md` before setting any key-model field.

   > **Name the output file after the Settings *member*, not the root element, and write it under `settings/`.** A `Settings` file must be `settings/<member>.settings-meta.xml`, where `<member>` is the org's metadata member name — **`EncryptionKey`** (root `<EncryptionKeySettings>`) and **`PlatformEncryption`** (root `<PlatformEncryptionSettings>`). Put it in the `settings/` source folder (e.g. `settings/EncryptionKey.settings-meta.xml`), not the repo root. Naming the key-settings file `Encryption.settings-meta.xml` or `EncryptionKeySettings.settings-meta.xml` fails deployment with *"The object '…' of type Settings metadata does not exist."*

   > **Cache-Only Keys and replay detection are a one-way dependency, not an auto-enable.** You may set `enableReplayDetection` only after `enableCacheOnlyKeys` is `true`; enabling Cache-Only does **not** turn replay detection on by itself. An org can validly run Cache-Only with replay detection off.

4. **For tenant-secret operations** (rotate, destroy, BYOK upload, Cache-Only callout setup) — read `references/tenant-secret-lifecycle.md`. These are UI/REST-only; capture the guidance in the single markdown answer file, not a deployable metadata file.

5. **Validate any generated settings XML** — run `scripts/validate-encryption-metadata.sh` with the file path as its argument, and fix anything it reports. It checks the replay-detection dependency and the `encryptionScheme` enum deterministically.

6. **Compare against the worked example** — verify a generated `EncryptionKeySettings` file against `examples/cache-only-keys.settings-meta.xml`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| `encryptionScheme` must be exactly one of `CaseInsensitiveDeterministicEncryption`, `CaseSensitiveDeterministicEncryption`, `None`, `ProbabilisticEncryption` | These are the only values the Metadata API accepts (`CustomField`, API 44.0+); any other string fails deployment. |
| Set `enableReplayDetection` only when `enableCacheOnlyKeys` is `true` | The contract is *"Requires enableCacheOnlyKeys=true before setting enableReplayDetection to true"* — a one-way dependency. |
| Use deterministic schemes only when the field must be filtered, sorted, or grouped | Probabilistic is stronger but non-filterable; deterministic trades some cryptographic strength for queryability. |
| Never claim a filter/sort/group on a probabilistically-encrypted field silently returns zero rows | The platform **rejects** the query with `INVALID_FIELD` (see gotchas); telling the user it "returns nothing" is factually wrong. |
| Do not emit `enableExternalKeyManagement` — the field is `canExternalKeyManagement` | The WSDL element is `canExternalKeyManagement`; the sample in some docs uses a non-existent element name. |
| Transactional-DB, EKM, and Data 360 key fields require API 63.0+ | `canEncryptTransactionalDatabase`, `canExternalKeyManagement`, `canManageDataCloudKeys` were introduced in 63.0. |
| A **guidance** question produces **exactly one markdown answer file** — never a deployable `*.settings-meta.xml` / `*.field-meta.xml`, and never a second doc | The answer file is the user's reference document — it persists in the workspace and can be shared or revised. Emitting a deployable metadata file for a guidance question is unsolicited configuration that could be accidentally applied; emitting no file leaves the user without a tangible deliverable. |
| An **artifact** request emits **only** the metadata file(s) asked for — no companion files | Adding a `DEPLOYMENT_GUIDE.md`/`README.md`/`EXPLANATION.md` or an extra `settings` file the user didn't request is noise. Prerequisites belong in a code comment inside the artifact, not a second file. |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Filtering/sorting/grouping on a probabilistically-encrypted field | The query is rejected with `INVALID_FIELD`: *"field '<Name>' can not be sorted / filtered / grouped in a query call."* Switch the field to a deterministic scheme if queryability is required. |
| Assuming Cache-Only Keys auto-enables replay detection | It does not. Set `enableReplayDetection` explicitly, and only after `enableCacheOnlyKeys=true`. |
| Case sensitivity in deterministic matching | `CaseSensitiveDeterministicEncryption` matches exact case; `CaseInsensitiveDeterministicEncryption` normalizes case. Choosing wrong silently breaks equality filters. |
| Confusing BYOK with BYOKMS/EKM | BYOK = you upload key material Salesforce stores; BYOKMS/EKM = key material stays in your external KMS. See `references/key-models.md`. |
| Using `enableExternalKeyManagement` element name | Wrong element. The field is `canExternalKeyManagement`. |
| Classic Encryption vs Shield | `encryptionScheme` is Shield only. `EncryptedText` custom fields are the legacy Classic feature and out of scope. |

---

## Output Expectations

Deliverables depend on the request — produce **exactly** these and nothing more:

- **Guidance questions produce exactly ONE markdown answer file.** Any "what happens when…", "how do I…", "which model…", "is X right…" question — including encrypted-field query behavior, Cache-Only/replay-detection relationships, tenant-secret / BYOK / Cache-Only lifecycle, and key-model choices — is answered by writing a single markdown file (e.g. `answer.md`) that fully captures the diagnosis/explanation. Do **not** additionally emit a deployable `*.settings-meta.xml` / `*.field-meta.xml` or a second doc, and do **not** answer with no file at all — the answer file is the user's persistent reference document.
- **Field encryption artifact**: **only** the `*.field-meta.xml` with `encryptionScheme` set, written at `objects/<ObjectApiName>/fields/<FieldApiName>__c.field-meta.xml`. Not a settings file, not a deploy guide. Pick `<type>` to match the request: **`Text`** for a string field up to **255** chars; **`LongTextArea`** only when the field must exceed 255 chars (256+). "Long text … up to 255 characters" is a `Text` field, not `LongTextArea`. Strip the template's instructional comment block from the delivered file — ship clean metadata. **Keep the accompanying chat prose tight — one or two sentences naming the scheme chosen and why (e.g. "ProbabilisticEncryption — strongest at-rest protection; the field can't be filtered/sorted/grouped, which matches your no-query requirement"). Do not restate the whole prompt, enumerate every scheme, or add setup/deployment walkthroughs; the deliverable is the file, not an essay.**
- **Org settings artifact**: **only** the settings file the request needs, at `settings/<member>.settings-meta.xml` named after its Metadata API member — `settings/PlatformEncryption.settings-meta.xml` (root `<PlatformEncryptionSettings>`) and/or `settings/EncryptionKey.settings-meta.xml` (root `<EncryptionKeySettings>`). Do **not** name the file after the root element, and do **not** drop it at the repo root.

Do **not** add companion files (`DEPLOYMENT_GUIDE.md`, `README.md`, an extra org-settings file) that the user did not ask for — state prerequisites in a code comment inside the artifact, or inside the single answer file for guidance. File structure follows the templates in `assets/`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| A custom field with no encryption | `platform-custom-field-generate` |
| The raw Metadata API type/field reference | `platform-metadata-api-context-get` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/encrypted-field.field-meta.xml` | Before generating an encrypted custom field |
| `assets/PlatformEncryption.settings-meta.xml` | Before generating org encryption-policy settings (member `PlatformEncryption`) |
| `assets/EncryptionKey.settings-meta.xml` | Before generating key-management settings — Cache-Only, EKM, Data 360 (member `EncryptionKey`) |
| `references/encryption-schemes.md` | When choosing deterministic vs probabilistic, or explaining encrypted-field query behavior |
| `references/key-models.md` | When configuring or explaining BYOK / BYOKMS / EKM / Cache-Only key models |
| `references/tenant-secret-lifecycle.md` | When the user asks about key rotation, destruction, or BYOK upload |
| `examples/cache-only-keys.settings-meta.xml` | To verify a generated Cache-Only key-settings file |
| `scripts/validate-encryption-metadata.sh` | After generating any settings XML — validates the replay dependency and scheme enum |
