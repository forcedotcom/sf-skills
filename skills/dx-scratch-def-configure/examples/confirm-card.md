# Example confirm card (Generate)

Show this card in chat with the preview JSON. Do not put the JSON in report.md.

Intent paraphrase: Developer-edition scratch-def for a B2B Revenue Cloud
project. Features are what the helper mapped from the user's words — not
extra catalog tokens.

- Edition: Developer
- Features: CoreCpq
- Settings enriched:
  - revenueManagementSettings.enableCoreCPQ = true
- Output path (after confirm): config/project-scratch-def.json

**Required in the chat reply (not in report.md):** show the schema-valid
helper `document` as a fenced JSON block. Example:

```json
{
  "edition": "Developer",
  "features": [
    "CoreCpq"
  ],
  "settings": {
    "revenueManagementSettings": {
      "enableCoreCPQ": true
    }
  }
}
```

Write file?

Write only if they accept this preview unchanged. A first generate that says
write or skip preview still uses this card. Write + change → preview
again, do not apply. After they accept: apply, show the **final written JSON**
in chat.

Pass the user's product or cloud words in the features array as-is.

## Refine diff card

Show this when patching an existing file. Source the bullets from helper
`diff` (preview --base with a structured delta). Do not put the JSON in
report.md.

Intent paraphrase: Add Communities to the existing Developer scratch-def.

Delta sent (example): `{"addFeatures":["Communities"]}`

- Base: config/project-scratch-def.json
- baseSha256: (from helper — optional on apply as a race guard)
- Features added: Communities
- Features removed: (none)
- Features quantity changed: (none) — or e.g. EducationCloud:3 → EducationCloud:5
  from helper `featuresQuantityChanged` (same-base quantity edits)
- Edition: unchanged (Developer)
- Fields added/removed/changed: (none) — or list top-level keys from helper
  `fieldsAdded` / `fieldsRemoved` / `fieldsChanged`
- Settings added: communitiesSettings.enableNetworksEnabled = true
- Settings removed: (none)
- Settings changed: (none) — or list paths whose values changed
  (helper `settingsChanged`)
- Orphaned required settings: (none)

**Required in the chat reply (not in report.md):** show the schema-valid
resulting helper `document` as a fenced JSON block.

Write file?

If orphaned required settings are listed, ask whether to delete them before
writing. Removing a feature does not silently delete unrelated settings.

## Shape + features variant

User supplied sourceOrg (or snapshot id/name).

- sourceOrg: 00D000000000001AAA
- Features: Communities, API
- Settings: communitiesSettings.enableNetworksEnabled = true
- Output path (after confirm): config/project-scratch-def.json

**Required in chat:** fenced JSON of preview `document` (sourceOrg + features +
enriched settings).

Write file?
