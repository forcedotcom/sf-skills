# SOP Parsing Patterns

Heuristics for turning SOP prose into post-copy action records.

## Identify the Post-Copy / Post-Refresh section

SOPs are typically structured as:

1. Pre-Refresh Steps (or Pre-Copy)
2. Refresh / Copy Steps (the act of cloning)
3. **Post-Refresh Steps** (or Post-Copy) — this is the section that
   produces actions. Everything else is filtered out.

Section markers to look for (case-insensitive):

- `Post Refresh Steps` / `Post-Refresh Steps`
- `Post Copy Steps` / `Post-Copy Steps`
- `After Refresh`
- `After Copy`

If the SOP has no such section, ask the user which sections are post-copy.

## Action signal patterns

Each post-copy action in the JSON output corresponds to one SOP instruction
that **also includes a concrete value** (URL, etc.). If the value is
missing, skip the action.

### Pattern 1 — "Update X to Y" (Outbound Messages)

> "Update the OBM Messages endpoint for `IR_Account_OBM_PROD` to
> `https://uat.example.com/account`."

- One entry per outbound message named in the SOP.
- `ConfigurationName: "OutboundMessages"`,
  `Fields: { "EndpointUrl": "<literal URL from SOP>", "Object": "<entity>" }`.
- `Label` = the outbound message Name as it appears in the SOP.
- `Object` is **mandatory** — infer from the OBM name
  (`IR_Account_OBM_PROD` → `Account`, `IR_Contact_OBM_PROD` → `Contact`,
  `IR_Asset_OBM_PROD` → `Asset`) or from explicit text in the SOP.
  The same Label may apply to two OBMs that differ only by entity, so
  the post-copy tool relies on `Object` to disambiguate.

If the SOP names the outbound message but does not state the new
endpoint URL ("Update the OBM endpoints" with no table or list of
URLs), **skip** and list the omission in the response. If the target
Object cannot be inferred from the OBM name or surrounding text,
also skip and surface it.

### Pattern 2 — Tabular updates with explicit URL columns

> A table with columns: `Remote Site Name`, `Prod URL`, `UAT URL`,
> `Difference found`.

- One entry per row whose `Difference found` (or equivalent) flag
  indicates the URL changed.
- `ConfigurationName: "RemoteSiteSettings"`,
  `Fields: { "RemoteSiteUrl": "<UAT URL from row>" }`.
- `Label` = the Remote Site Name from the row.
- Skip rows where Prod and UAT URLs are identical (no update needed).
- Do **not** add `RemoteSiteName` to `Fields` (lives in `Label`).
- Do **not** add `IsActive` to `Fields` (lives at the top level).

### Pattern 3 — "Delete all X"

> "Delete all integration endpoints in the OBM Messages setup."

- A single entry with `Fields: { "Action": "Delete" }` and a Label
  describing the deletion target ("All OBM Endpoints" or similar).
  `"Delete"` here is a literal instruction the tool understands.

### Pattern 4 — Sequential / phased instructions

> "First, update the OBM endpoints. Then, update the Remote Site Settings."

- Use the order in `ExecutionOrder`. See "Ordering heuristic" below.

### Pattern 5 — Conditional / environment-specific

> "If you are refreshing fcUAT, do X. For all other sandboxes, do Y."

- Emit both entries. Mark the conditional one with `IsActive: false` so
  the customer can toggle it per-environment, and surface the
  conditionality in your response message.

## Ordering heuristic — `ExecutionOrder` is a phase number

Treat `ExecutionOrder` like a phase / wave number, not a per-row index.
**Entries that have no dependency on each other share the same number.**
The post-copy tool runs all entries with the same number in parallel.

Default phasing (use unless the SOP explicitly says otherwise):

| Phase | Type | Why |
|-------|------|-----|
| 1 | OutboundMessages | Endpoint URLs the rest of the system depends on; no inter-OBM dependency |
| 2 | RemoteSiteSettings | Trusted URLs subsequent integrations need; no inter-site dependency |

Within a single `ConfigurationName`, every entry shares the same phase
number — there is no inter-row dependency among OBMs or among remote
sites. Across types, run OBMs before remote sites unless the SOP says
otherwise.

If the SOP states explicit dependencies ("Step 5 must finish before
Step 6"), break the dependent entry into a later phase.

## Locating values across multi-sheet sources

Customer SOPs often split the **action list** from the **endpoint
table**:

- The "Post Refresh / Post Copy" section names which OBMs / Remote
  Sites need updating, but only by name.
- A separate sheet (or appendix) holds a Prod URL → UAT URL table.

Before skipping an entry for "missing value", search **every tab /
sheet of every file the user supplied** for a row keyed by the same
OBM / RemoteSite / Configuration name. Look for column headers like
`Prod Endpoint URL`, `UAT Endpoint URL`, `Post-refresh URL`, or
`Endpoint`. The post-refresh value is the one to emit.

If after searching every supplied source the value is still not
present, **skip the entry** and list it in the response. Never emit
empty strings, `null`, or placeholder markers (`<from-backup>`, `TBD`,
`TODO`) — customers consume the JSON directly and unpopulated fields
break the tool.

## Filter rules

Skip these — they are not post-copy automation actions:

- Manual ServiceNow ticket creation (process / ops, not metadata).
- "Email the SSO team" / human notifications.
- "Schedule a meeting" / calendar actions.
- "Click Save" / UI navigation breadcrumbs.
- Pre-refresh data collection ("copy the endpoints to a spreadsheet").
- Verification / test steps with no metadata write.
- Any action that targets a configuration type **not** in
  `configuration_catalog.md` (Custom Labels, Connected Apps, Named
  Credentials, SSO, etc.) — list these in your response message so the
  user knows what was filtered and can prioritize extending the catalog.
- Any action where the SOP names the metadata but does not give a
  concrete value (URL, etc.). List these too in the response.

If a section is mostly process and not configuration, note in your
response message that the section was skipped and why.

## Disambiguating Label vs. DeveloperName

When the SOP shows an Outbound Message or Remote Site name like
`R12_Remote_Site`, use that as the `Label` field — this is the
DeveloperName, which is what the post-copy tool resolves at runtime.

When the SOP shows a UI Label like "TK Marine Parts Store Online", that's
ambiguous. Ask the user or pick the most likely API name based on the
surrounding context (the SOP usually shows the API name in setup
breadcrumbs).
