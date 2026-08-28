---
name: service-native-voice-recording-transcription-configure
description: "Enable call recording and call transcription for Native Voice (Thunderbird Voice) programmatically via the Metadata API, for headless / API-driven support where no human uses the Service Console UI. Use this skill when a user asks to turn on, enable, or configure Native Voice recording and/or transcription for headless or automated voice calls. TRIGGER when: users mention Thunderbird Voice, Native Voice, ThunderbirdVoiceSettings, enableCallRecording, enableCallTranscription, 'enable recording and transcription', 'turn on call recording via API', headless voice recording, or configuring voice-call capture without clicking through Setup. DO NOT TRIGGER when: the user wants to redact or scrub PII from existing recordings, transcribe a supplied audio file, or author a Flow/Apex — those are out of scope for this skill."
metadata:
  version: "1.1"
  domains: ["Service"]
  minApiVersion: "68.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Enable Native Voice Recording & Transcription (headless)

Turn on call **recording** and call **transcription** for Native Voice (Thunderbird
Voice) on an org, programmatically, so they take effect for headless / API-driven
support sessions that never touch the Service Console UI. Recording and transcription
are **two separate preferences** — this skill enables both and returns a structured
JSON confirmation.

## Scope

- **In scope**: enabling `enableCallRecording` and `enableCallTranscription` on the
  `ThunderbirdVoiceSettings` metadata via an sf CLI Metadata API deploy (the generic
  `Settings` container, member `ThunderbirdVoice`); returning a JSON confirmation of
  the resulting configuration.
- **Out of scope**: changing any other `ThunderbirdVoiceSettings` boolean (e.g.
  call-recording redaction, SIP recording) — siblings are read only to be preserved,
  never set or reported; redacting/scrubbing PII from existing recordings or
  transcripts; transcribing a supplied audio file; provisioning the Native Voice /
  Thunderbird channel itself; authoring Flow, Apex, or permission sets. These are
  outside this skill's scope — handle them separately.

---

## Required Inputs

Gather or infer before proceeding:

- **Target org** — an org alias or username the sf CLI is authenticated to. The deploy
  uses this existing `sf` login; no session id or access token is requested. Default:
  the org's default target. Confirm connectivity with `sf org display -o <alias>`.
- **Which preferences** — recording, transcription, or both. Default: **both**, since
  headless capture typically needs recording *and* transcription. Confirm only if the
  user named just one.

---

## Workflow

All steps are sequential. Do not skip or reorder. If blocked, stop and ask for the
missing org context.

1. **Confirm the two preferences are modeled separately.** Recording
   (`enableCallRecording`) and transcription (`enableCallTranscription`) are distinct
   booleans on the same metadata type — never collapse them into one combined flag.
   The final confirmation must report each independently.

2. **Run the enable script.** Run
   `scripts/enable-recording-transcription.sh --target-org <alias>`. It retrieves
   `ThunderbirdVoiceSettings` (via the `Settings` container), checks the org-perm gate,
   flips the two target flags to `true` while preserving every sibling, validates with
   a dry-run deploy, deploys, and verifies by round-trip. Use `--dry-run` to retrieve +
   validate without persisting. Run
   `scripts/enable-recording-transcription.sh --help` for all options.

3. **For the Metadata API contract**, read `references/thunderbird-voice-settings.md` —
   it documents the type, the two booleans, the `Settings`-container manifest, the
   **v68.0+** version floor, and the retrieve-first gate check. The manifest template
   the script generates is `assets/package.xml`.

   > This uses the sf CLI Metadata API deploy, not a raw SOAP call. The member is the
   > mdApiType **without** the `Settings` suffix (`ThunderbirdVoice`), and the manifest
   > version MUST be **>= 68.0** — the fields are not exposed at any lower version.

4. **Change only the two target fields.** The deployed settings file sets exactly
   `enableCallRecording` and `enableCallTranscription` to `true`; every other
   `ThunderbirdVoiceSettings` boolean keeps its retrieved value. Do not add or flip
   other booleans — they are out of this skill's scope.

5. **Return the confirmation JSON.** Emit a single JSON object matching
   `assets/confirmation-output.json`: the metadata `type` and `fullName`, that it was
   applied via a headless/API deploy, and — for **each** of the two preferences
   separately — its field name and enabled state, plus an overall `status`. It also
   includes a **`preserved`** array echoing every sibling boolean (e.g.
   `enableCallRecRedaction`, `enableSipRecording`) with the value it was retrieved
   with — this attests the siblings were carried through **unchanged**, which
   compliance callers need as explicit "nothing else moved" assurance. Reporting a
   sibling's value is NOT changing it. On a successful run the script prints this
   object on stdout; surface it verbatim as the deliverable — do not strip the
   `preserved` block.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Model recording and transcription as two separate preferences | They are distinct booleans (`enableCallRecording`, `enableCallTranscription`); collapsing them loses the ability to enable one without the other and fails the output contract. |
| Deploy through the generic `Settings` container with member `ThunderbirdVoice` | `ThunderbirdVoiceSettings` is not a retrievable top-level type name; the `Settings` container (member = mdApiType minus the `Settings` suffix) is the sf CLI path and uses the org's `sf` login — no session id. |
| Manifest version must be >= 68.0 | `ThunderbirdVoiceSettings` fields are only exposed at API v68.0+; below that the retrieve returns the type empty/absent. |
| Retrieve before deploy; preserve all sibling fields | The deploy is a full-file replace — starting from the retrieved file keeps other prefs intact and lets the gate be checked. |
| Report the preserved siblings in a `preserved` block, but never change them | Compliance callers need explicit "nothing else moved" assurance; the confirmation echoes each sibling's retrieved value unchanged. Echoing a value is not setting it — the deployed file still flips only the two target fields. |
| Verify by round-trip before reporting `ENABLED` | A "Succeeded" deploy is not proof; only claim enabled after a re-retrieve returns both `true`. |
| Output must be a single valid JSON object | The confirmation is consumed programmatically by headless callers; prose-only answers are not usable. |
| Do not include a session id, access token, phone number, recording URL, or transcript content in the output | These are secrets / PII; the confirmation reports configuration state only. |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `Property 'enableCallRecording' not valid in version <N>` / `Settings type 'ThunderbirdVoice' is unknown` | **API version too low.** The fields are only exposed at v68.0+. Raise `--api-version` to 68.0 or higher — this is NOT a feature gate. |
| Retrieve returns an empty `<ThunderbirdVoiceSettings/>` (no fields) | Org-perm gate `orgHasNativeVoiceAllowed` is off — Native Voice is not provisioned. Enable via provisioning/Blacktab; metadata cannot flip an unprovisioned feature. |
| Trying to retrieve `ThunderbirdVoiceSettings` as the type name | Use the `Settings` container with member `ThunderbirdVoice` (mdApiType minus the `Settings` suffix); the full type name is not a retrievable member. |
| Collapsing both prefs into one toggle (e.g. `recordingAndTranscription: true`) | Keep two distinct entries in both the deployed file and the confirmation JSON. |
| Deploying a partial settings file | Start from the retrieved file so sibling prefs keep their values; a partial file can reset them. |
| Missing `jq` / `sf` | The script depends on them; install or run in an environment that has them (declared in `metadata.cliTools`). |

---

## Output Expectations

Deliverables:
- A single JSON confirmation object on stdout, shaped per `assets/confirmation-output.json`
  — the metadata target, the headless/API deploy path, each of the two preferences
  reported separately with its enabled state, a `preserved` array echoing every
  sibling boolean (unchanged) so callers can confirm nothing else moved, and an
  overall `status`.

No files are written to the org's source tree — the script works in a temporary SFDX
project and reports the result.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `scripts/enable-recording-transcription.sh` | Step 2 — run to retrieve → flip → validate → deploy → verify (supports `--dry-run`, `--api-version`, `--help`). |
| `references/thunderbird-voice-settings.md` | Step 3 — for the metadata type, the two booleans, the `Settings` manifest, the v68.0+ floor, and the gate check. |
| `assets/package.xml` | Step 3 — the Metadata API manifest template the script generates; read to understand or hand-build the retrieve/deploy. |
| `assets/confirmation-output.json` | Step 5 — the exact shape of the JSON confirmation to return. |
