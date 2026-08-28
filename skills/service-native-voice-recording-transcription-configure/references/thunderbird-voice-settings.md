# ThunderbirdVoiceSettings — Metadata API contract

Reference for enabling Native Voice (Thunderbird Voice) recording and transcription
via the Metadata API, using the sf CLI `Settings`-container retrieve/deploy path.
Read this when constructing or debugging `scripts/enable-recording-transcription.sh`.

## The metadata type

`ThunderbirdVoiceSettings` is a singleton settings type (extends `Metadata`),
addressed by a fixed `fullName`:

- **type (mdApiType)**: `ThunderbirdVoiceSettings`
- **fullName**: `ThunderbirdVoice`

This skill manages exactly two boolean preferences:

| Field | Meaning | This skill |
|-------|---------|------------|
| `enableCallRecording` | Capture audio of Native Voice calls | **set `true`** (target) |
| `enableCallTranscription` | Produce transcripts of Native Voice calls | **set `true`** (target) |

Recording and transcription are independent — a call can be recorded without being
transcribed and vice versa — so they are always modeled and reported as two separate
preferences.

The type may expose other booleans (e.g. `enableCallRecRedaction`,
`enableRealTimeStreamingRecording`, `enableSipRecording`). They are **out of scope** to
*change*: the skill reads them only to preserve their existing values on the deployed
file. It does, however, **echo them back unchanged** in a `preserved` block of the
confirmation JSON — reporting a sibling's retrieved value is not the same as setting it,
and compliance callers rely on that block for explicit "nothing else moved" assurance.
No sibling is ever reported as changed.

## Why the sf CLI, not raw SOAP

`ThunderbirdVoiceSettings` is not a retrievable top-level type name, so it is easy to
conclude "raw SOAP `updateMetadata()` is the only path." That is wrong. The generic
**`Settings`** container type *is* in the sf CLI metadata registry, and its member is
the mdApiType **without** the trailing `Settings` — i.e. `ThunderbirdVoice`. Retrieving
and deploying through that container:

- authenticates with the org's existing **`sf` login** — no browser session id /
  access token is ever handled (raw SOAP on internal pc-rnd orgs rejects CLI OAuth
  sessions on the SOAP endpoint, which is why a SOAP path there needs a browser sid);
- lets us **retrieve first** to check the gate and snapshot sibling prefs, then deploy
  a full file that preserves them;
- gives a built-in **verify** step (round-trip retrieve).

## The manifest

`assets/package.xml` is the manifest template (the script generates it into a temp
SFDX project). Two things matter:

```xml
<types><members>ThunderbirdVoice</members><name>Settings</name></types>
<version>68.0</version>
```

- **member** = `ThunderbirdVoice` (mdApiType minus `Settings`), **name** = `Settings`.
- **Pin the version to 68.0.** `ThunderbirdVoiceSettings` fields are only exposed at
  API **v68.0 and above**, so anything below 68.0 returns the type empty/absent — the
  fields simply are not in the schema at those versions. But do NOT reach for the CLI's
  newest default either: a retrieve/deploy at a version **above the org's max supported
  API** SILENTLY returns an empty result (no error), indistinguishable from "feature not
  provisioned". 68.0 is the field-exposure floor and works on every org that has the
  feature. (Verified sweep on thb-einstein, org max v68.0: v64/62/60 → "Settings type
  'ThunderbirdVoice' is unknown"; v65/66/67 → type absent; v68 → fields present, deploy
  round-trips; **v69 → success:true but files:[] — silent empty**.)

## Sequence

1. **Retrieve** `-x package.xml` → `force-app/main/default/settings/ThunderbirdVoice.settings-meta.xml`.
2. **Gate check.** If the file is an empty self-closing `<ThunderbirdVoiceSettings/>`
   (no fields), the org-perm gate `ThunderbirdVoice.orgHasNativeVoiceAllowed` is **off**
   — Native Voice is not provisioned. Stop; this is enabled via provisioning/Blacktab,
   not this skill. If the fields are listed, the gate is on — proceed.
3. **Flip** `enableCallRecording` and `enableCallTranscription` to `true`; leave every
   sibling field at its retrieved value.
4. **Validate** with `deploy --dry-run` (never skip).
5. **Deploy**.
6. **Verify** by re-retrieving and confirming the org *returns* both `true`.

## Distinguishing the two failure modes

| Symptom | Cause | What to do |
|---------|-------|------------|
| Retrieve returns fields, deploy round-trips | Working as intended | done |
| Retrieve returns an **empty** `<ThunderbirdVoiceSettings/>` | Org-perm gate off (feature not provisioned) | provision / Blacktab — not fixable via metadata |
| Retrieve returns **no** settings file, or `Settings` type "unknown" | **API version too low** (< 68.0) | raise `--api-version` to 68.0+ |

> The historical `FIELD_INTEGRITY_EXCEPTION: Property 'enableCallRecording' not valid
> in version <N>` error was **a version problem, not a feature gate** — it appeared when
> the request used an API version below 68.0. Bumping to v68.0+ resolves it. Do not
> mistake it for an unprovisioned feature; distinguish the two with the retrieve gate
> check above.

## Auth

`scripts/enable-recording-transcription.sh --target-org <alias>` uses the sf CLI's
existing authentication for that alias (confirm with `sf org display -o <alias>`). No
session id or access token is requested, handled, or printed.
