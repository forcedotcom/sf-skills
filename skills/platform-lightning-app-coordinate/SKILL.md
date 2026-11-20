---
name: platform-lightning-app-coordinate
description: "Build complete, tab-based Salesforce Lightning Experience applications from natural language descriptions. Load this coordinator before individual metadata generators when a request combines a CustomApplication with supporting custom objects, fields, relationships, tabs, Lightning record pages (FlexiPages), list views, or permission sets—for example an employee directory or project-management app in the App Launcher. Load platform-metadata-api-context-get alongside the per-type generators before writing metadata. Do not use for a single component, an app container grouping existing tabs, or a React/UI bundle application."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "60.0"
  relatedSkills:
    - "automation-flow-generate"
    - "platform-custom-application-generate"
    - "platform-custom-field-generate"
    - "platform-custom-object-generate"
    - "platform-custom-tab-generate"
    - "platform-flexipage-generate"
    - "platform-list-view-generate"
    - "platform-permission-set-generate"
    - "platform-validation-rule-generate"
    - "platform-metadata-api-context-get"
  mcpTools:
    metadata-experts:
      tools: ["execute_metadata_action"]
      semver: ">=1.0.0"
---

# Generating Lightning App

## Overview

Build a complete, deployable Salesforce Lightning Experience application from a natural language description by defining a Lightning Custom Application and orchestrating its dependent metadata types in correct dependency order. Invoke specialized metadata skills when available; generate metadata directly when no skill exists.

## When to Use This Skill

**Use when:**

- User requests a "Lightning app", or "end-to-end solution"
- User says "build an app", "create an application", "build a [type] app" (project management, tracking, etc.)
- The work produces a custom app (CustomApplication) plus supporting metadata, not a lone object, page, or tab in isolation

**Examples that should trigger this skill:**

- "Build a project management lightning app with Tasks, Resources, and Supplies objects"
- "Create a LEX app to track vehicles with Lightning pages and permission sets"
- "I need a Space Station management system with multiple objects and relationships"
- "Build an employee onboarding lightning app with custom Lightning Record Pages"

**Do NOT use when:**

- Creating a single metadata component (use specific metadata skill instead)
- Troubleshooting or debugging existing metadata
- Building Salesforce Classic apps (not Lightning Experience)
- User asks for just one object, or just one page, or just one permission set (without others)
- User only needs to create or configure an app container (grouping existing tabs) without other metadata; use `platform-custom-application-generate` instead

## Metadata Type Registry

This table shows which metadata types are commonly needed for Lightning Experience apps, their skill availability, and API context requirement.

| Metadata Type | Skill Name | API Context | Usage Rule |
|---------------|------------|-------------|------------|
| **Custom Object** | `platform-custom-object-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |
| **Custom Field** | `platform-custom-field-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |
| **Custom Tab** | `platform-custom-tab-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |
| **FlexiPage** | `platform-flexipage-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |
| **Custom Application** | `platform-custom-application-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |
| **List View** | `platform-list-view-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context (if requested) |
| **Validation Rule** | `platform-validation-rule-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context (if requested) |
| **Flow** | `automation-flow-generate` | `metadata-experts` pipeline | MUST load skill AND run pipeline. **Exempt from the non-Flow schema-context step**. |
| **Permission Set** | `platform-permission-set-generate` | `platform-metadata-api-context-get` | MUST load skill AND consume schema context |

### Usage Rules

**SKILL RULE**: When a skill exists for a metadata type, you **MUST** load that skill. Do NOT generate metadata directly without loading the skill first.

**API CONTEXT RULE**: For every metadata type (except Flow), you **MUST** load `platform-metadata-api-context-get` alongside the generator and consume the type's required schema sections before generating. Do NOT generate metadata without attempting schema context first. The generator provides patterns and rules; schema context provides fields, enums, and child types. Bundled assets are not live-org/version discovery; check compatibility with the project's API version. Both are essential.

**FALLBACK RULE**: When no skill exists for a metadata type you need, generate the metadata directly using your knowledge of Salesforce Metadata API and best practices. API context is still required.

**RATIONALE**: Generator skills contain validated patterns and constraints. Schema context provides authoritative XML definitions; target-version compatibility still needs validation. Together they prevent deployment failures.

---

## Dependency Graph & Build Order

### Phase 1: Data Model (Foundation)

```text
Custom Objects (no dependencies)
    ↓
Custom Fields (depends on: Objects exist)
    ↓
Relationships (depends on: Both parent and child objects + fields exist)
```

**Metadata types in this phase:**

1. `platform-custom-object-generate` - once, with all objects
2. `platform-custom-field-generate` - once, with all fields (including Master-Detail, Lookup, Roll-up Summary)

### Phase 2: Business Logic (Optional - only if requested)

```text
Validation Rules (depends on: Fields exist)
    ↓
Flows (depends on: Objects, Fields exist)
```

**Metadata types in this phase (only if user requested):**

1. `platform-validation-rule-generate` - once, if validation requirements mentioned
2. `automation-flow-generate` - once, if automation/workflow requirements mentioned

### Phase 3: User Interface

```text
List Views (depends on: Objects, Fields exist)
    ↓
Custom Tabs (depends on: Objects exist)
    ↓
FlexiPages (depends on: Objects, Tabs exist)
```

**Metadata types in this phase:**

1. `platform-list-view-generate` - once, for filtered record views (if requested)
2. `platform-custom-tab-generate` - once, with all object tabs
3. `platform-flexipage-generate` - once, with all record/home/app pages

### Phase 4: Application Assembly

```text
Custom Application (depends on: Tabs exist)
```

**Metadata types in this phase:**

1. `platform-custom-application-generate` - once, to create the Lightning App container

### Phase 5: Security & Access

```text
Permission Sets (depends on: Objects, Fields, Tabs, App exist)
```

**Metadata types in this phase:**

1. `platform-permission-set-generate` - once, with all permission sets and access to:
   - Objects (Read, Create, Edit, Delete)
   - Fields (Read, Edit)
   - Tabs (Visible)
   - Custom Application (Visible)

---

## Execution Workflow

### STEP 1: Requirements Analysis & Planning

**Actions:**

1. Parse user's natural language request
2. Extract business entities (become Custom Objects)
3. Extract attributes/properties (become Custom Fields)
4. Identify relationships (Master-Detail, Lookup)
5. Detect validation requirements (become Validation Rules)
6. Detect automation requirements (become Flows)
7. Identify user personas (inform Permission Sets)

**Output: Build Plan**

Generate a structured plan listing:

```text
Lightning App Build Plan: [App Name]

DATA MODEL:
- Custom Objects: [list with object names]
- Custom Fields: [list grouped by object]
- Relationships: [list M-D and Lookup relationships]

BUSINESS LOGIC (if applicable):
- Validation Rules: [list with object and rule name]
- Flows: [list with flow name and type]

USER INTERFACE:
- List Views (if requested): [list with object and view name]
- Custom Tabs: [list with object]
- FlexiPages: [list with page name and type]
- Custom Application: [app name]

SECURITY:
- Permission Sets: [list with purpose]

PER-TYPE EXECUTION (skill + API context for each):
- CustomObject: load platform-custom-object-generate + consume platform-metadata-api-context-get for CustomObject
- CustomField: load platform-custom-field-generate + consume platform-metadata-api-context-get for CustomField
- ValidationRule: load platform-validation-rule-generate + consume platform-metadata-api-context-get for ValidationRule (if requested)
- Flow: load automation-flow-generate + run metadata-experts pipeline (if requested)
- ListView: load platform-list-view-generate + consume platform-metadata-api-context-get for ListView (if requested)
- CustomTab: load platform-custom-tab-generate + consume platform-metadata-api-context-get for CustomTab
- FlexiPage: load platform-flexipage-generate + consume platform-metadata-api-context-get for FlexiPage
- CustomApplication: load platform-custom-application-generate + consume platform-metadata-api-context-get for CustomApplication
- PermissionSet: load platform-permission-set-generate + consume platform-metadata-api-context-get for PermissionSet

STATUS LINES TO EMIT BEFORE FILE WRITES:
- `type=<Type> skill=complete context=complete|unavailable context_sections=<section-list|none>`
- Flow exception: `type=Flow skill=complete pipeline=complete`

DEPENDENCY ORDER:
1. Phase 1: Data Model (Objects -> Fields)
2. Phase 2: Business Logic (Validation Rules -> Flows)
3. Phase 3: User Interface (List Views -> Tabs -> Pages)
4. Phase 4: App Assembly (Application)
5. Phase 5: Security (Permission Sets)
```

### STEP 2: Per-Type Execution

Execute these four steps for each metadata type, one type at a time. Complete all four steps for the current type before moving to the next type. Do NOT skip any step.

| Step | What to do | Why |
|------|-----------|-----|
| **① Load skill** | Search for and read the per-type SKILL.md and load `platform-metadata-api-context-get` alongside it | Gives you the XML structure, required elements, naming rules, and validation constraints |
| **② Consume API context** | Resolve this type's asset using the context skill's documented lookup; extract only `fields` and the needed `sub_types`, enums, or child-type sections with `jq`/programmatic parsing. Use targeted `wsdl_segment` or examples only when needed; never read whole schema files. | Confirms allowed values and required vs. optional fields without loading unrelated schema. Check target-version compatibility separately. |
| **③ Record status** | Emit: `type=<Type> skill=complete context=complete\|unavailable context_sections=<section-list\|none>` | Confirms both steps were attempted before any files are written and records which schema sections were consumed |
| **④ Generate files** | Generate all files for this type, then checkpoint | Only after ①②③ are done. Verify, then move to the next type. |

**Do NOT combine ① and ② into a single action or skip ② after completing ①.** They are separate steps that serve different purposes. After loading the skill you may feel ready to generate — stop and do ② first.

If the context skill or required type/section is unavailable after a real lookup attempt (including its index recovery), record `context=unavailable`, name the missing context, and generate using skill knowledge alone. Do not claim schema confirmation or invent unsupported fields/enums. Not attempting ② at all is a bug.

---

**1. Custom Objects**
- ① Load skill: Read `platform-custom-object-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for CustomObject
- ③ Status: `type=CustomObject skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all Custom Object files, then proceed to #2

**2. Custom Fields**
- ① Load skill: Read `platform-custom-field-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for CustomField
- ③ Status: `type=CustomField skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all Custom Field files, then proceed to #3

**3. Validation Rules** (only if requested)
- ① Load skill: Read `platform-validation-rule-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for ValidationRule
- ③ Status: `type=ValidationRule skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all Validation Rule files, then proceed to #4

**4. Flows** (only if requested)
- ① Load skill: Read `automation-flow-generate` SKILL.md
- ② Pipeline: Run `metadata-experts/execute_metadata_action` 3-step pipeline (exempt from the non-Flow schema-context step)
- ③ Status: `type=Flow skill=complete pipeline=complete`
- ④ Generate + Checkpoint: Generate all Flow files via the pipeline, then proceed to #5

**5. List Views** (only if requested)
- ① Load skill: Read `platform-list-view-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for ListView
- ③ Status: `type=ListView skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all List View files, then proceed to #6

**6. Custom Tabs**
- ① Load skill: Read `platform-custom-tab-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for CustomTab
- ③ Status: `type=CustomTab skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all Custom Tab files, then proceed to #7

**7. FlexiPages**
- ① Load skill: Read `platform-flexipage-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for FlexiPage
- ③ Status: `type=FlexiPage skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all FlexiPage files, then proceed to #8

**8. Custom Application**
- ① Load skill: Read `platform-custom-application-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for CustomApplication
- ③ Status: `type=CustomApplication skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate the Custom Application file, then proceed to #9

**9. Permission Sets**
- ① Load skill: Read `platform-permission-set-generate` SKILL.md
- ② API context: Consume `platform-metadata-api-context-get` for PermissionSet
- ③ Status: `type=PermissionSet skill=complete context=complete|unavailable context_sections=<section-list|none>`
- ④ Generate + Checkpoint: Generate all Permission Set files — all types complete

### STEP 3: Final Artifact Assembly

After all phases complete, consolidate outputs into deployment-ready structure.

---

## Output

The completed build produces:

1. **Salesforce DX Project Directory** containing all generated metadata
   - Organized by standard SFDX structure: `force-app/main/default/`
2. **Metadata Files** - One file per component, organized by type:

   ```text
   force-app/main/default/
   ├── objects/              # Custom Objects (.object-meta.xml)
   ├── fields/               # Custom Fields (.field-meta.xml)
   ├── tabs/                 # Custom Tabs (.tab-meta.xml)
   ├── flexipages/           # Lightning Pages (.flexipage-meta.xml)
   ├── applications/         # Custom Applications (.app-meta.xml)
   ├── permissionsets/       # Permission Sets (.permissionset-meta.xml)
   ├── flows/                # Flows (.flow-meta.xml) - if applicable
   └── objects/.../validationRules/  # Validation Rules (.validationRule-meta.xml) - if applicable
   ```

3. **Deployment Manifest** (`package.xml`)
   - Lists all components with proper API version
   - Organized by metadata type in dependency order
   - Ready for Salesforce CLI deployment or Metadata API deployment
4. **Build Summary Report** - A markdown file listing:
   - Every component created
   - Component type and API name
   - File path location
   - Dependency relationships
   - Any warnings or recommendations

**Example Summary Structure:**

```text
Lightning App Build Complete: Project Management App

METADATA GENERATED:
1 Custom Objects
   - Project__c -> force-app/main/default/objects/Project__c/Project__c.object-meta.xml
   - Task__c -> force-app/main/default/objects/Task__c/Task__c.object-meta.xml
   - Resource__c -> force-app/main/default/objects/Resource__c/Resource__c.object-meta.xml

2 Custom Fields
   - Project__c.Name -> force-app/main/default/objects/Project__c/fields/Name.field-meta.xml
   - Project__c.Status__c -> force-app/main/default/objects/Project__c/fields/Status__c.field-meta.xml
   [... etc ...]

3 Custom Tabs
   - Project__c -> force-app/main/default/tabs/Project__c.tab-meta.xml
   [... etc ...]

4 Lightning Record Pages
   - Project_Record_Page -> force-app/main/default/flexipages/Project_Record_Page.flexipage-meta.xml
   [... etc ...]

5 Custom Application
   - Project_Management -> force-app/main/default/applications/Project_Management.app-meta.xml

6 Permission Sets
   - Project_Manager -> force-app/main/default/permissionsets/Project_Manager.permissionset-meta.xml
   - Project_User -> force-app/main/default/permissionsets/Project_User.permissionset-meta.xml

WARNINGS: None
```

---

## Validation

Before presenting the completed build to the user, verify cross-component integrity:

- [ ] **Object-Tab Coverage**: Every Custom Object has at least one Custom Tab
- [ ] **Relationship Integrity**: Every Custom Object referenced in a relationship (parent or child) exists in the build
- [ ] **Field References in Pages**: Every field referenced in a FlexiPage exists on the corresponding object
- [ ] **Tab References in App**: Every tab referenced in the Custom Application was successfully created
- [ ] **Permission Set Completeness**: Permission Sets grant access to all generated objects, fields, tabs, and the application
- [ ] **No Orphaned Components**: No tabs without objects, no pages without corresponding tabs, no app without tabs
- [ ] **Deployment Manifest Completeness**: `package.xml` includes all generated components in proper dependency order

**Validation Failure Handling (Category 2):**

- If validation fails, include failed checks in the Build Summary Report under a `VALIDATION WARNINGS` section
- These are post-generation issues — do NOT block delivery of the build, but clearly communicate what needs manual review or correction
- Provide specific remediation steps for each failed validation check

**Note**: Individual component validations (reserved words, name lengths, field types, etc.) are handled by specialized metadata skills and do not need to be re-validated here.

---

## Error Handling

### Category 1: Stop and Ask User

Stop execution and ask for clarification if:

- User request is too vague to extract any objects or fields
- Conflicting requirements detected (e.g., "make it private" + "everyone should see it")
- Invalid Salesforce naming detected (reserved words like `Order`, `Group`)

### Category 2: Post-Generation Warnings (Log Warning, Continue)

Log warning and continue if:

- Cross-component validation check fails (e.g., field referenced in FlexiPage doesn't exist on object)
- Optional component generation fails (e.g., List View generation has minor issues)
- Validation Rule or Flow has minor output issues

**Warning Pattern:**

```yaml
Warning: [Component Type] generation encountered issue
    Component: [Name]
    Issue: [Description]
    Impact: [What won't work]
    Recommendation: [How to fix manually]
    Continuing with remaining components...
```

---

## Best Practices

### 1. Always Follow Dependency Order

Never invoke skills out of sequence. Fields need objects, pages need tabs, apps need tabs.

### 2. Use Skills When Available

Don't reinvent the wheel. Specialized skills have field-specific validation that prevents deployment errors.

### 3. Generate Thoughtful Defaults

When user doesn't specify details:

- Use Text name fields for human entities
- Use AutoNumber for transactions
- Enable Search and Reports for user-facing objects
- Set sharingModel based on relationships

### 4. Validate Before Building

Check for:

- Reserved words in API names
- Relationship limits (max 2 M-D per object)
- Name length limits
- Duplicate names
