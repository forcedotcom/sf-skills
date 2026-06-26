---
name: platform-metadata-api-context-get
description: "Salesforce Metadata API reference for creating, understanding, or modifying metadata XML files (.object-meta.xml, .flow-meta.xml, etc.) and any of 604 metadata types (CustomObject, Flow, ApexClass, ApexTrigger, Profile, PermissionSet, Layout, ValidationRule, RecordType, EmailTemplate, ...). Use for questions about a type's fields or XML format, or Salesforce DX project structure (force-app/main/default). TRIGGER when: authoring or editing any *-meta.xml file, asking what fields/format a metadata type has, or whenever 'Salesforce metadata' or 'sfdx project' is mentioned. DO NOT TRIGGER when: SOQL/DML/runtime sObject access (use the Enterprise API skill), Tooling API developer records (ApexExecutionOverlayAction, TraceFlag), or non-XML logic (Apex code, LWC JS, Visualforce controllers)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
---

# Salesforce Metadata API Skill

This skill provides comprehensive documentation for all **604 Salesforce Metadata API types**. Use this skill to create, understand, and modify Salesforce metadata XML files in your Salesforce DX projects.

## Overview

The Salesforce Metadata API allows you to retrieve, deploy, create, update, or delete customizations for your org. This skill gives you access to detailed documentation for each metadata type, including:

- Field definitions and data types
- Required vs. optional fields
- WSDL schema definitions
- Sample XML structures
- File naming conventions
- Directory locations in Salesforce DX projects

## How to Use This Skill

### ⚡ CRITICAL: Section-Specific Consumption

**ALWAYS consume only the specific sections you need from JSON files, NOT entire files.**

**CRITICAL: For `data/metadata_api/*.json` files, always use `jq` or programmatic JSON parsing to extract only the specific sections you need.** Do not load these files whole via `Read`, `cat`, `read_file`, or any other tool that injects the complete file — they contain verbose WSDL segments and other sections that waste 60-80% of tokens. (Loading small files like this SKILL.md or the index table with `Read` is fine; the rule applies specifically to the large metadata-type JSON files.)

Each JSON file contains multiple sections (fields, description, wsdl_segment, etc.). Most use cases only require 1-2 sections:

- **For field definitions**: Load only the `fields` section
- **For understanding purpose**: Load only the `description` section
- **For XML examples**: Load only the `declarative_metadata_sample_definition` section
- **Skip by default**: `wsdl_segment` (verbose schema), `file_information`, `directory_location`

This reduces token consumption by **60-80% per file**.

### Quick Start

To get information about a specific metadata type:

1. **Section-specific** (BEST): "Show me only the 'fields' section from CustomObject.json"
2. **Multiple sections**: "Show me 'fields' and 'description' from Flow.json"
3. **Avoid loading entire files**: Don't ask for "the CustomObject metadata type" - specify sections

### Example Queries (Section-Specific)

- ✅ "Show me only the 'fields' section from CustomObject.json"
- ✅ "What fields are in the 'fields' section of Profile.json?"
- ✅ "Load the 'description' and 'fields' sections from Flow.json"
- ✅ "Give me just the 'declarative_metadata_sample_definition' from ApexClass.json"
- ❌ "Show me the CustomObject metadata type" (too broad - entire file)
- ❌ "Load CustomObject.json" (includes unnecessary WSDL and other sections)

## JSON File Structure

Each metadata type is stored as a JSON file in `data/metadata_api/` with the following structure:

```json
{
  "sections": ["title", "description", "fields", "wsdl_segment", ...],
  "title": "MetadataTypeName - Metadata API",
  "description": "Plain-text description of the metadata type.",
  "fields": {
    "fieldName": {
      "type": "string",
      "description": "Field description",
      "required": true
    }
  },
  "file_information": ".object",
  "directory_location": "objects",
  "wsdl_segment": "<xsd:complexType>...</xsd:complexType>",
  "declarative_metadata_sample_definition": [
    {
      "description": "Example description",
      "code": "<?xml version=\"1.0\"?>\n<MetadataType>...\n</MetadataType>"
    }
  ]
}
```

> **Note:** string values (`title`, `description`, `file_information`, `directory_location`, `wsdl_segment`) are stored as **plain text** — no markdown headers (`#`/`##`) or code fences. `file_information` holds just the file suffix (e.g. `.object`, `.ai`) and `directory_location` just the SFDX folder name (e.g. `objects`, `aiApplications`).

### Available Sections

The `sections` array indicates which top-level keys are present in each file. Common sections include:

- `title`: The metadata type name and header
- `description`: What the metadata type represents
- `fields`: The type's own fields, with types and descriptions
- `sub_types`: (composite types only) a map of referenced sub-type name → that sub-type's fields, e.g. `Flow` → `sub_types.FlowActionCall`
- `file_information`: File naming conventions and extensions
- `directory_location`: Where files are stored in SFDX projects
- `wsdl_segment`: XML schema definition from the WSDL
- `declarative_metadata_sample_definition`: Example XML code

Some metadata types have additional sections specific to their functionality. See the [Index Table](references/metadata_index_table.md) for a complete breakdown.


> **More detail:** background on *why* token optimization matters, worked usage examples, common workflows, a full section glossary, and versioning/support notes live in [`references/usage_guide.md`](references/usage_guide.md). Load it with the `Read` tool only when needed.

## Token Optimization Strategies

**CRITICAL**: To minimize token usage and costs:
1. Load only the specific metadata type(s) you need, not the full corpus
2. **Load only specific sections from each file, not entire files**

### Section-Specific Loading (BEST PRACTICE)

**⚠️ CRITICAL WARNING: DO NOT use the `read_file` tool (or any whole-file reading tool) on these JSON files!**

`read_file` loads the entire file content into your context, defeating the purpose of section-specific consumption. You will waste 60-80% of your token budget loading unnecessary WSDL segments and verbose sections. (Using `Read` on small files such as this SKILL.md or the index table is fine — this rule is only about the large metadata-type JSON files.)

**Approach**: Programmatically parse the JSON file and extract ONLY the sections you need using code, not whole-file reading tools.

**Working Examples Available**:

We provide complete, working code examples in multiple languages:

- **Python**: [`examples/python_section_loading.py`](examples/python_section_loading.py) - Shows `json.load()` with section extraction
- **JavaScript/Node.js**: [`examples/javascript_section_loading.js`](examples/javascript_section_loading.js) - Shows `JSON.parse()` with section extraction
- **Bash + jq**: [`examples/bash_section_loading.sh`](examples/bash_section_loading.sh) - Shows `jq` command-line JSON processing

See [`examples/README.md`](examples/README.md) for complete documentation and usage instructions.

**Quick Pattern** (adapt to your language):
1. Read the JSON file
2. Parse it into a data structure
3. Extract ONLY the sections you need (e.g., `fields`, `description`)
4. Ignore verbose sections (`wsdl_segment`, `declarative_metadata_sample_definition`)

### What NOT to Do

**❌ NEVER use the `read_file` tool on these JSON files**:
```text
read_file data/metadata_api/CustomObject.json  # Loads entire file into context!
read_file data/metadata_api/Flow.json          # Wastes 60-80% tokens!
```

**❌ NEVER load all files**:
```text
read_file data/metadata_api/*.json  # This loads ~15MB of data!
```

**Token Impact**:
- Section-specific: **50-200 tokens** per metadata type
- Entire file: **500-2000 tokens** per metadata type
- **Savings: 60-80% per file**

### When to Load Multiple Types

- **Related types**: CustomObject + CustomField + ValidationRule
- **Permission sets**: Profile + PermissionSet + PermissionSetGroup
- **UI components**: Layout + CompactLayout + QuickAction
- **Automation**: Flow + WorkflowRule + ApexTrigger

### When to Load Specific Sections (STRONGLY RECOMMENDED)

Many metadata types have large WSDL segments or extensive field lists. **Always load only the specific sections you need from each JSON file** rather than consuming the entire file:

1. **First, check available sections** by reading just the `sections` array from the JSON
2. **Extract only the sections you need** (e.g., `fields` for field definitions, `description` for overview)
3. **Skip WSDL segments** unless you specifically need schema validation
4. **Skip declarative_metadata_sample_definition** unless you need complete XML examples

This approach can reduce token consumption by **60-80%** per file by excluding verbose WSDL definitions and lengthy examples.

## Conceptual Approach to Using This Skill

### Step 1: Identify Your Need

Ask yourself:
- What am I trying to build or modify?
- Which Salesforce metadata type(s) am I working with?
- **Which specific information do I need?**
  - Field definitions only? → Load `fields` section
  - Understanding what it does? → Load `description` section
  - XML example? → Load `declarative_metadata_sample_definition` section
  - Schema validation? → Load `wsdl_segment` section (rarely needed)

### Step 2: Find the Right Type

Use one of these methods:
- **Direct reference**: If you know the type name (e.g., "CustomObject")
- **Index search**: Check `references/metadata_index_table.md` for related types
- **Common types**: See the "Quick Reference: Common Metadata Types" section below

### Step 3: Load Selectively (Section-Specific) ⚡

**Decision Tree for Section Loading**:

```text
Need field definitions?
  → Load ONLY 'fields' section (~50-200 tokens)

Need to understand what the type does?
  → Load ONLY 'description' section (~20-100 tokens)

Need XML structure example?
  → Load ONLY 'declarative_metadata_sample_definition' (~100-300 tokens)

Need all three?
  → Load 'fields' + 'description' + 'declarative_metadata_sample_definition'
  → Still skip 'wsdl_segment', 'file_information', 'directory_location'
  → Savings: ~60-70% vs loading entire file

Need schema validation?
  → Only then load 'wsdl_segment' (this is verbose)
```

**Request format**:
- **Single section** (BEST): "Show me only the 'fields' section from ApexClass.json"
- **Multiple sections**: "Load 'fields' and 'description' from CustomObject.json"
- **Skip verbose sections**: Never load `wsdl_segment` unless explicitly needed

### Step 4: Apply to Your Code

Use the loaded information to:
- Create new metadata XML files
- Understand existing files in your project
- Validate field names and types
- Generate correct XML structure with proper namespaces

## File Location

All metadata type JSON files are located in:

```text
data/metadata_api/
├── CustomObject.json
├── Flow.json
├── ApexClass.json
├── Profile.json
└── ... (600 more files)
```


### Path Resolution

When using this skill, files are referenced as:
- Absolute: `data/metadata_api/CustomObject.json`
- Relative to skill root: `./data/metadata_api/CustomObject.json`

The skill will automatically resolve paths based on the working directory.

## Metadata File Generation Requirements

When generating Salesforce metadata XML files, follow these requirements to ensure valid, deployable files.

### XML Structure Requirements

All metadata files must:

1. **Include XML declaration**:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   ```

2. **Use correct namespace**:
   ```xml
   <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
   ```

3. **Match root element to metadata type**:
   - CustomObject → `<CustomObject>`
   - Flow → `<Flow>`
   - Profile → `<Profile>`
   - etc.

### Namespace Declaration

The namespace is **required** and must be exactly:
```text
http://soap.sforce.com/2006/04/metadata
```

**Correct**:
```xml
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
```

**Incorrect**:
```xml
<CustomObject>  <!-- Missing namespace -->
<CustomObject xmlns="http://salesforce.com/metadata">  <!-- Wrong namespace -->
```

### Required vs. Optional Fields

Each metadata type has different field requirements:

- **Schema-required** (`required: true` in the JSON): the WSDL marks the field as required.
- **Effectively required** (not flagged but practically needed): in many cases the WSDL marks fewer fields as required than the authoring contract actually demands. CustomObject is the canonical example — the JSON marks only `externalDataSource`, `externalName`, `nameField` as `required: true` (the first two are external-object-only quirks), but a normal `__c` CustomObject also needs `label`, `pluralLabel`, `deploymentStatus`, and `sharingModel` to deploy. Always cross-check with the `declarative_metadata_sample_definition` examples.
- **Conditionally required**: some fields are required only when certain features are enabled.
- **Optional**: most fields can be omitted if not needed.

**Example from CustomObject** (note: practical authoring needs more than what `required: true` marks):
```json
{
  "fields": {
    "nameField": {
      "type": "CustomField",
      "description": "The name field for the custom object",
      "required": true
    },
    "label": {
      "type": "string",
      "description": "The label for the custom object (effectively required for normal __c objects)",
      "required": false
    },
    "sharingModel": {
      "type": "SharingModel (enumeration)",
      "description": "The sharing model for the object (effectively required for normal __c objects)",
      "required": false
    },
    "enableHistory": {
      "type": "boolean",
      "description": "Enable field history tracking",
      "required": false
    }
  }
}
```

### Validation Tips

Before deploying:

1. **Validate XML syntax**: Ensure well-formed XML (matching tags, proper nesting)
2. **Check required fields**: Verify all required fields are present
3. **Verify namespaces**: Namespace must be exact
4. **Test field types**: Ensure field values match expected types
5. **Use Salesforce CLI**: Run `sf project deploy validate` to catch errors

> **More detail:** field-type→XML mapping tables, file-naming/two-file/child-type conventions, and full well-formed-file examples are in [`references/usage_guide.md`](references/usage_guide.md).
## Duplicate and Ambiguous Type Names

Some Metadata API type names also exist as Enterprise/Data API or Tooling API object names. Examples include ApexClass, ApexTrigger, CustomField, CustomObject, EmailTemplate, Layout, Profile, PermissionSet, RecordType, StaticResource, WebLink, ValidationRule, and Flow.

When the prompt is ambiguous (e.g., "tell me about Profile" or "what fields are on ApexClass"), ask whether the user wants:

1. **Metadata API** XML structure for source/deployment authoring (this skill, e.g. `.profile-meta.xml`, `.cls-meta.xml`).
2. **Enterprise/Data API** runtime sObject/record reference (no dedicated skill currently — fall back to the Salesforce API family router).
3. **Tooling API** developer tooling record reference (no dedicated skill currently — fall back to the Salesforce API family router).

Heuristics that resolve most ambiguity without asking:

- Mentions of `package.xml`, `force-app/`, `sfdx`, `.meta.xml`, "deploy", "retrieve", "authoring", "blueprint", "template", "class definition", or "permissions" in a deployment sense → Metadata API (this skill).
- "What fields are on X" / "what columns" / "DML" / "SOQL" / "query" / "REST" / "sObject" / "record" / "runtime" → Enterprise/Data or Tooling API (other skill).
- Tooling-specific signals: "Tooling API", `ApexCodeCoverage`, `EntityDefinition`, `TraceFlag`, "code coverage", "compile errors", `SymbolTable`, debug logging → Tooling API.

**Default-when-no-signals rule**: if the prompt has none of the signals above AND this skill (`platform-metadata-api-context-get`) was invoked directly by name, default to the Metadata API interpretation and explicitly disclose the assumption to the user (e.g., "Interpreting this as the Metadata API type for `.cls-meta.xml` authoring; let me know if you meant the Tooling API record or Enterprise/Data sObject"). The skill-invocation context itself is a signal of authoring/deployment intent.

## Troubleshooting

### File Not Found

**Problem**: Cannot find metadata type file

**Solutions**:
- File names are **case-sensitive PascalCase** with no separators (e.g., `CustomObject.json`, NOT `customobject.json`, `Custom_Object.json`, or `Custom-Object.json`).
- Before declaring "not found", consult `references/metadata_index_table.md`. Use this two-pass recovery algorithm against the index:
  1. **Normalize-and-substring** (handles case + separator variants): strip non-alphanumeric characters and lowercase both the query and each index entry, then look for substring matches. Resolves: `customobject`, `Custom_Object`, `Custom-Object` → `CustomObject`.
  2. **On miss, fuzzy-match** (handles missing-letter typos): use `difflib.get_close_matches(query_normalized, index_normalized, n=3, cutoff=0.7)` or Levenshtein distance ≤ 2. Resolves: `customfeld` → `CustomField`, `apxclass` → `ApexClass`. Pure substring matching cannot recover character deletions.
- **Multi-hit tiebreaker**: when normalize-and-substring returns multiple matches (e.g., `customobject` matches both `CustomObject` and `CustomObjectTranslation`), prefer the entry whose normalized length **equals** the normalized query length; otherwise prefer the shortest match.
- Some types have unexpected naming conventions (no underscores, no spaces, no abbreviations like "OAuth"); the index is the source of truth.

### SOAP Envelope / Header Types (thin by design)

Two related patterns to recognize:

1. **Result types** (`AsyncResult`, `SaveResult`, `DeleteResult`, `UpsertResult`, `Error`, `DescribeMetadataResult`, etc.) — `fields` is empty AND `wsdl_segment` is populated. These are SOAP response wrappers; their schema lives entirely in `wsdl_segment`. Consume that section if you need their structure. They are not deployable source files.
2. **SOAP request headers** (`AllOrNoneHeader`, `SessionHeader`, `CallOptions`, `DebuggingHeader`, `OwnerChangeOptions`, etc.) — `fields` has 1–2 minimal entries, no `wsdl_segment`. These configure SOAP request behavior; they are call-time options, not metadata you author or deploy.

In both cases, the thin JSON output is correct. Don't try to author a `.AsyncResult-meta.xml` — these types have no source-file form.

### Missing Section

**Problem**: Expected section not in JSON file

**Solutions**:
- Check the `sections` array to see what's available
- Not all metadata types have all sections
- Some sections are type-specific (noted in index table)

### Incomplete Field Information

**Problem**: Field definition lacks details

**Solutions**:
- Check `wsdl_segment` for complete schema definition
- Some fields have complex types defined in WSDL
- Cross-reference with Salesforce documentation for enumerations

### Following Sub-Type Pointers (e.g., `ProfileObjectPermissions[]`)

When the `fields` section gives a complex type name like `ProfileObjectPermissions[]` or `LayoutItem[]` or `ApprovalStep[]`, the sub-fields of that nested type are NOT in the `fields` section — they live in `wsdl_segment` for that complex type. The skill's "skip wsdl_segment by default" rule is for token economy on the simple-field path; for nested types you need to drill in.

**Worked example** — find the sub-fields of `objectPermissions` on Profile:

```bash
# 1. Get the field type name from the fields section
jq '.fields.objectPermissions' data/metadata_api/Profile.json
# → {"type": "ProfileObjectPermissions[]", ...}

# 2. Pull just the matching complexType from wsdl_segment using grep -A
jq -r '.wsdl_segment' data/metadata_api/Profile.json   | grep -A 30 'complexType name="ProfileObjectPermissions"'
```

The `grep -A N` window keeps token cost ~150 tokens instead of loading the whole `wsdl_segment` (which can be 5K+ tokens on large types). Use this pattern any time `fields` returns a `Foo[]` type and you need Foo's sub-fields.

### XML Generation Errors

**Problem**: Generated XML fails validation

**Solutions**:
- Verify namespace is exactly: `http://soap.sforce.com/2006/04/metadata`
- Check all required fields are present
- Ensure field values match expected types
- Validate XML syntax (closing tags, proper nesting)

### Deployment Failures

**Problem**: Metadata file won't deploy

**Solutions**:
- Run `sf project deploy validate` first
- Check Salesforce API version compatibility
- Verify file naming matches conventions
- Ensure directory structure matches SFDX format

## Quick Reference: Common Metadata Types

Here are the most frequently used metadata types:

- **CustomObject**: defines the schema for a custom sObject, including fields, relationships, and settings
- **Flow**: automates business processes using a visual canvas of elements and connectors
- **ApexClass**: compiled Apex server-side class; includes body, API version, and status
- **ApexTrigger**: Apex code that executes before/after DML events on a specific sObject
- **Profile**: controls object/field permissions, app visibility, and login settings for a user profile
- **PermissionSet**: additive set of permissions granted to users independently of their profile
- **CustomField**: defines a field on a standard or custom object, including type, picklist values, and formula
- **Layout**: controls the arrangement of fields and related lists on a record detail/edit page
- **ValidationRule**: enforces data quality by preventing saves when a formula condition is true
- **ApexPage**: Visualforce page definition, including controller reference and markup
- **ApexComponent**: reusable Visualforce component that can be embedded in pages
- **CustomTab**: defines a tab pointing to a custom object, Visualforce page, or web URL
- **CustomApplication**: defines an app's tab bar, nav items, and branding
- **LightningComponentBundle**: LWC bundle including JS, HTML, and metadata descriptor
- **AuraDefinitionBundle**: Aura (Lightning) component bundle with component, controller, helper files
- **StaticResource**: uploaded file (JS, CSS, image, ZIP) accessible from Visualforce and LWC
- **EmailTemplate**: email template for use in workflow rules, Process Builder, or Apex
- **Report**: saved report definition including filters, groupings, and columns
- **Dashboard**: collection of dashboard components backed by reports

For a complete list of all metadata types, see [Index Table](references/metadata_index_table.md).

