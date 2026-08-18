---
name: platform-data-and-tooling-api-context-get
description: "Authoritative field/schema reference for 2130 STANDARD Salesforce objects — use to look up standard sObject and Tooling field API names, types, properties (filterable/sortable/groupable/updateable), and relationship names for Account, Contact, Opportunity, Lead, Case, ApexClass, ApexCodeCoverage, TraceFlag, and more. Load this alongside a SOQL/query/Apex skill when the field names, types, or Filter/Sort/Group capabilities are unverified — not when the fields are already known and only query syntax or optimization is needed. TRIGGER when verifying, validating, or debugging fields in a SOQL/SOSL query or DML against a standard object — capabilities, relationship/subquery paths, or what fields an object has — so the query runs instead of guessing. Custom __c objects and __c fields are NOT in these assets; describe the live org for those (sf sobject describe). DO NOT TRIGGER for authoring/deploying *-meta.xml or sfdx source (use the Metadata API skill)."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "67.0"
  relatedSkills:
    - "platform-metadata-api-context-get"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Salesforce Data + Tooling API Skill

This skill provides field-level reference for **2130 standard Salesforce objects** across two runtime API surfaces: the **Enterprise/Data API** (standard sObjects you query with SOQL and modify with DML) and the **Tooling API** (developer/metadata-adjacent records like `ApexClass`, `ApexCodeCoverage`, `TraceFlag`, and `EntityDefinition`).

Use it to look up authoritative field names, types, and properties **before** writing SOQL/SOSL, building DML, or reading records at runtime — so queries and writes don't fail with `INVALID_FIELD` / "No such column" errors.

> **Standard objects only.** These assets cover standard sObjects and
> Tooling records. Custom `__c` objects, and custom `__c` fields on standard
> objects, are **not** in this corpus — they don't exist as static docs pages.
> For those, describe the live org instead (`sf sobject describe --sobject <Name>`).

## Overview

Each object is documented as a JSON file with:

- Field definitions: name, type, and properties (Createable, Filterable, Groupable, Nillable, Sortable, Updateable)
- Relationship metadata (relationship name, referenced object, relationship type) for enterprise sObjects
- Supported SOAP calls and REST HTTP methods for Tooling records
- WSDL schema segment
- Usage notes and associated objects (enterprise sObjects)

> **This skill is for runtime data, not deployment.** For authoring `*-meta.xml`
> source files (CustomObject, Flow, Profile, ...) use the **Metadata API** skill
> (`platform-metadata-api-context-get`). The two are companions, not substitutes.

## How to Use This Skill

### CRITICAL: Field-Existence Gate (do this BEFORE answering)

**NEVER answer a field question — "does field X exist?", "is X filterable/sortable/groupable?", "what's X's API name/type?" — from memory or training data. This includes obvious system fields like `Id`, `Name`, `CreatedDate`, `LastModifiedDate`, `OwnerId`, `IsDeleted`. ALWAYS run the lookup first.** You know these fields from training, but this skill exists precisely because your recollection of their *properties* (Filter/Sort/Group) and of which catalog documents them is unreliable. Confidence is not verification.

**Run ONE atomic command that checks BOTH catalogs at once** (a field can live in `fields`, in `field_reference`, or neither — see the dual-catalog note below):

```bash
jq '{fields: .fields["<FieldName>"], field_reference: .field_reference["<FieldName>"]}' assets/enterprise_api/<Object>.json
# e.g. checking CreatedDate on Account:
jq '{fields: .fields["CreatedDate"], field_reference: .field_reference["CreatedDate"]}' assets/enterprise_api/Account.json
```

Interpret the result: found in `fields` → use its `properties` for capability answers. Found only in `field_reference` → it exists, but Filter/Sort/Group **cannot** be determined from this skill (that catalog carries no property flags). `null` in both → not in this corpus (may still be a real live-org/custom field — describe the org).

**MANDATORY VERIFICATION GATE.** Before you state any field fact, you MUST first print this line verbatim in your reply to the user (like the metadata skill's status line):

```text
field_lookup: object=<Object> field=<FieldName> checked_fields=<yes|no> checked_field_reference=<yes|no> result=<in_fields|in_field_reference|not_found>
```

If you cannot print this line truthfully with both checks = `yes`, you have not done the lookup — stop and run the jq command. Do not fabricate a citation like "based on the skill's data" without having run it.

This gate line is a self-verification marker for your conversational response **only** — do NOT write it into files you generate for the user (`.soql`, `.md`, `.json`, query comment headers, etc.). Deliverables should contain just the answer/query the user asked for; keep the `field_lookup:` line out of them.

### CRITICAL: Section-Specific Consumption

**ALWAYS consume only the specific sections you need from JSON files, NOT entire files.**

**For `assets/enterprise_api/*.json` and `assets/tooling_api/*.json` files, always use `jq` or programmatic JSON parsing to extract only the sections you need.** Do not load these files whole via `Read`, `cat`, or `read_file` — they contain verbose `wsdl_segment` and `field_reference` sections that waste 60-80% of tokens on large sObjects like Account.

Each JSON file contains multiple sections. Most use cases only need 1-2:

- **For query/DML field lists**: load only the `fields` section
- **For relationship traversal**: load `fields` (the `relationship_name` / `refers_to` columns are inline)
- **For Tooling call support**: load `supported_soap_calls` / `supported_rest_api_http_methods`
- **For "can this user query it?" / permission questions**: load `special_access_rules` (present on both surfaces when the object documents access gates)
- **For query ceilings / unsupported clauses** (record caps, no `ORDER BY`/`queryMore()`/`OFFSET`): load `limitations` — present only on objects that impose them
- **Skip by default**: `wsdl_segment`, `ispersonaccount_fields`

**Dual-catalog rule (imperative — this is the one people get wrong):**

1. A field can be in `fields`, in `field_reference`, in both, or in neither. These are two DIFFERENT catalogs, not a superset relationship.
2. **A miss in `fields` is NOT a "field doesn't exist" answer.** Check `field_reference` too before concluding anything — the atomic jq command above does both in one shot.
3. Filter/Sort/Group/Create/Update/Nillable properties come **only** from `fields`. A field found only in `field_reference` has NO retrievable capability flags here — say so; don't guess.

<details>
<summary><b>Why the two catalogs differ (reference — optional reading)</b></summary>

`fields` comes from Salesforce's SOAP "Fields" table (query/DML properties:
Create/Filter/Sort/Group/Update/Nillable). `field_reference` comes from a
different UI-facing "Field List" table (label/length/precision/scale) that some
objects document separately from the SOAP table — and it can include many fields
`fields` never lists at all (e.g. objects with very large boolean-flag catalogs, or
assorted admin-facing fields the SOAP table omits). Across the corpus, thousands of
fields exist ONLY in `field_reference`, and a smaller number exist only in `fields`.
This is why a field-existence answer requires checking both, and why capability
questions can only be answered from `fields`.
</details>

### Which folder?

- **Standard sObjects** you query and modify at runtime (Account, Contact, Opportunity, Lead, Case, ...) → `assets/enterprise_api/`
- **Developer / diagnostics records** (ApexClass, ApexCodeCoverageAggregate, TraceFlag, EntityDefinition, MetadataComponentDependency, SymbolTable) → `assets/tooling_api/`
- **Custom `__c` objects and custom `__c` fields** → NOT in these assets. Describe the live org: `sf sobject describe --sobject <Name> --target-org <alias>`. (A custom field like `Region__c` on standard Account won't be in `assets/enterprise_api/Account.json` either.)

### Example Queries (Section-Specific)

Do:

- "Show me only the 'fields' section from assets/enterprise_api/Account.json"
- "What are the filterable fields on Opportunity?"
- "Which fields on Contact are relationships, and what do they refer to?"
- "What SOAP calls does ApexClass support in the Tooling API?"
- "Field X isn't in `fields` — check `field_reference` before saying it doesn't exist"

Don't:

- "Load Account.json" (pulls the huge `wsdl_segment`; load `fields` and `field_reference` separately instead of the whole file)

## JSON File Structure

Enterprise (data) sObjects live in `assets/enterprise_api/`; Tooling records live in `assets/tooling_api/`. Both share a common core, with a few surface-specific sections.

```json
{
  "sections": ["title", "description", "fields", "wsdl_segment", ...],
  "title": "Account | Enterprise API",
  "description": "Plain-text description of the object.",
  "fields_columns": ["type", "properties", "description", "relationship_name", "refers_to", "relationship_type"],
  "fields": {
    "fieldName": {
      "type": "string | reference | picklist | ...",
      "properties": "Create, Filter, Group, Nillable, Sort, Update",
      "description": "Field description",
      "relationship_name": "(reference fields only)",
      "refers_to": "(reference fields only) e.g. Account"
    }
  },
  "wsdl_segment": "<xsd:complexType>...</xsd:complexType>"
}
```

`fields` is a **dict keyed by field API name** (e.g. `fields["AnnualRevenue"]`), not a list — iterate with `.items()`/`.keys()`, don't index it positionally.

### How sections are derived (read this before assuming a section list)

Each JSON file is generated from **whatever `## Heading` sections actually appear on
that object's Salesforce docs page** — the JSON schema is not a fixed, uniform
template applied identically to every object. Two consequences follow directly from
that:

1. **No section is guaranteed present on every object, `fields` included.** A section
   exists in a file only if the source docs page had a matching heading. Some Tooling
   docs pages have no fields table at all (thin/beta pages), so `fields` can be
   missing; a small number of SOAP-header-style pages label their field table
   singular (`field`) instead of plural. **Always check the file's own `sections`
   array (or `"fields" in sections`) before assuming a section exists** — don't hard
   code an expectation from having looked at one or two example objects.
2. **A page can carry extra sections beyond the common ones**, one per additional
   `##` heading Salesforce's docs used on that specific page (e.g. a nested complex
   type referenced by a field, like a picklist's value-metadata description, or a
   record-type-info block). These are normalized into `snake_case` keys and stored
   either as their own top-level section, or — when the converter recognizes the
   heading as a *distinct sub-type* rather than a plain content section — nested
   under a `sub_types` dict keyed by the sub-type's name. **Treat the "Available
   Sections" list below as the common/frequent case, not an exhaustive enum** — the
   authoritative list for any one object is that object's own `sections` array.

### Available Sections (common case — not exhaustive; see above)

- `title`, `description`, `fields_columns`: present on essentially all objects
- `fields`: present on the large majority of objects, but see point 1 above — verify
  via `sections` rather than assuming
- **Enterprise-only**: `usage`, `associated_objects`, `ispersonaccount_fields`, `field_reference`, `field_reference_columns`
- **Tooling-only**: `supported_soap_calls`, `supported_rest_api_http_methods`
- `special_access_rules`: **who can query/access the object and any permission or
  license gate** (e.g. "Customer Portal users can't access this object", "requires
  Omnistudio licenses"). Present on both surfaces. Read this before concluding a query
  will run for a given user — it's a query-eligibility fact no field flag captures.
- `limitations`: **query ceilings and unsupported SOQL clauses** the object imposes
  (e.g. MetadataComponentDependency: max 2000 records via Tooling API / 100,000 via
  Bulk API 2.0; `ORDER BY`, `OFFSET`, `queryMore()`, and `*Name`-field filters are not
  supported). Read this before writing a query against an object that has it —
  these constraints are not derivable from the `fields` properties.
- `wsdl_segment`: schema definition (verbose — skip unless you need the raw type)
- `sub_types` and any other `snake_case`-named section not listed above: object-specific
  nested schema description, present only when that object's docs page had a matching
  heading — inspect the file's `sections` array to discover them per-object

The `fields_columns` array tells you which columns each object's `fields` entries
carry — check it per-object rather than assuming a fixed shape. Enterprise sObjects
typically add `relationship_name`, `refers_to`, and `relationship_type`; Tooling
records typically carry only `type`, `properties`, `description` — but a meaningful
minority of Tooling objects also carry `relationship_type`, so don't treat it as
enterprise-exclusive. `relationship_type` values also have spelling variants in the
source data (e.g. `"Lookup"` vs. `"Look up"`) — compare loosely (e.g.
`.replace(" ", "").lower()`) rather than exact string equality.

**Type strings are case-inconsistent across objects — do not assume a single casing.**
The same concept appears under multiple castings depending on the source doc page:
`string`/`String`, `boolean`/`Boolean`, `dateTime`/`DateTime`/`datetime`. Compare
`type` values case-insensitively (e.g. `.lower()`) rather than with `==` against one
casing. Beyond the common `string | reference | picklist` types, real data also
includes `int`, `boolean`, `double`, `currency`, `date`, `dateTime`, `textarea`,
`address`, `url`, `phone`, `email`, `time`, `anyType`, `base64`, and others — treat
the type list as open-ended.

**A field can lack structured `type`/`properties` even when the object otherwise has
them — check `description` as a fallback before concluding the data is missing.**
Because each object's JSON is generated from that object's own docs page, a page that
presents a field's type/properties as prose (`"Type: ... Properties: ...
Description: ..."`) inside a single description paragraph — rather than as separate
table columns — produces a `fields` entry with `type`/`properties` empty and that
prose stuffed into `description`. This shows up for a range of reasons (generic
template pages reused across many standard objects, e.g. history/share/feed-tracking
companion objects) and can affect anywhere from
one field to every field on an object — in the worst case `fields_columns` itself may
say only `["description"]`. **If `type`/`properties` is empty or `fields_columns` looks
suspiciously thin, check whether `description` starts with `"Type: "` and parse it as
a fallback** before concluding the field/object has no type information.

**Picklist allowed values sometimes appear in `description` prose — check before
assuming they're absent.** No `fields` entry has a structured `picklistValues` list.
Whether a picklist's allowed values are enumerated in `description` (as
`"Possible values are: ..."` followed by the values) depends entirely on whether the
source docs page enumerated them for that specific field — many do, many don't (e.g.
org-configurable picklists backed by a separate value-set object typically only give
illustrative examples like "such as New, Closed, or Escalated" instead of a full
list). When present, the format itself is inconsistent — sometimes bare
space/comma-separated tokens, sometimes `Value—explanation` em-dash pairs per line —
so there's no single reliable regex; extract the substring after `"Possible values
are:"` and parse case-by-case, and don't assume every picklist has a discoverable
value set here.

**A field's `description` may reference a relationship (e.g. "this is a dependent
picklist", "this field controls X") without naming or resolving the other side of
that relationship — the enterprise sObject's own `fields` section is not always
where that answer lives.** The Tooling API side of this dataset documents Salesforce's
field-metadata objects (schema-about-schema, e.g. an object exposing per-field
describe-style attributes) which can carry structured attributes — like a controlling
field's identity for a dependent picklist — that the enterprise sObject's docs page
never named explicitly. If an enterprise field's description points at a relationship
it doesn't resolve, check whether a Tooling-side field-metadata object answers it
before concluding the data doesn't exist anywhere in this skill.

**A given object's JSON can carry sections beyond the common list above — inspect that
object's own `sections` array rather than assuming a closed set.** Any additional `##`
heading on the source docs page becomes its own `snake_case`-named section (or, when
the converter recognizes it as a distinct nested type, a `sub_types` entry). These
appear only on the specific objects whose docs happened to include that heading — a
per-object schema-description payload, not junk to ignore. There's no fixed
enumeration of every possible extra section name; discover them per-object via
`sections`.

See the [Index Table](references/data_and_tooling_index_table.md) for the full object listing and per-object extra sections — it's ~125 KB, so `grep -i "<ObjectName>"` it for a single lookup rather than reading the whole file.


> **More detail:** worked query/DML examples, relationship-traversal patterns, and a full section glossary live in [`references/usage_guide.md`](references/usage_guide.md). Load it with the `Read` tool only when needed.

## File Location

Object JSON files are split by API surface:

```text
assets/
├── enterprise_api/      # standard sObjects (SOQL/DML)
│   ├── Account.json
│   ├── Contact.json
│   └── ...
└── tooling_api/         # developer / diagnostics records
    ├── ApexClass.json
    ├── TraceFlag.json
    └── ...
```

Files are referenced relative to the skill root, e.g.
`assets/enterprise_api/Account.json` or `assets/tooling_api/ApexClass.json`.

### Working Examples

Runnable section-loading examples (each demonstrates: fields extraction,
filterable-field lookup via `properties`, relationship traversal, the
`fields` vs `field_reference` dual catalog, and reading Tooling
`supported_rest_api_http_methods`):

- **Python**: [`examples/python_section_loading.py`](examples/python_section_loading.py) — `json.load()` with section extraction
- **JavaScript/Node.js**: [`examples/javascript_section_loading.js`](examples/javascript_section_loading.js) — `JSON.parse()` with section extraction
- **Bash + jq**: [`examples/bash_section_loading.sh`](examples/bash_section_loading.sh) — `jq` command-line JSON processing

See [`examples/README.md`](examples/README.md) for usage and the property→SOQL/DML capability table.

## Query & DML Generation Requirements

When generating SOQL/SOSL or DML against these objects, follow these rules so the
statement actually runs.

### Verify the field exists and its API name

1. **Look up the field first (both catalogs, atomic jq) and print the
   `field_lookup:` gate line — even for system fields you're sure about.** See the
   Field-Existence Gate at the top of "How to Use This Skill". Field API names are
   case-insensitive to Salesforce but must resolve to a real field. Custom fields
   end in `__c`; custom relationships traverse with `__r`.
2. **Do not invent fields.** A guessed column produces
   `INVALID_FIELD: No such column 'X' on entity 'Y'`. If unsure, load the `fields`
   section and confirm.
3. **Don't case-fold `fields` keys when matching.** At least one object
   (`LoginEventLog`) has both `UserName` and `Username` as distinct real fields in
   the same `fields` dict — a lowercase/case-insensitive lookup would silently
   collide them. Match the exact key casing as given. These are **two different
   columns holding potentially different data** — they are NOT the same field that
   "resolves to whichever the platform picks." Select and filter each by its exact
   casing; do not describe them as interchangeable or say a query "resolves
   ambiguously," because the platform treats them as distinct fields.

### Respect field properties

The `properties` string on each field controls what you can do with it:

- **Filter** → usable in a `WHERE` clause. A field without `Filter` cannot be filtered.
- **Sort** → usable in `ORDER BY`.
- **Group** → usable in `GROUP BY`.
- **Createable / Updateable** → settable via `insert` / `update` DML. System and
  formula fields are read-only (no Create/Update) — writing them fails.
- **Nillable** → may be null; a non-nillable field is required on insert.

**This skill's `properties` string has no External ID flag** — `upsert` requires
a field marked External ID in the org, and that flag isn't captured by this data
source (it only appears in Metadata API describe output, not the HTML docs this
skill is built from). To find or set a field's External ID flag, use the
**Metadata API skill** (`platform-metadata-api-context-get`) and check
`CustomField`'s `externalId` attribute — don't guess an upsert field from this
skill's properties alone.

### Relationships (enterprise sObjects)

For `reference`-type fields, the `relationship_name` column gives the parent
relationship for SOQL traversal and `refers_to` names the target object(s):

```sql
-- OwnerId (reference, relationship_name = Owner, refers_to = User)
SELECT Id, Owner.Name FROM Account
-- Custom lookup Foo__c traverses as Foo__r
SELECT Id, Foo__r.Name FROM My_Object__c
```

### Tooling API vs Data API

Tooling records (`assets/tooling_api/`) are queried through the **Tooling API**
endpoint (`/services/data/vXX.0/tooling/query`), not the regular Data API. Check
`supported_soap_calls` / `supported_rest_api_http_methods` for what each record
supports. Many Tooling objects are read-only.

> **Not for deployment.** To author or edit `*-meta.xml` source (CustomObject,
> Flow, Profile, ...) use the Metadata API skill — the objects here are the
> runtime/queryable representation, not the deployable metadata form.
## Duplicate and Ambiguous Object Names

Several names exist in BOTH the Metadata API and here (ApexClass, ApexTrigger,
CustomField, CustomObject, EmailTemplate, Layout, Profile, PermissionSet,
RecordType, ValidationRule, Flow, ...). They mean different things:

- **This skill** = the runtime/queryable record: fields you `SELECT`, filter, and
  (sometimes) write via the Data or Tooling API.
- **Metadata API skill** = the `*-meta.xml` source form you author and deploy.

Resolve ambiguity with these signals:

- "query", "SOQL", "SOSL", "DML", "insert/update/upsert", "what fields/columns",
  "filterable", "record", "runtime", "REST/SOAP" → **this skill**.
- "authoring", "deploy", "retrieve", `package.xml`, `force-app/`, `sfdx`,
  `.meta.xml`, "blueprint/template" → **Metadata API skill**.
- Tooling-specific: "Tooling API", `ApexCodeCoverage`, `EntityDefinition`,
  `TraceFlag`, `SymbolTable`, "code coverage", "compile errors", "debug log" →
  Tooling half of **this skill** (`assets/tooling_api/`).

If invoked directly by name with no other signal, default to the runtime data
interpretation and disclose the assumption.

## Troubleshooting

### File Not Found

- File names are **case-sensitive PascalCase** matching the object API name
  (`Account.json`, `ApexClass.json`), no separators.
- Check the correct folder: enterprise sObjects in `assets/enterprise_api/`,
  Tooling records in `assets/tooling_api/`. A name can exist in only one, or in
  both with different fields.
- Before declaring "not found", search the index table (it lists every object name
  in the corpus) with a targeted grep rather than reading the whole ~125 KB file:
  `grep -i "<ObjectName>" references/data_and_tooling_index_table.md`. Match
  case-insensitively and allow for near-misses (spacing, plural, minor spelling)
  before concluding the object is absent. Read the full file only for a broad survey.

### INVALID_FIELD / No such column

- The field is not on that object, or you used the wrong API name. Load the
  `fields` section and confirm the exact name (custom fields end in `__c`).
- The field exists but lacks the needed property: filtering a non-`Filter`
  field, sorting a non-`Sort` field, or writing a read-only (no `Create`/`Update`)
  field all fail. Check the `properties` string.

### Relationship query fails

- Use `relationship_name` (not the id field) to traverse: `Owner.Name`, not
  `OwnerId.Name`. Custom lookups traverse with `__r`.
- Confirm `refers_to` — polymorphic fields (e.g. `WhoId`, `WhatId`) refer to
  multiple objects and need `TYPEOF` or the correct relationship.

### Tooling query returns nothing / errors

- Tooling objects must be queried against the Tooling API endpoint
  (`/tooling/query`), not the standard Data API. Verify with
  `supported_rest_api_http_methods` / `supported_soap_calls`.

### Field is in wsdl_segment but not fields

- Complex nested types have their sub-fields in `wsdl_segment`. Pull just the
  matching `complexType` with `jq -r '.wsdl_segment' file.json | grep -A 30
  'complexType name="Foo"'` instead of loading the whole segment.

## Common Objects

### Enterprise / Data API (SOQL + DML)

- **Account**: Represents an individual account, which is an organization or person involved with your business (such as customers, competitors, and partners).
- **Contact**: Represents a contact, which is a person associated with an account.
- **Opportunity**: Represents an opportunity, which is a sale or pending deal.
- **Lead**: Represents a prospect or lead.
- **Case**: Represents a case, which is a customer issue or problem.
- **User**: Represents a user in your organization.
- **Task**: Represents a business activity such as making a phone call or other to-do items.
- **Event**: Represents an event in the calendar.

### Tooling API (developer records)

- **ApexClass**: Represents the saved copy of an Apex class.
- **ApexTrigger**: Represents the saved copy of an Apex trigger.
- **ApexCodeCoverageAggregate**: Represents aggregate code coverage test results for an Apex class or trigger.
- **TraceFlag**: Represents a trace flag that triggers an Apex debug log at the specified logging level.
- **EntityDefinition**: Provides row-based access to metadata about standard and custom objects.

