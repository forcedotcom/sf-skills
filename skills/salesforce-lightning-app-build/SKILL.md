---
name: salesforce-lightning-app-build
description: Use this skill to build and orchestrate complete Salesforce Lightning Applications (LEX Apps), custom projects, or end-to-end business solutions from a natural language scenario. Triggers when a user requests a "custom app", a "business solution", or describes any scenario requiring multiple interconnected Salesforce components to be built together into a complete Lightning Experience (LEX) Application. Orchestrates the sequenced creation of Custom Objects, Relationships, Fields, Lightning Record Pages, Custom Tabs, Custom Applications, Permission Sets, and OPTIONALLY Flows and Validation Rules.
metadata:
  category: orchestration
  related-skills: salesforce-custom-object, salesforce-custom-field, salesforce-custom-tab, salesforce-flexipage, salesforce-custom-application, salesforce-flow, salesforce-validation-rule, salesforce-list-view
---

# Salesforce Lightning Application Build

## Overview

Build complete Lightning Experience applications from natural language by orchestrating multiple metadata types in proper dependency order. This skill acts as a "conductor" that invokes specialized metadata skills when available, or generates metadata directly when no skill exists.

## When to Use This Skill
**Use when:**
- User requests a "complete app", "Lightning app", or "end-to-end solution"
- User says "build an app", "create an application", "build a [type] app" (project management, tracking, etc.)
- Request involves 3+ metadata types working together (objects + fields + pages + security)
- User describes multiple custom objects with relationships between them
- User mentions custom objects AND Lightning Record Pages in the same request
- User mentions custom objects AND permission sets/security in the same request
- Request includes phrases like "allows users to manage/track", "management system", "tracking app"
- Need to ensure proper sequencing (Objects → Fields → UI → Security)

**Examples that should trigger this skill:**
- "Build a project management app with Tasks, Resources, and Supplies objects"
- "Create an app to track vehicles with Lightning pages and permission sets"
- "I need a Space Station management system with multiple objects and relationships"
- "Build an employee onboarding app with custom Lightning Record Pages"

**Do NOT use when:**
- Creating a single metadata component (use specific metadata skill instead)
- Troubleshooting or debugging existing metadata
- Building Salesforce Classic apps (not Lightning Experience)
- User asks for just one object, or just one page, or just one permission set (without others)
---

## Metadata Type Registry

This table shows which metadata types are commonly needed for LEX apps and their skill availability.

| Metadata Type | Skill Available? | Skill Name | Usage Rule |
|---------------|------------------|------------|------------|
| **Custom Object** | ✅ YES | `salesforce-custom-object` | MUST use skill |
| **Custom Field** | ✅ YES | `salesforce-custom-field` | MUST use skill |
| **Custom Tab** | ✅ YES | `salesforce-custom-tab` | MUST use skill |
| **FlexiPage** | ✅ YES | `salesforce-flexipage` | MUST use skill |
| **Custom Application** | ✅ YES | `salesforce-custom-application` | MUST use skill |
| **List View** | ✅ YES | `salesforce-list-view` | MUST use skill |
| **Validation Rule** | ✅ YES | `salesforce-validation-rule` | MUST use skill (if requested) |
| **Flow** | ✅ YES | `salesforce-flow` | MUST use skill (if requested) |
| **Permission Set** | ❌ NO | - | Generate directly using Metadata API knowledge |

### Skill Usage Rules

**CRITICAL RULE**: When a skill exists for a metadata type (✅ YES in table above), you **MUST** invoke that skill. Do NOT generate the metadata directly.

**FALLBACK RULE**: When NO skill exists for a metadata type (❌ NO in table above), you **MAY** generate the metadata directly using your knowledge of Salesforce Metadata API and best practices.

**RATIONALE**: Specialized skills contain validated patterns, error handling, and field-specific knowledge that prevent deployment failures. 

---

## Dependency Graph & Build Order

### Phase 1: Data Model (Foundation)
```
Custom Objects (no dependencies)
    ↓
Custom Fields (depends on: Objects exist)
    ↓
Relationships (depends on: Both parent and child objects + fields exist)
```

**Skills to invoke in order:**
1. `salesforce-custom-object` for each object
2. `salesforce-custom-field` for each field (including Master-Detail, Lookup, Roll-up Summary)

### Phase 2: Business Logic (Optional - only if requested)
```
Validation Rules (depends on: Fields exist)
    ↓
Flows (depends on: Objects, Fields exist)
```

**Skills to invoke (only if user requested):**
1. `salesforce-validation-rule` if validation requirements mentioned
2. `salesforce-flow` if automation/workflow requirements mentioned

### Phase 3: User Interface
```
List Views (depends on: Objects, Fields exist)
    ↓
Custom Tabs (depends on: Objects exist)
    ↓
FlexiPages (depends on: Objects, Tabs exist)
```

**Skills to invoke in order:**
1. `salesforce-list-view` for filtered record views (if requested)
2. `salesforce-custom-tab` for each object tab
3. `salesforce-flexipage` for record/home/app pages

### Phase 4: Application Assembly
```
Custom Application (depends on: Tabs exist)
```

**Skills to invoke:**
1. `salesforce-custom-application` to create the Lightning App container

### Phase 5: Security & Access
```
Permission Sets (depends on: Objects, Fields, Tabs, App exist)
```

**Fallback generation (no skill available):**
1. Generate Permission Set XML directly with access to:
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

```
📋 Lightning App Build Plan: [App Name]

DATA MODEL:
- Custom Objects: [list with object names]
- Custom Fields: [list grouped by object]
- Relationships: [list M-D and Lookup relationships]

BUSINESS LOGIC (if applicable):
- Validation Rules: [list with object and rule name]
- Flows: [list with flow name and type]

USER INTERFACE:
- List Views: [list with object and view name]
- Custom Tabs: [list with object]
- FlexiPages: [list with page name and type]
- Custom Application: [app name]

SECURITY:
- Permission Sets: [list with purpose]

METADATA SKILLS TO INVOKE:
- salesforce-custom-object (x N)
- salesforce-custom-field (x N)
- salesforce-validation-rule (x N) - if validation requirements identified
- salesforce-flow (x N) - if automation requirements identified
- salesforce-custom-tab (x N)
- salesforce-flexipage (x N)
- salesforce-custom-application (x 1)
- [fallback] Permission Set XML generation (x N)

DEPENDENCY ORDER:
1. Phase 1: Data Model (Objects → Fields)
2. Phase 2: Business Logic (Validation Rules → Flows)
3. Phase 3: User Interface (List Views → Tabs → Pages)
4. Phase 4: App Assembly (Application)
5. Phase 5: Security (Permission Sets)
```

### STEP 2: Skill Invocation Sequence

Execute in strict dependency order. For each metadata component:

1. **Check Metadata Type Registry**: Does a skill exist?
2. **If YES (✅)**: Invoke the specialized skill with required parameters
3. **If NO (❌)**: Generate metadata directly using Metadata API knowledge
4. **Handle Errors**: If skill invocation fails, log error and continue (don't block entire app)

**Invocation Pattern Example:**

- For Custom Object → Invoke `salesforce-custom-object`
- For Custom Field → Invoke `salesforce-custom-field`
- For Validation Rule → Invoke `salesforce-validation-rule`
- For Flow → Invoke `salesforce-flow`
- For Custom Tab → Invoke `salesforce-custom-tab`
- For FlexiPage → Invoke `salesforce-flexipage`
- For Custom Application → Invoke `salesforce-custom-application`
- For Permission Sets (no skill) → Generate XML directly

---

## Error Handling

### Critical Errors (Stop Execution)

Stop and ask user for clarification if:
- User request is too vague to extract any objects or fields
- Conflicting requirements detected (e.g., "make it private" + "everyone should see it")
- Invalid Salesforce naming detected (reserved words like `Order`, `Group`)

### Non-Critical Errors (Continue with Warning)

Log warning and continue if:
- Optional component fails (e.g., List View generation fails)
- Skill invocation fails for non-critical metadata
- Validation Rule or Flow has minor issues

**Warning Pattern:**
```
⚠️  Warning: [Component Type] generation encountered issue
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

### 5. Validate Before Building
Check for:
- Reserved words in API names
- Relationship limits (max 2 M-D per object)
- Name length limits
- Duplicate names