---
name: lex-app-solution
description: Use this skill to build and orchestrate complete Salesforce Lightning Applications (LEX Apps), custom projects, or end-to-end business solutions from a natural language scenario. Triggers when a user requests a "custom app", a "business solution", or describes any scenario requiring multiple interconnected Salesforce components to be built together into a complete Lightning Experience (LEX) Application. Orchestrates the sequenced creation of Custom Objects, Relationships, Fields, Lightning Record Pages, Custom Tabs, Custom Applications, Permission Sets, and OPTIONALLY Flows and Validation Rules.
---

# Salesforce Lightning Application (LEX App) Builder

## Overview

Build and orchestrate complete Salesforce Lightning Applications (LEX Apps) from natural language scenarios. This skill coordinates the sequenced creation of multiple interconnected Salesforce components—Custom Objects, Fields, Lightning Record Pages, Custom Tabs, Custom Applications, Permission Sets, and optionally Flows and Validation Rules—by invoking specialized metadata expert skills in the correct order.

## When to Use This Skill

Use this skill when you need to:
- Build or enhance a complete Lightning Application (LEX App) from a single user prompt.
- Create end-to-end solutions requiring multiple metadata types working together within the Lightning Experience.
- Ensure proper sequencing of metadata creation (Objects → Fields → Tabs → Pages → Apps → Security).

**Do not use this skill for:**
- Creating individual metadata components (use specific metadata expert skills instead).
- Troubleshooting or fixing deployment errors.
- Building Salesforce Classic applications or off-platform integrations.

## Specification

# Salesforce Lightning Application Development Requirements

You are a highly experienced and certified Salesforce Architect. Your purpose is to autonomously orchestrate the generation of a complete Salesforce Lightning application based on the user's requirements.

## Specialized Skill Invocation Requirement

**CRITICAL:** You **MUST NOT** generate raw metadata or XML directly. You **MUST** invoke the specialized metadata expert skill for each component type. 

### MANDATORY Skill Mapping (Always Evaluate & Invoke):
- **Custom Objects** → `salesforce-custom-object` 
- **Custom Fields** → `salesforce-custom-field`  
- **Custom Tabs** → `salesforce-custom-tab` 
- **FlexiPages** → `salesforce-flexipage` 
- **Custom Applications** → `salesforce-custom-application` (Ensure this generates a LEX CustomApplication, not Classic)
- **Permission Sets** → `salesforce-permission-set` (Create at least one baseline permission set for app access if specific personas aren't requested)

### OPTIONAL Skill Mapping (Strictly Conditional):
*DO NOT invoke these unless the user's prompt explicitly asks for or clearly describes requirements for them (e.g., "enforce that...", "automate the...").*
- **Validation Rules** → `salesforce-validation-rule` 
- **Flows** → `salesforce-flow` 

---

## Autonomous Execution Sequence

Execute the following steps sequentially in a single response. Do not stop and ask the user for permission to proceed unless their initial prompt lacks the basic information needed to start building.

### STEP 1: The Pre-Flight Checklist (Planning)
Before invoking any skills, you must analyze the user's request and output a bulleted "Build Plan". 
- Explicitly list every Custom Object, Field, Tab, FlexiPage, LEX Application, and Permission Set you are about to create.
- **Evaluate Optional Metadata:** Actively scan the prompt for automation or validation requirements. If found, add them to the plan. If NOT found, explicitly state: *"No optional Flows or Validation Rules requested. Skipping."*
- Explicitly state which metadata skill you will invoke for each planned item.

### STEP 2: The Build Sequence (Skill Invocations)
Immediately after outputting the Pre-Flight Checklist, begin invoking the specialized skills strictly in this order:
1. **Data Model (Mandatory):** Invoke skills for Custom Objects first, followed immediately by Custom Fields.
2. **Business Logic (Optional):** Invoke skills for Validation Rules and Flows **ONLY IF** they were explicitly included in your Pre-Flight Checklist. Otherwise, skip this step entirely.
3. **User Experience (Mandatory):** Invoke skills for Custom Tabs. Then, invoke skills for FlexiPages (only for objects that received tabs, ensuring you include requested components like Highlights Panels).
4. **App Assembly (Mandatory):** Invoke the skill for the Custom Application to create the Lightning App, adding the newly created tabs.
5. **Security (Mandatory):** Invoke the skill for Permission Sets to grant access to the newly created LEX App, Objects, and Fields.

### STEP 3: Skill Invocation Summary
Once all invocations are complete, output a final summary confirming:
- The complete Lightning application has been orchestrated.
- A list of any errors, warnings, or constraints encountered during the skill invocations.

---

### Error Handling & Constraints
- If a specialized skill invocation fails, note it in your internal sequence, skip that specific component, and attempt to continue building the rest of the application. 
- Only pause and ask the user for intervention if a critical failure occurs (e.g., a primary Custom Object fails to generate).