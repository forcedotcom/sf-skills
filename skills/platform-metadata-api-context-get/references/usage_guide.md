# Metadata API Skill — Usage Guide

Supplementary reference material for the `platform-metadata-api-context-get` skill. Load this file only when you need the deeper background below; the core decision tree, section-loading rules, generation requirements, and troubleshooting live in `SKILL.md`.
## Why Token Optimization Matters

### Context Window Constraints

Claude has a finite context window (200K tokens). Loading the full metadata-type corpus would consume:

- **~15MB of JSON data**
- **~75,000 tokens** (approximately 40% of available context)
- **Reduced space** for your actual code and conversation

This leaves less room for:
- Your project's code files
- Conversation history
- Generated responses
- Multi-turn problem solving

### Cost Implications

Token usage directly impacts costs:

- **Input tokens**: Every loaded file counts toward input cost
- **Repeated requests**: Loading files multiple times multiplies costs
- **Cache misses**: Large contexts may not fit in prompt cache

### Performance Trade-offs

Loading all files affects performance:

- **Slower response times**: More tokens to process
- **Reduced relevance**: LLM must search through more irrelevant data
- **Context dilution**: Important information gets buried in noise

### Best Practices

✅ **DO**:
- **Use programmatic JSON parsing** to extract only needed sections (Python json.load(), Node.js JSON.parse(), etc.)
- **Load only specific sections** from each JSON file (fields, description) not the entire file
- Load 1-5 specific metadata types relevant to your task
- Check the `sections` array first to see what's available
- Use the index table to find related types
- Skip WSDL segments and sample definitions unless explicitly needed
- Cache frequently used sections (fields for CustomObject, Flow, Profile)

❌ **DON'T**:
- **NEVER use the `read_file` tool or other whole-file readers on the metadata-type JSON files** (loads entire file into context)
- Load entire JSON files when you only need 1-2 sections
- Load every metadata type at once
- Load files "just in case" you might need them
- Repeatedly load the same files in a conversation
- Include WSDL segments unless you need schema validation
- Load declarative_metadata_sample_definition unless examples are required

### Example: Good vs. Bad

**Bad** (wastes ~75,000 tokens):
```text
"Load all metadata types so I can reference them"
```

**Better** (uses ~500 tokens):
```text
"Show me the CustomObject and CustomField metadata types"
```

**Best** (uses ~150 tokens):
```text
"Show me only the 'fields' section from CustomObject.json"
```

The section-specific approach uses **500x fewer tokens** while providing exactly what you need.
## Token Size Reference

Approximate token counts for different loading strategies:

| What You Load | Approx. Tokens | Use Case |
|---------------|----------------|----------|
| Single section (fields only) | 50-200 | ✅ **BEST** - Quick field reference |
| Single section (description) | 20-100 | ✅ Overview/understanding |
| 2-3 sections from one type | 150-500 | Most common use case |
| Entire single type (small) | 100-500 | Small types without WSDL |
| Entire single type (large) | 500-2,000 | ❌ **Wasteful** - includes unused WSDL |
| 5 related types (entire files) | 2,000-5,000 | ❌ Use section-specific loading instead |
| 20 types (entire files) | 10,000-15,000 | ❌ Avoid - major waste |
| 50 types (entire files) | 25,000-35,000 | ❌ Never do this |
| The full metadata-type corpus | ~75,000 | ❌ Catastrophic waste |

**Note**: Loading only specific sections (fields, description) typically reduces token usage by **60-80%** per file compared to loading entire files with WSDL segments and examples.
## Usage Examples

### Example 1: Creating a CustomObject (Section-Specific)

**User**: "I need to create a custom object metadata file for a Student object"

**Response approach** (Token-efficient):
1. Load ONLY the `fields` section from `data/metadata_api/CustomObject.json`
2. Review required fields: `label`, `nameField`, `deploymentStatus`, `sharingModel`
3. If needed, also load the `declarative_metadata_sample_definition` section for XML structure example
4. Generate XML with correct namespace
5. Include file naming convention: `Student__c.object-meta.xml`

**Token savings**: ~70% (loading only 'fields' + 'declarative_metadata_sample_definition' instead of entire file with WSDL)

### Example 2: Understanding Flow Metadata (Section-Specific)

**User**: "What fields are available in a Flow metadata type?"

**Response approach** (Token-efficient):
1. Load ONLY the `fields` section from `data/metadata_api/Flow.json`
2. List field names, types, and descriptions
3. Highlight required fields and common patterns
4. Skip `wsdl_segment`, `description`, and other sections

**Token savings**: ~80% (fields section is ~200 tokens vs ~1000 for entire file)

### Example 3: Modifying a Profile (Section-Specific)

**User**: "How do I add object permissions to a Profile?"

**Response approach** (Token-efficient):
1. Load ONLY the `fields` section from `data/metadata_api/Profile.json`
2. Find `objectPermissions` field definition within that section
3. Show structure and required sub-fields
4. If XML example needed, separately load `declarative_metadata_sample_definition`

**Token savings**: ~75% (avoiding massive WSDL segment in Profile.json)

### Example 4: Working with ApexClass Metadata (Section-Specific)

**User**: "What's the metadata file structure for an Apex class?"

**Response approach** (Token-efficient):
1. Load the `fields` and `description` sections from `data/metadata_api/ApexClass.json`
2. Show the simple structure (apiVersion, status)
3. Explain the relationship between `.cls` and `.cls-meta.xml` files
4. Load `file_information` section only if directory structure details needed

**Token savings**: ~60% (ApexClass is simpler but still benefits from section filtering)
## Common Workflows

### Workflow 1: Creating New Metadata

1. Identify the metadata type you need
2. Load the corresponding JSON file
3. Review required fields and their types
4. Check sample XML in `declarative_metadata_sample_definition`
5. Generate XML with correct namespace and structure
6. Save to appropriate directory in SFDX project
7. Validate with Salesforce CLI

### Workflow 2: Understanding Existing Metadata

1. Identify the metadata type from file extension
2. Load the JSON documentation
3. Review field descriptions to understand purpose
4. Check WSDL segment for complex type definitions
5. Cross-reference with your XML file

### Workflow 3: Modifying Metadata

1. Load JSON for the metadata type
2. Identify the field you want to modify
3. Verify it's not a required field or understand implications
4. Check field type and valid values
5. Update XML maintaining proper structure
6. Validate before deploying

### Workflow 4: Planning a Migration

1. List all metadata types involved
2. Load JSON for each type (5-10 at a time to optimize tokens)
3. Identify dependencies between types
4. Plan deployment order based on dependencies
5. Validate required fields for each type
## Understanding Sections

Different metadata types have different available sections. Here's what each section typically contains:

### Core Sections (Most Types)

- **title**: The metadata type name and page header
- **description**: Overview of what the metadata type represents and its purpose
- **fields**: Detailed field definitions with types, descriptions, and requirements
- **file_information**: File naming conventions and extensions
- **directory_location**: Where files are stored in Salesforce DX projects

### Schema Sections

- **wsdl_segment**: XML schema definition from the Metadata API WSDL
  - Contains complexType and simpleType definitions
  - Shows complete structure and type relationships
  - Useful for validation and understanding complex nested structures

### Example Sections

- **declarative_metadata_sample_definition**: Sample XML code
  - Usually includes 1-3 complete examples
  - Shows real-world usage patterns
  - Demonstrates proper XML structure

### Type-Specific Sections

Some metadata types have additional sections:

- **child_metadata_types**: Nested or related types (e.g., CustomObject has CustomField)
- **fields_for_customfield**: Special field definitions for CustomField type
- **countriesandstates**: Country and state data (AddressSettings)
- **action_override_types**: Available override types (ActionOverride)

#### `fields` vs `sub_types` — composite types

Every authored metadata type exposes its OWN fields under a **`fields`** key.
Composite types (Flow, Workflow, Layout, …) also reference distinct sub-types
(their own complexTypes); those are grouped under a **`sub_types`** object keyed
by the sub-type's CamelCase name — they are NOT mixed into the parent's `fields`.

| Pattern | Where the fields live | Examples |
|---|---|---|
| Simple type | `fields` | ApexTrigger, ApexPage, StaticResource, RemoteSiteSetting |
| Composite type | `fields` (the type's own fields) + `sub_types: { <CamelCaseName>: {…fields…} }` | `Flow` → `fields` + `sub_types.FlowActionCall`, `sub_types.FlowAssignment`, …; `Workflow` → `fields` + `sub_types.WorkflowAlert`, … |
| SOAP result / response wrapper | `properties` (no `fields`) | SaveResult, UpsertResult, DeleteResult, Error |

So for `Flow.json`: load **`fields`** for Flow's own fields (e.g. `actionCalls`,
which is typed `FlowActionCall[]`), and load **`sub_types.FlowActionCall`** for
that referenced type's fields (e.g. `actionName`). A sub-type's fields are NOT in
the parent's `fields`. Feature-gated settings (e.g. IndustriesSettings'
"Fields for Health Cloud" groups) are merged into the single `fields` section.

See the [Index Table](metadata_index_table.md) for a complete breakdown of which types have which sections.

## Metadata File Generation — Detailed Reference

### Field Type Validation

Match field types exactly:

| Field Type | XML Format | Example |
|------------|------------|---------|
| `string` | `<fieldName>value</fieldName>` | `<label>My Object</label>` |
| `boolean` | `<fieldName>true or false</fieldName>` | `<deploymentStatus>Deployed</deploymentStatus>` |
| `int` | `<fieldName>123</fieldName>` | `<externalSharingModel>Private</externalSharingModel>` |
| `CustomField[]` | Multiple `<fields>` tags | `<fields>...</fields><fields>...</fields>` |
| `enumeration` | Use exact enum value | `<sharingModel>ReadWrite</sharingModel>` |

### Common Patterns and Conventions

#### File Naming

- Custom objects: `MyObject__c.object-meta.xml`
- Custom fields: `MyObject__c.MyField__c.field-meta.xml`
- Flows: `My_Flow.flow-meta.xml`
- Apex classes: `MyClass.cls-meta.xml`
- Profiles: `Admin.profile-meta.xml`

#### Two-File ("source + meta") Types

Several metadata types are authored as **a pair** of files in SFDX source format: a source file with the actual content, and a sibling `<base>.<ext>-meta.xml` carrying deployment metadata. The JSON's `content` field (when present, base64-encoded) corresponds to the source file on disk:

| Type | Source file | Meta sidecar |
|---|---|---|
| ApexClass | `MyClass.cls` (Apex code) | `MyClass.cls-meta.xml` |
| ApexTrigger | `MyTrigger.trigger` (Apex code) | `MyTrigger.trigger-meta.xml` |
| ApexComponent | `MyComp.component` (markup) | `MyComp.component-meta.xml` |
| ApexPage | `MyPage.page` (Visualforce markup) | `MyPage.page-meta.xml` |
| StaticResource | `MyResource.<ext>` (any payload) | `MyResource.resource-meta.xml` |
| AuraDefinitionBundle | bundle dir with `.cmp`/`.app`/`.evt` + `.js` + `.css` etc. | `bundle-meta.xml` inside the dir |
| LightningComponentBundle | bundle dir with `.html`/`.js`/`.css` | `bundle.js-meta.xml` inside the dir |

When a JSON file contains a `content` field of type `base64`, that's the SOAP-API artifact equivalent of the disk source file. Authors write the source file directly; the `-meta.xml` sidecar carries fields like `apiVersion` and `status`.

#### Child Metadata Types (legacy MDAPI vs SFDX source format)

Some metadata types appear in the index but are **child elements** of a parent type, not standalone files. Examples: `ValidationRule`, `WebLink`, `RecordType`, `CompactLayout`, `ListView`, `BusinessProcess`, `FieldSet`, `SharingReason`, `Index` — all nested under `CustomObject`. Their JSON files lack `file_information` and `directory_location` because the legacy MDAPI form serializes them inline inside the parent `.object` file.

In modern **SFDX source format**, these child types are decomposed into their own files under the parent object directory:

```text
force-app/main/default/objects/MyObject__c/
├── MyObject__c.object-meta.xml
├── fields/
│   └── MyField__c.field-meta.xml
├── validationRules/
│   └── My_Rule.validationRule-meta.xml
├── recordTypes/
│   └── My_RT.recordType-meta.xml
├── webLinks/
│   └── My_Link.webLink-meta.xml
├── compactLayouts/
│   └── My_Layout.compactLayout-meta.xml
└── listViews/
    └── My_View.listView-meta.xml
```

The JSON's `declarative_metadata_sample_definition` shows the legacy inline form (e.g., `<validationRules>` inside `<CustomObject>`). When authoring in SFDX source format, take the inner element of that sample, drop it into its own file under the appropriate sub-directory, and add the standard `<?xml ...?>` + namespace wrapper using the type name as the root (e.g., `<ValidationRule xmlns=...>`).

#### Directory Structure (Salesforce DX)

```text
force-app/main/default/
├── objects/
│   └── MyObject__c/
│       ├── MyObject__c.object-meta.xml
│       └── fields/
│           └── MyField__c.field-meta.xml
├── flows/
│   └── My_Flow.flow-meta.xml
├── classes/
│   ├── MyClass.cls
│   └── MyClass.cls-meta.xml
└── profiles/
    └── Admin.profile-meta.xml
```

### Examples of Well-Formed Files

**CustomObject Example**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Custom Object</label>
    <pluralLabel>My Custom Objects</pluralLabel>
    <nameField>
        <label>Name</label>
        <type>Text</type>
    </nameField>
    <deploymentStatus>Deployed</deploymentStatus>
    <sharingModel>ReadWrite</sharingModel>
    <enableActivities>true</enableActivities>
    <enableHistory>true</enableHistory>
</CustomObject>
```

**Flow Example**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>61.0</apiVersion>
    <status>Active</status>
    <processType>AutoLaunchedFlow</processType>
    <start>
        <locationX>50</locationX>
        <locationY>50</locationY>
    </start>
</Flow>
```
## Updates & Versioning

### Current Version

- **API Version**: 67.0
- **Release**: Summer 26
- **Generated**: 2026-06-10 11:21:11

### Version Compatibility

This skill documentation is generated from Salesforce Metadata API version 67.0. When working with different API versions:

- **Newer versions**: May have additional fields or metadata types not documented here
- **Older versions**: Some fields or types may not be available
- **Check your org**: Use `sf project retrieve` to see what's available in your org

### Updating the Skill

This skill is automatically generated from source JSON files. To update:

1. Regenerate source JSON files from latest Salesforce WSDL
2. Run the skill generator script
3. Review changes in generation log
4. Deploy updated skill
## Additional Resources

### Official Salesforce Documentation

- [Metadata API Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/)
- [Metadata Types Reference](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_types_list.htm)
- [Salesforce DX Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/)

### Salesforce CLI Commands

- `sf project deploy validate`: Validate metadata before deploying
- `sf project deploy start`: Deploy metadata to org
- `sf project retrieve start`: Retrieve metadata from org
- `sf project convert`: Convert between source and metadata formats

### Related Skills

- **Enterprise API**: For SOQL queries and DML operations
- **Tooling API**: For development tools and metadata queries
- **SFDX**: For project structure and deployment
## Support

### Getting Help

If you encounter issues or have questions:

1. **Check the Index**: `metadata_index_table.md` (in this `references/` folder) lists all available types
2. **Review Examples**: See usage examples above for common patterns
3. **Consult WSDL**: Check `wsdl_segment` in JSON files for schema details
4. **Salesforce Documentation**: Official docs have additional context

### Reporting Issues

For issues with this skill:

- Check that the metadata type exists in your Salesforce org version
- Verify file paths are correct
- Review generation log for warnings or errors
- Contact the skill maintainer with specific error details

### Contributing

This skill is automatically generated. To contribute:

- Report incorrect or missing information
- Suggest improvements to documentation structure
- Provide feedback on token optimization strategies

---
