---
name: automation-sandbox-post-copy-config-generate
description: "Generate the JSON config file that the Salesforce sandbox post-copy automation tool consumes, from a customer SOP in any format (PDF, xlsx, csv, JSON, docx, Markdown, plain text, or a screenshot of an endpoint table). Use when the user asks to create, build, generate, produce, or convert a post-copy or post-refresh automation config — turning a sandbox-refresh SOP into a JSON array of OutboundMessages and RemoteSiteSettings entries with ConfigurationName, Label, Fields, IsActive, and ExecutionOrder. Also trigger for phrasings like \"post-copy config\", \"post-refresh automation JSON\", \"update the outbound message (OBM) endpoints after refresh\", \"convert this SOP to config\", \"remote site settings JSON\", \"refresh planner to JSON\", or \"sandbox refresh config\". DO NOT TRIGGER when: user wants to deploy the generated config to an org (use platform-metadata-deploy) or execute/run the post-copy automation tool. This is the only skill for Salesforce sandbox post-copy config generation."
metadata:
  version: "1.0"
---

# Automation: Sandbox Post-Copy Config Generate

Convert a customer's sandbox-refresh / post-copy SOP into a structured JSON
array that the post-copy automation tool consumes. Each entry is a
declarative instruction: which Salesforce configuration to update, which
fields are involved, whether it is active, and what order it runs in.

## STOP — do this before writing any JSON

Do **not** compose the output from memory. Before you write the file, you
MUST open and read `assets/config_template.json` and copy an entry from it
for each action. Every output entry is exactly one of these two shapes —
five top-level keys, no others, no wrapper object:

```json
[
  {
    "ConfigurationName": "OutboundMessages",
    "Label": "IR_Account_OBM_PROD",
    "Fields": { "EndpointUrl": "https://uat.example.com/services/account", "Object": "Account" },
    "IsActive": true,
    "ExecutionOrder": 1
  },
  {
    "ConfigurationName": "RemoteSiteSettings",
    "Label": "R12_Remote_Site",
    "Fields": { "RemoteSiteUrl": "https://uat.example.com" },
    "IsActive": true,
    "ExecutionOrder": 2
  }
]
```

- `ConfigurationName`: exactly `OutboundMessages` or `RemoteSiteSettings` — never `Type`, `Name`, or `Operation`.
- OBM `Fields`: `EndpointUrl` + `Object` (both required). RemoteSite `Fields`: `RemoteSiteUrl` only — never `Url`/`RemoteSiteURL`.
- Top level is a JSON array. No `steps`/`actions`/`records` wrapper. No `<…>` or `REPLACE_WITH_…` placeholder ever survives into the output.

If you announce "I will now write …" without having read the template and
catalog, stop and read them first — a from-memory guess produces the wrong
keys and fails at runtime.

## Scope

- **In scope**: Reading a customer SOP in any of the supported formats
  (PDF, xlsx, csv, JSON, docx, Markdown, plain text, pasted excerpt, or
  images containing data tables — e.g., a screenshot of an
  Outbound Messages list with endpoint URLs), identifying post-copy /
  post-refresh actions, mapping each action to a supported
  `ConfigurationName`, emitting the canonical JSON array.
- **Out of scope**: Generating Salesforce metadata XML (delegate to
  `generating-*` skills), deploying anything to an org, running the
  post-copy tool, inferring or fabricating values not present in the SOP —
  if the SOP does not give a concrete URL/value for an action, skip the
  action.

**Every emitted entry must have every Field populated with a real value
from the customer source.** No empty strings, no `null`, no
`<from-backup>` / `TBD` / `TODO` placeholders. Customers should never
see an unpopulated field in the output — if a value cannot be located,
skip the entry and surface it. See the corresponding rule below.

---

## Required Inputs

Gather or infer before generating:

- **SOP source(s)**: One or more paths (or pasted content) in any of:
  PDF, xlsx, csv, JSON, docx, Markdown, plain text, or images
  (.png/.jpg/.jpeg/.tiff/.bmp). Multiple files are common — the action
  list and the endpoint table sometimes live in different files. Read
  every file the user supplies.
- **Target output path**: Where the JSON config should be written. Default
  to `post-copy-config.json` in the current directory unless specified.
- **Scope filter** (optional): If the SOP covers many environments
  (e.g., fcQA, fcUAT, multiple sandboxes), confirm which subset the user
  wants in the output.

If the user provides a clear SOP and target, generate immediately without
asking unnecessary questions.

---

## Workflow

All steps are sequential. Steps 1–5 (reading the SOP, the catalog, the
template, and the schema) are **prerequisites to writing** — you may not
skip to the write step. If you catch yourself about to emit JSON without
having read `assets/config_template.json` and
`references/configuration_catalog.md`, go back and read them first.

1. **Locate and read every supplied SOP source** — read
   `references/source_format_handling.md` for the exact extraction
   recipe per format (PDF, xlsx, csv, JSON, docx, image). At a glance:
   - **PDF**: extract text with `pypdf` (text layer) and OCR
     image-based pages with `pytesseract` if the text layer is empty.
   - **xlsx**: read every sheet with `openpyxl` (`data_only=True`),
     scan all columns including ones outside the visible default
     range, check cell comments and embedded media.
   - **csv / JSON / Markdown / text**: read directly.
   - **docx**: extract paragraphs and tables with `python-docx`.
   - **Images** (.png/.jpg/...): use the `Read` tool to view, then
     decide if the image carries data (a table of endpoint URLs, a
     setup screenshot showing values to capture) or is purely
     illustrative (architecture diagram, flow chart). Extract values
     only from data-bearing images. See the image-handling rules in
     `references/source_format_handling.md`.
   - For very large SOPs (>50 pages / >20 sheets), focus on sections
     or sheets titled "Post Refresh", "Post-Copy", "Post-Refresh
     Steps", "Update …", or equivalent.

2. **Identify post-copy actions** — read
   `references/sop_parsing_patterns.md` for the heuristics that turn prose
   instructions ("Update Outbound Message endpoint X to URL Y") into
   structured action records.

3. **Map each action to a `ConfigurationName`** — load
   `references/configuration_catalog.md`. The catalog currently supports
   only `OutboundMessages` and `RemoteSiteSettings`. Any action that
   targets a different configuration type is out of scope: skip it and
   list it in the response so the user can extend the catalog later.

4. **Read the JSON template** — load `assets/config_template.json`. It
   shows the exact required shape of one `OutboundMessages` entry and one
   `RemoteSiteSettings` entry, with `<…>` placeholder slots. Copy an
   entry, replace every `<…>` slot with the concrete SOP value, and keep
   the exact top-level keys (`ConfigurationName`, `Label`, `Fields`,
   `IsActive`, `ExecutionOrder`) — never rename them to `Type`, `Name`,
   `Operation`, etc. Never emit an entry that still contains a `<…>`
   placeholder; if you cannot fill a slot, skip the entry (see Rules).

5. **Validate against the schema** — load `assets/json_schema.json`. Every
   entry must conform: `ConfigurationName` is one of the catalog values,
   `Fields` is an object, `IsActive` is boolean, `ExecutionOrder` is a
   positive integer.

6. **Group entries by phase, then assign `ExecutionOrder`** —
   `ExecutionOrder` is a phase number, not a per-row counter. Entries that
   can run in parallel (no dependency between them) share the same value.
   Different `ConfigurationName` types typically get different phases; all
   entries within one phase share its number. See the ordering heuristic
   in `references/sop_parsing_patterns.md`.

7. **Compare against the example** — verify the output shape against
   `examples/sample_sop_to_config.json` before writing.

8. **Write the JSON file** — emit pretty-printed JSON (2-space indent).

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Output is a JSON array at the top level (not an object with a wrapper key) | The post-copy tool consumes an array directly |
| Every entry has all five required keys: `ConfigurationName`, `Label`, `Fields`, `IsActive`, `ExecutionOrder` | The tool fails fast on missing keys; partial entries are not silently accepted |
| `ConfigurationName` is one of the catalog values | Unknown values cause the runtime mapper to error out — never invent a new type without updating the catalog |
| `Fields` keys are the actual API field names on the target metadata | Wrong key names mean the tool can't locate the field at runtime |
| `Fields` values are the concrete values from the SOP (literal URLs, names, etc.) | The post-copy tool applies the value as-is; placeholders are not resolved at runtime |
| If the SOP names an action but no concrete value (URL, etc.) is provided, **skip the entry** entirely and list it in the response | Generating an entry without a real value would produce a silent no-op or a deployment error at runtime |
| Every Field in every emitted entry must be a real value sourced from the customer's SOP or a supplemental sheet they provided. Never emit `""`, `null`, or placeholder markers like `<from-backup>` / `TBD` / `TODO` | Customers consume the JSON directly — empty / placeholder fields surface to them as broken output and would also fail at runtime |
| Before skipping an OBM / RemoteSite for missing values, **search every tab / sheet of the supplied workbook (and every supplied file)** for an endpoint table keyed by that name | Customer SOPs frequently split the action list and the URL table across different sheets (e.g., the Michelin UAT Refresh Planner lists OBMs in the Integration tab but the URL table lives in the Evolution SFA tab) |
| Information already captured by another field is **not** repeated in `Fields` (e.g., `RemoteSiteName` lives in `Label`, `IsActive` lives at the top level — neither belongs in `Fields`) | Duplicate keys make the entry ambiguous and waste bytes the tool then has to reconcile |
| For `OutboundMessages`, `Fields` MUST include both `EndpointUrl` and `Object` (the target SObject — `Account`, `Contact`, `Asset`, `Lead`, etc.) | Same Label can apply to multiple OBMs differing only by entity; `Object` disambiguates them at runtime |
| For `RemoteSiteSettings`, the URL key MUST be spelled exactly `RemoteSiteUrl` — never `Url`, `RemoteSiteURL`, `SiteUrl`, or `EndpointUrl` | The post-copy tool matches the field by exact API name; any other spelling means it can't locate the field and the entry silently no-ops at runtime |
| `ExecutionOrder` is a phase number — entries with no dependency on each other share the same value | The post-copy tool runs all entries with the same `ExecutionOrder` in parallel; sequencing is only needed where one action depends on another |
| `IsActive: false` entries remain in the output (do not delete them) | The customer toggles them on per-environment; deleting loses traceability |
| Default `IsActive` to `true` when the SOP marks an action as required | Most SOP steps are required; explicit opt-out is the exception |

### Canonical entry shape

See the entry shapes shown in the STOP section above, or copy directly from
`assets/config_template.json`. Do **not** rename the five top-level keys
(`ConfigurationName`, `Label`, `Fields`, `IsActive`, `ExecutionOrder`) to
`Type`, `Name`, `Operation`, `apiName`, etc., and do **not** wrap the array
in an object with a `steps` / `actions` / `records` key.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| SOP step says "delete all endpoints" rather than "update X to Y" | Emit an entry with `ConfigurationName: "OutboundMessages"`, `Label` describing the deletion target, and a note in `Fields` (`{"Action": "Delete"}`); the catalog documents the Delete pattern |
| Same Label appears for multiple environments (fcQA + fcUAT) | Emit one entry per environment; suffix the Label or use the environment-specific Label as it appears in the SOP |
| For OutboundMessages, the same Label can legitimately apply to multiple entries when each targets a different `Object` (e.g., one OBM for Account, one for Contact). | Do not collapse them — emit one entry per Object. The `Object` value (inferred from the OBM name like `IR_Account_OBM_PROD` → `Account`) is what distinguishes them, not the Label. |
| SOP groups many Custom Labels together in a single table | One entry per row of the table — do not collapse into a single bulk entry |
| Action targets a setting outside the catalog (CustomLabels, ConnectedApps, NamedCredentials, SSO, CustomSettings, etc.) | Skip the action, do NOT invent a new `ConfigurationName`; list every skipped action in the response so the user knows what to add to the catalog later |
| SOP includes pre-refresh steps interleaved with post-refresh | Filter out pre-refresh — only post-refresh / post-copy actions belong in the output |
| SOP names an outbound message / remote site to update but does not include the new URL | Skip the entry. List the skipped item in the response so the user can supply the URL or amend the SOP |
| SOP includes secrets in URLs (e.g., `https://USER:TOKEN@host/...`) | Embed them verbatim — the tool consumes the value as-is — but flag in the response so the user is aware the JSON now contains a secret and should be stored / shared accordingly |
| User's SOP is in a non-English language or has heavy formatting (tables, callouts) | Extract the prose first, normalize whitespace, then parse — formatting artifacts do not need to survive into the JSON |
| The SOP includes screenshots / images. Some are illustrative (architecture diagrams, flow charts, "this is what the setup screen looks like" examples); others are data-bearing (a screenshot of a real Outbound Messages list, a captured Remote Site table). | Treat illustrative images as out-of-scope — do NOT extract values from them. For data-bearing images (the surrounding text refers to "the values shown below" / "as captured in the screenshot above" / a real Endpoint URL is visible), OCR them and use the values. See `references/source_format_handling.md` for the heuristic. |
| The SOP is supplied as multiple files (e.g., a PDF + a companion xlsx + a screenshot folder), or values are split across tabs / pages | Read every supplied file end-to-end before skipping any entry. The action list and the URL table are frequently in different files — see the rule above about multi-sheet sources. |

---

## Output Expectations

Deliverables:
- A single JSON file (default `post-copy-config.json`) containing a
  top-level array of post-copy action entries.
- A short summary in your response listing: total entries, count per
  `ConfigurationName`, actions skipped because they did not map to the
  catalog, and actions skipped because the SOP did not include a concrete
  value.

The output file structure conforms to `assets/json_schema.json`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Generate the actual Salesforce metadata XML for a Custom Label / Named Credential / Remote Site / etc. | The matching `generating-*` skill |
| Deploy generated metadata or run the post-copy tool against an org | `deploying-metadata` skill |
| Compare an SOP against entities defined in UDD | `udd:research-entities` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/config_template.json` | Step 4 — starting structure for the JSON output |
| `assets/json_schema.json` | Step 5 — validate every emitted entry |
| `references/configuration_catalog.md` | Step 3 — to map an SOP action to a `ConfigurationName` and get the canonical Field keys |
| `references/sop_parsing_patterns.md` | Step 2 and step 6 — heuristics for extracting actions from prose and ordering them |
| `references/source_format_handling.md` | Step 1 — exact extraction recipe per input format (PDF / xlsx / csv / JSON / docx / image) and the data-bearing-vs-illustrative image heuristic |
| `examples/sample_sop_to_config.json` | Step 7 — verify output shape matches expected format |
| `examples/sample_sop_excerpt.md` | Step 7 — see a representative SOP excerpt that produced the sample JSON |
